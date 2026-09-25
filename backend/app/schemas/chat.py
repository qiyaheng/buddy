"""对话运行接口契约。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    model_config_id: str | None = None


class StopOut(BaseModel):
    task_id: str
    stopping: bool
