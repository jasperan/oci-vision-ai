from __future__ import annotations

from pathlib import Path

from PIL import Image

from oci_vision.core.exports import (
    build_html_report,
    resolve_source_image_path,
    save_overlay_image,
    write_html_report,
    write_json_report,
)
from oci_vision.core.models import (
    AnalysisReport,
    BoundingPolygon,
    ClassificationLabel,
    ClassificationResult,
    DetectedObject,
    DetectionResult,
    Vertex,
)


def _make_box() -> BoundingPolygon:
    return BoundingPolygon(
        normalized_vertices=[
            Vertex(x=0.1, y=0.1),
            Vertex(x=0.6, y=0.1),
            Vertex(x=0.6, y=0.6),
            Vertex(x=0.1, y=0.6),
        ]
    )


def _make_report(image_path: str = "sample.png") -> AnalysisReport:
    return AnalysisReport(
        image_path=image_path,
        classification=ClassificationResult(
            model_version="demo",
            labels=[ClassificationLabel(name="Dog", confidence=0.98)],
        ),
        detection=DetectionResult(
            model_version="demo",
            objects=[
                DetectedObject(
                    name="Dog",
                    confidence=0.98,
                    bounding_polygon=_make_box(),
                )
            ],
        ),
        elapsed_seconds=0.123,
    )


def test_build_html_report_contains_key_sections():
    report = _make_report()

    html = build_html_report(report)

    assert "OCI Vision AI Report" in html
    assert "Insights" in html
    assert "Classification" in html
    assert "Object Detection" in html
    assert "Dog" in html


def test_write_html_report_creates_file(tmp_path: Path):
    report = _make_report()
    output = tmp_path / "report.html"

    written = write_html_report(report, output)

    assert written == output
    assert output.exists()
    assert "OCI Vision AI Report" in output.read_text()


def test_write_json_report_creates_file(tmp_path: Path):
    report = _make_report()
    output = tmp_path / "report.json"

    written = write_json_report(report, output)

    assert written == output
    assert output.exists()
    assert '"classification"' in output.read_text()


def test_save_overlay_image_creates_png(tmp_path: Path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (200, 200), color=(128, 128, 128)).save(image_path)
    output = tmp_path / "overlay.png"

    saved = save_overlay_image(_make_report(str(image_path)), image_path, output)

    assert saved == output
    assert output.exists()
    rendered = Image.open(output)
    try:
        assert rendered.size == (200, 200)
    finally:
        rendered.close()


def test_resolve_source_image_path_supports_gallery_fixture():
    resolved = resolve_source_image_path("dog_closeup.jpg")

    assert resolved.exists()
    assert resolved.name == "dog_closeup.jpg"


def test_save_overlay_image_raises_for_missing_image(tmp_path: Path):
    report = _make_report("missing.png")

    try:
        save_overlay_image(report, "missing.png", tmp_path / "overlay.png")
    except FileNotFoundError as exc:
        assert "missing.png" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing image")
