"""幂等种子数据装配。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..db import session_scope
from . import experts, skills

logger = logging.getLogger(__name__)


def run_seeders() -> None:
    """在独立事务中执行全部种子（每个 seeder 内部幂等）。"""
    with session_scope() as db:  # type: Session
        expert_added = experts.seed(db)
        skill_added = skills.seed(db)
    if expert_added or skill_added:
        logger.info("Seeded %s experts, %s skills", expert_added, skill_added)
