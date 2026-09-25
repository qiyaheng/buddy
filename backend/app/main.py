"""FastAPI 应用入口（由 Electron sidecar 以 uvicorn 启动）。"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api.router import api_router
from .config import settings
from .db import init_db
from .errors import ApiError
from .logging_config import setup_logging
from .parent_watch import start_parent_watchdog

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="SMEbuddy Clone Sidecar", version=__version__)

# 仅允许本地渲染端访问（开发端口 6173，被占用时自动顺延，故放行本机任意端口）
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    logger.info("Sidecar starting: data_dir=%s port=%s", settings.data_dir, settings.port)
    init_db()
    start_parent_watchdog()


@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "请求参数校验失败",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "服务内部错误，请查看日志"},
    )


app.include_router(api_router)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "data_dir": str(settings.data_dir),
    }
