"""Tests for mcp_server/dictionary.py."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.dictionary import lookup_word


def _make_entry(*, kana=None, kanji=None, pos=None, gloss=None):
    sense = SimpleNamespace(pos=pos or [], gloss=gloss or [])
    return SimpleNamespace(
        kana_forms=[SimpleNamespace(text=t) for t in (kana or [])],
        kanji_forms=[SimpleNamespace(text=t) for t in (kanji or [])],
        senses=[sense],
    )


@patch("mcp_server.dictionary._jam")
def test_lookup_word_success(mock_jam: MagicMock):
    entry = _make_entry(kana=["たべる"], pos=["verb"], gloss=["to eat"])
    mock_jam.lookup.return_value = SimpleNamespace(entries=[entry])

    result = lookup_word("食べる")
    assert result == {
        "reading": "たべる",
        "pos": ["verb"],
        "meanings": ["to eat"],
        "examples": [],
    }


@patch("mcp_server.dictionary._jam")
def test_lookup_word_not_found(mock_jam: MagicMock):
    mock_jam.lookup.return_value = SimpleNamespace(entries=[])
    assert lookup_word("不存在") is None


@patch("mcp_server.dictionary._jam")
def test_lookup_word_kanji_fallback(mock_jam: MagicMock):
    entry = _make_entry(kana=[], kanji=["食べる"], pos=["verb"], gloss=["to eat"])
    mock_jam.lookup.return_value = SimpleNamespace(entries=[entry])

    result = lookup_word("食べる")
    assert result is not None
    assert result["reading"] == "食べる"

