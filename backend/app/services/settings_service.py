"""应用设置服务（KV 存储；搜索源等）。敏感值加密落盘。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import NotFoundError
from ..models import AppSetting
from ..schemas.app_settings import AppSettingsOut, AppSettingsUpdate
from ..security import decrypt, encrypt, mask_secret

SEARCH_PROVIDER_KEY = "search_provider"
TAVILY_API_KEY_KEY = "tavily_api_key"

# 允许通过接口删除的 key 白名单
RESETTABLE_KEYS = {TAVILY_API_KEY_KEY}


@dataclass
class SearchConfig:
    provider: str  # duckduckgo / tavily
    tavily_api_key: str | None


def _get_row(db: Session, key: str) -> AppSetting | None:
    return db.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()


def _get_raw(db: Session, key: str) -> object | None:
    row = _get_row(db, key)
    return row.value if row else None


def _set_raw(db: Session, key: str, value: object) -> None:
    row = _get_row(db, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def get_settings(db: Session) -> AppSettingsOut:
    search_provider = str(_get_raw(db, SEARCH_PROVIDER_KEY) or "duckduckgo")
    tavily_token = _get_raw(db, TAVILY_API_KEY_KEY)
    tavily_key = decrypt(str(tavily_token)) if isinstance(tavily_token, str) and tavily_token else None
    return AppSettingsOut(
        search_provider=search_provider if search_provider in {"duckduckgo", "tavily"} else "duckduckgo",
        has_tavily_key=bool(tavily_key),
        tavily_api_key_masked=mask_secret(tavily_key),
    )


def update_settings(db: Session, data: AppSettingsUpdate) -> AppSettingsOut:
    if data.search_provider is not None:
        _set_raw(db, SEARCH_PROVIDER_KEY, data.search_provider)
    if data.tavily_api_key:  # 空串/None 表示不修改
        _set_raw(db, TAVILY_API_KEY_KEY, encrypt(data.tavily_api_key))
    db.commit()
    return get_settings(db)


def reset_setting(db: Session, key: str) -> None:
    if key not in RESETTABLE_KEYS:
        raise NotFoundError("该设置项不可删除")
    row = _get_row(db, key)
    if row is not None:
        db.delete(row)
        db.commit()


def get_search_config(db: Session) -> SearchConfig:
    """供搜索工具调用：返回解密后的明文配置。"""
    out = get_settings(db)
    token = _get_raw(db, TAVILY_API_KEY_KEY)
    key = decrypt(str(token)) if isinstance(token, str) and token else None
    return SearchConfig(provider=out.search_provider, tavily_api_key=key)
