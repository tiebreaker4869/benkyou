"""
Tests for toc_writer.

Pure file I/O — no mocking needed.
"""
import json
import os

import pytest

from indexer.toc_writer import write_toc

SAMPLE_LESSONS = [
    {"lesson": 1, "title": "これはほんです", "page_start": 10, "page_end": 21},
    {"lesson": 2, "title": "これはだれのかばんですか", "page_start": 22, "page_end": 33},
]


@pytest.fixture()
def output_path(tmp_path) -> str:
    return str(tmp_path / "toc.json")


def test_file_is_created(output_path):
    write_toc(SAMPLE_LESSONS, output_path)
    assert os.path.isfile(output_path)


def test_toc_confirmed_is_false(output_path):
    write_toc(SAMPLE_LESSONS, output_path)
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["toc_confirmed"] is False


def test_confirmed_at_is_null(output_path):
    write_toc(SAMPLE_LESSONS, output_path)
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["confirmed_at"] is None


def test_lessons_written_correctly(output_path):
    write_toc(SAMPLE_LESSONS, output_path)
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["lessons"] == SAMPLE_LESSONS


def test_japanese_characters_not_escaped(output_path):
    write_toc(SAMPLE_LESSONS, output_path)
    raw = open(output_path, encoding="utf-8").read()
    assert "これはほんです" in raw


def test_parent_dir_created_automatically(tmp_path):
    nested_path = str(tmp_path / "volume" / "subdir" / "toc.json")
    write_toc(SAMPLE_LESSONS, nested_path)
    assert os.path.isfile(nested_path)
