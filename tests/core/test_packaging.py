from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib


def test_pyproject_keeps_oci_out_of_base_dependencies():
    with Path("pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    dependencies = pyproject["project"]["dependencies"]
    assert all(not dependency.startswith("oci>=") for dependency in dependencies)


def test_pyproject_exposes_live_extra_for_oci_sdk():
    with Path("pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    live_dependencies = pyproject["project"]["optional-dependencies"]["live"]
    assert any(dependency.startswith("oci>=") for dependency in live_dependencies)


def test_gitignore_blocks_local_agent_artifacts():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".omx/" in gitignore
    assert "IMPLEMENTATION.md" in gitignore
    assert "PLAN.md" in gitignore
