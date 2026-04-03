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
from fastapi.responses import HTMLResponse, JSONResponse
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


def _analysis_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, (FileNotFoundError, ValueError)):
        return JSONResponse({"detail": str(exc)}, status_code=400)
    if isinstance(exc, TimeoutError):
        return JSONResponse({"detail": f"Vision request timed out: {exc}"}, status_code=504)
    if isinstance(exc, ConnectionError):
        return JSONResponse({"detail": f"Could not reach OCI Vision service: {exc}"}, status_code=502)
    raise exc


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
                left_report = client.analyze(left)
                right_report = client.analyze(right)
                comparison = compare_reports(left_report, right_report)
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
        analysis_target = str(image_path) if image_path.exists() else image_name
        try:
            report = client.analyze(analysis_target)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"Vision request timed out: {exc}") from exc
        except ConnectionError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach OCI Vision service: {exc}") from exc

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
            report = client.analyze(body.image, features=requested_features)
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
        contents = await file.read()
        content_type = file.content_type or ""

        if not contents:
            return JSONResponse({"detail": "Uploaded file is empty."}, status_code=400)
        if not content_type.startswith("image/"):
            return JSONResponse({"detail": "Only image uploads are supported."}, status_code=400)
        if len(contents) > _MAX_UPLOAD_BYTES:
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
                from PIL import Image
                from oci_vision.core.renderer import render_overlay

                with Image.open(io.BytesIO(contents)) as img:
                    overlay = render_overlay(img, report)

                    buf = io.BytesIO()
                    overlay.save(buf, format="PNG")
                    buf.seek(0)
                    result["overlay_base64"] = base64.b64encode(buf.read()).decode()

                    feature_overlays = {}
                    for feature_name in [
                        feature for feature in report.available_features
                        if feature in {"classification", "detection", "text", "faces"}
                    ]:
                        feature_img = render_overlay(img, report, selected_features={feature_name})
                        feature_buf = io.BytesIO()
                        feature_img.save(feature_buf, format="PNG")
                        feature_buf.seek(0)
                        feature_overlays[feature_name] = base64.b64encode(feature_buf.read()).decode()
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
