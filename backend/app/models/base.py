"""模型公共基类与工具。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )


class IdMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)


__all__ = ["Base", "IdMixin", "TimestampMixin", "utc_now", "new_id"]
