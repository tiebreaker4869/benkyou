# benkyou

A Japanese textbook digitizer and MCP server. Converts physical textbook PDFs into structured Markdown lesson files, then exposes them to AI assistants (e.g. Claude Desktop) via the Model Context Protocol (MCP).

```
PDF → indexer/ (VLM OCR) → data/ (Markdown lessons) → MCP Server → Claude Desktop
```

---

> **Disclaimer:** This project is mostly vibe-coded for personal use and still has plenty of rough edges. If you run into friction or have ideas for improving the experience, feel free to open an issue — feedback is welcome.

---

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **OpenAI API key** — required for the indexer only (not needed to run the MCP server if lesson data already exists)

---

## Environment Setup

```bash
# Clone the repository
git clone <repo-url>
cd benkyou

# Install all dependencies
uv sync
```

Set your OpenAI API key before running the indexer:

```bash
export OPENAI_API_KEY=sk-...
```

Run the test suite:

```bash
uv run pytest tests/
```

## Indexer: PDF → Markdown

The indexer is a one-time processing script with two sequential steps. Both are invoked through `indexer/run.py`.

### Step 1 — Extract TOC

Renders all PDF pages to PNGs, sends the TOC pages to a vision model, and writes a `toc.json` file.

```bash
python indexer/run.py \
  --pdf inbox/book.pdf \
  --volume elementary-vol1 \
  --type textbook \
  --step toc \
  --toc-pages 3-5
```

After this completes, **manually open** `data/<volume>/<type>/toc.json` and set `toc_confirmed` to `true` before proceeding:

```json
{
  "toc_confirmed": true,
  ...
}
```

### Step 2 — Extract Lessons

Reads the confirmed TOC, then sends each lesson's page images to the VLM in parallel to produce structured Markdown lesson files.

```bash
python indexer/run.py \
  --pdf inbox/book.pdf \
  --volume elementary-vol1 \
  --type textbook \
  --step index
  --page-base 7 # number of pages before logical page 1 (e.g. cover, TOC pages); aligns PDF page numbers with the page numbers printed in the book
```

Repeat both steps with `--type workbook` for the workbook volume.

### CLI Reference

| Argument | Required | Description |
|---|---|---|
| `--pdf` | Yes | Path to source PDF |
| `--volume` | Yes | Volume identifier, e.g. `elementary-vol1` |
| `--type` | Yes | `textbook` or `workbook` |
| `--step` | Yes | `toc` or `index` |
| `--toc-pages` | For `--step toc` | TOC page range, e.g. `3-5` (1-indexed, inclusive) |
| `--page-base` | No | Integer offset added to TOC page numbers (default: `0`) |
| `--concurrency` | No | Number of parallel VLM workers (default: `8`) |
| `--model` | No | VLM model override (default: `gpt-5-mini-2025-08-07`) |

### Data Output Layout

```
data/
  manifest.json                  # Index of all processed volumes
  <volume>/
    <type>/
      _pages/                    # PNG renders of PDF pages (gitignore-able)
      toc.json                   # Human-confirmed TOC
      lesson_01.md               # Per-lesson Markdown with YAML frontmatter
      lesson_02.md
      ...
```

---

## MCP Server

The MCP server exposes lesson data, dictionary lookup, and workflow-flow tools to any MCP-compatible client (Claude Desktop, Codex Desktop, Zed, Cursor, etc.) over stdio transport.

### Starting the Server

```bash
# Default (looks for data/ in the current working directory)
uv run python -m mcp_server.server

# Recommended: use an absolute path to the data directory
uv run python -m mcp_server.server --data-dir /absolute/path/to/benkyou/data
```

### Configuring Claude Desktop

Add the following to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "benkyou": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/benkyou",
        "run",
        "python",
        "-m",
        "mcp_server.server",
        "--data-dir",
        "/absolute/path/to/benkyou/data"
      ]
    }
  }
}
```

Replace `/absolute/path/to/benkyou` with your actual clone path. Restart Claude Desktop after saving.

For MCP clients other than Claude Desktop, see [docs/mcp-clients.md](docs/mcp-clients.md).

---

## Tool Reference

The MCP server exposes **8 tools** and **2 prompts**. See [docs/api.md](docs/api.md) for full parameter documentation and examples.

| Tool | Parameters | Purpose |
|---|---|---|
| `list_volumes` | — | List all imported volumes |
| `list_lessons` | `volume` | List lesson numbers and titles for a volume |
| `get_lesson` | `volume`, `lesson`, `book_type` | Full lesson Markdown (textbook or workbook) |
| `get_question_structure` | `volume`, `lesson` | Workbook question metadata (question count + sub-question counts) |
| `get_question` | `volume`, `lesson`, `question_num` | Single question block (大題) with all sub-questions |
| `lookup_word` | `word` | Offline JMDict lookup: reading, POS, meanings |
| `browse_lesson_flow` | — | Returns instructions to start a browse session (discovery-based) |
| `practice_lesson_flow` | — | Returns instructions to start a practice session (discovery-based) |

**Prompts** (`browse_lesson`, `practice_lesson`): for clients that support MCP prompts as slash commands (e.g. Zed). Take `volume` and `lesson` supplied by the user — no discovery step needed.
