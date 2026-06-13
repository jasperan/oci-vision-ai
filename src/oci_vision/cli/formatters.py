"""Rich-based output formatting for terminal display of Vision AI results."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from oci_vision.core.models import AnalysisReport

console = Console()


def _bar(fraction: float, width: int = 30) -> str:
    """Return a Unicode bar chart string like ``████████░░░░░░░░``."""
    filled = int(round(fraction * width))
    empty = width - filled
    return "\u2588" * filled + "\u2591" * empty


def _format_header(report: AnalysisReport, demo: bool = False) -> Panel:
    """Build a Rich Panel showing image path, mode, and elapsed time."""
    mode = "[bold yellow]Demo[/bold yellow]" if demo else "[bold green]Live[/bold green]"
    features_str = ", ".join(report.available_features) if report.available_features else "none"

    lines = [
        f"[bold]Image:[/bold] {report.image_path}",
        f"[bold]Mode:[/bold]  {mode}",
        f"[bold]Time:[/bold]  {report.elapsed_seconds:.3f}s",
        f"[bold]Features:[/bold] {features_str}",
    ]
    body = "\n".join(lines)
    return Panel(body, title="[bold cyan]OCI Vision AI Analysis[/bold cyan]", border_style="cyan")


def _format_classification(report: AnalysisReport) -> Panel | None:
    """Build a Rich Panel with horizontal bar charts for classification labels."""
    if report.classification is None:
        return None

    lines = []
    for label in report.classification.labels[:10]:
        pct = label.confidence_pct
        bar = _bar(label.confidence)
        lines.append(f"  {label.name:<25} {bar} {pct:>6.2f}%")

    if not lines:
        return None

    body = "\n".join(lines)
    return Panel(body, title="[bold magenta]Classification[/bold magenta]", border_style="magenta")


def _format_detection(report: AnalysisReport) -> Table | None:
    """Build a Rich Table for detected objects."""
    if report.detection is None:
        return None
    if not report.detection.objects:
        return None

    table = Table(title="[bold red]Object Detection[/bold red]", border_style="red")
    table.add_column("Object", style="bold")
    table.add_column("Confidence", justify="right")
    table.add_column("Location", justify="center")

    for obj in report.detection.objects:
        pct = f"{obj.confidence_pct:.1f}%"
        # Use a default image size for human_position (normalised so 1.0 x 1.0 works)
        pos = obj.bounding_polygon.human_position(1.0, 1.0)
        table.add_row(obj.name, pct, pos)

    return table


def _format_text(report: AnalysisReport) -> Panel | None:
    """Build a Rich Panel for OCR / text detection results."""
    if report.text is None:
        return None
    if not report.text.lines:
        return None

    lines = []
    for tl in report.text.lines:
        pct = round(tl.confidence * 100, 1)
        lines.append(f'  [italic]"{tl.text}"[/italic]  ({pct}%)')

    body = "\n".join(lines)
    return Panel(body, title="[bold green]Text / OCR[/bold green]", border_style="green")


def _format_faces(report: AnalysisReport) -> Panel | None:
    """Build a Rich Panel for face detection results."""
    if report.faces is None:
        return None

    face_count = len(report.faces.faces)
    total_landmarks = sum(len(f.landmarks) for f in report.faces.faces)

    body = f"  Faces detected: [bold]{face_count}[/bold]\n  Total landmarks: [bold]{total_landmarks}[/bold]"

    for i, face in enumerate(report.faces.faces, 1):
        pct = round(face.confidence * 100, 1)
        lm_count = len(face.landmarks)
        body += f"\n  Face {i}: {pct}% confidence, {lm_count} landmarks"

    return Panel(body, title="[bold blue]Face Detection[/bold blue]", border_style="blue")


def _format_document(report: AnalysisReport) -> Panel | None:
    """Build a Rich Panel for document AI results."""
    if report.document is None:
        return None

    field_count = len(report.document.fields)
    table_count = len(report.document.tables)

    lines = [
        f"  Fields: [bold]{field_count}[/bold]",
        f"  Tables: [bold]{table_count}[/bold]",
    ]

    for field in report.document.fields[:10]:
        pct = round(field.confidence * 100, 1)
        lines.append(f"  [{field.field_type}] {field.label}: {field.value} ({pct}%)")

    for i, tbl in enumerate(report.document.tables, 1):
        lines.append(f"  Table {i}: {tbl.row_count} rows x {tbl.column_count} cols")

    body = "\n".join(lines)
    return Panel(body, title="[bold yellow]Document AI[/bold yellow]", border_style="yellow")


def format_report(report: AnalysisReport, *, demo: bool = False) -> None:
    """Print a beautifully formatted Rich report to the terminal.

    Parameters
    ----------
    report : AnalysisReport
        The analysis results to display.
    demo : bool
        Whether the results came from demo mode (affects header badge).
    """
    console.print()
    console.print(_format_header(report, demo=demo))

    cls_panel = _format_classification(report)
    if cls_panel is not None:
        console.print(cls_panel)

    det_table = _format_detection(report)
    if det_table is not None:
        console.print(det_table)

    text_panel = _format_text(report)
    if text_panel is not None:
        console.print(text_panel)

    face_panel = _format_faces(report)
    if face_panel is not None:
        console.print(face_panel)

    doc_panel = _format_document(report)
    if doc_panel is not None:
        console.print(doc_panel)

    console.print()


def output_comparison(comparison: dict[str, Any], output_format: str) -> None:
    """Render a side-by-side comparison summary as JSON or Rich tables."""
    if output_format == "json":
        print(json.dumps(comparison, indent=2))
        return

    console.print(Panel.fit(
        f"Compare: {comparison['left_image']} vs {comparison['right_image']}",
        border_style="cyan",
    ))

    summary = Table(title="Comparison Summary", border_style="cyan")
    summary.add_column("Metric", style="bold")
    summary.add_column("Value")
    summary.add_row("Shared features", ", ".join(comparison["shared_features"]) or "none")
    summary.add_row("Left only", ", ".join(comparison["left_only_features"]) or "none")
    summary.add_row("Right only", ", ".join(comparison["right_only_features"]) or "none")
    summary.add_row(
        "Top label",
        f"{comparison['top_label_change']['left']} → {comparison['top_label_change']['right']}",
    )
    summary.add_row("Object delta", str(comparison["object_count_delta"]))
    summary.add_row("OCR line delta", str(comparison["ocr_line_delta"]))
    summary.add_row("Face delta", str(comparison["face_count_delta"]))
    summary.add_row("Document field delta", str(comparison["document_field_delta"]))
    if comparison["ocr_similarity"] is not None:
        summary.add_row("OCR similarity", f"{comparison['ocr_similarity']:.3f}")
    console.print(summary)

    if comparison["object_deltas"]:
        object_table = Table(title="Object Deltas", border_style="magenta")
        object_table.add_column("Object", style="bold")
        object_table.add_column("Left", justify="right")
        object_table.add_column("Right", justify="right")
        object_table.add_column("Δ", justify="right")
        for item in comparison["object_deltas"]:
            object_table.add_row(item["name"], str(item["left"]), str(item["right"]), str(item["delta"]))
        console.print(object_table)


def output_batch_summary(batch: dict, output_format: str) -> None:
    """Render an aggregate batch summary as JSON or Rich tables."""
    if output_format == "json":
        print(json.dumps(batch, indent=2))
        return

    console.print(Panel.fit(f"Batch analysis: {batch['report_count']} image(s)", border_style="cyan"))

    report_table = Table(title="Per-image Summary", border_style="cyan")
    report_table.add_column("Image", style="bold")
    report_table.add_column("Features")
    report_table.add_column("Top label")
    report_table.add_column("Objects", justify="right")
    report_table.add_column("OCR", justify="right")
    report_table.add_column("Doc fields", justify="right")
    for report in batch["reports"]:
        report_table.add_row(
            report["image"],
            ", ".join(report["features"]),
            report["top_label"],
            str(report["object_count"]),
            str(report["ocr_line_count"]),
            str(report["document_field_count"]),
        )
    console.print(report_table)

    aggregate = Table(title="Aggregate Summary", border_style="magenta")
    aggregate.add_column("Metric", style="bold")
    aggregate.add_column("Value")
    aggregate.add_row("Feature coverage", json.dumps(batch["feature_coverage"], indent=2))
    aggregate.add_row("Top labels", json.dumps(batch["top_labels"], indent=2))
    aggregate.add_row("Object counts", json.dumps(batch["object_counts"], indent=2))
    aggregate.add_row("Total faces", str(batch["total_faces"]))
    aggregate.add_row("Total OCR lines", str(batch["total_ocr_lines"]))
    aggregate.add_row("Total document fields", str(batch["total_document_fields"]))
    console.print(aggregate)


def output_showcase(snapshot: dict) -> None:
    """Render a showcase snapshot as a stack of Rich tables."""
    console.print(
        Panel.fit(
            f"OCI Vision AI showcase • {snapshot['asset_count']} assets • "
            f"{len(snapshot['batch']['feature_coverage'])} features • "
            f"{snapshot['workflow_count']} workflows",
            border_style="cyan",
        )
    )

    headline_table = Table(title="Headline Insights", border_style="cyan")
    headline_table.add_column("Insight")
    for line in snapshot["headlines"]:
        headline_table.add_row(line)
    console.print(headline_table)

    gallery_table = Table(title="Gallery Coverage", border_style="cyan")
    gallery_table.add_column("Image", style="bold")
    gallery_table.add_column("Features")
    gallery_table.add_column("Top label")
    gallery_table.add_column("Objects", justify="right")
    gallery_table.add_column("OCR", justify="right")
    gallery_table.add_column("Doc", justify="right")
    for item in snapshot["gallery"]:
        summary = item["summary"]
        gallery_table.add_row(
            item["filename"],
            ", ".join(item["recommended_features"]),
            summary["top_label"],
            str(summary["object_count"]),
            str(summary["ocr_line_count"]),
            str(summary["document_field_count"]),
        )
    console.print(gallery_table)

    workflow_table = Table(title="Workflow Packs", border_style="magenta")
    workflow_table.add_column("Workflow", style="bold")
    workflow_table.add_column("Key output")
    workflow_table.add_row(
        "receipt",
        snapshot["workflows"]["receipt"]["fields"].get("Invoice Number", "No invoice number"),
    )
    workflow_table.add_row(
        "shelf",
        json.dumps(snapshot["workflows"]["shelf"]["objects"], indent=2),
    )
    workflow_table.add_row(
        "inspection",
        json.dumps(snapshot["workflows"]["inspection"], indent=2),
    )
    workflow_table.add_row(
        "archive-search",
        json.dumps(snapshot["workflows"]["archive_search"], indent=2),
    )
    console.print(workflow_table)

    if snapshot["comparisons"]:
        comparison_table = Table(title="Preset Comparisons", border_style="green")
        comparison_table.add_column("Comparison", style="bold")
        comparison_table.add_column("Label shift")
        comparison_table.add_column("Object Δ", justify="right")
        comparison_table.add_column("OCR Δ", justify="right")
        comparison_table.add_column("Doc Δ", justify="right")
        for item in snapshot["comparisons"]:
            summary = item["summary"]
            comparison_table.add_row(
                item["title"],
                f"{summary['top_label_change']['left']} → {summary['top_label_change']['right']}",
                str(summary["object_count_delta"]),
                str(summary["ocr_line_delta"]),
                str(summary["document_field_delta"]),
            )
        console.print(comparison_table)
