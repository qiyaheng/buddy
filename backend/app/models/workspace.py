"""工作区领域模型：文件夹、任务、消息、产物、用量。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, TimestampMixin, utc_now


class Folder(Base, IdMixin, TimestampMixin):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="folder", cascade="save-update, merge"
    )


class Task(Base, IdMixin, TimestampMixin):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新任务")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    folder_id: Mapped[str | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 专家 / 技能 / 模型采用快照，保证配置删除或修改后历史任务可回放
    expert_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    skill_snapshots: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    folder: Mapped[Folder | None] = relationship(back_populates="tasks")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        passive_deletes=True,
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Artifact.created_at",
        passive_deletes=True,
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(Base, IdMixin):
    __tablename__ = "messages"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 有序过程块：think / plan / tool / artifact 等
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="done")
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False, index=True)

    task: Mapped[Task] = relationship(back_populates="messages")


class Artifact(Base, IdMixin):
    __tablename__ = "artifacts"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # md/docx/pptx/txt/...
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="file")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    absolute_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False, index=True)

    task: Mapped[Task] = relationship(back_populates="artifacts")


class UsageRecord(Base, IdMixin):
    __tablename__ = "usage_records"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    provider_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False, index=True)

    task: Mapped[Task] = relationship(back_populates="usage_records")
