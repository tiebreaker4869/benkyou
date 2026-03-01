# Plan: P0 Task 3 — Human Review of toc.json & Markdown Files

## Context

P0 Task 2 (`--step index`) is complete with 57 passing tests. Both textbook and workbook have been fully processed:

- `data/elementary-vol1/textbook/lesson_01~25.md` — 25 files
- `data/elementary-vol1/workbook/lesson_01~25.md` — 25 files
- `data/manifest.json` — both volumes recorded as `status: complete`

This phase is a human QA task, not a coding task.

---

## Checklist

### toc.json Confirmation

- [x] `data/elementary-vol1/textbook/toc.json` — `toc_confirmed: true`, 25 lessons
- [x] `data/elementary-vol1/workbook/toc.json` — `toc_confirmed: true`, 25 lessons

### Structural Checks (automated ad-hoc)

Quick script verified all 50 files against:
- YAML frontmatter fields present (`volume`, `lesson`, `type`, `title`)
- Textbook: all 5 sections present (`単語`, `文型`, `例文`, `会話`, `文法`)
- Workbook: `問題N` headers consecutive starting from 1

Result: **0 issues across 50 files**

### Human Spot-Check

- [x] Textbook content quality reviewed manually
- [x] Workbook exercise format reviewed manually
- [x] VLM-generated image description lines (e.g. `画像说明（中文）：...`) noted — acceptable as visual context placeholders
- [x] Workbook toc.json titles (`第X課`) accepted as-is (workbook has no standalone lesson titles)

---

## Outcome

P0 is complete. All data assets are ready for P1 (MCP Server).

| Volume | Type | Lessons | Status |
|--------|------|---------|--------|
| elementary-vol1 | textbook | 25 | ✅ reviewed |
| elementary-vol1 | workbook | 25 | ✅ reviewed |

---

## Next Step

**P1: MCP Server** — implement `list_volumes`, `list_lessons`, `get_section`, `get_lesson`, `lookup_word` using the `mcp` Python SDK, backed by the `data/` directory.
