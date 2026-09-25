"""任务运行态注册表与取消信号。"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class RunControl:
    """单次任务运行的取消控制。"""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.cancel_event = asyncio.Event()
        self.async_task: asyncio.Task[None] | None = None
        self.llm_requests = 0  # LLM 实际发起请求计数（测试用）

    def request_stop(self) -> None:
        self.cancel_event.set()

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()


class RunRegistry:
    def __init__(self) -> None:
        self._controls: dict[str, RunControl] = {}

    def is_running(self, task_id: str) -> bool:
        return task_id in self._controls

    def register(self, task_id: str) -> RunControl:
        control = RunControl(task_id)
        self._controls[task_id] = control
        return control

    def get(self, task_id: str) -> RunControl | None:
        return self._controls.get(task_id)

    def unregister(self, task_id: str) -> None:
        self._controls.pop(task_id, None)

    def stop(self, task_id: str) -> bool:
        """返回是否找到了运行中的任务并发出停止信号。"""
        control = self._controls.get(task_id)
        if control is None:
            return False
        control.request_stop()
        return True


registry = RunRegistry()
