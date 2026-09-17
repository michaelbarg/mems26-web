# -*- coding: utf-8 -*-
"""F17b · T-412 — evidence for the existing REACTIVE/INITIATIVE producers.

Authority: docs/spec_authority/SETUP_GRAMMAR_2026-09-17.md (location · context ·
sequence · trigger · volume).  Order: docs/handoff/cc_orders/CC_NOW_2026-09-17_FIXES.md
§"⚠️ תיקון-כיוון ל-F17" + §F17b.

Three things are pinned here:
  1. every evidence function on synthetic bars (including the two definitions
     the order CORRECTED: direction-aware location, and absorption);
  2. the golden 17.09 cells the order names (real bars from
     v9_bars_5min_woodies, pasted below);
  3. S2_TRIGGER_QUALITY_V1='shadow' (the code default) ⇒ _detect_reactive
     returns EXACTLY what it returns today, plus info["evidence"].
"""
import os

import pytest

from backend.v9.systems.five_min import evidence as ev
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


# ── 1. trigger_quality ──────────────────────────────────────────────────────
def test_trigger_quality_long_close_in_top_30pct():
    bar = {"o": 100.0, "h": 110.0, "l": 100.0, "c": 108.0, "v": 10}
    q = ev.trigger_quality(bar, "LONG", atr=5.0)
    assert q["cp"] == 0.8 and q["ok"] is True
    assert q["body_ratio"] == 0.8
    assert q["range_atr"] == 2.0


def test_trigger_quality_long_mid_close_fails():
    bar = {"o": 100.0, "h": 110.0, "l": 100.0, "c": 105.0, "v": 10}
    assert ev.trigger_quality(bar, "LONG")["ok"] is False


def test_trigger_quality_short_close_in_bottom_30pct():
    bar = {"o": 110.0, "h": 110.0, "l": 100.0, "c": 102.0, "v": 10}
    q = ev.trigger_quality(bar, "SHORT")
    assert q["cp"] == 0.2 and q["ok"] is True
    # the same bar is NOT a long trigger
    assert ev.trigger_quality(bar, "LONG")["ok"] is False


def test_trigger_quality_zero_range_is_none_not_half():
    """Rule 1: a flat bar has no close position — None, never a synthetic 0.5."""
    q = ev.trigger_quality({"o": 100, "h": 100, "l": 100, "c": 100}, "LONG")
    assert q["cp"] is None and q["ok"] is None


def test_trigger_quality_accepts_long_key_names():
    bar = {"open": 100.0, "high": 110.0, "low": 100.0, "close": 108.0}
    assert ev.trigger_quality(bar, "LONG")["ok"] is True


# ── 2. delta_with ───────────────────────────────────────────────────────────
def test_delta_with_signed_and_sized():
    assert ev.delta_with(+900, 800, "LONG") is True
    assert ev.delta_with(+700, 800, "LONG") is False
    assert ev.delta_with(-900, 800, "SHORT") is True
    assert ev.delta_with(+900, 800, "SHORT") is False     # right size, wrong sign


def test_delta_with_missing_inputs_return_none():
    assert ev.delta_with(None, 800, "LONG") is None
    assert ev.delta_with(900, None, "LONG") is None
    assert ev.delta_with(900, 0, "LONG") is None          # zero yardstick ≠ "heavy"


def test_median_abs_delta_needs_enough_samples():
    assert ev.median_abs_delta([100, -200, 300]) is None  # < min_n
    assert ev.median_abs_delta([100, -200, 300, -400, 500]) == 300


# ── 3. vol_trigger ──────────────────────────────────────────────────────────
def test_vol_trigger_threshold():
    assert ev.vol_trigger(1300, 1000) is True
    assert ev.vol_trigger(1299, 1000) is False
    assert ev.vol_trigger(None, 1000) is None
    assert ev.vol_trigger(1300, None) is None


def test_median_volume():
    assert ev.median_volume([{"v": 10}, {"v": 20}, {"v": 30}]) == 20
    assert ev.median_volume([]) is None


# ── 4. location (the CORRECTED, direction-aware definition) ─────────────────
_DEV = {"vah": 7700.0, "val": 7680.0, "poc": 7690.0}
_PREV = {"vah": 7675.0, "val": 7650.0, "poc": 7660.0}
_IB = {"high": 7698.0, "low": 7682.0}


def test_location_long_at_lower_edge():
    loc = ev.location(7681.0, _DEV, _PREV, _IB, atr=6.0)
    assert loc["zone"] == "IN_VA"
    assert loc["at_edge_for"]["LONG"] is True
    assert loc["at_edge_for"]["SHORT"] is False


def test_location_short_at_upper_edge():
    loc = ev.location(7699.0, _DEV, _PREV, _IB, atr=6.0)
    assert loc["at_edge_for"]["SHORT"] is True
    assert loc["at_edge_for"]["LONG"] is False


def test_location_below_value_is_not_at_edge_for_long():
    """THE F17b FIX. The old study called any BELOW_VA long 'loc_edge'; a long
    25 points under VAL is beyond value, not at its edge."""
    loc = ev.location(7651.0, _DEV, _PREV, _IB, atr=6.0)
    assert loc["zone"] == "BELOW_VA"
    # far from dev VAL / IB low — but sitting on yesterday's VAL 7650
    assert loc["at_edge_for"]["LONG"] is True     # at YESTERDAY's edge, honestly
    loc_far = ev.location(7667.5, _DEV, _PREV, _IB, atr=6.0)
    assert loc_far["zone"] == "BELOW_VA"
    assert loc_far["at_edge_for"]["LONG"] is False, (
        "below value but far from every level must NOT count as 'at edge'")


def test_location_without_atr_makes_no_near_claim():
    loc = ev.location(7681.0, _DEV, _PREV, _IB, atr=None)
    assert loc["zone"] == "IN_VA"
    assert loc["at_edge_for"]["LONG"] is None and loc["near_prev_edge"] is None


def test_location_no_price_is_unknown():
    assert ev.location(None, _DEV, _PREV, _IB, atr=6.0)["zone"] == "UNKNOWN"


# ── 5. absorption (the CORRECTED definition — the old one scored N=0/164) ───
def _pair(d1, d2, l1=100.0, l2=99.0):
    return [{"o": 102, "h": 103, "l": l1, "c": 100.5, "delta": d1},
            {"o": 100.5, "h": 101, "l": l2, "c": 100.0, "delta": d2}]


def test_absorption_one_heavy_counter_bar_and_no_progress():
    """LONG: heavy SELLING into the low that goes nowhere = buyers absorbing."""
    assert ev.absorption(_pair(-3000, -200), "LONG", 800, 6.0) is True
    assert ev.absorption(_pair(-200, -3000), "LONG", 800, 6.0) is True


def test_absorption_requires_the_heavy_bar_to_be_against_the_trade():
    assert ev.absorption(_pair(+3000, +200), "LONG", 800, 6.0) is False
    assert ev.absorption(_pair(+3000, +200), "SHORT", 800, 6.0) is True


def test_absorption_fails_when_price_actually_progressed():
    """Heavy selling that DOES push price 10 pts (> 1×ATR) is not absorption."""
    assert ev.absorption(_pair(-3000, -200, l1=100.0, l2=89.0),
                         "LONG", 800, 6.0) is False


def test_absorption_no_heavy_bar():
    assert ev.absorption(_pair(-100, -200), "LONG", 800, 6.0) is False


def test_absorption_missing_inputs_return_none():
    assert ev.absorption(_pair(-3000, -200), "LONG", None, 6.0) is None
    assert ev.absorption(_pair(-3000, -200), "LONG", 800, None) is None
    assert ev.absorption([], "LONG", 800, 6.0) is None


# ── 6. shapes ───────────────────────────────────────────────────────────────
def _flat(n, price=100.0):
    return [{"o": price, "h": price + 1, "l": price - 1, "c": price} for _ in range(n)]


def test_double_bottom_needs_the_neckline_break():
    win = (_flat(1, 106) + [{"o": 106, "h": 107, "l": 100.0, "c": 105}]
           + _flat(3, 106) + [{"o": 106, "h": 107, "l": 100.1, "c": 105}]
           + _flat(1, 106) + [{"o": 105, "h": 109, "l": 104, "c": 108.5}])
    assert ev.double_bottom(win, atr=6.0) is True
    no_break = win[:-1] + [{"o": 105, "h": 107, "l": 104, "c": 106.5}]
    assert ev.double_bottom(no_break, atr=6.0) is False


def test_double_top_mirror():
    win = (_flat(1, 94) + [{"o": 94, "h": 100.0, "l": 93, "c": 95}]
           + _flat(3, 94) + [{"o": 94, "h": 99.9, "l": 93, "c": 95}]
           + _flat(1, 94) + [{"o": 94, "h": 94, "l": 90, "c": 90.5}])
    assert ev.double_top(win, atr=6.0) is True
    no_break = win[:-1] + [{"o": 94, "h": 95, "l": 93.5, "c": 94.5}]
    assert ev.double_top(no_break, atr=6.0) is False


def test_shape_detectors_match_the_oracle_engine_copies():
    """The producers and the nightly scan MUST run the same detector code.
    This compares evidence.py against scripts/oracle_engine.py bar-for-bar."""
    import sys
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))), "scripts"))
    import oracle_engine as oe

    import random
    rnd = random.Random(412)
    bars = []
    p = 100.0
    for _ in range(60):
        o = p
        c = o + rnd.uniform(-4, 4)
        bars.append({"o": o, "h": max(o, c) + rnd.uniform(0, 2),
                     "l": min(o, c) - rnd.uniform(0, 2), "c": c, "v": 1000})
        p = c
    for i in range(20, 60):
        assert (ev.detect_head_shoulders_short(bars, i, 5.0)
                == oe.detect_head_shoulders_short(bars, i, 5.0)), f"H&S short i={i}"
        assert (ev.detect_head_shoulders_long(bars, i, 5.0)
                == oe.detect_head_shoulders_long(bars, i, 5.0)), f"H&S long i={i}"
        assert (ev.detect_cup_handle_long(bars, i, 5.0)
                == oe.detect_cup_handle_long(bars, i, 5.0)), f"cup i={i}"


# ── 7. golden 17.09 (real bars, v9_bars_5min_woodies) ───────────────────────
# psql postgresql://localhost/mems26 — see LIVE_CHANNEL 17.09 for the raw output.
G = {
    "16:30": {"o": 7713.5, "h": 7716.25, "l": 7695.75, "c": 7695.75, "v": 30194, "delta": -1348},
    "16:35": {"o": 7695.75, "h": 7697.75, "l": 7691.75, "c": 7692.75, "v": 19560, "delta": 200},
    "16:40": {"o": 7693.0, "h": 7694.25, "l": 7688.25, "c": 7690.75, "v": 21100, "delta": 144},
    "16:45": {"o": 7690.75, "h": 7696.0, "l": 7688.25, "c": 7694.75, "v": 21102, "delta": 834},
    "16:50": {"o": 7695.0, "h": 7697.25, "l": 7691.0, "c": 7691.0, "v": 17806, "delta": 12},
    "16:55": {"o": 7691.0, "h": 7693.75, "l": 7688.25, "c": 7693.5, "v": 12797, "delta": -333},
    "17:00": {"o": 7693.75, "h": 7693.75, "l": 7683.75, "c": 7687.0, "v": 18723, "delta": -2855},
    "17:05": {"o": 7687.0, "h": 7687.5, "l": 7680.5, "c": 7683.0, "v": 14858, "delta": -1372},
    "17:10": {"o": 7683.25, "h": 7692.75, "l": 7681.75, "c": 7692.25, "v": 17129, "delta": 3319},
}
_SEQ = [G[k] for k in ("16:30", "16:35", "16:40", "16:45", "16:50", "16:55", "17:00", "17:05", "17:10")]
# median |delta| of the session before the 17:10 trigger
_MED = ev.median_abs_delta([b["delta"] for b in _SEQ[:-1]])


def test_golden_med_abs_delta():
    assert _MED == 583.5


def test_golden_initiative_short_1710_trigger_is_not_ok():
    """The live INITIATIVE_SHORT @7683 (17:10:04, −$102.50) fired on the CLOSE
    of the 17:05 bar, which closed at 36% of its range — not in the extreme
    30%. Under S2_TRIGGER_QUALITY_V1=1 it would have been recorded as blocked."""
    q = ev.trigger_quality(G["17:05"], "SHORT")
    assert round(q["cp"], 3) == 0.357
    assert q["ok"] is False


def test_golden_long_1710_trigger_is_ok_with_delta():
    """The other side of the same moment: the 17:10 bar (the reversal trigger
    of Michael's double-bottom example) closes at the top of its range with the
    session's largest positive delta."""
    q = ev.trigger_quality(G["17:10"], "LONG")
    assert q["cp"] >= 0.7 and q["ok"] is True
    assert ev.delta_with(G["17:10"]["delta"], _MED, "LONG") is True


def test_golden_absorption_1700_1705():
    """The order's example, called exactly as the order writes it:
    absorption(bars[-3:-1], ...) — the 17:00/17:05 push pair, δ −2,855/−1,372,
    price only 3.25 pts below the 17:00 low ⇒ True."""
    assert ev.absorption(_SEQ[-3:-1], "LONG", _MED, 6.93) is True


def test_golden_absorption_with_the_stricter_three_bar_reference():
    """Honest number, not a rounded claim: measured from the 16:55 low the
    counter-progress is 7.75 pts. Against the RTH-only ATR (6.93, opening bar
    excluded) that is MORE than 1×ATR ⇒ False; against the ATR that includes
    the 20.5-pt opening bar (8.63) ⇒ True. The pair-reference default above is
    what the order specifies."""
    assert ev.absorption(_SEQ[-4:-1], "LONG", _MED, 6.93) is False
    assert ev.absorption(_SEQ[-4:-1], "LONG", _MED, 8.63) is True


def test_golden_location_long_at_yesterdays_vah():
    """SETUP_GRAMMAR §2: the sequence low 7680.5 sits on yesterday's VAH
    7680.75 / today's VAL 7687.5 — a LONG at its edge, not a SHORT one."""
    loc = ev.location(7680.5, {"vah": 7704.0, "val": 7687.5, "poc": 7693.0},
                      {"vah": 7680.75, "val": 7650.0}, {"high": 7716.25, "low": 7680.5},
                      atr=6.93)
    assert loc["at_edge_for"]["LONG"] is True
    assert loc["at_edge_for"]["SHORT"] is False
    assert loc["near_prev_edge"] is True


# ── 8. the producer: shadow = zero behaviour change ─────────────────────────
def _reactive_long_bars(weak_trigger=False):
    """3 quiet lookback bars + a valid Reactive-LONG 4-bar setup (7 total).
    Same fixture as test_s2_independent_of_s3.py."""
    pad = [{"o": 5250, "h": 5251, "l": 5249, "c": 5250, "v": 50} for _ in range(3)]
    b4 = ({"o": 5248.5, "h": 5254, "l": 5248.5, "c": 5249.75, "v": 700}  # cp 0.23
          if weak_trigger else
          {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700})  # cp 0.83
    setup = [
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},
        b4,
    ]
    return pad + setup


def _sys_no_footprint():
    s = FiveMinSystem()
    s._get_cot_from_footprint = lambda: None
    s._get_amt_from_footprint = lambda: None
    s._get_belly_from_footprint = lambda: None
    s._get_belly_ratio_from_footprint = lambda d: None
    s._poc_vol_rising = lambda b: False
    s._poc_vol_falling = lambda b: False
    s._compute_setup_cvd = lambda bars, window=4: None   # no CVD in the fixture
    s._current_atr_5m = 3.0
    return s


@pytest.fixture(autouse=True)
def _no_sierra(monkeypatch):
    """Levels come from the Sierra export in production; pin them here so the
    tests do not depend on whatever file is on disk."""
    monkeypatch.setattr(
        "backend.v9.systems.five_min.five_min_system._load_sierra_tpo",
        lambda: {"vah": 5252.0, "val": 5246.0, "poc": 5249.0,
                 "ib_high": 5251.0, "ib_low": 5247.0,
                 "previous_session": {"vah": 5253.0, "val": 5244.0}},
        raising=False)


def test_code_default_is_shadow(monkeypatch):
    monkeypatch.delenv("S2_TRIGGER_QUALITY_V1", raising=False)
    assert FiveMinSystem._s2_tq_mode() == "shadow"


def test_shadow_fires_exactly_as_today_and_attaches_evidence(monkeypatch):
    """The whole point of the flag's default: identical direction/confidence/
    info to today, with evidence added for measurement."""
    monkeypatch.delenv("S2_TRIGGER_QUALITY_V1", raising=False)
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    d, conf, info = _sys_no_footprint()._detect_reactive(_reactive_long_bars())
    assert d == "LONG" and conf == 0.75
    assert info["kind"] == "REACTIVE" and info["structural_anchor"] == 5247
    assert "evidence" in info
    assert info["evidence"]["trigger"]["ok"] is True
    assert info["evidence"]["mode"] == "shadow"


def test_shadow_does_not_block_a_weak_trigger(monkeypatch):
    """A weak trigger in shadow still fires — zero behaviour change."""
    monkeypatch.setenv("S2_TRIGGER_QUALITY_V1", "shadow")
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    d, _, info = _sys_no_footprint()._detect_reactive(_reactive_long_bars(weak_trigger=True))
    assert d == "LONG"
    assert info["evidence"]["trigger"]["ok"] is False


def test_flag_on_blocks_the_weak_trigger(monkeypatch):
    """S2_TRIGGER_QUALITY_V1=1 (NOT enabled anywhere — replay decides, then
    Michael rules) gates the same fire."""
    monkeypatch.setenv("S2_TRIGGER_QUALITY_V1", "1")
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    d, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(weak_trigger=True))
    assert d is None
    d2, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars())
    assert d2 == "LONG", "a strong trigger still fires with the gate on"


def test_flag_off_skips_evidence_entirely(monkeypatch):
    """'0' = the pre-F17b path, byte-identical info (no evidence key, no DB read)."""
    monkeypatch.setenv("S2_TRIGGER_QUALITY_V1", "0")
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    d, _, info = _sys_no_footprint()._detect_reactive(_reactive_long_bars())
    assert d == "LONG" and info["evidence"] == {}


def test_evidence_failure_never_breaks_the_fire(monkeypatch):
    monkeypatch.delenv("S2_TRIGGER_QUALITY_V1", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    s = _sys_no_footprint()

    def _boom(*a, **k):
        raise RuntimeError("CVD exploded")
    s._compute_setup_cvd = _boom
    d, _, info = s._detect_reactive(_reactive_long_bars())
    assert d == "LONG" and info["evidence"] == {}
