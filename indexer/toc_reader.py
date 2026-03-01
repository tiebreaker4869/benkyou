"""Read and validate toc.json before --step index."""

import json


def read_toc(toc_path: str) -> dict:
    """Load toc.json and ensure it has been manually confirmed."""
    with open(toc_path, encoding="utf-8") as f:
        toc = json.load(f)

    if not toc.get("toc_confirmed"):
        raise ValueError("toc not confirmed")

    return toc
