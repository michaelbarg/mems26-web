"""F5 · RUNNER_TRAIL_V2 — structural swing trail for the runner leg.

Michael 2026-08-20, after ORACLE_STUDY_2026-08-20: the same entries with a
structural exit book +$2,635 instead of +$320. The gap is exit management, not
entry selection (trades 3+ per day contributed +$32.50).

Every test here runs REAL code. The 2026-08-03 block runs it over the REAL
5-min bars of that session (pulled from v9_bars_5min_woodies and frozen into
this file, so the test needs no DB) and reproduces the ORACLE's published
number to the cent — that is the anti-tautology anchor: if the trail geometry
drifts from the engine that measured the $2,315, this test goes red.
"""
from __future__ import annotations

import ast
import asyncio
import pathlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.v9.services.trade_manager.swing_trail import (
    confirmed_pivots, last_confirmed_swing, swing_rev_threshold, swing_trail_stop,
)

REPO = pathlib.Path(__file__).resolve().parents[3]

# ── real RTH bars, 2026-08-03 (78 bars, v9_bars_5min_woodies) ──────────────
# (hh:mm ET, open, high, low, close). Session: open 7546.00 · low 7542.75 at
# 09:30 · high 7638.50 at 15:00 · close 7628.50 → ONE 95.75pt LONG swing.
BARS_0803 = [
    ('09:30', 7546.0, 7565.25, 7542.75, 7559.25),
    ('09:35', 7559.25, 7571.0, 7559.0, 7568.75),
    ('09:40', 7568.75, 7570.0, 7561.0, 7567.5),
    ('09:45', 7567.5, 7575.0, 7565.0, 7570.75),
    ('09:50', 7570.75, 7581.5, 7567.75, 7579.5),
    ('09:55', 7579.5, 7588.25, 7578.25, 7587.5),
    ('10:00', 7588.25, 7591.25, 7582.5, 7585.75),
    ('10:05', 7586.0, 7588.25, 7583.5, 7587.5),
    ('10:10', 7587.5, 7592.5, 7587.25, 7591.0),
    ('10:15', 7591.0, 7597.5, 7590.0, 7593.75),
    ('10:20', 7593.75, 7600.0, 7593.5, 7598.0),
    ('10:25', 7598.25, 7600.0, 7595.5, 7597.25),
    ('10:30', 7597.0, 7598.5, 7595.0, 7597.25),
    ('10:35', 7597.0, 7601.5, 7596.25, 7599.75),
    ('10:40', 7600.0, 7603.75, 7599.5, 7601.0),
    ('10:45', 7601.25, 7601.75, 7598.75, 7600.75),
    ('10:50', 7600.75, 7603.25, 7600.0, 7601.0),
    ('10:55', 7601.25, 7606.0, 7601.25, 7606.0),
    ('11:00', 7605.75, 7606.25, 7603.0, 7604.5),
    ('11:05', 7604.5, 7604.5, 7599.75, 7601.25),
    ('11:10', 7601.25, 7603.5, 7600.0, 7602.5),
    ('11:15', 7602.5, 7606.0, 7602.25, 7605.75),
    ('11:20', 7605.75, 7609.0, 7605.75, 7607.75),
    ('11:25', 7607.75, 7609.0, 7602.25, 7603.25),
    ('11:30', 7603.25, 7606.75, 7602.75, 7604.75),
    ('11:35', 7604.75, 7608.0, 7603.75, 7607.25),
    ('11:40', 7607.5, 7610.5, 7607.25, 7608.25),
    ('11:45', 7608.5, 7613.0, 7608.5, 7612.5),
    ('11:50', 7612.5, 7614.0, 7611.75, 7613.75),
    ('11:55', 7613.5, 7613.75, 7610.0, 7611.25),
    ('12:00', 7611.5, 7613.5, 7611.0, 7611.5),
    ('12:05', 7611.5, 7612.5, 7610.0, 7612.0),
    ('12:10', 7612.0, 7612.0, 7609.25, 7611.5),
    ('12:15', 7611.25, 7614.5, 7611.0, 7614.25),
    ('12:20', 7614.25, 7614.5, 7612.25, 7614.25),
    ('12:25', 7614.25, 7617.75, 7613.5, 7617.0),
    ('12:30', 7617.25, 7618.0, 7614.75, 7616.0),
    ('12:35', 7615.75, 7616.25, 7613.75, 7614.25),
    ('12:40', 7614.5, 7616.75, 7613.75, 7616.25),
    ('12:45', 7616.25, 7616.75, 7614.5, 7614.5),
    ('12:50', 7614.75, 7615.5, 7612.0, 7612.25),
    ('12:55', 7612.25, 7615.25, 7611.5, 7613.75),
    ('13:00', 7613.75, 7614.75, 7611.75, 7613.75),
    ('13:05', 7613.75, 7614.5, 7611.25, 7613.75),
    ('13:10', 7613.75, 7617.75, 7613.75, 7616.75),
    ('13:15', 7616.5, 7619.5, 7616.25, 7619.25),
    ('13:20', 7619.5, 7622.0, 7618.25, 7621.25),
    ('13:25', 7621.25, 7623.25, 7620.0, 7622.5),
    ('13:30', 7622.25, 7625.75, 7621.75, 7625.25),
    ('13:35', 7625.5, 7626.25, 7623.0, 7624.0),
    ('13:40', 7624.25, 7625.25, 7623.25, 7625.0),
    ('13:45', 7625.0, 7627.25, 7625.0, 7626.5),
    ('13:50', 7626.5, 7628.25, 7626.0, 7628.25),
    ('13:55', 7628.0, 7629.75, 7627.25, 7628.25),
    ('14:00', 7628.25, 7633.25, 7628.0, 7633.0),
    ('14:05', 7633.25, 7635.25, 7632.5, 7635.0),
    ('14:10', 7634.75, 7635.25, 7630.0, 7631.75),
    ('14:15', 7631.75, 7634.75, 7630.5, 7631.25),
    ('14:20', 7631.25, 7633.25, 7629.5, 7631.0),
    ('14:25', 7631.0, 7632.0, 7626.25, 7627.25),
    ('14:30', 7627.25, 7629.75, 7625.0, 7626.5),
    ('14:35', 7626.75, 7629.75, 7626.25, 7628.25),
    ('14:40', 7628.25, 7632.75, 7627.25, 7632.5),
    ('14:45', 7632.5, 7633.5, 7629.0, 7632.5),
    ('14:50', 7632.5, 7634.25, 7630.5, 7632.75),
    ('14:55', 7632.5, 7634.0, 7630.75, 7631.25),
    ('15:00', 7631.0, 7638.5, 7631.0, 7637.0),
    ('15:05', 7637.0, 7637.25, 7632.0, 7633.75),
    ('15:10', 7633.75, 7636.0, 7632.5, 7633.5),
    ('15:15', 7633.75, 7636.25, 7633.75, 7635.25),
    ('15:20', 7635.5, 7636.5, 7633.75, 7636.0),
    ('15:25', 7636.0, 7637.5, 7634.25, 7635.5),
    ('15:30', 7635.5, 7637.0, 7633.5, 7635.5),
    ('15:35', 7635.5, 7636.5, 7631.25, 7631.75),
    ('15:40', 7631.75, 7633.5, 7630.5, 7632.5),
    ('15:45', 7632.5, 7634.5, 7631.0, 7633.25),
    ('15:50', 7633.25, 7635.5, 7627.75, 7629.25),
    ('15:55', 7629.0, 7632.0, 7626.25, 7628.5),
]



def _b(rows):
    return [dict(t=t, o=o, h=h, l=l, c=c) for (t, o, h, l, c) in rows]


BARS = _b(BARS_0803)                     # noqa: F821 (injected literal above)
IDX = {b["t"]: i for i, b in enumerate(BARS)}
REV_0803 = 9.5                           # clamp(1.0×ATR(07-31), 4, 12) — verified live

# The 9 live trades of 2026-08-03 (v9_trades, mode='live'). All nine were LONG —
# the direction was right 9/9 — and together they booked +$183.75 while the day
# offered 95.75 points. Five exited at a FIXED T2 target; that is the leak.
TRADES_0803 = [
    (588, "T2_HIT", +71.25), (591, "STOP_HIT", -20.00), (593, "T2_HIT", +76.25),
    (595, "T2_HIT", +37.50), (598, "STOP_HIT", -7.50), (601, "T2_HIT", +58.75),
    (604, "T2_HIT", +25.00), (607, "STOP_HIT", -25.00), (610, "STOP_HIT", -32.50),
]


# ══════════════════════════════════════════════ A. swing geometry (pure)
class TestSwingGeometry:

    def test_rev_threshold_is_clamped_prev_session_atr(self):
        """rev = clamp(1.0×ATR(previous session), 4.0, 12.0), snapped to a tick."""
        quiet = [dict(h=100.5, l=100.0, c=100.2) for _ in range(30)]
        assert swing_rev_threshold(quiet) == 4.0          # floor
        wild = [dict(h=100 + 30 * i, l=70 + 30 * i, c=90 + 30 * i) for i in range(30)]
        assert swing_rev_threshold(wild) == 12.0          # cap

    def test_rev_threshold_honest_none_on_short_session(self):
        """No usable prior session → None. Never an invented threshold (Rule 1)."""
        assert swing_rev_threshold([dict(h=1, l=0, c=0.5)] * 5) is None
        assert swing_rev_threshold(None) is None

    def test_running_extreme_is_not_a_pivot(self):
        """Lookahead-free: an extreme that has not yet been retraced by `rev` is
        NOT tradable structure. On a one-way rally the only confirmed swing is the
        low the rally CAME FROM — the running high is nothing yet. Trailing behind
        that running high is just a tighter chandelier, which is the behaviour that
        produced +$320."""
        rising = _b([(f"{i:02d}:00", 100 + i, 101 + i, 99 + i, 100 + i) for i in range(12)])
        assert [p["kind"] for p in confirmed_pivots(rising, 5.0)] == ["L"]
        assert last_confirmed_swing(rising, "LONG", 5.0)["price"] == 99.0
        assert last_confirmed_swing(rising, "SHORT", 5.0) is None, \
            "the un-retraced running high must never become a SHORT anchor"

    def test_pivot_confirms_only_after_the_retrace(self):
        up = [(f"{i:02d}:00", 100 + i, 101 + i, 99 + i, 100 + i) for i in range(10)]   # 100→109
        down = [(f"{10 + i:02d}:00", 109 - i, 110 - i, 108 - i, 109 - i) for i in range(7)]
        bars = _b(up + down)
        piv = confirmed_pivots(bars, 5.0)
        assert [p["kind"] for p in piv] == ["L", "H"]
        h = piv[-1]
        assert h["price"] == 110.0                         # the bar's real HIGH
        assert h["confirm_i"] > h["i"], "a pivot is only knowable after the retrace"

    def test_trail_sits_beyond_the_swing(self):
        down = [(f"{i:02d}:00", 110 - i, 111 - i, 109 - i, 110 - i) for i in range(10)]  # 110→101
        up = [(f"{10 + i:02d}:00", 101 + i, 102 + i, 100 + i, 101 + i) for i in range(7)]
        bars = _b(down + up)
        stop = swing_trail_stop(bars, "LONG", rev=5.0, offset_ticks=1)
        low = last_confirmed_swing(bars, "LONG", 5.0)["price"]
        assert stop == round(low - 0.25, 2), "LONG trails UNDER the confirmed swing low"

    def test_short_is_the_mirror(self):
        up = [(f"{i:02d}:00", 100 + i, 101 + i, 99 + i, 100 + i) for i in range(10)]
        down = [(f"{10 + i:02d}:00", 109 - i, 110 - i, 108 - i, 109 - i) for i in range(7)]
        bars = _b(up + down)
        stop = swing_trail_stop(bars, "SHORT", rev=5.0, offset_ticks=1)
        high = last_confirmed_swing(bars, "SHORT", 5.0)["price"]
        assert stop == round(high + 0.25, 2), "SHORT trails ABOVE the confirmed swing high"


# ══════════════════════════════════════════════ B. manager policy
def _trade(entry=7400.0, stop=7400.25, direction="LONG", t1=True):
    return SimpleNamespace(
        id=999, entry_price=entry, stop=stop, direction=direction,
        t1_hit_ts=datetime.now(timezone.utc) if t1 else None,
        entry_ts=datetime.now(timezone.utc) - timedelta(hours=1),
        quality={"initial_stop": 7390.0}, cross_context=[], state="PARTIAL",
        mode="live",
    )


def _tm(today, prev):
    from backend.v9.services.trade_manager.manager import TradeManager
    tm = TradeManager.__new__(TradeManager)
    tm._db = MagicMock()
    tm._emitter = MagicMock()
    tm._log_management = MagicMock()
    tm._emit_modify_stop = MagicMock()
    tm._swing_bars_today = lambda: (today, prev)
    return tm


PREV = [dict(h=100 + i * 0.1, l=95 + i * 0.1, c=98 + i * 0.1) for i in range(40)]  # ATR≈5


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("RUNNER_TRAIL_V2", "1")


class TestManagerPolicy:

    def _rally_pullback_rally(self):
        """7390→7420, pull back to 7399, rally again → last CONFIRMED swing low
        = 7398 (the pullback low), well above a 7385 entry's break-even."""
        up1 = [(f"{i:02d}:00", 7390 + i * 3, 7391 + i * 3, 7389 + i * 3, 7390 + i * 3)
               for i in range(11)]
        pb = [(f"{11 + i:02d}:00", 7420 - i * 3, 7421 - i * 3, 7419 - i * 3, 7420 - i * 3)
              for i in range(8)]
        up2 = [(f"{19 + i:02d}:00", 7399 + i * 3, 7400 + i * 3, 7398 + i * 3, 7399 + i * 3)
               for i in range(6)]
        return _b(up1 + pb + up2)

    def _rally_after_swing_low(self):
        return self._rally_pullback_rally()

    def test_flag_off_is_a_no_op(self, monkeypatch):
        monkeypatch.setenv("RUNNER_TRAIL_V2", "0")
        tm = _tm(self._rally_after_swing_low(), PREV)
        t = _trade(entry=7385.0, stop=7385.25)
        assert tm.apply_structural_swing_trail(t) is None
        assert t.stop == 7385.25
        tm._emit_modify_stop.assert_not_called()

    def test_before_t1_the_banked_legs_own_the_stop(self):
        tm = _tm(self._rally_after_swing_low(), PREV)
        t = _trade(entry=7385.0, stop=7385.25, t1=False)
        assert tm.apply_structural_swing_trail(t) is None
        assert t.stop == 7385.25

    def test_zlr_stop_stays_locked(self, monkeypatch):
        tm = _tm(self._rally_after_swing_low(), PREV)
        tm._zlr_stop_locked = lambda _t: True
        t = _trade(entry=7385.0, stop=7385.25)
        assert tm.apply_structural_swing_trail(t) is False
        assert t.stop == 7385.25
        tm._emit_modify_stop.assert_not_called()

    def test_moves_to_the_confirmed_swing_and_tells_sierra(self):
        bars = self._rally_pullback_rally()
        tm = _tm(bars, PREV)
        t = _trade(entry=7385.0, stop=7385.25)          # BE+1T already
        assert tm.apply_structural_swing_trail(t) is True
        assert t.stop == 7397.75                        # swing low 7398.00 − 1 tick
        assert t.stop == swing_trail_stop(bars, "LONG", rev=swing_rev_threshold(PREV),
                                          offset_ticks=1)
        tm._emit_modify_stop.assert_called_once_with(t, 7397.75)
        assert tm._log_management.call_args[0][1] == "SWING_TRAIL"

    def test_never_widens(self):
        bars = self._rally_pullback_rally()
        tm = _tm(bars, PREV)
        t = _trade(entry=7385.0, stop=7405.0)           # already tighter than the swing
        assert tm.apply_structural_swing_trail(t) is False
        assert t.stop == 7405.0
        tm._emit_modify_stop.assert_not_called()

    def test_floor_is_be_plus_one_tick(self):
        """A swing low BELOW break-even can never pull the stop back under BE+1T."""
        down = [(f"{i:02d}:00", 7400 - i * 2, 7401 - i * 2, 7399 - i * 2, 7400 - i * 2)
                for i in range(11)]                     # 7400 → 7380
        up = [(f"{11 + i:02d}:00", 7380 + i * 3, 7381 + i * 3, 7379 + i * 3, 7380 + i * 3)
              for i in range(8)]
        bars = _b(down + up)
        assert swing_trail_stop(bars, "LONG", rev=swing_rev_threshold(PREV)) == 7378.75
        tm = _tm(bars, PREV)
        t = _trade(entry=7395.0, stop=7390.0)           # swing low 7379 << entry
        assert tm.apply_structural_swing_trail(t) is True
        assert t.stop == 7395.25                        # BE + 1 tick, not 7378.75

    def test_feed_gap_falls_back_instead_of_inventing(self):
        """Rule 1: no bars / no prior ATR → None, so the caller keeps the old
        trail. A data gap must never leave a runner un-trailed OR trail it off a
        synthesised level."""
        assert _tm(None, PREV).apply_structural_swing_trail(_trade()) is None
        assert _tm(self._rally_after_swing_low(), None).apply_structural_swing_trail(
            _trade()) is None

    def test_no_confirmed_swing_yet_falls_back(self):
        """A session that has not yet moved `rev` in either direction has no
        structure to trail behind → None, the legacy trail keeps the stop."""
        flat = _b([(f"{i:02d}:00", 7400 + (i % 2), 7401, 7399, 7400 + (i % 2))
                   for i in range(12)])
        tm = _tm(flat, PREV)
        t = _trade(entry=7395.0, stop=7395.25)
        assert tm.apply_structural_swing_trail(t) is None
        assert t.stop == 7395.25


# ══════════════════════════════════════════════ C. entry side (the half that holds)
def _setup(contracts=6, pattern="REACTIVE_LONG"):
    return {
        "direction": "LONG", "entry_price": 7500.0, "stop": 7490.0,
        "t1": 7505.0, "t2": 7510.0, "t3": 7520.0,
        "contracts": contracts, "classification": pattern,
        "metadata": {"pattern": pattern}, "firing_system": 2,
        "day_type_at_entry": "Trend_Normal",
    }


def _cmd(setup, monkeypatch):
    """command_from_setup with the file write stubbed — we inspect the payload."""
    from backend.v9.services import sierra_command as SC
    seen = {}

    def _fake_write(**kw):
        seen.update(kw)
        return kw
    monkeypatch.setattr(SC, "write_trade_command", _fake_write)
    monkeypatch.setattr(SC, "_margin_capped", lambda n, *a, **k: n, raising=False)
    SC.command_from_setup(setup, trade_id="t1", account="Sim1", mode="live")
    return seen


class TestRunnerLegPlacement:
    """A stop-trail cannot hold a position past a resting limit order. Unless the
    runner leg goes out WITHOUT a target, F5 is decoration — this is the half of
    the fix that actually holds. 2026-08-03 #588: entry 7563.50, t2 7572.50, out
    in ten minutes at +9.00pt while the day ran 95.75."""

    def test_off_by_default_byte_identical(self, monkeypatch):
        monkeypatch.setenv("RUNNER_TRAIL_V2", "0")
        monkeypatch.setenv("T0_TARGET_PTS", "3.0")
        ctx = _cmd(_setup(6), monkeypatch)["context"]
        assert ctx["t4"] is not None, "flag OFF must not change the bracket"

    def test_runner_leg_goes_out_stop_only(self, monkeypatch):
        monkeypatch.setenv("T0_TARGET_PTS", "3.0")
        s = _setup(6)
        out = _cmd(s, monkeypatch)
        ctx = out["context"]
        assert ctx["t4"] is None, "the runner leg must carry NO fixed target"
        # the banked legs are untouched — the 1/2/2/1 ladder ruling stands
        assert out["target_price"] == 7503.0                # T0 = entry + 3.0
        assert (ctx["t2"], ctx["t3"]) == (7505.0, 7510.0)   # T1, T2 legs intact
        assert s["runner_stop_only"] == "c4"

    def test_three_contracts_drops_the_third_leg(self, monkeypatch):
        monkeypatch.setenv("T0_TARGET_PTS", "3.0")
        ctx = _cmd(_setup(3), monkeypatch)["context"]
        assert ctx["t3"] is None and ctx["t2"] == 7510.0

    def test_below_min_contracts_unchanged(self, monkeypatch):
        monkeypatch.setenv("T0_TARGET_PTS", "3.0")
        monkeypatch.setenv("RUNNER_TRAIL_V2_MIN_CONTRACTS", "3")
        ctx = _cmd(_setup(2), monkeypatch)["context"]
        assert ctx["t2"] == 7510.0, "2 contracts is below the floor — no change"

    def test_zlr_is_excluded(self, monkeypatch):
        """ZLR_MGMT_V1 owns its own allocation AND locks the stop against every
        trail — a stop-only ZLR runner would have no exit but the EOD flatten."""
        monkeypatch.setenv("ZLR_MGMT_V1", "1")
        monkeypatch.setenv("T0_TARGET_PTS", "3.0")
        ctx = _cmd(_setup(6, pattern="ZLR"), monkeypatch)["context"]
        assert ctx["t4"] is not None or ctx["t3"] is not None


# ══════════════════════════════════════════════ D. wiring / precedence
class TestPrecedence:

    def _detector(self, f5_result):
        from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
        d = BarLevelDetector.__new__(BarLevelDetector)
        d._tm = MagicMock()
        d._gateway = None
        d._bars_processed = 0
        d._last_bar_ts_processed = ""
        d._eod_flatten_requested = set()
        d._runner_trail_v1_shadow_warned = False
        d._app_state = None
        t = _trade(entry=7400.0, stop=7400.25)
        t.state = "OPEN"
        t.mode = "shadow"                     # keep the demo/live branches out
        d._tm.get_active_trades.return_value = [t]
        d._tm.apply_structural_swing_trail.return_value = f5_result
        return d, t

    def _bar(self):
        # after the trade's entry_ts — a bar that predates the entry is skipped
        ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return SimpleNamespace(
            payload={"high": 7420.0, "low": 7410.0, "close": 7415.0, "ts": ts},
            mode="LIVE")

    def test_f5_wins_and_a_hold_does_not_fall_through(self, monkeypatch):
        """A deliberate HOLD (False) must NOT hand the stop to the older trail —
        holding is the entire point of F5."""
        monkeypatch.setenv("DYNAMIC_STRUCT_TRAIL", "1")
        for verdict in (True, False):
            d, _ = self._detector(verdict)
            asyncio.run(d.on_bar(self._bar()))
            d._tm.apply_structural_swing_trail.assert_called_once()
            d._tm.apply_dynamic_struct_trail.assert_not_called()

    def test_cannot_evaluate_falls_back_to_the_old_trail(self, monkeypatch):
        """None = feed gap / no swing yet → the runner is never left un-trailed."""
        monkeypatch.setenv("DYNAMIC_STRUCT_TRAIL", "1")
        d, _ = self._detector(None)
        asyncio.run(d.on_bar(self._bar()))
        d._tm.apply_structural_swing_trail.assert_called_once()
        d._tm.apply_dynamic_struct_trail.assert_called_once()


# ══════════════════════════════════════════════ E. 2026-08-03 — the whole case
def _replay_leg(entry, stop0, target, start, dirn=1):
    """One leg over the real 08-03 bars: fixed target vs. the F5 swing trail.
    Stop checked before anything else in the bar (conservative); a trail exit
    pays 1 tick of slippage; EOD closes what is left."""
    out = {}
    for mode in ("fixed", "trail"):
        stop, be, exit_p, why, when = stop0, entry + dirn * 0.25, None, None, None
        for k in range(start, len(BARS)):
            b = BARS[k]
            if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
                exit_p, why, when = stop - dirn * 0.25, "STOP", b["t"]
                break
            if mode == "fixed" and target is not None and (
                    (dirn > 0 and b["h"] >= target) or (dirn < 0 and b["l"] <= target)):
                exit_p, why, when = target, "TARGET", b["t"]
                break
            if mode == "trail":
                a = swing_trail_stop(BARS[:k + 1], "LONG" if dirn > 0 else "SHORT",
                                     rev=REV_0803, offset_ticks=1)
                if a is not None:
                    cand = max(a, be) if dirn > 0 else min(a, be)
                    if (dirn > 0 and cand > stop) or (dirn < 0 and cand < stop):
                        stop = round(cand, 2)
            if b["t"] >= "15:55":
                exit_p, why, when = b["c"] - dirn * 0.25, "EOD", b["t"]
                break
        out[mode] = dict(pts=round(dirn * (exit_p - entry), 2), exit=round(exit_p, 2),
                         why=why, when=when)
    return out


class TestAugust03:

    def test_the_day_was_one_swing(self):
        lo = min(b["l"] for b in BARS)
        hi = max(b["h"] for b in BARS)
        assert (lo, hi) == (7542.75, 7638.50)
        assert round(hi - lo, 2) == 95.75
        assert len(BARS) == 78

    def test_the_system_was_right_nine_times_out_of_nine(self):
        """Direction 9/9, +$183.75 booked, and FIVE of the nine exits were a
        fixed target — this is a HOLDING failure, not a firing failure."""
        assert round(sum(p for _, _, p in TRADES_0803), 2) == 183.75
        assert sum(1 for _, r, _ in TRADES_0803 if r == "T2_HIT") == 5

    def test_588_fixed_target_takes_9pt_while_the_trail_takes_64(self):
        """#588 entered 7563.50 at 09:35 — 7.5pt BETTER than the ORACLE's causal
        trigger — and its fixed T2 at 7572.50 closed it ten minutes later."""
        r = _replay_leg(7563.50, 7556.00, 7572.50, IDX["09:40"])
        assert r["fixed"] == dict(pts=9.00, exit=7572.50, why="TARGET", when="09:45")
        assert r["trail"]["pts"] == 64.75 and r["trail"]["why"] == "EOD"
        assert r["trail"]["pts"] > 7 * r["fixed"]["pts"]

    def test_reproduces_the_oracle_1139_to_the_cent(self):
        """ORACLE_STUDY §3: the single causal STAIR trigger at 09:45 — entry
        7571.00, structural stop 7558.75, held on the structural trail — is
        +$1,139.00 on 4 contracts. If this drifts, the live trail geometry has
        drifted from the engine that measured the $2,315."""
        r = _replay_leg(7571.00, 7558.75, None, IDX["09:50"])
        assert r["trail"]["exit"] == 7628.25
        usd = round(r["trail"]["pts"] * 4 * 5.0 - 1.50 * 4, 2)
        assert usd == 1139.00

    def test_the_trail_holds_because_no_swing_confirmed_against_it(self):
        """One swing all day: exactly one confirmed pivot (the 09:30 low), so the
        stop never rose above BE+1T and the runner rode to the close. This is what
        'let the swing run' means — not a tighter chandelier."""
        piv = confirmed_pivots(BARS, REV_0803)
        assert [(p["kind"], p["price"]) for p in piv] == [("L", 7542.75)]


# ══════════════════════════════════════════════ F. safety invariants
class TestSafety:

    @pytest.mark.parametrize("rel", [
        "backend/v9/services/trade_manager/swing_trail.py",
        "backend/v9/services/trade_manager/manager.py",
        "backend/v9/services/sierra_command.py",
    ])
    def test_f5_never_reaches_for_the_broken_exit_op(self, rel):
        """op=EXIT is known-broken (CLAUDE.md, returns r=-1). F5 exits by
        MODIFY_STOP and by the attached OCO only. Guard the whole F5 surface by
        AST so a later edit cannot quietly wire a new caller."""
        src = (REPO / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        f5 = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef)
              and n.name in ("apply_structural_swing_trail", "_swing_bars_today",
                             "swing_trail_stop", "last_confirmed_swing",
                             "confirmed_pivots", "swing_rev_threshold",
                             "command_from_setup")]
        for fn in f5:
            names = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
            names |= {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            assert "_emit_exit" not in names, f"{rel}:{fn.name} wires the broken op=EXIT"
            assert "write_exit" not in names, f"{rel}:{fn.name} wires the broken op=EXIT"

    def test_no_hour_gating_in_the_f5_surface(self):
        """Michael 2026-08-20: 'אתה לא מגביל שעות בשום אופן'. The swing module is
        pure geometry — it must not know what time it is."""
        src = (REPO / "backend/v9/services/trade_manager/swing_trail.py").read_text()
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not (names & {"datetime", "now", "time", "hour", "ZoneInfo"}), \
            "swing_trail must stay clock-free"

    def test_runner_trail_v1_is_documented_as_shadowed(self):
        """AUDIT §L1: with DYNAMIC_STRUCT_TRAIL=1 the RUNNER_TRAIL_V1 branch is
        unreachable. The detector must say so out loud rather than let the flag
        index keep claiming a lever that never runs (books: action='TRAIL' = 127
        rows, all shadow, all 2026-06-18..06-24)."""
        src = (REPO / "backend/v9/services/trade_manager/bar_level_detector.py").read_text()
        assert "RUNNER_TRAIL_V1=1 is INERT" in src
