from __future__ import annotations

import oracledb

from oci_vision.oracle.config import OracleConfig

oracledb.defaults.thin_mode = True
oracledb.defaults.fetch_lobs = False


def connect(config: OracleConfig):
    return oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=config.resolved_dsn,
    )
