"""OCI Vision AI — Typer CLI application.

Entry point registered in pyproject.toml as ``oci-vision``.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from oci_vision.cli.formatters import format_report
from oci_vision.core.client import VisionClient
from oci_vision.core.models import AnalysisReport
from oci_vision.gallery import load_manifest

console = Console()

app = typer.Typer(
    name="oci-vision",
    help="OCI Vision AI — image analysis powered by Oracle Cloud Vision.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_client(demo: bool) -> VisionClient:
    """Create a VisionClient in demo or live mode."""
    return VisionClient(demo=demo)


def _output_report(
    report: AnalysisReport,
    output_format: str,
    demo: bool,
) -> None:
    """Dispatch the report to the chosen output format."""
    if output_format == "json":
        print(report.model_dump_json(indent=2))
    elif output_format == "html":
        _output_html(report)
    else:
        format_report(report, demo=demo)


def _output_html(report: AnalysisReport) -> None:
    """Generate a self-contained HTML report and write it to disk."""
    esc = html.escape
    image_name = esc(Path(report.image_path).stem)
    out_path = Path(f"{Path(report.image_path).stem}_report.html")

    features_html = []
    if report.classification:
        rows = "".join(
            f"<tr><td>{esc(l.name)}</td><td>{l.confidence_pct:.1f}%</td></tr>"
            for l in report.classification.labels
        )
        features_html.append(
            f"<h2>Classification</h2><table border='1' cellpadding='4'>"
            f"<tr><th>Label</th><th>Confidence</th></tr>{rows}</table>"
        )

    if report.detection:
        rows = "".join(
            f"<tr><td>{esc(o.name)}</td><td>{o.confidence_pct:.1f}%</td></tr>"
            for o in report.detection.objects
        )
        features_html.append(
            f"<h2>Object Detection</h2><table border='1' cellpadding='4'>"
            f"<tr><th>Object</th><th>Confidence</th></tr>{rows}</table>"
        )

    if report.text:
        lines = "".join(
            f"<p>&ldquo;{esc(l.text)}&rdquo; ({round(l.confidence*100,1)}%)</p>"
            for l in report.text.lines
        )
        features_html.append(f"<h2>Text / OCR</h2>{lines}")

    if report.faces:
        features_html.append(
            f"<h2>Face Detection</h2><p>{len(report.faces.faces)} face(s), "
            f"{sum(len(f.landmarks) for f in report.faces.faces)} landmarks</p>"
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
    safe_features = esc(', '.join(report.available_features))

    page = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>OCI Vision AI Report — {image_name}</title>
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

    out_path.write_text(page)
    console.print(f"[green]HTML report saved to:[/green] {out_path.absolute()}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def analyze(
    image: str = typer.Argument(..., help="Image path or gallery name (e.g. dog_closeup.jpg)"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode (no OCI credentials needed)"),
    features: Optional[str] = typer.Option(None, "--features", help="Comma-separated features: classification,detection,text,faces,document"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
    save_overlay: Optional[str] = typer.Option(None, "--save-overlay", help="Save annotated image to this path"),
) -> None:
    """Analyse an image with all OCI Vision AI features."""
    client = _build_client(demo)

    feat_list: list[str] | str = "all"
    if features:
        feat_list = [f.strip() for f in features.split(",")]

    report = client.analyze(image, features=feat_list)
    _output_report(report, output_format, demo)

    if save_overlay:
        _save_overlay(report, image, save_overlay)


@app.command()
def classify(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run image classification only."""
    client = _build_client(demo)
    result = client.classify(image)
    report = AnalysisReport(image_path=image, classification=result)
    _output_report(report, output_format, demo)


@app.command()
def detect(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run object detection only."""
    client = _build_client(demo)
    result = client.detect_objects(image)
    report = AnalysisReport(image_path=image, detection=result)
    _output_report(report, output_format, demo)


@app.command()
def ocr(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run text / OCR extraction only."""
    client = _build_client(demo)
    result = client.detect_text(image)
    report = AnalysisReport(image_path=image, text=result)
    _output_report(report, output_format, demo)


@app.command()
def faces(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run face detection only."""
    client = _build_client(demo)
    result = client.detect_faces(image)
    report = AnalysisReport(image_path=image, faces=result)
    _output_report(report, output_format, demo)


@app.command()
def document(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run document AI analysis only."""
    client = _build_client(demo)
    result = client.analyze_document(image)
    report = AnalysisReport(image_path=image, document=result)
    _output_report(report, output_format, demo)


@app.command()
def gallery() -> None:
    """List curated demo images with descriptions and example commands."""
    manifest = load_manifest()

    table = Table(title="[bold cyan]OCI Vision AI — Demo Gallery[/bold cyan]", border_style="cyan")
    table.add_column("ID", style="bold")
    table.add_column("Filename")
    table.add_column("Description")
    table.add_column("Features")
    table.add_column("Example Command", style="dim")

    for entry in manifest["images"]:
        table.add_row(
            entry["id"],
            entry["filename"],
            entry.get("description", ""),
            ", ".join(entry.get("features", [])),
            f"oci-vision analyze {entry['filename']} --demo",
        )

    console.print()
    console.print(table)
    console.print()


@app.command()
def config(
    demo: bool = typer.Option(False, "--demo", help="Check demo mode availability"),
    profile: Optional[str] = typer.Option(None, "--profile", help="OCI config profile to validate"),
) -> None:
    """Validate OCI credentials or check demo mode status."""
    if demo:
        console.print(Panel(
            "[bold green]Demo mode is always available.[/bold green]\n"
            "No OCI credentials required.\n\n"
            "Try: [dim]oci-vision analyze dog_closeup.jpg --demo[/dim]",
            title="[bold cyan]Configuration Check[/bold cyan]",
            border_style="cyan",
        ))
        return

    # Validate OCI credentials
    try:
        import oci
        cfg = oci.config.from_file(profile_name=profile) if profile else oci.config.from_file()
        oci.config.validate_config(cfg)
        console.print(Panel(
            f"[bold green]OCI configuration is valid.[/bold green]\n"
            f"Tenancy: {cfg.get('tenancy', 'N/A')}\n"
            f"Region:  {cfg.get('region', 'N/A')}\n"
            f"User:    {cfg.get('user', 'N/A')}",
            title="[bold cyan]OCI Credentials[/bold cyan]",
            border_style="green",
        ))
    except ImportError:
        console.print("[red]Error:[/red] oci package not installed. Install with: pip install oci")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address"),
    port: int = typer.Option(8000, "--port", help="Port number"),
    demo: bool = typer.Option(False, "--demo", help="Start in demo mode"),
) -> None:
    """Launch the web dashboard."""
    try:
        import uvicorn
        from oci_vision.web.app import create_app

        console.print(f"[bold cyan]Starting OCI Vision AI web dashboard[/bold cyan] on {host}:{port}")
        mode = "demo" if demo else "live"
        console.print(f"Mode: [bold]{mode}[/bold]")
        uvicorn.run(
            create_app(demo=demo),
            host=host,
            port=port,
            reload=False,
        )
    except ImportError:
        console.print("[red]Error:[/red] uvicorn not installed. Install with: pip install uvicorn")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Overlay saving helper
# ---------------------------------------------------------------------------

def _save_overlay(report: AnalysisReport, image_path: str, output_path: str) -> None:
    """Save annotated image with visual overlays."""
    try:
        from PIL import Image
        from oci_vision.core.renderer import render_overlay

        img_path = Path(image_path)
        if not img_path.is_file():
            # Try gallery path
            from oci_vision.gallery import get_gallery_path
            img_path = get_gallery_path() / "images" / Path(image_path).name
            if not img_path.is_file():
                console.print(f"[yellow]Warning:[/yellow] Cannot find image file for overlay: {image_path}")
                return

        img = Image.open(img_path)
        result = render_overlay(img, report)
        result.save(output_path)
        console.print(f"[green]Overlay saved to:[/green] {output_path}")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/yellow] Could not save overlay: {exc}")
