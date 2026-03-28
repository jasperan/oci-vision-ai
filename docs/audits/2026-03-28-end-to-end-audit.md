# 2026-03-28 End-to-End Audit

## Phase 1: Fresh Eyes

I read the project top to bottom before changing behavior.

### Findings

1. **Demo mode silently analyzes the wrong image.**
   - `src/oci_vision/core/demo.py` falls back to the first gallery asset when it can't match the requested image.
   - `README.md` shows generic filenames like `photo.jpg`, `document.pdf`, and `group.jpg`, but the shipped gallery only contains `dog_closeup.jpg`, `sign_board.png`, `portrait_demo.png`, and `invoice_demo.png`.
   - Result: typos and many README demo commands appear to work while actually returning dog-fixture data.

2. **Web uploads can return believable results for a different image in demo mode.**
   - `src/oci_vision/web/app.py` writes uploads to a temp file and sends that path into the same demo resolver.
   - When the filename is unknown, the backend analyzes the dog fixture while rendering overlays on the real uploaded bytes.
   - That is a nasty trust break.

3. **The compare page is a placeholder, not a compare tool.**
   - `src/oci_vision/web/templates/compare.html` renders two static copies of the gallery list.
   - There are no selectors, no outputs, and no comparison logic.
   - The README sells a compare surface that doesn't actually exist.

4. **The web dashboard isn't fully offline.**
   - `src/oci_vision/web/templates/base.html` pulls Tailwind and HTMX from public CDNs.
   - The README says the project runs fully offline in demo mode. That's true for the CLI, not for the browser UI.

5. **Live mode doesn't fail fast on bad local paths.**
   - `src/oci_vision/core/client.py` turns a missing local file into an empty inline OCI payload instead of raising `FileNotFoundError`.
   - A local typo becomes an opaque service-side failure.

6. **The web feature picker lies when everything is unchecked.**
   - The frontend sends an empty feature string.
   - The backend treats that as falsy and runs `all` features anyway.
   - The UI says one thing, the server does another.

7. **The docs and server binding disagree.**
   - `README.md` says the dashboard opens at `http://localhost:8000`.
   - `src/oci_vision/cli/app.py` binds `oci-vision web` to `0.0.0.0` by default.
   - That's a real security and expectation mismatch.

8. **Oracle defaults are too privileged for a showcase.**
   - `src/oci_vision/oracle/config.py` defaults to `system` / `VisionAI2026`.
   - `docker-compose.oracle.yml` and the README repeat the same credentials.
   - `src/oci_vision/oracle/schema.py` creates app tables in `SYSAUX`.
   - For a local demo, this is rough.

9. **The custom-model story overclaims offline coverage.**
   - The custom-model notebook says demo mode exercises the `model_id` hooks.
   - In practice, `model_id` is ignored in demo mode for classification and detection.

10. **Several broad exception handlers hide useful failure signals.**
    - `src/oci_vision/web/app.py`, `src/oci_vision/tui/app.py`, and `src/oci_vision/cli/app.py` swallow generic exceptions in user-facing paths.
    - That makes debugging harder and risks masking broken behavior as a soft warning.

### Priority order before deeper audit work

1. Fix demo-mode trust breaks.
2. Make web/offline/docs claims true.
3. Lock down Oracle defaults and web exposure.
4. Tighten input validation and error handling.
5. Turn placeholder surfaces into real features or tone down the docs.

## Phase 2: Test Sweep

### Baseline

- Full suite before fixes: **1 failed, 174 passed, 3 skipped**.
- The failure was a flaky deterministic-screenshot test for the Textual cockpit.
- Baseline coverage: **78.54%** (`79%` displayed by pytest-cov).

### What I changed

1. **Stabilized cockpit screenshot generation.**
   - Screenshot mode now omits the live footer bar and waits for the headless capture file in a tighter loop.
   - That removed a race where the footer sometimes rendered before capture and sometimes didn't.

2. **Added CLI coverage for critical export paths.**
   - Added tests for HTML report generation.
   - Added tests for overlay export output.

3. **Added web coverage for best-effort rendering paths.**
   - Added a report-page test that forces overlay rendering to fail and verifies the page still responds cleanly.
   - Added an upload-endpoint test that forces overlay rendering to fail and verifies the JSON fallback payload stays well-formed.

4. **Added evaluation coverage for OCR edge cases.**
   - Covered empty-string edit distance.
   - Covered `line_accuracy()` behavior when ground truth is empty.

### Result

- Full suite after fixes: **181 passed, 3 skipped**.
- Coverage after fixes: **79.93%** (`80%` displayed by pytest-cov).
- Coverage delta: **+1.39 percentage points**.

### Critical paths still under-covered after this sweep

- `src/oci_vision/core/client.py` error handling and live-path validation.
- `src/oci_vision/cli/app.py` live-mode and failure branches.
- Oracle storage/search modules.
- `src/oci_vision/core/recording.py` serialization branches.

## Phase 3: Battle Hardening

### Edge cases I attacked

- Unknown demo image names.
- Missing local file paths in live mode.
- Empty feature selections.
- Arbitrary demo uploads that don't match bundled fixtures.
- Non-image uploads.
- Oversized uploads.
- CLI timeout failures.
- API connection-drop failures.
- Unknown demo report pages.

### What actually broke

1. **Demo mode lied on unknown assets.**
   - Unknown image names used to silently fall back to the dog fixture.
   - I changed that to raise a clear `FileNotFoundError` with the known demo assets.

2. **Live mode hid local typos behind empty OCI payloads.**
   - Missing local files now fail fast with `FileNotFoundError` before any OCI call is attempted.

3. **The CLI crashed on common service failures.**
   - Added guarded execution for file-not-found, validation, timeout, and connection errors.
   - The CLI now exits with a clean user-facing error instead of a traceback for those cases.

4. **The web upload path trusted unsafe input.**
   - Added server-side checks for empty uploads, non-image uploads, and the documented 20 MB limit.
   - Empty feature selection now returns a 400 instead of silently running every feature.
   - Demo uploads now preserve the original filename in a temp directory, so bundled demo assets work honestly and arbitrary uploads fail clearly instead of returning the wrong fixture.

5. **Unknown demo report pages were misleading.**
   - They now return 404 instead of rendering a report for the wrong image.

### Tests added in this phase

- Demo unknown-image failure tests.
- Live missing-file failure tests.
- CLI timeout and missing-demo-asset tests.
- API empty-feature and connection-error tests.
- Upload rejection tests for unknown demo assets, non-image files, empty feature selection, and oversized payloads.
- Report-page 404 behavior for unknown demo assets.

### Verification

- Full suite after hardening: **191 passed, 3 skipped**.

## Phase 4: Security Audit

### What I checked

- Insecure defaults and hardcoded credentials.
- Web exposure and network defaults.
- Security misconfiguration around Oracle integration.
- Basic OWASP-style input handling in upload and analyze paths.
- Dependency risk with a targeted `pip-audit` pass over the project dependency set.

### Fixes shipped

1. **Local web server now defaults to localhost, not all interfaces.**
   - `oci-vision web` now binds to `127.0.0.1` by default.
   - This matches the README claim and reduces accidental LAN exposure.

2. **Oracle integration now fails secure when credentials are missing.**
   - `OracleConfig` no longer defaults to `system` / `VisionAI2026`.
   - Enabling Oracle mode without explicit credentials now stays disabled instead of quietly reaching for privileged defaults.

3. **Oracle schema bootstrap no longer forces `SYSAUX`.**
   - Table creation now uses the default tablespace instead of pinning app data into a privileged system tablespace.

4. **Upload and API hardening from Phase 3 double as OWASP fixes.**
   - Empty feature selections now fail closed.
   - Non-image and oversized uploads are rejected server-side.
   - Unknown demo uploads and unknown demo report pages no longer produce misleading results.

### Proof via tests

- Added tests for localhost web binding.
- Added tests proving Oracle config is fail-secure without credentials.
- Added tests proving Oracle config enables only with explicit credentials.
- Added tests proving schema initialization no longer injects `SYSAUX`.
- Added API/upload validation tests in Phase 3 that cover the hardened request handling.

### Dependency-risk findings

Targeted `pip-audit` on the project dependency set surfaced:

- `pyopenssl 25.3.0` with published fixes available in `26.0.0`.
- `pygments 2.19.2` with a published advisory and no fix version listed by `pip-audit`.

These are transitive in the current environment, not direct imports in this repo. I’m flagging them for discussion rather than forcing a speculative pin mid-audit.

### Still needs discussion

- `docker-compose.oracle.yml` and `README.md` still document the old sample Oracle credentials and privileged user flow. I’ll clean that up in the onboarding/docs phase so the code and docs land together.
- The web dashboard intentionally has no authentication. That’s reasonable for a localhost demo, not for a shared deployment.

## Phase 5: Performance

### Profiling target

I profiled the hot offline paths that drive the demo experience:

1. Repeated demo analyses.
2. Overlay rendering.
3. Web-style multi-overlay generation (full overlay plus per-feature overlays).

### Biggest bottlenecks found

1. **Demo fixture disk I/O and JSON parsing**
   - `src/oci_vision/gallery/__init__.py:get_cached_response()` re-read and re-decoded the same JSON fixture on every call.

2. **Renderer alpha compositing**
   - `src/oci_vision/core/renderer.py:render_overlay()` built a separate RGBA overlay and then alpha-composited it back onto the base image every time.

3. **Repeated label measurement and font setup work**
   - `_draw_label()` re-measured text even when callers had already measured it.
   - Font lookup also happened for every render even when the size never changed.

### Fixes shipped

- Added in-memory caching for `load_manifest()` and `get_cached_response()`.
- Cleared those caches after fixture recording so demo additions stay correct in-process.
- Switched overlay rendering to draw directly onto a single RGBA canvas, removing an extra `Image.alpha_composite()` pass.
- Cached fonts by size.
- Reused precomputed text sizes when drawing labels.

### Benchmarks

Average wall-clock time across 5 runs on this machine:

| Benchmark | Before | After | Improvement |
|---|---:|---:|---:|
| `demo_analyze_500` | 0.289s | 0.119s | **58.7% faster** |
| `render_overlay_100` | 2.046s | 1.629s | **20.4% faster** |
| `web_like_overlays_50` | 2.716s | 2.015s | **25.8% faster** |

### Verification

- Full suite after performance work: **195 passed, 3 skipped**.

## Phase 6: Ruthless Simplification

Pending.

## Phase 7: Innovation

Pending.

## Phase 8: Onboarding Verify

Pending.

## Phase 9: Final Gate

Pending.
