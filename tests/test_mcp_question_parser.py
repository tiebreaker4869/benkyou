"""Tests for mcp_server/question_parser.py."""

import pytest

from mcp_server.question_parser import extract_question, parse_question_structure


def test_parse_structure_basic():
    markdown = """# 第1課 練習

## 問題1
題目1
### (1)
### (2)
### (3)

## 問題2
題目2
### (1)
### (2)

## 問題3
題目3
### (1)
"""
    result = parse_question_structure(markdown)
    assert result == {
        "total": 3,
        "questions": [
            {"num": 1, "sub_count": 3},
            {"num": 2, "sub_count": 2},
            {"num": 3, "sub_count": 1},
        ],
    }


def test_parse_fullwidth_digits():
    markdown = """## 問題１
### (1)
"""
    result = parse_question_structure(markdown)
    assert result["total"] == 1
    assert result["questions"][0]["num"] == 1
    assert result["questions"][0]["sub_count"] == 1


def test_parse_fullwidth_parens():
    markdown = """## 問題1
### （1）
### （2）
"""
    result = parse_question_structure(markdown)
    assert result["questions"][0]["sub_count"] == 2


def test_get_question_returns_block():
    markdown = """# 第1課 練習

## 問題1
題目1
### (1)

## 問題2
題目2
### (1)
### (2)

## 問題3
題目3
"""
    result = extract_question(markdown, 2)
    assert result.startswith("## 問題2")
    assert "題目2" in result
    assert "### (2)" in result
    assert "## 問題3" not in result


def test_get_question_out_of_range():
    markdown = """## 問題1
內容
"""
    with pytest.raises(ValueError, match="Question 2 not found"):
        extract_question(markdown, 2)

