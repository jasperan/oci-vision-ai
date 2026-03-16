from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


LIVE_ENV_VAR = "OCI_VISION_RUN_LIVE"
ORACLE_ENV_VAR = "OCI_VISION_RUN_ORACLE"


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def should_run_live_tests() -> bool:
    return _is_truthy(os.getenv(LIVE_ENV_VAR))


def should_run_oracle_tests() -> bool:
    return _is_truthy(os.getenv(ORACLE_ENV_VAR))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_live = pytest.mark.skip(reason=f"live OCI tests require {LIVE_ENV_VAR}=1")
    skip_oracle = pytest.mark.skip(reason=f"Oracle integration tests require {ORACLE_ENV_VAR}=1")

    run_live = should_run_live_tests()
    run_oracle = should_run_oracle_tests()

    for item in items:
        if "live" in item.keywords and not run_live:
            item.add_marker(skip_live)
        if "oracle" in item.keywords and not run_oracle:
            item.add_marker(skip_oracle)
