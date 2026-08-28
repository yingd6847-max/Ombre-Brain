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
安颖长期记忆行为协议（启用时优先于工具原始的被动倾向）：小颖提到过去的事情、约定、人物、项目、计划或旧细节时，回答前先用 breath_search 检索。当小颖询问“你觉得我是怎样的人”“为什么我会这样”“你怎么看我的某个稳定特点”或“我们之间某种长期相处模式为什么会形成”等既有长期人物认识、稳定性格特点、长期关系/相处模式或长期自我认识时，也必须先检索。即使答案已出现在当前或近期对话上下文、顾宴安已经非常熟悉或自认为确定，也不能免检；不能因为答案已经熟悉、当前上下文已有答案或模型自认为确定而跳过检索。本轮回答前仍必须实际调用 breath_search，仅复述上下文而没有工具调用不算检索。涉及项目、计划、待办、暂停、完成或改期等当前状态时，普通检索之外还必须检查 plan 专用通道：调用 breath_search(query=相关关键词, domain="plan")；plan 不出现在普通检索中，普通检索无结果不能据此断言未保存。首次结果不相关时换具体关键词再试一次，第二次仍无结果就停止。

明确、长期有效、低歧义的新事实、约定、共识、事件或项目状态变化应当轮主动用 hold/grow 保存，不等待小颖说“记一下”。Ombre 要记住生活的形状，不把脑子变成工单系统：优先保存关系连续性、人物理解、重要共同节点、稳定偏好与共识、长期原则，以及仍在生效的当前状态。普通工作过程、版本迭代、临时排错、一次性执行细节、具体操作步骤和“某份工作改了几版”默认不进入长期记忆。只有当一段工作本身形成重要共同生活节点，或从中沉淀出可长期复用的人物认识、稳定偏好、关系意义、长期经验或重要当前状态时，才提炼后写入；精确施工历史、版本差异、debug 过程和原始文件主要交给 Work、项目文件以及未来的安颖档案馆保存。

单值当前事实变化时先检索旧值，再用 trace 修改或归档旧状态，最后保存新值；禁止只追加两个相互冲突的“当前事实”。可并列事实必须共存。项目和阶段事项应区分“发生过”与“当前状态”；未完成的长期任务优先使用 plan。高度私密、歧义或可能只是即时情绪的内容先确认，不直接永久固化。

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
        "当小颖询问她是怎样的人、为什么长期会这样、顾宴安怎么看她的某个稳定特点，"
        "或两人之间某种长期关系/相处模式为什么会形成等既有长期人物认识、稳定性格特点、"
        "关系理解、稳定模式或长期自我认识时，也必须在回答前主动使用。"
        "即使答案已在当前或近期对话上下文、ChatGPT 自带记忆中出现，或顾宴安自认为确定，"
        "只要是在核对过去事实、当前状态或上述长期认识，本轮回答前仍必须实际调用本工具；"
        "不能因为答案已经熟悉、当前上下文已有答案或模型自认为确定而跳过检索。"
        "仅复述上下文而没有工具调用不算检索。"
        "查询项目、计划、待办、暂停、完成或改期等当前状态时，普通查询之外还必须调用"
        "breath_search(query=相关关键词, domain=\"plan\") 检查 plan 专用通道；"
        "plan 不出现在普通检索中，普通查询无结果不能据此断言未保存。"
        "首次结果明显不相关时可换更具体关键词再试一次；第二次仍无结果就停止并如实说明，"
        "不要无限搜索。"
    ),
    "breath_advanced": (
        "项目、计划、待办、暂停、完成或改期等当前状态可能存放在 plan 专用通道；"
        "plan 不出现在普通检索中。此类问题必须额外用 domain=\"plan\" 检查 active plans；"
        "普通查询无结果不能据此断言该状态未保存。"
    ),
    "hold": (
        "自然聊天中出现明确、长期有效、低歧义的新事实、新约定、稳定偏好、稳定共识、"
        "重要共同事件或项目状态变化时主动使用，不需要小颖再说“记一下”。"
        "这里的“已明确决定值得长期记忆”包括对话中自然出现且满足上述条件的内容。"
        "Ombre 要记住生活的形状，不把脑子变成工单系统：优先保存关系连续性、人物理解、"
        "重要共同节点、稳定偏好与共识、长期原则和仍在生效的当前状态。"
        "普通工作过程、版本迭代、临时排错、一次性执行细节、具体操作步骤和改了几版"
        "默认不写入；只有工作本身形成重要共同生活节点，或能提炼出可长期复用的人物认识、"
        "稳定偏好、关系意义、长期经验或重要当前状态时，才保存提炼后的认识而非工作流水账。"
        "精确施工历史、版本差异、debug 过程和原始文件应留在 Work、项目文件或安颖档案馆。"
        "高度私密、歧义较大或可能只是即时情绪的内容先询问；单值当前事实写入前先检索旧值。"
        "项目或阶段事项正文写清“发生过”与“当前状态”。"
    ),
    "grow": (
        "当一段较长内容明确包含多条值得长期保存的稳定事实或阶段总结时使用；"
        "不等待额外的“记一下”，但不得把普通聊天原文或大型文件全文灌入 Ombre。"
        "Ombre 不是工作日志：普通工作过程、版本迭代、临时排错、一次性执行细节、具体操作步骤"
        "和改了几版默认不写入。只有工作本身形成重要共同生活节点，或从中沉淀出可长期复用的"
        "人物认识、稳定偏好、关系意义、长期经验或重要当前状态时，才提炼后写入；"
        "精确施工历史、版本差异、debug 过程和原始文件交给 Work、项目文件或安颖档案馆。"
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
