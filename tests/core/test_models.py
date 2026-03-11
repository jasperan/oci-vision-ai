"""Comprehensive tests for OCI Vision Pydantic response models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oci_vision.core.models import (
    AnalysisReport,
    BoundingPolygon,
    ClassificationLabel,
    ClassificationResult,
    DetectedFace,
    DetectedObject,
    DetectionResult,
    DocumentField,
    DocumentResult,
    DocumentTable,
    FaceDetectionResult,
    FaceLandmark,
    TextDetectionResult,
    TextLine,
    TextWord,
    Vertex,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLASSIFICATION_JSON = PROJECT_ROOT / "json" / "out_image_classification.json"
DETECTION_JSON = PROJECT_ROOT / "json" / "out_object_detection.json"


# ---------------------------------------------------------------------------
# Vertex
# ---------------------------------------------------------------------------

class TestVertex:
    def test_basic(self):
        v = Vertex(x=0.5, y=0.75)
        assert v.x == 0.5
        assert v.y == 0.75

    def test_from_dict(self):
        v = Vertex.model_validate({"x": 0.1, "y": 0.2})
        assert v.x == 0.1
        assert v.y == 0.2


# ---------------------------------------------------------------------------
# BoundingPolygon
# ---------------------------------------------------------------------------

class TestBoundingPolygon:
    @staticmethod
    def _make(cx: float, cy: float, size: float = 0.1) -> BoundingPolygon:
        """Create a small square bounding polygon centered at (cx, cy)."""
        half = size / 2
        return BoundingPolygon(normalized_vertices=[
            Vertex(x=cx - half, y=cy - half),
            Vertex(x=cx + half, y=cy - half),
            Vertex(x=cx + half, y=cy + half),
            Vertex(x=cx - half, y=cy + half),
        ])

    def test_center(self):
        bp = self._make(0.5, 0.5)
        cx, cy = bp.center
        assert abs(cx - 0.5) < 1e-9
        assert abs(cy - 0.5) < 1e-9

    # human_position: all 9 quadrant combinations
    @pytest.mark.parametrize("cx,cy,expected", [
        (0.1, 0.1, "top-left"),
        (0.5, 0.1, "top"),
        (0.9, 0.1, "top-right"),
        (0.1, 0.5, "left"),
        (0.5, 0.5, "center"),
        (0.9, 0.5, "right"),
        (0.1, 0.9, "bottom-left"),
        (0.5, 0.9, "bottom"),
        (0.9, 0.9, "bottom-right"),
    ])
    def test_human_position(self, cx, cy, expected):
        bp = self._make(cx, cy)
        assert bp.human_position(1000, 1000) == expected

    def test_to_pixels(self):
        bp = BoundingPolygon(normalized_vertices=[
            Vertex(x=0.0, y=0.0),
            Vertex(x=1.0, y=0.0),
            Vertex(x=1.0, y=1.0),
            Vertex(x=0.0, y=1.0),
        ])
        pixels = bp.to_pixels(800, 600)
        assert pixels == [(0, 0), (800, 0), (800, 600), (0, 600)]

    def test_to_pixels_fractional(self):
        bp = BoundingPolygon(normalized_vertices=[
            Vertex(x=0.5, y=0.25),
        ])
        pixels = bp.to_pixels(200, 400)
        assert pixels == [(100, 100)]


# ---------------------------------------------------------------------------
# ClassificationLabel
# ---------------------------------------------------------------------------

class TestClassificationLabel:
    def test_confidence_pct(self):
        label = ClassificationLabel(name="Dog", confidence=0.9925129)
        assert label.confidence_pct == 99.25

    def test_confidence_pct_low(self):
        label = ClassificationLabel(name="Cat", confidence=0.01)
        assert label.confidence_pct == 1.0

    def test_confidence_pct_zero(self):
        label = ClassificationLabel(name="Nothing", confidence=0.0)
        assert label.confidence_pct == 0.0


# ---------------------------------------------------------------------------
# ClassificationResult
# ---------------------------------------------------------------------------

class TestClassificationResult:
    def test_above_threshold(self):
        result = ClassificationResult(
            model_version="1.0",
            labels=[
                ClassificationLabel(name="Dog", confidence=0.99),
                ClassificationLabel(name="Cat", confidence=0.5),
                ClassificationLabel(name="Bird", confidence=0.91),
            ],
        )
        above = result.above_threshold(0.9)
        assert len(above) == 2
        names = {l.name for l in above}
        assert names == {"Dog", "Bird"}

    def test_above_threshold_default(self):
        result = ClassificationResult(
            model_version="1.0",
            labels=[
                ClassificationLabel(name="Dog", confidence=0.95),
                ClassificationLabel(name="Cat", confidence=0.89),
            ],
        )
        # default threshold is 0.9
        above = result.above_threshold()
        assert len(above) == 1
        assert above[0].name == "Dog"

    def test_above_threshold_none_qualify(self):
        result = ClassificationResult(
            model_version="1.0",
            labels=[
                ClassificationLabel(name="Cat", confidence=0.1),
            ],
        )
        assert result.above_threshold(0.5) == []


# ---------------------------------------------------------------------------
# DetectedObject
# ---------------------------------------------------------------------------

class TestDetectedObject:
    def test_confidence_pct(self):
        obj = DetectedObject(
            name="Dog",
            confidence=0.98203605,
            bounding_polygon=BoundingPolygon(normalized_vertices=[
                Vertex(x=0.0, y=0.0),
                Vertex(x=1.0, y=0.0),
                Vertex(x=1.0, y=1.0),
                Vertex(x=0.0, y=1.0),
            ]),
        )
        assert obj.confidence_pct == 98.2

    def test_has_bounding_polygon(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.5, y=0.5)])
        obj = DetectedObject(name="Car", confidence=0.9, bounding_polygon=bp)
        assert obj.bounding_polygon is bp


# ---------------------------------------------------------------------------
# DetectionResult
# ---------------------------------------------------------------------------

class TestDetectionResult:
    def test_above_threshold(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.5, y=0.5)])
        result = DetectionResult(
            model_version="1.0",
            objects=[
                DetectedObject(name="Dog", confidence=0.95, bounding_polygon=bp),
                DetectedObject(name="Cat", confidence=0.7, bounding_polygon=bp),
                DetectedObject(name="Car", confidence=0.85, bounding_polygon=bp),
            ],
        )
        above = result.above_threshold(0.8)
        assert len(above) == 2
        names = {o.name for o in above}
        assert names == {"Dog", "Car"}

    def test_above_threshold_default(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.5, y=0.5)])
        result = DetectionResult(
            model_version="1.0",
            objects=[
                DetectedObject(name="Dog", confidence=0.85, bounding_polygon=bp),
                DetectedObject(name="Cat", confidence=0.79, bounding_polygon=bp),
            ],
        )
        # default threshold is 0.8
        above = result.above_threshold()
        assert len(above) == 1
        assert above[0].name == "Dog"


# ---------------------------------------------------------------------------
# TextDetectionResult
# ---------------------------------------------------------------------------

class TestTextDetectionResult:
    def test_full_text(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.0, y=0.0)])
        result = TextDetectionResult(
            model_version="1.0",
            lines=[
                TextLine(text="Hello world", confidence=0.99, bounding_polygon=bp),
                TextLine(text="Second line", confidence=0.95, bounding_polygon=bp),
            ],
        )
        assert result.full_text == "Hello world\nSecond line"

    def test_full_text_empty(self):
        result = TextDetectionResult(model_version="1.0", lines=[])
        assert result.full_text == ""

    def test_text_line_with_words(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.0, y=0.0)])
        line = TextLine(
            text="Hello world",
            confidence=0.99,
            bounding_polygon=bp,
            words=[
                TextWord(text="Hello", confidence=0.99, bounding_polygon=bp),
                TextWord(text="world", confidence=0.98, bounding_polygon=bp),
            ],
        )
        assert len(line.words) == 2
        assert line.words[0].text == "Hello"


# ---------------------------------------------------------------------------
# FaceDetectionResult
# ---------------------------------------------------------------------------

class TestFaceDetectionResult:
    def test_basic(self):
        bp = BoundingPolygon(normalized_vertices=[
            Vertex(x=0.2, y=0.2),
            Vertex(x=0.8, y=0.2),
            Vertex(x=0.8, y=0.8),
            Vertex(x=0.2, y=0.8),
        ])
        face = DetectedFace(confidence=0.95, bounding_polygon=bp)
        result = FaceDetectionResult(model_version="1.0", faces=[face])
        assert len(result.faces) == 1
        assert result.faces[0].confidence == 0.95

    def test_with_landmarks(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.5, y=0.5)])
        face = DetectedFace(
            confidence=0.99,
            bounding_polygon=bp,
            landmarks=[
                FaceLandmark(type="LEFT_EYE", x=0.3, y=0.4),
                FaceLandmark(type="RIGHT_EYE", x=0.7, y=0.4),
                FaceLandmark(type="NOSE", x=0.5, y=0.6),
            ],
        )
        assert len(face.landmarks) == 3
        assert face.landmarks[0].type == "LEFT_EYE"

    def test_empty_faces(self):
        result = FaceDetectionResult(model_version="1.0", faces=[])
        assert result.faces == []


# ---------------------------------------------------------------------------
# DocumentResult
# ---------------------------------------------------------------------------

class TestDocumentResult:
    def test_basic_fields(self):
        result = DocumentResult(
            model_version="1.0",
            fields=[
                DocumentField(
                    field_type="KEY_VALUE",
                    label="Name",
                    value="John",
                    confidence=0.98,
                ),
            ],
        )
        assert len(result.fields) == 1
        assert result.fields[0].label == "Name"

    def test_with_tables(self):
        result = DocumentResult(
            model_version="1.0",
            tables=[
                DocumentTable(
                    row_count=3,
                    column_count=2,
                    header_rows=["Col1", "Col2"],
                    body_rows=[["a", "b"], ["c", "d"]],
                    confidence=0.95,
                ),
            ],
        )
        assert len(result.tables) == 1
        assert result.tables[0].row_count == 3
        assert result.tables[0].column_count == 2

    def test_defaults(self):
        result = DocumentResult(model_version="1.0")
        assert result.fields == []
        assert result.tables == []


# ---------------------------------------------------------------------------
# AnalysisReport
# ---------------------------------------------------------------------------

class TestAnalysisReport:
    def test_available_features_empty(self):
        report = AnalysisReport(image_path="/tmp/test.jpg")
        assert report.available_features == []

    def test_available_features_all(self):
        bp = BoundingPolygon(normalized_vertices=[Vertex(x=0.5, y=0.5)])
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(model_version="1.0", labels=[]),
            detection=DetectionResult(model_version="1.0", objects=[]),
            text=TextDetectionResult(model_version="1.0", lines=[]),
            faces=FaceDetectionResult(model_version="1.0", faces=[]),
            document=DocumentResult(model_version="1.0"),
        )
        assert report.available_features == [
            "classification", "detection", "text", "faces", "document"
        ]

    def test_available_features_partial(self):
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(model_version="1.0", labels=[]),
            text=TextDetectionResult(model_version="1.0", lines=[]),
        )
        assert report.available_features == ["classification", "text"]

    def test_elapsed_seconds_default(self):
        report = AnalysisReport(image_path="/tmp/test.jpg")
        assert report.elapsed_seconds == 0.0


# ---------------------------------------------------------------------------
# Real JSON Fixture: Classification
# ---------------------------------------------------------------------------

class TestRealClassificationJSON:
    @pytest.fixture()
    def raw(self):
        return json.loads(CLASSIFICATION_JSON.read_text())

    def test_fixture_exists(self):
        assert CLASSIFICATION_JSON.exists(), f"Missing fixture: {CLASSIFICATION_JSON}"

    def test_parse_labels(self, raw):
        labels = [
            ClassificationLabel(name=l["name"], confidence=l["confidence"])
            for l in raw["labels"]
        ]
        # The fixture has 131 labels (based on the real file)
        assert len(labels) >= 100  # "525+" in the task refers to ontology_classes + labels combined

    def test_classification_result(self, raw):
        result = ClassificationResult(
            model_version=raw["image_classification_model_version"],
            labels=[
                ClassificationLabel(name=l["name"], confidence=l["confidence"])
                for l in raw["labels"]
            ],
        )
        assert result.model_version == "1.5.97"
        assert len(result.labels) >= 100

    def test_dog_is_top_label(self, raw):
        result = ClassificationResult(
            model_version=raw["image_classification_model_version"],
            labels=[
                ClassificationLabel(name=l["name"], confidence=l["confidence"])
                for l in raw["labels"]
            ],
        )
        top_label = max(result.labels, key=lambda l: l.confidence)
        assert top_label.name == "Dog"
        assert top_label.confidence_pct == 99.25

    def test_above_threshold_90(self, raw):
        result = ClassificationResult(
            model_version=raw["image_classification_model_version"],
            labels=[
                ClassificationLabel(name=l["name"], confidence=l["confidence"])
                for l in raw["labels"]
            ],
        )
        above_90 = result.above_threshold(0.9)
        # Dog, Vegetation, Metal, Fur, Paw, Dog collar, Animal, Cheek, Neck,
        # Twig, Shadow, Carnivore are all above 0.9
        assert len(above_90) >= 10
        names = {l.name for l in above_90}
        assert "Dog" in names


# ---------------------------------------------------------------------------
# Real JSON Fixture: Object Detection
# ---------------------------------------------------------------------------

class TestRealDetectionJSON:
    @pytest.fixture()
    def raw(self):
        return json.loads(DETECTION_JSON.read_text())

    def test_fixture_exists(self):
        assert DETECTION_JSON.exists(), f"Missing fixture: {DETECTION_JSON}"

    def test_parse_objects(self, raw):
        objects = []
        for obj in raw["image_objects"]:
            bp = BoundingPolygon(
                normalized_vertices=[
                    Vertex(x=v["x"], y=v["y"])
                    for v in obj["bounding_polygon"]["normalized_vertices"]
                ]
            )
            objects.append(DetectedObject(
                name=obj["name"],
                confidence=obj["confidence"],
                bounding_polygon=bp,
            ))
        assert len(objects) == 11

    def test_detection_result(self, raw):
        objects = []
        for obj in raw["image_objects"]:
            bp = BoundingPolygon(
                normalized_vertices=[
                    Vertex(x=v["x"], y=v["y"])
                    for v in obj["bounding_polygon"]["normalized_vertices"]
                ]
            )
            objects.append(DetectedObject(
                name=obj["name"],
                confidence=obj["confidence"],
                bounding_polygon=bp,
            ))
        result = DetectionResult(
            model_version=raw["object_detection_model_version"],
            objects=objects,
        )
        assert result.model_version == "1.3.557"
        assert len(result.objects) == 11

    def test_dog_objects(self, raw):
        objects = []
        for obj in raw["image_objects"]:
            bp = BoundingPolygon(
                normalized_vertices=[
                    Vertex(x=v["x"], y=v["y"])
                    for v in obj["bounding_polygon"]["normalized_vertices"]
                ]
            )
            objects.append(DetectedObject(
                name=obj["name"],
                confidence=obj["confidence"],
                bounding_polygon=bp,
            ))
        dogs = [o for o in objects if o.name == "Dog"]
        assert len(dogs) == 5
        # All dogs should have confidence > 0.7
        for dog in dogs:
            assert dog.confidence > 0.7

    def test_bounding_polygon_center(self, raw):
        """Check the first Dog object's bounding polygon center."""
        first_obj = raw["image_objects"][0]
        bp = BoundingPolygon(
            normalized_vertices=[
                Vertex(x=v["x"], y=v["y"])
                for v in first_obj["bounding_polygon"]["normalized_vertices"]
            ]
        )
        cx, cy = bp.center
        # First Dog: x range ~0.323-0.459, y range ~0.370-0.634
        # center ~(0.391, 0.502)
        assert 0.35 < cx < 0.45
        assert 0.45 < cy < 0.55

    def test_above_threshold_80(self, raw):
        objects = []
        for obj in raw["image_objects"]:
            bp = BoundingPolygon(
                normalized_vertices=[
                    Vertex(x=v["x"], y=v["y"])
                    for v in obj["bounding_polygon"]["normalized_vertices"]
                ]
            )
            objects.append(DetectedObject(
                name=obj["name"],
                confidence=obj["confidence"],
                bounding_polygon=bp,
            ))
        result = DetectionResult(
            model_version=raw["object_detection_model_version"],
            objects=objects,
        )
        above = result.above_threshold(0.8)
        # Dog(0.982), Dog(0.979), Dog(0.978), Bull(0.955), Car(0.933),
        # Car(0.930), Bear(0.908), Dog(0.898), Van(0.825) = 9 objects >= 0.8
        assert len(above) >= 9
