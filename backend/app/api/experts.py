"""专家目录路由：列表/详情/自定义 CRUD/复制为自定义。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.catalog import ExpertCreate, ExpertOut, ExpertUpdate
from ..services import expert_service

router = APIRouter(prefix="/experts", tags=["experts"])


@router.get("", response_model=list[ExpertOut])
def list_experts(
    category: str | None = Query(default=None, description="分类精确筛选"),
    q: str | None = Query(default=None, description="按名称/一句话描述/详情搜索"),
    db: Session = Depends(get_db),
) -> list[ExpertOut]:
    return list(expert_service.list_experts(db, category=category, q=q))


@router.post("", response_model=ExpertOut, status_code=status.HTTP_201_CREATED)
def create_expert(data: ExpertCreate, db: Session = Depends(get_db)) -> ExpertOut:
    return expert_service.create_expert(db, data)


@router.get("/{expert_id}", response_model=ExpertOut)
def get_expert(expert_id: str, db: Session = Depends(get_db)) -> ExpertOut:
    return expert_service.get_expert(db, expert_id)


@router.patch("/{expert_id}", response_model=ExpertOut)
def update_expert(
    expert_id: str, data: ExpertUpdate, db: Session = Depends(get_db)
) -> ExpertOut:
    return expert_service.update_expert(db, expert_id, data)


@router.delete("/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expert(expert_id: str, db: Session = Depends(get_db)) -> None:
    expert_service.delete_expert(db, expert_id)


@router.post(
    "/{expert_id}/duplicate",
    response_model=ExpertOut,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_expert(expert_id: str, db: Session = Depends(get_db)) -> ExpertOut:
    return expert_service.duplicate_expert(db, expert_id)
