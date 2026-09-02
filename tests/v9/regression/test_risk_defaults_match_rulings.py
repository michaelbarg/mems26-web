# -*- coding: utf-8 -*-
"""Code defaults must equal the ruled values — not stricter, not looser.

Michael 2026-09-02: "לא אישרתי להפסיק עסקאות אחרי 2 הפסדים רציפים ולא אישרתי
מגבלה של 250 דולר". Neither number was ever ruled; both lived as code defaults
in risk_checks.py, waiting for any environment without .env to impose them.
CLAUDE.md standing-decisions: the ruled behavior IS the code default, so a
restart/clone keeps it — no env var needed.
"""
import importlib, os
import pytest

def test_defaults_without_env_are_the_ruled_values(monkeypatch):
    monkeypatch.delenv("RISK_DAILY_LOSS_CAP", raising=False)
    monkeypatch.delenv("RISK_CONSECUTIVE_LOSS_LIMIT", raising=False)
    import backend.v9.gateway.risk_checks as rc
    importlib.reload(rc)
    assert rc.DAILY_LOSS_CAP == 800.0, "cap default drifted from the 07-24 ruling (800)"
    assert rc.CONSECUTIVE_LOSS_LIMIT == 0, "a 2-loss stop-day was never ruled; default must be off"

def test_gateway_path_default_is_off():
    src = open("backend/v9/gateway/trading_gateway.py",encoding="utf-8").read()
    assert 'os.getenv("RISK_CONSECUTIVE_LOSS_LIMIT", "0")' in src
