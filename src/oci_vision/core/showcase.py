from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oci_vision.core.client import VisionClient
from oci_vision.core.exports import save_overlay_image, write_html_report, write_json_report
from oci_vision.core.insights import compare_reports, report_insights, summarize_batch, summarize_report
from oci_vision.gallery import load_manifest
from oci_vision.workflows import (
    archive_search_workflow,
    inspection_workflow,
    receipt_workflow,
    shelf_audit_workflow,
)


def build_showcase_bundle(client: VisionClient, output_dir: str | Path) -> dict[str, Any]:
    """Generate a portable showcase bundle for the bundled gallery assets."""
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    reports_by_filename = {}
    image_entries: list[dict[str, Any]] = []

    for entry in manifest.get("images", []):
        filename = entry["filename"]
        report = client.analyze(filename, features=entry.get("features") or "all")
        reports_by_filename[filename] = report

        json_path = write_json_report(report, base_dir / f"{entry['id']}_report.json")
        html_path = write_html_report(report, base_dir / f"{entry['id']}_report.html")
        overlay_path = base_dir / f"{entry['id']}_overlay.png"

        overlay_artifact: str | None = None
        try:
            save_overlay_image(report, filename, overlay_path)
            overlay_artifact = overlay_path.name
        except Exception:
            overlay_artifact = None

        image_entries.append(
            {
                "id": entry["id"],
                "filename": filename,
                "description": entry.get("description", ""),
                "requested_features": list(entry.get("features", [])),
                "available_features": list(report.available_features),
                "summary": summarize_report(report),
                "insights": report_insights(report),
                "artifacts": {
                    "json": json_path.name,
                    "html": html_path.name,
                    "overlay": overlay_artifact,
                },
            }
        )

    reports = list(reports_by_filename.values())
    batch_summary = summarize_batch(reports)
    batch_path = base_dir / "batch_summary.json"
    batch_path.write_text(json.dumps(batch_summary, indent=2), encoding="utf-8")

    comparison = compare_reports(
        reports_by_filename["dog_closeup.jpg"],
        reports_by_filename["sign_board.png"],
    )
    comparison_path = base_dir / "comparison_dog_closeup_vs_sign_board.json"
    comparison_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    workflows = {
        "receipt": receipt_workflow(client, "invoice_demo.png"),
        "shelf": shelf_audit_workflow(client, "dog_closeup.jpg"),
        "inspection": inspection_workflow(client, "dog_closeup.jpg"),
        "archive-search": archive_search_workflow(client, ["invoice_demo.png"], query="INV-1001"),
    }
    workflows_path = base_dir / "workflow_summaries.json"
    workflows_path.write_text(json.dumps(workflows, indent=2), encoding="utf-8")

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo": client.is_demo,
        "image_count": len(image_entries),
        "images": image_entries,
        "batch_summary_artifact": batch_path.name,
        "comparison_artifact": comparison_path.name,
        "workflow_artifact": workflows_path.name,
        "workflows": workflows,
        "summary_artifact": "showcase_summary.json",
        "index_artifact": "index.html",
    }

    summary_path = base_dir / "showcase_summary.json"
    summary_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    index_path = base_dir / "index.html"
    index_path.write_text(_build_showcase_index(bundle), encoding="utf-8")
    return bundle


def _build_showcase_index(bundle: dict[str, Any]) -> str:
    esc = html.escape
    cards = []
    for entry in bundle["images"]:
        artifacts = entry["artifacts"]
        links = [
            f'<a href="{esc(artifacts["json"])}">JSON report</a>',
            f'<a href="{esc(artifacts["html"])}">HTML report</a>',
        ]
        if artifacts["overlay"]:
            links.append(f'<a href="{esc(artifacts["overlay"])}">Overlay image</a>')
        cards.append(
            f"""
            <section class="card">
              <h2>{esc(entry['filename'])}</h2>
              <p>{esc(entry['description'])}</p>
              <p><strong>Features:</strong> {esc(', '.join(entry['available_features']))}</p>
              <ul>
                {''.join(f'<li>{esc(line)}</li>' for line in entry['insights'])}
              </ul>
              <p>{' · '.join(links)}</p>
            </section>
            """
        )

    workflow_rows = "".join(
        f"<tr><td>{esc(name)}</td><td><pre>{esc(json.dumps(payload, indent=2))}</pre></td></tr>"
        for name, payload in bundle["workflows"].items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OCI Vision AI Showcase Bundle</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
    .card {{ border: 1px solid #d0d7de; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }}
    a {{ color: #0969da; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border: 1px solid #d0d7de; padding: 0.75rem; vertical-align: top; }}
    pre {{ margin: 0; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>OCI Vision AI Showcase Bundle</h1>
  <p><strong>Generated:</strong> {esc(bundle['generated_at'])}</p>
  <p><strong>Mode:</strong> {'demo' if bundle['demo'] else 'live'}</p>
  <p>
    <a href="{esc(bundle['summary_artifact'])}">Summary JSON</a> ·
    <a href="{esc(bundle['batch_summary_artifact'])}">Batch summary</a> ·
    <a href="{esc(bundle['comparison_artifact'])}">Comparison snapshot</a> ·
    <a href="{esc(bundle['workflow_artifact'])}">Workflow summaries</a>
  </p>
  {''.join(cards)}
  <section class="card">
    <h2>Workflow outputs</h2>
    <table>
      <thead><tr><th>Workflow</th><th>Output</th></tr></thead>
      <tbody>{workflow_rows}</tbody>
    </table>
  </section>
</body>
</html>"""
