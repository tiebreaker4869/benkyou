"""
Tests for the pdf_to_images module.

Creates a minimal in-memory PDF using pymupdf — no mocking needed.
"""
import os

import fitz  # pymupdf
import pytest

from indexer.pdf_to_images import pdf_to_images


@pytest.fixture()
def sample_pdf(tmp_path) -> str:
    """Generate a simple 3-page PDF."""
    pdf_path = str(tmp_path / "sample.pdf")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_returns_correct_count(sample_pdf, tmp_path):
    output_dir = str(tmp_path / "pages")
    paths = pdf_to_images(sample_pdf, output_dir)
    assert len(paths) == 3


def test_files_exist_on_disk(sample_pdf, tmp_path):
    output_dir = str(tmp_path / "pages")
    paths = pdf_to_images(sample_pdf, output_dir)
    for p in paths:
        assert os.path.isfile(p), f"Missing image file: {p}"


def test_naming_convention(sample_pdf, tmp_path):
    output_dir = str(tmp_path / "pages")
    paths = pdf_to_images(sample_pdf, output_dir)
    basenames = [os.path.basename(p) for p in paths]
    assert basenames == ["page_001.png", "page_002.png", "page_003.png"]


def test_output_dir_created_automatically(sample_pdf, tmp_path):
    output_dir = str(tmp_path / "nested" / "pages")
    assert not os.path.exists(output_dir)
    pdf_to_images(sample_pdf, output_dir)
    assert os.path.isdir(output_dir)


def test_files_are_valid_png(sample_pdf, tmp_path):
    output_dir = str(tmp_path / "pages")
    paths = pdf_to_images(sample_pdf, output_dir)
    for p in paths:
        with open(p, "rb") as f:
            header = f.read(8)
        assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{p} is not a valid PNG"
