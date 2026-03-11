"""Pydantic v2 response models for all OCI Vision API result types."""

from __future__ import annotations

from pydantic import BaseModel, computed_field


class Vertex(BaseModel):
    x: float
    y: float


class BoundingPolygon(BaseModel):
    normalized_vertices: list[Vertex]

    @computed_field
    @property
    def center(self) -> tuple[float, float]:
        xs = [v.x for v in self.normalized_vertices]
        ys = [v.y for v in self.normalized_vertices]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def human_position(self, img_w: float, img_h: float) -> str:
        cx, cy = self.center
        col = "left" if cx < 0.33 else ("right" if cx > 0.66 else "center")
        row = "top" if cy < 0.33 else ("bottom" if cy > 0.66 else "center")
        if row == "center" and col == "center":
            return "center"
        if row == "center":
            return col
        if col == "center":
            return row
        return f"{row}-{col}"

    def to_pixels(self, img_w: int, img_h: int) -> list[tuple[int, int]]:
        return [(int(v.x * img_w), int(v.y * img_h)) for v in self.normalized_vertices]


class ClassificationLabel(BaseModel):
    name: str
    confidence: float

    @computed_field
    @property
    def confidence_pct(self) -> float:
        return round(self.confidence * 100, 2)


class ClassificationResult(BaseModel):
    model_version: str
    labels: list[ClassificationLabel]

    def above_threshold(self, threshold: float = 0.9) -> list[ClassificationLabel]:
        return [l for l in self.labels if l.confidence >= threshold]


class DetectedObject(BaseModel):
    name: str
    confidence: float
    bounding_polygon: BoundingPolygon

    @computed_field
    @property
    def confidence_pct(self) -> float:
        return round(self.confidence * 100, 2)


class DetectionResult(BaseModel):
    model_version: str
    objects: list[DetectedObject]

    def above_threshold(self, threshold: float = 0.8) -> list[DetectedObject]:
        return [o for o in self.objects if o.confidence >= threshold]


class TextWord(BaseModel):
    text: str
    confidence: float
    bounding_polygon: BoundingPolygon


class TextLine(BaseModel):
    text: str
    confidence: float
    bounding_polygon: BoundingPolygon
    words: list[TextWord] = []


class TextDetectionResult(BaseModel):
    model_version: str
    lines: list[TextLine]

    @computed_field
    @property
    def full_text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class FaceLandmark(BaseModel):
    type: str
    x: float
    y: float


class DetectedFace(BaseModel):
    confidence: float
    bounding_polygon: BoundingPolygon
    landmarks: list[FaceLandmark] = []


class FaceDetectionResult(BaseModel):
    model_version: str
    faces: list[DetectedFace]


class DocumentField(BaseModel):
    field_type: str
    label: str
    value: str
    confidence: float


class DocumentTable(BaseModel):
    row_count: int
    column_count: int
    header_rows: list[str] = []
    body_rows: list[list[str]] = []
    confidence: float = 0.0


class DocumentResult(BaseModel):
    model_version: str
    fields: list[DocumentField] = []
    tables: list[DocumentTable] = []


class AnalysisReport(BaseModel):
    image_path: str
    classification: ClassificationResult | None = None
    detection: DetectionResult | None = None
    text: TextDetectionResult | None = None
    faces: FaceDetectionResult | None = None
    document: DocumentResult | None = None
    elapsed_seconds: float = 0.0

    @computed_field
    @property
    def available_features(self) -> list[str]:
        features = []
        if self.classification is not None:
            features.append("classification")
        if self.detection is not None:
            features.append("detection")
        if self.text is not None:
            features.append("text")
        if self.faces is not None:
            features.append("faces")
        if self.document is not None:
            features.append("document")
        return features
