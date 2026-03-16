from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from oci_vision.cli.app import app
from oci_vision.core.models import BoundingPolygon, DetectedObject, DetectionResult, Vertex

runner = CliRunner()


def _box(x1: float, y1: float, x2: float, y2: float) -> BoundingPolygon:
    return BoundingPolygon(
        normalized_vertices=[
            Vertex(x=x1, y=y1),
            Vertex(x=x2, y=y1),
            Vertex(x=x2, y=y2),
            Vertex(x=x1, y=y2),
        ]
    )


def test_cli_eval_detection_json(tmp_path: Path):
    pred = DetectionResult(
        model_version="1.0",
        objects=[DetectedObject(name="Dog", confidence=0.95, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4))],
    )
    truth = DetectionResult(
        model_version="1.0",
        objects=[DetectedObject(name="Dog", confidence=1.0, bounding_polygon=_box(0.1, 0.1, 0.4, 0.4))],
    )
    pred_path = tmp_path / "pred.json"
    truth_path = tmp_path / "truth.json"
    pred_path.write_text(pred.model_dump_json(indent=2))
    truth_path.write_text(truth.model_dump_json(indent=2))

    result = runner.invoke(
        app,
        [
            "eval",
            "detection",
            str(pred_path),
            str(truth_path),
            "--output-format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert '"precision": 1.0' in result.output
