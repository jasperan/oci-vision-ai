import importlib
import sys
from types import SimpleNamespace

import pytest
from oci_vision.core.client import VisionClient
from oci_vision.core.models import AnalysisReport, ClassificationResult, DetectionResult


def test_live_tests_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OCI_VISION_RUN_LIVE", raising=False)

    from tests.conftest import should_run_live_tests

    assert should_run_live_tests() is False


def test_live_tests_enabled_with_env(monkeypatch):
    monkeypatch.setenv("OCI_VISION_RUN_LIVE", "1")

    from tests.conftest import should_run_live_tests

    assert should_run_live_tests() is True


def test_oracle_module_is_lazy_imported():
    sys.modules.pop("oci_vision.oracle", None)
    sys.modules.pop("oracledb", None)

    importlib.import_module("oci_vision.oracle")

    assert "oracledb" not in sys.modules


def test_cli_module_does_not_force_oracle_import():
    sys.modules.pop("oci_vision.oracle", None)
    sys.modules.pop("oci_vision.cli.app", None)
    sys.modules.pop("oracledb", None)

    importlib.import_module("oci_vision.cli.app")

    assert "oracledb" not in sys.modules


def test_web_module_does_not_force_oracle_import():
    sys.modules.pop("oci_vision.oracle", None)
    sys.modules.pop("oci_vision.web.app", None)
    sys.modules.pop("oracledb", None)

    importlib.import_module("oci_vision.web.app")

    assert "oracledb" not in sys.modules


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


def test_client_demo_text():
    client = VisionClient(demo=True)
    result = client.detect_text("sign_board.png")
    assert result is not None
    assert result.full_text == "STOP\nSCHOOL XING"


def test_client_demo_faces():
    client = VisionClient(demo=True)
    result = client.detect_faces("portrait_demo.png")
    assert result is not None
    assert len(result.faces) == 1
    assert result.faces[0].landmarks[0].type == "LEFT_EYE"


def test_client_demo_document():
    client = VisionClient(demo=True)
    result = client.analyze_document("invoice_demo.png")
    assert result is not None
    assert result.page_count == 1
    assert result.fields[0].label == "Invoice Number"


def test_build_classification_feature_with_model_id():
    feature = VisionClient._build_classification_feature(max_results=10, model_id="ocid1.model.oc1..demo")
    assert feature.feature_type == "IMAGE_CLASSIFICATION"
    assert feature.max_results == 10
    assert feature.model_id == "ocid1.model.oc1..demo"


def test_build_detection_feature_with_model_id():
    feature = VisionClient._build_detection_feature(max_results=5, model_id="ocid1.model.oc1..demo")
    assert feature.feature_type == "OBJECT_DETECTION"
    assert feature.max_results == 5
    assert feature.model_id == "ocid1.model.oc1..demo"


def test_build_text_feature_uses_image_text_detection_feature():
    feature = VisionClient._build_text_feature()
    assert type(feature).__name__ == "ImageTextDetectionFeature"
    assert feature.feature_type == "TEXT_DETECTION"


def test_live_classify_uses_analyze_image_without_name_error(monkeypatch):
    import oci.ai_vision.models as vm

    client = VisionClient(demo=False, config={})
    client._compartment_id = "ocid1.compartment.oc1..demo"

    response = vm.AnalyzeImageResult(
        labels=[vm.Label(name="Dog", confidence=0.99)],
        image_classification_model_version="1.0.0",
    )
    client._oci_client = SimpleNamespace(analyze_image=lambda req: SimpleNamespace(data=response))
    monkeypatch.setattr(client, "_ensure_oci_client", lambda: None)

    result = client.classify("missing.jpg", model_id="ocid1.model.oc1..demo")

    assert result is not None
    assert result.labels[0].name == "Dog"


def test_live_detect_uses_analyze_image_without_name_error(monkeypatch):
    import oci.ai_vision.models as vm

    client = VisionClient(demo=False, config={})
    client._compartment_id = "ocid1.compartment.oc1..demo"

    response = vm.AnalyzeImageResult(
        image_objects=[
            vm.ImageObject(
                name="Dog",
                confidence=0.98,
                bounding_polygon=vm.BoundingPolygon(
                    normalized_vertices=[
                        vm.NormalizedVertex(x=0.1, y=0.1),
                        vm.NormalizedVertex(x=0.4, y=0.1),
                        vm.NormalizedVertex(x=0.4, y=0.4),
                        vm.NormalizedVertex(x=0.1, y=0.4),
                    ]
                ),
            )
        ],
        object_detection_model_version="1.0.0",
    )
    client._oci_client = SimpleNamespace(analyze_image=lambda req: SimpleNamespace(data=response))
    monkeypatch.setattr(client, "_ensure_oci_client", lambda: None)

    result = client.detect_objects("missing.jpg", model_id="ocid1.model.oc1..demo")

    assert result is not None
    assert result.objects[0].name == "Dog"


def test_live_text_uses_analyze_image_without_name_error(monkeypatch):
    import oci.ai_vision.models as vm

    client = VisionClient(demo=False, config={})
    client._compartment_id = "ocid1.compartment.oc1..demo"

    vertices = [
        vm.NormalizedVertex(x=0.1, y=0.1),
        vm.NormalizedVertex(x=0.3, y=0.1),
        vm.NormalizedVertex(x=0.3, y=0.2),
        vm.NormalizedVertex(x=0.1, y=0.2),
    ]
    response = vm.AnalyzeImageResult(
        image_text=vm.ImageText(
            words=[vm.Word(text="STOP", confidence=0.99, bounding_polygon=vm.BoundingPolygon(normalized_vertices=vertices))],
            lines=[vm.Line(text="STOP", confidence=0.97, bounding_polygon=vm.BoundingPolygon(normalized_vertices=vertices), word_indexes=[0])],
        ),
        text_detection_model_version="1.0.0",
    )
    client._oci_client = SimpleNamespace(analyze_image=lambda req: SimpleNamespace(data=response))
    monkeypatch.setattr(client, "_ensure_oci_client", lambda: None)

    result = client.detect_text("missing.jpg")

    assert result is not None
    assert result.full_text == "STOP"


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


def test_parse_live_text_result():
    import oci.ai_vision.models as vm

    vertices = [
        vm.NormalizedVertex(x=0.1, y=0.1),
        vm.NormalizedVertex(x=0.3, y=0.1),
        vm.NormalizedVertex(x=0.3, y=0.2),
        vm.NormalizedVertex(x=0.1, y=0.2),
    ]
    response = vm.AnalyzeImageResult(
        image_text=vm.ImageText(
            words=[
                vm.Word(
                    text="STOP",
                    confidence=0.99,
                    bounding_polygon=vm.BoundingPolygon(normalized_vertices=vertices),
                )
            ],
            lines=[
                vm.Line(
                    text="STOP",
                    confidence=0.97,
                    bounding_polygon=vm.BoundingPolygon(normalized_vertices=vertices),
                    word_indexes=[0],
                )
            ],
        ),
        text_detection_model_version="1.0.0",
    )

    result = VisionClient._parse_text(response)

    assert result is not None
    assert result.model_version == "1.0.0"
    assert result.full_text == "STOP"
    assert result.lines[0].words[0].text == "STOP"


def test_parse_live_face_result():
    import oci.ai_vision.models as vm

    vertices = [
        vm.NormalizedVertex(x=0.25, y=0.2),
        vm.NormalizedVertex(x=0.55, y=0.2),
        vm.NormalizedVertex(x=0.55, y=0.7),
        vm.NormalizedVertex(x=0.25, y=0.7),
    ]
    response = vm.AnalyzeImageResult(
        detected_faces=[
            vm.Face(
                confidence=0.98,
                quality_score=0.94,
                bounding_polygon=vm.BoundingPolygon(normalized_vertices=vertices),
                landmarks=[
                    vm.Landmark(type="LEFT_EYE", x=0.34, y=0.35),
                    vm.Landmark(type="RIGHT_EYE", x=0.46, y=0.35),
                    vm.Landmark(type="NOSE_TIP", x=0.4, y=0.48),
                ],
            )
        ],
        face_detection_model_version="1.0.0",
    )

    result = VisionClient._parse_faces(response)

    assert result is not None
    assert result.model_version == "1.0.0"
    assert len(result.faces) == 1
    assert result.faces[0].landmarks[0].type == "LEFT_EYE"


def test_parse_live_document_result():
    import oci.ai_vision.models as vm

    box = vm.BoundingPolygon(
        normalized_vertices=[
            vm.NormalizedVertex(x=0.1, y=0.1),
            vm.NormalizedVertex(x=0.9, y=0.1),
            vm.NormalizedVertex(x=0.9, y=0.2),
            vm.NormalizedVertex(x=0.1, y=0.2),
        ]
    )
    response = vm.AnalyzeDocumentResult(
        pages=[
            vm.Page(
                page_number=1,
                lines=[
                    vm.Line(
                        text="INVOICE",
                        confidence=0.99,
                        bounding_polygon=box,
                        word_indexes=[0],
                    )
                ],
                words=[
                    vm.Word(
                        text="INVOICE",
                        confidence=0.99,
                        bounding_polygon=box,
                    )
                ],
                document_fields=[
                    vm.DocumentField(
                        field_type="KEY_VALUE",
                        field_label=vm.FieldLabel(name="Invoice Number", confidence=0.98),
                        field_value=vm.ValueString(
                            value_type="STRING",
                            text="INV-1001",
                            confidence=0.97,
                            bounding_polygon=box,
                            word_indexes=[0],
                            value="INV-1001",
                        ),
                    )
                ],
                tables=[
                    vm.Table(
                        row_count=2,
                        column_count=3,
                        header_rows=[
                            vm.TableRow(
                                cells=[
                                    vm.Cell(text="Item", row_index=0, column_index=0, confidence=0.99, bounding_polygon=box, word_indexes=[0]),
                                    vm.Cell(text="Qty", row_index=0, column_index=1, confidence=0.99, bounding_polygon=box, word_indexes=[0]),
                                    vm.Cell(text="Price", row_index=0, column_index=2, confidence=0.99, bounding_polygon=box, word_indexes=[0]),
                                ]
                            )
                        ],
                        body_rows=[
                            vm.TableRow(
                                cells=[
                                    vm.Cell(text="Widget", row_index=1, column_index=0, confidence=0.98, bounding_polygon=box, word_indexes=[0]),
                                    vm.Cell(text="2", row_index=1, column_index=1, confidence=0.98, bounding_polygon=box, word_indexes=[0]),
                                    vm.Cell(text="$10.00", row_index=1, column_index=2, confidence=0.98, bounding_polygon=box, word_indexes=[0]),
                                ]
                            )
                        ],
                        footer_rows=[],
                        confidence=0.96,
                        bounding_polygon=box,
                    )
                ],
            )
        ],
        text_detection_model_version="1.0.0",
        key_value_detection_model_version="1.0.0",
        table_detection_model_version="1.0.0",
    )

    result = VisionClient._parse_document_result(response)

    assert result is not None
    assert result.model_version == "1.0.0"
    assert result.page_count == 1
    assert result.full_text == "INVOICE"
    assert result.fields[0].label == "Invoice Number"
    assert result.tables[0].body_rows[0] == ["Widget", "2", "$10.00"]


@pytest.mark.live
def test_client_live_classify():
    client = VisionClient()
    result = client.classify("oci://vision-bucket/2.jpeg", max_results=10)
    assert isinstance(result, ClassificationResult)
    assert len(result.labels) > 0
