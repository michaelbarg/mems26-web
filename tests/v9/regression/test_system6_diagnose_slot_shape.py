"""T-187: /api/v9/system6/diagnose must read a DICT slot, not just a scalar.

Finding (31.08 22:07, live trade #939 open): the endpoint answered
`{"active": true, "trade": null, "note": "slot {...} not found in DB"}` while
the DB DID hold 939. Root: `system6_routes.py:52` did `int(slot)`, but
`ef01d040` (08-08) changed `gateway.live_slot` from a scalar to
`{"trade_id": "939", "mode": "live", ...}`. TypeError -> swallowed by the
except -> `trade: null`. Blind for 23 days, and the failure READ LIKE HEALTH.

The pre-existing tests missed it because they fed the scalar shape. These feed
BOTH shapes, which is the gap that let it live 23 days.
"""
import asyncio

import pytest

from backend.v9.api.v9 import system6_routes


class _Gw:
    def __init__(self, demo=None, live=None):
        self.demo_slot = demo
        self.live_slot = live


class _State:
    def __init__(self, gw):
        self.trading_gateway = gw


class _Req:
    """Minimal stand-in for fastapi Request (only .app.state is read)."""
    def __init__(self, gw):
        self.app = type("_App", (), {"state": _State(gw)})()


def _diagnose(gw):
    """Run the async route synchronously (no async pytest plugin installed)."""
    return asyncio.run(system6_routes.diagnose(_Req(gw)))


def _patch_db(monkeypatch, row):
    """Stub the module-level read helpers diagnose() imports lazily."""
    import backend.v9.db.read as _read
    monkeypatch.setattr(_read, "read_one", lambda *a, **k: row)
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: [])
    monkeypatch.setattr(
        system6_routes, "ruled_contracts", lambda *a, **k: 3, raising=False)


_ROW = {"id": 939, "direction": "SHORT", "entry_price": 7685.25,
        "stop": 7690.0, "t1_hit_ts": None}


# ── the regression itself ─────────────────────────────────────────────────

def test_dict_slot_is_read(monkeypatch):
    """THE BUG: dict slot used to raise int(dict) -> trade stayed null."""
    _patch_db(monkeypatch, _ROW)
    gw = _Gw(live={"trade_id": "939", "mode": "live", "state": "FILLED",
                   "entry_price": 7685.25})
    res = _diagnose(gw)
    assert res["active"] is True
    assert res.get("error") is None, f"unexpected error: {res.get('error')}"
    assert res["trade"] is not None, "dict slot still unreadable (T-187)"
    assert res["trade"]["id"] == 939
    assert res["trade"]["direction"] == "SHORT"


def test_scalar_slot_still_works(monkeypatch):
    """Backward compatibility: the old scalar shape must not break."""
    _patch_db(monkeypatch, _ROW)
    res = _diagnose(_Gw(live=939))
    assert res["trade"] is not None and res["trade"]["id"] == 939


def test_scalar_string_slot_still_works(monkeypatch):
    _patch_db(monkeypatch, _ROW)
    res = _diagnose(_Gw(live="939"))
    assert res["trade"] is not None and res["trade"]["id"] == 939


def test_demo_dict_slot_is_read(monkeypatch):
    """demo_slot is checked first — same shape change applies to it."""
    _patch_db(monkeypatch, _ROW)
    res = _diagnose(_Gw(demo={"trade_id": 939, "mode": "demo"}))
    assert res["trade"] is not None and res["trade"]["id"] == 939


# ── the other half: failures must NOT read like health ────────────────────

def test_empty_slot_still_reports_inactive(monkeypatch):
    _patch_db(monkeypatch, _ROW)
    assert _diagnose(_Gw()) == {"active": False}
    assert _diagnose(None) == {"active": False}


def test_unreadable_slot_reports_explicit_error(monkeypatch):
    """A slot we cannot parse must say so — not answer `trade: null` quietly."""
    _patch_db(monkeypatch, _ROW)
    res = _diagnose(_Gw(live={"mode": "live"}))  # no trade_id
    assert res["active"] is True
    assert res["error"] == "slot_unreadable"
    assert res["trade"] is None


def test_db_error_is_distinguishable_from_not_found(monkeypatch):
    """Read failure and genuine absence used to look identical."""
    import backend.v9.db.read as _read

    def _boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(_read, "read_one", _boom)
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: [])
    res = _diagnose(_Gw(live={"trade_id": "939"}))
    assert res["error"] == "trade_read_failed"

    _patch_db(monkeypatch, None)  # genuine not-found
    res2 = _diagnose(_Gw(live={"trade_id": "939"}))
    assert res2["error"] == "trade_not_in_db"
    assert res["error"] != res2["error"]


def test_no_bare_int_on_slot_remains():
    """Pin the shape bug itself: `int(slot)` must never come back as CODE.

    Comment lines are stripped first — the fix's own docstring quotes the bad
    expression, and matching that would make this test permanently red.
    """
    import inspect
    code = "\n".join(
        ln for ln in inspect.getsource(system6_routes).splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "int(slot)" not in code, "the T-187 int(dict) bug was reintroduced"
