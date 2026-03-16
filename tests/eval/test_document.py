from __future__ import annotations

from oci_vision.core.models import DocumentField, DocumentResult, DocumentTable
from oci_vision.eval.document import evaluate_document_result


def test_evaluate_document_result_fields_and_tables():
    prediction = DocumentResult(
        model_version="1.0",
        fields=[
            DocumentField(field_type="KEY_VALUE", label="Invoice Number", value="INV-1001", confidence=0.98),
            DocumentField(field_type="KEY_VALUE", label="Total Due", value="$10.00", confidence=0.96),
        ],
        tables=[
            DocumentTable(
                row_count=2,
                column_count=3,
                header_rows=["Item", "Qty", "Price"],
                body_rows=[["Widget", "2", "$10.00"]],
                confidence=0.95,
            )
        ],
    )
    truth = DocumentResult(
        model_version="1.0",
        fields=[
            DocumentField(field_type="KEY_VALUE", label="Invoice Number", value="INV-1001", confidence=1.0),
            DocumentField(field_type="KEY_VALUE", label="Total Due", value="$10.00", confidence=1.0),
            DocumentField(field_type="KEY_VALUE", label="Bill To", value="Example Co.", confidence=1.0),
        ],
        tables=[
            DocumentTable(
                row_count=2,
                column_count=3,
                header_rows=["Item", "Qty", "Price"],
                body_rows=[["Widget", "2", "$10.00"]],
                confidence=1.0,
            )
        ],
    )

    metrics = evaluate_document_result(prediction, truth)

    assert metrics["matched_fields"] == 2
    assert metrics["missing_fields"] == 1
    assert metrics["field_accuracy"] == 2 / 3
    assert metrics["table_accuracy"] == 1.0
