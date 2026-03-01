"""Tests for indexer/lesson_extractor.py

Only the OpenAI HTTP call (client.chat.completions.create) is mocked.
Image encoding and message construction run for real.
"""
import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import fitz  # pymupdf
import pytest

from indexer.lesson_extractor import extract_lesson


SAMPLE_LESSON = {"lesson": 3, "title": "これはほんです", "page_start": 10, "page_end": 21}


@pytest.fixture()
def sample_png(tmp_path) -> str:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Lesson page content")
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    png_path = str(tmp_path / "lesson_page.png")
    pix.save(png_path)
    doc.close()
    return png_path


def _make_api_response(content: str) -> MagicMock:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    response = MagicMock()
    response.choices = [choice]
    return response


def _get_image_urls(call_args) -> list[str]:
    messages = call_args.kwargs.get("messages") or call_args.args[0]
    return [
        part["image_url"]["url"]
        for msg in messages
        if msg.get("role") == "user"
        for part in msg.get("content", [])
        if isinstance(part, dict) and part.get("type") == "image_url"
    ]


def test_returns_string(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("## 単語\nfoo")
    result = extract_lesson([sample_png], SAMPLE_LESSON, "vol1", "textbook", client)
    assert isinstance(result, str)


def test_api_called_once_for_single_page(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("markdown")
    extract_lesson([sample_png], SAMPLE_LESSON, "vol1", "textbook", client)
    assert client.chat.completions.create.call_count == 2


def test_api_called_once_per_page(tmp_path):
    doc = fitz.open()
    png_paths = []
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i}")
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        p = str(tmp_path / f"page_{i}.png")
        pix.save(p)
        png_paths.append(p)
    doc.close()

    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("markdown")
    extract_lesson(png_paths, SAMPLE_LESSON, "vol1", "textbook", client)

    assert client.chat.completions.create.call_count == 4


def test_each_request_contains_one_image(tmp_path):
    doc = fitz.open()
    png_paths = []
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i}")
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        p = str(tmp_path / f"page_{i}.png")
        pix.save(p)
        png_paths.append(p)
    doc.close()

    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("markdown")
    extract_lesson(png_paths, SAMPLE_LESSON, "vol1", "textbook", client)

    # Page-level calls each contain one image.
    for call in client.chat.completions.create.call_args_list[:2]:
        urls = _get_image_urls(call)
        assert len(urls) == 1
    # Final aggregation call contains no image payload.
    final_urls = _get_image_urls(client.chat.completions.create.call_args_list[-1])
    assert len(final_urls) == 0


def test_merges_page_outputs_in_order(tmp_path):
    doc = fitz.open()
    png_paths = []
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i}")
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        p = str(tmp_path / f"page_{i}.png")
        pix.save(p)
        png_paths.append(p)
    doc.close()

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _make_api_response("page1"),
        _make_api_response("page2"),
        _make_api_response("merged"),
    ]
    result = extract_lesson(png_paths, SAMPLE_LESSON, "vol1", "textbook", client)
    assert result == "merged"


def test_aggregate_call_receives_page_fragments(tmp_path):
    doc = fitz.open()
    png_paths = []
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i}")
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        p = str(tmp_path / f"page_{i}.png")
        pix.save(p)
        png_paths.append(p)
    doc.close()

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _make_api_response("frag-1"),
        _make_api_response("frag-2"),
        _make_api_response("final"),
    ]
    extract_lesson(png_paths, SAMPLE_LESSON, "vol1", "textbook", client)
    aggregate_call = client.chat.completions.create.call_args_list[-1]
    messages = aggregate_call.kwargs.get("messages") or aggregate_call.args[0]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert "frag-1" in user_content
    assert "frag-2" in user_content


def test_textbook_and_workbook_use_different_prompts(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("markdown")

    extract_lesson([sample_png], SAMPLE_LESSON, "vol1", "textbook", client)
    textbook_call = client.chat.completions.create.call_args

    client.reset_mock()
    client.chat.completions.create.return_value = _make_api_response("markdown")
    extract_lesson([sample_png], SAMPLE_LESSON, "vol1", "workbook", client)
    workbook_call = client.chat.completions.create.call_args

    def get_system(call):
        messages = call.kwargs.get("messages") or call.args[0]
        return next(m["content"] for m in messages if m["role"] == "system")

    assert get_system(textbook_call) != get_system(workbook_call)


def test_model_passed_to_api(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response("markdown")
    extract_lesson([sample_png], SAMPLE_LESSON, "vol1", "textbook", client, model="gpt-4o")
    assert client.chat.completions.create.call_args.kwargs.get("model") == "gpt-4o"
