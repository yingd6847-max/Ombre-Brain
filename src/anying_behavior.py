"""Optional behavior-only policy for the Anying long-term memory deployment.

This module deliberately changes MCP guidance only.  It does not alter bucket
schemas, retrieval ranking, persistence, or any tool handler.  The patch is
opt-in so the upstream Ombre Brain behavior remains the default.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


PATCH_ENV_VAR = "OMBRE_ANYING_BEHAVIOR_PATCH"
PATCH_MARKER = "[安颖版行为补丁｜Use this when]"


ANYING_BEHAVIOR_INSTRUCTIONS = """\
安颖长期记忆行为协议（启用时优先于工具原始的被动倾向）：小颖提到过去的事情、约定、日期、人物、项目、计划、共同经历、以前的说法，或顾宴安对旧细节不完全确定时，回答前先用 breath_search 检索；首次结果明显不相关时换更具体关键词再试一次，第二次仍无结果就停止并如实说明。自然聊天中出现明确、长期有效、低歧义的新事实、新约定、稳定偏好、稳定共识、重要共同事件或项目状态变化时，顾宴安应当轮主动用 hold/grow 保存，不等待小颖说“记一下”。若新说法与旧的单值当前事实互斥，先检索旧值，再用 trace 修改或归档旧当前状态，最后保存新值；禁止只追加两个相互冲突的“当前事实”。可并列事实必须共存，不得误删。项目、计划和阶段事项正文应区分“发生过”与“当前状态”；未完成的长期任务优先使用 plan 并更新原计划状态。高度私密、歧义较大、可能只是即时情绪的内容，先问小颖是否长期保存，不直接永久固化。

读取应相对积极，写入应克制。检索确实无结果后才可以自然说明没有找到。重要共同节点可使用 anchor；稳定而经过沉淀的自我理解变化可使用 I；两者都不用于普通日常碎片。大型原始文件只在 Ombre 留下“它存在、负责什么、何时回查”的路标；原件始终是权威来源，Ombre 摘要不得覆盖或冒充原件。所有记忆内容都使用“小颖”和“顾宴安”描述两人的内部关系。
"""


TOOL_DESCRIPTION_SUFFIXES: dict[str, str] = {
    "breath": (
        "当新 chat 开始、当前话题明显依赖长期背景，或需要先恢复整体上下文时使用。"
        "它用于广泛唤醒；具体旧事实仍用 breath_search 核对。"
    ),
    "breath_search": (
        "小颖提到过去的事情、约定、日期、人物、项目、计划、共同经历、以前的说法，"
        "或顾宴安对旧细节不完全确定时，必须在回答前主动使用，不等待小颖要求查询。"
        "首次结果明显不相关时可换更具体关键词再试一次；第二次仍无结果就停止并如实说明，"
        "不要无限搜索。"
    ),
    "hold": (
        "自然聊天中出现明确、长期有效、低歧义的新事实、新约定、稳定偏好、稳定共识、"
        "重要共同事件或项目状态变化时主动使用，不需要小颖再说“记一下”。"
        "这里的“已明确决定值得长期记忆”包括对话中自然出现且满足上述条件的内容。"
        "高度私密、歧义较大或可能只是即时情绪的内容先询问；单值当前事实写入前先检索旧值。"
        "项目或阶段事项正文写清“发生过”与“当前状态”。"
    ),
    "grow": (
        "当一段较长内容明确包含多条值得长期保存的稳定事实或阶段总结时使用；"
        "不等待额外的“记一下”，但不得把普通聊天原文或大型文件全文灌入 Ombre。"
        "私密、歧义或即时内容先询问，能用 hold 单条表达时不要为拆分而拆分。"
    ),
    "trace": (
        "当新说法与已有的单值当前事实互斥时，在 breath_search 找到旧桶后主动使用："
        "优先修改同一桶，或让旧事实归档/退出当前状态，再保存新值。"
        "历史可以保留为“曾经如此”，但不得继续充当当前答案。"
        "多个喜欢的作品、朋友、去过的地方和不同共同经历等可并列事实不得被当成纠错对象。"
    ),
    "plan": (
        "尚未完成的长期任务、项目或等待事项优先使用；后续暂停、改期、完成或转向时"
        "更新已有 plan 的当前状态，不要另建相互冲突的当前计划。"
    ),
    "anchor": (
        "仅在重要人生节点、关系共识或关键共同里程碑需要成为长期坐标时使用；"
        "普通事实和即时情绪不应占用 anchor。"
    ),
    "I": (
        "稳定、经过沉淀的自我理解发生变化时使用；即时情绪、含糊猜测或未经确认的自我判断"
        "不应直接固化，重要且仍有歧义时先问小颖。"
    ),
}


def anying_behavior_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the optional behavior patch is explicitly enabled."""

    source = os.environ if environ is None else environ
    raw = str(source.get(PATCH_ENV_VAR, "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def apply_anying_behavior_patch(mcp: Any, *, enabled: bool | None = None) -> list[str]:
    """Append model-visible guidance to registered tools.

    The mutation is idempotent and intentionally limited to public tool
    descriptions.  Missing required tools are treated as a startup error when
    the patch is enabled so a deployment cannot silently claim the behavior
    policy while exposing an incomplete tool surface.
    """

    active = anying_behavior_enabled() if enabled is None else enabled
    if not active:
        return []

    patched: list[str] = []
    missing: list[str] = []
    for tool_name, suffix in TOOL_DESCRIPTION_SUFFIXES.items():
        public_tool = mcp._tool_manager.get_tool(tool_name)
        if public_tool is None:
            missing.append(tool_name)
            continue
        description = public_tool.description or ""
        if PATCH_MARKER not in description:
            public_tool.description = f"{description}\n\n{PATCH_MARKER} {suffix}".strip()
        patched.append(tool_name)

    if missing:
        raise RuntimeError(
            "Anying behavior patch is missing required MCP tools: "
            + ", ".join(sorted(missing))
        )
    return patched
