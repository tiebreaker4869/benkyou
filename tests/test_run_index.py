"""Tests for indexer/run.py --step index."""

import base64
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from indexer.run import parse_args, run_index


def _make_markdown_response(content: str) -> MagicMock:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    response = MagicMock()
    response.choices = [choice]
    return response


def _write_toc(toc_path: str, confirmed: bool, lessons: list[dict]) -> None:
    os.makedirs(os.path.dirname(toc_path), exist_ok=True)
    with open(toc_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "toc_confirmed": confirmed,
                "confirmed_at": "2026-02-28" if confirmed else None,
                "lessons": lessons,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def _write_pages(pages_dir: str, page_count: int) -> list[str]:
    os.makedirs(pages_dir, exist_ok=True)
    paths = []
    for i in range(page_count):
        path = os.path.join(pages_dir, f"page_{i + 1:03d}.png")
        # Unique bytes per page so we can assert exact page slicing.
        with open(path, "wb") as f:
            f.write(f"PAGE-{i + 1}".encode("utf-8"))
        paths.append(path)
    return paths


def _decode_first_image_url(call) -> bytes:
    messages = call.kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    first_url = user_msg["content"][0]["image_url"]["url"]
    encoded = first_url.split(",", 1)[1]
    return base64.b64decode(encoded)


def _image_count(call) -> int:
    messages = call.kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    return sum(1 for p in user_msg["content"] if p.get("type") == "image_url")


def test_run_index_aborts_when_toc_not_confirmed(tmp_path, capsys):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    _write_toc(
        toc_path,
        confirmed=False,
        lessons=[{"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2}],
    )

    client = MagicMock()
    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    out = capsys.readouterr()
    assert "toc not confirmed" in out.err.lower()
    client.chat.completions.create.assert_not_called()


def test_parse_args_index_has_default_concurrency():
    args = parse_args(
        [
            "--pdf",
            "inbox/book.pdf",
            "--volume",
            "elementary-vol1",
            "--type",
            "textbook",
            "--step",
            "index",
        ]
    )
    assert args.concurrency == 8


def test_run_index_calls_vlm_once_per_page(tmp_path):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [
        {"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2},
        {"lesson": 2, "title": "第2課", "page_start": 3, "page_end": 4},
    ]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 6)

    client = MagicMock()
    client.chat.completions.create.return_value = _make_markdown_response("# lesson")

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    assert client.chat.completions.create.call_count == 6


def test_run_index_page_slice_with_page_base_0(tmp_path):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [{"lesson": 1, "title": "第1課", "page_start": 2, "page_end": 3}]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    page_paths = _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 5)

    client = MagicMock()
    client.chat.completions.create.return_value = _make_markdown_response("# lesson")

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    call = client.chat.completions.create.call_args_list[0]
    assert _image_count(call) == 1
    first_sent = _decode_first_image_url(call)
    expected_first = open(page_paths[1], "rb").read()
    assert first_sent == expected_first


def test_run_index_page_slice_with_page_base_5(tmp_path):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [{"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2}]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    page_paths = _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 8)

    client = MagicMock()
    client.chat.completions.create.return_value = _make_markdown_response("# lesson")

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=5,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    call = client.chat.completions.create.call_args_list[0]
    assert _image_count(call) == 1
    first_sent = _decode_first_image_url(call)
    expected_first = open(page_paths[5], "rb").read()
    assert first_sent == expected_first


def test_run_index_creates_lesson_markdown_and_manifest(tmp_path):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [{"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2}]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 3)

    client = MagicMock()
    client.chat.completions.create.return_value = _make_markdown_response("# 第1課\n\n内容")

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    lesson_md = os.path.join(data_root, "elementary-vol1", "textbook", "lesson_01.md")
    assert os.path.isfile(lesson_md)
    assert "第1課" in open(lesson_md, encoding="utf-8").read()

    manifest_path = os.path.join(data_root, "manifest.json")
    assert os.path.isfile(manifest_path)
    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert len(manifest) == 1
    assert manifest[0]["volume"] == "elementary-vol1"
    assert manifest[0]["type"] == "textbook"
    assert manifest[0]["lessons"] == 1


def test_run_index_retries_transient_failure(tmp_path):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [{"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2}]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 3)

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        RuntimeError("temporary 500"),
        _make_markdown_response("# 第1課\n\n内容"),
        _make_markdown_response("# 第1課\n\n内容"),
        _make_markdown_response("# 第1課\n\n内容"),
    ]

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    assert client.chat.completions.create.call_count == 4
    lesson_md = os.path.join(data_root, "elementary-vol1", "textbook", "lesson_01.md")
    assert os.path.isfile(lesson_md)


def test_run_index_prints_progress(tmp_path, capsys):
    data_root = str(tmp_path / "data")
    toc_path = os.path.join(data_root, "elementary-vol1", "textbook", "toc.json")
    lessons = [{"lesson": 1, "title": "第1課", "page_start": 1, "page_end": 2}]
    _write_toc(toc_path, confirmed=True, lessons=lessons)
    _write_pages(os.path.join(data_root, "elementary-vol1", "textbook", "_pages"), 3)

    client = MagicMock()
    client.chat.completions.create.return_value = _make_markdown_response("# 第1課\n\n内容")

    run_index(
        pdf_path="inbox/book.pdf",
        volume="elementary-vol1",
        book_type="textbook",
        data_root=data_root,
        page_base=0,
        client=client,
        model="gpt-5-mini-2025-08-07",
    )

    out = capsys.readouterr().out
    assert "[1/1]" in out
