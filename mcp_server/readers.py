"""File readers for MCP tools."""

import json
from pathlib import Path


def read_manifest(data_dir: str) -> list[dict]:
    """Read and return manifest entries from data directory."""
    manifest_path = Path(data_dir) / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_toc(data_dir: str, volume: str, type_: str) -> dict:
    """Read toc.json for a given volume/type."""
    toc_path = Path(data_dir) / volume / type_ / "toc.json"
    with toc_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_lesson(data_dir: str, volume: str, type_: str, lesson: int) -> str:
    """Read lesson markdown by lesson number (zero padded)."""
    lesson_path = Path(data_dir) / volume / type_ / f"lesson_{lesson:02d}.md"
    with lesson_path.open("r", encoding="utf-8") as f:
        return f.read()

