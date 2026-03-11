"""Rich-based output formatting for terminal display of Vision AI results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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
