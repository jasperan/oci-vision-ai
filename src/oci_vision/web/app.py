"""OCI Vision AI — FastAPI web dashboard.

Factory function ``create_app(demo=False)`` returns a fully configured
FastAPI application.  The CLI ``web`` command imports this module.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from oci_vision.core.client import VisionClient
from oci_vision.core.insights import compare_reports, report_insights
from oci_vision.core.showcase import build_showcase_snapshot
from oci_vision.gallery import load_manifest
from oci_vision.oracle import search_if_enabled, store_report_if_enabled


class AnalyzeRequest(BaseModel):
    """Request body for the /api/analyze endpoint."""
    image: str
    features: list[str] | str = "all"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_WEB_DIR = Path(__file__).parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"
_ALLOWED_FEATURES = {"classification", "detection", "text", "faces", "document"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 1024 * 1024


_MAX_JSON_BODY_BYTES = 64 * 1024
# Multipart framing (boundaries, headers, the ``features`` field) on top of the file cap.
_MULTIPART_OVERHEAD_BYTES = 1024 * 1024
# Pillow decodes before it warns (its own limit is ~179 Mpx); skip the best-effort overlay above this.
_MAX_OVERLAY_PIXELS = 40_000_000
# Formats the overlay decoder may open. Pillow's auto-detection would also hand EPS to Ghostscript.
_OVERLAY_FORMATS = ["PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF"]


class _BodyLimitMiddleware:
    """Reject request bodies over a per-path cap before the framework spools them.

    A ``Content-Length`` over the cap is refused outright; chunked or understated bodies are cut
    off as soon as the received bytes pass the cap. The handler never sees the over-limit body.
    """

    def __init__(self, app, limits: dict[str, int]) -> None:
        self.app = app
        self.limits = limits

    async def __call__(self, scope, receive, send):
        limit = self.limits.get(scope.get("path")) if scope["type"] == "http" else None
        if limit is None or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(send)
            return

        received = 0
        exceeded = False

        async def limited_receive():
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message):
            if not exceeded:
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not exceeded:
                raise
        if exceeded:
            await self._reject(send)

    @staticmethod
    async def _reject(send) -> None:
        body = b'{"detail":"Request body too large."}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


def _gallery_target(client: VisionClient, name: str) -> str:
    """Map a request-supplied image name to something safe to analyse.

    Live mode forwards the string to the OCI request builders, which read any local path or
    ``oci://`` object. The HTTP surface only ever offers curated gallery assets (uploads have their
    own route), so anything else is refused. Demo mode only looks the name up in fixtures.
    """
    if client.is_demo:
        return name
    from oci_vision.gallery import get_gallery_path

    filename = Path(name).name
    if filename != name or not any(image["filename"] == filename for image in load_manifest()["images"]):
        raise HTTPException(status_code=404, detail="Unknown gallery image")
    return str(get_gallery_path() / "images" / filename)


def _render_upload_overlays(contents: bytes, report) -> tuple[str, dict[str, str]]:
    """Render the combined and per-feature overlays for an upload (blocking; run in a thread)."""
    from PIL import Image
    from oci_vision.core.renderer import render_overlay

    with Image.open(io.BytesIO(contents), formats=_OVERLAY_FORMATS) as img:
        width, height = img.size
        if width * height > _MAX_OVERLAY_PIXELS:
            raise ValueError("image too large for overlay rendering")
        overlay = render_overlay(img, report)
        buf = io.BytesIO()
        overlay.save(buf, format="PNG")
        overlay_base64 = base64.b64encode(buf.getvalue()).decode()

        feature_overlays: dict[str, str] = {}
        for feature_name in [
            feature for feature in report.available_features
            if feature in {"classification", "detection", "text", "faces"}
        ]:
            feature_img = render_overlay(img, report, selected_features={feature_name})
            feature_buf = io.BytesIO()
            feature_img.save(feature_buf, format="PNG")
            feature_overlays[feature_name] = base64.b64encode(feature_buf.getvalue()).decode()
    return overlay_base64, feature_overlays


async def _read_capped(
    upload: UploadFile,
    limit: int,
    chunk_size: int = _UPLOAD_CHUNK_BYTES,
) -> tuple[bytes, bool]:
    """Read an upload without buffering more than ``limit`` + one chunk.

    Returns the bytes read and whether the limit was exceeded. The endpoint used to call
    ``read()`` with no size and check the length afterwards, so the 20 MB guard only limited what
    was *processed* - an oversized upload was already in memory by then. Stopping the loop once the
    cap is passed keeps the guard's memory bound proportional to the cap.
    """
    chunks: list[bytes] = []
    total = 0
    while total <= limit:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks), total > limit


def _parse_requested_features(features: list[str] | str | None) -> list[str] | str:
    if features is None:
        return "all"

    if isinstance(features, str):
        if features.strip().lower() == "all":
            return "all"
        requested = [part.strip().lower() for part in features.split(",") if part.strip()]
    else:
        requested = [str(part).strip().lower() for part in features if str(part).strip()]

    if not requested:
        raise ValueError("Select at least one feature.")

    invalid = sorted({feature for feature in requested if feature not in _ALLOWED_FEATURES})
    if invalid:
        raise ValueError(
            f"Unsupported feature selection: {', '.join(invalid)}. "
            f"Valid features: {', '.join(sorted(_ALLOWED_FEATURES))}"
        )

    return requested


def _classify_analysis_error(
    exc: Exception, *, missing_file_status: int = 404
) -> tuple[int, str] | None:
    """Map known OCI/IO failures to (status_code, detail). Returns None for unknown errors.

    ``missing_file_status`` lets callers choose how a missing image surfaces:
    page routes report 404, while ``/api/analyze*`` reports 400 for API clients.
    """
    if isinstance(exc, FileNotFoundError):
        return missing_file_status, str(exc)
    if isinstance(exc, ValueError):
        return 400, str(exc)
    if isinstance(exc, TimeoutError):
        return 504, f"Vision request timed out: {exc}"
    if isinstance(exc, ConnectionError):
        return 502, f"Could not reach OCI Vision service: {exc}"
    return None


def _analysis_error_response(exc: Exception) -> JSONResponse:
    classified = _classify_analysis_error(exc, missing_file_status=400)
    if classified is None:
        raise exc
    status_code, detail = classified
    return JSONResponse({"detail": detail}, status_code=status_code)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_app(demo: bool = False) -> FastAPI:
    """Create and return a configured FastAPI application.

    Parameters
    ----------
    demo : bool
        When *True*, the embedded :class:`VisionClient` operates in demo mode
        (no OCI credentials required).
    """
    app = FastAPI(
        title="OCI Vision Studio",
        description="Web dashboard for OCI Vision AI analysis",
    )

    app.add_middleware(
        _BodyLimitMiddleware,
        limits={
            "/api/analyze": _MAX_JSON_BODY_BYTES,
            "/api/analyze-upload": _MAX_UPLOAD_BYTES + _MULTIPART_OVERHEAD_BYTES,
        },
    )

    # State ----------------------------------------------------------------
    client = VisionClient(demo=demo)
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

    # Static files ---------------------------------------------------------
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ------------------------------------------------------------------
    # Page routes
    # ------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main analyzer page."""
        return templates.TemplateResponse(request, "index.html", {
            "demo": client.is_demo,
        })

    @app.get("/gallery", response_class=HTMLResponse)
    async def gallery_page(request: Request):
        """Gallery page with demo images."""
        manifest = load_manifest()
        return templates.TemplateResponse(request, "gallery.html", {
            "images": manifest["images"],
            "demo": client.is_demo,
        })

    @app.get("/gallery-image/{image_name}")
    async def gallery_image(image_name: str):
        """Serve a curated gallery asset for the contact sheet."""
        from oci_vision.gallery import get_gallery_path

        filename = Path(image_name).name
        manifest = load_manifest()
        if not any(image["filename"] == filename for image in manifest["images"]):
            raise HTTPException(status_code=404, detail="Unknown gallery image")
        image_path = get_gallery_path() / "images" / filename
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file missing")
        return FileResponse(image_path)

    @app.get("/compare", response_class=HTMLResponse)
    async def compare_page(request: Request, left: str | None = None, right: str | None = None):
        """Comparison page for side-by-side gallery inspection."""
        manifest = load_manifest()
        left_report = None
        right_report = None
        comparison = None
        error = None

        if left and right:
            try:
                left_report = client.analyze(_gallery_target(client, left))
                right_report = client.analyze(_gallery_target(client, right))
                comparison = compare_reports(left_report, right_report)
            except HTTPException as exc:
                error = str(exc.detail)
            except Exception as exc:
                error = str(exc)

        return templates.TemplateResponse(request, "compare.html", {
            "images": manifest["images"],
            "demo": client.is_demo,
            "selected_left": left,
            "selected_right": right,
            "left_report": left_report,
            "right_report": right_report,
            "comparison": comparison,
            "error": error,
        })

    @app.get("/showcase", response_class=HTMLResponse)
    async def showcase_page(request: Request):
        """Portfolio-style showcase page covering the whole demo surface."""
        if not client.is_demo:
            raise HTTPException(status_code=404, detail="Showcase is available in demo mode only.")
        showcase_snapshot, _ = build_showcase_snapshot(client)
        return templates.TemplateResponse(request, "showcase.html", {
            "showcase": showcase_snapshot,
            "demo": client.is_demo,
        })

    @app.get("/report/{image_name}", response_class=HTMLResponse)
    async def report_page(request: Request, image_name: str):
        """Static report page for a gallery image."""
        from oci_vision.gallery import get_gallery_path

        image_path = get_gallery_path() / "images" / Path(image_name).name
        analysis_target = _gallery_target(client, image_name)
        if client.is_demo and image_path.exists():
            analysis_target = str(image_path)
        try:
            report = client.analyze(analysis_target)
        except Exception as exc:
            classified = _classify_analysis_error(exc)
            if classified is None:
                raise
            status_code, detail = classified
            raise HTTPException(status_code=status_code, detail=detail) from exc

        overlay_base64 = None

        if image_path.exists():
            try:
                from PIL import Image
                from oci_vision.core.renderer import render_overlay

                with Image.open(image_path) as img:
                    overlay = render_overlay(img, report)
                buf = io.BytesIO()
                overlay.save(buf, format="PNG")
                buf.seek(0)
                overlay_base64 = base64.b64encode(buf.read()).decode()
            except Exception:
                overlay_base64 = None

        return templates.TemplateResponse(request, "report.html", {
            "report": report,
            "overlay_base64": overlay_base64,
            "image_name": image_name,
            "demo": client.is_demo,
            "image_path": str(image_path) if image_path.exists() else None,
            "insights": report_insights(report),
        })

    # ------------------------------------------------------------------
    # API routes
    # ------------------------------------------------------------------

    @app.get("/api/gallery")
    async def gallery_api():
        """Return JSON list of gallery images."""
        manifest = load_manifest()
        return JSONResponse({"images": manifest["images"]})

    @app.get("/api/search")
    async def search_api(query: str, limit: int = 5):
        """Search Oracle-backed stored runs when enabled."""
        return JSONResponse({"results": search_if_enabled(query, limit=limit)})

    @app.post("/api/analyze")
    async def analyze_api(body: AnalyzeRequest):
        """Analyse a named image (JSON body).

        Expects ``{"image": "...", "features": [...]}``
        """
        try:
            requested_features = _parse_requested_features(body.features)
            target = _gallery_target(client, body.image)
            report = client.analyze(target, features=requested_features)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        except Exception as exc:
            return _analysis_error_response(exc)

        result = report.model_dump()
        result["insights"] = report_insights(report)
        stored_run_id = store_report_if_enabled(report)
        if stored_run_id:
            result["stored_run_id"] = stored_run_id
        return JSONResponse(result)

    @app.post("/api/analyze-upload")
    async def analyze_upload(
        file: UploadFile = File(...),
        features: Optional[str] = Form(None),
    ):
        """Analyse an uploaded image (multipart form).

        Returns analysis JSON with an optional base64-encoded overlay image.
        """
        contents, oversize = await _read_capped(file, _MAX_UPLOAD_BYTES)
        content_type = file.content_type or ""

        if not contents:
            return JSONResponse({"detail": "Uploaded file is empty."}, status_code=400)
        if not content_type.startswith("image/"):
            return JSONResponse({"detail": "Only image uploads are supported."}, status_code=400)
        if oversize:
            return JSONResponse(
                {"detail": "Upload exceeds the 20 MB limit."},
                status_code=413,
            )

        if features is None:
            return JSONResponse({"detail": "Select at least one feature."}, status_code=400)

        try:
            requested_features = _parse_requested_features(features)
        except Exception as exc:
            return _analysis_error_response(exc)

        upload_name = Path(file.filename or "upload.png").name or "upload.png"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / upload_name
            tmp_path.write_bytes(contents)

            try:
                report = client.analyze(str(tmp_path), features=requested_features)
            except Exception as exc:
                return _analysis_error_response(exc)

            result = report.model_dump()
            result["insights"] = report_insights(report)

            try:
                overlay_base64, feature_overlays = await run_in_threadpool(
                    _render_upload_overlays, contents, report
                )
                result["overlay_base64"] = overlay_base64
                result["feature_overlays"] = feature_overlays
            except Exception:
                # Overlay generation is best-effort
                result["overlay_base64"] = None
                result["feature_overlays"] = {}

        stored_run_id = store_report_if_enabled(report)
        if stored_run_id:
            result["stored_run_id"] = stored_run_id

        return JSONResponse(result)

    return app
