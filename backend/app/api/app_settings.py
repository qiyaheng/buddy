"""应用设置路由（搜索源等）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.app_settings import AppSettingsOut, AppSettingsUpdate
from ..services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
def get_settings(db: Session = Depends(get_db)) -> AppSettingsOut:
    return settings_service.get_settings(db)


@router.put("", response_model=AppSettingsOut)
def update_settings(
    data: AppSettingsUpdate, db: Session = Depends(get_db)
) -> AppSettingsOut:
    return settings_service.update_settings(db, data)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def reset_setting(key: str, db: Session = Depends(get_db)) -> None:
    settings_service.reset_setting(db, key)
