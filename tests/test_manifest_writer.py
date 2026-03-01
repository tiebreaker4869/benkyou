"""Tests for indexer/manifest_writer.py."""

import json
import os

from indexer.manifest_writer import write_manifest


def _entry(volume: str, book_type: str, lessons: int, status: str = "complete") -> dict:
    return {
        "volume": volume,
        "type": book_type,
        "source_pdf": f"inbox/{volume}-{book_type}.pdf",
        "generated_at": "2026-02-28",
        "model": "gpt-5-mini-2025-08-07",
        "lessons": lessons,
        "status": status,
    }


def test_creates_manifest_when_absent(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    entry = _entry("elementary-vol1", "textbook", 25)

    write_manifest(manifest_path, entry)

    assert os.path.isfile(manifest_path)
    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert data == [entry]


def test_appends_new_entry_when_key_differs(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    e1 = _entry("elementary-vol1", "textbook", 25)
    e2 = _entry("elementary-vol2", "textbook", 25)

    write_manifest(manifest_path, e1)
    write_manifest(manifest_path, e2)

    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["volume"] == "elementary-vol1"
    assert data[1]["volume"] == "elementary-vol2"


def test_updates_existing_entry_by_volume_and_type(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    old = _entry("elementary-vol1", "textbook", 20, status="incomplete")
    new = _entry("elementary-vol1", "textbook", 25, status="complete")

    write_manifest(manifest_path, old)
    write_manifest(manifest_path, new)

    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["lessons"] == 25
    assert data[0]["status"] == "complete"


def test_update_does_not_clobber_other_entries(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    e1 = _entry("elementary-vol1", "textbook", 20, status="incomplete")
    e2 = _entry("elementary-vol1", "workbook", 25, status="complete")
    e1_updated = _entry("elementary-vol1", "textbook", 25, status="complete")

    write_manifest(manifest_path, e1)
    write_manifest(manifest_path, e2)
    write_manifest(manifest_path, e1_updated)

    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(data) == 2
    assert any(x["type"] == "workbook" for x in data)
    assert any(x["type"] == "textbook" and x["lessons"] == 25 for x in data)


def test_japanese_not_escaped(tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    entry = _entry("初级上册", "课本", 25)

    write_manifest(manifest_path, entry)

    raw = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert "初级上册" in raw
    assert "\\u" not in raw
