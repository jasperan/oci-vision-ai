from __future__ import annotations

import json

from oci_vision.core.client import VisionClient
from oci_vision.core.showcase import build_showcase_bundle


def test_showcase_bundle_generates_expected_artifacts(tmp_path):
    bundle = build_showcase_bundle(VisionClient(demo=True), tmp_path)

    assert bundle["demo"] is True
    assert bundle["image_count"] >= 4
    assert (tmp_path / "showcase_summary.json").exists()
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "batch_summary.json").exists()
    assert (tmp_path / "workflow_summaries.json").exists()
    assert (tmp_path / "comparison_dog_closeup_vs_sign_board.json").exists()

    summary_payload = json.loads((tmp_path / "showcase_summary.json").read_text(encoding="utf-8"))
    assert summary_payload["image_count"] == bundle["image_count"]
    assert summary_payload["workflows"]["receipt"]["fields"]["Invoice Number"] == "INV-1001"

    first_entry = bundle["images"][0]
    assert (tmp_path / first_entry["artifacts"]["json"]).exists()
    assert (tmp_path / first_entry["artifacts"]["html"]).exists()
