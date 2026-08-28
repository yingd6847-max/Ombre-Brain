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


def test_first_512_instruction_characters_are_self_contained() -> None:
    head = ANYING_BEHAVIOR_INSTRUCTIONS[:512]
    for phrase in (
        "回答前先用 breath_search 检索",
        "不等待小颖说“记一下”",
        "先检索旧值",
        "可并列事实必须共存",
        "区分“发生过”与“当前状态”",
        "即时情绪",
    ):
        assert phrase in head


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
