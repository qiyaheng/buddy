"""任务 / 消息 / 用量路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.workspace import (
    MessageOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    UsageSummaryOut,
)
from ..services import workspace_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    folder_id: str | None = Query(default=None, description="传 none 表示未分组"),
    q: str | None = Query(default=None, description="按标题与消息内容搜索"),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    return list(workspace_service.list_tasks(db, folder_id=folder_id, q=q))


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    return workspace_service.create_task(db, data)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskOut:
    return workspace_service.get_task(db, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str, data: TaskUpdate, db: Session = Depends(get_db)
) -> TaskOut:
    # exclude_unset 区分「未传」与「显式 null」（folder_id 移动到未分组）
    applied = set(data.model_dump(exclude_unset=True).keys())
    return workspace_service.update_task(db, task_id, data, applied=applied)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)) -> None:
    workspace_service.delete_task(db, task_id)


@router.get("/{task_id}/messages", response_model=list[MessageOut])
def list_messages(task_id: str, db: Session = Depends(get_db)) -> list[MessageOut]:
    return list(workspace_service.list_messages(db, task_id))


@router.get("/{task_id}/usage", response_model=UsageSummaryOut)
def usage_summary(task_id: str, db: Session = Depends(get_db)) -> UsageSummaryOut:
    return UsageSummaryOut(**workspace_service.usage_summary(db, task_id))
