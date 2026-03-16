from __future__ import annotations

from .config import OracleConfig


def connect(config: OracleConfig):
    from .connection import connect as _connect

    return _connect(config)


def init_schema(conn) -> None:
    from .schema import init_schema as _init_schema

    return _init_schema(conn)


def reset_schema(conn) -> None:
    from .schema import reset_schema as _reset_schema

    return _reset_schema(conn)


class OracleVisionStore:
    def __new__(cls, conn):
        from .store import OracleVisionStore as _OracleVisionStore

        return _OracleVisionStore(conn)


def search_if_enabled(query: str, limit: int = 5):
    from .store import search_if_enabled as _search_if_enabled

    return _search_if_enabled(query, limit=limit)


def store_report_if_enabled(report):
    from .store import store_report_if_enabled as _store_report_if_enabled

    return _store_report_if_enabled(report)


__all__ = [
    "OracleConfig",
    "connect",
    "init_schema",
    "reset_schema",
    "OracleVisionStore",
    "search_if_enabled",
    "store_report_if_enabled",
]
