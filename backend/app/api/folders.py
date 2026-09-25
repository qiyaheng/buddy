"""文件夹路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.workspace import FolderCreate, FolderOut, FolderUpdate
from ..services import workspace_service

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderOut])
def list_folders(db: Session = Depends(get_db)) -> list[FolderOut]:
    return list(workspace_service.list_folders(db))


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(data: FolderCreate, db: Session = Depends(get_db)) -> FolderOut:
    return workspace_service.create_folder(db, data.name)


@router.patch("/{folder_id}", response_model=FolderOut)
def rename_folder(
    folder_id: str, data: FolderUpdate, db: Session = Depends(get_db)
) -> FolderOut:
    return workspace_service.rename_folder(db, folder_id, data.name)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: str, db: Session = Depends(get_db)) -> None:
    workspace_service.delete_folder(db, folder_id)
