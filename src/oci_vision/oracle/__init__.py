from __future__ import annotations

from .config import OracleConfig


def _is_oracle_enabled() -> bool:
    return OracleConfig.from_env().enabled


def _missing_oracle_dependency_message() -> str:
    return "Oracle integration is enabled but python-oracledb is not installed. Install with: pip install -e '.[oracle]'"


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
    if not _is_oracle_enabled():
        return []

    try:
        from .store import search_if_enabled as _search_if_enabled
    except ModuleNotFoundError as exc:
        if exc.name == 'oracledb':
            raise RuntimeError(_missing_oracle_dependency_message()) from exc
        raise

    return _search_if_enabled(query, limit=limit)


def store_report_if_enabled(report):
    if not _is_oracle_enabled():
        return None

    try:
        from .store import store_report_if_enabled as _store_report_if_enabled
    except ModuleNotFoundError as exc:
        if exc.name == 'oracledb':
            raise RuntimeError(_missing_oracle_dependency_message()) from exc
        raise

    return _store_report_if_enabled(report)


__all__ = [
    'OracleConfig',
    'connect',
    'init_schema',
    'reset_schema',
    'OracleVisionStore',
    'search_if_enabled',
    'store_report_if_enabled',
]
