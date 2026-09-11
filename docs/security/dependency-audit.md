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

## Current unresolved findings

**None.** As of 2026-09-11 the base dependency audit reports no actionable and no unresolved
advisories.

### Resolved: `pygments` `CVE-2026-4539`

- **Package:** `pygments`
- **Was:** `2.19.2`
- **ID:** `CVE-2026-4539` (alias `GHSA-5239-wwwm-4pmq`, reported by `pip-audit` as `PYSEC-2026-2987`)
- **Fixed in:** `2.20.0` (current release: `2.21.0`)

The advisory was allowlisted on 2026-03-28 because no fix version existed. A fix version does exist
now, so the condition on that entry was met and the entry was removed from
`scripts/dependency_audit.py`; the allowlist is empty. Two facts make the removal safe rather than
merely tidy:

1. The base set no longer resolves the vulnerable version — the workflow's own command reports
   "No actionable findings" and "No known unresolved findings" and exits 0.
2. Even a finding that did resurface would fail the audit, because a finding that carries fix
   versions is classified as actionable regardless of the allowlist. The entry was inert, which is
   why leaving it in place was a documentation error rather than a live risk.

`tests/core/test_dependency_audit_script.py` pins both halves: the advisory is actionable when it
carries a fix version, and it is actionable when it does not, because nothing is allowlisted for
it any more.

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
