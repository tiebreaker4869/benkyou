"""Extract one lesson markdown from page images via VLM."""

from indexer.image_utils import encode_image


TEXTBOOK_PAGE_PROMPT = """\
You are extracting one textbook page for lesson assembly.
Return only markdown fragment from this single page.

Rules:
- Keep only these sections if present: 単語, 文型, 例文, 会話, 文法
- Do NOT output frontmatter
- Do NOT output the lesson H1 title
- Keep original order within this page
- If there is an image needed for understanding, add a short **Chinese** image description. The rationale is that the reader should be able to understand the text with the description.
"""

WORKBOOK_PAGE_PROMPT = """\
You are extracting one workbook page for lesson assembly.
Return only markdown fragment from this single page.

Rules:
- Keep exercise content and numbering as shown on this page
- Do NOT output frontmatter
- Do NOT output the lesson H1 title
- Keep original order within this page
- If there is an image needed for solving, add a short **Chinese** image description. The rationale is that the reader should be able to complete the problem with the description.
"""

TEXTBOOK_AGGREGATE_PROMPT = """\
You are merging page fragments into one complete lesson markdown.
Return only markdown (no explanations).

Use this structure exactly:
---
volume: {volume}
lesson: {lesson}
type: textbook
title: {title}
---

# 第{lesson}課 {title}

## 単語
| 単語 | 品詞 | 意味 |
|------|------|------|

## 文型

## 例文

## 会話

## 文法
### 语法点1
### 语法点2

Rules:
- Merge all fragments in page order
- Deduplicate repeated lines/sections
- Keep only one frontmatter and one H1
- Keep the image description in Chinese, not in Japanese. 
"""

WORKBOOK_AGGREGATE_PROMPT = """\
You are merging page fragments into one complete workbook lesson markdown.
Return only markdown (no explanations).

Use this structure exactly:
---
volume: {volume}
lesson: {lesson}
type: workbook
title: {title}
---

# 第{lesson}課 練習

## 問題1
题目内容

### (1)
### (2)

## 問題2
题目内容

Rules:
- Merge all fragments in page order
- Problem numbering must be consecutive
- Keep only one frontmatter and one H1
- Keep the image description in Chinese, not in Japanese. 
"""


def extract_lesson(
    image_paths: list[str],
    lesson: dict,
    volume: str,
    book_type: str,
    client,
    model: str = "gpt-5-mini-2025-08-07",
) -> str:
    """Extract page fragments first, then run one final aggregation call."""
    page_prompt_tpl = TEXTBOOK_PAGE_PROMPT if book_type == "textbook" else WORKBOOK_PAGE_PROMPT
    page_system_prompt = page_prompt_tpl

    aggregate_prompt_tpl = (
        TEXTBOOK_AGGREGATE_PROMPT if book_type == "textbook" else WORKBOOK_AGGREGATE_PROMPT
    )
    aggregate_system_prompt = aggregate_prompt_tpl.format(
        volume=volume,
        lesson=lesson["lesson"],
        title=lesson["title"],
    )

    chunks: list[str] = []
    for page_idx, image_path in enumerate(image_paths, start=1):
        image_parts = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encode_image(image_path)}"},
            }
        ]
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": page_system_prompt},
                {"role": "user", "content": image_parts},
            ],
        )
        chunks.append(f"## PAGE {page_idx}\n{response.choices[0].message.content}")

    aggregate_input = "\n\n".join(chunks)
    aggregate_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": aggregate_system_prompt},
            {"role": "user", "content": aggregate_input},
        ],
    )
    return aggregate_response.choices[0].message.content
