from __future__ import annotations

import pytest

from oci_vision.core.client import VisionClient
from oci_vision.oracle.store import OracleVisionStore


@pytest.mark.oracle
def test_search_returns_invoice_match(oracle_connection):
    client = VisionClient(demo=True)
    report = client.analyze("invoice_demo.png", features=["document"])
    store = OracleVisionStore(oracle_connection)
    run_id = store.store_report(report)

    results = store.search("INV-1001", limit=3)

    assert results
    assert results[0]["run_id"] == run_id
    assert "INV-1001" in results[0]["chunk_text"]
