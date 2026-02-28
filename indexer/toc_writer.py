import json
import os


def write_toc(lessons: list[dict], output_path: str) -> None:
    """Write lessons to toc.json in the standard format."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    toc = {
        "toc_confirmed": False,
        "confirmed_at": None,
        "lessons": lessons,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
