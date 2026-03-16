from __future__ import annotations

from typing import Any

from oci_vision.core.models import BoundingPolygon, DetectionResult


def _bounds(polygon: BoundingPolygon) -> tuple[float, float, float, float]:
    xs = [vertex.x for vertex in polygon.normalized_vertices]
    ys = [vertex.y for vertex in polygon.normalized_vertices]
    return min(xs), min(ys), max(xs), max(ys)


def intersection_over_union(a: BoundingPolygon, b: BoundingPolygon) -> float:
    ax1, ay1, ax2, ay2 = _bounds(a)
    bx1, by1, bx2, by2 = _bounds(b)

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(ax2 - ax1, 0.0) * max(ay2 - ay1, 0.0)
    area_b = max(bx2 - bx1, 0.0) * max(by2 - by1, 0.0)
    union = area_a + area_b - intersection
    if union <= 0:
        return 0.0
    return round(intersection / union, 6)


def evaluate_detection_result(
    prediction: DetectionResult,
    truth: DetectionResult,
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    predicted = sorted(prediction.objects, key=lambda obj: obj.confidence, reverse=True)
    truth_objects = list(truth.objects)
    matched_truth_indexes: set[int] = set()
    matched_ious: list[float] = []
    true_positives = 0
    false_positives = 0

    for predicted_object in predicted:
        best_match_index = None
        best_iou = 0.0

        for index, truth_object in enumerate(truth_objects):
            if index in matched_truth_indexes:
                continue
            if truth_object.name != predicted_object.name:
                continue
            iou = intersection_over_union(
                predicted_object.bounding_polygon,
                truth_object.bounding_polygon,
            )
            if iou >= iou_threshold and iou > best_iou:
                best_iou = iou
                best_match_index = index

        if best_match_index is not None:
            matched_truth_indexes.add(best_match_index)
            matched_ious.append(best_iou)
            true_positives += 1
        else:
            false_positives += 1

    false_negatives = len(truth_objects) - len(matched_truth_indexes)
    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "mean_iou": (sum(matched_ious) / len(matched_ious)) if matched_ious else 0.0,
        "iou_threshold": iou_threshold,
    }


def threshold_sweep(
    prediction: DetectionResult,
    truth: DetectionResult,
    *,
    thresholds: list[float] | None = None,
    iou_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    thresholds = thresholds or sorted({obj.confidence for obj in prediction.objects})
    results = []
    for threshold in thresholds:
        filtered = DetectionResult(
            model_version=prediction.model_version,
            objects=[obj for obj in prediction.objects if obj.confidence >= threshold],
        )
        metrics = evaluate_detection_result(filtered, truth, iou_threshold=iou_threshold)
        metrics["threshold"] = threshold
        results.append(metrics)
    return results
