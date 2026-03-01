"""Write lesson markdown files to disk."""

import os


def lesson_output_path(data_root: str, volume: str, book_type: str, lesson_num: int) -> str:
    filename = f"lesson_{lesson_num:02d}.md"
    return os.path.join(data_root, volume, book_type, filename)


def write_lesson(markdown: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
