"""Route-account resolution (2026-07-27) — the root of "the system did not fire".

The account in the PLACE command becomes `o.TradeAccount` in the DLL, which
decides WHERE the order routes. Sending the hard-coded LIVE account while Sierra
sits in Sim ("Sim1") is a mismatch → ACSIL r=-1 GENERAL_ERROR_OR_NOT_ENABLED.
That killed all 3 live orders on 07-27 (16:45/16:55/17:25) while shadows filled.

Truth source = Sierra's own `trade_account` in sierra_state.json (fresh ≤10s),
env fallback only when the file is unusable (honest degradation).
"""
import json
import os
import time

import backend.v9.gateway.trading_gateway as gw


def _write_state(tmp_path, monkeypatch, acct, age_s=0.0, raw=None):
    p = tmp_path / "sierra_state.json"
    p.write_text(raw if raw is not None else json.dumps(
        {"ts": int(time.time()), "is_sim": 1, "trade_account": acct,
         "position_qty": 0, "avg_price": 0.0}))
    if age_s:
        old = time.time() - age_s
        os.utime(p, (old, old))
    monkeypatch.setenv("SIERRA_STATE_PATH", str(p))
    return p


def test_uses_sierra_sim_account(tmp_path, monkeypatch):
    """Sierra in Sim → route to Sim1, NOT the live account (the 07-27 bug)."""
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    _write_state(tmp_path, monkeypatch, "Sim1")
    assert gw._sierra_route_account() == "Sim1"


def test_uses_sierra_live_account(tmp_path, monkeypatch):
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    _write_state(tmp_path, monkeypatch, "37138283")
    assert gw._sierra_route_account() == "37138283"


def test_stale_state_falls_back_to_env(tmp_path, monkeypatch):
    """State older than 10s is not trusted → env fallback (no silent wrong route)."""
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    _write_state(tmp_path, monkeypatch, "Sim1", age_s=60)
    assert gw._sierra_route_account() == "37138283"


def test_missing_file_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    monkeypatch.setenv("SIERRA_STATE_PATH", str(tmp_path / "nope.json"))
    assert gw._sierra_route_account() == "37138283"


def test_corrupt_json_falls_back_to_env(tmp_path, monkeypatch):
    """The 07-27 inf-JSON class must not break routing."""
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    _write_state(tmp_path, monkeypatch, None, raw='{"trade_account":-inf,')
    assert gw._sierra_route_account() == "37138283"


def test_empty_account_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SIERRA_LIVE_ACCOUNT", "37138283")
    _write_state(tmp_path, monkeypatch, "")
    assert gw._sierra_route_account() == "37138283"
