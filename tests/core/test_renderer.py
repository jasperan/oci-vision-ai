"""Tests for the image overlay renderer."""

from __future__ import annotations

from PIL import Image

from oci_vision.core.models import (
    AnalysisReport,
    BoundingPolygon,
    ClassificationLabel,
    ClassificationResult,
    DetectedFace,
    DetectedObject,
    DetectionResult,
    FaceDetectionResult,
    FaceLandmark,
    TextDetectionResult,
    TextLine,
    TextWord,
    Vertex,
)
from oci_vision.core.renderer import render_overlay


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_image(w: int = 640, h: int = 480) -> Image.Image:
    return Image.new("RGB", (w, h), color=(100, 100, 100))


def _make_box(
    x1: float = 0.1, y1: float = 0.1, x2: float = 0.5, y2: float = 0.5,
) -> BoundingPolygon:
    return BoundingPolygon(normalized_vertices=[
        Vertex(x=x1, y=y1),
        Vertex(x=x2, y=y1),
        Vertex(x=x2, y=y2),
        Vertex(x=x1, y=y2),
    ])


# ---------------------------------------------------------------------------
# Detection overlay
# ---------------------------------------------------------------------------

class TestDetectionOverlay:
    def test_produces_valid_image_same_size(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Dog",
                        confidence=0.98,
                        bounding_polygon=_make_box(),
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        assert result.mode == "RGB"

    def test_multiple_objects_different_colors(self):
        """Multiple objects should render without error."""
        img = _make_test_image()
        objects = []
        for i, name in enumerate(["Dog", "Cat", "Car", "Person"]):
            x1 = i * 0.2
            objects.append(DetectedObject(
                name=name,
                confidence=0.9 - i * 0.05,
                bounding_polygon=_make_box(x1, 0.1, x1 + 0.15, 0.5),
            ))
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(model_version="1.0", objects=objects),
        )
        result = render_overlay(img, report)
        assert result.size == img.size
        assert result.mode == "RGB"

    def test_image_pixels_are_modified(self):
        """The overlay should actually change some pixels compared to the original."""
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Dog",
                        confidence=0.98,
                        bounding_polygon=_make_box(0.1, 0.1, 0.9, 0.9),
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        # The result image should differ from the original
        assert result.tobytes() != img.tobytes()


# ---------------------------------------------------------------------------
# Classification overlay
# ---------------------------------------------------------------------------

class TestClassificationOverlay:
    def test_produces_valid_image(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(
                model_version="1.0",
                labels=[
                    ClassificationLabel(name="Dog", confidence=0.99),
                    ClassificationLabel(name="Animal", confidence=0.95),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        assert result.mode == "RGB"

    def test_single_label(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(
                model_version="1.0",
                labels=[ClassificationLabel(name="Cat", confidence=0.87)],
            ),
        )
        result = render_overlay(img, report)
        assert result.size == img.size

    def test_empty_labels_list(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(
                model_version="1.0", labels=[],
            ),
        )
        result = render_overlay(img, report)
        assert result.size == img.size


# ---------------------------------------------------------------------------
# Text / OCR overlay
# ---------------------------------------------------------------------------

class TestTextOverlay:
    def test_produces_valid_image(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            text=TextDetectionResult(
                model_version="1.0",
                lines=[
                    TextLine(
                        text="Hello world",
                        confidence=0.99,
                        bounding_polygon=_make_box(0.05, 0.1, 0.6, 0.2),
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        assert result.mode == "RGB"

    def test_multiple_text_lines(self):
        img = _make_test_image()
        lines = [
            TextLine(
                text=f"Line {i}",
                confidence=0.95,
                bounding_polygon=_make_box(0.05, 0.1 + i * 0.15, 0.6, 0.2 + i * 0.15),
            )
            for i in range(3)
        ]
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            text=TextDetectionResult(model_version="1.0", lines=lines),
        )
        result = render_overlay(img, report)
        assert result.size == img.size

    def test_text_with_words(self):
        img = _make_test_image()
        line = TextLine(
            text="Hello world",
            confidence=0.99,
            bounding_polygon=_make_box(0.05, 0.1, 0.6, 0.2),
            words=[
                TextWord(
                    text="Hello",
                    confidence=0.99,
                    bounding_polygon=_make_box(0.05, 0.1, 0.3, 0.2),
                ),
                TextWord(
                    text="world",
                    confidence=0.98,
                    bounding_polygon=_make_box(0.31, 0.1, 0.6, 0.2),
                ),
            ],
        )
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            text=TextDetectionResult(model_version="1.0", lines=[line]),
        )
        result = render_overlay(img, report)
        assert result.size == img.size


# ---------------------------------------------------------------------------
# Face landmark overlay
# ---------------------------------------------------------------------------

class TestFaceLandmarkOverlay:
    def test_produces_valid_image(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            faces=FaceDetectionResult(
                model_version="1.0",
                faces=[
                    DetectedFace(
                        confidence=0.99,
                        bounding_polygon=_make_box(0.2, 0.1, 0.8, 0.8),
                        landmarks=[
                            FaceLandmark(type="LEFT_EYE", x=0.35, y=0.35),
                            FaceLandmark(type="RIGHT_EYE", x=0.65, y=0.35),
                            FaceLandmark(type="NOSE", x=0.5, y=0.5),
                            FaceLandmark(type="MOUTH_LEFT", x=0.4, y=0.65),
                            FaceLandmark(type="MOUTH_RIGHT", x=0.6, y=0.65),
                        ],
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        assert result.mode == "RGB"

    def test_face_without_landmarks(self):
        img = _make_test_image()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            faces=FaceDetectionResult(
                model_version="1.0",
                faces=[
                    DetectedFace(
                        confidence=0.95,
                        bounding_polygon=_make_box(0.2, 0.2, 0.6, 0.7),
                        landmarks=[],
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert result.size == img.size

    def test_multiple_faces(self):
        img = _make_test_image()
        faces = [
            DetectedFace(
                confidence=0.95,
                bounding_polygon=_make_box(0.05 + i * 0.3, 0.1, 0.25 + i * 0.3, 0.8),
                landmarks=[
                    FaceLandmark(type="LEFT_EYE", x=0.1 + i * 0.3, y=0.35),
                    FaceLandmark(type="RIGHT_EYE", x=0.2 + i * 0.3, y=0.35),
                ],
            )
            for i in range(3)
        ]
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            faces=FaceDetectionResult(model_version="1.0", faces=faces),
        )
        result = render_overlay(img, report)
        assert result.size == img.size


# ---------------------------------------------------------------------------
# Combined overlay (multiple features)
# ---------------------------------------------------------------------------

class TestCombinedOverlay:
    def test_all_features_combined(self):
        img = _make_test_image(800, 600)
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            classification=ClassificationResult(
                model_version="1.0",
                labels=[
                    ClassificationLabel(name="Dog", confidence=0.99),
                    ClassificationLabel(name="Outdoor", confidence=0.92),
                ],
            ),
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Dog",
                        confidence=0.98,
                        bounding_polygon=_make_box(0.1, 0.2, 0.5, 0.8),
                    ),
                    DetectedObject(
                        name="Car",
                        confidence=0.85,
                        bounding_polygon=_make_box(0.6, 0.3, 0.9, 0.7),
                    ),
                ],
            ),
            text=TextDetectionResult(
                model_version="1.0",
                lines=[
                    TextLine(
                        text="STOP",
                        confidence=0.97,
                        bounding_polygon=_make_box(0.7, 0.05, 0.85, 0.15),
                    ),
                ],
            ),
            faces=FaceDetectionResult(
                model_version="1.0",
                faces=[
                    DetectedFace(
                        confidence=0.96,
                        bounding_polygon=_make_box(0.15, 0.25, 0.35, 0.55),
                        landmarks=[
                            FaceLandmark(type="LEFT_EYE", x=0.22, y=0.35),
                            FaceLandmark(type="RIGHT_EYE", x=0.28, y=0.35),
                            FaceLandmark(type="NOSE", x=0.25, y=0.42),
                        ],
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)
        assert result.mode == "RGB"
        # Combined overlay should differ from original
        assert result.tobytes() != img.tobytes()


# ---------------------------------------------------------------------------
# Empty report
# ---------------------------------------------------------------------------

class TestEmptyReport:
    def test_returns_unchanged_image(self):
        img = _make_test_image()
        report = AnalysisReport(image_path="/tmp/test.jpg")
        result = render_overlay(img, report)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
        assert result.mode == "RGB"
        # With an empty report, the pixel data should be identical
        assert result.tobytes() == img.tobytes()

    def test_preserves_image_dimensions(self):
        for w, h in [(100, 100), (1920, 1080), (320, 240)]:
            img = _make_test_image(w, h)
            report = AnalysisReport(image_path="/tmp/test.jpg")
            result = render_overlay(img, report)
            assert result.size == (w, h)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_rgba_input_returns_rgb(self):
        """Even if the input image is RGBA, the output should be RGB."""
        img = Image.new("RGBA", (640, 480), color=(100, 100, 100, 255))
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Dog",
                        confidence=0.98,
                        bounding_polygon=_make_box(),
                    ),
                ],
            ),
        )
        result = render_overlay(img, report)
        assert result.mode == "RGB"

    def test_small_image(self):
        """Renderer should handle very small images without crashing."""
        img = _make_test_image(32, 32)
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Object",
                        confidence=0.9,
                        bounding_polygon=_make_box(0.0, 0.0, 1.0, 1.0),
                    ),
                ],
            ),
            classification=ClassificationResult(
                model_version="1.0",
                labels=[ClassificationLabel(name="Thing", confidence=0.9)],
            ),
        )
        result = render_overlay(img, report)
        assert result.size == (32, 32)

    def test_does_not_mutate_original(self):
        """render_overlay should return a NEW image, not modify the input."""
        img = _make_test_image()
        original_data = img.tobytes()
        report = AnalysisReport(
            image_path="/tmp/test.jpg",
            detection=DetectionResult(
                model_version="1.0",
                objects=[
                    DetectedObject(
                        name="Dog",
                        confidence=0.98,
                        bounding_polygon=_make_box(0.1, 0.1, 0.9, 0.9),
                    ),
                ],
            ),
        )
        render_overlay(img, report)
        assert img.tobytes() == original_data
