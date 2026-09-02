"""T-214: t3 required belt — PLACE rejected if t3 is NULL/0 on >=3 contracts.

9/27 recent live trades had t3=NULL/0 → DLL sends contracts without a target
→ unprotected runner.
"""
import os
import tempfile
from unittest.mock import patch

import pytest
from backend.v9.services.sierra_command import command_from_setup

# Prevent test from writing to the live Sierra signals directory
_TMP = tempfile.mkdtemp()
os.environ.setdefault("MEMS26_SIGNALS_DIR", _TMP)


def _setup(t3=7680.0, contracts=5):
    return {
        "firing_system": 2,
        "direction": "LONG",
        "entry_price": 7660.0,
        "stop": 7651.0,
        "t1": 7668.0,
        "t2": 7675.0,
        "t3": t3,
        "classification": "REACTIVE_LONG",
        "confidence": 0.9,
        "metadata": {},
    }


class TestT3Belt:

    def test_valid_t3_passes(self):
        """t3=7680 → command built normally."""
        with patch.dict(os.environ, {"T3_REQUIRED_V1": "1", "FIXED_CONTRACTS_5": "1"}):
            cmd = command_from_setup(
                _setup(t3=7680.0),
                trade_id="999", account="test", mode="demo")
        assert cmd.get("rejected") is not True

    def test_null_t3_rejected(self):
        """t3=None on 5 contracts → rejected."""
        with patch.dict(os.environ, {"T3_REQUIRED_V1": "1", "FIXED_CONTRACTS_5": "1"}):
            cmd = command_from_setup(
                _setup(t3=None),
                trade_id="999", account="test", mode="demo")
        assert cmd.get("rejected") is True
        assert "t3_missing" in cmd.get("reason", "")

    def test_zero_t3_rejected(self):
        """t3=0 on 5 contracts → rejected."""
        with patch.dict(os.environ, {"T3_REQUIRED_V1": "1", "FIXED_CONTRACTS_5": "1"}):
            cmd = command_from_setup(
                _setup(t3=0),
                trade_id="999", account="test", mode="demo")
        assert cmd.get("rejected") is True

    def test_flag_off_allows_null_t3(self):
        """Flag OFF → null t3 passes (byte-identical)."""
        with patch.dict(os.environ, {"FIXED_CONTRACTS_5": "1"}, clear=False):
            os.environ.pop("T3_REQUIRED_V1", None)
            cmd = command_from_setup(
                _setup(t3=None),
                trade_id="999", account="test", mode="demo")
        assert cmd.get("rejected") is not True
