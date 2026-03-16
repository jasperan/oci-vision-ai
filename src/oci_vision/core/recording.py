from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from oci_vision.core.models import (
    ClassificationResult,
    DetectionResult,
    DocumentResult,
    FaceDetectionResult,
    TextDetectionResult,
)
from oci_vision.gallery import get_gallery_path


FeatureResult = (
    ClassificationResult
    | DetectionResult
    | TextDetectionResult
    | FaceDetectionResult
    | DocumentResult
)


def _vertices_to_payload(vertices: list[Any]) -> list[dict[str, float]]:
    return [{"x": vertex.x, "y": vertex.y} for vertex in vertices]


def serialize_feature_result(feature: str, result: FeatureResult) -> dict[str, Any]:
    if feature == "classification" and isinstance(result, ClassificationResult):
        return {
            "image_classification_model_version": result.model_version,
            "labels": [label.model_dump() for label in result.labels],
        }

    if feature == "detection" and isinstance(result, DetectionResult):
        return {
            "object_detection_model_version": result.model_version,
            "image_objects": [
                {
                    "name": obj.name,
                    "confidence": obj.confidence,
                    "bounding_polygon": {
                        "normalized_vertices": _vertices_to_payload(
                            obj.bounding_polygon.normalized_vertices
                        )
                    },
                }
                for obj in result.objects
            ],
        }

    if feature == "text" and isinstance(result, TextDetectionResult):
        words = []
        word_lookup: dict[tuple[str, float, tuple[tuple[float, float], ...]], int] = {}
        lines_payload = []

        for line in result.lines:
            word_indexes = []
            for word in line.words:
                key = (
                    word.text,
                    word.confidence,
                    tuple((vertex.x, vertex.y) for vertex in word.bounding_polygon.normalized_vertices),
                )
                if key not in word_lookup:
                    word_lookup[key] = len(words)
                    words.append(
                        {
                            "text": word.text,
                            "confidence": word.confidence,
                            "bounding_polygon": {
                                "normalized_vertices": _vertices_to_payload(
                                    word.bounding_polygon.normalized_vertices
                                )
                            },
                        }
                    )
                word_indexes.append(word_lookup[key])

            lines_payload.append(
                {
                    "text": line.text,
                    "confidence": line.confidence,
                    "bounding_polygon": {
                        "normalized_vertices": _vertices_to_payload(
                            line.bounding_polygon.normalized_vertices
                        )
                    },
                    "word_indexes": word_indexes,
                }
            )

        return {
            "text_detection_model_version": result.model_version,
            "image_text": {
                "words": words,
                "lines": lines_payload,
            },
        }

    if feature == "faces" and isinstance(result, FaceDetectionResult):
        return {
            "face_detection_model_version": result.model_version,
            "detected_faces": [
                {
                    "confidence": face.confidence,
                    "bounding_polygon": {
                        "normalized_vertices": _vertices_to_payload(
                            face.bounding_polygon.normalized_vertices
                        )
                    },
                    "landmarks": [landmark.model_dump() for landmark in face.landmarks],
                }
                for face in result.faces
            ],
        }

    if feature == "document" and isinstance(result, DocumentResult):
        lines = []
        for index, text in enumerate(filter(None, result.full_text.splitlines())):
            lines.append(
                {
                    "text": text,
                    "confidence": 1.0,
                    "bounding_polygon": {
                        "normalized_vertices": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 1.0, "y": 0.0},
                            {"x": 1.0, "y": 1.0},
                            {"x": 0.0, "y": 1.0},
                        ]
                    },
                    "word_indexes": [index],
                }
            )

        words = [
            {
                "text": text,
                "confidence": 1.0,
                "bounding_polygon": {
                    "normalized_vertices": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 1.0, "y": 0.0},
                        {"x": 1.0, "y": 1.0},
                        {"x": 0.0, "y": 1.0},
                    ]
                },
            }
            for text in filter(None, result.full_text.splitlines())
        ]

        return {
            "text_detection_model_version": result.model_version,
            "key_value_detection_model_version": result.model_version,
            "table_detection_model_version": result.model_version,
            "pages": [
                {
                    "page_number": 1,
                    "lines": lines,
                    "words": words,
                    "document_fields": [
                        {
                            "field_type": field.field_type,
                            "field_label": {"name": field.label, "confidence": field.confidence},
                            "field_value": {
                                "value_type": "STRING",
                                "text": field.value,
                                "confidence": field.confidence,
                                "bounding_polygon": {
                                    "normalized_vertices": [
                                        {"x": 0.0, "y": 0.0},
                                        {"x": 1.0, "y": 0.0},
                                        {"x": 1.0, "y": 1.0},
                                        {"x": 0.0, "y": 1.0},
                                    ]
                                },
                                "word_indexes": [],
                            },
                        }
                        for field in result.fields
                    ],
                    "tables": [
                        {
                            "row_count": table.row_count,
                            "column_count": table.column_count,
                            "header_rows": [
                                {
                                    "cells": [
                                        {
                                            "text": text,
                                            "row_index": 0,
                                            "column_index": idx,
                                            "confidence": 1.0,
                                            "bounding_polygon": {
                                                "normalized_vertices": [
                                                    {"x": 0.0, "y": 0.0},
                                                    {"x": 1.0, "y": 0.0},
                                                    {"x": 1.0, "y": 1.0},
                                                    {"x": 0.0, "y": 1.0},
                                                ]
                                            },
                                            "word_indexes": [],
                                        }
                                        for idx, text in enumerate(table.header_rows)
                                    ]
                                }
                            ]
                            if table.header_rows
                            else [],
                            "body_rows": [
                                {
                                    "cells": [
                                        {
                                            "text": text,
                                            "row_index": row_idx + 1,
                                            "column_index": col_idx,
                                            "confidence": 1.0,
                                            "bounding_polygon": {
                                                "normalized_vertices": [
                                                    {"x": 0.0, "y": 0.0},
                                                    {"x": 1.0, "y": 0.0},
                                                    {"x": 1.0, "y": 1.0},
                                                    {"x": 0.0, "y": 1.0},
                                                ]
                                            },
                                            "word_indexes": [],
                                        }
                                        for col_idx, text in enumerate(row)
                                    ]
                                }
                                for row_idx, row in enumerate(table.body_rows)
                            ],
                            "footer_rows": [],
                            "confidence": table.confidence,
                            "bounding_polygon": {
                                "normalized_vertices": [
                                    {"x": 0.0, "y": 0.0},
                                    {"x": 1.0, "y": 0.0},
                                    {"x": 1.0, "y": 1.0},
                                    {"x": 0.0, "y": 1.0},
                                ]
                            },
                        }
                        for table in result.tables
                    ],
                }
            ],
        }

    raise ValueError(f"Unsupported feature/result combination: {feature}")


def record_fixture(
    *,
    image_path: Path,
    feature: str,
    response_payload: dict[str, Any],
    gallery_root: Path | None = None,
    image_id: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    gallery_root = Path(gallery_root) if gallery_root is not None else get_gallery_path()
    images_dir = gallery_root / "images"
    responses_dir = gallery_root / "responses"
    manifest_path = gallery_root / "manifest.json"

    images_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    image_path = Path(image_path)
    image_id = image_id or image_path.stem
    description = description or f"Recorded fixture for {image_id}"

    target_image = images_dir / image_path.name
    shutil.copy2(image_path, target_image)

    response_path = responses_dir / f"{image_id}_{feature}.json"
    response_path.write_text(json.dumps(response_payload, indent=2) + "\n")

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"images": []}

    existing = None
    for entry in manifest["images"]:
        if entry["id"] == image_id:
            existing = entry
            break

    if existing is None:
        existing = {
            "id": image_id,
            "filename": image_path.name,
            "description": description,
            "features": [feature],
        }
        manifest["images"].append(existing)
    else:
        existing["filename"] = image_path.name
        if description:
            existing["description"] = description
        existing["features"] = sorted(set(existing.get("features", [])) | {feature})

    manifest["images"] = sorted(manifest["images"], key=lambda item: item["id"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return existing
