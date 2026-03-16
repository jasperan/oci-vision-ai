from __future__ import annotations

import html
from typing import Any


def render_eval_report(kind: str, metrics: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in metrics.items()
    )
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>OCI Vision Eval Report — {html.escape(kind)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.6rem; text-align: left; }}
    th {{ width: 35%; background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>OCI Vision Evaluation Report</h1>
  <p>Kind: <strong>{html.escape(kind)}</strong></p>
  <table>{rows}</table>
</body>
</html>"""
