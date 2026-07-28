"""Account-Monitor passthrough (Michael 2026-07-28: "צריך לקחת נתונים מה-account
monitor").

Sierra's Trade Accounts window is fed by sc.GetTradeAccountData(), not by the
position struct — the screenshot showed DailyProfit/Loss 0.00 on the position
path while the account carried a real daily loss. The DLL now exports an
acct_* block guarded by acct_ok; when the guard is 0/absent (DLL not yet
rebuilt) every acct_* field must be None so the UI renders "—" rather than a
plausible wrong number (Rule 1: honest failure > synthetic value).
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.v9.api.v9.account_state_routes as asr


def _client(tmp_path, state: dict) -> TestClient:
    p = tmp_path / "sierra_state.json"
    p.write_text(json.dumps(state))
    asr.STATE = p
    app = FastAPI()
    app.include_router(asr.router)
    return TestClient(app)


_BASE = {"position_qty": 0, "avg_price": 0.0, "working_orders": 0, "is_sim": 0}
_ACCT = {
    "acct_ok": 1, "acct_cash_balance": 1946.19, "acct_account_value": 1908.69,
    "acct_available_funds": 527.64, "acct_margin_req": 1381.05,
    "acct_open_positions_pl": -37.5, "acct_daily_pl": -1167.71,
    "acct_daily_net_loss_limit": 0.0, "acct_loss_limit_reached": 0,
    "acct_under_margin": 0, "acct_trading_disabled": 0, "acct_is_sim": 0,
}


def test_account_monitor_values_passed_through(tmp_path):
    d = _client(tmp_path, {**_BASE, **_ACCT}).get("/api/v9/account/state").json()
    s = d["sierra_state"]
    assert s["acct_ok"] is True
    assert s["acct_account_value"] == 1908.69
    assert s["acct_cash_balance"] == 1946.19
    assert s["acct_daily_pl"] == -1167.71
    assert s["acct_open_positions_pl"] == -37.5


def test_acct_ok_zero_nulls_every_field(tmp_path):
    """Sierra could not supply account data → "—", never a stale/zero number."""
    bad = {**_ACCT, "acct_ok": 0}
    s = _client(tmp_path, {**_BASE, **bad}).get("/api/v9/account/state").json()["sierra_state"]
    assert s["acct_ok"] is False
    for f in ("acct_account_value", "acct_daily_pl", "acct_cash_balance",
              "acct_under_margin", "acct_trading_disabled"):
        assert s[f] is None, f


def test_old_dll_without_acct_block_is_none_not_missing(tmp_path):
    """Pre-build state file (no acct_* keys at all) must still answer with the
    keys present and None — the UI binds to them unconditionally."""
    s = _client(tmp_path, _BASE).get("/api/v9/account/state").json()["sierra_state"]
    assert s["acct_ok"] is False
    assert s["acct_account_value"] is None and s["acct_daily_pl"] is None


def test_position_daily_pnl_still_exposed_separately(tmp_path):
    """The position-struct number is kept (some readers use it) but must NOT be
    presented as the account number — they are different quantities."""
    st = {**_BASE, "daily_pnl": 0.0, **_ACCT}
    s = _client(tmp_path, st).get("/api/v9/account/state").json()["sierra_state"]
    assert s["daily_pnl"] == 0.0
    assert s["acct_daily_pl"] == -1167.71
