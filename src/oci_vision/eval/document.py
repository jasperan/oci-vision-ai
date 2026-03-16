from __future__ import annotations

from typing import Any

from oci_vision.core.models import DocumentResult


def evaluate_document_result(prediction: DocumentResult, truth: DocumentResult) -> dict[str, Any]:
    truth_fields = {field.label: field.value for field in truth.fields}
    pred_fields = {field.label: field.value for field in prediction.fields}

    matched_fields = sum(
        1 for label, value in truth_fields.items() if pred_fields.get(label) == value
    )
    missing_fields = max(len(truth_fields) - matched_fields, 0)
    extra_fields = sum(1 for label in pred_fields if label not in truth_fields)
    field_accuracy = matched_fields / max(len(truth_fields), 1)

    truth_tables = [
        {"header_rows": table.header_rows, "body_rows": table.body_rows}
        for table in truth.tables
    ]
    pred_tables = [
        {"header_rows": table.header_rows, "body_rows": table.body_rows}
        for table in prediction.tables
    ]
    matched_tables = sum(1 for pred, actual in zip(pred_tables, truth_tables) if pred == actual)
    table_accuracy = matched_tables / max(len(truth_tables), 1) if truth_tables else 1.0

    return {
        "matched_fields": matched_fields,
        "missing_fields": missing_fields,
        "extra_fields": extra_fields,
        "field_accuracy": field_accuracy,
        "matched_tables": matched_tables,
        "table_accuracy": table_accuracy,
    }
