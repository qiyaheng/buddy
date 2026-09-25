"""Task 5：文件夹 / 任务 / 消息 / 用量 REST API 验收测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.config import settings
from app.db import session_scope
from app.models.catalog import Expert, Skill
from app.models.workspace import Artifact, Message, Task, UsageRecord
from app.services import workspace_service


@pytest.fixture()
def expert_id() -> str:
    with session_scope() as db:
        expert = db.query(Expert).order_by(Expert.sort_order).first()
        return expert.id


@pytest.fixture()
def skill_id() -> str:
    with session_scope() as db:
        skill = db.query(Skill).order_by(Skill.sort_order).first()
        return skill.id


# ---------- Folder ----------


def test_folder_crud_and_duplicate(client):
    # create
    res = client.post("/api/folders", json={"name": "项目甲"})
    assert res.status_code == 201
    folder = res.json()
    assert folder["name"] == "项目甲"

    # duplicate → 409
    dup = client.post("/api/folders", json={"name": "项目甲"})
    assert dup.status_code == 409
    assert dup.json()["code"] == "conflict"

    # rename
    res = client.patch(f"/api/folders/{folder['id']}", json={"name": "项目甲-改"})
    assert res.status_code == 200
    assert res.json()["name"] == "项目甲-改"

    # 纯空白名称 → service 层 400
    bad = client.post("/api/folders", json={"name": "   "})
    assert bad.status_code == 400
    assert bad.json()["code"] == "bad_request"

    # list
    folders = client.get("/api/folders").json()
    assert any(f["id"] == folder["id"] for f in folders)


def test_delete_folder_moves_tasks_to_ungrouped(client, expert_id):
    folder = client.post("/api/folders", json={"name": "待删文件夹"}).json()
    task = client.post(
        "/api/tasks", json={"title": "文件夹内任务", "folder_id": folder["id"], "expert_id": expert_id}
    ).json()
    assert task["folder_id"] == folder["id"]

    res = client.delete(f"/api/folders/{folder['id']}")
    assert res.status_code == 204

    moved = client.get(f"/api/tasks/{task['id']}").json()
    assert moved["folder_id"] is None
    # 快照保留
    assert moved["expert_snapshot"]["id"] == expert_id


def test_folder_not_found(client):
    assert client.patch("/api/folders/nope", json={"name": "x"}).status_code == 404
    assert client.delete("/api/folders/nope").status_code == 404


# ---------- Task ----------


def test_create_task_defaults_and_snapshot(client, expert_id, skill_id):
    res = client.post(
        "/api/tasks",
        json={"expert_id": expert_id, "skill_ids": [skill_id]},
    )
    assert res.status_code == 201
    task = res.json()
    assert task["title"] == "新任务"
    assert task["status"] == "idle"
    assert task["folder_id"] is None
    assert task["expert_snapshot"] is not None
    assert task["expert_snapshot"]["id"] == expert_id
    assert len(task["skill_snapshots"]) == 1
    assert task["skill_snapshots"][0]["id"] == skill_id
    # 未配置任何模型时快照为空，但任务仍可创建
    assert task["model_snapshot"] is None
    assert task["model_id"] is None


def test_create_task_with_unknown_refs_404(client):
    assert client.post("/api/tasks", json={"folder_id": "nope"}).status_code == 404
    assert client.post("/api/tasks", json={"expert_id": "nope"}).status_code == 404
    assert client.post("/api/tasks", json={"skill_ids": ["nope"]}).status_code == 404
    assert client.post("/api/tasks", json={"model_config_id": "nope"}).status_code == 404


def test_task_move_and_status(client):
    folder_a = client.post("/api/folders", json={"name": "A 组"}).json()
    task = client.post("/api/tasks", json={"title": "移动测试"}).json()

    moved = client.patch(f"/api/tasks/{task['id']}", json={"folder_id": folder_a["id"]})
    assert moved.status_code == 200
    assert moved.json()["folder_id"] == folder_a["id"]

    ungrouped = client.patch(f"/api/tasks/{task['id']}", json={"folder_id": None})
    assert ungrouped.status_code == 200
    assert ungrouped.json()["folder_id"] is None

    running = client.patch(f"/api/tasks/{task['id']}", json={"status": "running"})
    assert running.json()["status"] == "running"

    bad = client.patch(f"/api/tasks/{task['id']}", json={"status": "weird"})
    assert bad.status_code == 422

    rename = client.patch(f"/api/tasks/{task['id']}", json={"title": "新的标题"})
    assert rename.json()["title"] == "新的标题"


def test_task_list_filter_and_search(client, expert_id):
    # 会话级共享数据库：关键词加唯一后缀，避免与其他测试模块的文案碰撞
    marker = uuid4().hex[:8]
    title_kw = f"复盘{marker}"
    content_kw = f"竞品定价{marker}"

    folder = client.post("/api/folders", json={"name": f"搜索组{marker}"}).json()
    t1 = client.post(
        "/api/tasks", json={"title": f"季度{title_kw}报告", "folder_id": folder["id"]}
    ).json()
    t2 = client.post("/api/tasks", json={"title": f"招聘面试纪要{marker}"}).json()

    # 给 t2 追加一条含关键词的消息
    with session_scope() as db:
        task = db.get(Task, t2["id"])
        workspace_service.add_message(
            db, task, role="user", content=f"帮我分析{content_kw}策略"
        )

    # 标题搜索
    by_title = client.get("/api/tasks", params={"q": title_kw}).json()
    assert {t["id"] for t in by_title} == {t1["id"]}

    # 消息内容搜索
    by_content = client.get("/api/tasks", params={"q": content_kw}).json()
    assert {t["id"] for t in by_content} == {t2["id"]}

    # 文件夹过滤
    in_folder = client.get("/api/tasks", params={"folder_id": folder["id"]}).json()
    assert {t["id"] for t in in_folder} == {t1["id"]}

    ungrouped = client.get("/api/tasks", params={"folder_id": "none"}).json()
    assert t2["id"] in {t["id"] for t in ungrouped}
    assert t1["id"] not in {t["id"] for t in ungrouped}


# ---------- Message & 级联 ----------


def test_messages_ordering_and_usage(client):
    task = client.post("/api/tasks", json={"title": "消息顺序"}).json()

    with session_scope() as db:
        task_obj = db.get(Task, task["id"])
        m1 = workspace_service.add_message(db, task_obj, role="user", content="第一条")
        m2 = workspace_service.add_message(
            db,
            task_obj,
            role="assistant",
            content="第二条",
            blocks=[{"type": "think", "text": "思考中"}],
            status="done",
        )
        db.add(
            UsageRecord(
                task_id=task["id"],
                message_id=m2.id,
                model="gpt-4o-mini",
                request_count=1,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            )
        )
        db.add(
            UsageRecord(
                task_id=task["id"],
                message_id=m2.id,
                model="gpt-4o-mini",
                request_count=1,
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30,
            )
        )
        db.commit()

    messages = client.get(f"/api/tasks/{task['id']}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["blocks"][0]["type"] == "think"

    usage = client.get(f"/api/tasks/{task['id']}/usage").json()
    assert usage == {
        "request_count": 2,
        "prompt_tokens": 120,
        "completion_tokens": 60,
        "total_tokens": 180,
    }


def test_delete_task_cascades_records_and_files(client):
    task = client.post("/api/tasks", json={"title": "将被删除"}).json()

    with session_scope() as db:
        task_obj = db.get(Task, task["id"])
        workspace_service.add_message(db, task_obj, role="user", content="再见")
        db.add(
            Artifact(
                task_id=task["id"],
                filename="report.md",
                format="md",
                kind="document",
                size_bytes=12,
                absolute_path=str(settings.artifacts_dir / task["id"] / "report.md"),
            )
        )
        db.add(
            UsageRecord(
                task_id=task["id"], request_count=1, prompt_tokens=1, completion_tokens=1, total_tokens=2
            )
        )
        db.commit()

    # 模拟产物落盘
    task_dir = settings.artifacts_dir / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "report.md").write_text("# report", encoding="utf-8")

    res = client.delete(f"/api/tasks/{task['id']}")
    assert res.status_code == 204

    assert client.get(f"/api/tasks/{task['id']}").status_code == 404
    assert client.get(f"/api/tasks/{task['id']}/messages").status_code == 404

    # 数据库记录级联清除
    with session_scope() as db:
        assert db.query(Message).filter(Message.task_id == task["id"]).count() == 0
        assert db.query(Artifact).filter(Artifact.task_id == task["id"]).count() == 0
        assert db.query(UsageRecord).filter(UsageRecord.task_id == task["id"]).count() == 0

    # 磁盘目录一并清除
    assert not task_dir.exists()


def test_snapshot_survives_catalog_deletion(client):
    # 自建临时专家/技能，避免删除种子数据影响其他用例
    with session_scope() as db:
        expert = Expert(
            name="临时专家",
            emoji="🧪",
            color="#000000",
            category="test",
            system_prompt="snapshot me",
            sort_order=999,
        )
        skill = Skill(
            name="临时技能",
            icon="🧷",
            prompt_template="do x",
            kind="custom",
            sort_order=999,
        )
        db.add_all([expert, skill])
        db.commit()
        expert_id, skill_id = expert.id, skill.id

    task = client.post(
        "/api/tasks", json={"expert_id": expert_id, "skill_ids": [skill_id]}
    ).json()

    with session_scope() as db:
        db.query(Skill).filter(Skill.id == skill_id).delete()
        db.query(Expert).filter(Expert.id == expert_id).delete()
        db.commit()

    detail = client.get(f"/api/tasks/{task['id']}").json()
    assert detail["expert_snapshot"]["id"] == expert_id
    assert detail["expert_snapshot"]["system_prompt"] == "snapshot me"
    assert detail["skill_snapshots"][0]["id"] == skill_id
