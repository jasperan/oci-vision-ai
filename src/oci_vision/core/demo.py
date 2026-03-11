from __future__ import annotations

import time
from pathlib import Path

from oci_vision.core.models import (
    AnalysisReport,
    BoundingPolygon,
    ClassificationLabel,
    ClassificationResult,
    DetectedObject,
    DetectionResult,
    DocumentResult,
    FaceDetectionResult,
    TextDetectionResult,
    Vertex,
)
from oci_vision.gallery import get_cached_response, load_manifest


class DemoClient:
    def __init__(self):
        self._manifest = load_manifest()
        self._image_ids = {e["id"]: e for e in self._manifest["images"]}
        self._filenames = {e["filename"]: e["id"] for e in self._manifest["images"]}

    def _resolve_image_id(self, image: str) -> str:
        filename = Path(image).name
        if filename in self._filenames:
            return self._filenames[filename]
        stem = Path(image).stem
        if stem in self._image_ids:
            return stem
        # Fallback: return first gallery image
        return self._manifest["images"][0]["id"]

    def classify(self, image: str, max_results: int = 25) -> ClassificationResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "classification")
        if raw is None:
            return None
        return ClassificationResult(
            model_version=raw.get("image_classification_model_version", "demo"),
            labels=[
                ClassificationLabel(name=l["name"], confidence=l["confidence"])
                for l in raw.get("labels", [])[:max_results]
            ],
        )

    def detect_objects(self, image: str, max_results: int = 25, threshold: float = 0.0) -> DetectionResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "detection")
        if raw is None:
            return None
        return DetectionResult(
            model_version=raw.get("object_detection_model_version", "demo"),
            objects=[
                DetectedObject(
                    name=o["name"],
                    confidence=o["confidence"],
                    bounding_polygon=BoundingPolygon(
                        normalized_vertices=[
                            Vertex(x=v["x"], y=v["y"])
                            for v in o["bounding_polygon"]["normalized_vertices"]
                        ]
                    ),
                )
                for o in raw.get("image_objects", [])[:max_results]
            ],
        )

    def detect_text(self, image: str) -> TextDetectionResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "text")
        if raw is None:
            return None
        return None  # No OCR cache yet

    def detect_faces(self, image: str) -> FaceDetectionResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "faces")
        if raw is None:
            return None
        return None  # No face cache yet

    def analyze_document(self, image: str) -> DocumentResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "document")
        if raw is None:
            return None
        return None  # No document cache yet

    def analyze(self, image: str, features: list[str] | str = "all") -> AnalysisReport:
        start = time.monotonic()
        image_id = self._resolve_image_id(image)
        entry = self._image_ids.get(image_id, {})
        available = entry.get("features", [])

        if features == "all":
            run_features = available
        else:
            run_features = [f for f in features if f in available]

        classification = self.classify(image) if "classification" in run_features else None
        detection = self.detect_objects(image) if "detection" in run_features else None
        text = self.detect_text(image) if "text" in run_features else None
        faces = self.detect_faces(image) if "faces" in run_features else None
        document = self.analyze_document(image) if "document" in run_features else None

        return AnalysisReport(
            image_path=image,
            classification=classification,
            detection=detection,
            text=text,
            faces=faces,
            document=document,
            elapsed_seconds=round(time.monotonic() - start, 3),
        )
