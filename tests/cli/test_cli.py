"""CLI tests using Typer's CliRunner — all in demo mode (no OCI creds)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from oci_vision.cli.app import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "OCI Vision" in result.output or "oci-vision" in result.output


def test_cli_analyze_demo():
    result = runner.invoke(app, ["analyze", "dog_closeup.jpg", "--demo"])
    assert result.exit_code == 0
    assert "Dog" in result.output


def test_cli_classify_demo():
    result = runner.invoke(app, ["classify", "dog_closeup.jpg", "--demo"])
    assert result.exit_code == 0
    assert "Dog" in result.output


def test_cli_detect_demo():
    result = runner.invoke(app, ["detect", "dog_closeup.jpg", "--demo"])
    assert result.exit_code == 0
    assert "Dog" in result.output


def test_cli_ocr_demo():
    result = runner.invoke(app, ["ocr", "sign_board.png", "--demo"])
    assert result.exit_code == 0
    assert "STOP" in result.output


def test_cli_faces_demo():
    result = runner.invoke(app, ["faces", "portrait_demo.png", "--demo"])
    assert result.exit_code == 0
    assert "Face" in result.output


def test_cli_document_demo():
    result = runner.invoke(app, ["document", "invoice_demo.png", "--demo"])
    assert result.exit_code == 0
    assert "Invoice Number" in result.output


def test_cli_classify_accepts_model_id_in_demo():
    result = runner.invoke(app, ["classify", "dog_closeup.jpg", "--demo", "--model-id", "ocid1.model.oc1..demo"])
    assert result.exit_code == 0
    assert "Dog" in result.output


def test_cli_analyze_json_output():
    result = runner.invoke(
        app, ["analyze", "dog_closeup.jpg", "--demo", "--output-format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "classification" in data


def test_cli_analyze_html_output_creates_report():
    with runner.isolated_filesystem():
        result = runner.invoke(
            app, ["analyze", "dog_closeup.jpg", "--demo", "--output-format", "html"]
        )
        report_path = Path("dog_closeup_report.html")

        assert result.exit_code == 0
        assert report_path.exists()
        assert "HTML report saved to" in result.output


def test_cli_analyze_save_overlay_creates_png():
    with runner.isolated_filesystem():
        overlay_path = Path("demo-overlay.png")
        result = runner.invoke(
            app,
            [
                "analyze",
                "dog_closeup.jpg",
                "--demo",
                "--save-overlay",
                str(overlay_path),
            ],
        )

        assert result.exit_code == 0
        assert overlay_path.exists()
        assert "Overlay saved to" in result.output


def test_cli_analyze_reports_missing_demo_asset_cleanly():
    result = runner.invoke(app, ["analyze", "missing-demo.png", "--demo"])

    assert result.exit_code == 1
    assert "Demo asset not found" in result.output


def test_cli_analyze_timeout_returns_user_error(monkeypatch):
    def explode(self, *args, **kwargs):
        raise TimeoutError("network stalled")

    monkeypatch.setattr("oci_vision.core.client.VisionClient.analyze", explode)
    result = runner.invoke(app, ["analyze", "dog_closeup.jpg", "--demo"])

    assert result.exit_code == 1
    assert "timed out" in result.output.lower()
    assert "network stalled" in result.output


def test_cli_web_defaults_to_localhost(monkeypatch):
    captured = {}

    def fake_run(app_obj, *, host, port, reload):
        captured.update(host=host, port=port, reload=reload)

    monkeypatch.setattr("uvicorn.run", fake_run)
    result = runner.invoke(app, ["web", "--demo"])

    assert result.exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8000
    assert captured["reload"] is False


def test_cli_gallery():
    result = runner.invoke(app, ["gallery"])
    assert result.exit_code == 0
    assert "dog_closeup" in result.output


def test_cli_search_runs_without_oracle_enabled(monkeypatch):
    monkeypatch.delenv("OCI_VISION_ENABLE_ORACLE", raising=False)
    result = runner.invoke(app, ["search-runs", "invoice"])
    assert result.exit_code == 0
    assert "[]" in result.output


def test_cli_config_demo():
    result = runner.invoke(app, ["config", "--demo"])
    assert result.exit_code == 0
