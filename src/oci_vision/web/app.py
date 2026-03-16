"""OCI Vision AI — FastAPI web dashboard.

Factory function ``create_app(demo=False)`` returns a fully configured
FastAPI application.  The CLI ``web`` command imports this module.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from oci_vision.core.client import VisionClient
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
    async def compare_page(request: Request):
        """Comparison page for side-by-side gallery inspection."""
        manifest = load_manifest()
        return templates.TemplateResponse(request, "compare.html", {
            "images": manifest["images"],
            "demo": client.is_demo,
        })

    @app.get("/report/{image_name}", response_class=HTMLResponse)
    async def report_page(request: Request, image_name: str):
        """Static report page for a gallery image."""
        report = client.analyze(image_name)
        overlay_base64 = None
        image_path = None

        try:
            from PIL import Image
            from oci_vision.core.renderer import render_overlay
            from oci_vision.gallery import get_gallery_path

            image_path = get_gallery_path() / "images" / Path(image_name).name
            analysis_target = str(image_path) if image_path.exists() else image_name
            report = client.analyze(analysis_target)
            img = Image.open(image_path)
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
            "image_path": str(image_path) if image_path else None,
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
        report = client.analyze(body.image, features=body.features)
        result = report.model_dump()
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

        # Write to a temp path so VisionClient can read it (inline mode).
        # For demo mode, VisionClient will fall back to the first gallery
        # image when the file doesn't match a known gallery entry.
        import tempfile
        suffix = Path(file.filename or "upload.png").suffix or ".png"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Parse features
        feat_list: list[str] | str = "all"
        if features:
            feat_list = [f.strip() for f in features.split(",")]

        report = client.analyze(tmp_path, features=feat_list)

        # Build response with overlay
        result = report.model_dump()

        try:
            from PIL import Image
            from oci_vision.core.renderer import render_overlay

            img = Image.open(io.BytesIO(contents))
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

        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass

        return JSONResponse(result)

    return app
