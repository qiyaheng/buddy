"""API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from . import app_settings, experts, folders, providers, runs, setup, tasks

api_router = APIRouter(prefix="/api")
api_router.include_router(setup.router)
api_router.include_router(providers.router)
api_router.include_router(app_settings.router)
api_router.include_router(folders.router)
api_router.include_router(tasks.router)
api_router.include_router(runs.router)
api_router.include_router(experts.router)
