from __future__ import annotations

import pytest

from oci_vision.oracle.config import OracleConfig
from oci_vision.oracle.connection import connect
from oci_vision.oracle.schema import init_schema, reset_schema


@pytest.fixture()
def oracle_connection():
    config = OracleConfig.from_env()
    conn = connect(config)
    init_schema(conn)
    reset_schema(conn)
    try:
        yield conn
    finally:
        reset_schema(conn)
        conn.close()
