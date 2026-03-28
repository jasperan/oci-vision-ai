from __future__ import annotations

from collections import Counter
from typing import Any

from oci_vision.core.models import AnalysisReport
from oci_vision.eval.text import normalized_edit_distance


def summarize_report(report: AnalysisReport) -> dict[str, Any]:
    classification = report.classification.labels[0].name if report.classification and report.classification.labels else "—"
    top_confidence = (
        report.classification.labels[0].confidence_pct
        if report.classification and report.classification.labels
        else None
    )
    object_counts = Counter(obj.name for obj in (report.detection.objects if report.detection else []))
    document_fields = {
        field.label: field.value
        for field in (report.document.fields if report.document else [])
    }

    return {
        "image": report.image_path,
        "features": list(report.available_features),
        "feature_count": len(report.available_features),
        "top_label": classification,
        "top_confidence_pct": top_confidence,
        "object_count": sum(object_counts.values()),
        "object_counts": dict(object_counts),
        "ocr_line_count": len(report.text.lines) if report.text else 0,
        "ocr_preview": (report.text.full_text[:120] if report.text and report.text.full_text else ""),
        "face_count": len(report.faces.faces) if report.faces else 0,
        "document_field_count": len(document_fields),
        "document_fields": document_fields,
        "document_table_count": len(report.document.tables) if report.document else 0,
        "elapsed_seconds": report.elapsed_seconds,
    }


def report_insights(report: AnalysisReport) -> list[str]:
    summary = summarize_report(report)
    lines: list[str] = []

    if report.classification and report.classification.labels:
        lines.append(
            f"Top label: {summary['top_label']} ({summary['top_confidence_pct']:.1f}%)"
        )
    if report.detection and summary["object_count"]:
        object_counts = summary["object_counts"]
        top_objects = ", ".join(
            f"{name}×{count}" for name, count in list(object_counts.items())[:3]
        )
        lines.append(f"Detected {summary['object_count']} objects ({top_objects})")
    if report.text and report.text.full_text:
        lines.append(f"OCR extracted {summary['ocr_line_count']} line(s)")
    if report.faces and summary["face_count"]:
        lines.append(f"Found {summary['face_count']} face(s)")
    if report.document:
        lines.append(
            f"Document fields: {summary['document_field_count']}, tables: {summary['document_table_count']}"
        )

    return lines or ["No insights available for this report yet."]


def compare_reports(left: AnalysisReport, right: AnalysisReport) -> dict[str, Any]:
    left_summary = summarize_report(left)
    right_summary = summarize_report(right)

    left_features = set(left_summary["features"])
    right_features = set(right_summary["features"])

    object_names = sorted(set(left_summary["object_counts"]) | set(right_summary["object_counts"]))
    object_deltas = [
        {
            "name": name,
            "left": left_summary["object_counts"].get(name, 0),
            "right": right_summary["object_counts"].get(name, 0),
            "delta": right_summary["object_counts"].get(name, 0) - left_summary["object_counts"].get(name, 0),
        }
        for name in object_names
    ]

    field_names = sorted(set(left_summary["document_fields"]) | set(right_summary["document_fields"]))
    field_changes = [
        {
            "label": label,
            "left": left_summary["document_fields"].get(label),
            "right": right_summary["document_fields"].get(label),
            "changed": left_summary["document_fields"].get(label) != right_summary["document_fields"].get(label),
        }
        for label in field_names
        if left_summary["document_fields"].get(label) != right_summary["document_fields"].get(label)
    ]

    ocr_similarity = None
    if left.text and right.text:
        ocr_similarity = 1.0 - normalized_edit_distance(left.text.full_text, right.text.full_text)

    return {
        "left_image": left.image_path,
        "right_image": right.image_path,
        "shared_features": sorted(left_features & right_features),
        "left_only_features": sorted(left_features - right_features),
        "right_only_features": sorted(right_features - left_features),
        "top_label_change": {
            "left": left_summary["top_label"],
            "right": right_summary["top_label"],
            "changed": left_summary["top_label"] != right_summary["top_label"],
        },
        "object_count_delta": right_summary["object_count"] - left_summary["object_count"],
        "object_deltas": object_deltas,
        "ocr_similarity": ocr_similarity,
        "ocr_line_delta": right_summary["ocr_line_count"] - left_summary["ocr_line_count"],
        "face_count_delta": right_summary["face_count"] - left_summary["face_count"],
        "document_field_delta": right_summary["document_field_count"] - left_summary["document_field_count"],
        "document_field_changes": field_changes,
        "left_summary": left_summary,
        "right_summary": right_summary,
    }


def summarize_batch(reports: list[AnalysisReport]) -> dict[str, Any]:
    label_counts = Counter()
    object_counts = Counter()
    feature_coverage = Counter()
    total_faces = 0
    total_ocr_lines = 0
    total_document_fields = 0

    summaries = [summarize_report(report) for report in reports]
    for summary in summaries:
        if summary["top_label"] != "—":
            label_counts[summary["top_label"]] += 1
        object_counts.update(summary["object_counts"])
        feature_coverage.update(summary["features"])
        total_faces += summary["face_count"]
        total_ocr_lines += summary["ocr_line_count"]
        total_document_fields += summary["document_field_count"]

    return {
        "report_count": len(reports),
        "feature_coverage": dict(feature_coverage),
        "top_labels": dict(label_counts.most_common(5)),
        "object_counts": dict(object_counts.most_common(10)),
        "total_faces": total_faces,
        "total_ocr_lines": total_ocr_lines,
        "total_document_fields": total_document_fields,
        "reports": summaries,
    }
