from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oci_vision.core.exports import save_overlay_image, write_html_report, write_json_report
from oci_vision.core.insights import compare_reports, report_insights, summarize_batch, summarize_report
from oci_vision.gallery import load_manifest
from oci_vision.workflows import (
    archive_search_workflow,
    inspection_workflow,
    receipt_workflow,
    shelf_audit_workflow,
)

SHOWCASE_COMPARE_SPECS = [
    {
        "slug": "dog-vs-sign",
        "title": "Animal vs sign",
        "left": "dog_closeup.jpg",
        "right": "sign_board.png",
    },
    {
        "slug": "invoice-vs-sign",
        "title": "Structured document vs OCR sign",
        "left": "invoice_demo.png",
        "right": "sign_board.png",
    },
]


def _analysis_command(filename: str, *, demo: bool) -> str:
    command = f"oci-vision analyze {filename}"
    return f"{command} --demo" if demo else command


def _build_headlines(
    *,
    gallery_items: list[dict[str, Any]],
    batch_summary: dict[str, Any],
    workflow_results: dict[str, dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> list[str]:
    headlines = [
        f"{len(gallery_items)} curated demo assets cover {len(batch_summary['feature_coverage'])} vision feature(s).",
        (
            f"Batch mode sees {batch_summary['total_faces']} face(s), "
            f"{batch_summary['total_ocr_lines']} OCR line(s), and "
            f"{batch_summary['total_document_fields']} extracted document field(s)."
        ),
    ]

    receipt_fields = workflow_results["receipt"].get("fields", {})
    invoice_number = receipt_fields.get("Invoice Number")
    if invoice_number:
        headlines.append(f"Receipt workflow extracts invoice number {invoice_number}.")

    archive_matches = workflow_results["archive_search"].get("match_count", 0)
    headlines.append(f"Archive search finds {archive_matches} matching document(s) for INV-1001.")

    changed_labels = [
        item["summary"]["top_label_change"]
        for item in comparisons
        if item["summary"]["top_label_change"]["changed"]
    ]
    if changed_labels:
        first_change = changed_labels[0]
        headlines.append(
            f"Preset comparison highlights a label shift from {first_change['left']} to {first_change['right']}."
        )

    return headlines


def build_showcase_snapshot(client, *, archive_query: str = "INV-1001") -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_manifest()
    reports: dict[str, Any] = {}
    gallery_items: list[dict[str, Any]] = []

    for entry in manifest["images"]:
        requested_features = entry.get("features") or "all"
        report = client.analyze(entry["filename"], features=requested_features)
        reports[entry["filename"]] = report
        gallery_items.append(
            {
                "id": entry["id"],
                "filename": entry["filename"],
                "description": entry.get("description", ""),
                "recommended_features": list(entry.get("features", [])),
                "command": _analysis_command(entry["filename"], demo=client.is_demo),
                "summary": summarize_report(report),
                "insights": report_insights(report),
            }
        )

    batch_summary = summarize_batch(list(reports.values()))

    comparisons: list[dict[str, Any]] = []
    for spec in SHOWCASE_COMPARE_SPECS:
        left_report = reports[spec["left"]]
        right_report = reports[spec["right"]]
        comparisons.append(
            {
                "slug": spec["slug"],
                "title": spec["title"],
                "summary": compare_reports(left_report, right_report),
            }
        )

    workflow_results = {
        "receipt": receipt_workflow(client, "invoice_demo.png"),
        "shelf": shelf_audit_workflow(client, "dog_closeup.jpg"),
        "inspection": inspection_workflow(client, "dog_closeup.jpg"),
        "archive_search": archive_search_workflow(client, ["invoice_demo.png"], query=archive_query),
    }

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo": client.is_demo,
        "asset_count": len(gallery_items),
        "workflow_count": len(workflow_results),
        "comparison_count": len(comparisons),
        "gallery": gallery_items,
        "batch": batch_summary,
        "comparisons": comparisons,
        "workflows": workflow_results,
        "commands": {
            "showcase": "oci-vision showcase --demo" if client.is_demo else "oci-vision showcase",
            "batch": "oci-vision batch dog_closeup.jpg sign_board.png invoice_demo.png --demo --output-format json"
            if client.is_demo
            else "oci-vision batch <images> --output-format json",
            "cockpit": "oci-vision cockpit --demo",
            "web": "oci-vision web --demo",
        },
    }
    snapshot["headlines"] = _build_headlines(
        gallery_items=gallery_items,
        batch_summary=batch_summary,
        workflow_results=workflow_results,
        comparisons=comparisons,
    )

    return snapshot, reports


def _render_showcase_html(snapshot: dict[str, Any]) -> str:
    esc = html.escape
    gallery_cards: list[str] = []
    for item in snapshot["gallery"]:
        summary = item["summary"]
        feature_badges = "".join(
            f"<span class='badge'>{esc(feature)}</span>"
            for feature in item["recommended_features"]
        )
        stem = Path(item["filename"]).stem
        gallery_cards.append(
            f"""
            <section class="card">
              <div class="card-header">
                <div>
                  <h3>{esc(item['filename'])}</h3>
                  <p class="muted">{esc(item['description'])}</p>
                </div>
                <div class="badge-row">{feature_badges}</div>
              </div>
              <img src="overlays/{esc(stem)}.png" alt="Overlay for {esc(item['filename'])}" class="overlay" />
              <div class="stats-grid">
                <div><span class="label">Top label</span><strong>{esc(summary['top_label'])}</strong></div>
                <div><span class="label">Objects</span><strong>{summary['object_count']}</strong></div>
                <div><span class="label">OCR lines</span><strong>{summary['ocr_line_count']}</strong></div>
                <div><span class="label">Doc fields</span><strong>{summary['document_field_count']}</strong></div>
              </div>
              <p class="muted small">{esc(item['command'])}</p>
              <p><a href="reports/{esc(stem)}.html">Open full report</a> · <a href="reports/{esc(stem)}.json">JSON</a></p>
            </section>
            """
        )

    comparison_cards: list[str] = []
    for comparison in snapshot["comparisons"]:
        summary = comparison["summary"]
        comparison_cards.append(
            f"""
            <section class="card">
              <h3>{esc(comparison['title'])}</h3>
              <p class="muted">{esc(summary['left_image'])} → {esc(summary['right_image'])}</p>
              <ul>
                <li><strong>Shared:</strong> {esc(', '.join(summary['shared_features']) or 'none')}</li>
                <li><strong>Left only:</strong> {esc(', '.join(summary['left_only_features']) or 'none')}</li>
                <li><strong>Right only:</strong> {esc(', '.join(summary['right_only_features']) or 'none')}</li>
                <li><strong>Top label:</strong> {esc(summary['top_label_change']['left'])} → {esc(summary['top_label_change']['right'])}</li>
                <li><strong>Object delta:</strong> {summary['object_count_delta']}</li>
                <li><strong>OCR line delta:</strong> {summary['ocr_line_delta']}</li>
                <li><strong>Document field delta:</strong> {summary['document_field_delta']}</li>
              </ul>
            </section>
            """
        )

    workflow_cards: list[str] = []
    for workflow_name, payload in snapshot["workflows"].items():
        workflow_cards.append(
            f"""
            <section class="card">
              <h3>{esc(workflow_name.replace('_', ' ').title())}</h3>
              <pre>{esc(json.dumps(payload, indent=2))}</pre>
            </section>
            """
        )

    headline_items = "".join(f"<li>{esc(line)}</li>" for line in snapshot["headlines"])
    feature_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{count}</td></tr>"
        for name, count in snapshot["batch"]["feature_coverage"].items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OCI Vision AI Showcase</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card: #1e293b;
      --muted: #94a3b8;
      --text: #e2e8f0;
      --accent: #22d3ee;
      --border: rgba(148, 163, 184, 0.3);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem 1rem 4rem;
    }}
    h1, h2, h3 {{ margin-top: 0; }}
    a {{ color: var(--accent); }}
    pre {{
      overflow-x: auto;
      white-space: pre-wrap;
      background: rgba(15, 23, 42, 0.6);
      border-radius: 0.75rem;
      padding: 1rem;
    }}
    .hero, .card {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--border);
      border-radius: 1rem;
      padding: 1.25rem;
    }}
    .hero {{ margin-bottom: 1.5rem; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 0.875rem; }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .badge {{
      display: inline-block;
      border: 1px solid rgba(34, 211, 238, 0.4);
      color: var(--accent);
      padding: 0.25rem 0.625rem;
      border-radius: 999px;
      font-size: 0.75rem;
    }}
    .section {{
      margin-top: 2rem;
    }}
    .grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .overlay {{
      width: 100%;
      border-radius: 0.75rem;
      margin: 1rem 0;
      border: 1px solid var(--border);
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.75rem;
      margin-bottom: 1rem;
    }}
    .label {{
      display: block;
      color: var(--muted);
      font-size: 0.75rem;
      margin-bottom: 0.125rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 0.5rem;
      border-bottom: 1px solid var(--border);
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p class="muted small">Generated at {esc(snapshot['generated_at'])}</p>
      <h1>OCI Vision AI Showcase</h1>
      <p>A single offline summary of the repo’s gallery, comparisons, workflows, and generated artifacts.</p>
      <ul>{headline_items}</ul>
      <p>
        <a href="showcase_summary.json">showcase_summary.json</a> ·
        <a href="batch_summary.json">batch_summary.json</a> ·
        <a href="workflow_summaries.json">workflow_summaries.json</a> ·
        <a href="comparisons.json">comparisons.json</a>
      </p>
    </section>

    <section class="section">
      <h2>Feature coverage</h2>
      <div class="card">
        <table>
          <thead><tr><th>Feature</th><th>Count</th></tr></thead>
          <tbody>{feature_rows}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <h2>Gallery</h2>
      <div class="grid">{''.join(gallery_cards)}</div>
    </section>

    <section class="section">
      <h2>Comparisons</h2>
      <div class="grid">{''.join(comparison_cards)}</div>
    </section>

    <section class="section">
      <h2>Workflow packs</h2>
      <div class="grid">{''.join(workflow_cards)}</div>
    </section>
  </main>
</body>
</html>"""


def write_showcase_bundle(
    snapshot: dict[str, Any],
    reports: dict[str, Any],
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    root = Path(output_dir or "showcase_bundle")
    overlays_dir = root / "overlays"
    reports_dir = root / "reports"
    root.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = root / "showcase_summary.json"
    payload = json.dumps(snapshot, indent=2)
    json_path.write_text(payload, encoding="utf-8")
    (root / "showcase.json").write_text(payload, encoding="utf-8")
    batch_path = root / "batch_summary.json"
    batch_path.write_text(json.dumps(snapshot["batch"], indent=2), encoding="utf-8")
    workflow_path = root / "workflow_summaries.json"
    workflow_path.write_text(json.dumps(snapshot["workflows"], indent=2), encoding="utf-8")
    comparisons_path = root / "comparisons.json"
    comparisons_path.write_text(json.dumps(snapshot["comparisons"], indent=2), encoding="utf-8")

    for filename, report in reports.items():
        stem = Path(filename).stem
        write_html_report(report, reports_dir / f"{stem}.html")
        write_json_report(report, reports_dir / f"{stem}.json")
        save_overlay_image(report, filename, overlays_dir / f"{stem}.png")

    html_path = root / "index.html"
    html_path.write_text(_render_showcase_html(snapshot), encoding="utf-8")

    return {
        "root": root,
        "html": html_path,
        "json": json_path,
        "batch": batch_path,
        "workflows": workflow_path,
        "comparisons": comparisons_path,
        "reports": reports_dir,
        "overlays": overlays_dir,
    }


def build_showcase_bundle(client, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Compatibility wrapper that returns a portable bundle manifest for the CLI."""
    snapshot, reports = build_showcase_snapshot(client)
    bundle_paths = write_showcase_bundle(snapshot, reports, output_dir or "showcase")

    images: list[dict[str, Any]] = []
    for item in snapshot["gallery"]:
        stem = Path(item["filename"]).stem
        images.append(
            {
                "id": stem,
                "filename": item["filename"],
                "description": item["description"],
                "requested_features": item["recommended_features"],
                "available_features": item["summary"]["features"],
                "summary": item["summary"],
                "insights": item["insights"],
                "artifacts": {
                    "json": str(Path("reports") / f"{stem}.json"),
                    "html": str(Path("reports") / f"{stem}.html"),
                    "overlay": str(Path("overlays") / f"{stem}.png"),
                },
            }
        )

    return {
        "generated_at": snapshot["generated_at"],
        "demo": snapshot["demo"],
        "image_count": snapshot["asset_count"],
        "images": images,
        "batch_summary_artifact": bundle_paths["batch"].name,
        "comparison_artifact": bundle_paths["comparisons"].name,
        "workflow_artifact": bundle_paths["workflows"].name,
        "workflows": snapshot["workflows"],
        "summary_artifact": bundle_paths["json"].name,
        "index_artifact": bundle_paths["html"].name,
    }
