"""全局配置：数据目录、端口、密钥等。

数据目录解析优先级：
1. 环境变量 SMEBUDDY_DATA_DIR（Electron 主进程传入 userData，生产模式）；
2. 开发默认值：仓库根目录下 `.data/`。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _REPO_ROOT / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMEBUDDY_", extra="ignore")

    data_dir: Path = _DEFAULT_DATA_DIR
    port: int = 18790
    app_name: str = "SMEbuddy Clone"
    version: str = "0.1.0"
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db.sqlite3"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def secret_key_path(self) -> Path:
        return self.data_dir / ".secret_key"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        data_dir=Path(os.environ.get("SMEBUDDY_DATA_DIR", str(_DEFAULT_DATA_DIR))),
        port=int(os.environ.get("SMEBUDDY_PORT", "18790")),
        log_level=os.environ.get("SMEBUDDY_LOG_LEVEL", "INFO"),
    )
    settings.ensure_dirs()
    return settings


settings = get_settings()
