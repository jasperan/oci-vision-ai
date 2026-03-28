from __future__ import annotations

from oci_vision.core.models import (
    AnalysisReport,
    ClassificationLabel,
    ClassificationResult,
    DetectedObject,
    DetectionResult,
    BoundingPolygon,
    Vertex,
)
from oci_vision.tui.insights import compare_reports, push_history, summarize_report


def _box() -> BoundingPolygon:
    return BoundingPolygon(
        normalized_vertices=[
            Vertex(x=0.1, y=0.1),
            Vertex(x=0.4, y=0.1),
            Vertex(x=0.4, y=0.4),
            Vertex(x=0.1, y=0.4),
        ]
    )


def _report(image: str, label: str, object_count: int) -> AnalysisReport:
    return AnalysisReport(
        image_path=image,
        classification=ClassificationResult(
            model_version="demo",
            labels=[ClassificationLabel(name=label, confidence=0.95)],
        ),
        detection=DetectionResult(
            model_version="demo",
            objects=[
                DetectedObject(name="Dog", confidence=0.9, bounding_polygon=_box())
                for _ in range(object_count)
            ],
        ),
        elapsed_seconds=0.111,
    )


def test_summarize_report_extracts_demo_cards():
    summary = summarize_report(_report("dog_closeup.jpg", "Dog", 2))

    assert summary["image"] == "dog_closeup.jpg"
    assert summary["top_label"] == "Dog"
    assert summary["object_count"] == 2
    assert summary["feature_count"] == 2


def test_compare_reports_describes_current_vs_previous():
    previous = _report("dog_closeup.jpg", "Dog", 1)
    current = _report("invoice_demo.png", "Invoice", 3)

    compare = compare_reports(current, previous)

    assert compare["has_previous"] is True
    assert "Dog" in compare["top_label_delta"]
    assert "Invoice" in compare["top_label_delta"]
    assert compare["object_count_delta"] == "+2"


def test_compare_reports_handles_first_run():
    compare = compare_reports(_report("dog_closeup.jpg", "Dog", 1), None)

    assert compare["has_previous"] is False
    assert "Run another analysis" in compare["summary"]


def test_push_history_keeps_latest_five_reports():
    history: list[AnalysisReport] = []
    for index in range(6):
        history = push_history(history, _report(f"image-{index}.png", "Dog", index + 1), limit=5)

    assert len(history) == 5
    assert history[0].image_path == "image-5.png"
    assert history[-1].image_path == "image-1.png"
