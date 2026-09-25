"""任务运行：POST SSE 流 + 停止。"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agent.runner import prepare_run, run_stream
from ..agent.state import registry as run_registry
from ..schemas.chat import RunCreate, StopOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["runs"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/{task_id}/runs")
async def create_run(task_id: str, data: RunCreate):
    # 先在事件循环线程占位，避免并发请求同时通过运行态检查
    if run_registry.is_running(task_id):
        from ..errors import ConflictError

        raise ConflictError("该任务正在运行中，请等待结束或先停止")
    control = run_registry.register(task_id)

    try:
        prepared = await asyncio.to_thread(
            prepare_run, task_id, data.content, data.model_config_id
        )
    except Exception:
        run_registry.unregister(task_id)
        raise

    return StreamingResponse(
        run_stream(prepared, data.content, control),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/{task_id}/stop", response_model=StopOut)
def stop_run(task_id: str) -> StopOut:
    stopping = run_registry.stop(task_id)
    return StopOut(task_id=task_id, stopping=stopping)
