from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "dependency_audit.py"
SPEC = importlib.util.spec_from_file_location("dependency_audit_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_load_base_dependencies_reads_runtime_requirements():
    deps = MODULE.load_base_dependencies(Path("pyproject.toml"))

    assert any(dep.startswith("fastapi>=") for dep in deps)
    assert any(dep.startswith("textual>=") for dep in deps)
    assert all(not dep.startswith("oci>=") for dep in deps)


def test_partition_findings_moves_known_unresolved_pygments_issue():
    findings = [
        {
            "name": "pygments",
            "version": "2.19.2",
            "id": "CVE-2026-4539",
            "aliases": ["GHSA-5239-wwwm-4pmq"],
            "fix_versions": [],
            "description": "regex complexity issue",
        }
    ]

    actionable, unresolved = MODULE.partition_findings(findings)

    assert actionable == []
    assert len(unresolved) == 1
    assert unresolved[0]["name"] == "pygments"
    assert "No upstream fix is published yet" in unresolved[0]["reason"]


def test_partition_findings_keeps_fixable_issue_actionable():
    findings = [
        {
            "name": "pyopenssl",
            "version": "25.3.0",
            "id": "CVE-2026-27448",
            "aliases": [],
            "fix_versions": ["26.0.0"],
            "description": "fixable vuln",
        }
    ]

    actionable, unresolved = MODULE.partition_findings(findings)

    assert len(actionable) == 1
    assert unresolved == []


def test_render_markdown_includes_status_sections():
    markdown = MODULE.render_markdown(
        dependencies=["fastapi>=0.104.0", "textual>=0.70.0"],
        actionable_findings=[],
        unresolved_findings=[
            {
                "name": "pygments",
                "version": "2.19.2",
                "id": "CVE-2026-4539",
                "aliases": ["GHSA-5239-wwwm-4pmq"],
                "fix_versions": [],
                "description": "regex complexity issue",
                "reason": "No upstream fix is published yet.",
            }
        ],
    )

    assert "Base Dependency Audit" in markdown
    assert "Known unresolved findings" in markdown
    assert "CVE-2026-4539" in markdown
    assert "No actionable findings" in markdown
