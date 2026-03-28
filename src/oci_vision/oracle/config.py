from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class OracleConfig:
    user: str = ""
    password: str = ""
    host: str = "localhost"
    port: int = 1524
    service: str = "FREEPDB1"
    dsn: str | None = None
    enable: bool = False

    @classmethod
    def from_env(cls) -> "OracleConfig":
        return cls(
            user=os.getenv("OCI_VISION_ORACLE_USER", "").strip(),
            password=os.getenv("OCI_VISION_ORACLE_PASSWORD", "").strip(),
            host=os.getenv("OCI_VISION_ORACLE_HOST", "localhost"),
            port=int(os.getenv("OCI_VISION_ORACLE_PORT", "1524")),
            service=os.getenv("OCI_VISION_ORACLE_SERVICE", "FREEPDB1"),
            dsn=os.getenv("OCI_VISION_ORACLE_DSN"),
            enable=os.getenv("OCI_VISION_ENABLE_ORACLE", "0").strip().lower() in {"1", "true", "yes", "on"},
        )

    @property
    def resolved_dsn(self) -> str:
        return self.dsn or f"{self.host}:{self.port}/{self.service}"

    @property
    def enabled(self) -> bool:
        return self.enable and bool(self.user and self.password and self.resolved_dsn)
