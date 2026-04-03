from __future__ import annotations

import json

from oci_vision.core.client import VisionClient
from oci_vision.core.showcase import build_showcase_snapshot, write_showcase_bundle


def test_showcase_snapshot_includes_gallery_workflows_and_comparisons():
    snapshot, reports = build_showcase_snapshot(VisionClient(demo=True))

    assert snapshot["demo"] is True
    assert snapshot["asset_count"] >= 4
    assert snapshot["comparison_count"] >= 1
    assert len(snapshot["gallery"]) == snapshot["asset_count"]
    assert snapshot["workflows"]["receipt"]["fields"]["Invoice Number"] == "INV-1001"
    assert snapshot["workflows"]["archive_search"]["match_count"] >= 1
    assert "classification" in snapshot["batch"]["feature_coverage"]
    assert "document" in snapshot["batch"]["feature_coverage"]
    assert reports["dog_closeup.jpg"].classification is not None
    assert snapshot["headlines"]


def test_showcase_bundle_generates_expected_artifacts(tmp_path):
    snapshot, reports = build_showcase_snapshot(VisionClient(demo=True))
    bundle = write_showcase_bundle(snapshot, reports, tmp_path)

    assert bundle["html"].exists()
    assert bundle["json"].exists()
    assert (tmp_path / "reports" / "dog_closeup.html").exists()
    assert (tmp_path / "reports" / "dog_closeup.json").exists()
    assert (tmp_path / "overlays" / "dog_closeup.png").exists()

    payload = json.loads(bundle["json"].read_text(encoding="utf-8"))
    assert payload["asset_count"] == snapshot["asset_count"]
    assert payload["workflows"]["receipt"]["fields"]["Invoice Number"] == "INV-1001"
