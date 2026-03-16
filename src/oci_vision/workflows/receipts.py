from __future__ import annotations

from oci_vision.core.client import VisionClient


def receipt_workflow(client: VisionClient, image: str) -> dict:
    document = client.analyze_document(image)
    if document is None:
        return {"field_count": 0, "fields": {}, "table_count": 0}

    return {
        "field_count": len(document.fields),
        "fields": {field.label: field.value for field in document.fields},
        "table_count": len(document.tables),
        "page_count": document.page_count,
    }
