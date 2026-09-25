"""pytest 公共夹具：每个测试进程使用独立临时数据目录 + 全新 SQLite + 种子数据。"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

import pytest

# 确保 `backend/` 在 sys.path 上（兼容从仓库根目录运行 `pytest backend/tests`）
_BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# 必须在导入任何 app.* 模块之前确定数据目录：
# 测试模块可能在顶层导入 app.config，而 settings 是模块级单例，
# 放到 session fixture 里设置会晚于收集期导入，导致串到开发库 .data。
_TEST_DATA_DIR = pathlib.Path(tempfile.mkdtemp(prefix="wb-pytest-"))
os.environ["SMEBUDDY_DATA_DIR"] = str(_TEST_DATA_DIR)
os.environ.setdefault("SMEBUDDY_FAKE_LLM", "0")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.db import init_db
    from app.main import app
    from app.seed import run_seeders

    init_db()
    run_seeders()

    with TestClient(app) as test_client:
        yield test_client
