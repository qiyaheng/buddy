"""OpenAI 兼容 LLM 客户端工厂与连接测试。

Task 6 会在此扩展流式对话与 Agent Loop；本模块只依赖模型层，不依赖 API 层。
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    AsyncOpenAI,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from sqlalchemy.orm import Session

from ..errors import ApiError, NotFoundError
from ..models import ModelConfig, Provider
from ..security import decrypt
from .state import RunControl

logger = logging.getLogger(__name__)


class AgentStopped(Exception):
    """任务被用户停止或客户端断链。"""


@dataclass
class ConnectionTestResult:
    ok: bool
    code: str  # success / auth_failed / rate_limited / timeout / network / bad_request / upstream_error / unknown
    message: str = ""


def build_openai_client(provider: Provider, *, timeout: int | None = None) -> OpenAI:
    """以本地存储配置构造 SDK 客户端；无密钥时使用占位值（兼容免鉴权本地模型）。"""
    api_key = decrypt(provider.encrypted_api_key) or "dummy-key"
    return OpenAI(
        base_url=provider.base_url.rstrip("/"),
        api_key=api_key,
        timeout=timeout or provider.timeout_seconds,
        max_retries=0,
    )


def resolve_model(db: Session, provider_id: str, model_id: str | None) -> ModelConfig:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise NotFoundError("模型服务商不存在")
    if model_id:
        model = (
            db.query(ModelConfig)
            .filter_by(provider_id=provider_id, model_id=model_id)
            .first()
        )
    else:
        model = (
            db.query(ModelConfig)
            .filter_by(provider_id=provider_id, is_default=True)
            .first()
        )
        if model is None:
            model = (
                db.query(ModelConfig)
                .filter_by(provider_id=provider_id)
                .order_by(ModelConfig.sort_order, ModelConfig.created_at)
                .first()
            )
    if model is None:
        raise NotFoundError("该服务商下尚未配置模型，请先添加模型")
    return model


def test_connection(
    db: Session, provider_id: str, model_id: str | None = None
) -> ConnectionTestResult:
    model = resolve_model(db, provider_id, model_id)
    provider = db.get(Provider, provider_id)
    assert provider is not None
    client = build_openai_client(provider)

    started = time.monotonic()
    try:
        client.chat.completions.create(
            model=model.model_id,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
    except (AuthenticationError, PermissionDeniedError) as exc:
        logger.info("连接测试-鉴权失败 provider=%s: %s", provider_id, exc)
        return ConnectionTestResult(False, "auth_failed", "API Key 无效或权限不足（401/403）")
    except RateLimitError as exc:
        logger.info("连接测试-限流 provider=%s: %s", provider_id, exc)
        return ConnectionTestResult(False, "rate_limited", "触发上游限流（429），请稍后重试")
    except APITimeoutError:
        return ConnectionTestResult(False, "timeout", f"请求超时（>{provider.timeout_seconds}s）")
    except APIConnectionError as exc:
        logger.info("连接测试-网络失败 provider=%s: %s", provider_id, exc)
        return ConnectionTestResult(False, "network", "无法连接到 Base URL，请检查地址与网络")
    except APIStatusError as exc:
        if exc.status_code in (400, 404):
            return ConnectionTestResult(
                False,
                "bad_request",
                f"上游返回 {exc.status_code}：模型 ID 可能不存在或请求不被接受",
            )
        return ConnectionTestResult(
            False, "upstream_error", f"上游服务返回错误（{exc.status_code}）"
        )
    except Exception as exc:  # noqa: BLE001 - 分类兜底，避免泄漏堆栈
        logger.exception("连接测试未知异常")
        return ConnectionTestResult(False, "unknown", f"未知错误：{type(exc).__name__}")

    elapsed = (time.monotonic() - started) * 1000
    return ConnectionTestResult(
        True, "success", f"连接成功，模型「{model.model_id}」响应正常（{elapsed:.0f}ms）"
    )


# ---------- 流式对话（Task 6） ----------


@dataclass
class StreamChunk:
    content: str = ""
    reasoning: str = ""
    usage: dict[str, int] | None = None


def build_async_openai_client(provider: Provider) -> AsyncOpenAI:
    api_key = decrypt(provider.encrypted_api_key) or "dummy-key"
    return AsyncOpenAI(
        base_url=provider.base_url.rstrip("/"),
        api_key=api_key,
        timeout=provider.timeout_seconds,
        max_retries=0,
    )


def classify_upstream_error(exc: Exception) -> ApiError:
    """把 OpenAI SDK 异常映射为统一 ApiError（code 与连接测试保持一致）。"""
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return ApiError("auth_failed", "API Key 无效或权限不足（401/403）", 502)
    if isinstance(exc, RateLimitError):
        return ApiError("rate_limited", "触发上游限流（429），请稍后重试", 503)
    if isinstance(exc, APITimeoutError):
        return ApiError("timeout", "模型响应超时，请检查网络或增大超时时间", 504)
    if isinstance(exc, APIConnectionError):
        return ApiError("network", "无法连接到模型服务，请检查 Base URL 与网络", 502)
    if isinstance(exc, APIStatusError):
        if exc.status_code in (400, 404):
            return ApiError(
                "bad_request",
                f"上游返回 {exc.status_code}：模型 ID 可能不存在或请求不被接受",
                502,
            )
        return ApiError("upstream_error", f"上游服务返回错误（{exc.status_code}）", 502)
    return ApiError("upstream_error", f"模型调用失败：{type(exc).__name__}", 500)


async def stream_chat(
    *,
    client: AsyncOpenAI,
    model_id: str,
    messages: list[dict[str, str]],
    control: RunControl,
) -> AsyncIterator[StreamChunk]:
    """流式调用 chat.completions；在每个 chunk 边界响应取消信号。"""
    control.llm_requests += 1
    if control.cancelled:
        raise AgentStopped()

    async def _open_stream(with_usage: bool):  # noqa: ANN202
        kwargs: dict[str, object] = {
            "model": model_id,
            "messages": messages,
            "stream": True,
        }
        if with_usage:
            kwargs["stream_options"] = {"include_usage": True}
        return await client.chat.completions.create(**kwargs)

    try:
        try:
            stream = await _open_stream(with_usage=True)
        except APIStatusError as exc:
            # 部分兼容端点不支持 stream_options，降级重试一次
            if exc.status_code == 400:
                logger.info("上游不支持 stream_options，降级为无 usage 流式调用")
                stream = await _open_stream(with_usage=False)
            else:
                raise

        async for chunk in stream:
            if control.cancelled:
                raise AgentStopped()
            choice = chunk.choices[0] if chunk.choices else None
            delta = getattr(choice, "delta", None) if choice else None
            if delta is not None:
                content = getattr(delta, "content", None)
                # DeepSeek-R1 等推理模型将思考放在 reasoning_content
                reasoning = getattr(delta, "reasoning_content", None)
                if content:
                    yield StreamChunk(content=content)
                if reasoning:
                    yield StreamChunk(reasoning=reasoning)
            usage = getattr(chunk, "usage", None)
            if usage is not None and (usage.prompt_tokens or usage.completion_tokens):
                yield StreamChunk(
                    usage={
                        "prompt_tokens": usage.prompt_tokens or 0,
                        "completion_tokens": usage.completion_tokens or 0,
                        "total_tokens": usage.total_tokens
                        or (usage.prompt_tokens or 0) + (usage.completion_tokens or 0),
                    }
                )
    except AgentStopped:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一分类后转 error 事件
        raise classify_upstream_error(exc) from exc
