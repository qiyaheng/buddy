"""文件夹 / 任务 / 消息 / 用量接口契约。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["idle", "running", "stopped", "error", "done"]
MessageRole = Literal["user", "assistant"]
MessageStatus = Literal["streaming", "done", "error", "stopped"]


# ---------- Folder ----------


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ---------- Task ----------


class TaskCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    folder_id: str | None = None
    expert_id: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    # 指定 ModelConfig 主键；不传则使用全局默认模型
    model_config_id: str | None = None


class TaskUpdate(BaseModel):
    # 缺省字段不修改；folder_id 显式传 null 表示移动到「未分组」
    title: str | None = Field(default=None, min_length=1, max_length=200)
    folder_id: str | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    folder_id: str | None
    expert_snapshot: dict[str, Any] | None
    skill_snapshots: list[dict[str, Any]]
    model_id: str | None
    model_snapshot: dict[str, Any] | None
    error_message: str | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------- Message ----------


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    role: str
    content: str
    blocks: list[dict[str, Any]]
    status: str
    error_text: str | None
    created_at: datetime


# ---------- Usage ----------


class UsageSummaryOut(BaseModel):
    request_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
