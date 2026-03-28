from __future__ import annotations

from oci_vision.core.client import VisionClient
from oci_vision.tui.services import (
    derive_artifact_paths,
    load_gallery_entries,
    recommended_features_for_image,
    resolve_initial_image,
    run_analysis,
    run_named_workflow,
)


def test_load_gallery_entries_returns_manifest_items():
    entries = load_gallery_entries()

    assert len(entries) >= 4
    assert entries[0].id == "dog_closeup"
    assert entries[0].filename == "dog_closeup.jpg"


def test_recommended_features_follow_gallery_manifest():
    assert recommended_features_for_image("dog_closeup.jpg") == ["classification", "detection"]
    assert recommended_features_for_image("invoice_demo.png") == ["document"]


def test_resolve_initial_image_uses_first_gallery_image_by_default():
    assert resolve_initial_image(None, demo=True) == "dog_closeup.jpg"


def test_resolve_initial_image_rejects_unknown_demo_image():
    try:
        resolve_initial_image("missing-demo-image.png", demo=True)
    except ValueError as exc:
        assert "missing-demo-image.png" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing demo image")


def test_run_analysis_uses_existing_client_logic():
    client = VisionClient(demo=True)

    report = run_analysis(client, "dog_closeup.jpg", ["classification", "detection"])

    assert report.classification is not None
    assert report.detection is not None
    assert report.text is None


def test_run_named_workflow_receipt():
    client = VisionClient(demo=True)

    result = run_named_workflow(client, "receipt", "invoice_demo.png")

    assert result["field_count"] >= 1
    assert result["fields"]["Invoice Number"] == "INV-1001"


def test_run_named_workflow_archive_search_requires_query():
    client = VisionClient(demo=True)

    try:
        run_named_workflow(client, "archive-search", "invoice_demo.png")
    except ValueError as exc:
        assert "query" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError when archive-search query is missing")


def test_derive_artifact_paths_uses_image_stem(tmp_path):
    paths = derive_artifact_paths("invoice_demo.png", output_dir=tmp_path)

    assert paths["json"].name == "invoice_demo_report.json"
    assert paths["html"].name == "invoice_demo_report.html"
    assert paths["overlay"].name == "invoice_demo_overlay.png"
