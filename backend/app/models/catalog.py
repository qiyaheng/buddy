"""专家与技能目录模型。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, TimestampMixin


class Expert(Base, IdMixin, TimestampMixin):
    __tablename__ = "experts"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    emoji: Mapped[str] = mapped_column(String(8), nullable=False, default="🤖")
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#4f7cff")
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    tagline: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_prompts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)


class Skill(Base, IdMixin, TimestampMixin):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[str] = mapped_column(String(8), nullable=False, default="🧩")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # 技能绑定的工具白名单（空表示不额外注入工具说明）
    tools: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
