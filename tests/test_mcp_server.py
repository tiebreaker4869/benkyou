"""Integration tests for mcp_server/server.py."""

import asyncio
import json

from mcp_server.server import create_server, parse_args


def test_server_has_eight_tools():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}
    assert len(tool_names) == 8
    assert tool_names == {
        "list_volumes",
        "list_lessons",
        "get_lesson",
        "get_question_structure",
        "get_question",
        "lookup_word",
        "browse_lesson_flow",
        "practice_lesson_flow",
    }


def test_all_tools_have_meaningful_descriptions():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    descriptions = {tool.name: (tool.description or "") for tool in tools}

    assert len(descriptions) == 8
    assert "Japanese learning volumes" in descriptions["list_volumes"]
    assert "Japanese volume" in descriptions["list_lessons"]
    assert "full Japanese lesson markdown" in descriptions["get_lesson"]
    assert "workbook question structure" in descriptions["get_question_structure"]
    assert "full workbook question block" in descriptions["get_question"]
    assert "Japanese word in JMDict" in descriptions["lookup_word"]
    assert "READ or BROWSE" in descriptions["browse_lesson_flow"]
    assert "PRACTICE or DO EXERCISES" in descriptions["practice_lesson_flow"]


def test_browse_lesson_flow_returns_instructions():
    server = create_server()
    _, payload = asyncio.run(server.call_tool("browse_lesson_flow", {}))
    result = payload["result"]
    assert "list_volumes" in result
    assert "list_lessons" in result
    assert "get_lesson" in result
    assert "単語" in result
    assert "文型" in result
    assert "例文" in result
    assert "会話" in result
    assert "文法" in result


def test_practice_lesson_flow_returns_instructions():
    server = create_server()
    _, payload = asyncio.run(server.call_tool("practice_lesson_flow", {}))
    result = payload["result"]
    assert "list_volumes" in result
    assert "list_lessons" in result
    assert "get_question_structure" in result
    assert "get_question" in result
    assert "image description text" in result
    assert "never skip, hide, or omit it" in result


def test_list_volumes_integration(tmp_path):
    manifest = [
        {
            "volume": "elementary-vol1",
            "type": "textbook",
            "lessons": 1,
            "status": "complete",
        }
    ]
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    server = create_server(data_dir=str(tmp_path))
    _, payload = asyncio.run(server.call_tool("list_volumes", {}))
    result = payload["result"]
    assert isinstance(result, list)
    assert len(result) == 1
    assert "volume" in result[0]
    assert "type" in result[0]


def test_get_lesson_integration(tmp_path):
    lesson_path = tmp_path / "elementary-vol1" / "textbook" / "lesson_01.md"
    lesson_path.parent.mkdir(parents=True, exist_ok=True)
    lesson_path.write_text("# 第1課\n\n内容", encoding="utf-8")

    server = create_server(data_dir=str(tmp_path))
    _, payload = asyncio.run(
        server.call_tool(
            "get_lesson",
            {"volume": "elementary-vol1", "lesson": 1, "book_type": "textbook"},
        )
    )
    lesson_md = payload["result"]
    assert isinstance(lesson_md, str)
    assert "# 第1課" in lesson_md


def test_parse_args_default_data_dir():
    args = parse_args([])
    assert args.data_dir == "data"


def test_prompts_listed():
    server = create_server()
    prompts = asyncio.run(server.list_prompts())
    prompt_names = {prompt.name for prompt in prompts}
    assert "browse_lesson" in prompt_names
    assert "practice_lesson" in prompt_names


def test_browse_lesson_prompt_contains_key_instructions():
    server = create_server()
    prompt = asyncio.run(server.get_prompt("browse_lesson", {"volume": "vol1", "lesson": "3"}))
    prompt_text = str(prompt)
    assert "get_lesson" in prompt_text
    assert "単語" in prompt_text
    assert "文型" in prompt_text
    assert "例文" in prompt_text
    assert "会話" in prompt_text
    assert "文法" in prompt_text


def test_practice_lesson_prompt_contains_image_instruction():
    server = create_server()
    prompt = asyncio.run(
        server.get_prompt("practice_lesson", {"volume": "vol1", "lesson": "3"})
    )
    prompt_text = str(prompt)
    assert "get_question_structure" in prompt_text
    assert "get_question" in prompt_text
    assert "image description text" in prompt_text
    assert "never skip, hide, or omit it" in prompt_text

