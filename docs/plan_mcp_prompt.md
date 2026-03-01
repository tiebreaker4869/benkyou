# Plan: Add MCP Prompts for Browse and Practice Workflows

> **Status: Implemented and extended** (2026-03-01).
> Core plan completed as written. Additionally: `browse_lesson_flow` and `practice_lesson_flow`
> were added as parameter-free tools (compatible with all MCP clients); flow tools use
> discovery-based instructions (call `list_volumes`/`list_lessons` first) to prevent hallucinated
> volume names. Instruction text extracted into four module-level helpers as single source of truth.

## Context

Claude Desktop has no persistent instructions between sessions, so when users want to browse a lesson or practice exercises, Claude sometimes improvises instead of following the workflows defined in `docs/PRD.md` (§6). The fix is to add **MCP Prompts** to the server — these appear as slash commands in Claude Desktop (e.g. `/mcp__benkyou__browse_lesson`) and deliver explicit workflow instructions alongside the call, so Claude knows exactly what to do.

A known edge case: workbook questions sometimes contain image descriptions instead of real images (stored as `- 图片描述（中文）：...` or `**图片说明：...**`). Claude tends to skip these kind of problem since they feel it lacks image, but they carry real question content and must be shown to the user.

---

## Files to Modify

- **`mcp_server/server.py`** — add two `@server.prompt()` functions inside `create_server()`
- **`tests/test_mcp_server.py`** — add tests for the two new prompts

---

## Implementation

### 1. `mcp_server/server.py` — add two prompts inside `create_server()`

```python
@server.prompt()
def browse_lesson(volume: str, lesson: int) -> str:
    """Browse a full lesson (textbook)."""
    return f"""\
You are a Japanese tutor. The student wants to read lesson {lesson} from {volume}.

Steps:
1. Call get_lesson(volume="{volume}", lesson={lesson}, book_type="textbook").
2. Present the full content in order: 単語 → 文型 → 例文 → 会話 → 文法.
   Do NOT skip or summarise any section.
3. After presenting, invite the student to ask questions about any part.
"""

@server.prompt()
def practice_lesson(volume: str, lesson: int) -> str:
    """Interactive practice session for a lesson (workbook)."""
    return f"""\
You are a Japanese tutor. The student wants to practice lesson {lesson} from {volume}.

Steps:
1. Call get_question_structure(volume="{volume}", lesson={lesson}) to learn the total number of 問題.
2. For each 問題 in order (starting from 1):
   a. Call get_question(volume="{volume}", lesson={lesson}, question_num=N) and display the FULL content.
   b. IMPORTANT — some sub-questions contain image description text instead of a real image.
      Always display this content verbatim; never skip, hide, or omit it. It is part of the question.
   c. Wait for the student to answer all sub-questions before giving any feedback.
   d. Grade each sub-answer: correct → brief explanation; incorrect → correct answer + detailed explanation.
   e. Wait for the student to acknowledge, then move to the next 問題.
3. After all 問題 are done, give a brief summary of mistakes and suggestions.

Do NOT reveal answers before the student responds. Do NOT skip any 問題 or sub-question.
"""
```

### 2. `tests/test_mcp_server.py` — add three test cases

- `test_prompts_listed` — `asyncio.run(server.list_prompts())` returns both `browse_lesson` and `practice_lesson`
- `test_browse_lesson_prompt_contains_key_instructions` — call `get_prompt("browse_lesson", {"volume": "vol1", "lesson": "3"})`, assert result contains `get_lesson` and all five section names
- `test_practice_lesson_prompt_contains_image_instruction` — call `get_prompt("practice_lesson", {"volume": "vol1", "lesson": "3"})`, assert result contains `get_question_structure`, `get_question`, and the image description keywords

---

## Verification

```bash
# 1. Run tests
uv run pytest tests/test_mcp_server.py -v

# 2. Full suite — ensure nothing broke
uv run pytest tests/ -q

# 3. Manual: restart MCP server in Claude Desktop,
#    type / in the input box and confirm both prompts appear as slash commands
```