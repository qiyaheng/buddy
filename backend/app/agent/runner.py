"""Agent 运行编排：事件消费、过程块增量落库、中断与错误收口。"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from ..config import settings
from ..errors import ApiError, BadRequestError, NotFoundError
from ..models.app_config import ModelConfig, Provider
from ..models.workspace import Artifact, Message, Task, UsageRecord
from ..db import SessionLocal
from . import events as ev
from .fake import FakeContext, fake_events
from .llm import AgentStopped, build_async_openai_client, stream_chat
from .prompts import build_chat_messages, build_system_prompt
from .state import RunControl
from .state import registry as run_registry

logger = logging.getLogger(__name__)


@dataclass
class PreparedRun:
    task_id: str
    user_message_id: str
    assistant_message_id: str
    model_config_id: str | None
    history: list[tuple[str, str]]
    system_prompt: str


def fake_mode() -> bool:
    return os.environ.get("SMEBUDDY_FAKE_LLM", "").strip() == "1"


def prepare_run(task_id: str, content: str, model_config_id: str | None) -> PreparedRun:
    """同步预校验 + 落库用户消息与占位助手消息。错误以 ApiError 抛出（返回 JSON）。

    调用方必须先通过 run_registry 占位（保证并发互斥），本函数不再检查运行态。
    """
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            raise NotFoundError("任务不存在")

        content = (content or "").strip()
        if not content:
            raise BadRequestError("消息内容不能为空")
        if len(content) > 20000:
            raise BadRequestError("单条消息不能超过 20000 字")

        # 历史消息（仅已完成、有正文的）
        history_rows = (
            db.query(Message.role, Message.content)
            .filter(Message.task_id == task_id, Message.status == "done")
            .order_by(Message.created_at.asc(), Message.id.asc())
            .all()
        )
        history = [(row.role, row.content) for row in history_rows if row.content]

        chosen_model_id: str | None = model_config_id or task.model_id
        if not fake_mode() and not chosen_model_id:
            raise BadRequestError("尚未配置可用模型，请先在设置中添加模型")
        if not fake_mode() and chosen_model_id:
            model = db.get(ModelConfig, chosen_model_id)
            if model is None:
                raise BadRequestError("选择的模型已不可用，请重新选择")

        system_prompt = build_system_prompt(
            expert_snapshot=task.expert_snapshot,
            skill_snapshots=list(task.skill_snapshots or []),
        )

        user_msg = Message(task_id=task_id, role="user", content=content, status="done")
        assistant_msg = Message(
            task_id=task_id, role="assistant", content="", blocks=[], status="streaming"
        )
        db.add_all([user_msg, assistant_msg])
        task.status = "running"
        task.error_message = None
        task.last_message_at = assistant_msg.created_at
        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return PreparedRun(
            task_id=task_id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant_msg.id,
            model_config_id=chosen_model_id,
            history=history,
            system_prompt=system_prompt,
        )
    finally:
        db.close()


def _persist_snapshot(
    *,
    task_id: str,
    assistant_message_id: str,
    content: str,
    blocks: list[dict[str, Any]],
    status: str,
    task_status: str,
    error_text: str | None = None,
    usage: dict[str, int] | None = None,
    provider_id: str | None = None,
    model_name: str | None = None,
) -> None:
    """同步事务：把当前运行快照写入 SQLite（每次事件后调用，保证重启可见过程）。"""
    db = SessionLocal()
    try:
        message = db.get(Message, assistant_message_id)
        if message is not None:
            message.content = content
            message.blocks = blocks
            message.status = status
            message.error_text = error_text
        task = db.get(Task, task_id)
        if task is not None:
            task.status = task_status
            task.error_message = error_text
        if usage:
            db.add(
                UsageRecord(
                    task_id=task_id,
                    message_id=assistant_message_id,
                    provider_id=provider_id,
                    model=model_name,
                    request_count=1,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    latency_ms=usage.get("latency_ms"),
                )
            )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("持久化运行快照失败 task=%s", task_id)
    finally:
        db.close()


def _write_artifact(
    task_id: str, filename: str, file_content: str, fmt: str, kind: str
) -> dict[str, Any]:
    """写产物文件并入库，返回事件负载。"""
    db = SessionLocal()
    try:
        artifact_dir = settings.artifacts_dir / task_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        path = artifact_dir / filename
        path.write_text(file_content, encoding="utf-8")
        artifact = Artifact(
            task_id=task_id,
            filename=filename,
            format=fmt,
            kind=kind,
            size_bytes=path.stat().st_size,
            absolute_path=str(path),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return {
            "id": artifact.id,
            "filename": artifact.filename,
            "format": artifact.format,
            "kind": artifact.kind,
            "size_bytes": artifact.size_bytes,
        }
    finally:
        db.close()


async def run_stream(prepared: PreparedRun, user_content: str, control: RunControl):
    """SSE 异步生成器：产出已序列化的 event-stream 文本块。"""
    task_id = prepared.task_id
    content_parts: list[str] = []
    blocks: list[dict[str, Any]] = []
    plan_index: dict[str, int] = {}
    think_index: dict[str, int] = {}
    tool_index: dict[str, int] = {}
    final_usage: dict[str, int] | None = None
    model_name: str | None = None
    provider_id: str | None = None

    async def persist(
        *, status: str = "streaming", task_status: str = "running", error_text: str | None = None
    ) -> None:
        await asyncio.to_thread(
            _persist_snapshot,
            task_id=task_id,
            assistant_message_id=prepared.assistant_message_id,
            content="".join(content_parts),
            blocks=blocks,
            status=status,
            task_status=task_status,
            error_text=error_text,
            usage=None,
        )

    async def write_artifact(filename: str, file_content: str, fmt: str, kind: str):
        return await asyncio.to_thread(
            _write_artifact, task_id, filename, file_content, fmt, kind
        )

    async def apply_event(event_data: dict[str, Any]) -> None:
        etype = event_data.get("type")
        if etype == ev.PLAN_START:
            block = {
                "type": "plan",
                "steps": [
                    {"id": s["id"], "title": s["title"], "status": "pending"}
                    for s in event_data.get("steps", [])
                ],
            }
            blocks.append(block)
            plan_index["__block"] = len(blocks) - 1
            for step in block["steps"]:
                plan_index[step["id"]] = plan_index["__block"]
        elif etype == ev.PLAN_UPDATE:
            idx = plan_index.get(event_data["step_id"])
            if idx is not None:
                for step in blocks[idx]["steps"]:
                    if step["id"] == event_data["step_id"]:
                        step["status"] = event_data["status"]
        elif etype == ev.THINK_START:
            block = {"type": "think", "id": event_data["id"], "text": ""}
            blocks.append(block)
            think_index[event_data["id"]] = len(blocks) - 1
        elif etype == ev.THINK_DELTA:
            idx = think_index.get(event_data["id"])
            if idx is not None:
                blocks[idx]["text"] += event_data["delta"]
        elif etype == ev.TOOL_CALL:
            block = {
                "type": "tool",
                "id": event_data["id"],
                "name": event_data["name"],
                "status": event_data["status"],
                "input_summary": event_data.get("input_summary", ""),
            }
            blocks.append(block)
            tool_index[event_data["id"]] = len(blocks) - 1
        elif etype == ev.TOOL_RESULT:
            idx = tool_index.get(event_data["id"])
            if idx is not None:
                blocks[idx].update(
                    {
                        "status": event_data["status"],
                        "summary": event_data.get("summary", ""),
                        "sources": event_data.get("sources", []),
                        "elapsed_ms": event_data.get("elapsed_ms"),
                    }
                )
        elif etype == ev.MESSAGE_DELTA:
            content_parts.append(event_data["delta"])
        elif etype == ev.ARTIFACT:
            blocks.append({"type": "artifact", **{k: v for k, v in event_data.items() if k != "type"}})
        elif etype == ev.USAGE:
            nonlocal final_usage
            final_usage = {
                "prompt_tokens": event_data.get("prompt_tokens", 0),
                "completion_tokens": event_data.get("completion_tokens", 0),
                "total_tokens": event_data.get("total_tokens", 0),
                "latency_ms": event_data.get("latency_ms"),
            }

    def emit(event_data: dict[str, Any]) -> str:
        return ev.sse_dumps(event_data)

    yield emit(
        ev.event(
            ev.RUN_STARTED,
            task_id=task_id,
            user_message_id=prepared.user_message_id,
            assistant_message_id=prepared.assistant_message_id,
        )
    )

    try:
        if fake_mode():
            async for event_data in fake_events(
                FakeContext(
                    control=control,
                    write_artifact=write_artifact,
                    user_content=user_content.strip(),
                )
            ):
                await apply_event(event_data)
                await persist()
                yield emit(event_data)
        else:
            # 真实模型路径：纯流式对话（工具循环在 Task 11 随调研技能加入）
            db = SessionLocal()
            try:
                model = db.get(ModelConfig, prepared.model_config_id)
                provider = db.get(Provider, model.provider_id) if model else None
            finally:
                db.close()
            if model is None or provider is None:
                raise BadRequestError("选择的模型已不可用，请重新选择")
            model_name = model.model_id
            provider_id = provider.id
            client = build_async_openai_client(provider)
            messages = build_chat_messages(
                system_prompt=prepared.system_prompt,
                history=prepared.history,
                user_content=user_content.strip(),
            )
            think_opened: dict[str, bool] = {}
            async for chunk in stream_chat(
                client=client,
                model_id=model.model_id,
                messages=messages,
                control=control,
            ):
                if chunk.reasoning:
                    if not think_opened.get("t1"):
                        await apply_event(ev.event(ev.THINK_START, id="t1"))
                        think_opened["t1"] = True
                    await apply_event(ev.event(ev.THINK_DELTA, id="t1", delta=chunk.reasoning))
                if chunk.content:
                    await apply_event(ev.event(ev.MESSAGE_DELTA, delta=chunk.content))
                if chunk.usage:
                    await apply_event(ev.event(ev.USAGE, **chunk.usage))
                await persist()
                if chunk.reasoning:
                    yield emit(ev.event(ev.THINK_DELTA, id="t1", delta=chunk.reasoning))
                if chunk.content:
                    yield emit(ev.event(ev.MESSAGE_DELTA, delta=chunk.content))
                if chunk.usage:
                    yield emit(ev.event(ev.USAGE, **chunk.usage))

        # 正常结束：usage 落库 + 任务完成
        await asyncio.to_thread(
            _persist_snapshot,
            task_id=task_id,
            assistant_message_id=prepared.assistant_message_id,
            content="".join(content_parts),
            blocks=blocks,
            status="done",
            task_status="done",
            usage=final_usage,
            provider_id=provider_id,
            model_name=model_name,
        )
        yield emit(ev.event(ev.DONE, task_id=task_id, status="done"))

    except AgentStopped:
        await _shielded_final_persist(
            prepared, "".join(content_parts), blocks, status="stopped", task_status="stopped"
        )
        yield emit(
            ev.event(
                ev.STOPPED, reason="user_stop", llm_requests=control.llm_requests
            )
        )
    except asyncio.CancelledError:
        # 客户端断链：尽力落盘后重新抛出
        await _shielded_final_persist(
            prepared, "".join(content_parts), blocks, status="stopped", task_status="stopped"
        )
        raise
    except ApiError as exc:
        await _shielded_final_persist(
            prepared,
            "".join(content_parts),
            blocks,
            status="error",
            task_status="error",
            error_text=f"[{exc.code}] {exc.message}",
        )
        yield emit(ev.event(ev.ERROR, code=exc.code, message=exc.message))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent 运行未知异常 task=%s", task_id)
        message = f"运行失败：{type(exc).__name__}"
        await _shielded_final_persist(
            prepared,
            "".join(content_parts),
            blocks,
            status="error",
            task_status="error",
            error_text=message,
        )
        yield emit(ev.event(ev.ERROR, code="internal_error", message=message))
    finally:
        run_registry.unregister(task_id)


async def _shielded_final_persist(
    prepared: PreparedRun,
    content: str,
    blocks: list[dict[str, Any]],
    *,
    status: str,
    task_status: str,
    error_text: str | None = None,
) -> None:
    """取消场景下也尽力把最终状态落盘（线程写入不受协程取消影响）。"""
    try:
        await asyncio.shield(
            asyncio.to_thread(
                _persist_snapshot,
                task_id=prepared.task_id,
                assistant_message_id=prepared.assistant_message_id,
                content=content,
                blocks=blocks,
                status=status,
                task_status=task_status,
                error_text=error_text,
                usage=None,
            )
        )
    except Exception:  # noqa: BLE001
        logger.exception("最终落盘失败 task=%s", prepared.task_id)
