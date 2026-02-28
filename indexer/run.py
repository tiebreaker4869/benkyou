"""CLI entry point for the indexer."""
import argparse
import os
import sys

from openai import OpenAI

from indexer.pdf_to_images import pdf_to_images
from indexer.toc_extractor import extract_toc
from indexer.toc_writer import write_toc


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="benkyou indexer")
    parser.add_argument("--pdf", required=True, help="Path to the source PDF")
    parser.add_argument("--volume", required=True, help="Volume name (e.g. elementary-vol1)")
    parser.add_argument("--type", dest="book_type", required=True,
                        choices=["textbook", "workbook"], help="Book type")
    parser.add_argument("--step", required=True, choices=["toc", "index"],
                        help="Processing step to run")
    parser.add_argument("--toc-pages", dest="toc_pages", default=None,
                        help="Page range for TOC (e.g. 3-5, 1-indexed, inclusive)")
    parser.add_argument("--model", default="gpt-5-mini-2025-08-07",
                        help="VLM model to use")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.step == "toc" and not args.toc_pages:
        print("Error: --toc-pages is required when --step toc is used", file=sys.stderr)
        sys.exit(1)


def _parse_page_range(toc_pages: str) -> tuple[int, int]:
    """Parse '3-5' → (3, 5). Both bounds are 1-indexed, inclusive."""
    parts = toc_pages.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid --toc-pages format: {toc_pages!r}. Expected 'START-END'.")
    return int(parts[0]), int(parts[1])


def run_toc(
    pdf_path: str,
    volume: str,
    book_type: str,
    toc_pages: str,
    data_root: str,
    client,
    model: str = "gpt-5-mini-2025-08-07",
) -> None:
    pages_dir = os.path.join(data_root, volume, book_type, "_pages")
    toc_path = os.path.join(data_root, volume, book_type, "toc.json")

    print(f"Rendering PDF to images → {pages_dir}")
    all_pages = pdf_to_images(pdf_path, pages_dir)

    start, end = _parse_page_range(toc_pages)
    # Convert 1-indexed inclusive range to 0-indexed slice
    selected = all_pages[start - 1 : end]
    print(f"Sending pages {start}-{end} ({len(selected)} image(s)) to VLM...")

    lessons = extract_toc(selected, client, model=model)
    write_toc(lessons, toc_path)

    print(f"\nDone. Detected {len(lessons)} lesson(s).")
    print(f"TOC written to: {toc_path}")
    print("\nPlease review toc.json and set toc_confirmed to true when satisfied.")


def main() -> None:
    args = parse_args()
    validate_args(args)

    if args.step == "toc":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set", file=sys.stderr)
            sys.exit(1)
        client = OpenAI(api_key=api_key)
        data_root = os.path.join(os.path.dirname(__file__), "..", "data")
        run_toc(
            pdf_path=args.pdf,
            volume=args.volume,
            book_type=args.book_type,
            toc_pages=args.toc_pages,
            data_root=data_root,
            client=client,
            model=args.model,
        )
    elif args.step == "index":
        print("--step index is not yet implemented (P0 task 2)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
