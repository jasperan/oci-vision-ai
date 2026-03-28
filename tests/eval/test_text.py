from __future__ import annotations

from oci_vision.core.models import BoundingPolygon, TextDetectionResult, TextLine, Vertex
from oci_vision.eval.text import line_accuracy, normalized_edit_distance, text_similarity


BOX = BoundingPolygon(normalized_vertices=[Vertex(x=0.0, y=0.0)])


def test_normalized_edit_distance_identical_strings():
    assert normalized_edit_distance("STOP", "STOP") == 0.0


def test_normalized_edit_distance_handles_empty_strings():
    assert normalized_edit_distance("", "") == 0.0
    assert normalized_edit_distance("STOP", "") == 1.0


def test_text_similarity_uses_full_text():
    prediction = TextDetectionResult(
        model_version="1.0",
        lines=[TextLine(text="STOP", confidence=0.99, bounding_polygon=BOX)],
    )
    truth = TextDetectionResult(
        model_version="1.0",
        lines=[TextLine(text="STOP", confidence=1.0, bounding_polygon=BOX)],
    )

    assert text_similarity(prediction, truth) == 1.0


def test_line_accuracy_partial_match():
    prediction = TextDetectionResult(
        model_version="1.0",
        lines=[
            TextLine(text="STOP", confidence=0.99, bounding_polygon=BOX),
            TextLine(text="SCHOOL XING", confidence=0.97, bounding_polygon=BOX),
        ],
    )
    truth = TextDetectionResult(
        model_version="1.0",
        lines=[
            TextLine(text="STOP", confidence=1.0, bounding_polygon=BOX),
            TextLine(text="SLOW", confidence=1.0, bounding_polygon=BOX),
        ],
    )

    assert line_accuracy(prediction, truth) == 0.5


def test_line_accuracy_handles_empty_truth():
    empty_prediction = TextDetectionResult(model_version="1.0", lines=[])
    empty_truth = TextDetectionResult(model_version="1.0", lines=[])
    non_empty_prediction = TextDetectionResult(
        model_version="1.0",
        lines=[TextLine(text="STOP", confidence=0.99, bounding_polygon=BOX)],
    )

    assert line_accuracy(empty_prediction, empty_truth) == 1.0
    assert line_accuracy(non_empty_prediction, empty_truth) == 0.0
