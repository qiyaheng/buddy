"""Task 6：Agent 引擎 SSE 事件序列、取消、错误分类与过程持久化。

注意：所有 app.* 导入放在函数/fixture 内，避免在 conftest 设置
SMEBUDDY_DATA_DIR 之前提前实例化 config 单例。
"""

from __future__ import annotations

import json
import threading
import time

import pytest


# ---------- 辅助 ----------


def _create_task(client, title: str = "agent 测试任务") -> str:
    resp = client.post("/api/tasks", json={"title": title})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _collect_sse(client, task_id: str, content: str = "帮我做一次行业调研"):
    """同步消费完整 SSE 流，返回事件列表。"""
    events: list[dict] = []
    with client.stream(
        "POST", f"/api/tasks/{task_id}/runs", json={"content": content}
    ) as resp:
        assert resp.status_code == 200, resp.read().decode()
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def _type_indexes(events: list[dict]) -> dict[str, int]:
    return {
        e["type"]: i
        for i, e in enumerate(events)
        if e["type"] not in ("plan_update", "think_delta", "message_delta")
    }


@pytest.fixture
def fake_env(monkeypatch):
    monkeypatch.setenv("SMEBUDDY_FAKE_LLM", "1")
    monkeypatch.setenv("SMEBUDDY_FAKE_STEP", "0")
    # 保证错误注入不串测试
    monkeypatch.delenv("SMEBUDDY_FAKE_ERROR", raising=False)
    yield monkeypatch


# ---------- TR-6.1：完整事件序列 ----------


def test_full_run_event_sequence_and_persistence(client, fake_env):
    from app.config import settings

    task_id = _create_task(client)
    events = _collect_sse(client, task_id, "帮我调研一下 AI 办公赛道")

    types = [e["type"] for e in events]

    # 首事件为 run_started，携带两条消息 id
    assert types[0] == "run_started"
    assert events[0]["task_id"] == task_id
    assert events[0]["user_message_id"] != events[0]["assistant_message_id"]

    # 关键事件按序出现
    assert types.count("plan_start") == 1
    assert types.count("done") == 1
    assert {"tool_call", "tool_result", "artifact", "usage"}.issubset(set(types))
    first_tool_call = next(i for i, t in enumerate(types) if t == "tool_call")
    tool_result = types.index("tool_result")
    first_delta = types.index("message_delta")
    artifact = types.index("artifact")
    done = types.index("done")
    assert first_tool_call < tool_result < first_delta < artifact < done

    # 计划状态推进
    plan_updates = [e for e in events if e["type"] == "plan_update"]
    assert {"s1", "s2", "s3"}.issubset({e["step_id"] for e in plan_updates})
    final_steps = {
        e["step_id"]: e["status"]
        for e in plan_updates
    }
    assert all(v == "done" for v in final_steps.values())

    # 工具事件负载
    tc = events[first_tool_call]
    assert tc["name"] == "web_search"
    assert tc["status"] == "started"
    assert tc["input_summary"]
    tr = events[tool_result]
    assert tr["status"] == "finished"
    assert tr["elapsed_ms"] >= 0
    assert len(tr["sources"]) == 2

    # 正文由多个 delta 组成
    deltas = [e["delta"] for e in events if e["type"] == "message_delta"]
    assert len(deltas) >= 3
    assert "".join(deltas).startswith("# 任务简报")

    # usage 事件
    usage = next(e for e in events if e["type"] == "usage")
    assert usage["total_tokens"] == 530

    # 任务与消息落库状态
    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["status"] == "done"
    assert task["error_message"] is None

    msgs = client.get(f"/api/tasks/{task_id}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assistant = msgs[1]
    assert assistant["status"] == "done"
    assert assistant["content"].startswith("# 任务简报")
    block_types = [b["type"] for b in assistant["blocks"]]
    assert block_types == ["plan", "think", "tool", "artifact"]
    # 过程块最终内容完整
    assert assistant["blocks"][0]["steps"][-1]["status"] == "done"
    assert "拆解关键目标" in assistant["blocks"][1]["text"]
    assert assistant["blocks"][2]["name"] == "web_search"
    assert assistant["blocks"][3]["filename"] == "fake-report.md"

    # 产物入库 + 文件落盘
    artifact_event = events[artifact]
    assert artifact_event["format"] == "md"
    assert artifact_event["size_bytes"] > 0
    artifact_path = settings.artifacts_dir / task_id / "fake-report.md"
    assert artifact_path.exists()
    assert "# 任务简报" in artifact_path.read_text(encoding="utf-8")

    # 用量汇总
    summary = client.get(f"/api/tasks/{task_id}/usage").json()
    assert summary["total_tokens"] == 530
    assert summary["request_count"] == 1


# ---------- TR-6.1：中途停止，之后不再发起 LLM 请求 ----------


def test_stop_mid_run_halts_agent(client, fake_env, monkeypatch):
    from app.agent.state import registry

    monkeypatch.setenv("SMEBUDDY_FAKE_STEP", "0.1")
    task_id = _create_task(client)

    events: list[dict] = []

    def consume() -> None:
        # 注意：Starlette TestClient 在流结束后才一次性交付缓冲事件，
        # 但 registry 运行态跨线程实时可见，取消信号同样跨线程生效。
        with client.stream(
            "POST", f"/api/tasks/{task_id}/runs", json={"content": "长任务调研"}
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

    t = threading.Thread(target=consume)
    t.start()
    try:
        # 等待运行开始并越过唯一的 LLM 请求边界
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            control = registry.get(task_id)
            if control is not None and control.llm_requests >= 1:
                break
            time.sleep(0.02)
        control = registry.get(task_id)
        assert control is not None and control.llm_requests == 1

        stop_resp = client.post(f"/api/tasks/{task_id}/stop")
        assert stop_resp.status_code == 200
        assert stop_resp.json() == {"task_id": task_id, "stopping": True}
        t.join(timeout=5)
        assert not t.is_alive(), "SSE 流未在停止后结束"
    finally:
        t.join(timeout=1)

    types = [e["type"] for e in events]
    assert "done" not in types
    assert "artifact" not in types
    assert types[-1] == "stopped"
    # 停止发生在首次 LLM 请求之后，且没有再发起新请求
    assert events[-1]["llm_requests"] == 1

    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["status"] == "stopped"
    msgs = client.get(f"/api/tasks/{task_id}/messages").json()
    assert msgs[1]["status"] == "stopped"
    # 已产出的过程块保留
    assert [b["type"] for b in msgs[1]["blocks"]][:2] == ["plan", "think"]

    # 停止后可重新发起运行（运行态锁已释放）
    monkeypatch.setenv("SMEBUDDY_FAKE_STEP", "0")
    events2 = _collect_sse(client, task_id, "再来一轮")
    assert events2[-1]["type"] == "done"
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "done"


def test_concurrent_run_rejected(client, fake_env, monkeypatch):
    from app.agent.state import registry

    monkeypatch.setenv("SMEBUDDY_FAKE_STEP", "0.15")
    task_id = _create_task(client)

    def consume() -> None:
        with client.stream(
            "POST", f"/api/tasks/{task_id}/runs", json={"content": "第一轮"}
        ) as resp:
            resp.read()

    t = threading.Thread(target=consume)
    t.start()
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not registry.is_running(task_id):
            time.sleep(0.02)
        assert registry.is_running(task_id)

        conflict = client.post(
            f"/api/tasks/{task_id}/runs", json={"content": "并发的第二轮"}
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "conflict"
        client.post(f"/api/tasks/{task_id}/stop")
        t.join(timeout=5)
    finally:
        t.join(timeout=1)


# ---------- TR-6.2：上游错误分类 ----------


@pytest.mark.parametrize(
    ("fail_code", "hint"),
    [
        ("auth_failed", "API Key"),
        ("timeout", "超时"),
        ("network", "无法连接"),
    ],
)
def test_upstream_errors_emit_error_and_persist(client, fake_env, monkeypatch, fail_code, hint):
    monkeypatch.setenv("SMEBUDDY_FAKE_ERROR", fail_code)
    task_id = _create_task(client)

    events = _collect_sse(client, task_id, "触发错误的任务")
    types = [e["type"] for e in events]

    assert "done" not in types
    assert types[-1] == "error"
    err = events[-1]
    assert err["code"] == fail_code
    assert hint in err["message"]

    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["status"] == "error"
    assert fail_code in (task["error_message"] or "")

    msgs = client.get(f"/api/tasks/{task_id}/messages").json()
    assistant = msgs[1]
    assert assistant["status"] == "error"
    # 出错前的思考过程已增量落库并保留
    think_blocks = [b for b in assistant["blocks"] if b["type"] == "think"]
    assert think_blocks and think_blocks[0]["text"].strip()
    plan_blocks = [b for b in assistant["blocks"] if b["type"] == "plan"]
    assert plan_blocks[0]["steps"][0]["status"] == "done"
    # 工具尚未执行
    assert not [b for b in assistant["blocks"] if b["type"] == "tool"]


# ---------- TR-6.3：重启后可读到持久化过程块 ----------


def test_process_blocks_visible_after_restart(client, fake_env):
    from app.db import SessionLocal
    from app.models.workspace import Artifact, Message, Task, UsageRecord

    task_id = _create_task(client)
    events = _collect_sse(client, task_id, "持久化验证任务")
    assistant_message_id = events[0]["assistant_message_id"]

    # 模拟进程重启：使用全新 Session 直接打开同一个 SQLite 文件
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        assert task.status == "done"
        message = db.get(Message, assistant_message_id)
        assert message.status == "done"
        assert "行动建议" in message.content
        block_types = [b["type"] for b in message.blocks]
        assert block_types == ["plan", "think", "tool", "artifact"]
        assert message.blocks[2]["sources"][0]["url"].startswith("https://")
        artifact = (
            db.query(Artifact).filter(Artifact.task_id == task_id).one()
        )
        assert artifact.filename == "fake-report.md"
        usage = (
            db.query(UsageRecord).filter(UsageRecord.task_id == task_id).one()
        )
        assert usage.total_tokens == 530
    finally:
        db.close()


# ---------- 预校验 ----------


def test_run_without_model_returns_400(client, monkeypatch):
    monkeypatch.delenv("SMEBUDDY_FAKE_LLM", raising=False)
    task_id = _create_task(client)
    resp = client.post(f"/api/tasks/{task_id}/runs", json={"content": "你好"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "bad_request"
    # 未产生消息
    assert client.get(f"/api/tasks/{task_id}/messages").json() == []
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "idle"


def test_run_unknown_task_returns_404(client, fake_env):
    resp = client.post("/api/tasks/nope/runs", json={"content": "你好"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


def test_run_blank_content_returns_400(client, fake_env):
    task_id = _create_task(client)
    resp = client.post(f"/api/tasks/{task_id}/runs", json={"content": "   "})
    # Pydantic min_length 拦空白字符 -> 422；service 层 strip 兜底 -> 400（此处内容全空格可过 Pydantic）
    assert resp.status_code in (400, 422)


def test_stop_idempotent_when_idle(client, fake_env):
    task_id = _create_task(client)
    resp = client.post(f"/api/tasks/{task_id}/stop")
    assert resp.status_code == 200
    assert resp.json() == {"task_id": task_id, "stopping": False}
