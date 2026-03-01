"""MCP server entry point."""

import argparse

from mcp.server.fastmcp import FastMCP

from mcp_server.dictionary import lookup_word as lookup_word_in_dict
from mcp_server.question_parser import extract_question, parse_question_structure
from mcp_server.readers import read_lesson, read_manifest, read_toc


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
    def get_lesson(volume: str, lesson: int, type: str) -> str:
        """Return full lesson markdown content."""
        return read_lesson(data_dir, volume, type, lesson)

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

