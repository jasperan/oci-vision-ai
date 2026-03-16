from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from oci_vision.cli.app import app
from oci_vision.core.recording import record_fixture

runner = CliRunner()


def test_record_fixture_adds_image_response_and_manifest(tmp_path: Path):
    gallery_root = tmp_path / "gallery"
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)

    response = {
        "image_text": {"words": [], "lines": []},
        "text_detection_model_version": "1.0.0",
    }

    entry = record_fixture(
        image_path=image_path,
        feature="text",
        response_payload=response,
        gallery_root=gallery_root,
        image_id="sample_text",
        description="Sample OCR fixture",
    )

    assert entry["id"] == "sample_text"
    assert entry["features"] == ["text"]
    assert (gallery_root / "images" / "sample.png").exists()
    assert (gallery_root / "responses" / "sample_text_text.json").exists()

    manifest = json.loads((gallery_root / "manifest.json").read_text())
    assert manifest["images"][0]["id"] == "sample_text"


def test_record_fixture_merges_features_for_existing_entry(tmp_path: Path):
    gallery_root = tmp_path / "gallery"
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)

    record_fixture(
        image_path=image_path,
        feature="text",
        response_payload={"image_text": {"words": [], "lines": []}, "text_detection_model_version": "1.0.0"},
        gallery_root=gallery_root,
        image_id="sample",
        description="Sample",
    )
    entry = record_fixture(
        image_path=image_path,
        feature="faces",
        response_payload={"detected_faces": [], "face_detection_model_version": "1.0.0"},
        gallery_root=gallery_root,
        image_id="sample",
        description="Sample",
    )

    assert entry["features"] == ["faces", "text"]
    manifest = json.loads((gallery_root / "manifest.json").read_text())
    assert manifest["images"][0]["features"] == ["faces", "text"]


def test_cli_record_demo_from_response_json(tmp_path: Path):
    gallery_root = tmp_path / "gallery"
    image_path = tmp_path / "sample.png"
    response_path = tmp_path / "response.json"

    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)
    response_path.write_text(json.dumps({
        "image_text": {"words": [], "lines": []},
        "text_detection_model_version": "1.0.0",
    }))

    result = runner.invoke(
        app,
        [
            "record-demo",
            str(image_path),
            "--feature",
            "text",
            "--response-json",
            str(response_path),
            "--image-id",
            "sample_text",
            "--description",
            "Sample OCR fixture",
            "--gallery-root",
            str(gallery_root),
        ],
    )

    assert result.exit_code == 0
    assert (gallery_root / "manifest.json").exists()
    assert (gallery_root / "responses" / "sample_text_text.json").exists()
