from oci_vision.core.demo import DemoClient
from oci_vision.core.models import AnalysisReport, ClassificationResult, DetectionResult


def test_demo_client_classify():
    client = DemoClient()
    result = client.classify("dog_closeup.jpg")
    assert isinstance(result, ClassificationResult)
    assert len(result.labels) > 0
    assert result.labels[0].name == "Dog"


def test_demo_client_detect_objects():
    client = DemoClient()
    result = client.detect_objects("dog_closeup.jpg")
    assert isinstance(result, DetectionResult)
    assert len(result.objects) > 0


def test_demo_client_analyze_all():
    client = DemoClient()
    report = client.analyze("dog_closeup.jpg")
    assert isinstance(report, AnalysisReport)
    assert report.classification is not None
    assert report.detection is not None
    assert "classification" in report.available_features


def test_demo_client_analyze_specific_features():
    client = DemoClient()
    report = client.analyze("dog_closeup.jpg", features=["classification"])
    assert report.classification is not None
    assert report.detection is None


def test_demo_client_unknown_image_returns_fallback():
    client = DemoClient()
    result = client.classify("unknown_photo.jpg")
    assert isinstance(result, ClassificationResult)
    assert len(result.labels) > 0  # falls back to first gallery image


def test_demo_client_feature_not_cached_returns_none():
    client = DemoClient()
    result = client.detect_text("dog_closeup.jpg")
    assert result is None  # no OCR cache for this image yet


def test_demo_client_analyze_from_path():
    client = DemoClient()
    report = client.analyze("/some/path/to/dog_closeup.jpg")
    assert report.classification is not None  # matches by filename
