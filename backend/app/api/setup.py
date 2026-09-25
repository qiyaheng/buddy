"""初始化引导状态路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.provider import SetupStatusOut
from ..services import provider_service

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusOut)
def setup_status(db: Session = Depends(get_db)) -> SetupStatusOut:
    return provider_service.get_setup_status(db)
