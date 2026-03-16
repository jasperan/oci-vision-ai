"""Tests for the OCI Vision AI web dashboard (FastAPI + HTMX)."""

import pytest
from httpx import AsyncClient, ASGITransport

from oci_vision.web.app import create_app


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
    """Test multipart file upload analyze endpoint with a tiny synthetic image."""
    from io import BytesIO
    from PIL import Image

    # Create a tiny 10x10 red PNG in memory
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-upload",
            files={"file": ("test.png", buf, "image/png")},
            data={"features": "classification,detection"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "image_path" in data
        assert "classification" in data
        assert "feature_overlays" in data


@pytest.mark.asyncio
async def test_static_files(app):
    """Test that static files are served."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/static/app.js")
        assert resp.status_code == 200
        assert "text/javascript" in resp.headers.get("content-type", "")
