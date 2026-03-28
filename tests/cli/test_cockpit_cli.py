from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner

from oci_vision.cli.app import app

runner = CliRunner()


def test_cli_cockpit_help():
    result = runner.invoke(app, ["cockpit", "--help"])

    assert result.exit_code == 0
    assert "cockpit" in result.output.lower()
    assert "screenshot" in result.output.lower()


def test_cli_cockpit_screenshot_mode_creates_svg(tmp_path: Path):
    screenshot_path = tmp_path / "cockpit.svg"

    result = runner.invoke(
        app,
        [
            "cockpit",
            "--demo",
            "--image",
            "dog_closeup.jpg",
            "--features",
            "classification,detection",
            "--screenshot",
            str(screenshot_path),
        ],
    )

    assert result.exit_code == 0
    assert screenshot_path.exists()
    assert "<svg" in screenshot_path.read_text(encoding="utf-8")


def test_cli_cockpit_screenshot_mode_is_deterministic(tmp_path: Path):
    first = tmp_path / "first.svg"
    second = tmp_path / "second.svg"
    snippet = """
from oci_vision.tui.app import CockpitConfig, capture_cockpit_screenshot
capture_cockpit_screenshot(
    CockpitConfig(
        demo=True,
        image='dog_closeup.jpg',
        features=['classification', 'detection'],
        screenshot_path={path!r},
    )
)
"""

    subprocess.run([sys.executable, "-c", snippet.format(path=str(first))], check=True)
    subprocess.run([sys.executable, "-c", snippet.format(path=str(second))], check=True)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_cli_cockpit_screenshot_requires_svg_extension(tmp_path: Path):
    screenshot_path = tmp_path / "cockpit.png"

    result = runner.invoke(
        app,
        ["cockpit", "--demo", "--screenshot", str(screenshot_path)],
    )

    assert result.exit_code != 0
    assert ".svg" in result.output


def test_cli_cockpit_archive_search_requires_query(tmp_path: Path):
    screenshot_path = tmp_path / "archive.svg"

    result = runner.invoke(
        app,
        [
            "cockpit",
            "--demo",
            "--workflow",
            "archive-search",
            "--screenshot",
            str(screenshot_path),
        ],
    )

    assert result.exit_code != 0
    assert "query" in result.output.lower()


def test_cli_cockpit_rejects_unknown_workflow():
    result = runner.invoke(
        app,
        ["cockpit", "--demo", "--workflow", "mystery-mode"],
    )

    assert result.exit_code != 0
    assert "unsupported workflow" in result.output.lower()


def test_cli_cockpit_rejects_unknown_features():
    result = runner.invoke(
        app,
        ["cockpit", "--demo", "--features", "classification,laser-beams"],
    )

    assert result.exit_code != 0
    assert "unsupported feature" in result.output.lower()
