import pytest
from oci_vision.core.client import VisionClient
from oci_vision.core.models import AnalysisReport, ClassificationResult, DetectionResult


def test_client_demo_mode():
    client = VisionClient(demo=True)
    assert client.is_demo


def test_client_demo_classify():
    client = VisionClient(demo=True)
    result = client.classify("dog_closeup.jpg")
    assert isinstance(result, ClassificationResult)
    assert result.labels[0].name == "Dog"


def test_client_demo_detect():
    client = VisionClient(demo=True)
    result = client.detect_objects("dog_closeup.jpg")
    assert isinstance(result, DetectionResult)
    assert len(result.objects) > 0


def test_client_demo_analyze():
    client = VisionClient(demo=True)
    report = client.analyze("dog_closeup.jpg")
    assert isinstance(report, AnalysisReport)
    assert len(report.available_features) >= 2


def test_client_demo_analyze_specific_features():
    client = VisionClient(demo=True)
    report = client.analyze("dog_closeup.jpg", features=["classification"])
    assert report.classification is not None
    assert report.detection is None


def test_client_accepts_image_path_types():
    client = VisionClient(demo=True)
    r1 = client.classify("dog_closeup.jpg")
    assert r1 is not None
    r2 = client.classify("/some/dir/dog_closeup.jpg")
    assert r2 is not None


@pytest.mark.live
def test_client_live_classify():
    client = VisionClient()
    result = client.classify("oci://vision-bucket/2.jpeg", max_results=10)
    assert isinstance(result, ClassificationResult)
    assert len(result.labels) > 0
