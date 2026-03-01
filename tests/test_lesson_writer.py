"""Tests for indexer/lesson_writer.py."""

import os

from indexer.lesson_writer import lesson_output_path, write_lesson


def test_lesson_output_path_textbook():
    p = lesson_output_path("data", "elementary-vol1", "textbook", 3)
    assert p == os.path.join("data", "elementary-vol1", "textbook", "lesson_03.md")


def test_lesson_output_path_workbook():
    p = lesson_output_path("data", "elementary-vol1", "workbook", 12)
    assert p == os.path.join("data", "elementary-vol1", "workbook", "lesson_12.md")


def test_write_lesson_writes_content(tmp_path):
    output_path = str(tmp_path / "lesson_01.md")
    content = "# 第1課\n\n内容"
    write_lesson(content, output_path)

    assert os.path.isfile(output_path)
    assert (tmp_path / "lesson_01.md").read_text(encoding="utf-8") == content


def test_write_lesson_creates_parent_dirs(tmp_path):
    output_path = str(tmp_path / "nested" / "textbook" / "lesson_01.md")
    write_lesson("# test", output_path)

    assert os.path.isfile(output_path)
