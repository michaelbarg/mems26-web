"""Verify conftest isolation — gateway decisions NEVER touch the live file.

Regression test for the 2026-08-11/12 incidents where pytest wrote 510
fixture lines to the live gateway_decisions.jsonl during RTH.
"""
import os

import pytest


class TestDecisionIsolation:
    """Gateway decisions must be redirected to tmp_path."""

    def test_env_set(self):
        """GATEWAY_DECISIONS_PATH must NOT point to the real export dir."""
        path = os.environ.get("GATEWAY_DECISIONS_PATH", "")
        assert path, "GATEWAY_DECISIONS_PATH must be set by conftest"
        assert "SierraChart" not in path, \
            f"GATEWAY_DECISIONS_PATH points to live dir: {path}"
        assert "tmp" in path.lower() or "pytest" in path.lower() or "/var/" in path, \
            f"GATEWAY_DECISIONS_PATH should be in a temp dir: {path}"

    def test_test_mode_set(self):
        """MEMS26_TEST_MODE must be 1."""
        assert os.environ.get("MEMS26_TEST_MODE") == "1"

    def test_hydrate_off(self):
        """GATEWAY_DECISIONS_HYDRATE must be unset."""
        assert os.environ.get("GATEWAY_DECISIONS_HYDRATE") in (None, "")

    def test_gateway_writes_to_tmp(self, tmp_path):
        """A TradingGateway instance writes decisions to the temp file."""
        from unittest.mock import MagicMock
        from backend.v9.gateway.trading_gateway import TradingGateway

        gw = TradingGateway.__new__(TradingGateway)
        # Minimal init for _persist_decision
        from pathlib import Path
        from collections import deque
        gw._decisions_path = Path(os.environ["GATEWAY_DECISIONS_PATH"])
        gw.decisions = deque(maxlen=300)
        gw._last_rotation_date = None

        # Write a decision
        gw._persist_decision({"test": True, "ts": "2026-08-12T10:00:00Z"})

        # Verify it went to the temp file
        assert gw._decisions_path.exists()
        content = gw._decisions_path.read_text()
        assert '"test": true' in content

        # Verify the real file was NOT touched
        real_path = os.path.expanduser(
            "~/SierraChart_Data/v9_export/gateway_decisions.jsonl")
        if os.path.exists(real_path):
            real_content = open(real_path).read()
            assert '"test": true' not in real_content

    def test_v9_export_dir_isolated(self):
        """V9_EXPORT_DIR must be redirected to tmp."""
        path = os.environ.get("V9_EXPORT_DIR", "")
        assert path, "V9_EXPORT_DIR must be set by conftest"
        assert "SierraChart" not in path
