"""Tests for the OCI Vision AI web dashboard (FastAPI + HTMX)."""

from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from oci_vision.web.app import create_app


def _gallery_upload(name: str) -> tuple[str, BytesIO, str]:
    from oci_vision.gallery import get_gallery_path

    path = get_gallery_path() / "images" / name
    return name, BytesIO(path.read_bytes()), "image/jpeg"


@pytest.fixture
def app():
    return create_app(demo=True)


@pytest.mark.asyncio
async def test_index(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "OCI Vision" in resp.text


@pytest.mark.asyncio
async def test_gallery_page(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/gallery")
        assert resp.status_code == 200
        assert "dog_closeup" in resp.text


@pytest.mark.asyncio
async def test_compare_page(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/compare")
        assert resp.status_code == 200
        assert "Compare" in resp.text


@pytest.mark.asyncio
async def test_report_page_for_gallery_image(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/report/dog_closeup.jpg")
        assert resp.status_code == 200
        assert "OCI Vision Report" in resp.text


@pytest.mark.asyncio
async def test_report_page_tolerates_overlay_failure(app, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("overlay boom")

    monkeypatch.setattr("oci_vision.core.renderer.render_overlay", explode)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/report/dog_closeup.jpg")
        assert resp.status_code == 200
        assert "Overlay unavailable" in resp.text


@pytest.mark.asyncio
async def test_report_page_unknown_demo_image_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/report/mystery.png")
        assert resp.status_code == 404
        assert "Demo asset not found" in resp.text


@pytest.mark.asyncio
async def test_analyze_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"image": "dog_closeup.jpg", "features": ["classification"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "classification" in data


@pytest.mark.asyncio
async def test_analyze_endpoint_rejects_empty_feature_selection(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"image": "dog_closeup.jpg", "features": []},
        )
        assert resp.status_code == 400
        assert "Select at least one feature" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_endpoint_surfaces_connection_error(app, monkeypatch):
    def explode(*args, **kwargs):
        raise ConnectionError("socket dropped")

    monkeypatch.setattr("oci_vision.core.client.VisionClient.analyze", explode)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"image": "dog_closeup.jpg", "features": ["classification"]},
        )
        assert resp.status_code == 502
        assert "socket dropped" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_gallery_api(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/gallery")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["images"]) >= 1


@pytest.mark.asyncio
async def test_search_api_without_oracle_enabled(app, monkeypatch):
    monkeypatch.delenv("OCI_VISION_ENABLE_ORACLE", raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/search", params={"query": "invoice"})
        assert resp.status_code == 200
        assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_analyze_upload_endpoint(app):
    """Test multipart file upload analyze endpoint with a real bundled demo image."""
    file_name, buf, content_type = _gallery_upload("dog_closeup.jpg")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": (file_name, buf, content_type)},
            data={"features": "classification,detection"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "image_path" in data
        assert "classification" in data
        assert "feature_overlays" in data


@pytest.mark.asyncio
async def test_analyze_upload_endpoint_rejects_unknown_demo_upload(app):
    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": ("random.png", buf, "image/png")},
            data={"features": "classification"},
        )
        assert resp.status_code == 400
        assert "Demo asset not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_upload_endpoint_rejects_non_image_file(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
            data={"features": "classification"},
        )
        assert resp.status_code == 400
        assert "Only image uploads are supported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_upload_endpoint_rejects_empty_feature_selection(app):
    file_name, buf, content_type = _gallery_upload("dog_closeup.jpg")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": (file_name, buf, content_type)},
            data={"features": ""},
        )
        assert resp.status_code == 400
        assert "Select at least one feature" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_upload_endpoint_tolerates_overlay_failure(app, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("overlay boom")

    monkeypatch.setattr("oci_vision.core.renderer.render_overlay", explode)

    file_name, buf, content_type = _gallery_upload("dog_closeup.jpg")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": (file_name, buf, content_type)},
            data={"features": "classification"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overlay_base64"] is None
        assert data["feature_overlays"] == {}


@pytest.mark.asyncio
async def test_analyze_upload_endpoint_rejects_oversized_file(app):
    too_large = BytesIO(b"0" * ((20 * 1024 * 1024) + 1))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": ("dog_closeup.jpg", too_large, "image/jpeg")},
            data={"features": "classification"},
        )
        assert resp.status_code == 413
        assert "20 MB" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_static_files(app):
    """Test that static files are served."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/static/app.js")
        assert resp.status_code == 200
        assert "text/javascript" in resp.headers.get("content-type", "")
