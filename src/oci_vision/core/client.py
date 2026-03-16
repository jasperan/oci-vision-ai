"""VisionClient — unified public API for OCI Vision AI.

When ``demo=True`` every call is served from the bundled gallery cache
(no OCI credentials required).  When ``demo=False`` the real OCI Vision
service is called and results are parsed into the same Pydantic models.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

from oci_vision.core.demo import DemoClient
from oci_vision.core.models import (
    AnalysisReport,
    BoundingPolygon,
    ClassificationLabel,
    ClassificationResult,
    DetectedFace,
    DetectedObject,
    DetectionResult,
    DocumentResult,
    FaceDetectionResult,
    FaceLandmark,
    TextDetectionResult,
    TextLine,
    TextWord,
    Vertex,
)


class VisionClient:
    """Unified OCI Vision client that works in demo and live modes.

    Parameters
    ----------
    config : optional
        An ``oci.config.Config`` dict.  When *None* (the default) and
        ``demo=False``, ``oci.config.from_file()`` is used automatically.
    demo : bool
        When *True*, all calls are routed to :class:`DemoClient` (offline,
        no credentials needed).
    compartment_id : str | None
        OCI compartment OCID used for live API calls.  Ignored in demo mode.
    """

    def __init__(
        self,
        config: dict | None = None,
        demo: bool = False,
        compartment_id: str | None = None,
    ):
        self._demo = demo
        self._compartment_id = compartment_id
        self._demo_client: DemoClient | None = None
        self._oci_client = None  # lazily initialised

        if demo:
            self._demo_client = DemoClient()
        else:
            self._config = config

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_demo(self) -> bool:
        """Return *True* when the client operates in demo mode."""
        return self._demo

    # ------------------------------------------------------------------
    # Private helpers — live OCI path
    # ------------------------------------------------------------------

    def _ensure_oci_client(self):
        """Lazy-initialise the OCI AI Vision client (live mode only)."""
        if self._oci_client is not None:
            return
        import oci  # noqa: delayed import so demo mode never needs oci

        cfg = self._config or oci.config.from_file()
        self._oci_client = oci.ai_vision.AIServiceVisionClient(cfg)
        if self._compartment_id is None:
            self._compartment_id = cfg.get("tenancy")

    @staticmethod
    def _parse_image_source(image: str) -> tuple[str, dict]:
        """Classify *image* and return ``(kind, details)``.

        ``kind`` is one of ``"object_storage"`` or ``"inline"``.
        """
        if image.startswith("oci://"):
            # oci://bucket/object_name
            without_prefix = image[len("oci://"):]
            bucket, _, obj_name = without_prefix.partition("/")
            return "object_storage", {"bucket": bucket, "object_name": obj_name}

        # Local file path — read & base64-encode
        path = Path(image)
        if path.is_file():
            data = base64.b64encode(path.read_bytes()).decode()
            return "inline", {"data": data}

        # Path doesn't exist on disk — still treat as inline placeholder
        return "inline", {"data": ""}

    def _build_image_details(self, image: str):
        """Build the OCI SDK image-details object for *image*."""
        import oci.ai_vision.models as vm  # noqa: delayed import

        kind, info = self._parse_image_source(image)
        if kind == "object_storage":
            namespace = self._get_namespace()
            return vm.ObjectStorageImageDetails(
                source="OBJECT_STORAGE",
                namespace_name=namespace,
                bucket_name=info["bucket"],
                object_name=info["object_name"],
            )
        return vm.InlineImageDetails(
            source="INLINE",
            data=info["data"],
        )

    def _build_document_details(self, image: str):
        """Build the OCI SDK document-details object for *image*."""
        import oci.ai_vision.models as vm  # noqa: delayed import

        kind, info = self._parse_image_source(image)
        if kind == "object_storage":
            namespace = self._get_namespace()
            return vm.ObjectStorageDocumentDetails(
                source="OBJECT_STORAGE",
                namespace_name=namespace,
                bucket_name=info["bucket"],
                object_name=info["object_name"],
            )
        return vm.InlineDocumentDetails(
            source="INLINE",
            data=info["data"],
        )

    def _get_namespace(self) -> str:
        """Fetch the Object Storage namespace for the current tenancy."""
        import oci  # noqa: delayed import

        cfg = self._config or oci.config.from_file()
        os_client = oci.object_storage.ObjectStorageClient(cfg)
        return os_client.get_namespace().data

    # ------------------------------------------------------------------
    # Live response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _build_classification_feature(*, max_results: int = 25, model_id: str | None = None):
        import oci.ai_vision.models as vm

        return vm.ImageClassificationFeature(
            feature_type="IMAGE_CLASSIFICATION",
            max_results=max_results,
            model_id=model_id,
        )

    @staticmethod
    def _build_detection_feature(*, max_results: int = 25, model_id: str | None = None):
        import oci.ai_vision.models as vm

        return vm.ImageObjectDetectionFeature(
            feature_type="OBJECT_DETECTION",
            max_results=max_results,
            model_id=model_id,
        )

    @staticmethod
    def _build_text_feature():
        import oci.ai_vision.models as vm

        return vm.ImageTextDetectionFeature(feature_type="TEXT_DETECTION")

    @staticmethod
    def _parse_classification(resp) -> ClassificationResult:
        labels = [
            ClassificationLabel(name=l.name, confidence=l.confidence)
            for l in resp.labels
        ]
        return ClassificationResult(
            model_version=resp.image_classification_model_version or "live",
            labels=labels,
        )

    @staticmethod
    def _parse_detection(resp) -> DetectionResult:
        objects = []
        for o in resp.image_objects:
            verts = [
                Vertex(x=v.x, y=v.y)
                for v in o.bounding_polygon.normalized_vertices
            ]
            objects.append(
                DetectedObject(
                    name=o.name,
                    confidence=o.confidence,
                    bounding_polygon=BoundingPolygon(normalized_vertices=verts),
                )
            )
        return DetectionResult(
            model_version=resp.object_detection_model_version or "live",
            objects=objects,
        )

    @staticmethod
    def _parse_text(resp) -> TextDetectionResult | None:
        """Parse text detection from a live OCI response."""
        if resp.image_text is None:
            return None

        words = [
            TextWord(
                text=word.text,
                confidence=word.confidence,
                bounding_polygon=BoundingPolygon(
                    normalized_vertices=[
                        Vertex(x=vertex.x, y=vertex.y)
                        for vertex in word.bounding_polygon.normalized_vertices
                    ]
                ),
            )
            for word in (resp.image_text.words or [])
        ]

        lines = []
        for line in resp.image_text.lines or []:
            lines.append(
                TextLine(
                    text=line.text,
                    confidence=line.confidence,
                    bounding_polygon=BoundingPolygon(
                        normalized_vertices=[
                            Vertex(x=vertex.x, y=vertex.y)
                            for vertex in line.bounding_polygon.normalized_vertices
                        ]
                    ),
                    words=[
                        words[index]
                        for index in (line.word_indexes or [])
                        if 0 <= index < len(words)
                    ],
                )
            )

        return TextDetectionResult(
            model_version=resp.text_detection_model_version or "live",
            lines=lines,
        )

    @staticmethod
    def _parse_faces(resp) -> FaceDetectionResult | None:
        """Parse face detection from a live OCI response."""
        if not resp.detected_faces:
            return None

        faces = []
        for face in resp.detected_faces:
            faces.append(
                DetectedFace(
                    confidence=face.confidence,
                    bounding_polygon=BoundingPolygon(
                        normalized_vertices=[
                            Vertex(x=vertex.x, y=vertex.y)
                            for vertex in face.bounding_polygon.normalized_vertices
                        ]
                    ),
                    landmarks=[
                        FaceLandmark(type=landmark.type, x=landmark.x, y=landmark.y)
                        for landmark in (face.landmarks or [])
                    ],
                )
            )

        return FaceDetectionResult(
            model_version=resp.face_detection_model_version or "live",
            faces=faces,
        )

    @staticmethod
    def _parse_document_result(resp) -> DocumentResult | None:
        """Parse document analysis from a live OCI response."""
        if not resp.pages:
            return None

        fields = []
        tables = []
        text_lines = []

        for page in resp.pages or []:
            text_lines.extend(line.text for line in (page.lines or []) if line.text)

            for field in page.document_fields or []:
                label = None
                if getattr(field, "field_label", None) is not None:
                    label = field.field_label.name
                elif getattr(field, "field_name", None) is not None:
                    label = getattr(field.field_name, "name", None)

                value = getattr(field.field_value, "text", "") if field.field_value else ""
                confidence = getattr(field.field_value, "confidence", 0.0) if field.field_value else 0.0
                fields.append(
                    {
                        "field_type": field.field_type,
                        "label": label or "Unknown",
                        "value": value,
                        "confidence": confidence,
                    }
                )

            for table in page.tables or []:
                header_rows = []
                if table.header_rows:
                    header_rows = [cell.text for cell in table.header_rows[0].cells]

                body_rows = [
                    [cell.text for cell in row.cells]
                    for row in (table.body_rows or [])
                ]

                tables.append(
                    {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "header_rows": header_rows,
                        "body_rows": body_rows,
                        "confidence": table.confidence,
                    }
                )

        model_version = (
            resp.key_value_detection_model_version
            or resp.table_detection_model_version
            or resp.text_detection_model_version
            or "live"
        )

        return DocumentResult(
            model_version=model_version,
            fields=fields,
            tables=tables,
            full_text="\n".join(text_lines),
            page_count=len(resp.pages or []),
        )

    # ------------------------------------------------------------------
    # Public API — individual features
    # ------------------------------------------------------------------

    def classify(
        self, image: str, *, max_results: int = 25, model_id: str | None = None
    ) -> ClassificationResult | None:
        """Run image classification on *image*.

        Returns a :class:`ClassificationResult` or *None*.
        """
        if self._demo:
            return self._demo_client.classify(image, max_results=max_results)

        self._ensure_oci_client()

        feature = self._build_classification_feature(
            max_results=max_results,
            model_id=model_id,
        )
        image_details = self._build_image_details(image)
        req = vm.AnalyzeImageDetails(
            features=[feature],
            image=image_details,
            compartment_id=self._compartment_id,
        )
        resp = self._oci_client.analyze_image(req).data
        return self._parse_classification(resp)

    def detect_objects(
        self,
        image: str,
        *,
        max_results: int = 25,
        threshold: float = 0.0,
        model_id: str | None = None,
    ) -> DetectionResult | None:
        """Run object detection on *image*.

        Returns a :class:`DetectionResult` or *None*.
        """
        if self._demo:
            return self._demo_client.detect_objects(
                image, max_results=max_results, threshold=threshold
            )

        self._ensure_oci_client()

        feature = self._build_detection_feature(
            max_results=max_results,
            model_id=model_id,
        )
        image_details = self._build_image_details(image)
        req = vm.AnalyzeImageDetails(
            features=[feature],
            image=image_details,
            compartment_id=self._compartment_id,
        )
        resp = self._oci_client.analyze_image(req).data
        return self._parse_detection(resp)

    def detect_text(self, image: str) -> TextDetectionResult | None:
        """Run text/OCR detection on *image*.

        Returns a :class:`TextDetectionResult` or *None*.
        """
        if self._demo:
            return self._demo_client.detect_text(image)

        self._ensure_oci_client()

        feature = self._build_text_feature()
        image_details = self._build_image_details(image)
        req = vm.AnalyzeImageDetails(
            features=[feature],
            image=image_details,
            compartment_id=self._compartment_id,
        )
        resp = self._oci_client.analyze_image(req).data
        return self._parse_text(resp)

    def detect_faces(self, image: str) -> FaceDetectionResult | None:
        """Run face detection on *image*.

        Returns a :class:`FaceDetectionResult` or *None*.
        """
        if self._demo:
            return self._demo_client.detect_faces(image)

        self._ensure_oci_client()
        import oci.ai_vision.models as vm

        feature = vm.FaceDetectionFeature(feature_type="FACE_DETECTION")
        image_details = self._build_image_details(image)
        req = vm.AnalyzeImageDetails(
            features=[feature],
            image=image_details,
            compartment_id=self._compartment_id,
        )
        resp = self._oci_client.analyze_image(req).data
        return self._parse_faces(resp)

    def analyze_document(self, image: str) -> DocumentResult | None:
        """Run document analysis on *image*."""
        if self._demo:
            return self._demo_client.analyze_document(image)

        self._ensure_oci_client()
        import oci.ai_vision.models as vm

        req = vm.AnalyzeDocumentDetails(
            features=[
                vm.DocumentTextDetectionFeature(feature_type="TEXT_DETECTION"),
                vm.DocumentKeyValueDetectionFeature(feature_type="KEY_VALUE_DETECTION"),
                vm.DocumentTableDetectionFeature(feature_type="TABLE_DETECTION"),
            ],
            document=self._build_document_details(image),
            compartment_id=self._compartment_id,
        )
        resp = self._oci_client.analyze_document(req).data
        return self._parse_document_result(resp)

    # ------------------------------------------------------------------
    # Public API — multi-feature analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        image: str,
        features: list[str] | str = "all",
        *,
        model_id: str | None = None,
    ) -> AnalysisReport:
        """Run one or more vision features and return a unified report.

        Parameters
        ----------
        image : str
            Path, ``oci://`` URI, or raw filename.
        features : list[str] | str
            Feature names to run, or ``"all"`` for every supported feature.
        """
        if self._demo:
            return self._demo_client.analyze(image, features=features)

        start = time.monotonic()

        all_features = ["classification", "detection", "text", "faces", "document"]
        if features == "all":
            run_features = all_features
        else:
            run_features = [f for f in features if f in all_features]

        classification = (
            self.classify(image, model_id=model_id)
            if "classification" in run_features
            else None
        )
        detection = (
            self.detect_objects(image, model_id=model_id)
            if "detection" in run_features
            else None
        )
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
