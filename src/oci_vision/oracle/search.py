from __future__ import annotations

from oci_vision.oracle.store import OracleVisionStore


def search_runs(conn, query: str, limit: int = 5):
    return OracleVisionStore(conn).search(query, limit=limit)
