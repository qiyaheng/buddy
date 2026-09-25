"""内置技能种子：深度调研、文档生成、PPT 生成。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Skill

BUILTIN_SKILLS: list[dict] = [
    {
        "name": "深度调研",
        "icon": "🔬",
        "description": "自动拆解问题、多源联网检索并交叉验证，产出带来源引用的结构化研究报告（Markdown）。",
        "tools": ["web_search", "web_fetch", "create_document"],
        "prompt_template": (
            "本次任务启用【深度调研】模式，请严格执行：\n"
            "1. 先输出 3-6 个搜索子问题（作为计划步骤）；\n"
            "2. 针对每个子问题调用 web_search 检索，对高价值结果使用 web_fetch 阅读正文；\n"
            "3. 多源交叉验证，剔除不可靠与重复信息，记录每条关键信息的来源 URL；\n"
            "4. 最终通过 create_document 生成一份 Markdown 报告，结构包含：摘要（核心结论先行）、"
            "背景与范围、分章发现、结论与建议、参考来源（编号+标题+URL）；正文关键论断用 [n] 角标对应参考来源。\n"
            "不得编造数据与链接；无法验证的信息需明确标注。"
        ),
        "sort_order": 10,
    },
    {
        "name": "文档生成",
        "icon": "📄",
        "description": "将内容整理为结构规范的 Word 文档（标题层级、列表、表格），适合报告与制度文件。",
        "tools": ["create_document"],
        "prompt_template": (
            "本次任务启用【文档生成】模式：\n"
            "1. 先给出文档大纲并与任务目标对齐；\n"
            "2. 内容完整后调用 create_document 生成 Word（format=docx），正确使用标题层级、项目符号与表格；\n"
            "3. 文档包含标题、正文结构与（如适用）结论部分；语言正式、逻辑清晰。"
        ),
        "sort_order": 20,
    },
    {
        "name": "PPT 生成",
        "icon": "📽️",
        "description": "按汇报故事线生成演示文稿：封面、目录、章节内容页与结尾页，一页一个核心观点。",
        "tools": ["create_document"],
        "prompt_template": (
            "本次任务启用【PPT 生成】模式：\n"
            "1. 先设计故事线与分页大纲（每页标题必须是结论式标题）；\n"
            "2. 内容齐备后调用 create_document 生成 PPT（format=pptx），含封面页、目录页、"
            "按章节组织的内容页（要点式，避免大段文字）、结尾页；\n"
            "3. 每页给出 3-5 个要点，必要时用表格页呈现对比信息。"
        ),
        "sort_order": 30,
    },
]


def seed(db: Session) -> int:
    existing = {name for (name,) in db.execute(select(Skill.name)).all()}
    added = 0
    for item in BUILTIN_SKILLS:
        if item["name"] in existing:
            continue
        db.add(Skill(**item, kind="builtin", is_builtin=True, enabled=True))
        added += 1
    if added:
        db.flush()
    return added
