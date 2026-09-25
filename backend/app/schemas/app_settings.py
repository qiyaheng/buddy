"""应用设置（搜索源等）接口契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    search_provider: Literal["duckduckgo", "tavily"] = "duckduckgo"
    has_tavily_key: bool = False
    tavily_api_key_masked: str = ""


class AppSettingsUpdate(BaseModel):
    search_provider: Literal["duckduckgo", "tavily"] | None = None
    # None/空串 = 不修改；非空 = 更新
    tavily_api_key: str | None = None
