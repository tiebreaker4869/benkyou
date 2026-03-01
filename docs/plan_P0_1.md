# Plan: P0 Task 2 — `--step index` Implementation

## Context

P0 Task 1 (toc generation) is complete with 26 passing tests. The next phase is `--step index`: read the confirmed toc.json, send each lesson's pages to a VLM for OCR + structured Markdown output, write per-lesson `.md` files, and update `manifest.json`. Currently `run.py:88-90` stubs this with a `sys.exit(1)`.

---

## Scope

Implement 4 new modules + extend `run.py`, all TDD with tests written first:

```
indexer/
  toc_reader.py       ← new
  lesson_extractor.py ← new
  lesson_writer.py    ← new
  manifest_writer.py  ← new
  run.py              ← extend run_index() + main()

tests/
  test_toc_reader.py
  test_lesson_extractor.py
  test_lesson_writer.py
  test_manifest_writer.py
  test_run_index.py
```

Output layout:
```
data/
  manifest.json
  {volume}/
    toc.json         ← already exists after --step toc
    _pages/          ← already rendered
    textbook/
      lesson_01.md
      lesson_02.md
      ...
    workbook/
      lesson_01.md
```

---

## Checkpoints

### Checkpoint 1 — `toc_reader.py`

**Function:** `read_toc(toc_path: str) -> dict`

Behavior:
- Returns the full toc dict (including `lessons` list) if `toc_confirmed` is `True`
- Raises `ValueError("toc not confirmed")` if `toc_confirmed` is falsy
- Raises `FileNotFoundError` naturally if file is missing

**Tests (`test_toc_reader.py`, ~4 tests):**
1. Happy path: writes a confirmed toc.json with tmp_path, reads back lessons
2. `toc_confirmed: false` → raises `ValueError`
3. Missing file → raises `FileNotFoundError`
4. Returns correct lesson count and fields

---

### Checkpoint 2 — `lesson_extractor.py`

**Function:**
```python
def extract_lesson(
    image_paths: list[str],
    lesson: dict,       # {lesson: N, title: "...", page_start: X, page_end: Y}
    volume: str,
    book_type: str,     # "textbook" or "workbook"
    client,
    model: str = "gpt-5-mini-2025-08-07",
) -> str
```

Behavior:
- Builds a system prompt specifying the Markdown structure (textbook vs workbook format from PRD §4.5)
- Encodes each image as base64, sends all in a single API call (`response_format` = text)
- Returns the VLM response string (expected Markdown with frontmatter)

System prompt includes:
- Frontmatter schema: `volume`, `lesson`, `type`, `title`
- Textbook sections: `単語` (3-col table: 単語/品詞/意味), `文型`, `例文`, `会話`, `文法` with sub-headers
- Workbook sections: `問題N` / `### (N)` subproblems; enforce consecutive numbering

**Tests (`test_lesson_extractor.py`, ~5 tests):**
Mock only `client.chat.completions.create`.
1. Returns a string
2. Makes exactly one API call
3. API call contains correct number of image messages (one per page)
4. `book_type="textbook"` vs `"workbook"` produces different system prompts
5. `model` parameter is passed through to the API

---

### Checkpoint 3 — `lesson_writer.py`

**Functions:**
```python
def lesson_output_path(data_root: str, volume: str, book_type: str, lesson_num: int) -> str
def write_lesson(markdown: str, output_path: str) -> None
```

`lesson_output_path` returns e.g. `data/elementary-vol1/textbook/lesson_01.md`
(zero-padded 2 digits; no padding beyond 2 since Minna no Nihongo has ≤50 lessons)

`write_lesson` writes the string, creating parent dirs automatically.

**Tests (`test_lesson_writer.py`, ~4 tests):**
Pure file I/O, no mocking.
1. `lesson_output_path` returns correct path for textbook (lesson 3 → `lesson_03.md`)
2. `lesson_output_path` returns correct path for workbook
3. `write_lesson` creates file with correct content
4. `write_lesson` creates parent directories automatically

---

### Checkpoint 4 — `manifest_writer.py`

**Function:** `write_manifest(manifest_path: str, entry: dict) -> None`

Behavior:
- If `manifest.json` doesn't exist → create it as `[entry]`
- If exists → load list, find entry with same `(volume, type)` key, replace it; append if not found
- Writes UTF-8, `ensure_ascii=False`, pretty-printed

Entry shape (mirrors PRD §4.4):
```json
{
  "volume": "...",
  "type": "textbook",
  "source_pdf": "...",
  "generated_at": "2025-02-27",
  "model": "gpt-5-mini-2025-08-07",
  "lessons": 25,
  "status": "complete"
}
```

**Tests (`test_manifest_writer.py`, ~5 tests):**
Pure file I/O.
1. Creates manifest.json with one entry when file absent
2. Appends a new entry (different volume)
3. Updates in-place when `(volume, type)` matches
4. Does not clobber other entries when updating
5. Japanese chars not ASCII-escaped

---

### Checkpoint 5 — `run_index()` in `run.py`

**New CLI arg:** `--page-base` (integer, default `0`, only used with `--step index`)

Page index formula: to get toc page `k` (1-indexed), use PDF page index `pb + k - 1` (0-indexed).

**Function:**
```python
def run_index(
    pdf_path: str,
    volume: str,
    book_type: str,
    data_root: str,
    page_base: int,
    client,
    model: str,
) -> None
```

Logic:
1. `toc_path = data_root/{volume}/{book_type}/toc.json`; call `read_toc()` → abort with message if `ValueError`
2. `pages_dir = data_root/{volume}/{book_type}/_pages`; list all PNGs sorted
3. For each lesson in `toc["lessons"]`:
   - `start_idx = page_base + lesson["page_start"] - 1`
   - `end_idx   = page_base + lesson["page_end"]`   (exclusive, so slice `[start_idx:end_idx]`)
   - Call `extract_lesson(all_pages[start_idx:end_idx], ...)`
   - Call `write_lesson(markdown, lesson_output_path(...))`
   - Print progress
4. Build manifest entry, call `write_manifest(data_root/manifest.json, entry)`
5. Print summary

Wire into `main()`: replace the stub at line 88-90 with a call to `run_index()`.

**Tests (`test_run_index.py`, ~6 tests):**
Mock only `client.chat.completions.create`.
1. Aborts cleanly when `toc_confirmed` is false (no VLM calls)
2. Calls VLM once per lesson (N lessons → N API calls)
3. With `page_base=0`: correct pages are sent per lesson (verify via captured call args)
4. With `page_base=5`: page slicing shifts by 5 correctly
5. Creates lesson markdown files at correct paths
6. Creates `manifest.json` with correct entry

---

## Critical Files

| File | Role |
|------|------|
| `indexer/run.py` | Extend `run_index()`, update `main()` |
| `indexer/toc_extractor.py` | Reference: `_encode_image()` helper to reuse in `lesson_extractor.py` |
| `indexer/toc_writer.py` | Reference: UTF-8 / `ensure_ascii=False` pattern to reuse |
| `docs/PRD.md` | §4.5 Markdown structure spec, §4.4 manifest format |

Reuse `_encode_image()` from `toc_extractor.py` — extract it to a shared helper or import it directly in `lesson_extractor.py`.

---

## Verification

```bash
# Run all tests (should go from 26 → ~46 passing)
uv run pytest tests/

# Manual smoke test (requires confirmed toc.json and OPENAI_API_KEY)
python indexer/run.py \
  --pdf inbox/jpbook-junior-1.pdf \
  --volume elementary-vol1 \
  --type textbook \
  --step index

# Check outputs
ls data/elementary-vol1/textbook/
cat data/elementary-vol1/textbook/lesson_01.md
cat data/manifest.json
```
