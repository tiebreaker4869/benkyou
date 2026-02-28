"""
Tests for toc_extractor.

Only the OpenAI HTTP call (client.chat.completions.create) is mocked.
The rest — JSON parsing, message construction, image encoding — runs for real.
"""
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import fitz  # pymupdf
import pytest

from indexer.toc_extractor import extract_toc


@pytest.fixture()
def sample_png(tmp_path) -> str:
    """Generate a minimal PNG using pymupdf (1-page PDF rendered to PNG)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Table of Contents")
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    png_path = str(tmp_path / "toc_page.png")
    pix.save(png_path)
    doc.close()
    return png_path


def _make_api_response(lessons: list[dict]) -> MagicMock:
    """Build a minimal fake OpenAI chat completion response."""
    content = json.dumps({"lessons": lessons})
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_LESSONS = [
    {"lesson": 1, "title": "これはほんです", "page_start": 10, "page_end": 21},
    {"lesson": 2, "title": "これはだれのかばんですか", "page_start": 22, "page_end": 33},
]


def test_returns_list_of_lessons(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    result = extract_toc([sample_png], client)

    assert isinstance(result, list)
    assert len(result) == 2


def test_lesson_fields_present(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    result = extract_toc([sample_png], client)

    for lesson in result:
        assert "lesson" in lesson
        assert "title" in lesson
        assert "page_start" in lesson
        assert "page_end" in lesson


def test_lesson_values_match_api_response(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    result = extract_toc([sample_png], client)

    assert result[0]["lesson"] == 1
    assert result[0]["page_start"] == 10
    assert result[1]["title"] == "これはだれのかばんですか"


def test_api_called_once(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    extract_toc([sample_png], client)

    client.chat.completions.create.assert_called_once()


def test_images_sent_as_base64_url(sample_png):
    """Verify that the image is encoded and sent as a base64 data URL."""
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    extract_toc([sample_png], client)

    call_kwargs = client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]

    # Flatten all content parts from user messages
    image_urls = []
    for msg in messages:
        if msg.get("role") == "user":
            for part in msg.get("content", []):
                if isinstance(part, dict) and part.get("type") == "image_url":
                    image_urls.append(part["image_url"]["url"])

    assert len(image_urls) == 1
    assert image_urls[0].startswith("data:image/png;base64,")

    # Verify the base64 payload actually decodes to the original file bytes
    encoded = image_urls[0].split(",", 1)[1]
    decoded = base64.b64decode(encoded)
    with open(sample_png, "rb") as f:
        original = f.read()
    assert decoded == original


def test_model_passed_to_api(sample_png):
    """The model argument should be forwarded to the API call."""
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    extract_toc([sample_png], client, model="gpt-4o")

    call_kwargs = client.chat.completions.create.call_args
    assert call_kwargs.kwargs.get("model") == "gpt-4o"


def test_default_model_is_gpt5_mini(sample_png):
    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    extract_toc([sample_png], client)

    call_kwargs = client.chat.completions.create.call_args
    assert call_kwargs.kwargs.get("model") == "gpt-5-mini-2025-08-07"


def test_multiple_images_all_sent(tmp_path):
    """All provided images should appear in the API call."""
    doc = fitz.open()
    png_paths = []
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"TOC page {i}")
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        p = str(tmp_path / f"toc_{i}.png")
        pix.save(p)
        png_paths.append(p)
    doc.close()

    client = MagicMock()
    client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    extract_toc(png_paths, client)

    call_kwargs = client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
    image_count = sum(
        1
        for msg in messages
        if msg.get("role") == "user"
        for part in msg.get("content", [])
        if isinstance(part, dict) and part.get("type") == "image_url"
    )
    assert image_count == 2
