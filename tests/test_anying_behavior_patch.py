from mcp.server.fastmcp import FastMCP

from anying_behavior import (
    ANYING_BEHAVIOR_INSTRUCTIONS,
    PATCH_ENV_VAR,
    PATCH_MARKER,
    TOOL_DESCRIPTION_SUFFIXES,
    anying_behavior_enabled,
    apply_anying_behavior_patch,
)


def _server_with_patch_tools() -> FastMCP:
    server = FastMCP("test-anying-behavior")

    for tool_name in TOOL_DESCRIPTION_SUFFIXES:
        async def placeholder() -> str:
            return "ok"

        placeholder.__name__ = f"placeholder_{tool_name}"
        server.tool(name=tool_name, description=f"original {tool_name}")(placeholder)

    return server


def test_patch_flag_is_opt_in_and_accepts_documented_true_values() -> None:
    assert not anying_behavior_enabled({})
    assert not anying_behavior_enabled({PATCH_ENV_VAR: "false"})
    for value in ("true", "TRUE", "1", "yes", "on"):
        assert anying_behavior_enabled({PATCH_ENV_VAR: value})


def test_server_instructions_cover_the_four_behavior_protocols() -> None:
    required_phrases = (
        "回答前先用 breath_search 检索",
        "即使答案已出现在当前或近期对话上下文",
        "本轮回答前仍必须实际调用 breath_search",
        "仅复述上下文而没有工具调用不算检索",
        "还必须检查 plan 专用通道",
        'domain="plan"',
        "plan 不出现在普通检索中",
        "不等待小颖说“记一下”",
        "先检索旧值",
        "禁止只追加两个相互冲突的“当前事实”",
        "可并列事实必须共存",
        "区分“发生过”与“当前状态”",
        "即时情绪",
        "原件始终是权威来源",
    )
    for phrase in required_phrases:
        assert phrase in ANYING_BEHAVIOR_INSTRUCTIONS


def test_first_512_instruction_characters_cover_retrieval_boundaries() -> None:
    head = ANYING_BEHAVIOR_INSTRUCTIONS[:512]
    for phrase in (
        "回答前先用 breath_search 检索",
        "长期人物认识",
        "稳定性格特点",
        "长期自我认识",
        "即使答案已出现在当前或近期对话上下文",
        "本轮回答前仍必须实际调用 breath_search",
        "仅复述上下文而没有工具调用不算检索",
        "还必须检查 plan 专用通道",
        'domain="plan"',
        "plan 不出现在普通检索中",
    ):
        assert phrase in head


def test_search_description_rejects_recent_context_as_a_retrieval_substitute() -> None:
    suffix = TOOL_DESCRIPTION_SUFFIXES["breath_search"]
    for phrase in (
        "当前或近期对话上下文",
        "本轮回答前仍必须实际调用本工具",
        "仅复述上下文而没有工具调用不算检索",
    ):
        assert phrase in suffix


def test_stable_person_and_relationship_questions_require_retrieval() -> None:
    for guidance in (
        ANYING_BEHAVIOR_INSTRUCTIONS,
        TOOL_DESCRIPTION_SUFFIXES["breath_search"],
    ):
        for phrase in (
            "长期人物认识",
            "稳定性格特点",
            "长期自我认识",
            "长期关系",
        ):
            assert phrase in guidance
        assert "当前上下文已有答案" in guidance
        assert "自认为确定" in guidance


def test_work_logs_are_filtered_from_long_term_writes() -> None:
    for guidance in (
        ANYING_BEHAVIOR_INSTRUCTIONS,
        TOOL_DESCRIPTION_SUFFIXES["hold"],
        TOOL_DESCRIPTION_SUFFIXES["grow"],
    ):
        for phrase in (
            "普通工作过程",
            "版本迭代",
            "临时排错",
            "一次性执行细节",
            "具体操作步骤",
            "重要共同生活节点",
            "人物认识",
            "稳定偏好",
            "关系意义",
            "长期经验",
            "重要当前状态",
            "Work",
            "项目文件",
            "安颖档案馆",
        ):
            assert phrase in guidance


def test_project_status_retrieval_checks_the_dedicated_plan_channel() -> None:
    search_suffix = TOOL_DESCRIPTION_SUFFIXES["breath_search"]
    advanced_suffix = TOOL_DESCRIPTION_SUFFIXES["breath_advanced"]
    for suffix in (search_suffix, advanced_suffix):
        assert 'domain="plan"' in suffix
        assert "plan 不出现在普通检索中" in suffix
        assert "普通查询无结果不能据此断言" in suffix


def test_fastmcp_exposes_server_instructions() -> None:
    server = FastMCP("test", instructions=ANYING_BEHAVIOR_INSTRUCTIONS)
    assert server._mcp_server.instructions == ANYING_BEHAVIOR_INSTRUCTIONS


def test_disabled_patch_leaves_descriptions_unchanged() -> None:
    server = _server_with_patch_tools()
    before = {
        name: server._tool_manager.get_tool(name).description
        for name in TOOL_DESCRIPTION_SUFFIXES
    }
    assert apply_anying_behavior_patch(server, enabled=False) == []
    after = {
        name: server._tool_manager.get_tool(name).description
        for name in TOOL_DESCRIPTION_SUFFIXES
    }
    assert after == before


def test_enabled_patch_updates_every_target_once() -> None:
    server = _server_with_patch_tools()
    expected = list(TOOL_DESCRIPTION_SUFFIXES)

    assert apply_anying_behavior_patch(server, enabled=True) == expected
    assert apply_anying_behavior_patch(server, enabled=True) == expected

    for name in expected:
        description = server._tool_manager.get_tool(name).description
        assert description.startswith(f"original {name}")
        assert description.count(PATCH_MARKER) == 1
        assert TOOL_DESCRIPTION_SUFFIXES[name] in description


def test_enabled_patch_fails_if_a_required_tool_is_missing() -> None:
    server = _server_with_patch_tools()
    server._tool_manager._tools.pop("trace")

    try:
        apply_anying_behavior_patch(server, enabled=True)
    except RuntimeError as exc:
        assert "trace" in str(exc)
    else:
        raise AssertionError("missing required patch tool should fail startup")
