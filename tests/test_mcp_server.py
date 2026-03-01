"""Integration tests for mcp_server/server.py."""

import asyncio

from mcp_server.server import create_server, parse_args


def test_server_has_six_tools():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}
    assert len(tool_names) == 6
    assert tool_names == {
        "list_volumes",
        "list_lessons",
        "get_lesson",
        "get_question_structure",
        "get_question",
        "lookup_word",
    }


def test_all_tools_have_meaningful_descriptions():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    descriptions = {tool.name: (tool.description or "") for tool in tools}

    assert len(descriptions) == 6
    assert "Japanese learning volumes" in descriptions["list_volumes"]
    assert "Japanese volume" in descriptions["list_lessons"]
    assert "full Japanese lesson markdown" in descriptions["get_lesson"]
    assert "workbook question structure" in descriptions["get_question_structure"]
    assert "full workbook question block" in descriptions["get_question"]
    assert "Japanese word in JMDict" in descriptions["lookup_word"]


def test_list_volumes_integration():
    server = create_server(data_dir="data")
    _, payload = asyncio.run(server.call_tool("list_volumes", {}))
    result = payload["result"]
    assert isinstance(result, list)
    assert len(result) > 0
    assert "volume" in result[0]
    assert "type" in result[0]


def test_get_lesson_integration():
    server = create_server(data_dir="data")
    _, payload = asyncio.run(
        server.call_tool(
            "get_lesson",
            {"volume": "elementary-vol1", "lesson": 1, "type": "textbook"},
        )
    )
    lesson_md = payload["result"]
    assert isinstance(lesson_md, str)
    assert "# 第1課" in lesson_md


def test_parse_args_default_data_dir():
    args = parse_args([])
    assert args.data_dir == "data"

