from __future__ import annotations

import json
from pathlib import Path


def get_gallery_path() -> Path:
    return Path(__file__).parent


def load_manifest() -> dict:
    manifest_path = get_gallery_path() / "manifest.json"
    return json.loads(manifest_path.read_text())


def get_cached_response(image_id: str, feature: str) -> dict | None:
    resp_path = get_gallery_path() / "responses" / f"{image_id}_{feature}.json"
    if not resp_path.exists():
        return None
    return json.loads(resp_path.read_text())
