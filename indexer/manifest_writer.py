"""Create/update data/manifest.json entries."""

import json
import os


def write_manifest(manifest_path: str, entry: dict) -> None:
    """Upsert one manifest entry keyed by (volume, type)."""
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

    if not os.path.exists(manifest_path):
        data = [entry]
    else:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        replaced = False
        for i, existing in enumerate(data):
            if (
                existing.get("volume") == entry.get("volume")
                and existing.get("type") == entry.get("type")
            ):
                data[i] = entry
                replaced = True
                break

        if not replaced:
            data.append(entry)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
