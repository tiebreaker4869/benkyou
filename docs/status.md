# Project Status Snapshot

> Last updated: 2026-03-01

---

## Overall Status

The full end-to-end pipeline is **complete and operational**:

- **Indexer**: All 8 modules implemented and tested. `elementary-vol1` (textbook + workbook, 25 lessons each) has been fully processed and written to `data/`.
- **MCP Server**: All 6 tools implemented, registered, and tested. Server starts over stdio transport and is ready to connect to Claude Desktop.

---

## Module Inventory

### Indexer (`indexer/`)

| Module | Status | Purpose |
|---|---|---|
| `run.py` | Complete | CLI entry point; orchestrates `run_toc()` and `run_index()` |
| `pdf_to_images.py` | Complete | Renders PDF pages to PNG via `pymupdf` at 150 DPI |
| `toc_extractor.py` | Complete | Sends TOC page images to VLM; returns structured lesson list |
| `toc_writer.py` | Complete | Writes `toc.json` with `toc_confirmed: false` |
| `toc_reader.py` | Complete | Reads and validates `toc.json`; aborts if not confirmed |
| `lesson_extractor.py` | Complete | Two-pass VLM extraction (per-page + aggregation) |
| `lesson_writer.py` | Complete | Writes `lesson_NN.md` per lesson |
| `manifest_writer.py` | Complete | Upserts entry in `data/manifest.json` by (volume, type) |

### MCP Server (`mcp_server/`)

| Module | Status | Purpose |
|---|---|---|
| `server.py` | Complete | Registers 6 tools via FastMCP; starts stdio transport |
| `readers.py` | Complete | File readers for manifest, toc, and lesson markdown |
| `question_parser.py` | Complete | Parses workbook structure; normalizes full-width characters |
| `dictionary.py` | Complete | Offline JMDict lookup via `jamdict` singleton |

---

## Data State

| Volume | Type | Lessons Generated | Status |
|---|---|---|---|
| `elementary-vol1` | `textbook` | 25 | complete |
| `elementary-vol1` | `workbook` | 25 | complete |

- `data/manifest.json`: 2 entries (one per type), both `"status": "complete"`
- Page images (`data/elementary-vol1/*/\_pages/`) are present but can be gitignored
- TOC files confirmed: both `data/elementary-vol1/textbook/toc.json` and `data/elementary-vol1/workbook/toc.json` have `toc_confirmed: true`

---

## Test Coverage

13 test files covering every module:

| Test File | Module Covered | Strategy |
|---|---|---|
| `test_pdf_to_images.py` | `pdf_to_images.py` | Real `pymupdf`, `tmp_path` |
| `test_toc_extractor.py` | `toc_extractor.py` | Mock `client.chat.completions.create` |
| `test_toc_writer.py` | `toc_writer.py` | Real file I/O, `tmp_path` |
| `test_toc_reader.py` | `toc_reader.py` | Real file I/O |
| `test_run_toc.py` | `run.py run_toc()` | Mock VLM |
| `test_run_index.py` | `run.py run_index()` | Mock VLM |
| `test_lesson_extractor.py` | `lesson_extractor.py` | Mock VLM |
| `test_lesson_writer.py` | `lesson_writer.py` | Real file I/O |
| `test_manifest_writer.py` | `manifest_writer.py` | Real file I/O |
| `test_mcp_readers.py` | `readers.py` | Real file I/O, `tmp_path` |
| `test_mcp_question_parser.py` | `question_parser.py` | Pure function, no mocks |
| `test_mcp_lookup_word.py` | `dictionary.py` | Mock `_jam` singleton |
| `test_mcp_server.py` | `server.py` | Integration, partial real `data/` |

---

## Dependencies

From `pyproject.toml` (Python ≥ 3.12, managed with `uv`):

| Package | Purpose |
|---|---|
| `pymupdf >= 1.24.0` | PDF rendering (indexer) |
| `openai >= 1.0.0` | VLM API client (indexer) |
| `mcp >= 1.0.0` | Official MCP Python SDK (`FastMCP`) |
| `jamdict` + `jamdict-data` | Local offline JMDict dictionary |
| `pytest >= 8.0.0` | Test runner (dev dependency) |

---

## Known Deviations from Plan

| Area | Planned (`plan_P1_0.md`) | Actual Implementation |
|---|---|---|
| Dictionary backend | `jisho.org` HTTP API | `jamdict` local offline (no network required) |
| Server module path | `mcp-server/` | `mcp_server/` (Python package naming) |
| Default VLM model | `gpt-4o-mini` | `gpt-5-mini-2025-08-07` |

---

## Known Limitations

- `lookup_word` returns only the **first** JMDict entry; multi-sense words are truncated to the first sense.
- `examples` field in `lookup_word` response is always an empty list (reserved for future extension).
- Workbook image content is represented as **Chinese text descriptions** (e.g., `图片描述（中文）：一本写着「手帳」的手册。`) rather than actual images, since VLM output is text-only.
- `list_lessons` always reads from `textbook` TOC; workbook-only navigation is not directly supported via this tool.
- No lesson progress tracking or user state persistence.
