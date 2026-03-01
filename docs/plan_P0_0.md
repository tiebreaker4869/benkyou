# P0 Task 1 Implementation Plan: Indexer - PDF to Images + VLM TOC Extraction + Generate toc.json

## Context

benkyou is a tool for digitizing Japanese textbook PDFs. The first P0 task is to implement the first stage of the Indexer:
convert each PDF page into an image, use a VLM (GPT-5 mini) to recognize user-specified table-of-contents pages, and generate `toc.json` for manual confirmation.
This is the entry point of the entire data processing pipeline, and the later `--step index` stage depends on this file.

Current status: the project has just been initialized, with only a placeholder `main.py`; the `indexer/` directory does not exist yet, and no dependencies are installed.

---

## Subtasks and Checkpoints

### Subtask 1: Environment Setup

**Goal:** Create the directory structure and install dependencies.

**Tasks:**
- Create `indexer/` and `inbox/` directories
- Add dependencies in `pyproject.toml`: `pymupdf`, `openai`
- Create `indexer/__init__.py` (empty file)

**Key file:** `pyproject.toml`

**✅ Checkpoint 1: Dependencies are importable**
```bash
uv sync
python -c "import fitz; import openai; print('OK')"
```
Expected output: `OK`, with no ImportError.

---

### Subtask 2: PDF-to-Image Module

**Goal:** Implement a function that renders each PDF page into a PNG image.

**Tasks:**
- Create `indexer/pdf_to_images.py`
- Implement function: `pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 150) -> list[str]`
  - Open the PDF with `pymupdf` (`import fitz`) and render page by page
  - Naming convention: `page_001.png`, `page_002.png`, ...
  - Return the list of image paths

**✅ Checkpoint 2: Images are generated correctly**
```bash
python -c "
from indexer.pdf_to_images import pdf_to_images
paths = pdf_to_images('inbox/test.pdf', '/tmp/test_pages')
print(f'Generated {len(paths)} images')
print('First image:', paths[0])
"
```
Expected: `Generated N images`, where `N` equals the PDF page count; corresponding PNG files exist under `/tmp/test_pages/`.

---

### Subtask 3: VLM TOC Extraction Module

**Goal:** Let the user specify the TOC page range with `--toc-pages`, send those images to GPT-5 mini, and extract lesson-to-page mappings.

**Tasks:**
- Create `indexer/toc_extractor.py`
- Implement function:
  - `extract_toc(toc_image_paths: list[str], client: OpenAI) -> list[dict]`
    - Send the input TOC images to the VLM and request structured JSON output
    - Output format: `[{"lesson": 1, "title": "...", "page_start": N, "page_end": M}, ...]`
    - Use `response_format={"type": "json_object"}` to enforce JSON output

**Prompt design notes:**
- Explicitly require JSON output
- Clearly describe TOC structure (lesson number, title, page range)

**✅ Checkpoint 3: VLM returns structured data**
```bash
python -c "
import os; from openai import OpenAI
from indexer.toc_extractor import extract_toc
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
# Assume TOC is on page 3 (0-indexed: 2)
image_paths = ['/tmp/test_pages/page_003.png']
lessons = extract_toc(image_paths, client)
print('Detected lessons:', len(lessons))
print('First lesson:', lessons[0])
"
```
Expected: `lessons` is a non-empty list, and each item contains `lesson`, `title`, `page_start`, and `page_end`.

---

### Subtask 4: Write toc.json

**Goal:** Write VLM output into the standard `toc.json` format.

**Tasks:**
- Create `indexer/toc_writer.py`
- Implement function: `write_toc(lessons: list[dict], output_path: str) -> None`
  - Write data in PRD section 4.3 format: `toc_confirmed: false`, `confirmed_at: null`, `lessons: [...]`
  - Output path: `data/<volume>/toc.json` (provided by caller)
  - Use `json.dump` with proper encoding (`ensure_ascii=False`, `indent=2`)

**✅ Checkpoint 4: toc.json format is valid**
```bash
python -c "
import json
with open('data/elementary-vol1/toc.json') as f:
    toc = json.load(f)
assert toc['toc_confirmed'] == False
assert toc['confirmed_at'] is None
assert len(toc['lessons']) > 0
lesson = toc['lessons'][0]
assert all(k in lesson for k in ['lesson', 'title', 'page_start', 'page_end'])
print('toc.json validation passed, total lessons:', len(toc['lessons']))
"
```
Expected: no AssertionError; total lesson count is printed.

---

### Subtask 5: CLI Entry `--step toc`

**Goal:** Chain all modules above into a usable command-line tool.

**Tasks:**
- Create `indexer/run.py`
- Implement arguments with `argparse`: `--pdf`, `--volume`, `--type`, `--step`, `--toc-pages` (only `toc` in this phase)
  - `--toc-pages`: TOC page range in format `3-5` (1-indexed, inclusive)
- Execution order for `--step toc`:
  1. Call `pdf_to_images()` to generate images (store in `data/<volume>/_pages/`)
  2. Filter the corresponding page images based on `--toc-pages`
  3. Call `extract_toc()` to detect lesson-to-page mappings
  4. Call `write_toc()` to write `data/<volume>/toc.json`
  5. Print output path and lesson count, and prompt user to verify

**✅ Checkpoint 5 (Final Acceptance): End-to-end flow runs successfully**
```bash
export OPENAI_API_KEY=sk-...
python indexer/run.py \
  --pdf inbox/elementary-vol1.pdf \
  --volume elementary-vol1 \
  --type textbook \
  --step toc \
  --toc-pages 3-5
```
Expected results:
1. Command finishes successfully without abnormal exit
2. Per-page PNG files exist under `data/elementary-vol1/_pages/`
3. `data/elementary-vol1/toc.json` exists, is valid JSON, and has a non-empty `lessons` field
4. Terminal prints a prompt such as: "Please review toc.json and set toc_confirmed to true once verified"

---

## File Structure Overview

```
benkyou/
  indexer/
    __init__.py
    run.py            # CLI entry
    pdf_to_images.py  # PDF -> images
    toc_extractor.py  # VLM TOC extraction (user-specified TOC page range)
    toc_writer.py     # Write toc.json
  inbox/              # Input PDFs to process
  data/
    elementary-vol1/
      _pages/         # Temporary images (can be gitignored)
      toc.json        # Pending manual confirmation
  pyproject.toml      # Added dependencies
```

## Dependencies

| Package | Purpose |
|----|------|
| `pymupdf` | PDF rendering (`import fitz`) |
| `openai` | Call GPT-5 mini Vision API |

## Out of Scope for This Phase

- `--step index` (TOC confirmation + per-lesson OCR): P0 task 2
- `manifest.json` generation: P0 task 2
- MCP Server: P1