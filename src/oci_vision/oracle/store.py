from __future__ import annotations

import array
import hashlib
import json
import math
import uuid
from typing import Any

import oracledb

from oci_vision.core.models import AnalysisReport
from oci_vision.oracle.config import OracleConfig
from oci_vision.oracle.connection import connect
from oci_vision.oracle.schema import init_schema


def _read_lob(value):
    if value is None:
        return None
    if isinstance(value, oracledb.LOB):
        return value.read()
    if hasattr(value, "read"):
        return value.read()
    return value


def embed_text(text: str, dimensions: int = 16) -> list[float]:
    buckets = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = digest[0] % dimensions
        sign = -1.0 if digest[1] % 2 else 1.0
        buckets[bucket] += sign * (1.0 + (digest[2] / 255.0))

    norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
    return [value / norm for value in buckets]


def _to_vector(values: list[float]) -> array.array:
    return array.array("f", values)


class OracleVisionStore:
    def __init__(self, conn):
        self.conn = conn

    def _extract_chunks(self, report: AnalysisReport) -> list[tuple[str, str]]:
        chunks: list[tuple[str, str]] = []
        if report.classification and report.classification.labels:
            chunks.append((
                "classification",
                " ".join(label.name for label in report.classification.labels[:10]),
            ))
        if report.detection and report.detection.objects:
            chunks.append((
                "detection",
                " ".join(obj.name for obj in report.detection.objects),
            ))
        if report.text and report.text.full_text:
            chunks.append(("text", report.text.full_text))
        if report.document:
            if report.document.full_text:
                chunks.append(("document_text", report.document.full_text))
            if report.document.fields:
                chunks.append((
                    "document_fields",
                    "\n".join(f"{field.label}: {field.value}" for field in report.document.fields),
                ))
        return [(kind, text) for kind, text in chunks if text.strip()]

    def store_report(self, report: AnalysisReport) -> str:
        run_id = uuid.uuid4().hex
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO vision_runs (run_id, image_path, elapsed_seconds, features_json, report_json)
            VALUES (:run_id, :image_path, :elapsed_seconds, :features_json, :report_json)
            """,
            {
                "run_id": run_id,
                "image_path": report.image_path,
                "elapsed_seconds": report.elapsed_seconds,
                "features_json": json.dumps(report.available_features),
                "report_json": report.model_dump_json(),
            },
        )

        for feature_kind, chunk_text in self._extract_chunks(report):
            cursor.execute(
                """
                INSERT INTO vision_vectors (vector_id, run_id, feature_kind, chunk_text, embedding)
                VALUES (:vector_id, :run_id, :feature_kind, :chunk_text, :embedding)
                """,
                {
                    "vector_id": uuid.uuid4().hex,
                    "run_id": run_id,
                    "feature_kind": feature_kind,
                    "chunk_text": chunk_text,
                    "embedding": _to_vector(embed_text(chunk_text)),
                },
            )

        self.conn.commit()
        return run_id

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_vec = _to_vector(embed_text(query))
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT vector_id, run_id, feature_kind, chunk_text,
                   1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS similarity
            FROM vision_vectors
            ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
            FETCH FIRST {int(limit)} ROWS ONLY
            """,
            {"query_vec": query_vec},
        )
        rows = cursor.fetchall()
        results = []
        for vector_id, run_id, feature_kind, chunk_text, similarity in rows:
            results.append(
                {
                    "vector_id": vector_id,
                    "run_id": run_id,
                    "feature_kind": feature_kind,
                    "chunk_text": _read_lob(chunk_text) or "",
                    "similarity": float(similarity),
                }
            )
        return results


def store_report_if_enabled(report: AnalysisReport) -> str | None:
    config = OracleConfig.from_env()
    if not config.enabled:
        return None

    conn = connect(config)
    try:
        init_schema(conn)
        return OracleVisionStore(conn).store_report(report)
    finally:
        conn.close()


def search_if_enabled(query: str, limit: int = 5) -> list[dict[str, Any]]:
    config = OracleConfig.from_env()
    if not config.enabled:
        return []

    conn = connect(config)
    try:
        init_schema(conn)
        return OracleVisionStore(conn).search(query, limit=limit)
    finally:
        conn.close()
