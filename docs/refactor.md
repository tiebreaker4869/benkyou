# Refactor Notes

Code review findings. Ordered by priority.

---

## High Priority

### 1. Integration tests hard-depend on real `data/` directory

**File:** `tests/test_mcp_server.py:37-58`

`test_list_volumes_integration` and `test_get_lesson_integration` call `create_server(data_dir="data")` and read actual files from disk. On a fresh clone or in CI without processed data, both tests fail with `FileNotFoundError`. Every other test uses `tmp_path` to construct fixture data — these two are the exception. Fix: use `tmp_path` to write a minimal `manifest.json` and `lesson_01.md`, same pattern as `test_mcp_readers.py`.

### 2. `type` shadows Python builtin in `server.py`

**File:** `mcp_server/server.py:46`

```python
def get_lesson(volume: str, lesson: int, type: str) -> str:
```

`type` is a Python builtin. Rename to `book_type` or `type_` — consistent with `indexer/run.py` which already uses `dest="book_type"`.

---

## Medium Priority

### 3. `_encode_image` is duplicated across two modules

**Files:** `indexer/toc_extractor.py:31-33`, `indexer/lesson_extractor.py:96-98`

Identical function in both files:

```python
def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
```

Extract to `indexer/image_utils.py` and import from both.

### 4. `question_parser.py` duplicates its core parse logic

**File:** `mcp_server/question_parser.py`

Both `parse_question_structure` and `extract_question` independently do: `normalize → QUESTION_HEADER_RE.finditer → slice between matches`. Extract a shared helper:

```python
def _split_questions(markdown: str) -> list[tuple[int, str]]:
    """Returns [(question_num, block_text), ...]."""
```

Both public functions delegate to it. Currently only ~10 lines of duplication, but the shared logic will grow if alias normalization is extended.

---

## Low Priority

### 5. Retry test actually sleeps

**File:** `tests/test_run_index.py::test_run_index_retries_transient_failure`

`run_index` defaults to `retry_base_delay=0.2`, so the retry test sleeps 200ms+. Either pass `retry_base_delay=0` in the test call, or patch `time.sleep`. The parameter is already injectable — just not used in the test.

### 6. `os.path` vs `pathlib` inconsistency

`indexer/` uses `os.path` throughout; `mcp_server/readers.py` uses `pathlib.Path`. Not a bug, but mixing both in one project adds friction. The most awkward spot is `run.py:109-113`:

```python
# current
all_pages = sorted(
    os.path.join(pages_dir, f)
    for f in os.listdir(pages_dir)
    if f.lower().endswith(".png")
)

# with pathlib
all_pages = sorted(str(p) for p in Path(pages_dir).glob("*.png"))
```

### 7. `Jamdict()` initializes at import time

**File:** `mcp_server/dictionary.py:5`

`_jam = Jamdict()` runs when the module is first imported, loading the JMDict database immediately. Tests patch `_jam` directly so there's no functional problem. If the test suite is ever split or run in parallel, import-time side effects can cause unexpected slowdowns. Consider lazy initialization:

```python
_jam = None

def _get_jam() -> Jamdict:
    global _jam
    if _jam is None:
        _jam = Jamdict()
    return _jam
```

---

## Implementation Plan

Each checkpoint is independently verifiable with `uv run pytest tests/`. Items within the same checkpoint can be done in any order; checkpoints must be done in sequence.

---

### Checkpoint 1 — Fix high-priority issues (no behavior change)

**Goal:** All tests pass on a fresh clone with no `data/` directory.

Tasks:
- **#2** Rename `type` → `book_type` in `mcp_server/server.py:46`. Update the MCP tool signature; the FastMCP framework picks up the parameter name for the tool schema, so also verify the tool still works end-to-end.
- **#1** Rewrite `test_list_volumes_integration` and `test_get_lesson_integration` in `tests/test_mcp_server.py` to use `tmp_path` instead of the real `data/` directory. Model after the fixture setup in `tests/test_mcp_readers.py`.

**Verify:**
```bash
# Must pass in a clean environment with no data/ present
uv run pytest tests/test_mcp_server.py -v
```

---

### Checkpoint 2 — Eliminate `_encode_image` duplication

**Goal:** Single source of truth for base64 image encoding in the indexer.

Tasks:
- **#3** Create `indexer/image_utils.py` with the shared `encode_image(path: str) -> str` function (drop the leading underscore since it's now a public API of the module).
- Remove `_encode_image` from `indexer/toc_extractor.py` and `indexer/lesson_extractor.py`; import `encode_image` from `indexer.image_utils` in both.

**Verify:**
```bash
uv run pytest tests/test_toc_extractor.py tests/test_lesson_extractor.py tests/test_run_toc.py tests/test_run_index.py -v
```

---

### Checkpoint 3 — Refactor `question_parser.py` internals

**Goal:** Single parse path for question-block splitting.

Tasks:
- **#4** Extract `_split_questions(markdown: str) -> list[tuple[int, str]]` inside `mcp_server/question_parser.py`.
- Rewrite `parse_question_structure` and `extract_question` to delegate to it.
- Public signatures and return values must not change.

**Verify:**
```bash
uv run pytest tests/test_mcp_question_parser.py -v
```

---

### Checkpoint 4 — Fix low-priority issues

**Goal:** Faster test suite, no import-time side effects, consistent file-path style.

Tasks:
- **#5** In `tests/test_run_index.py::test_run_index_retries_transient_failure`, pass `retry_base_delay=0` to `run_index(...)` so the test doesn't sleep.
- **#7** Make `Jamdict` lazy in `mcp_server/dictionary.py`: replace the module-level `_jam = Jamdict()` with a `_get_jam()` helper; update `lookup_word` to call `_get_jam()`. Update the `@patch` target in `tests/test_mcp_lookup_word.py` if necessary.
- **#6** Migrate `indexer/run.py` page-listing logic (lines 109-113) from `os.listdir` to `pathlib.Path.glob`. No other files need to change; the rest of `indexer/` can stay on `os.path` for now.

**Verify:**
```bash
# Retry test should now be noticeably faster
uv run pytest tests/test_run_index.py::test_run_index_retries_transient_failure -v
uv run pytest tests/test_mcp_lookup_word.py -v
# Full suite green
uv run pytest tests/ -v
```

---

## Summary Table

| # | Issue | File(s) | Priority |
|---|-------|---------|----------|
| 1 | Integration tests depend on real `data/` | `test_mcp_server.py:37-58` | High |
| 2 | `type` shadows Python builtin | `server.py:46` | High |
| 3 | `_encode_image` duplicated | `toc_extractor.py`, `lesson_extractor.py` | Medium |
| 4 | `question_parser` internal logic duplicated | `question_parser.py` | Medium |
| 5 | Retry test sleeps 200ms+ | `test_run_index.py` | Low |
| 6 | `os.path` / `pathlib` inconsistency | `indexer/` vs `mcp_server/` | Low |
| 7 | `Jamdict` initialized at import time | `dictionary.py` | Low |
