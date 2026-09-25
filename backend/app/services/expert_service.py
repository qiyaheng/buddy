"""专家目录业务逻辑：列表筛选、自定义 CRUD、内置保护与复制。"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..errors import ConflictError, NotFoundError
from ..models.catalog import Expert
from ..schemas.catalog import ExpertCreate, ExpertUpdate

# 自定义专家排序起点（内置种子 0..N，自定义统一沉到其后并按创建时间排）
_CUSTOM_SORT_BASE = 1000


def get_expert(db: Session, expert_id: str) -> Expert:
    expert = db.get(Expert, expert_id)
    if expert is None:
        raise NotFoundError("专家不存在")
    return expert


def list_experts(
    db: Session, *, category: str | None = None, q: str | None = None
) -> list[Expert]:
    stmt = select(Expert)
    if category:
        stmt = stmt.where(Expert.category == category.strip())
    keyword = (q or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Expert.name.ilike(pattern),
                Expert.tagline.ilike(pattern),
                Expert.description.ilike(pattern),
            )
        )
    rows = list(db.scalars(stmt))
    # 内置优先（按 sort_order），自定义按创建时间
    builtin = sorted((e for e in rows if e.is_builtin), key=lambda e: e.sort_order)
    custom = sorted(
        (e for e in rows if not e.is_builtin), key=lambda e: e.created_at
    )
    return builtin + custom


def create_expert(db: Session, data: ExpertCreate) -> Expert:
    name = data.name.strip()
    category = data.category.strip()
    _ensure_name_unique(db, name)
    expert = Expert(
        name=name,
        emoji=data.emoji.strip() or "🤖",
        color=(data.color.strip() or "#4f7cff"),
        category=category,
        tagline=data.tagline.strip(),
        description=data.description.strip(),
        system_prompt=data.system_prompt.strip(),
        suggested_prompts=_clean_prompts(data.suggested_prompts),
        is_builtin=False,
        sort_order=_CUSTOM_SORT_BASE,
    )
    db.add(expert)
    db.commit()
    db.refresh(expert)
    return expert


def update_expert(db: Session, expert_id: str, data: ExpertUpdate) -> Expert:
    expert = get_expert(db, expert_id)
    if expert.is_builtin:
        raise ConflictError("内置专家不可编辑，可复制为自定义专家后再修改")

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"] is not None:
        name = payload["name"].strip()
        _ensure_name_unique(db, name, exclude_id=expert.id)
        expert.name = name
    if "emoji" in payload and payload["emoji"] is not None:
        expert.emoji = payload["emoji"].strip() or "🤖"
    if "color" in payload and payload["color"] is not None:
        expert.color = payload["color"].strip() or "#4f7cff"
    if "category" in payload and payload["category"] is not None:
        expert.category = payload["category"].strip()
    if "tagline" in payload and payload["tagline"] is not None:
        expert.tagline = payload["tagline"].strip()
    if "description" in payload and payload["description"] is not None:
        expert.description = payload["description"].strip()
    if "system_prompt" in payload and payload["system_prompt"] is not None:
        expert.system_prompt = payload["system_prompt"].strip()
    if "suggested_prompts" in payload and payload["suggested_prompts"] is not None:
        expert.suggested_prompts = _clean_prompts(payload["suggested_prompts"])

    db.commit()
    db.refresh(expert)
    return expert


def delete_expert(db: Session, expert_id: str) -> None:
    expert = get_expert(db, expert_id)
    if expert.is_builtin:
        raise ConflictError("内置专家不可删除，可复制为自定义专家后再调整")
    db.delete(expert)
    db.commit()


def duplicate_expert(db: Session, expert_id: str) -> Expert:
    source = get_expert(db, expert_id)
    new_name = _unique_copy_name(db, source.name)
    expert = Expert(
        name=new_name,
        emoji=source.emoji,
        color=source.color,
        category=source.category,
        tagline=source.tagline,
        description=source.description,
        system_prompt=source.system_prompt,
        suggested_prompts=list(source.suggested_prompts or []),
        is_builtin=False,
        sort_order=_CUSTOM_SORT_BASE,
    )
    db.add(expert)
    db.commit()
    db.refresh(expert)
    return expert


# ---------- helpers ----------


def _clean_prompts(prompts: list[str] | None) -> list[str]:
    cleaned = [p.strip() for p in (prompts or []) if p and p.strip()]
    return cleaned[:3]


def _ensure_name_unique(db: Session, name: str, *, exclude_id: str | None = None) -> None:
    stmt = select(Expert.id).where(Expert.name == name)
    if exclude_id:
        stmt = stmt.where(Expert.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError("已存在同名专家")


def _unique_copy_name(db: Session, source_name: str) -> str:
    base = f"{source_name} 副本"
    candidate = base
    index = 2
    existing = set(db.scalars(select(Expert.name)).all())
    while candidate in existing:
        candidate = f"{base} {index}"
        index += 1
    return candidate

