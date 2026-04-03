from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib

ALLOWLIST: dict[str, dict[str, str]] = {
    "CVE-2026-4539": {
        "package": "pygments",
        "reason": "No upstream fix is published yet. Keep the finding visible and remove this allowlist entry as soon as a fixed release exists.",
    }
}


def load_base_dependencies(pyproject_path: Path) -> list[str]:
    with pyproject_path.open("rb") as handle:
        pyproject = tomllib.load(handle)
    return list(pyproject["project"]["dependencies"])


def run_pip_audit(requirements_path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(requirements_path),
        "--format",
        "json",
        "--progress-spinner",
        "off",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    if not stdout:
        raise RuntimeError(completed.stderr.strip() or "pip-audit produced no JSON output")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(stdout) from exc


def flatten_findings(audit_result: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for dependency in audit_result.get("dependencies", []):
        for vuln in dependency.get("vulns", []):
            findings.append(
                {
                    "name": dependency["name"],
                    "version": dependency["version"],
                    "id": vuln["id"],
                    "aliases": list(vuln.get("aliases", [])),
                    "fix_versions": list(vuln.get("fix_versions", [])),
                    "description": vuln.get("description", ""),
                }
            )
    return findings


def partition_findings(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actionable: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for finding in findings:
        rule = ALLOWLIST.get(finding["id"])
        if (
            rule
            and finding["name"] == rule["package"]
            and not finding["fix_versions"]
        ):
            unresolved.append({**finding, "reason": rule["reason"]})
        else:
            actionable.append(finding)

    return actionable, unresolved


def render_markdown(
    *,
    dependencies: list[str],
    actionable_findings: list[dict[str, Any]],
    unresolved_findings: list[dict[str, Any]],
    generated_at: str | None = None,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    lines = [
        "# Base Dependency Audit",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Scope",
        "",
        "This audit covers the base runtime dependency set from `pyproject.toml`.",
        "Optional extras like `.[live]`, `.[notebooks]`, and `.[oracle]` are intentionally excluded here.",
        "",
        "## Dependencies audited",
        "",
    ]
    lines.extend(f"- `{dependency}`" for dependency in dependencies)
    lines.append("")

    lines.extend(["## Actionable findings", ""])
    if actionable_findings:
        for finding in actionable_findings:
            aliases = ", ".join(finding["aliases"]) or "none"
            fixes = ", ".join(finding["fix_versions"]) or "none"
            lines.extend(
                [
                    f"### `{finding['name']}` `{finding['version']}`",
                    "",
                    f"- ID: `{finding['id']}`",
                    f"- Aliases: `{aliases}`",
                    f"- Fix versions: `{fixes}`",
                    f"- Description: {finding['description'] or 'n/a'}",
                    "",
                ]
            )
    else:
        lines.extend(["No actionable findings.", ""])

    lines.extend(["## Known unresolved findings", ""])
    if unresolved_findings:
        for finding in unresolved_findings:
            aliases = ", ".join(finding["aliases"]) or "none"
            lines.extend(
                [
                    f"### `{finding['name']}` `{finding['version']}`",
                    "",
                    f"- ID: `{finding['id']}`",
                    f"- Aliases: `{aliases}`",
                    "- Fix versions: `none published`",
                    f"- Why it is temporarily allowlisted: {finding['reason']}",
                    f"- Description: {finding['description'] or 'n/a'}",
                    "",
                ]
            )
    else:
        lines.extend(["No known unresolved findings.", ""])

    lines.extend([
        "## Exit policy",
        "",
        "- The audit fails if it finds any actionable vulnerability.",
        "- The audit passes if the only findings are explicitly allowlisted unresolved advisories with no published fix.",
        "",
    ])
    return "\n".join(lines)


def write_requirements_file(dependencies: list[str]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
    with handle:
        handle.write("\n".join(dependencies) + "\n")
    return Path(handle.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the base dependency set with pip-audit.")
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--report", default="dependency-audit-report.md")
    args = parser.parse_args()

    pyproject_path = Path(args.pyproject)
    report_path = Path(args.report)
    dependencies = load_base_dependencies(pyproject_path)
    requirements_path = write_requirements_file(dependencies)

    try:
        audit_result = run_pip_audit(requirements_path)
    finally:
        requirements_path.unlink(missing_ok=True)

    findings = flatten_findings(audit_result)
    actionable, unresolved = partition_findings(findings)
    markdown = render_markdown(
        dependencies=dependencies,
        actionable_findings=actionable,
        unresolved_findings=unresolved,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    print(markdown)

    return 1 if actionable else 0


if __name__ == "__main__":
    raise SystemExit(main())
