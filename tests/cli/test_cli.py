"""CLI tests using Typer's CliRunner — all in demo mode (no OCI creds)."""

import json

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


def test_cli_analyze_json_output():
    result = runner.invoke(
        app, ["analyze", "dog_closeup.jpg", "--demo", "--output-format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "classification" in data


def test_cli_gallery():
    result = runner.invoke(app, ["gallery"])
    assert result.exit_code == 0
    assert "dog_closeup" in result.output


def test_cli_config_demo():
    result = runner.invoke(app, ["config", "--demo"])
    assert result.exit_code == 0
