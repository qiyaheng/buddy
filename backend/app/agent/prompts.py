"""系统提示词与会话历史组装。"""

from __future__ import annotations

from typing import Any

BASE_SYSTEM_PROMPT = """你是 SMEbuddy 智能工作台中的 AI 专家助手。
请遵循以下原则：
1. 先理解任务目标，必要时给出简短清晰的执行思路；
2. 使用中文回答，结构清晰、结论先行；
3. 调用工具时基于事实，不编造来源与数据；
4. 产出文档时使用规范的 Markdown 格式。"""

SKILL_PROMPT_TEMPLATE = """

# 当前启用的技能：{name}
{template}""".strip()


def build_system_prompt(
    *, expert_snapshot: dict[str, Any] | None, skill_snapshots: list[dict[str, Any]]
) -> str:
    parts: list[str] = []
    if expert_snapshot and expert_snapshot.get("system_prompt"):
        parts.append(expert_snapshot["system_prompt"].strip())
    parts.append(BASE_SYSTEM_PROMPT)
    for skill in skill_snapshots:
        template = (skill.get("prompt_template") or "").strip()
        if template:
            parts.append(SKILL_PROMPT_TEMPLATE.format(name=skill.get("name", ""), template=template))
    return "\n\n".join(parts)


def build_chat_messages(
    *, system_prompt: str, history: list[tuple[str, str]], user_content: str
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for role, content in history:
        if content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_content})
    return messages
