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

from oci_vision.core.client import VisionClient
from oci_vision.gallery import load_manifest

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

    # ------------------------------------------------------------------
    # API routes
    # ------------------------------------------------------------------

    @app.get("/api/gallery")
    async def gallery_api():
        """Return JSON list of gallery images."""
        manifest = load_manifest()
        return JSONResponse({"images": manifest["images"]})

    @app.post("/api/analyze")
    async def analyze_api(request: Request):
        """Analyse a named image (JSON body).

        Expects ``{"image": "...", "features": [...]}``
        """
        body = await request.json()
        image = body.get("image", "")
        features = body.get("features", "all")

        report = client.analyze(image, features=features)
        return JSONResponse(report.model_dump())

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
        except Exception:
            # Overlay generation is best-effort
            result["overlay_base64"] = None

        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass

        return JSONResponse(result)

    return app
