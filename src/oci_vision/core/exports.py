from __future__ import annotations

import html
import json
from pathlib import Path

from PIL import Image

from oci_vision.core.insights import report_insights
from oci_vision.core.models import AnalysisReport
from oci_vision.core.renderer import render_overlay
from oci_vision.gallery import get_gallery_path


def build_html_report(report: AnalysisReport) -> str:
    """Build a self-contained HTML report for an analysis result."""
    esc = html.escape
    image_name = esc(Path(report.image_path).stem)

    features_html: list[str] = []
    insight_items = "".join(f"<li>{esc(line)}</li>" for line in report_insights(report))
    features_html.append(f"<h2>Insights</h2><ul>{insight_items}</ul>")
    if report.classification:
        rows = "".join(
            f"<tr><td>{esc(label.name)}</td><td>{label.confidence_pct:.1f}%</td></tr>"
            for label in report.classification.labels
        )
        features_html.append(
            f"<h2>Classification</h2><table border='1' cellpadding='4'>"
            f"<tr><th>Label</th><th>Confidence</th></tr>{rows}</table>"
        )

    if report.detection:
        rows = "".join(
            f"<tr><td>{esc(obj.name)}</td><td>{obj.confidence_pct:.1f}%</td></tr>"
            for obj in report.detection.objects
        )
        features_html.append(
            f"<h2>Object Detection</h2><table border='1' cellpadding='4'>"
            f"<tr><th>Object</th><th>Confidence</th></tr>{rows}</table>"
        )

    if report.text:
        lines = "".join(
            f"<p>&ldquo;{esc(line.text)}&rdquo; ({round(line.confidence * 100, 1)}%)</p>"
            for line in report.text.lines
        )
        features_html.append(f"<h2>Text / OCR</h2>{lines}")

    if report.faces:
        features_html.append(
            f"<h2>Face Detection</h2><p>{len(report.faces.faces)} face(s), "
            f"{sum(len(face.landmarks) for face in report.faces.faces)} landmarks</p>"
        )

    if report.document:
        doc_parts = [
            f"<h2>Document AI</h2><p>{len(report.document.fields)} fields, "
            f"{len(report.document.tables)} tables</p>"
        ]
        for field in report.document.fields:
            doc_parts.append(
                f"<p>{esc(field.field_type)}: {esc(field.label)} = {esc(field.value)}</p>"
            )
        features_html.append("\n".join(doc_parts))

    body = "\n".join(features_html) if features_html else "<p>No features analysed.</p>"
    safe_image_path = esc(report.image_path)
    safe_features = esc(", ".join(report.available_features))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset=\"utf-8\"><title>OCI Vision AI Report — {image_name}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th {{ background: #f0f0f0; }}
h1 {{ color: #1a73e8; }}
h2 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
</style></head>
<body>
<h1>OCI Vision AI Report</h1>
<p><strong>Image:</strong> {safe_image_path}<br>
<strong>Elapsed:</strong> {report.elapsed_seconds:.3f}s<br>
<strong>Features:</strong> {safe_features}</p>
{body}
</body></html>"""


def write_html_report(
    report: AnalysisReport,
    output_path: str | Path | None = None,
) -> Path:
    """Write a self-contained HTML report to disk and return the path."""
    out_path = Path(output_path or f"{Path(report.image_path).stem}_report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_html_report(report), encoding="utf-8")
    return out_path


def build_json_report_payload(report: AnalysisReport) -> dict:
    payload = report.model_dump()
    payload["insights"] = report_insights(report)
    return payload


def write_json_report(
    report: AnalysisReport,
    output_path: str | Path | None = None,
) -> Path:
    """Write the normalized JSON report to disk and return the path."""
    out_path = Path(output_path or f"{Path(report.image_path).stem}_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(build_json_report_payload(report), indent=2), encoding="utf-8")
    return out_path


def resolve_source_image_path(image_path: str | Path) -> Path:
    """Resolve a local image path, including bundled gallery fixtures."""
    source = Path(image_path)
    if source.is_file():
        return source

    gallery_candidate = get_gallery_path() / "images" / source.name
    if gallery_candidate.is_file():
        return gallery_candidate

    raise FileNotFoundError(f"Could not find image file: {image_path}")


def save_overlay_image(
    report: AnalysisReport,
    image_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Render an annotated overlay image and save it to disk."""
    source_path = resolve_source_image_path(image_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(source_path)
    try:
        rendered = render_overlay(image, report)
    finally:
        image.close()

    rendered.save(out_path)
    return out_path
