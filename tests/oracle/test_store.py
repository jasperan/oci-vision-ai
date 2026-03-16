from __future__ import annotations

import pytest

from oci_vision.core.client import VisionClient
from oci_vision.oracle.store import OracleVisionStore


@pytest.mark.oracle
def test_store_report_inserts_run_and_vectors(oracle_connection):
    client = VisionClient(demo=True)
    report = client.analyze("invoice_demo.png", features=["document"])
    store = OracleVisionStore(oracle_connection)

    run_id = store.store_report(report)

    assert run_id

    cursor = oracle_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM vision_runs WHERE run_id = :run_id", {"run_id": run_id})
    run_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM vision_vectors WHERE run_id = :run_id", {"run_id": run_id})
    vector_count = cursor.fetchone()[0]

    assert run_count == 1
    assert vector_count >= 1
