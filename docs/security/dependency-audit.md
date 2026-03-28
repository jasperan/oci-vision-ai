# Base Dependency Audit

This project has a dedicated GitHub Action for the **base install path**. The goal is simple: keep `pip install -e .` as small and boring as possible, and fail CI only when a base dependency has an actionable published fix.

## Scope

The audit covers only the runtime dependencies in `pyproject.toml` under `[project].dependencies`.

It does **not** include:

- `.[live]`
- `.[notebooks]`
- `.[oracle]`
- the full `.[all]` install

That split is deliberate. OCI live-mode dependencies are opt-in now, so the default install path should stay lean.

## Current unresolved finding

As of 2026-03-28, the base dependency audit still reports 1 unresolved advisory:

- **Package:** `pygments`
- **Version:** `2.19.2`
- **ID:** `CVE-2026-4539`
- **Alias:** `GHSA-5239-wwwm-4pmq`
- **Status:** no fix version published by `pip-audit`

We keep this finding **visible** in the generated audit report, but the workflow does not fail on it yet because there is no upstream fixed release to move to.

The moment a fixed `pygments` release exists, the allowlist entry in `scripts/dependency_audit.py` should be removed and the dependency should be upgraded.

## CI behavior

The workflow:

1. checks out the repo
2. installs `pip-audit`
3. audits the base dependency set through `scripts/dependency_audit.py`
4. uploads the generated markdown report as a workflow artifact
5. writes the report into the GitHub Actions step summary

## Local verification

Run the same audit locally with:

```bash
python -m pip install pip-audit
python scripts/dependency_audit.py --report dependency-audit-report.md
```

If the script exits nonzero, a new actionable dependency issue landed in the base install path.
