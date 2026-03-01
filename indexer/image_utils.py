"""Shared image helpers for indexer modules."""

import base64


def encode_image(path: str) -> str:
    """Read image bytes and return a base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
