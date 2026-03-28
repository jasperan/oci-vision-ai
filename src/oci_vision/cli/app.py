"""OCI Vision AI — Typer CLI application.

Entry point registered in pyproject.toml as ``oci-vision``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from oci_vision.cli.formatters import format_report
from oci_vision.core.client import VisionClient
from oci_vision.core.exports import save_overlay_image, write_html_report
from oci_vision.core.models import AnalysisReport, DetectionResult, DocumentResult, TextDetectionResult
from oci_vision.core.recording import record_fixture, serialize_feature_result
from oci_vision.eval import (
    evaluate_detection_result,
    evaluate_document_result,
    line_accuracy,
    render_eval_report,
    text_similarity,
)
from oci_vision.gallery import load_manifest
from oci_vision.oracle import search_if_enabled, store_report_if_enabled
from oci_vision.workflows import (
    archive_search_workflow,
    inspection_workflow,
    receipt_workflow,
    shelf_audit_workflow,
)

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
    out_path = write_html_report(report)
    console.print(f"[green]HTML report saved to:[/green] {out_path.absolute()}")


def _load_eval_payload(kind: str, path: str):
    payload = Path(path).read_text()
    if kind == "detection":
        return DetectionResult.model_validate_json(payload)
    if kind == "text":
        return TextDetectionResult.model_validate_json(payload)
    if kind == "document":
        return DocumentResult.model_validate_json(payload)
    raise typer.BadParameter(f"Unsupported eval kind: {kind}")


def _run_vision_call(action, *, label: str = "request"):
    try:
        return action()
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except TimeoutError as exc:
        console.print(f"[red]Error:[/red] {label} timed out: {exc}")
        raise typer.Exit(code=1) from exc
    except ConnectionError as exc:
        console.print(f"[red]Error:[/red] could not reach the OCI Vision service: {exc}")
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def analyze(
    image: str = typer.Argument(..., help="Image path or gallery name (e.g. dog_closeup.jpg)"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode (no OCI credentials needed)"),
    features: Optional[str] = typer.Option(None, "--features", help="Comma-separated features: classification,detection,text,faces,document"),
    model_id: Optional[str] = typer.Option(None, "--model-id", help="Optional OCI custom model OCID for classification/detection"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
    save_overlay: Optional[str] = typer.Option(None, "--save-overlay", help="Save annotated image to this path"),
) -> None:
    """Analyse an image with all OCI Vision AI features."""
    client = _build_client(demo)

    feat_list: list[str] | str = "all"
    if features:
        feat_list = [f.strip() for f in features.split(",")]

    report = _run_vision_call(
        lambda: client.analyze(image, features=feat_list, model_id=model_id),
        label="analysis",
    )
    _output_report(report, output_format, demo)
    stored_run_id = store_report_if_enabled(report)
    if stored_run_id and output_format not in {"json", "html"}:
        console.print(f"[dim]Stored run in Oracle:[/dim] {stored_run_id}")

    if save_overlay:
        _save_overlay(report, image, save_overlay)


@app.command()
def classify(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    model_id: Optional[str] = typer.Option(None, "--model-id", help="Optional OCI custom model OCID"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run image classification only."""
    client = _build_client(demo)
    result = _run_vision_call(
        lambda: client.classify(image, model_id=model_id),
        label="classification",
    )
    report = AnalysisReport(image_path=image, classification=result)
    _output_report(report, output_format, demo)


@app.command()
def detect(
    image: str = typer.Argument(..., help="Image path or gallery name"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    model_id: Optional[str] = typer.Option(None, "--model-id", help="Optional OCI custom model OCID"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
) -> None:
    """Run object detection only."""
    client = _build_client(demo)
    result = _run_vision_call(
        lambda: client.detect_objects(image, model_id=model_id),
        label="detection",
    )
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
    result = _run_vision_call(lambda: client.detect_text(image), label="text detection")
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
    result = _run_vision_call(lambda: client.detect_faces(image), label="face detection")
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
    result = _run_vision_call(
        lambda: client.analyze_document(image),
        label="document analysis",
    )
    report = AnalysisReport(image_path=image, document=result)
    _output_report(report, output_format, demo)


@app.command("eval")
def eval_results(
    kind: str = typer.Argument(..., help="Result kind: detection, text, or document"),
    prediction_json: str = typer.Argument(..., help="Prediction result JSON path"),
    truth_json: str = typer.Argument(..., help="Ground-truth result JSON path"),
    output_format: str = typer.Option("rich", "--output-format", help="Output format: rich, json, or html"),
    iou_threshold: float = typer.Option(0.5, "--iou-threshold", help="IoU threshold for detection metrics"),
    html_out: Optional[str] = typer.Option(None, "--html-out", help="Optional HTML output path"),
) -> None:
    """Evaluate normalized prediction results against ground truth."""
    kind = kind.strip().lower()
    prediction = _load_eval_payload(kind, prediction_json)
    truth = _load_eval_payload(kind, truth_json)

    if kind == "detection":
        metrics = evaluate_detection_result(prediction, truth, iou_threshold=iou_threshold)
    elif kind == "text":
        metrics = {
            "text_similarity": text_similarity(prediction, truth),
            "line_accuracy": line_accuracy(prediction, truth),
        }
    elif kind == "document":
        metrics = evaluate_document_result(prediction, truth)
    else:
        raise typer.BadParameter(f"Unsupported eval kind: {kind}")

    if output_format == "json":
        print(json.dumps(metrics, indent=2))
        return

    if output_format == "html":
        html_text = render_eval_report(kind, metrics)
        out_path = Path(html_out or f"eval_{kind}.html")
        out_path.write_text(html_text)
        console.print(f"[green]Evaluation report saved to:[/green] {out_path}")
        return

    console.print(Panel.fit(f"OCI Vision eval: {kind}", border_style="cyan"))
    for key, value in metrics.items():
        console.print(f"[bold]{key}:[/bold] {value}")


@app.command("search-runs")
def search_runs_command(
    query: str = typer.Argument(..., help="Semantic search query"),
    limit: int = typer.Option(5, "--limit", help="Maximum number of results"),
) -> None:
    """Search Oracle-backed stored runs when Oracle integration is enabled."""
    results = search_if_enabled(query, limit=limit)
    if not results:
        console.print("[]")
        return
    console.print(json.dumps(results, indent=2))


@app.command("workflow")
def workflow_command(
    kind: str = typer.Argument(..., help="Workflow kind: receipt, shelf, inspection, archive-search"),
    image: str = typer.Argument(..., help="Image path or comma-separated image list for archive-search"),
    demo: bool = typer.Option(False, "--demo", help="Use demo mode"),
    query: Optional[str] = typer.Option(None, "--query", help="Archive-search query"),
) -> None:
    """Run an opinionated workflow pack."""
    client = _build_client(demo)
    kind = kind.strip().lower()

    if kind == "receipt":
        summary = _run_vision_call(lambda: receipt_workflow(client, image), label="receipt workflow")
    elif kind == "shelf":
        summary = _run_vision_call(lambda: shelf_audit_workflow(client, image), label="shelf workflow")
    elif kind == "inspection":
        summary = _run_vision_call(lambda: inspection_workflow(client, image), label="inspection workflow")
    elif kind == "archive-search":
        if not query:
            raise typer.BadParameter("--query is required for archive-search")
        summary = _run_vision_call(
            lambda: archive_search_workflow(
                client,
                [part.strip() for part in image.split(",") if part.strip()],
                query=query,
            ),
            label="archive-search workflow",
        )
    else:
        raise typer.BadParameter(f"Unsupported workflow kind: {kind}")

    console.print(json.dumps(summary, indent=2))


@app.command("record-demo")
def record_demo(
    image: str = typer.Argument(..., help="Image path to register in the gallery"),
    feature: str = typer.Option(..., "--feature", help="Feature name: classification, detection, text, faces, or document"),
    response_json: Optional[str] = typer.Option(None, "--response-json", help="Existing JSON response file to import instead of calling OCI"),
    image_id: Optional[str] = typer.Option(None, "--image-id", help="Gallery image id (defaults to file stem)"),
    description: Optional[str] = typer.Option(None, "--description", help="Gallery description"),
    gallery_root: Optional[str] = typer.Option(None, "--gallery-root", help="Override gallery root for writing fixtures"),
) -> None:
    """Record a new demo fixture into the gallery."""
    image_path = Path(image)
    if not image_path.is_file():
        console.print(f"[red]Error:[/red] image not found: {image}")
        raise typer.Exit(code=1)

    feature = feature.strip().lower()
    if feature not in {"classification", "detection", "text", "faces", "document"}:
        console.print(f"[red]Error:[/red] unsupported feature: {feature}")
        raise typer.Exit(code=1)

    if response_json:
        response_payload = json.loads(Path(response_json).read_text())
    else:
        client = VisionClient(demo=False)
        if feature == "classification":
            result = _run_vision_call(
                lambda: client.classify(str(image_path)),
                label="classification",
            )
        elif feature == "detection":
            result = _run_vision_call(
                lambda: client.detect_objects(str(image_path)),
                label="detection",
            )
        elif feature == "text":
            result = _run_vision_call(lambda: client.detect_text(str(image_path)), label="text detection")
        elif feature == "faces":
            result = _run_vision_call(lambda: client.detect_faces(str(image_path)), label="face detection")
        else:
            result = _run_vision_call(
                lambda: client.analyze_document(str(image_path)),
                label="document analysis",
            )

        if result is None:
            console.print(f"[red]Error:[/red] OCI returned no result for feature: {feature}")
            raise typer.Exit(code=1)

        response_payload = serialize_feature_result(feature, result)

    entry = record_fixture(
        image_path=image_path,
        feature=feature,
        response_payload=response_payload,
        gallery_root=Path(gallery_root) if gallery_root else None,
        image_id=image_id,
        description=description,
    )

    console.print(
        f"[green]Recorded fixture[/green] [bold]{entry['id']}[/bold] "
        f"for feature [bold]{feature}[/bold]"
    )


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
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
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


@app.command()
def cockpit(
    demo: bool = typer.Option(False, "--demo", help="Start the cockpit in demo mode"),
    image: Optional[str] = typer.Option(None, "--image", help="Optional initial image or gallery filename"),
    features: Optional[str] = typer.Option(None, "--features", help="Optional comma-separated feature selection"),
    workflow: Optional[str] = typer.Option(None, "--workflow", help="Optional workflow to auto-run: receipt, shelf, inspection, archive-search"),
    query: Optional[str] = typer.Option(None, "--query", help="Archive-search query or initial workflow query"),
    screenshot: Optional[str] = typer.Option(None, "--screenshot", help="Write a deterministic SVG cockpit screenshot and exit"),
) -> None:
    """Launch the interactive demo cockpit or capture a deterministic screenshot."""
    if screenshot and Path(screenshot).suffix.lower() != ".svg":
        raise typer.BadParameter("Textual screenshots are SVG files. Please use a .svg output path.")

    if workflow and workflow.strip().lower() == "archive-search" and not query:
        raise typer.BadParameter("--query is required for archive-search")

    try:
        from oci_vision.tui.app import CockpitConfig, VisionCockpitApp, capture_cockpit_screenshot
        from oci_vision.tui.services import ALL_FEATURES, WORKFLOW_NAMES
    except ImportError as exc:
        console.print(
            "[red]Error:[/red] cockpit mode requires the [bold]textual[/bold] dependency. "
            "Install with: [dim]python -m pip install -e '.[all]'[/dim]"
        )
        raise typer.Exit(code=1) from exc

    parsed_features = [part.strip() for part in features.split(",") if part.strip()] if features else None
    if parsed_features is not None:
        invalid_features = [feature for feature in parsed_features if feature not in ALL_FEATURES]
        if invalid_features:
            raise typer.BadParameter(
                f"Unsupported feature(s): {', '.join(invalid_features)}. Valid choices: {', '.join(ALL_FEATURES)}"
            )
        if not parsed_features:
            raise typer.BadParameter("--features must include at least one valid feature")

    if workflow and workflow.strip().lower() not in WORKFLOW_NAMES:
        raise typer.BadParameter(
            f"Unsupported workflow: {workflow}. Valid choices: {', '.join(WORKFLOW_NAMES)}"
        )

    config = CockpitConfig(
        demo=demo,
        image=image,
        features=parsed_features,
        workflow=workflow,
        query=query,
        screenshot_path=screenshot,
    )

    try:
        if screenshot:
            out_path = capture_cockpit_screenshot(config)
            console.print(f"[green]Cockpit screenshot saved to:[/green] {out_path}")
            return

        VisionCockpitApp(config).run()
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Overlay saving helper
# ---------------------------------------------------------------------------

def _save_overlay(report: AnalysisReport, image_path: str, output_path: str) -> None:
    """Save annotated image with visual overlays."""
    try:
        out_path = save_overlay_image(report, image_path, output_path)
        console.print(f"[green]Overlay saved to:[/green] {out_path}")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/yellow] Could not save overlay: {exc}")
