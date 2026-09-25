"""文件夹 / 任务 / 消息业务逻辑。"""

from __future__ import annotations

import shutil
from typing import Any

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..errors import BadRequestError, ConflictError, NotFoundError
from ..models.app_config import ModelConfig
from ..models.catalog import Expert, Skill
from ..models.workspace import Folder, Message, Task, UsageRecord
from ..schemas.workspace import TaskCreate, TaskUpdate

UNGROUPED = "none"

VALID_TASK_STATUS = {"idle", "running", "stopped", "error", "done"}


# ---------- Folder ----------


def list_folders(db: Session) -> list[Folder]:
    stmt = select(Folder).order_by(Folder.sort_order.asc(), Folder.created_at.asc())
    return list(db.scalars(stmt))


def create_folder(db: Session, name: str) -> Folder:
    name = name.strip()
    if not name:
        raise BadRequestError("文件夹名称不能为空")
    exists_row = db.scalar(select(Folder).where(Folder.name == name))
    if exists_row:
        raise ConflictError("同名文件夹已存在")
    max_order = db.scalar(select(func.coalesce(func.max(Folder.sort_order), 0))) or 0
    folder = Folder(name=name, sort_order=max_order + 1)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def _get_folder(db: Session, folder_id: str) -> Folder:
    folder = db.get(Folder, folder_id)
    if folder is None:
        raise NotFoundError("文件夹不存在")
    return folder


def rename_folder(db: Session, folder_id: str, name: str) -> Folder:
    name = name.strip()
    if not name:
        raise BadRequestError("文件夹名称不能为空")
    folder = _get_folder(db, folder_id)
    dup = db.scalar(select(Folder).where(Folder.name == name, Folder.id != folder_id))
    if dup:
        raise ConflictError("同名文件夹已存在")
    folder.name = name
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(db: Session, folder_id: str) -> None:
    folder = _get_folder(db, folder_id)
    db.delete(folder)
    db.commit()


# ---------- Task ----------


def _expert_snapshot(expert: Expert) -> dict[str, Any]:
    return {
        "id": expert.id,
        "name": expert.name,
        "emoji": expert.emoji,
        "color": expert.color,
        "system_prompt": expert.system_prompt,
    }


def _skill_snapshot(skill: Skill) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "icon": skill.icon,
        "prompt_template": skill.prompt_template,
        "tools": list(skill.tools or []),
    }


def _resolve_model(db: Session, model_config_id: str | None) -> ModelConfig | None:
    if model_config_id:
        model = db.get(ModelConfig, model_config_id)
        if model is None:
            raise NotFoundError("指定的模型不存在")
        return model
    return db.scalar(select(ModelConfig).where(ModelConfig.is_default.is_(True)))


def create_task(db: Session, data: TaskCreate) -> Task:
    if data.folder_id:
        _get_folder(db, data.folder_id)

    expert_snapshot = None
    if data.expert_id:
        expert = db.get(Expert, data.expert_id)
        if expert is None:
            raise NotFoundError("指定的专家不存在")
        expert_snapshot = _expert_snapshot(expert)

    skill_snapshots: list[dict[str, Any]] = []
    for skill_id in data.skill_ids:
        skill = db.get(Skill, skill_id)
        if skill is None:
            raise NotFoundError(f"指定的技能不存在: {skill_id}")
        skill_snapshots.append(_skill_snapshot(skill))

    model = _resolve_model(db, data.model_config_id)

    task = Task(
        title=(data.title.strip() if data.title and data.title.strip() else "新任务"),
        folder_id=data.folder_id or None,
        status="idle",
        expert_snapshot=expert_snapshot,
        skill_snapshots=skill_snapshots,
        model_id=model.id if model else None,
        model_snapshot=(
            {"id": model.id, "model_id": model.model_id, "display_name": model.display_name}
            if model
            else None
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError("任务不存在")
    return task


def list_tasks(
    db: Session, *, folder_id: str | None = None, q: str | None = None
) -> list[Task]:
    stmt = select(Task)

    if folder_id is not None:
        if folder_id == UNGROUPED:
            stmt = stmt.where(Task.folder_id.is_(None))
        else:
            # 校验文件夹存在，避免静默返回空列表
            _get_folder(db, folder_id)
            stmt = stmt.where(Task.folder_id == folder_id)

    keyword = (q or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        message_match = exists().where(
            Message.task_id == Task.id, Message.content.ilike(pattern)
        )
        stmt = stmt.where(or_(Task.title.ilike(pattern), message_match))

    last_touch = func.coalesce(Task.last_message_at, Task.created_at)
    stmt = stmt.order_by(
        case((Task.last_message_at.is_(None), 1), else_=0).asc(),
        last_touch.desc(),
    )
    return list(db.scalars(stmt))


def update_task(db: Session, task_id: str, data: TaskUpdate, *, applied: set[str]) -> Task:
    task = get_task(db, task_id)

    if "title" in applied and data.title is not None:
        title = data.title.strip()
        if not title:
            raise BadRequestError("任务标题不能为空")
        task.title = title

    if "folder_id" in applied:
        if data.folder_id:
            _get_folder(db, data.folder_id)
            task.folder_id = data.folder_id
        else:
            task.folder_id = None

    if "status" in applied and data.status is not None:
        if data.status not in VALID_TASK_STATUS:
            raise BadRequestError(f"非法任务状态: {data.status}")
        task.status = data.status

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> None:
    task = get_task(db, task_id)
    # best-effort 删除该任务的产物文件目录（artifacts/<task_id>/）
    task_artifact_dir = settings.artifacts_dir / task.id
    shutil.rmtree(task_artifact_dir, ignore_errors=True)
    db.delete(task)
    db.commit()


# ---------- Message ----------


def add_message(
    db: Session,
    task: Task,
    *,
    role: str,
    content: str = "",
    blocks: list[dict[str, Any]] | None = None,
    status: str = "done",
    error_text: str | None = None,
    commit: bool = True,
) -> Message:
    message = Message(
        task_id=task.id,
        role=role,
        content=content,
        blocks=blocks or [],
        status=status,
        error_text=error_text,
    )
    db.add(message)
    task.last_message_at = message.created_at
    if commit:
        db.commit()
        db.refresh(message)
    return message


def list_messages(db: Session, task_id: str) -> list[Message]:
    get_task(db, task_id)
    # 一轮 run 内 user/assistant 两条消息可能在同一微秒创建，
    # 同刻时按 user 优先排序，避免随机 uuid 打乱问答顺序。
    role_order = case((Message.role == "user", 0), else_=1)
    stmt = (
        select(Message)
        .where(Message.task_id == task_id)
        .order_by(Message.created_at.asc(), role_order.asc(), Message.id.asc())
    )
    return list(db.scalars(stmt))


# ---------- Usage ----------


def usage_summary(db: Session, task_id: str) -> dict[str, int]:
    get_task(db, task_id)
    row = db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.request_count), 0),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
        ).where(UsageRecord.task_id == task_id)
    ).one()
    return {
        "request_count": int(row[0]),
        "prompt_tokens": int(row[1]),
        "completion_tokens": int(row[2]),
        "total_tokens": int(row[3]),
    }
