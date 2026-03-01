"""MCP server entry point."""

import argparse

from mcp.server.fastmcp import FastMCP

from mcp_server.dictionary import lookup_word as lookup_word_in_dict
from mcp_server.question_parser import extract_question, parse_question_structure
from mcp_server.readers import read_lesson, read_manifest, read_toc


def _browse_lesson_flow_instructions() -> str:
    """Return discovery-based tutor workflow for browsing a lesson (used by tool)."""
    return """\
You are a Japanese tutor. The student wants to read a lesson.

Steps:
1. Call list_volumes() to get the exact volume identifiers available.
2. If the student has not specified a volume, show the list and ask which one they want.
3. Call list_lessons(volume=<chosen_volume>) to confirm available lesson numbers and titles.
4. If the student has not specified a lesson, show the list and ask which one they want.
5. Call get_lesson(volume=<chosen_volume>, lesson=<chosen_lesson>, book_type="textbook").
6. Present the full content in order: 単語 → 文型 → 例文 → 会話 → 文法.
   Do NOT skip or summarise any section.
7. After presenting, invite the student to ask questions about any part.
"""


def _practice_lesson_flow_instructions() -> str:
    """Return discovery-based tutor workflow for practicing a lesson (used by tool)."""
    return """\
You are a Japanese tutor. The student wants to practice a lesson.

Steps:
1. Call list_volumes() to get the exact volume identifiers available.
2. If the student has not specified a volume, show the list and ask which one they want.
3. Call list_lessons(volume=<chosen_volume>) to confirm available lesson numbers and titles.
4. If the student has not specified a lesson, show the list and ask which one they want.
5. Call get_question_structure(volume=<chosen_volume>, lesson=<chosen_lesson>) to learn the total number of 問題.
6. For each 問題 in order (starting from 1):
   a. Call get_question(volume=<chosen_volume>, lesson=<chosen_lesson>, question_num=N) and display the FULL content.
   b. IMPORTANT — some sub-questions contain image description text instead of a real image.
      Always display this content verbatim; never skip, hide, or omit it. It is part of the question.
   c. Wait for the student to answer all sub-questions before giving any feedback.
   d. Grade each sub-answer: correct → brief explanation; incorrect → correct answer + detailed explanation.
   e. Wait for the student to acknowledge, then move to the next 問題.
7. After all 問題 are done, give a brief summary of mistakes and suggestions.

Do NOT reveal answers before the student responds. Do NOT skip any 問題 or sub-question.
"""


def _browse_lesson_instructions(volume: str, lesson: int) -> str:
    """Return parameterized tutor workflow for browsing a lesson (used by prompt)."""
    return f"""\
You are a Japanese tutor. The student wants to read lesson {lesson} from {volume}.

Steps:
1. Call get_lesson(volume="{volume}", lesson={lesson}, book_type="textbook").
2. Present the full content in order: 単語 → 文型 → 例文 → 会話 → 文法.
   Do NOT skip or summarise any section.
3. After presenting, invite the student to ask questions about any part.
"""


def _practice_lesson_instructions(volume: str, lesson: int) -> str:
    """Return parameterized tutor workflow for practicing a lesson (used by prompt)."""
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


def create_server(data_dir: str = "data") -> FastMCP:
    """Create and return the MCP server instance."""
    server = FastMCP(name="benkyou")

    @server.tool(
        description=(
            "List all available Japanese learning volumes (textbook/workbook) from "
            "the manifest so learners can choose what to study next."
        )
    )
    def list_volumes() -> list[dict]:
        """Return all imported volumes from manifest."""
        return read_manifest(data_dir)

    @server.tool(
        description=(
            "List lesson numbers and titles for a Japanese volume from the textbook "
            "TOC, so users can navigate lessons by topic."
        )
    )
    def list_lessons(volume: str) -> list[dict]:
        """Return lesson numbers and titles for a volume."""
        toc = read_toc(data_dir, volume, "textbook")
        return [
            {"lesson": lesson["lesson"], "title": lesson["title"]}
            for lesson in toc.get("lessons", [])
        ]

    @server.tool(
        description=(
            "Return the full Japanese lesson markdown (textbook or workbook), "
            "including structured content for lesson reading and review."
        )
    )
    def get_lesson(volume: str, lesson: int, book_type: str) -> str:
        """Return full lesson markdown content."""
        return read_lesson(data_dir, volume, book_type, lesson)

    @server.tool(
        description=(
            "Return workbook question structure for a Japanese lesson (total "
            "questions and sub-question counts) to plan step-by-step practice."
        )
    )
    def get_question_structure(volume: str, lesson: int) -> dict:
        """Return workbook question structure metadata."""
        markdown = read_lesson(data_dir, volume, "workbook", lesson)
        return parse_question_structure(markdown)

    @server.tool(
        description=(
            "Return one full workbook question block for a Japanese lesson by "
            "question number, enabling focused answer-and-feedback practice."
        )
    )
    def get_question(volume: str, lesson: int, question_num: int) -> str:
        """Return one workbook question block."""
        markdown = read_lesson(data_dir, volume, "workbook", lesson)
        return extract_question(markdown, question_num)

    @server.tool(
        description=(
            "Look up a Japanese word in JMDict and return reading, part of speech, "
            "and meanings for in-context vocabulary learning."
        )
    )
    def lookup_word(word: str) -> dict | None:
        """Lookup a Japanese word in dictionary."""
        return lookup_word_in_dict(word)

    @server.tool(
        description=(
            "Call this tool when the student wants to READ or BROWSE a lesson. "
            "Returns step-by-step workflow instructions: first discover the correct "
            "volume and lesson via list_volumes/list_lessons, then fetch and present "
            "the full textbook lesson (単語→文型→例文→会話→文法) without skipping any section."
        )
    )
    def browse_lesson_flow() -> str:
        """Return tutor workflow instructions for browsing a textbook lesson."""
        return _browse_lesson_flow_instructions()

    @server.tool(
        description=(
            "Call this tool when the student wants to PRACTICE or DO EXERCISES for a lesson. "
            "Returns step-by-step workflow instructions: first discover the correct volume "
            "and lesson via list_volumes/list_lessons, then run an interactive workbook "
            "practice session — present each 問題 one by one, wait for answers, grade with explanations."
        )
    )
    def practice_lesson_flow() -> str:
        """Return tutor workflow instructions for an interactive workbook practice session."""
        return _practice_lesson_flow_instructions()

    @server.prompt()
    def browse_lesson(volume: str, lesson: int) -> str:
        """Browse a full lesson (textbook)."""
        return _browse_lesson_instructions(volume, lesson)

    @server.prompt()
    def practice_lesson(volume: str, lesson: int) -> str:
        """Interactive practice session for a lesson (workbook)."""
        return _practice_lesson_instructions(volume, lesson)

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for MCP server startup."""
    parser = argparse.ArgumentParser(description="Run benkyou MCP server.")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to data directory (default: data).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Start MCP server over stdio transport."""
    args = parse_args(argv)
    server = create_server(data_dir=args.data_dir)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

