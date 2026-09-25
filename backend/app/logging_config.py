"""结构化日志配置：控制台 + 按日滚动文件。"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

from .config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_wb_configured", False):
        return

    root.setLevel(settings.log_level.upper())
    formatter = logging.Formatter(_LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = TimedRotatingFileHandler(
        settings.logs_dir / "backend.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # 降低三方库噪声
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("trafilatura").setLevel(logging.ERROR)

    root._wb_configured = True  # type: ignore[attr-defined]
