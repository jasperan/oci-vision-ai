from __future__ import annotations

from oci_vision.oracle.config import OracleConfig
from oci_vision.oracle.schema import init_schema


class RecordingCursor:
    def __init__(self):
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(" ".join(statement.split()))


class RecordingConnection:
    def __init__(self):
        self.cursor_obj = RecordingCursor()
        self.committed = False

    def cursor(self) -> RecordingCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True


def test_oracle_config_is_fail_secure_without_credentials(monkeypatch):
    monkeypatch.setenv("OCI_VISION_ENABLE_ORACLE", "1")
    monkeypatch.delenv("OCI_VISION_ORACLE_USER", raising=False)
    monkeypatch.delenv("OCI_VISION_ORACLE_PASSWORD", raising=False)
    monkeypatch.delenv("OCI_VISION_ORACLE_DSN", raising=False)

    config = OracleConfig.from_env()

    assert config.user == ""
    assert config.password == ""
    assert config.enabled is False


def test_oracle_config_enables_with_explicit_credentials(monkeypatch):
    monkeypatch.setenv("OCI_VISION_ENABLE_ORACLE", "1")
    monkeypatch.setenv("OCI_VISION_ORACLE_USER", "vision_app")
    monkeypatch.setenv("OCI_VISION_ORACLE_PASSWORD", "secret-pass")
    monkeypatch.setenv("OCI_VISION_ORACLE_HOST", "db.local")
    monkeypatch.setenv("OCI_VISION_ORACLE_PORT", "1540")
    monkeypatch.setenv("OCI_VISION_ORACLE_SERVICE", "FREEPDB1")

    config = OracleConfig.from_env()

    assert config.enabled is True
    assert config.resolved_dsn == "db.local:1540/FREEPDB1"


def test_init_schema_does_not_force_sysaux_tablespace():
    conn = RecordingConnection()

    init_schema(conn)

    assert conn.committed is True
    assert conn.cursor_obj.statements
    assert all("SYSAUX" not in statement.upper() for statement in conn.cursor_obj.statements)
