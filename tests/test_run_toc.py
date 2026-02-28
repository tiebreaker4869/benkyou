"""
Tests for indexer/run.py --step toc.

Strategy:
- Argument parsing: no mocking, test directly via the parse_args helper
- End-to-end flow: mock only client.chat.completions.create (the HTTP boundary)
  to avoid real API calls; all file I/O and PDF rendering run for real
"""
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import fitz
import pytest

# We import run as a module to test parse_args and run_toc separately
import importlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_response(lessons):
    content = json.dumps({"lessons": lessons})
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_LESSONS = [
    {"lesson": 1, "title": "これはほんです", "page_start": 10, "page_end": 21},
    {"lesson": 2, "title": "これはだれのかばんですか", "page_start": 22, "page_end": 33},
]


@pytest.fixture()
def sample_pdf(tmp_path) -> str:
    pdf_path = str(tmp_path / "textbook.pdf")
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def test_parse_args_toc_step(sample_pdf):
    from indexer.run import parse_args
    args = parse_args([
        "--pdf", sample_pdf,
        "--volume", "elementary-vol1",
        "--type", "textbook",
        "--step", "toc",
        "--toc-pages", "2-3",
    ])
    assert args.step == "toc"
    assert args.volume == "elementary-vol1"
    assert args.toc_pages == "2-3"


def test_parse_args_toc_pages_required_for_toc_step(sample_pdf, capsys):
    """--toc-pages must be provided when --step toc is used."""
    from indexer.run import parse_args, validate_args
    args = parse_args([
        "--pdf", sample_pdf,
        "--volume", "elementary-vol1",
        "--type", "textbook",
        "--step", "toc",
    ])
    with pytest.raises(SystemExit):
        validate_args(args)


# ---------------------------------------------------------------------------
# End-to-end flow (mocking only the OpenAI HTTP call)
# ---------------------------------------------------------------------------

def test_run_toc_creates_pages_dir(sample_pdf, tmp_path):
    from indexer.run import run_toc

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    data_dir = str(tmp_path / "data")
    run_toc(
        pdf_path=sample_pdf,
        volume="elementary-vol1",
        toc_pages="2-3",
        data_root=data_dir,
        client=mock_client,
    )

    pages_dir = os.path.join(data_dir, "elementary-vol1", "_pages")
    assert os.path.isdir(pages_dir)


def test_run_toc_creates_toc_json(sample_pdf, tmp_path):
    from indexer.run import run_toc

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    data_dir = str(tmp_path / "data")
    run_toc(
        pdf_path=sample_pdf,
        volume="elementary-vol1",
        toc_pages="2-3",
        data_root=data_dir,
        client=mock_client,
    )

    toc_path = os.path.join(data_dir, "elementary-vol1", "toc.json")
    assert os.path.isfile(toc_path)

    with open(toc_path, encoding="utf-8") as f:
        toc = json.load(f)

    assert toc["toc_confirmed"] is False
    assert toc["confirmed_at"] is None
    assert len(toc["lessons"]) == 2


def test_run_toc_only_sends_requested_pages_to_vlm(sample_pdf, tmp_path):
    """Only the pages specified by --toc-pages should be sent to the VLM."""
    from indexer.run import run_toc

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    data_dir = str(tmp_path / "data")
    run_toc(
        pdf_path=sample_pdf,
        volume="elementary-vol1",
        toc_pages="2-3",   # pages 2 and 3 only
        data_root=data_dir,
        client=mock_client,
    )

    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
    image_count = sum(
        1
        for msg in messages
        if msg.get("role") == "user"
        for part in msg.get("content", [])
        if isinstance(part, dict) and part.get("type") == "image_url"
    )
    assert image_count == 2  # pages 2-3 → 2 images


def test_run_toc_passes_model_to_extract_toc(sample_pdf, tmp_path):
    """model arg should reach the API call."""
    from indexer.run import run_toc

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    data_dir = str(tmp_path / "data")
    run_toc(
        pdf_path=sample_pdf,
        volume="elementary-vol1",
        toc_pages="2-3",
        data_root=data_dir,
        client=mock_client,
        model="gpt-4o",
    )

    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs.get("model") == "gpt-4o"


def test_run_toc_prints_confirmation_prompt(sample_pdf, tmp_path, capsys):
    from indexer.run import run_toc

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_api_response(SAMPLE_LESSONS)

    data_dir = str(tmp_path / "data")
    run_toc(
        pdf_path=sample_pdf,
        volume="elementary-vol1",
        toc_pages="2-3",
        data_root=data_dir,
        client=mock_client,
    )

    captured = capsys.readouterr()
    assert "toc_confirmed" in captured.out
