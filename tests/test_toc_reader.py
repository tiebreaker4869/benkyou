"""Tests for indexer/toc_reader.py"""
import json
import pytest
from indexer.toc_reader import read_toc


SAMPLE_LESSONS = [
    {"lesson": 1, "title": "第1課 これはほんです", "page_start": 10, "page_end": 21},
    {"lesson": 2, "title": "第2課 かばんです", "page_start": 22, "page_end": 33},
]


def _write_toc(path, confirmed, lessons=None):
    data = {
        "toc_confirmed": confirmed,
        "confirmed_at": "2026-02-27" if confirmed else None,
        "lessons": lessons if lessons is not None else SAMPLE_LESSONS,
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def test_returns_toc_when_confirmed(tmp_path):
    toc_file = tmp_path / "toc.json"
    _write_toc(toc_file, confirmed=True)
    result = read_toc(str(toc_file))
    assert result["toc_confirmed"] is True
    assert len(result["lessons"]) == 2


def test_raises_when_not_confirmed(tmp_path):
    toc_file = tmp_path / "toc.json"
    _write_toc(toc_file, confirmed=False)
    with pytest.raises(ValueError, match="toc not confirmed"):
        read_toc(str(toc_file))


def test_raises_when_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_toc(str(tmp_path / "nonexistent.json"))


def test_returns_correct_lesson_fields(tmp_path):
    toc_file = tmp_path / "toc.json"
    _write_toc(toc_file, confirmed=True)
    result = read_toc(str(toc_file))
    lesson = result["lessons"][0]
    assert lesson["lesson"] == 1
    assert lesson["title"] == "第1課 これはほんです"
    assert lesson["page_start"] == 10
    assert lesson["page_end"] == 21
