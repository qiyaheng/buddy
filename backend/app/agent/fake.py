"""脚本化 Fake Agent：在无真实模型时完整演练 Agent 事件协议。

启用方式：环境变量 SMEBUDDY_FAKE_LLM=1。
错误注入：SMEBUDDY_FAKE_ERROR=auth_failed|timeout|network|rate_limited|upstream_error。
步长（秒）：SMEBUDDY_FAKE_STEP（默认 0.03）。
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ..errors import ApiError
from . import events as ev
from .llm import AgentStopped
from .state import RunControl

logger = logging.getLogger(__name__)

WriteArtifact = Callable[[str, str, str, str], Awaitable[dict[str, Any]]]


@dataclass
class FakeContext:
    control: RunControl
    write_artifact: WriteArtifact
    user_content: str


def _step_seconds() -> float:
    try:
        return float(os.environ.get("SMEBUDDY_FAKE_STEP", "0.03"))
    except ValueError:
        return 0.03


def _fail_error() -> ApiError | None:
    code = os.environ.get("SMEBUDDY_FAKE_ERROR", "").strip()
    if not code:
        return None
    messages = {
        "auth_failed": "API Key 无效或权限不足（401/403）",
        "timeout": "模型响应超时，请检查网络或增大超时时间",
        "network": "无法连接到模型服务，请检查 Base URL 与网络",
        "rate_limited": "触发上游限流（429），请稍后重试",
        "upstream_error": "上游服务返回错误（500）",
    }
    return ApiError(code, messages.get(code, f"模拟上游错误：{code}"), 502)


async def fake_events(ctx: FakeContext) -> AsyncIterator[dict[str, Any]]:
    control = ctx.control
    fail = _fail_error()

    async def checkpoint() -> None:
        await asyncio.sleep(_step_seconds())
        if control.cancelled:
            raise AgentStopped()

    # —— 1. 执行计划 ——
    steps = [
        {"id": "s1", "title": "分析任务需求"},
        {"id": "s2", "title": "检索相关资料"},
        {"id": "s3", "title": "整理并生成交付物"},
    ]
    yield ev.event(ev.PLAN_START, steps=steps)
    yield ev.event(ev.PLAN_UPDATE, step_id="s1", status="running")
    await checkpoint()
    yield ev.event(ev.PLAN_UPDATE, step_id="s1", status="done")

    # —— 2. 思考过程 ——
    yield ev.event(ev.THINK_START, id="t1")
    for piece in (
        f"收到任务：{ctx.user_content[:60]}。",
        "先拆解关键目标，再通过工具获取事实依据，",
        "最后按结论先行的方式组织正文。",
    ):
        await checkpoint()
        yield ev.event(ev.THINK_DELTA, id="t1", delta=piece)

    # —— 3. 模拟第一次 LLM 请求边界（错误注入点，此前内容必须已落库） ——
    control.llm_requests += 1
    await checkpoint()
    if fail is not None:
        raise fail

    # —— 4. 工具调用 ——
    yield ev.event(
        ev.TOOL_CALL,
        id="tool-1",
        name="web_search",
        status="started",
        input_summary=f"搜索与「{ctx.user_content[:30]}」相关的资料",
    )
    await checkpoint()
    yield ev.event(
        ev.TOOL_RESULT,
        id="tool-1",
        status="finished",
        summary="找到 3 条相关结果，已提取正文用于交叉验证",
        sources=[
            {"title": "示例来源一：行业观察", "url": "https://example.com/a"},
            {"title": "示例来源二：数据报告", "url": "https://example.com/b"},
        ],
        elapsed_ms=420,
    )

    yield ev.event(ev.PLAN_UPDATE, step_id="s2", status="running")
    await checkpoint()
    yield ev.event(ev.PLAN_UPDATE, step_id="s2", status="done")
    yield ev.event(ev.PLAN_UPDATE, step_id="s3", status="running")
    await checkpoint()

    # —— 5. 正文流式输出 ——
    markdown_pieces = [
        f"# 任务简报\n\n针对「{ctx.user_content[:40]}」，结论如下：\n\n",
        "## 核心发现\n\n",
        "- **要点一**：基于检索到的资料，趋势正在加速；\n",
        "- **要点二**：主要风险集中在执行节奏与资源投入；\n",
        "- **要点三**：建议分两阶段推进，先验证再放量。\n\n",
        "## 行动建议\n\n",
        "1. 本周完成关键假设验证；\n",
        "2. 下周输出可复用的模板与清单；\n",
        "3. 建立每周复盘机制，持续校准。\n",
    ]
    for piece in markdown_pieces:
        await checkpoint()
        yield ev.event(ev.MESSAGE_DELTA, delta=piece)

    # —— 6. 产物 ——
    await checkpoint()
    artifact = await ctx.write_artifact(
        "fake-report.md",
        "".join(markdown_pieces),
        "md",
        "document",
    )
    yield ev.event(ev.ARTIFACT, **artifact)

    yield ev.event(ev.PLAN_UPDATE, step_id="s3", status="done")

    # —— 7. 用量 ——
    yield ev.event(
        ev.USAGE,
        prompt_tokens=320,
        completion_tokens=210,
        total_tokens=530,
        latency_ms=860,
    )
