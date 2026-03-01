"""Tests for mcp_server/readers.py."""

import json

import pytest

from mcp_server.readers import read_lesson, read_manifest, read_toc


def test_read_manifest_returns_list(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    expected = [
        {
            "volume": "elementary-vol1",
            "type": "textbook",
            "lessons": 25,
            "status": "complete",
        }
    ]
    manifest_path.write_text(json.dumps(expected), encoding="utf-8")

    result = read_manifest(str(tmp_path))
    assert result == expected


def test_read_manifest_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_manifest(str(tmp_path))


def test_read_toc_returns_lessons(tmp_path):
    toc_path = tmp_path / "elementary-vol1" / "textbook" / "toc.json"
    toc_path.parent.mkdir(parents=True, exist_ok=True)
    toc_data = {
        "toc_confirmed": True,
        "confirmed_at": "2026-02-28",
        "lessons": [
            {"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 10},
            {"lesson": 2, "title": "第2課", "page_start": 11, "page_end": 20},
        ],
    }
    toc_path.write_text(json.dumps(toc_data, ensure_ascii=False), encoding="utf-8")

    result = read_toc(str(tmp_path), "elementary-vol1", "textbook")
    assert result["lessons"] == toc_data["lessons"]


def test_read_lesson_returns_content(tmp_path):
    lesson_path = tmp_path / "elementary-vol1" / "textbook" / "lesson_01.md"
    lesson_path.parent.mkdir(parents=True, exist_ok=True)
    lesson_content = "# 第1課\n\n内容"
    lesson_path.write_text(lesson_content, encoding="utf-8")

    result = read_lesson(str(tmp_path), "elementary-vol1", "textbook", 1)
    assert result == lesson_content


def test_read_lesson_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_lesson(str(tmp_path), "elementary-vol1", "textbook", 1)

