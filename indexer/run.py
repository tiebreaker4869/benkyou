"""CLI entry point for the indexer."""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from openai import OpenAI

from indexer.lesson_extractor import extract_lesson
from indexer.lesson_writer import lesson_output_path, write_lesson
from indexer.manifest_writer import write_manifest
from indexer.pdf_to_images import pdf_to_images
from indexer.toc_reader import read_toc
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
    parser.add_argument("--page-base", dest="page_base", type=int, default=0,
                        help="Offset for TOC page numbers when running --step index")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Parallel lesson workers for --step index")
    parser.add_argument("--model", default="gpt-5-mini-2025-08-07",
                        help="VLM model to use")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.step == "toc" and not args.toc_pages:
        print("Error: --toc-pages is required when --step toc is used", file=sys.stderr)
        sys.exit(1)
    if args.step == "index" and args.concurrency < 1:
        print("Error: --concurrency must be >= 1 when --step index is used", file=sys.stderr)
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


def run_index(
    pdf_path: str,
    volume: str,
    book_type: str,
    data_root: str,
    page_base: int,
    client,
    model: str,
    concurrency: int = 4,
    max_retries: int = 3,
    retry_base_delay: float = 0.2,
) -> None:
    toc_path = os.path.join(data_root, volume, book_type, "toc.json")
    pages_dir = os.path.join(data_root, volume, book_type, "_pages")

    try:
        toc = read_toc(toc_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    if not os.path.isdir(pages_dir):
        print(f"Error: pages directory not found: {pages_dir}", file=sys.stderr)
        return

    all_pages = sorted(str(p) for p in Path(pages_dir).glob("*.png"))
    if not all_pages:
        print(f"Error: no PNG pages found in {pages_dir}", file=sys.stderr)
        return

    def _process_lesson(lesson: dict) -> str:
        start_idx = page_base + lesson["page_start"] - 1
        end_idx = page_base + lesson["page_end"]  # end-exclusive slice
        lesson_pages = all_pages[start_idx:end_idx]
        delay = retry_base_delay
        markdown = None
        for attempt in range(1, max_retries + 1):
            try:
                markdown = extract_lesson(
                    lesson_pages,
                    lesson=lesson,
                    volume=volume,
                    book_type=book_type,
                    client=client,
                    model=model,
                )
                break
            except Exception as e:
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Lesson {lesson['lesson']:02d} failed after {max_retries} attempts"
                    ) from e
                print(
                    f"[lesson {lesson['lesson']:02d}] attempt {attempt}/{max_retries} failed: "
                    f"{e}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= 2

        output_path = lesson_output_path(data_root, volume, book_type, lesson["lesson"])
        write_lesson(markdown, output_path)
        return f"Wrote lesson {lesson['lesson']:02d} → {output_path}"

    total = len(toc["lessons"])
    completed = 0
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_process_lesson, lesson) for lesson in toc["lessons"]]
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            print(f"[{completed}/{total}] {result}")

    manifest_entry = {
        "volume": volume,
        "type": book_type,
        "source_pdf": pdf_path,
        "generated_at": date.today().isoformat(),
        "model": model,
        "lessons": len(toc["lessons"]),
        "status": "complete",
    }
    manifest_path = os.path.join(data_root, "manifest.json")
    write_manifest(manifest_path, manifest_entry)
    print(f"\nDone. Generated {len(toc['lessons'])} lesson file(s).")
    print(f"Manifest updated: {manifest_path}")


def main() -> None:
    args = parse_args()
    validate_args(args)

    if args.step in {"toc", "index"}:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set", file=sys.stderr)
            sys.exit(1)
        client = OpenAI(api_key=api_key)
        data_root = os.path.join(os.path.dirname(__file__), "..", "data")

    if args.step == "toc":
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
        run_index(
            pdf_path=args.pdf,
            volume=args.volume,
            book_type=args.book_type,
            data_root=data_root,
            page_base=args.page_base,
            client=client,
            model=args.model,
            concurrency=args.concurrency,
        )


if __name__ == "__main__":
    main()
