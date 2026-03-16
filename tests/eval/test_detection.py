from __future__ import annotations

from oci_vision.core.models import BoundingPolygon, DetectedObject, DetectionResult, Vertex
from oci_vision.eval.detection import evaluate_detection_result, intersection_over_union, threshold_sweep


def _box(x1: float, y1: float, x2: float, y2: float) -> BoundingPolygon:
    return BoundingPolygon(
        normalized_vertices=[
            Vertex(x=x1, y=y1),
            Vertex(x=x2, y=y1),
            Vertex(x=x2, y=y2),
            Vertex(x=x1, y=y2),
        ]
    )


def test_intersection_over_union_identical_boxes():
    box = _box(0.1, 0.1, 0.4, 0.4)
    assert intersection_over_union(box, box) == 1.0


def test_evaluate_detection_result_counts_tp_fp_fn():
    prediction = DetectionResult(
        model_version="1.0",
        objects=[
            DetectedObject(name="Dog", confidence=0.95, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4)),
            DetectedObject(name="Cat", confidence=0.85, bounding_polygon=_box(0.6, 0.6, 0.9, 0.9)),
        ],
    )
    truth = DetectionResult(
        model_version="1.0",
        objects=[
            DetectedObject(name="Dog", confidence=1.0, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4)),
            DetectedObject(name="Bird", confidence=1.0, bounding_polygon=_box(0.2, 0.6, 0.4, 0.8)),
        ],
    )

    metrics = evaluate_detection_result(prediction, truth, iou_threshold=0.5)

    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5


def test_threshold_sweep_returns_multiple_points():
    prediction = DetectionResult(
        model_version="1.0",
        objects=[
            DetectedObject(name="Dog", confidence=0.95, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4)),
            DetectedObject(name="Dog", confidence=0.55, bounding_polygon=_box(0.5, 0.5, 0.8, 0.8)),
        ],
    )
    truth = DetectionResult(
        model_version="1.0",
        objects=[
            DetectedObject(name="Dog", confidence=1.0, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4)),
            DetectedObject(name="Dog", confidence=1.0, bounding_polygon=_box(0.5, 0.5, 0.8, 0.8)),
        ],
    )

    points = threshold_sweep(prediction, truth, thresholds=[0.5, 0.9])

    assert [point["threshold"] for point in points] == [0.5, 0.9]
    assert points[0]["recall"] == 1.0
    assert points[1]["recall"] == 0.5
