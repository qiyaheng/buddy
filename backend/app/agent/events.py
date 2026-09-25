"""SSE 事件协议。

事件通过 text/event-stream 下发，每条消息为 `data: {json}\\n\\n`。
前端 src/renderer/src/lib/sse.ts 按 type 字段分发。
"""

from __future__ import annotations

import json
from typing import Any


def event(type_: str, **payload: Any) -> dict[str, Any]:  # noqa: A002 - 协议构造器
    return {"type": type_, **payload}


def sse_dumps(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# 事件类型常量
RUN_STARTED = "run_started"
PLAN_START = "plan_start"
PLAN_UPDATE = "plan_update"
THINK_START = "think_start"
THINK_DELTA = "think_delta"
TOOL_CALL = "tool_call"
TOOL_RESULT = "tool_result"
MESSAGE_DELTA = "message_delta"
ARTIFACT = "artifact"
USAGE = "usage"
STOPPED = "stopped"
ERROR = "error"
DONE = "done"
