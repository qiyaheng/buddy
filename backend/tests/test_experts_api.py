"""Task 9：专家广场 API 验收（TR-9.1）。"""

from __future__ import annotations

import pytest

from app.agent.runner import prepare_run
from app.agent.prompts import BASE_SYSTEM_PROMPT
from app.seed.experts import BUILTIN_EXPERTS


def _expert_payload(**overrides) -> dict:
    payload = {
        "name": "自定义效率教练",
        "emoji": "⚡",
        "color": "#12b886",
        "category": "效率工具",
        "tagline": "时间管理与专注力训练",
        "description": "帮助知识工作者建立可执行的日程与复盘体系。",
        "system_prompt": "你是一名严谨的效率教练，所有建议必须给出可执行的当日动作。",
        "suggested_prompts": ["帮我安排明天的深度工作时间表", "设计一个周复盘模板"],
    }
    payload.update(overrides)
    return payload


# ---------- 种子与查询 ----------


def test_builtin_experts_seeded(client):
    experts = client.get("/api/experts").json()
    builtin = [e for e in experts if e["is_builtin"]]
    assert len(builtin) >= 12
    assert len(builtin) == len(BUILTIN_EXPERTS)

    required = {
        "产品经理",
        "软件工程师",
        "测试 QA",
        "UI/UX 设计师",
        "运营专家",
        "市场营销",
        "数据分析师",
        "财务顾问",
        "法务顾问",
        "文案写作",
        "行业研究员",
        "PPT 汇报专家",
    }
    names = {e["name"] for e in builtin}
    assert required <= names

    for e in builtin:
        assert e["emoji"]
        assert e["color"].startswith("#")
        assert e["category"]
        assert e["tagline"]
        assert len(e["system_prompt"]) >= 30
        assert 2 <= len(e["suggested_prompts"]) <= 3

    # 内置排在自定义之前
    flags = [e["is_builtin"] for e in experts]
    assert flags == sorted(flags, reverse=True)


def test_category_filter_and_search(client):
    data_analyst = next(
        e for e in client.get("/api/experts").json() if e["name"] == "数据分析师"
    )

    by_cat = client.get(f"/api/experts?category={data_analyst['category']}").json()
    assert by_cat, "分类筛选应返回结果"
    assert all(e["category"] == data_analyst["category"] for e in by_cat)
    assert any(e["name"] == "数据分析师" for e in by_cat)

    # 按名称搜索
    by_name = client.get("/api/experts?q=法务").json()
    assert [e["name"] for e in by_name] == ["法务顾问"]

    # 按描述内容搜索
    by_desc = client.get("/api/experts?q=合同审查").json()
    assert any(e["name"] == "法务顾问" for e in by_desc)

    # 无匹配
    assert client.get("/api/experts?q=不存在的角色xyz").json() == []


# ---------- 自定义 CRUD ----------


def test_custom_expert_crud(client):
    # create
    res = client.post("/api/experts", json=_expert_payload())
    assert res.status_code == 201
    expert = res.json()
    assert expert["is_builtin"] is False
    assert expert["id"]

    # 重名 → 409
    dup = client.post("/api/experts", json=_expert_payload())
    assert dup.status_code == 409
    assert dup.json()["code"] == "conflict"

    # update
    res = client.patch(
        f"/api/experts/{expert['id']}",
        json={"tagline": "新版一句话描述", "suggested_prompts": ["只保留一个问题"]},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["tagline"] == "新版一句话描述"
    assert updated["suggested_prompts"] == ["只保留一个问题"]
    # 未传字段保持
    assert updated["system_prompt"] == expert["system_prompt"]

    # delete
    assert client.delete(f"/api/experts/{expert['id']}").status_code == 204
    assert client.get(f"/api/experts/{expert['id']}").status_code == 404


def test_validation(client):
    # 缺名称
    res = client.post("/api/experts", json=_expert_payload(name=""))
    assert res.status_code == 422
    # 推荐问题超过 3 个
    res = client.post(
        "/api/experts",
        json=_expert_payload(suggested_prompts=["a", "b", "c", "d"]),
    )
    assert res.status_code == 422


# ---------- 内置保护与复制 ----------


def test_builtin_protected(client):
    expert = client.get("/api/experts?q=产品经理").json()[0]
    assert expert["is_builtin"]

    assert client.patch(f"/api/experts/{expert['id']}", json={"name": "x"}).status_code == 409
    assert client.delete(f"/api/experts/{expert['id']}").status_code == 409


def test_duplicate_builtin_then_edit(client):
    source = client.get("/api/experts?q=产品经理").json()[0]

    res = client.post(f"/api/experts/{source['id']}/duplicate")
    assert res.status_code == 201
    clone = res.json()
    assert clone["is_builtin"] is False
    assert clone["name"] == "产品经理 副本"
    assert clone["system_prompt"] == source["system_prompt"]
    assert clone["suggested_prompts"] == source["suggested_prompts"]
    assert clone["emoji"] == source["emoji"]

    # 连续复制不改名：自动避让重名
    second = client.post(f"/api/experts/{source['id']}/duplicate").json()
    assert second["name"] == "产品经理 副本 2"

    # 副本可改可删
    patched = client.patch(
        f"/api/experts/{clone['id']}", json={"name": "B 端产品总监"}
    ).json()
    assert patched["name"] == "B 端产品总监"

    assert client.delete(f"/api/experts/{clone['id']}").status_code == 204
    assert client.delete(f"/api/experts/{second['id']}").status_code == 204


# ---------- TR-9.1：专家 system_prompt 进入首个后端请求 ----------


def test_expert_system_prompt_injected_to_run(client, monkeypatch):
    expert = client.get("/api/experts?q=软件工程师").json()[0]

    task = client.post(
        "/api/tasks", json={"title": "专家任务", "expert_id": expert["id"]}
    ).json()
    assert task["expert_snapshot"]["id"] == expert["id"]

    # prepare_run 是首个后端 LLM 请求的组装点（fake 模式跳过模型可用性校验）
    monkeypatch.setenv("SMEBUDDY_FAKE_LLM", "1")
    prepared = prepare_run(task["id"], "帮我写个排序算法", None)

    assert expert["system_prompt"].strip() in prepared.system_prompt
    assert BASE_SYSTEM_PROMPT in prepared.system_prompt
    assert prepared.history == []
    assert prepared.user_message_id and prepared.assistant_message_id


def test_task_without_expert_uses_base_prompt(client, monkeypatch):
    task = client.post("/api/tasks", json={"title": "普通任务"}).json()
    monkeypatch.setenv("SMEBUDDY_FAKE_LLM", "1")
    prepared = prepare_run(task["id"], "你好", None)
    assert BASE_SYSTEM_PROMPT in prepared.system_prompt
