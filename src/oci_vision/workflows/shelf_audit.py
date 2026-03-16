from __future__ import annotations

from collections import Counter

from oci_vision.core.client import VisionClient


def shelf_audit_workflow(client: VisionClient, image: str) -> dict:
    detection = client.detect_objects(image)
    counts = Counter(obj.name for obj in (detection.objects if detection else []))
    return {
        "object_count": sum(counts.values()),
        "objects": dict(counts),
    }
