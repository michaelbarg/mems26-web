# -*- coding: utf-8 -*-
"""BE_AFTER_T1_RULE_V1 — the "better NOT to move the stop to breakeven after T1" side
of System 6.

Michael 19.10.2026: "after T1 is realized we move the stop to the entry price — unless;
for that we create a mechanism for when it is better to move the stop earlier or better
NOT to move it — that is System 6".

Pinned here
  * flag OFF (unset / "0" / anything not 1|true|yes|apply) is byte-identical to today:
    BE+1T, and the rule's inputs (live extension, tpo / day-type reads) are never touched;
  * flag ON + the trade runs WITH the session's accepted extension (System 1) on a
    trend / variation day + a structure sits between the ORIGINAL stop and the entry
    -> the stop is HELD one tick beyond that structure (not breakeven), MODIFY_STOP once;
  * every other case -> exactly today's BE+1T / structure-trail, plus a one-line reason;
  * never widens, never at/beyond the entry, any exception -> breakeven (fail-safe);
  * the hold is not undone by the OTHER post-T1 breakeven enforcers: System 6's
    stop_not_at_be (SYSTEM6_AUTOCORRECT=protective is live) and the BE+1T floor of the
    runner trails (F5 swing trail, dynamic structure trail).

Fixture = the FIX-12 one (TradeManager via __new__, stubbed management log + emitter)
plus a fake "world" for the three things the rule reads from outside the trade:
trade_context.get_live_expansion, db.read.read_one (v9_tpo_sessions / v9_day_type_history)
and the ET trading date.
"""
import datetime
import logging
import sys
import types
from unittest.mock import MagicMock

import pytest

import backend.v9.services.trade_manager.manager as M
from backend.v9.services.trade_manager.manager import TradeManager

LOGGER = "backend.v9.services.trade_manager.manager"
TODAY = datetime.date(2026, 10, 19)

ENTRY = 7770.0
LONG_STOP, SHORT_STOP = 7757.0, 7783.0          # the ORIGINAL (entry) stops, 13 pt risk
# LONG: IB low 7762.50 sits between the original stop and the entry -> hold 7762.25
LONG_TPO = {"ib_high": 7790.0, "ib_low": 7762.5, "vah_price": 7775.0, "val_price": 7750.0}
# SHORT: IB high 7777.50 sits between the entry and the original stop -> hold 7777.75
SHORT_TPO = {"ib_high": 7777.5, "ib_low": 7750.0, "vah_price": 7790.0, "val_price": 7765.0}


class World:
    """Everything the rule reads from outside the trade."""

    def __init__(self):
        self.ext = {"dir": "UP", "ref": "ib_high"}     # trade_context.get_live_expansion()
        self.ext_error = None
        self.tpo = None                                # v9_tpo_sessions CASH row for today
        self.tpo_error = None
        self.hist = None                               # v9_day_type_history row for today
        self.hist_error = None
        self.calls = []                                # every outside read, in order

    def live_expansion(self):
        self.calls.append("get_live_expansion")
        if self.ext_error is not None:
            raise self.ext_error
        return self.ext

    def read_one(self, sql, params=None):
        self.calls.append(("read_one", " ".join(sql.split()), dict(params or {})))
        if "v9_tpo_sessions" in sql:
            assert "session_type = 'CASH'" in sql, "IB / VA edges must come from the CASH session"
            if self.tpo_error is not None:
                raise self.tpo_error
            return self.tpo
        if "v9_day_type_history" in sql:
            if self.hist_error is not None:
                raise self.hist_error
            return self.hist
        raise AssertionError("unexpected query: %s" % sql)

    def sql_params(self, table):
        return [c[2] for c in self.calls
                if isinstance(c, tuple) and table in c[1]]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Pin every flag the Smart-BE path reads — a sourced production .env must not leak in."""
    for k, v in {"STOP_STRUCTURE_TRAIL_V1": "0", "ZLR_MGMT_V1": "0",
                 "S6_TREND_BE_DELAY_V1": "0", "POSITION_REF_PRICE_V1": "0",
                 "RUNNER_TRAIL_V2": "0"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("BE_AFTER_T1_RULE_V1", raising=False)


@pytest.fixture
def world(monkeypatch):
    w = World()
    import backend.v9.common.trading_date as td
    import backend.v9.db.read as dbread
    import backend.v9.services.trade_context as tc
    monkeypatch.setattr(tc, "get_live_expansion", w.live_expansion)
    monkeypatch.setattr(dbread, "read_one", w.read_one)
    monkeypatch.setattr(td, "et_today", lambda: TODAY)
    return w


def _on(monkeypatch, value="1"):
    monkeypatch.setenv("BE_AFTER_T1_RULE_V1", value)


def _tm():
    tm = TradeManager.__new__(TradeManager)         # skip __init__ (no DB needed)
    tm._db = None
    tm._mgmt_log = []
    tm._log_management = lambda tid, kind, payload=None: tm._mgmt_log.append((tid, kind, payload))
    tm._emits = []
    tm._emit_modify_stop = lambda trade, stop: tm._emits.append((trade.id, stop))
    return tm


def _trade(direction="LONG", day="Variation", stop=None, entry_stop=None, anchor=None,
           quality_extra=None, drop_entry_stop=False):
    long_ = direction == "LONG"
    original = LONG_STOP if long_ else SHORT_STOP
    meta = {}
    if anchor is not None:
        meta["structural_anchor"] = anchor
    q = {"entry_stop": original if entry_stop is None else entry_stop,
         "contracts": 3, "metadata": meta}
    q.update(quality_extra or {})
    if drop_entry_stop:
        q.pop("entry_stop")
    return types.SimpleNamespace(
        id=4242, mode="shadow", state="PARTIAL", direction=direction, entry_price=ENTRY,
        stop=original if stop is None else stop, quality=q, cross_context=[],
        day_type_at_entry=day)


def _run(trade, tm=None):
    tm = tm or _tm()
    tm._apply_smart_be_after_t1(trade)
    return tm


def _msgs(caplog):
    return [r.getMessage() for r in caplog.records]


BE_LONG, BE_SHORT = ENTRY + 0.25, ENTRY - 0.25   # what Smart-BE does today (BE+1T / BE-1T)
HOLD_LONG, HOLD_SHORT = 7762.25, 7777.75         # IB low - 1 tick / IB high + 1 tick
HOLD_REASON = "structure-hold (with-extension day)"


def _snapshot(tm, trade):
    """Everything an outside observer could see after one Smart-BE call."""
    return {
        "stop": trade.stop,
        "emits": list(tm._emits),
        "mgmt": [(tid, kind, dict(p or {})) for tid, kind, p in tm._mgmt_log],
        "ctx": [dict(c) for c in trade.cross_context],
        "quality": dict(trade.quality),
    }


def _arm(world, direction="LONG", **kw):
    """Rig the world so the rule WOULD hold: extension with the trade, a CASH IB edge
    between the original stop and the entry."""
    world.ext = {"dir": "UP" if direction == "LONG" else "DOWN"}
    world.tpo = LONG_TPO if direction == "LONG" else SHORT_TPO
    for k, v in kw.items():
        setattr(world, k, v)


# ══════════════════════════════════════════════ A. flag OFF = today, byte for byte
class TestFlagOff:

    @pytest.mark.parametrize("value", [None, "0", "", "off", "false", "no", "2"])
    @pytest.mark.parametrize("direction, be", [("LONG", BE_LONG), ("SHORT", BE_SHORT)])
    def test_breakeven_exactly_as_today(self, monkeypatch, world, caplog, value, direction, be):
        if value is not None:
            monkeypatch.setenv("BE_AFTER_T1_RULE_V1", value)
        _arm(world, direction)                     # the rule would hold, were it on
        t = _trade(direction)
        original = t.stop
        with caplog.at_level(logging.INFO, logger=LOGGER):
            tm = _run(t)
        assert t.stop == be
        assert tm._emits == [(4242, be)]
        assert tm._mgmt_log == [(4242, "SMART_BE", {"from": original, "to": be})]
        assert t.cross_context == [{"event": "stop_move", "from": original, "to": be,
                                    "reason": "BE+1T after T1 hit"}]
        assert "be_rule_hold" not in t.quality
        assert world.calls == [], "flag OFF must not even read the rule's inputs"
        assert not [m for m in _msgs(caplog) if "BE_RULE" in m], "flag OFF stays silent"

    def test_flag_is_read_at_call_time(self, monkeypatch):
        assert M._be_after_t1_rule_enabled() is False           # unset = off
        monkeypatch.setenv("BE_AFTER_T1_RULE_V1", "1")
        assert M._be_after_t1_rule_enabled() is True
        monkeypatch.setenv("BE_AFTER_T1_RULE_V1", "0")
        assert M._be_after_t1_rule_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes", "apply", " apply "])
    def test_every_truthy_spelling_enables_the_rule(self, monkeypatch, world, value):
        monkeypatch.setenv("BE_AFTER_T1_RULE_V1", value)
        _arm(world)
        t = _trade("LONG")
        _run(t)
        assert t.stop == HOLD_LONG


# ══════════════════════════════════════════════ B. flag ON: the hold
class TestHold:

    def test_long_variation_with_long_extension_holds_ib_low_minus_one_tick(
            self, monkeypatch, world, caplog):
        """The spec case: Variation day, LONG, extension LONG, IB low between the
        original stop and the entry -> stop = IB low - 1 tick, MODIFY_STOP once."""
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", day="Variation")
        with caplog.at_level(logging.INFO, logger=LOGGER):
            tm = _run(t)
        assert t.stop == HOLD_LONG, "IB low 7762.50 - 1 tick; NOT BE+1T 7770.25"
        assert tm._emits == [(4242, HOLD_LONG)], "MODIFY_STOP exactly once"
        assert tm._mgmt_log == [(4242, "SMART_BE", {
            "from": LONG_STOP, "to": HOLD_LONG, "reason": HOLD_REASON, "anchor": 7762.5,
            "anchor_kind": "ib_low", "day_type": "Variation", "extension": "LONG"})]
        assert t.cross_context == [{"event": "stop_move", "from": LONG_STOP, "to": HOLD_LONG,
                                    "reason": HOLD_REASON}]
        hold = t.quality["be_rule_hold"]
        assert (hold["stop"], hold["anchor"], hold["kind"]) == (HOLD_LONG, 7762.5, "ib_low")
        assert hold["day_type"] == "Variation" and hold["ext"] == "LONG" and hold["ts"]
        assert ("BE_RULE hold-structure after T1: trade 4242 stop 7757.00 -> 7762.25 "
                "(day Variation, dir LONG = extension, anchor ib_low 7762.50)"
                in " | ".join(_msgs(caplog)))

    def test_short_mirror_holds_ib_high_plus_one_tick(self, monkeypatch, world):
        _on(monkeypatch)
        _arm(world, "SHORT")
        t = _trade("SHORT", day="Trend_Normal")
        tm = _run(t)
        assert t.stop == HOLD_SHORT, "IB high 7777.50 + 1 tick; NOT BE-1T 7769.75"
        assert tm._emits == [(4242, HOLD_SHORT)]
        assert tm._mgmt_log[0][2]["reason"] == HOLD_REASON
        assert tm._mgmt_log[0][2]["extension"] == "SHORT"
        assert t.quality["be_rule_hold"]["kind"] == "ib_high"

    @pytest.mark.parametrize("day", ["Trend_Normal", "Trend_DD", "Normal_Variation", "Variation",
                                     "trend_normal", "Trend Normal", "VARIATION"])
    def test_continuation_day_types_hold(self, monkeypatch, world, day):
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", day=day)
        _run(t)
        assert t.stop == HOLD_LONG

    @pytest.mark.parametrize("day", ["Normal", "Neutral", "Non_Trend", "Double_Distribution",
                                     "", None])
    def test_other_day_types_keep_breakeven(self, monkeypatch, world, caplog, day):
        """Normal day (and every non-continuation type) -> BE+1T, with the reason logged."""
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", day=day)
        with caplog.at_level(logging.INFO, logger=LOGGER):
            tm = _run(t)
        assert t.stop == BE_LONG
        assert tm._emits == [(4242, BE_LONG)]
        assert "be_rule_hold" not in t.quality
        assert any("BE_RULE breakeven after T1: trade 4242 (reason: day-type (" in m
                   for m in _msgs(caplog)), _msgs(caplog)

    @pytest.mark.parametrize("direction, ext", [
        ("LONG", {"dir": "DOWN"}), ("SHORT", {"dir": "UP"}),
        ("LONG", {"dir": "UNDETERMINED"}), ("SHORT", {"dir": "UNDETERMINED"}),
        ("LONG", None), ("SHORT", None)])
    def test_not_with_extension_keeps_breakeven(self, monkeypatch, world, caplog, direction, ext):
        """Direction against the extension (or no / undetermined extension) -> BE+1T."""
        _on(monkeypatch)
        _arm(world, direction, ext=ext)
        t = _trade(direction, day="Variation")
        with caplog.at_level(logging.INFO, logger=LOGGER):
            tm = _run(t)
        be = BE_LONG if direction == "LONG" else BE_SHORT
        assert t.stop == be
        assert tm._emits == [(4242, be)]
        assert "be_rule_hold" not in t.quality
        assert any("BE_RULE breakeven after T1: trade 4242 (reason: not-with-extension"
                   in m for m in _msgs(caplog)), _msgs(caplog)
        assert world.sql_params("v9_tpo_sessions") == [], "no extension -> structure never read"

    def test_day_type_falls_back_to_todays_history_row(self, monkeypatch, world):
        _on(monkeypatch)
        _arm(world, "LONG", hist={"day_type": "Variation"})
        t = _trade("LONG", day=None)
        _run(t)
        assert t.stop == HOLD_LONG
        assert world.sql_params("v9_day_type_history") == [{"d": "2026-10-19"}]
        assert world.sql_params("v9_tpo_sessions") == [{"d": "2026-10-19"}]

    def test_history_row_that_is_not_a_continuation_day_keeps_breakeven(self, monkeypatch, world):
        _on(monkeypatch)
        _arm(world, "LONG", hist={"day_type": "Normal"})
        t = _trade("LONG", day=None)
        _run(t)
        assert t.stop == BE_LONG

    def test_trade_day_type_wins_over_history(self, monkeypatch, world):
        """day_type_at_entry (the column) is the trade's own record; the history table is
        only a fallback and is not even queried when the trade has one."""
        _on(monkeypatch)
        _arm(world, "LONG", hist={"day_type": "Variation"})
        t = _trade("LONG", day="Normal")
        _run(t)
        assert t.stop == BE_LONG
        assert world.sql_params("v9_day_type_history") == []

    def test_day_type_from_the_quality_json(self, monkeypatch, world):
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", day=None, quality_extra={"day_type_at_entry": "Trend_DD"})
        _run(t)
        assert t.stop == HOLD_LONG
        assert world.sql_params("v9_day_type_history") == []


# ══════════════════════════════════════════════ C. the structural anchor
def _tpo(**kw):
    row = {"ib_high": None, "ib_low": None, "vah_price": None, "val_price": None}
    row.update(kw)
    return row


class TestAnchor:
    """Candidates: quality.metadata.structural_anchor, CASH ib_low / val (LONG) or
    ib_high / vah (SHORT). Only a level STRICTLY between the ORIGINAL stop (7757) and
    the entry (7770), whose held stop is tighter than the original and the current
    stop, qualifies. The farthest from the entry wins."""

    @pytest.mark.parametrize("tpo, anchor, stop, kind", [
        pytest.param(None, None, BE_LONG, None, id="no-row-no-anchor"),
        pytest.param(_tpo(), None, BE_LONG, None, id="row-without-levels"),
        pytest.param(_tpo(ib_low=0.0, val_price=0.0), None, BE_LONG, None, id="zero-means-unset"),
        pytest.param(_tpo(ib_low=7757.0), None, BE_LONG, None, id="ib-low-at-original-stop"),
        pytest.param(_tpo(ib_low=7750.0, val_price=7745.0), None, BE_LONG, None,
                     id="all-below-original-stop"),
        pytest.param(_tpo(ib_low=7757.25), None, BE_LONG, None, id="hold-would-equal-original"),
        pytest.param(_tpo(ib_low=7770.0), None, BE_LONG, None, id="ib-low-at-entry"),
        pytest.param(_tpo(ib_low=7775.0, val_price=7772.0), None, BE_LONG, None,
                     id="above-entry-never-beyond-entry"),
        pytest.param(_tpo(ib_high=7765.0, vah_price=7766.0), None, BE_LONG, None,
                     id="long-ignores-the-high-side-edges"),
        pytest.param(_tpo(ib_low=7757.5), None, 7757.25, "ib_low", id="one-tick-tighter-than-original"),
        pytest.param(_tpo(ib_low=7769.75), None, 7769.5, "ib_low", id="just-under-entry"),
        pytest.param(_tpo(ib_low=7762.6), None, 7762.25, "ib_low", id="off-grid-level-floors-to-tick"),
        pytest.param(None, 7764.0, 7763.75, "pattern", id="pattern-anchor-alone"),
        pytest.param(_tpo(val_price=7760.0), None, 7759.75, "val", id="value-area-edge-alone"),
        pytest.param(_tpo(ib_low=7762.5, val_price=7759.0), 7765.0, 7758.75, "val",
                     id="farthest-from-entry-wins"),
        pytest.param(_tpo(ib_low=7762.5, val_price=7750.0), 7765.0, HOLD_LONG, "ib_low",
                     id="candidate-beyond-original-stop-is-dropped"),
    ])
    def test_long(self, monkeypatch, world, tpo, anchor, stop, kind):
        _on(monkeypatch)
        _arm(world, "LONG", tpo=tpo)
        t = _trade("LONG", anchor=anchor)
        tm = _run(t)
        assert t.stop == stop
        assert tm._emits == [(4242, stop)], "exactly one MODIFY_STOP either way"
        if kind is None:
            assert "be_rule_hold" not in t.quality
            assert stop == BE_LONG
        else:
            assert t.quality["be_rule_hold"]["kind"] == kind
            assert stop < BE_LONG, "a hold is always tighter than the original, never beyond BE"

    @pytest.mark.parametrize("tpo, anchor, stop, kind", [
        pytest.param(None, None, BE_SHORT, None, id="no-row-no-anchor"),
        pytest.param(_tpo(ib_high=7783.0), None, BE_SHORT, None, id="ib-high-at-original-stop"),
        pytest.param(_tpo(ib_high=7770.0), None, BE_SHORT, None, id="ib-high-at-entry"),
        pytest.param(_tpo(ib_low=7775.0, val_price=7776.0), None, BE_SHORT, None,
                     id="short-ignores-the-low-side-edges"),
        pytest.param(_tpo(ib_high=7777.4), None, 7777.75, "ib_high", id="off-grid-level-ceils-to-tick"),
        pytest.param(_tpo(ib_high=7777.5, vah_price=7780.0), 7775.0, 7780.25, "vah",
                     id="farthest-from-entry-wins"),
    ])
    def test_short(self, monkeypatch, world, tpo, anchor, stop, kind):
        _on(monkeypatch)
        _arm(world, "SHORT", tpo=tpo)
        t = _trade("SHORT", anchor=anchor)
        tm = _run(t)
        assert t.stop == stop
        assert tm._emits == [(4242, stop)]
        if kind is None:
            assert "be_rule_hold" not in t.quality
        else:
            assert t.quality["be_rule_hold"]["kind"] == kind
            assert stop > BE_SHORT

    def test_never_widens_when_the_stop_is_already_tighter_than_the_hold(self, monkeypatch, world):
        """Current stop 7765.00 is already tighter than IB low - 1 tick (7762.25): holding
        there would WIDEN it -> no hold, today's behaviour (BE+1T, which tightens)."""
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", stop=7765.0)
        _run(t)
        assert t.stop == BE_LONG
        assert "be_rule_hold" not in t.quality

    def test_the_original_stop_not_the_current_one_bounds_the_window(self, monkeypatch, world):
        """The stop had been pulled up pre-T1 (7760). IB low 7762.50 is still tighter than
        both the original (7757) and the current stop -> hold."""
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", stop=7760.0)
        _run(t)
        assert t.stop == HOLD_LONG
        assert t.cross_context[0]["from"] == 7760.0

    def test_a_level_between_original_and_current_stop_is_not_a_hold(self, monkeypatch, world):
        """IB low 7758.50 is inside (original 7757, entry) but the hold stop 7758.25 is
        below the current stop 7760 -> would widen -> BE+1T."""
        _on(monkeypatch)
        _arm(world, "LONG", tpo=_tpo(ib_low=7758.5))
        t = _trade("LONG", stop=7760.0)
        _run(t)
        assert t.stop == BE_LONG

    def test_original_stop_falls_back_to_initial_stop(self, monkeypatch, world):
        """No quality.entry_stop recorded -> the stop Smart-BE saw (initial_stop) bounds it."""
        _on(monkeypatch)
        _arm(world, "LONG")
        t = _trade("LONG", drop_entry_stop=True)
        _run(t)
        assert t.stop == HOLD_LONG
        assert t.quality["initial_stop"] == LONG_STOP

    def test_pure_geometry_edges(self):
        """The decision function itself — no IO, tick grid, strictness."""
        pick = M._be_rule_pick_hold
        c = [("ib_low", 7762.5)]
        assert pick("LONG", ENTRY, LONG_STOP, LONG_STOP, 0.25, c) == {
            "hold": True, "kind": "ib_low", "anchor": 7762.5, "stop": 7762.25}
        assert pick("LONG", ENTRY, LONG_STOP, LONG_STOP, 0.25, []) == {
            "hold": False, "reason": "no-anchor"}
        assert pick("LONG", ENTRY, LONG_STOP, LONG_STOP, 0.25, [("ib_low", 7757.25)]) == {
            "hold": False, "reason": "not-tighter"}
        assert pick("FLAT", ENTRY, LONG_STOP, LONG_STOP, 0.25, c)["hold"] is False
        assert pick("LONG", None, LONG_STOP, LONG_STOP, 0.25, c)["hold"] is False
        assert pick("LONG", ENTRY, None, None, 0.25, c)["hold"] is False
        assert pick("LONG", ENTRY, LONG_STOP, LONG_STOP, 0.25,
                    [("x", "n/a"), ("y", float("nan")), ("z", None), ("w", -1.0)])["hold"] is False


# ══════════════════════════════════════════════ D. fail-safe: any exception -> today's BE+1T
class TestFailSafe:

    @pytest.mark.parametrize("breaker", ["extension", "tpo", "history", "decide"])
    def test_exception_in_the_rule_means_breakeven(self, monkeypatch, world, caplog, breaker):
        _on(monkeypatch)
        _arm(world, "LONG")
        tm = _tm()
        t = _trade("LONG", day="Variation")
        if breaker == "extension":
            world.ext_error = RuntimeError("live expansion unavailable")
        elif breaker == "tpo":
            world.tpo_error = RuntimeError("db gone")
        elif breaker == "history":
            t.day_type_at_entry = None
            world.hist_error = RuntimeError("db gone")
        else:
            def _boom(*a, **k):
                raise ValueError("bug inside the rule")
            tm._be_rule_decide = _boom
        with caplog.at_level(logging.INFO, logger=LOGGER):
            _run(t, tm)
        assert t.stop == BE_LONG, "fail-safe = exactly today's BE+1T"
        assert tm._emits == [(4242, BE_LONG)]
        assert "be_rule_hold" not in t.quality
        warn = [r.getMessage() for r in caplog.records
                if r.levelno == logging.WARNING and "BE_RULE failed" in r.getMessage()]
        assert len(warn) == 1 and "fail-safe -> breakeven" in warn[0], _msgs(caplog)

    def test_garbage_inputs_are_simply_no_anchor_not_an_error(self, monkeypatch, world, caplog):
        _on(monkeypatch)
        _arm(world, "LONG", tpo=_tpo(ib_low="n/a", val_price=float("nan")))
        t = _trade("LONG", anchor="oops")
        with caplog.at_level(logging.INFO, logger=LOGGER):
            _run(t)
        assert t.stop == BE_LONG
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING], _msgs(caplog)

    def test_a_malformed_extension_payload_is_not_an_extension(self, monkeypatch, world):
        _on(monkeypatch)
        for bad in ("sideways", 42, [], {"ref": "ib_high"}, {"dir": None}):
            _arm(world, "LONG", ext=bad)
            t = _trade("LONG")
            _run(t)
            assert t.stop == BE_LONG, bad


# ══════════════════════════════════════════════ E. rule declines == flag off, byte for byte
def _decline_normal_day(w, t):
    t.day_type_at_entry = "Normal"


def _decline_against(w, t):
    w.ext = {"dir": "DOWN" if t.direction == "LONG" else "UP"}


def _decline_no_anchor(w, t):
    w.tpo = None


def _decline_not_tighter(w, t):
    # the hold stop would equal the ORIGINAL stop -> not a tightening
    w.tpo = _tpo(ib_low=7757.25) if t.direction == "LONG" else _tpo(ib_high=7782.75)


def _decline_ext_raises(w, t):
    w.ext_error = RuntimeError("boom")


def _decline_tpo_raises(w, t):
    w.tpo_error = RuntimeError("boom")


DECLINES = {
    "normal-day": _decline_normal_day,
    "against-extension": _decline_against,
    "extension-undetermined": lambda w, t: setattr(w, "ext", {"dir": "UNDETERMINED"}),
    "no-extension": lambda w, t: setattr(w, "ext", None),
    "no-anchor": _decline_no_anchor,
    "anchor-not-tighter": _decline_not_tighter,
    "extension-read-raises": _decline_ext_raises,
    "tpo-read-raises": _decline_tpo_raises,
}


class TestDeclinedEqualsFlagOff:
    """Whenever the rule says "no", flag ON must leave EXACTLY what flag OFF leaves: the
    same stop, the same MODIFY_STOP, the same management-log row, the same audit entry,
    the same quality JSON — with or without STOP_STRUCTURE_TRAIL_V1."""

    @pytest.mark.parametrize("structure", [False, True], ids=["bare-BE", "structure-trail"])
    @pytest.mark.parametrize("direction, struct_stop, be", [("LONG", 7764.0, BE_LONG),
                                                            ("SHORT", 7776.0, BE_SHORT)])
    @pytest.mark.parametrize("name", sorted(DECLINES))
    def test_byte_identical(self, monkeypatch, world, name, direction, struct_stop, be, structure):
        def run(flag_on):
            world.ext_error = world.tpo_error = world.hist_error = None
            _arm(world, direction)
            if flag_on:
                monkeypatch.setenv("BE_AFTER_T1_RULE_V1", "1")
            else:
                monkeypatch.delenv("BE_AFTER_T1_RULE_V1", raising=False)
            t = _trade(direction, day="Variation")
            DECLINES[name](world, t)
            tm = _tm()
            if structure:
                monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "1")
                tm._structure_stop_after_t1 = lambda d: struct_stop     # tightens vs the original
            _run(t, tm)
            return _snapshot(tm, t)

        off, on = run(False), run(True)
        assert on == off
        assert off["stop"] == (struct_stop if structure else be)
        assert len(off["emits"]) == 1 and "be_rule_hold" not in off["quality"]


# ══════════════════════════════════════════════ F. precedence, lifecycle, plumbing
class TestPrecedenceAndLifecycle:

    def test_hold_supersedes_the_structure_trail(self, monkeypatch, world):
        _on(monkeypatch)
        _arm(world)
        monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "1")
        tm = _tm()

        def _must_not_run(direction):
            raise AssertionError("structure-trail consulted after a hold")
        tm._structure_stop_after_t1 = _must_not_run
        t = _trade("LONG")
        _run(t, tm)
        assert t.stop == HOLD_LONG

    def test_zlr_keeps_its_plain_be_and_never_consults_the_rule(self, monkeypatch, world):
        """ZLR_MGMT_V1's own ruling (plain BE at T1) returns before the new hook."""
        monkeypatch.setenv("ZLR_MGMT_V1", "1")
        _on(monkeypatch)
        _arm(world)
        t = _trade("LONG", quality_extra={"classification": "ZLR"})
        tm = _run(t)
        assert t.stop == ENTRY
        assert tm._emits == [(4242, ENTRY)]
        assert world.calls == []
        assert "be_rule_hold" not in t.quality

    def test_e2_trend_be_delay_still_comes_first(self, monkeypatch, world):
        """E2 (S6_TREND_BE_DELAY_V1) skips the BE move on a Trend day altogether."""
        monkeypatch.setenv("S6_TREND_BE_DELAY_V1", "1")
        _on(monkeypatch)
        _arm(world)
        t = _trade("LONG", day="Trend_Normal", quality_extra={"day_type_at_entry": "Trend_Normal"})
        tm = _run(t)
        assert t.stop == LONG_STOP
        assert tm._emits == []
        assert world.calls == []

    def test_duplicate_t1_report_does_not_turn_the_hold_into_breakeven(
            self, monkeypatch, world, caplog):
        _on(monkeypatch)
        _arm(world)
        tm, t = _tm(), _trade("LONG")
        _run(t, tm)
        first = _snapshot(tm, t)
        with caplog.at_level(logging.INFO, logger=LOGGER):
            _run(t, tm)
            _run(t, tm)
        assert _snapshot(tm, t) == first, "the 2nd/3rd T1 report must be a no-op"
        assert t.stop == HOLD_LONG and len(tm._emits) == 1
        assert any("BE_RULE hold already applied" in m for m in _msgs(caplog))

    def test_the_marker_is_inert_once_the_flag_is_off(self, monkeypatch, world):
        """A hold stamped while the flag was ON changes nothing after a restart WITHOUT the
        flag: Smart-BE does exactly what it does today (BE+1T tightens the held stop)."""
        _on(monkeypatch)
        _arm(world)
        tm, t = _tm(), _trade("LONG")
        _run(t, tm)
        assert t.stop == HOLD_LONG
        monkeypatch.delenv("BE_AFTER_T1_RULE_V1")
        _run(t, tm)
        assert t.stop == BE_LONG

    def test_hold_goes_out_through_the_real_modify_stop_plumbing(self, monkeypatch, world):
        """The REAL _emit_modify_stop (not a stub): one command with the held stop, the
        per-contract stop ids, and the write-back + commit."""
        sent = []
        monkeypatch.setattr("backend.v9.services.sierra_command.write_modify_stop",
                            lambda **kw: sent.append(kw) or {"ok": True})
        monkeypatch.setenv("DEMO_EXECUTION_ENABLED", "1")
        monkeypatch.setenv("STOP_MOVE_TARGET_RESTORE_V1", "0")
        _on(monkeypatch)
        _arm(world)

        class _DB:
            commits = 0

            def commit(self):
                _DB.commits += 1

            def rollback(self):
                pass
        tm = TradeManager.__new__(TradeManager)
        tm._db = _DB()
        tm._log_management = lambda *a, **k: None
        t = _trade("LONG", quality_extra={"sierra_order_id": 10110, "c1_stop_id": 11,
                                          "c2_stop_id": 12})
        t.mode = "demo"
        tm._apply_smart_be_after_t1(t)
        assert sent == [{"trade_id": "4242", "order_id": 10110, "new_stop": HOLD_LONG,
                         "stop_ids": [11, 12]}]
        assert t.stop == HOLD_LONG and _DB.commits == 1


# ══════════════════════════════════════════════ G. the OTHER post-T1 breakeven enforcers
# A hold is only real if nothing snaps it back to BE on the next bar. Three live
# enforcers would: System 6's stop_not_at_be AUTO fix (SYSTEM6_AUTOCORRECT=protective),
# and the BE+1T floor of the F5 swing trail / the dynamic structure trail (and the
# inert hwm trail). Each honours the marker — only while the flag is ON.
class TestSystem6:

    @staticmethod
    def _issues(direction, stop, held):
        from backend.v9.systems.system6_supervisor import diagnose_trade
        return diagnose_trade(
            trade={"direction": direction, "entry_price": ENTRY, "stop": stop,
                   "be_rule_hold": held}, atr=4.0, t1_hit=True)

    @pytest.mark.parametrize("direction, stop", [("LONG", HOLD_LONG), ("SHORT", HOLD_SHORT)])
    def test_a_held_stop_is_not_a_stop_not_at_be_fault(self, monkeypatch, direction, stop):
        codes = lambda held: [i.code for i in self._issues(direction, stop, held).issues]  # noqa: E731
        # flag OFF: today's invariant, marker or not
        assert "stop_not_at_be" in codes(True)
        assert "stop_not_at_be" in codes(False)
        _on(monkeypatch)
        # flag ON + marker: the deliberate hold is not a fault (and nothing to auto-correct)
        rep = self._issues(direction, stop, True)
        assert "stop_not_at_be" not in [i.code for i in rep.issues]
        assert rep.auto_corrections == []
        # flag ON, NO marker: a stop left under BE by anything else is still a fault
        rep = self._issues(direction, stop, False)
        fault = [i for i in rep.issues if i.code == "stop_not_at_be"]
        assert fault and fault[0].correction == {"op": "MODIFY_STOP", "price": ENTRY}

    @staticmethod
    def _scan(monkeypatch, quality, stop):
        from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

        class _TM:
            def __init__(self):
                self.modify_calls = []

            def _emit_modify_stop(self, trade, price):
                self.modify_calls.append(price)

            def _emit_drop_target(self, trade, target_field):
                return True
        for k, v in {"SYSTEM6_SUPERVISOR": "1", "SYSTEM6_AUTOCORRECT": "protective",
                     "SYSTEM6_REVERSAL_TIGHTEN_V1": "0", "S6_STUCK_TO_BE_V1": "0",
                     "OPS_LOG_DISABLE": "1"}.items():
            monkeypatch.setenv(k, v)
        det = BarLevelDetector(trade_manager=_TM())
        det._system6_scan(types.SimpleNamespace(
            id=4242, direction="LONG", entry_price=ENTRY, stop=stop, t1=None, t2=None, t3=None,
            contracts=None, t1_hit_ts=datetime.datetime.now(), quality=quality))
        return det._tm.modify_calls

    def test_the_live_scan_does_not_correct_a_held_stop_back_to_be(self, monkeypatch):
        """End to end through BarLevelDetector._system6_scan with the protective autocorrect
        that is live: the marker in trade.quality reaches the supervisor."""
        marker = {"be_rule_hold": {"stop": HOLD_LONG}}
        # flag OFF -> System 6 corrects to BE exactly as it does today
        assert self._scan(monkeypatch, dict(marker), HOLD_LONG) == [ENTRY]
        _on(monkeypatch)
        # flag ON + marker -> no correction
        assert self._scan(monkeypatch, dict(marker), HOLD_LONG) == []
        # flag ON, no marker (a different trade / an un-held stop) -> corrected as today
        assert self._scan(monkeypatch, {}, HOLD_LONG) == [ENTRY]


PREV = [dict(h=100 + i * 0.1, l=95 + i * 0.1, c=98 + i * 0.1) for i in range(40)]   # ATR ~ 5


def _swing_bars(direction):
    """7400 -> 7380 down, then up: the last confirmed swing LOW is 7379 (SHORT: the
    mirror image around 7390, last confirmed swing HIGH 7401)."""
    down = [("%02d:00" % i, 7400 - i * 2, 7401 - i * 2, 7399 - i * 2, 7400 - i * 2)
            for i in range(11)]
    up = [("%02d:00" % (11 + i), 7380 + i * 3, 7381 + i * 3, 7379 + i * 3, 7380 + i * 3)
          for i in range(8)]
    bars = [dict(t=t, o=o, h=h, l=l, c=c) for (t, o, h, l, c) in down + up]
    if direction == "SHORT":
        bars = [dict(t=b["t"], o=14780.0 - b["o"], h=14780.0 - b["l"], l=14780.0 - b["h"],
                     c=14780.0 - b["c"]) for b in bars]
    return bars


# per direction: entry, ORIGINAL stop, held stop (structure - 1 tick), F5 swing-trail anchor
# (swing -/+ 1 tick), and the BE+1T / BE-1T floor the trails use today
RUNNER = {
    "LONG": dict(entry=7395.0, original=7370.0, held=7375.75, anchor=7378.75, floor=7395.25),
    "SHORT": dict(entry=7385.0, original=7410.0, held=7404.25, anchor=7401.25, floor=7384.75),
}


def _runner(direction, stop, marked, case=None):
    c = case or RUNNER[direction]
    q = {"initial_stop": c["original"], "entry_stop": c["original"]}
    if marked:
        q["be_rule_hold"] = {"stop": c["held"]}
    now = datetime.datetime.now(datetime.timezone.utc)
    return types.SimpleNamespace(
        id=4242, entry_price=c["entry"], stop=stop, direction=direction, t1_hit_ts=now,
        entry_ts=now - datetime.timedelta(hours=1), quality=q, cross_context=[], state="PARTIAL",
        mode="live", t2=None, t3=None, t2_hit_ts=None, t3_hit_ts=None)


def _runner_tm(bars=None):
    tm = _tm()
    tm._db = MagicMock()
    tm._swing_bars_today = lambda: (bars, PREV)
    tm._apply_window_anchor_trail = lambda trade: None      # STOP_PERBAR_STRUCT_V1: not under test
    return tm


class TestRunnerStopFloor:

    @pytest.mark.parametrize("direction", ["LONG", "SHORT"])
    def test_floor_is_be_unless_a_hold_is_active(self, monkeypatch, direction):
        tm = _tm()
        be = BE_LONG if direction == "LONG" else BE_SHORT
        hold = HOLD_LONG if direction == "LONG" else HOLD_SHORT
        plain = _trade(direction)
        marked = _trade(direction, quality_extra={"be_rule_hold": {"stop": hold}})
        floor = lambda tr: tm._runner_stop_floor(tr, direction, ENTRY, 0.25)  # noqa: E731
        assert floor(plain) == be and floor(marked) == be, "flag OFF = today's BE+-1T"
        _on(monkeypatch)
        assert floor(plain) == be, "flag ON but no hold on this trade"
        assert floor(marked) == hold, "flag ON + hold -> the held structure stop"

    @pytest.mark.parametrize("direction", ["LONG", "SHORT"])
    def test_a_bad_marker_can_never_loosen_or_break_the_floor(self, monkeypatch, direction):
        _on(monkeypatch)
        tm = _tm()
        be = BE_LONG if direction == "LONG" else BE_SHORT
        beyond = be + 5 if direction == "LONG" else be - 5      # on the wrong side of the floor
        for bad in (None, "yes", 7.5, {}, {"stop": None}, {"stop": "x"}, {"stop": float("nan")},
                    {"stop": 0}, {"stop": -3}, {"stop": beyond}):
            t = _trade(direction, quality_extra={"be_rule_hold": bad})
            assert tm._runner_stop_floor(t, direction, ENTRY, 0.25) == be, bad
        t = _trade(direction)
        t.quality = "not-a-dict"
        assert tm._runner_stop_floor(t, direction, ENTRY, 0.25) == be


# the hwm trail (RUNNER_TRAIL_V1) and the dynamic structure trail work off a 10-pt risk
RISK10 = {
    "LONG": dict(entry=7395.0, original=7385.0, held=7389.75, floor=7395.25),
    "SHORT": dict(entry=7385.0, original=7395.0, held=7390.25, floor=7384.75),
}


class TestTrailsHonourTheHold:

    @pytest.mark.parametrize("direction", ["LONG", "SHORT"])
    def test_f5_scenario_is_the_real_swing_math(self, direction):
        """Anti-tautology: the anchors the tests below expect are what the real swing
        engine computes on these bars (not numbers typed to fit)."""
        from backend.v9.services.trade_manager.swing_trail import (
            swing_rev_threshold, swing_trail_stop)
        got = swing_trail_stop(_swing_bars(direction), direction,
                               rev=swing_rev_threshold(PREV), offset_ticks=1)
        assert got == RUNNER[direction]["anchor"]

    @pytest.mark.parametrize("direction", ["LONG", "SHORT"])
    def test_f5_swing_trail_tightens_the_hold_by_structure_not_to_be(self, monkeypatch, direction):
        c = RUNNER[direction]
        monkeypatch.setenv("RUNNER_TRAIL_V2", "1")
        bars = _swing_bars(direction)
        # flag OFF: a stop-hold marker is inert -> today's BE+-1T floor
        tm, t = _runner_tm(bars), _runner(direction, c["held"], True)
        assert tm.apply_structural_swing_trail(t) is True
        assert t.stop == c["floor"]
        _on(monkeypatch)
        # flag ON but no hold on this trade -> the BE+-1T floor, as today
        tm, t = _runner_tm(bars), _runner(direction, c["held"], False)
        assert tm.apply_structural_swing_trail(t) is True
        assert t.stop == c["floor"]
        # flag ON + hold -> floored at the HELD stop: the confirmed swing tightens it
        tm, t = _runner_tm(bars), _runner(direction, c["held"], True)
        assert tm.apply_structural_swing_trail(t) is True
        assert t.stop == c["anchor"]
        assert tm._emits == [(4242, c["anchor"])]

    @pytest.mark.parametrize("direction", ["LONG", "SHORT"])
    def test_f5_never_widens_a_hold(self, monkeypatch, direction):
        monkeypatch.setenv("RUNNER_TRAIL_V2", "1")
        _on(monkeypatch)
        tighter = 7380.0 if direction == "LONG" else 7400.0     # already tighter than the swing
        tm, t = _runner_tm(_swing_bars(direction)), _runner(direction, tighter, True)
        t.quality["be_rule_hold"]["stop"] = tighter
        assert tm.apply_structural_swing_trail(t) is False
        assert t.stop == tighter and tm._emits == []

    @pytest.mark.parametrize("direction, bar, trail", [("LONG", (7400.0, 7396.0), 7390.0),
                                                       ("SHORT", (7384.0, 7380.0), 7390.0)])
    def test_hwm_trail_floor(self, monkeypatch, direction, bar, trail):
        c = RISK10[direction]
        monkeypatch.setattr("backend.v9.config_loader.load_stop_anchors", lambda: {})   # k = 1.0R
        run = lambda marked: self._hwm(direction, bar, marked)  # noqa: E731
        t, tm = run(True)                                # flag OFF -> BE+-1T floor
        assert t.stop == c["floor"]
        _on(monkeypatch)
        t, tm = run(False)                               # flag ON, no hold -> BE+-1T floor
        assert t.stop == c["floor"]
        t, tm = run(True)                                # flag ON + hold -> the hwm trail itself
        assert t.stop == trail and tm._emits == [(4242, trail)]

    @staticmethod
    def _hwm(direction, bar, marked):
        tm, t = _runner_tm(), _runner(direction, RISK10[direction]["held"], marked,
                                      case=RISK10[direction])
        tm.apply_trail_after_t1(t, bar[0], bar[1])
        return t, tm

    @pytest.mark.parametrize("direction, zone, new_stop", [
        ("LONG", dict(anchor_extreme=7391.0, zone_low=7391.0, zone_high=7393.0,
                      zone_range=2.0, advance=12.0), 7390.25),         # zone low - 3 ticks
        ("SHORT", dict(anchor_extreme=7389.0, zone_low=7387.0, zone_high=7389.0,
                       zone_range=2.0, advance=12.0), 7389.75)])       # zone high + 3 ticks
    def test_dynamic_structure_trail_floor(self, monkeypatch, direction, zone, new_stop):
        import backend.v9.services.trade_manager.consolidation as consolidation
        monkeypatch.setattr(consolidation, "detect_consolidation", lambda **kw: dict(zone))
        monkeypatch.setattr(consolidation, "next_target_from_levels", lambda **kw: None)
        fake_app = types.ModuleType("backend.v9.app")            # keep the key-level lookup light
        fake_app.app = types.SimpleNamespace(state=types.SimpleNamespace())
        monkeypatch.setitem(sys.modules, "backend.v9.app", fake_app)
        fake_kl = types.ModuleType("backend.v9.api.v9.key_levels_routes")
        fake_kl._load_sierra_tpo = lambda: {}
        monkeypatch.setitem(sys.modules, "backend.v9.api.v9.key_levels_routes", fake_kl)
        c = RISK10[direction]

        def run(marked):
            tm, t = _runner_tm(), _runner(direction, c["held"], marked, case=c)
            tm.apply_dynamic_struct_trail(t, c["entry"] + 5, c["entry"] + 1, c["entry"] + 3)
            return t, tm
        t, tm = run(True)                                # flag OFF -> BE+-1T floor
        assert t.stop == c["floor"]
        _on(monkeypatch)
        t, tm = run(False)                               # flag ON, no hold -> BE+-1T floor
        assert t.stop == c["floor"]
        t, tm = run(True)                                # flag ON + hold -> the zone stop
        assert t.stop == new_stop and tm._emits == [(4242, new_stop)]
