# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest tests/

# Run a single test file
uv run pytest tests/test_toc_extractor.py

# Run a single test by name
uv run pytest tests/test_run_index.py::test_run_index_aborts_when_toc_not_confirmed

# Run the indexer (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
python indexer/run.py --pdf inbox/book.pdf --volume elementary-vol1 --type textbook --step toc --toc-pages 3-5
python indexer/run.py --pdf inbox/book.pdf --volume elementary-vol1 --type textbook --step index
```

## Architecture

This is a Japanese textbook digitizer. The pipeline is:

```
PDF → indexer/ scripts → per-lesson Markdown files (data/) → MCP Server (mcp_server/)
```

Top-level layout:

```
benkyou/
  indexer/        # PDF → Markdown one-time scripts
  mcp_server/     # MCP Server
  mcp-client/     # Specialized client (future)
  data/           # Generated lesson files
  inbox/          # Input PDFs
```

### Indexer (`indexer/`)

One-time processing script with two sequential steps, both invoked via `indexer/run.py`:

**`--step toc`** (must run first):
1. `pdf_to_images.py` — renders all PDF pages to PNGs at `data/<volume>/<type>/_pages/`
2. User specifies TOC page range via `--toc-pages START-END` (1-indexed, inclusive)
3. `toc_extractor.py` — sends TOC page images to VLM, returns structured lesson list
4. `toc_writer.py` — writes `data/<volume>/<type>/toc.json` with `toc_confirmed: false`
5. **Human must manually set `toc_confirmed: true`** in toc.json before proceeding

**`--step index`** (runs after toc is confirmed):
1. `toc_reader.py` — reads and validates `toc.json`, aborts if `toc_confirmed` is not `true`
2. For each lesson: `lesson_extractor.py` sends page images to VLM in two passes:
   - Per-page pass: extract markdown fragment from each page individually
   - Aggregation pass: merge all fragments into a single structured lesson markdown
3. `lesson_writer.py` — writes `data/<volume>/<type>/lesson_NN.md`
4. `manifest_writer.py` — upserts entry in `data/manifest.json` keyed by (volume, type)
5. Lessons are processed in parallel (default 8 workers); each lesson retries up to 3× with exponential backoff

### MCP Server (`mcp_server/`)

Implemented in Python using the official `mcp` SDK. Four modules:

- `server.py` — entry point; registers all tools and starts stdio transport via `main()`
- `readers.py` — file reading utilities: `read_manifest()`, `read_toc()`, `read_lesson()`
- `question_parser.py` — parses workbook question structure with full-width alias normalization
- `dictionary.py` — local JMDict lookup via `jamdict` (offline, no HTTP required)

Exposes six tools:

| Tool | Signature | Purpose |
|------|-----------|---------|
| `list_volumes` | `()` | Reads manifest.json, returns all imported volumes with metadata |
| `list_lessons` | `(volume)` | Returns lesson numbers and titles for a volume |
| `get_lesson` | `(volume, lesson, type)` | Returns full lesson Markdown (textbook or workbook) |
| `get_question_structure` | `(volume, lesson)` | Returns workbook question metadata: total 問題 count and sub-question counts |
| `get_question` | `(volume, lesson, question_num)` | Returns a single 問題's full content |
| `lookup_word` | `(word)` | Looks up a Japanese word in JMDict, returns reading / POS / meanings |

**Starting the MCP server:**

```bash
# Default (data dir = ./data)
uv run python -m mcp_server.server

# Custom data directory (recommended when running from a different working directory)
uv run python -m mcp_server.server --data-dir /absolute/path/to/data
```

### Key CLI args

| Arg | Purpose |
|-----|---------|
| `--type` | `textbook` or `workbook` |
| `--toc-pages` | TOC page range e.g. `3-5` (required for `--step toc`) |
| `--page-base` | Offset added to TOC page numbers (use when TOC page numbers don't match PDF page numbers) |
| `--concurrency` | Parallel VLM workers for `--step index` (default 8) |
| `--model` | VLM model override (default `gpt-5-mini-2025-08-07`) |

### Data layout

```
data/
  manifest.json               # index of all processed volumes
  <volume>/
    <type>/
      _pages/                 # PNG renders of PDF pages (can be gitignored)
      toc.json                # human-confirmed TOC
      lesson_01.md            # per-lesson markdown with YAML frontmatter
      lesson_02.md
      ...
```

## Conventions

- **TDD**: write tests before implementation
- **Mock only at HTTP boundaries**: mock `client.chat.completions.create`; let file I/O and PDF rendering run real (use `tmp_path` + pymupdf fixtures)
- All code, comments and generated docs in **English**
- Default VLM model: `gpt-5-mini-2025-08-07`

## Output formats

**toc.json** — written by `write_toc`, read by `read_toc`:
```json
{
  "toc_confirmed": false,
  "confirmed_at": null,
  "lessons": [
    {"lesson": 1, "title": "第1課 これはほんです", "page_start": 10, "page_end": 21}
  ]
}
```

**manifest.json** — upserted by `manifest_writer`, read by `list_volumes`:
```json
[
  {
    "volume": "elementary-vol1",
    "type": "textbook",
    "source_pdf": "inbox/elementary-vol1.pdf",
    "generated_at": "2026-02-28",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  }
]
```

**lesson_NN.md** — YAML frontmatter + structured sections.

Textbook format:
```markdown
---
volume: elementary-vol1
lesson: 3
type: textbook
title: これはほんです
---

# 第3課 これはほんです

## 単語
| 単語 | 品詞 | 意味 |
| ---- | ---- | ---- |

## 文型

## 例文

## 会話

## 文法
### 语法点1
### 语法点2
```

Workbook format:
```markdown
---
volume: elementary-vol1
lesson: 3
type: workbook
title: これはほんです
---

# 第3課 練習

## 問題1
题目内容

### (1)
### (2)

## 問題2
题目内容
```

Problem numbering must be consecutive. Use `## 問題N` for 大题, `### (N)` for 小问. No mixed full-width digits or other formats.
