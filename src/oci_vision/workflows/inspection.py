from __future__ import annotations

from collections import Counter

from oci_vision.core.client import VisionClient


def inspection_workflow(client: VisionClient, image: str) -> dict:
    report = client.analyze(image, features=["classification", "detection", "text"])
    return {
        "classification": [label.name for label in (report.classification.labels[:5] if report.classification else [])],
        "detection": dict(Counter(obj.name for obj in (report.detection.objects if report.detection else []))),
        "text": report.text.full_text if report.text else "",
    }
