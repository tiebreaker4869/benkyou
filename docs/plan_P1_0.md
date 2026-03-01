# P1 Task 1 Implementation Plan: MCP Server + Tools (with Section Alias Normalization)

## Context

P0 is complete: textbook + workbook each have 25 lessons generated, `data/manifest.json` is ready.
This plan implements PRD Section 9, P1 item 1: **MCP Server setup + tools implementation (with section alias normalization)**.

Current state:
- `mcp-server/` directory does not exist
- `mcp` SDK not yet installed
- All 6 tools need to be implemented from scratch

---

## Target Directory Structure

```
mcp-server/
  __init__.py
  server.py          # MCP entry point, registers tools, starts stdio server
  readers.py         # File reading utilities (manifest / toc / lesson)
  question_parser.py # Parses workbook question structure (with alias normalization)
  dictionary.py      # lookup_word via jisho.org API
tests/
  test_mcp_readers.py
  test_mcp_question_parser.py
  test_mcp_lookup_word.py
  test_mcp_server.py
```

## Section Alias Normalization

VLM-generated markdown may use full-width digits (`問題１`) or half-width (`問題1`), and full-width parentheses (`（1）`) or half-width (`(1)`). `question_parser.py` normalizes all to half-width before parsing.

## Data Flow

```
MCP Client (Claude Desktop)
        │ stdio
        ▼
  server.py (mcp SDK)
   ├── readers.py ──► data/manifest.json
   │               ├► data/<volume>/<type>/toc.json
   │               └► data/<volume>/<type>/lesson_NN.md
   ├── question_parser.py
   └── dictionary.py ──► https://jisho.org/api/v1/search/words
```

---

## Checkpoint 1: Environment Setup

**Goal**: Add `mcp` dependency, create `mcp-server/` skeleton.

**Changes**:
- [`pyproject.toml`](../pyproject.toml): add `mcp>=1.0.0` (pulls in `httpx` transitively)
- Create `mcp-server/__init__.py` (empty)
- Create `mcp-server/server.py` (only `mcp.Server` instantiation, no tools yet)

**Verification**:
```bash
uv sync
uv run python -c "import mcp; print('OK')"
uv run python -c "from mcp_server.server import create_server; print('OK')"
```

---

## Checkpoint 2: readers.py + First Three Tools (list_volumes / list_lessons / get_lesson)

**TDD order**: write `tests/test_mcp_readers.py` first, then implement.

**Test cases (`test_mcp_readers.py`)**:
- `test_read_manifest_returns_list`: reads `tmp_path/manifest.json`, asserts correct fields returned
- `test_read_manifest_missing_file`: raises `FileNotFoundError` when file does not exist
- `test_read_toc_returns_lessons`: reads `toc.json`, returns lesson list
- `test_read_lesson_returns_content`: reads `lesson_01.md`, returns markdown string
- `test_read_lesson_not_found`: raises `FileNotFoundError` when lesson does not exist

**Implementation (`readers.py`)**:
```python
def read_manifest(data_dir: str) -> list[dict]: ...
def read_toc(data_dir: str, volume: str, type_: str) -> dict: ...
def read_lesson(data_dir: str, volume: str, type_: str, lesson: int) -> str: ...
```

**Tool registration (`server.py`)**:
- `list_volumes()` → calls `read_manifest()`, returns volume list
- `list_lessons(volume)` → reads textbook `toc.json`, returns `{lesson, title}` list
- `get_lesson(volume, lesson, type)` → calls `read_lesson()`, lesson zero-padded to two digits (`lesson_NN.md`)

**Verification**:
```bash
uv run pytest tests/test_mcp_readers.py -v
```

---

## Checkpoint 3: question_parser.py + get_question_structure / get_question

**TDD order**: write `tests/test_mcp_question_parser.py` first, then implement.

**Test cases (`test_mcp_question_parser.py`)**:
- `test_parse_structure_basic`: markdown with 3 問題 each having sub-questions → `{total: 3, questions: [{num:1, sub_count:3}, ...]}`
- `test_parse_fullwidth_digits`: input `## 問題１` (full-width) treated identically to `## 問題1`
- `test_parse_fullwidth_parens`: input `### （1）` (full-width parens) treated identically to `### (1)`
- `test_get_question_returns_block`: extracts 問題2's full content (from `## 問題2` up to next `## 問題3`)
- `test_get_question_out_of_range`: raises `ValueError` when requested question number does not exist

**Implementation (`question_parser.py`)**:
```python
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
FULLWIDTH_PARENS = str.maketrans("（）", "()")

def normalize(text: str) -> str:
    return text.translate(FULLWIDTH_DIGITS).translate(FULLWIDTH_PARENS)

def parse_question_structure(markdown: str) -> dict: ...
def extract_question(markdown: str, question_num: int) -> str: ...
```

**Tool registration (`server.py`)**:
- `get_question_structure(volume, lesson)` → reads workbook `lesson_NN.md`, calls `parse_question_structure()`
- `get_question(volume, lesson, question_num)` → reads workbook `lesson_NN.md`, calls `extract_question()`

**Verification**:
```bash
uv run pytest tests/test_mcp_question_parser.py -v
```

---

## Checkpoint 4: dictionary.py + lookup_word

**TDD order**: write `tests/test_mcp_lookup_word.py` (mock `Jamdict.lookup`) first, then implement.

**Library**: [`jamdict`](https://github.com/neocl/jamdict) — local offline access to JMDict data, no HTTP required.
Add to `pyproject.toml`: `jamdict>=0.1.0` and `jamdict-data>=0.1.0`.

Key API:
```python
from jamdict import Jamdict
jam = Jamdict()
result = jam.lookup("食べる")
# result.entries[0].kana_forms[0].text  → reading
# result.entries[0].senses[0].pos       → list of parts-of-speech
# result.entries[0].senses[0].gloss     → list of meanings (SenseGloss objects)
```

**Test cases (`test_mcp_lookup_word.py`)**:
- `test_lookup_word_success`: mock `Jamdict.lookup()` to return a fake result with one entry; assert returned dict has `reading / pos / meanings / examples`
- `test_lookup_word_not_found`: mock `Jamdict.lookup()` to return result with empty `entries`; assert returns `None`
- `test_lookup_word_kanji_fallback`: word has no kana form but has kanji form; assert `reading` falls back to kanji text

**Implementation (`dictionary.py`)**:
```python
from jamdict import Jamdict

_jam = Jamdict()

def lookup_word(word: str) -> dict | None:
    result = _jam.lookup(word)
    if not result.entries:
        return None
    entry = result.entries[0]
    if entry.kana_forms:
        reading = entry.kana_forms[0].text
    elif entry.kanji_forms:
        reading = entry.kanji_forms[0].text
    else:
        reading = ""
    senses = entry.senses
    return {
        "reading": reading,
        "pos": [str(p) for p in senses[0].pos] if senses else [],
        "meanings": [str(g) for g in senses[0].gloss] if senses else [],
        "examples": [],
    }
```

**Tool registration (`server.py`)**:
- `lookup_word(word)` → calls `dictionary.lookup_word(word)`, serializes result to string

**Verification**:
```bash
uv run pytest tests/test_mcp_lookup_word.py -v
```

---

## Checkpoint 5: Server Integration + Full Test Suite

**Test cases (`test_mcp_server.py`)**:
- `test_server_has_six_tools`: instantiate server, assert 6 tools are registered with names matching PRD
- `test_list_volumes_integration`: use real `data/manifest.json`, call `list_volumes`, assert non-empty result
- `test_get_lesson_integration`: use real `data/elementary-vol1/textbook/lesson_01.md`, assert markdown returned

**Full test suite verification**:
```bash
uv run pytest tests/ -v
```

Expected: all pass (P0 original tests + P1 new tests).

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `pyproject.toml` | Add `mcp` dependency |
| `mcp-server/server.py` | Entry point + 6 tool registrations |
| `mcp-server/readers.py` | manifest / toc / lesson file reading |
| `mcp-server/question_parser.py` | Question structure parsing + alias normalization |
| `mcp-server/dictionary.py` | JMDict lookup via `jamdict` (offline, no HTTP) |
| `tests/test_mcp_readers.py` | TDD tests for readers |
| `tests/test_mcp_question_parser.py` | TDD tests for question parser |
| `tests/test_mcp_lookup_word.py` | TDD tests for dictionary (mocked HTTP) |
| `tests/test_mcp_server.py` | Integration tests for server |
