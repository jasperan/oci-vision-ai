from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from oci_vision.core.client import VisionClient
from oci_vision.gallery import load_manifest
from oci_vision.workflows import (
    archive_search_workflow,
    inspection_workflow,
    receipt_workflow,
    shelf_audit_workflow,
)

ALL_FEATURES = ["classification", "detection", "text", "faces", "document"]
WORKFLOW_NAMES = ["receipt", "shelf", "inspection", "archive-search"]


@dataclass(frozen=True, slots=True)
class GalleryEntry:
    id: str
    filename: str
    description: str
    features: list[str]


def load_gallery_entries() -> list[GalleryEntry]:
    manifest = load_manifest()
    return [
        GalleryEntry(
            id=entry["id"],
            filename=entry["filename"],
            description=entry.get("description", ""),
            features=list(entry.get("features", [])),
        )
        for entry in manifest.get("images", [])
    ]


def find_gallery_entry(image: str | None) -> GalleryEntry | None:
    if not image:
        return None

    needle = Path(image).name
    stem = Path(needle).stem
    for entry in load_gallery_entries():
        if image == entry.id or needle == entry.filename or stem == entry.id:
            return entry
    return None


def resolve_initial_image(image: str | None, *, demo: bool) -> str:
    if image:
        entry = find_gallery_entry(image)
        if entry is not None:
            return entry.filename
        if demo:
            raise ValueError(f"Unknown demo gallery image: {image}")
        return image

    entries = load_gallery_entries()
    if not entries:
        raise ValueError("No gallery entries are available")
    return entries[0].filename


def recommended_features_for_image(image: str) -> list[str]:
    entry = find_gallery_entry(image)
    if entry is not None and entry.features:
        return list(entry.features)
    return list(ALL_FEATURES)


def parse_feature_selection(features: str | Sequence[str] | None, default: Sequence[str]) -> list[str]:
    if features is None:
        return list(default)
    if isinstance(features, str):
        requested = [part.strip() for part in features.split(",") if part.strip()]
    else:
        requested = [part.strip() for part in features if part and part.strip()]
    filtered = [feature for feature in requested if feature in ALL_FEATURES]
    return filtered or list(default)


def run_analysis(client: VisionClient, image: str, features: Sequence[str]):
    return client.analyze(image, features=list(features))


def run_named_workflow(
    client: VisionClient,
    workflow_name: str,
    image: str,
    query: str | None = None,
):
    workflow_name = workflow_name.strip().lower()
    if workflow_name == "receipt":
        return receipt_workflow(client, image)
    if workflow_name == "shelf":
        return shelf_audit_workflow(client, image)
    if workflow_name == "inspection":
        return inspection_workflow(client, image)
    if workflow_name == "archive-search":
        if not query:
            raise ValueError("Archive-search workflow requires a query")
        return archive_search_workflow(client, [image], query=query)
    raise ValueError(f"Unsupported workflow: {workflow_name}")


def derive_artifact_paths(image_path: str, output_dir: str | Path | None = None) -> dict[str, Path]:
    base_dir = Path(output_dir or Path.cwd())
    stem = Path(image_path).stem
    return {
        "json": base_dir / f"{stem}_report.json",
        "html": base_dir / f"{stem}_report.html",
        "overlay": base_dir / f"{stem}_overlay.png",
    }
