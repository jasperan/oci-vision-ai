from __future__ import annotations

import time
from pathlib import Path

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

        known_assets = ", ".join(sorted(self._filenames))
        raise FileNotFoundError(
            f"Demo asset not found: {image}. Known demo assets: {known_assets}"
        )

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

        image_text = raw.get("image_text") or {}
        words = [
            TextWord(
                text=word["text"],
                confidence=word["confidence"],
                bounding_polygon=BoundingPolygon(
                    normalized_vertices=[
                        Vertex(x=vertex["x"], y=vertex["y"])
                        for vertex in word["bounding_polygon"]["normalized_vertices"]
                    ]
                ),
            )
            for word in image_text.get("words", [])
        ]

        lines = []
        for line in image_text.get("lines", []):
            line_word_indexes = line.get("word_indexes", [])
            lines.append(
                TextLine(
                    text=line["text"],
                    confidence=line["confidence"],
                    bounding_polygon=BoundingPolygon(
                        normalized_vertices=[
                            Vertex(x=vertex["x"], y=vertex["y"])
                            for vertex in line["bounding_polygon"]["normalized_vertices"]
                        ]
                    ),
                    words=[
                        words[index]
                        for index in line_word_indexes
                        if 0 <= index < len(words)
                    ],
                )
            )

        return TextDetectionResult(
            model_version=raw.get("text_detection_model_version", "demo"),
            lines=lines,
        )

    def detect_faces(self, image: str) -> FaceDetectionResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "faces")
        if raw is None:
            return None

        faces = []
        for face in raw.get("detected_faces", []):
            faces.append(
                DetectedFace(
                    confidence=face["confidence"],
                    bounding_polygon=BoundingPolygon(
                        normalized_vertices=[
                            Vertex(x=vertex["x"], y=vertex["y"])
                            for vertex in face["bounding_polygon"]["normalized_vertices"]
                        ]
                    ),
                    landmarks=[
                        FaceLandmark(
                            type=landmark["type"],
                            x=landmark["x"],
                            y=landmark["y"],
                        )
                        for landmark in face.get("landmarks", [])
                    ],
                )
            )

        return FaceDetectionResult(
            model_version=raw.get("face_detection_model_version", "demo"),
            faces=faces,
        )

    def analyze_document(self, image: str) -> DocumentResult | None:
        image_id = self._resolve_image_id(image)
        raw = get_cached_response(image_id, "document")
        if raw is None:
            return None

        pages = raw.get("pages", [])
        full_text = "\n".join(
            line["text"]
            for page in pages
            for line in page.get("lines", [])
            if line.get("text")
        )

        fields = []
        tables = []
        for page in pages:
            for field in page.get("document_fields", []):
                label = (field.get("field_label") or {}).get("name") or "Unknown"
                value = (field.get("field_value") or {}).get("text") or ""
                confidence = (field.get("field_value") or {}).get("confidence") or 0.0
                fields.append(
                    DocumentField(
                        field_type=field.get("field_type", "KEY_VALUE"),
                        label=label,
                        value=value,
                        confidence=confidence,
                    )
                )

            for table in page.get("tables", []):
                header_rows = []
                if table.get("header_rows"):
                    header_rows = [cell.get("text", "") for cell in table["header_rows"][0].get("cells", [])]

                body_rows = [
                    [cell.get("text", "") for cell in row.get("cells", [])]
                    for row in table.get("body_rows", [])
                ]

                tables.append(
                    DocumentTable(
                        row_count=table.get("row_count", 0),
                        column_count=table.get("column_count", 0),
                        header_rows=header_rows,
                        body_rows=body_rows,
                        confidence=table.get("confidence", 0.0),
                    )
                )

        return DocumentResult(
            model_version=(
                raw.get("key_value_detection_model_version")
                or raw.get("table_detection_model_version")
                or raw.get("text_detection_model_version")
                or "demo"
            ),
            fields=fields,
            tables=tables,
            full_text=full_text,
            page_count=len(pages),
        )

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
