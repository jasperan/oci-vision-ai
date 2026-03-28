from __future__ import annotations

from typing import Sequence

from oci_vision.core.insights import compare_reports as core_compare_reports
from oci_vision.core.insights import summarize_report as core_summarize_report
from oci_vision.core.models import AnalysisReport


def summarize_report(report: AnalysisReport) -> dict[str, object]:
    return core_summarize_report(report)


def compare_reports(current: AnalysisReport, previous: AnalysisReport | None) -> dict[str, object]:
    if previous is None:
        return {
            "has_previous": False,
            "summary": "Run another analysis to unlock compare mode.",
            "top_label_delta": "—",
            "object_count_delta": "0",
            "ocr_line_delta": "0",
            "document_field_delta": "0",
        }

    comparison = core_compare_reports(previous, current)

    return {
        "has_previous": True,
        "summary": f"Previous run: {previous.image_path}",
        "top_label_delta": (
            f"{comparison['top_label_change']['left']} → {comparison['top_label_change']['right']}"
        ),
        "object_count_delta": _signed_delta(int(comparison["object_count_delta"])),
        "ocr_line_delta": _signed_delta(int(comparison["ocr_line_delta"])),
        "document_field_delta": _signed_delta(int(comparison["document_field_delta"])),
    }


def summarize_workflow_result(workflow_name: str, payload: dict) -> str:
    workflow_name = workflow_name.strip().lower()
    if workflow_name == "receipt":
        fields = payload.get("fields", {})
        lines = ["Receipt workflow", f"Fields: {payload.get('field_count', 0)}", f"Tables: {payload.get('table_count', 0)}"]
        for key, value in list(fields.items())[:5]:
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    if workflow_name == "shelf":
        lines = ["Shelf audit workflow", f"Objects: {payload.get('object_count', 0)}"]
        for key, value in payload.get("objects", {}).items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    if workflow_name == "inspection":
        lines = ["Inspection workflow"]
        labels = payload.get("classification", [])
        if labels:
            lines.append("Labels: " + ", ".join(labels))
        detections = payload.get("detection", {})
        if detections:
            lines.append("Detections: " + ", ".join(f"{key}={value}" for key, value in detections.items()))
        text = payload.get("text", "")
        if text:
            lines.append(f"OCR: {text[:80]}")
        return "\n".join(lines)

    if workflow_name == "archive-search":
        lines = ["Archive search workflow", f"Matches: {payload.get('match_count', 0)}"]
        for match in payload.get("matches", [])[:5]:
            lines.append(f"- {match.get('image')} ({match.get('field_count', 0)} fields)")
        return "\n".join(lines)

    return f"{workflow_name}: {payload}"


def push_history(
    history: Sequence[AnalysisReport],
    report: AnalysisReport,
    *,
    limit: int = 5,
) -> list[AnalysisReport]:
    return [report, *list(history)][:limit]


def history_lines(history: Sequence[AnalysisReport]) -> list[str]:
    return [
        f"{report.image_path} · {', '.join(report.available_features)} · {report.elapsed_seconds:.3f}s"
        for report in history
    ]


def _signed_delta(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)
