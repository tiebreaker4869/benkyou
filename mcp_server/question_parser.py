"""Workbook question parsing with section alias normalization."""

import re

FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
FULLWIDTH_PARENS = str.maketrans("（）", "()")

QUESTION_HEADER_RE = re.compile(r"^##\s*問題(\d+)\s*$", re.MULTILINE)
SUBQUESTION_HEADER_RE = re.compile(r"^###\s*\((\d+)\)\s*$", re.MULTILINE)


def normalize(text: str) -> str:
    """Normalize full-width digits and parentheses to half-width."""
    return text.translate(FULLWIDTH_DIGITS).translate(FULLWIDTH_PARENS)


def parse_question_structure(markdown: str) -> dict:
    """Parse workbook markdown and return question/sub-question structure."""
    normalized = normalize(markdown)
    matches = list(QUESTION_HEADER_RE.finditer(normalized))
    questions: list[dict] = []

    for i, match in enumerate(matches):
        question_num = int(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
        block = normalized[start:end]
        sub_count = len(SUBQUESTION_HEADER_RE.findall(block))
        questions.append({"num": question_num, "sub_count": sub_count})

    return {"total": len(questions), "questions": questions}


def extract_question(markdown: str, question_num: int) -> str:
    """Extract one full question block by question number."""
    normalized = normalize(markdown)
    matches = list(QUESTION_HEADER_RE.finditer(normalized))

    for i, match in enumerate(matches):
        current_num = int(match.group(1))
        if current_num == question_num:
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
            return normalized[start:end].strip()

    raise ValueError(f"Question {question_num} not found")

