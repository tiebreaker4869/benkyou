# MCP Tool Reference

The MCP server exposes **8 tools** and **2 prompts**.

**Data tools** (6): retrieve lesson content and dictionary entries.  
**Workflow-flow tools** (2): no parameters — call these to start a browse or practice session. The returned instructions guide the model to first call `list_volumes()` / `list_lessons()` to discover the correct volume and lesson, then proceed. Works in any MCP client.  
**Prompts** (2): for MCP clients that support prompts as slash commands (e.g. Zed). Take `volume` and `lesson` as explicit parameters supplied by the user.

---

### `list_volumes`

Lists all imported volumes from `manifest.json`.

**Parameters:** none

**Example call:**
```
list_volumes()
```

**Example output:**
```json
[
  {
    "volume": "elementary-vol1",
    "type": "workbook",
    "source_pdf": "./inbox/jpbook-junior-1-workbook.pdf",
    "generated_at": "2026-02-28",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  },
  {
    "volume": "elementary-vol1",
    "type": "textbook",
    "source_pdf": "./inbox/jpbook-junior-1.pdf",
    "generated_at": "2026-02-28",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  },
  {
    "volume": "elementary-vol2",
    "type": "workbook",
    "source_pdf": "inbox/jpbook-junior-2-workbook.pdf",
    "generated_at": "2026-03-01",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  },
  {
    "volume": "elementary-vol2",
    "type": "textbook",
    "source_pdf": "inbox/jpbook-junior-2.pdf",
    "generated_at": "2026-03-01",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  }
]
```

---

### `list_lessons`

Returns lesson numbers and titles from the textbook TOC for a given volume.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `volume` | `string` | Volume identifier, e.g. `"elementary-vol1"` |

**Example call:**
```
list_lessons(volume="elementary-vol1")
```

**Example output:**
```json
[
  { "lesson": 1, "title": "第1課 初めまして" },
  { "lesson": 2, "title": "第2課 これはほんです" },
  ...
]
```

**Error behavior:** Raises a file-not-found error if the volume or its textbook `toc.json` does not exist.

---

### `get_lesson`

Returns the full Markdown content for a single lesson.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `volume` | `string` | Volume identifier, e.g. `"elementary-vol1"` |
| `lesson` | `integer` | Lesson number, e.g. `1` |
| `book_type` | `string` | `"textbook"` or `"workbook"` |

**Example call:**
```
get_lesson(volume="elementary-vol1", lesson=1, book_type="textbook")
```

**Example output** (truncated):
```markdown
---
volume: elementary-vol1
lesson: 1
type: textbook
title: 初めまして
---

# 第1課 初めまして

## 単語
| 単語 | 品詞 | 意味 |
|------|------|------|
| わたし（私） | 〈名〉 | 我 |
| がくせい（学生） | 〈名〉 | 学生 |
...

## 文型
...

## 例文
...

## 会話
...

## 文法
...
```

**Error behavior:** Raises a file-not-found error if the lesson file does not exist.

---

### `get_question_structure`

Returns the workbook question structure (total question count and sub-question counts per question) for a lesson. Use this to plan a step-by-step practice session before retrieving individual questions.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `volume` | `string` | Volume identifier, e.g. `"elementary-vol1"` |
| `lesson` | `integer` | Lesson number, e.g. `1` |

**Example call:**
```
get_question_structure(volume="elementary-vol1", lesson=1)
```

**Example output:**
```json
{
  "total": 4,
  "questions": [
    { "num": 1, "sub_count": 9 },
    { "num": 2, "sub_count": 5 },
    { "num": 3, "sub_count": 0 },
    { "num": 4, "sub_count": 4 }
  ]
}
```

`sub_count` is `0` for questions that have no `### (N)` sub-question headers.

**Error behavior:** Raises a file-not-found error if the workbook lesson file does not exist.

---

### `get_question`

Returns one complete question block (大題) from a workbook lesson by question number. The block includes the question prompt and all sub-questions.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `volume` | `string` | Volume identifier, e.g. `"elementary-vol1"` |
| `lesson` | `integer` | Lesson number, e.g. `1` |
| `question_num` | `integer` | Question number (1-indexed), e.g. `2` |

**Example call:**
```
get_question(volume="elementary-vol1", lesson=1, question_num=1)
```

**Example output:**
```markdown
## 問題1
1.

例：
（手帳）
- 图片描述（中文）：一本写着「手帳」的手册。

### (1)
- 图片描述（中文）：挂在支架上的墙钟或相框。
（　）

### (2)
...
```

**Error behavior:** Raises `ValueError: Question N not found` if the question number does not exist in the lesson. Full-width digits in the source Markdown (e.g. `問題１`) are normalized to half-width automatically.

---

### `lookup_word`

Looks up a Japanese word in the local offline JMDict database and returns its reading, part of speech, and meanings.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `word` | `string` | Japanese word to look up (kanji, kana, or mixed) |

**Example call:**
```
lookup_word(word="学生")
```

**Example output:**
```json
{
  "reading": "がくせい",
  "pos": ["noun (common) (futsuumeishi)"],
  "meanings": ["student"],
  "examples": []
}
```

**Example call (kana input):**
```
lookup_word(word="たべる")
```

**Example output:**
```json
{
  "reading": "たべる",
  "pos": ["Ichidan verb", "transitive verb"],
  "meanings": ["to eat"],
  "examples": []
}
```

**Not found:**
```json
null
```

**Behavior notes:**
- Uses a local `jamdict` database — no network access required.
- Returns only the **first** dictionary entry and the **first** sense when multiple exist.
- `examples` is always an empty list (reserved for future use).
- If the word has no kana form, the first kanji form is used as the reading.

---

### `browse_lesson_flow`

Call this tool when the student wants to **read or browse a lesson**. Takes no parameters — the returned instructions guide the model to first call `list_volumes()` and `list_lessons()` to confirm the correct volume and lesson number, then fetch and present the full textbook content (単語→文型→例文→会話→文法) without skipping any section.

**Parameters:** none

**Example call:**
```
browse_lesson_flow()
```

**Returns:** A plain-text instruction string the model follows to execute the browse workflow.

---

### `practice_lesson_flow`

Call this tool when the student wants to **practice or do exercises for a lesson**. Takes no parameters — the returned instructions guide the model to first call `list_volumes()` and `list_lessons()` to confirm the correct volume and lesson number, then run an interactive practice session: present each 問題 one by one, wait for answers, grade with explanations.

> **Note:** Some sub-questions contain image description text (e.g. `- 图片描述（中文）：…`) instead of a real image. The workflow instructions explicitly require this text to be shown verbatim — it is part of the question and must not be skipped.

**Parameters:** none

**Example call:**
```
practice_lesson_flow()
```

**Returns:** A plain-text instruction string the model follows to execute the practice workflow.

---

### Prompts: `browse_lesson` / `practice_lesson`

For MCP clients that support prompts as slash commands (currently **Zed**; Claude Desktop support is client-version dependent).

| Prompt | Parameters | Behaviour |
|---|---|---|
| `browse_lesson` | `volume`, `lesson` | Parameterized browse workflow injected at conversation start |
| `practice_lesson` | `volume`, `lesson` | Parameterized practice workflow injected at conversation start |

The user supplies `volume` and `lesson` via the slash command UI (no discovery step needed). The model then calls `get_lesson` / `get_question_structure` / `get_question` directly with the provided values.
