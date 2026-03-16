from __future__ import annotations

from oci_vision.core.client import VisionClient


def archive_search_workflow(client: VisionClient, images: list[str], query: str) -> dict:
    needle = query.lower()
    matches = []

    for image in images:
        document = client.analyze_document(image)
        if document is None:
            continue

        haystacks = [document.full_text, *[field.value for field in document.fields]]
        if any(needle in (text or "").lower() for text in haystacks):
            matches.append(
                {
                    "image": image,
                    "page_count": document.page_count,
                    "field_count": len(document.fields),
                }
            )

    return {
        "query": query,
        "match_count": len(matches),
        "matches": matches,
    }
