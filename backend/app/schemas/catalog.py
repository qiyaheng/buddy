"""专家 / 技能目录接口契约。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Expert ----------


class ExpertBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    emoji: str = Field(default="🤖", max_length=8)
    color: str = Field(default="#4f7cff", max_length=20)
    category: str = Field(min_length=1, max_length=30)
    tagline: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=2000)
    system_prompt: str = Field(default="", max_length=8000)
    suggested_prompts: list[str] = Field(default_factory=list, max_length=3)


class ExpertCreate(ExpertBase):
    pass


class ExpertUpdate(BaseModel):
    # 全部可选；内置专家整体不可编辑
    name: str | None = Field(default=None, min_length=1, max_length=50)
    emoji: str | None = Field(default=None, max_length=8)
    color: str | None = Field(default=None, max_length=20)
    category: str | None = Field(default=None, min_length=1, max_length=30)
    tagline: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    system_prompt: str | None = Field(default=None, max_length=8000)
    suggested_prompts: list[str] | None = Field(default=None, max_length=3)


class ExpertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    emoji: str
    color: str
    category: str
    tagline: str
    description: str
    system_prompt: str
    suggested_prompts: list[str]
    is_builtin: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
