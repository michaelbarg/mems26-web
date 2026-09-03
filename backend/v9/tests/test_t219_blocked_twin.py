"""T-219: shadow_blocked twin for every refused candidate.

Five isolation guarantees (spec §3):
  3.1 Structural: runs AFTER result is final
  3.2 Slot: never touches live_slot/demo_slot
  3.3 Sierra: no order written
  3.4 Feedback: NOT appended to shadow_trades (no phantom fires)
  3.5 Flag: BLOCKED_TWIN_V1, code default OFF
"""
import ast
import inspect
import os
import textwrap

import pytest


def test_blocked_twin_flag_in_route_setup():
    """The flag must be checked in route_setup."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    assert "BLOCKED_TWIN_V1" in source


def test_blocked_twin_does_not_append_shadow_trades():
    """shadow_trades.append must NOT appear in the T-219 block.
    Appending would feed duplicate_fire/cluster_guard with phantom fires."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    assert start > 0
    # The block from T-219 marker to the end of the try
    block = source[start:start + 3000]
    # shadow_trades.append must NOT be in this block
    assert "shadow_trades.append" not in block, (
        "MUTATION §3.4: shadow_blocked appends to shadow_trades — "
        "this feeds duplicate_fire/cluster_guard with phantom fires")


def test_blocked_twin_does_not_touch_daily_trades():
    """_daily_trades and _daily_pnl must NOT be incremented."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    block = source[start:start + 3000]
    # Check for actual assignment (=), not just mentions in comments
    code_lines = [l for l in block.split("\n") if l.strip() and not l.strip().startswith("#")]
    code_only = "\n".join(code_lines)
    assert "_daily_trades +=" not in code_only and "_daily_trades =" not in code_only, (
        "MUTATION §3.4: shadow_blocked increments _daily_trades")
    assert "_daily_pnl +=" not in code_only and "_daily_pnl =" not in code_only, (
        "MUTATION §3.4: shadow_blocked increments _daily_pnl")


def test_blocked_twin_has_daily_cap():
    """A daily cap must exist to bound management load."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    start = source.find("T-219")
    block = source[start:start + 3000]
    assert "SHADOW_BLOCKED_MAX_PER_DAY" in block or "_bt_max" in block, (
        "T-219 must have a daily cap (spec §4.2: ~124/day mean)")


def test_flag_off_no_effect():
    """BLOCKED_TWIN_V1=0 → the insertion block is skipped entirely."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway.route_setup)
    # The flag check must gate the entire block
    assert 'BLOCKED_TWIN_V1", "0"' in source, (
        "Flag must default to OFF")


# ─────────────────────────────────────────────────────────────────────────────
# 03.09 — the five tests above ALL passed while the feature was 100% dead
# (212 blocks on 03.09 → 212 TypeErrors → 0 rows ever). They are static source
# assertions; none of them CALLS route_setup. The tests below are behavioural.
#
# Two independent defects were found:
#   (a) `self._capture_cross_context(setup)` — the method takes ZERO args
#       (def at ~:4681, correct call at :987). Every blocked candidate raised
#       TypeError, swallowed by the `except Exception as _bt_err` → logged as
#       "non-fatal" → no twin.
#   (b) v9_trades.mode was varchar(10); 'shadow_blocked' is 14 chars → even
#       with (a) fixed the INSERT would fail. Migration 026 widens it to 20.
# ─────────────────────────────────────────────────────────────────────────────

import sys


class _FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class _FakeTrade:
    def __init__(self):
        self.quality = {}


class _FakeTradeManager:
    def __init__(self):
        self._db = _FakeDB()
        self.trades = {}

    def _get_trade(self, tid):
        return self.trades.get(int(tid))


class _StubGateway:
    """Duck-typed host for the REAL TradingGateway.route_setup.

    `_capture_cross_context` deliberately takes zero args — exactly like the
    production method — so passing `setup` raises TypeError here too.
    """

    TWIN_TRADE_ID = 4242

    def __init__(self, blocked_by="entry_location_quality"):
        self._blocked_by = blocked_by
        self.decisions = []
        self.shadow_trades = []
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self.cross_ctx_calls = 0
        self.shadow_calls = []
        self._trade_manager = _FakeTradeManager()

    # matches production signature: def _capture_cross_context(self) -> dict
    def _capture_cross_context(self):
        self.cross_ctx_calls += 1
        return {"woodies_system": {}, "tpo_system": {}}

    def _route_setup_inner(self, setup, system_id):
        return {"shadow": None, "demo": None, "live": None,
                "blocked_by": self._blocked_by,
                "reason": "chaser: pos=0.98 > 0.66 (top 34% of leg, no pullback)"}

    def _execute_shadow(self, setup, system_id, cross_context):
        self.shadow_calls.append(setup)
        self._trade_manager.trades[self.TWIN_TRADE_ID] = _FakeTrade()
        return {"trade_id": self.TWIN_TRADE_ID}

    def _persist_decision(self, dec):
        pass


def _blocked_setup():
    return {
        "direction": "LONG",
        "classification": "ZLR",
        "entry_price": 7764.75,
        "stop": 7756.25,
        "t1": 7770.0, "t2": 7775.0, "t3": 7780.0,
        "metadata": {"candidate_id": "cand-t219-1"},
    }


def _run(gw, monkeypatch, func=None):
    from backend.v9.gateway.trading_gateway import TradingGateway
    monkeypatch.setenv("BLOCKED_TWIN_V1", "shadow")
    monkeypatch.setenv("SHADOW_BLOCKED_MAX_PER_DAY", "150")
    fn = func or TradingGateway.route_setup
    return fn(gw, _blocked_setup(), 4)


def test_blocked_candidate_produces_shadow_blocked_twin(monkeypatch):
    """BEHAVIOURAL: a blocked candidate must produce exactly one twin."""
    gw = _StubGateway()
    result = _run(gw, monkeypatch)

    assert result["blocked_by"] == "entry_location_quality"
    assert gw.cross_ctx_calls == 1, "cross-context must be captured (zero-arg call)"
    assert len(gw.shadow_calls) == 1, (
        "T-219 produced NO twin — this is the 03.09 bug (0 rows in 212 blocks)")

    twin = gw.shadow_calls[0]
    assert twin["metadata"]["shadow_blocked"] is True
    assert twin["metadata"]["blocked_by"] == "entry_location_quality"

    # the quality dict written back onto the trade row
    row = gw._trade_manager.trades[_StubGateway.TWIN_TRADE_ID]
    assert row.quality["blocked_by"] == "entry_location_quality"
    assert row.quality["block_reason"].startswith("chaser: pos=0.98")
    assert row.quality["candidate_id"] == "cand-t219-1"
    assert gw._trade_manager._db.commits == 1

    # §3.4 isolation — measurement must never feed duplicate_fire/cluster_guard
    assert gw.shadow_trades == []
    assert gw._daily_trades == 0
    assert gw._shadow_blocked_today == 1


def test_mutation_restoring_setup_arg_kills_the_twin(monkeypatch):
    """MUTATION: put `setup` back into _capture_cross_context() → 0 twins.

    Proves the one-word fix is load-bearing and not cosmetic.
    """
    from backend.v9.gateway.trading_gateway import TradingGateway
    src = textwrap.dedent(inspect.getsource(TradingGateway.route_setup))
    mutated = src.replace("self._capture_cross_context() if hasattr(",
                          "self._capture_cross_context(setup) if hasattr(")
    assert mutated != src, "mutation target not found — the fix moved?"

    ns = dict(sys.modules["backend.v9.gateway.trading_gateway"].__dict__)
    exec(compile(mutated, "<t219-mutant>", "exec"), ns)

    gw = _StubGateway()
    _run(gw, monkeypatch, func=ns["route_setup"])
    assert gw.shadow_calls == [], (
        "MUTATION FAILED TO KILL: the twin survived _capture_cross_context(setup) "
        "— the test is not actually exercising the fixed line")


def test_daily_cap_is_honoured(monkeypatch):
    """SHADOW_BLOCKED_MAX_PER_DAY bounds the twin count."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    monkeypatch.setenv("BLOCKED_TWIN_V1", "shadow")
    monkeypatch.setenv("SHADOW_BLOCKED_MAX_PER_DAY", "2")
    gw = _StubGateway()
    for _ in range(5):
        TradingGateway.route_setup(gw, _blocked_setup(), 4)
    assert gw._shadow_blocked_today == 2, (
        f"cap not honoured: {gw._shadow_blocked_today} twins with cap=2")
    assert len(gw.shadow_calls) == 2


def test_flag_off_produces_no_twin(monkeypatch):
    """BLOCKED_TWIN_V1 unset → byte-identical behaviour (no twin, no capture)."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    monkeypatch.delenv("BLOCKED_TWIN_V1", raising=False)
    gw = _StubGateway()
    TradingGateway.route_setup(gw, _blocked_setup(), 4)
    assert gw.shadow_calls == []
    assert gw.cross_ctx_calls == 0


def test_not_blocked_produces_no_twin(monkeypatch):
    """A candidate that was NOT blocked must not get a shadow_blocked twin."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    monkeypatch.setenv("BLOCKED_TWIN_V1", "shadow")
    gw = _StubGateway(blocked_by=None)
    TradingGateway.route_setup(gw, _blocked_setup(), 4)
    assert gw.shadow_calls == []


def test_mode_column_is_wide_enough_for_shadow_blocked():
    """DEFECT (b): 'shadow_blocked' is 14 chars — varchar(10) fails the INSERT.

    Reads the model, which is the schema contract; migration 026 applies the
    same widening to the live DB.
    """
    from backend.v9.db.models.trades import V9Trade
    length = V9Trade.__table__.c.mode.type.length
    assert length is not None and length >= len("shadow_blocked"), (
        f"v9_trades.mode is varchar({length}) — 'shadow_blocked' (14 chars) "
        "cannot be written")
