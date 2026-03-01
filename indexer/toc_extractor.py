import base64
import json

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a precise OCR assistant specializing in Japanese textbooks.
Extract the table of contents from the provided image(s) and return a JSON object.

Return format (JSON object, no markdown):
{
  "lessons": [
    {"lesson": 1, "title": "...", "page_start": 10, "page_end": 21},
    ...
  ]
}

Rules:
- "lesson" is an integer lesson number
- "title" is the full lesson title as it appears in the TOC (keep Japanese)
- "page_start" and "page_end" are integers and represent an inclusive page range
- "page_end" must be >= "page_start"
- If the TOC lists only lesson start pages, infer "page_end" using the next lesson start page minus 1
- For the last lesson, set "page_end" to the final page of that lesson inferred from TOC context
- Adjacent lessons must not overlap in page ranges
- Include every lesson listed in the TOC
- Output only the JSON object, no explanations
"""


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_toc(
    toc_image_paths: list[str],
    client: OpenAI,
    model: str = "gpt-5-mini-2025-08-07",
) -> list[dict]:
    """Send TOC page images to the VLM and return structured lesson list."""
    image_parts = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{_encode_image(p)}"},
        }
        for p in toc_image_paths
    ]

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": image_parts},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    return data["lessons"]