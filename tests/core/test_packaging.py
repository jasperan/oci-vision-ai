from __future__ import annotations

import tomllib
from pathlib import Path


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
