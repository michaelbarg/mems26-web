"""CEILING_FLOOR_STATE_V1 — the double-ceiling / double-floor failure detector.

Michael 2026-08-28: "ברגע שנוצרה תקרה כפולה שלא הצליחה להתקדם, אני רוצה
שהמערכת תזהה את זה" · 18:55: "זה היה צריך להיות יחסי".

The anchor block runs the REAL detector over the REAL 5-min bars of 2026-08-28
(pulled once from v9_bars_5min_woodies and frozen here, so the test needs no
DB), bar by bar, with the running ATR-14 the live path would have seen. If the
geometry drifts, the anchor goes red with the actual numbers.

Test classes:
  TestAnchor0828       — the ruled anchor: CEILING_FAILED on the 28.08 top.
  TestRelativity       — same shape, double ATR ⇒ same verdict (the ruling).
  TestHonestFailure    — no ATR / no level ⇒ None, never a guess (Rule 1).
  TestCounterExamples  — a trend day with no double ceiling ⇒ None.
  TestMirror           — FLOOR is the exact mirror of CEILING.
  TestWiringMutation   — delete the call site or the flag ⇒ these fail.
  TestFlagOffIdentical — flag unset ⇒ no code path runs at all.
"""
from __future__ import annotations

import ast
import inspect
import os
import pathlib
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest

from backend.v9.config_loader import load_ceiling_floor
from backend.v9.shared.atr import atr_5min
from backend.v9.systems.ceiling_floor_state import (
    DEFAULTS, detect_ceiling_floor,
)

REPO = pathlib.Path(__file__).resolve().parents[3]
FIVE_MIN_SRC = REPO / "backend" / "v9" / "systems" / "five_min" / "five_min_system.py"

# ── real bars, 2026-08-28, 16:00→19:55 IL (09:00→12:55 ET) ────────────────
# (hh:mm IL, open, high, low, close) from v9_bars_5min_woodies. The ruled
# structure: session high 7782.50 at 18:00 IL, second peak 7781.50 at 18:25,
# TPO VAH 7771.50, IB high 7761.00 — the day Michael's long was bought four
# times INTO the ceiling and scratched to zero.
BARS_0828 = [
    ('16:00', 7749.75, 7754.75, 7748.5, 7752.0),
    ('16:05', 7752.0, 7753.0, 7750.5, 7750.75),
    ('16:10', 7751.0, 7752.25, 7748.75, 7749.75),
    ('16:15', 7750.0, 7750.5, 7748.5, 7748.75),
    ('16:20', 7748.5, 7749.0, 7747.0, 7748.0),
    ('16:25', 7748.0, 7748.25, 7742.75, 7746.25),
    ('16:30', 7746.25, 7750.0, 7743.75, 7749.5),
    ('16:35', 7749.25, 7753.75, 7746.25, 7751.5),
    ('16:40', 7751.5, 7757.5, 7750.5, 7754.75),
    ('16:45', 7755.0, 7758.0, 7748.0, 7750.75),
    ('16:50', 7750.5, 7751.0, 7745.5, 7746.25),
    ('16:55', 7746.0, 7753.0, 7745.0, 7747.0),
    ('17:00', 7745.75, 7760.5, 7739.5, 7746.0),
    ('17:05', 7746.0, 7746.75, 7735.0, 7738.75),
    ('17:10', 7738.75, 7740.0, 7726.5, 7731.0),
    ('17:15', 7731.25, 7746.5, 7730.25, 7743.0),
    ('17:20', 7743.0, 7751.5, 7738.5, 7744.5),
    ('17:25', 7744.75, 7745.75, 7735.0, 7742.0),
    ('17:30', 7742.0, 7750.75, 7738.0, 7750.75),
    ('17:35', 7750.75, 7756.5, 7749.0, 7752.25),
    ('17:40', 7752.5, 7765.0, 7752.0, 7763.25),
    ('17:45', 7763.0, 7768.0, 7761.0, 7767.75),
    ('17:50', 7768.0, 7776.5, 7767.0, 7774.5),
    ('17:55', 7774.5, 7780.0, 7774.0, 7779.0),
    ('18:00', 7779.25, 7782.5, 7776.75, 7778.25),
    ('18:05', 7778.25, 7779.75, 7770.0, 7772.0),
    ('18:10', 7771.75, 7773.75, 7767.25, 7771.25),
    ('18:15', 7771.25, 7776.25, 7771.0, 7772.25),
    ('18:20', 7772.25, 7778.5, 7772.25, 7777.5),
    ('18:25', 7777.5, 7781.5, 7776.75, 7779.0),
    ('18:30', 7779.25, 7779.5, 7773.5, 7773.5),
    ('18:35', 7773.75, 7775.5, 7764.75, 7765.75),
    ('18:40', 7766.0, 7766.0, 7755.5, 7757.5),
    ('18:45', 7757.25, 7759.5, 7750.5, 7752.0),
    ('18:50', 7752.0, 7754.0, 7743.5, 7750.0),
    ('18:55', 7750.0, 7750.5, 7737.25, 7739.75),
    ('19:00', 7739.75, 7741.5, 7733.5, 7737.25),
    ('19:05', 7737.0, 7745.25, 7736.5, 7744.5),
    ('19:10', 7744.25, 7745.0, 7738.25, 7738.75),
    ('19:15', 7738.75, 7741.5, 7726.25, 7730.75),
    ('19:20', 7730.75, 7732.5, 7720.25, 7724.0),
    ('19:25', 7723.75, 7727.75, 7721.75, 7725.25),
    ('19:30', 7725.0, 7734.25, 7724.5, 7725.25),
    ('19:35', 7725.25, 7735.25, 7725.25, 7732.25),
    ('19:40', 7732.25, 7732.75, 7724.25, 7725.5),
    ('19:45', 7725.5, 7735.25, 7725.25, 7733.0),
    ('19:50', 7733.0, 7736.0, 7727.0, 7728.0),
    ('19:55', 7728.25, 7730.25, 7725.75, 7725.75),
]

VAH_0828 = 7771.50      # TPO VAH, per the work order
IB_HIGH_0828 = 7761.0   # IB high, per the work order
RTH_OPEN_IL = '16:30'   # 09:30 ET


def _bars(rows) -> List[Dict]:
    return [{"il": il, "o": o, "h": h, "l": lo, "c": c}
            for il, o, h, lo, c in rows]


def _replay(rows, *, vah=VAH_0828, val=None, ib_high=IB_HIGH_0828, ib_low=None,
            cfg=None, atr_scale=1.0):
    """Bar-by-bar replay: exactly what the live wiring feeds the detector.

    Session high/low are the RUNNING RTH extremes up to and including the
    candidate bar — no look-ahead, same as `_maybe_ceiling_floor_state`.
    """
    bars = _bars(rows)
    fired, out = set(), []
    hi = lo = None
    for i, b in enumerate(bars):
        if b["il"] >= RTH_OPEN_IL:
            hi = b["h"] if hi is None else max(hi, b["h"])
            lo = b["l"] if lo is None else min(lo, b["l"])
        window = bars[: i + 1]
        atr = atr_5min(window, period=14)
        levels = {"vah": vah, "val": val, "ib_high": ib_high, "ib_low": ib_low,
                  "session_high": hi, "session_low": lo}
        st = detect_ceiling_floor(
            window, levels, None if atr is None else atr * atr_scale,
            cfg, already_fired=fired)
        if st:
            fired.add(st["key"])
            out.append((b["il"], st))
    return out


class TestAnchor0828:
    """The ruled anchor. These numbers are measurements, not preferences —
    if the detector stops reproducing them the geometry has drifted."""

    def test_ceiling_failed_fires_on_2026_08_28(self):
        hits = _replay(BARS_0828)
        ceilings = [(t, s) for t, s in hits if s["state"] == "CEILING_FAILED"]
        assert ceilings, (
            "CEILING_FAILED did not fire on the 28.08 double top — "
            f"all states seen: {[(t, s['state']) for t, s in hits]}")

    def test_anchor_numbers_are_exact(self):
        """P1/P2/neckline/confirm — the full frozen measurement."""
        t, st = [(t, s) for t, s in _replay(BARS_0828)
                 if s["state"] == "CEILING_FAILED"][0]
        assert t == '18:35'                     # IL — 11:35 ET
        assert st["p1"] == 7782.50              # session high, 18:00 bar
        assert st["p2"] == 7781.50              # second peak, 18:25 bar
        assert st["edge_source"] == "VAH"       # VAH is tried first and wins
        assert st["edge_price"] == 7771.50
        assert st["confirm_level"] == 7767.25   # neckline = min low (P1..P2]
        assert st["confirm_close"] == 7765.75
        assert st["confirm_bar_low"] == 7764.75
        assert st["bars_between"] == 5
        assert st["bars_to_confirm"] == 2

    def test_p2_minus_p1_is_inside_the_relative_tolerance(self):
        """|P2-P1| = 1.00 pt against tol = 0.25 x ATR14(7.972) = 1.993.

        A FIXED 2-point tolerance would also have passed here — which is
        exactly why the ruling is relative: the same 1.00 pt gap on a
        4-point-ATR morning is a different structure entirely.
        """
        _, st = [(t, s) for t, s in _replay(BARS_0828)
                 if s["state"] == "CEILING_FAILED"][0]
        assert abs(st["p2"] - st["p1"]) == 1.00
        assert st["atr"] == pytest.approx(7.972, abs=0.01)
        assert st["tol"] == pytest.approx(1.993, abs=0.01)

    def test_exactly_one_ceiling_state_for_the_whole_session(self):
        """No re-fire spam: the same structure must not report twice, not
        even under a second edge source (it re-fired under SESSION_HIGH one
        bar later until the dedup key dropped the source tag)."""
        hits = _replay(BARS_0828)
        assert sum(1 for _, s in hits if s["state"] == "CEILING_FAILED") == 1

    def test_no_state_before_the_confirm_bar(self):
        """18:25 and 18:30 must stay silent — the neckline was not broken
        yet (closes 7779.00 and 7773.50 vs neckline 7767.25). Reporting the
        state before the break is the failure mode that would make the
        flip-short consumer enter into a live ceiling."""
        early = [t for t, s in _replay(BARS_0828)
                 if s["state"] == "CEILING_FAILED" and t < '18:35']
        assert early == []


def _scaled(rows, k, pivot=7750.0):
    """Same SHAPE, k times the volatility: p' = pivot + k*(p - pivot)."""
    return [(il,) + tuple(round(pivot + k * (p - pivot), 2) for p in (o, h, lo, c))
            for il, o, h, lo, c in rows]


class TestRelativity:
    """Michael 28.08 18:55: "זה היה צריך להיות יחסי". The same geometry at a
    different volatility must produce the SAME decision — that is the whole
    difference between this detector and a 2-point constant."""

    @pytest.mark.parametrize("k", [2.0, 3.0])
    def test_same_shape_bigger_atr_same_verdict(self, k):
        base = [(t, s) for t, s in _replay(BARS_0828)
                if s["state"] == "CEILING_FAILED"][0]
        scaled = [(t, s) for t, s in _replay(
            _scaled(BARS_0828, k),
            vah=round(7750.0 + k * (VAH_0828 - 7750.0), 2),
            ib_high=round(7750.0 + k * (IB_HIGH_0828 - 7750.0), 2),
        ) if s["state"] == "CEILING_FAILED"][0]
        assert scaled[0] == base[0] == '18:35'          # same confirm bar
        assert scaled[1]["p1_index"] == base[1]["p1_index"]
        assert scaled[1]["p2_index"] == base[1]["p2_index"]
        assert scaled[1]["bars_between"] == base[1]["bars_between"]
        # and the tolerance scaled with the market, as ruled (the 1e-3 slack is
        # the 2-decimal price rounding in `_scaled`, not detector drift)
        assert scaled[1]["tol"] == pytest.approx(k * base[1]["tol"], rel=1e-3)

    def test_a_fixed_two_point_tolerance_would_have_missed_it(self):
        """At 3x volatility the peaks are 3.00 pt apart. A constant
        `tol = 2.0 points` — the kind of threshold the ruling banned —
        rejects this identical structure; the ATR-relative one accepts it."""
        _, st = [(t, s) for t, s in _replay(
            _scaled(BARS_0828, 3.0),
            vah=round(7750.0 + 3.0 * (VAH_0828 - 7750.0), 2),
            ib_high=round(7750.0 + 3.0 * (IB_HIGH_0828 - 7750.0), 2),
        ) if s["state"] == "CEILING_FAILED"][0]
        assert abs(st["p2"] - st["p1"]) == 3.00     # a fixed 2.0 pt tol fails
        assert abs(st["p2"] - st["p1"]) <= st["tol"]  # the relative one holds

    def test_shrinking_atr_alone_kills_the_state(self):
        """The coupling is real, not decorative: hold the prices, quarter the
        ATR, and the 1.00 pt gap stops qualifying as "the same area"."""
        hits = _replay(BARS_0828, atr_scale=0.25)
        assert [s for _, s in hits if s["state"] == "CEILING_FAILED"] == []


class TestHonestHalt:
    """Rule 1 (CLAUDE.md): honest failure beats a synthetic value. Missing
    ATR or missing levels must yield None — never a guessed threshold."""

    def test_no_atr_returns_none(self):
        bars = _bars(BARS_0828)
        levels = {"vah": VAH_0828, "session_high": 7782.5}
        assert detect_ceiling_floor(bars, levels, None) is None
        assert detect_ceiling_floor(bars, levels, 0) is None
        assert detect_ceiling_floor(bars, levels, -1.0) is None
        assert detect_ceiling_floor(bars, levels, "nonsense") is None

    def test_no_levels_returns_none(self):
        bars = _bars(BARS_0828)
        atr = atr_5min(bars, period=14)
        assert detect_ceiling_floor(bars, None, atr) is None
        assert detect_ceiling_floor(bars, {}, atr) is None
        assert detect_ceiling_floor(
            bars, {"vah": None, "session_high": None, "ib_high": None}, atr) is None

    def test_one_missing_level_does_not_borrow_another(self):
        """VAH absent must NOT silently fall back to a substituted VAH — it
        must fall through to the NEXT CONFIGURED source and say so."""
        hits = _replay(BARS_0828, vah=None)
        ceilings = [s for _, s in hits if s["state"] == "CEILING_FAILED"]
        assert ceilings and ceilings[0]["edge_source"] == "SESSION_HIGH"
        assert ceilings[0]["edge_price"] == 7782.50   # the real session high

    def test_too_few_bars_returns_none(self):
        bars = _bars(BARS_0828)
        assert detect_ceiling_floor(bars[:2], {"vah": VAH_0828}, 8.0) is None

    def test_unreadable_bar_returns_none(self):
        bars = _bars(BARS_0828)
        bars[-1] = {"il": '19:55', "o": 1.0}          # no h/l/c
        assert detect_ceiling_floor(
            bars, {"vah": VAH_0828}, 8.0) is None


class TestCounterExamples:
    """A detector that fires everywhere is worth nothing. These pin the
    silence as tightly as the anchor pins the fire."""

    def test_real_session_is_almost_entirely_silent(self):
        """46 of the 48 real 28.08 bars produce NO state: one CEILING_FAILED
        (18:35) and one FLOOR_FAILED (19:35, the 19:20/19:25 double bottom
        that broke up through 7727.75)."""
        hits = _replay(BARS_0828, val=None, ib_low=None)
        assert [(t, s["state"]) for t, s in hits] == [
            ('18:35', 'CEILING_FAILED'),
            ('19:35', 'FLOOR_FAILED'),
        ]

    def test_clean_trend_never_reports_a_ceiling(self):
        """A one-way staircase — every bar a higher high, no retest of any
        prior peak. There is no double ceiling, so there is no state."""
        rows = []
        px = 7700.0
        for i in range(40):
            rows.append(('%02d:%02d' % (16 + (30 + i * 5) // 60, (30 + i * 5) % 60),
                         px, px + 4.0, px - 1.0, px + 3.0))
            px += 3.0
        assert _replay(rows, vah=7705.0, ib_high=7710.0) == []

    def test_a_higher_second_peak_re_anchors_p1_instead_of_confirming(self):
        """Lift the 18:25 bar above the 18:00 high and the state disappears —
        but for a subtler reason than "the close guard rejected it": the
        higher bar simply BECOMES P1 and no qualifying second touch follows
        it. Named for what it actually proves; the mutation harness showed
        the close-guard is not what fires here."""
        rows = [list(r) for r in BARS_0828]
        for r in rows:
            if r[0] == '18:25':
                r[2] = 7790.0      # high above the old P1
                r[4] = 7788.0      # close above it too
        hits = _replay([tuple(r) for r in rows])
        assert [s for _, s in hits if s["state"] == "CEILING_FAILED"] == []

    def test_second_peak_closing_above_p1_is_rejected(self):
        """"תקרה כפולה שלא הצליחה להתקדם" — a second touch that CLOSED above
        the first peak ADVANCED, so it is not a failed ceiling however weak
        the next bar is.

        This is the one position where that guard is load-bearing: P2 at
        `last-1` sits outside the window P1 is chosen from, so it is the only
        place a bar in (P1..P2] can out-close P1. Two runs identical except
        that one close; ATR is passed explicitly (4.0 ⇒ tol 1.00) so the case
        needs no warm-up series to set it.
        """
        warm = [('%02d:00' % (1 + i), 100.0, 102.0, 98.0, 100.0) for i in range(14)]
        edge = 104.0

        def _case(p2_close):
            rows = warm + [
                ('15:00', 100.0, 105.0, 99.0, 101.0),     # P1 = 105, past the edge
                ('15:05', 101.0, 101.0, 96.0, 97.0),      # rejection + neckline 96
                ('15:10', 97.0, 106.0, 103.0, p2_close),  # P2 = 106, |P2-P1| = 1.0
                ('15:15', 104.0, 104.0, 94.0, 95.0),      # confirm: closes below 96
            ]
            return detect_ceiling_floor(_bars(rows), {"vah": edge}, 4.0)

        control = _case(104.0)
        assert control is not None, "the control case must be a valid ceiling"
        assert control["state"] == "CEILING_FAILED"
        assert _case(105.5) is None, (
            "a second peak that closed ABOVE P1 advanced — it must not be "
            "reported as a failed ceiling")

    def test_double_top_far_below_the_edge_is_not_a_ceiling(self):
        """The structure alone is not enough — it has to be AT an edge.

        Same 28.08 geometry, but every edge moved 120 pt above it: two equal
        highs in the middle of the range are a coil, not a ceiling, and
        Michael's ruling is about the edge ("נגיעה/חריגה בקצה"). Mutation
        trap: delete the `p1 < edge` guard and this goes red while every
        other test still passes.
        """
        bars = _bars(BARS_0828[:32])          # ends on the 18:35 confirm bar
        atr = atr_5min(bars, period=14)
        assert detect_ceiling_floor(
            bars, {"vah": 7900.0, "session_high": 7900.0, "ib_high": 7900.0},
            atr) is None

    def test_close_above_the_neckline_is_not_a_confirmation(self):
        """Raise only the 18:35 close back above the neckline (7767.25) and
        the confirmation disappears — the break IS the trigger."""
        rows = [list(r) for r in BARS_0828]
        for r in rows:
            if r[0] == '18:35':
                r[4] = 7768.0      # close just above the neckline
        hits = [(t, s) for t, s in _replay([tuple(r) for r in rows])
                if s["state"] == "CEILING_FAILED"]
        assert not any(t == '18:35' for t, _ in hits)


def _mirror(rows, axis=7750.0):
    """Reflect the chart: high<->low, price -> 2*axis - price."""
    return [(il, 2 * axis - o, 2 * axis - lo, 2 * axis - h, 2 * axis - c)
            for il, o, h, lo, c in rows]


class TestMirror:
    """"FLOOR — מראה מדויקת". Proven by reflecting the anchor session."""

    def test_floor_is_the_exact_mirror_of_the_anchor(self):
        _, ceil = [(t, s) for t, s in _replay(BARS_0828)
                   if s["state"] == "CEILING_FAILED"][0]
        axis = 7750.0
        t, floor = [(t, s) for t, s in _replay(
            _mirror(BARS_0828, axis),
            vah=None, val=2 * axis - VAH_0828,
            ib_high=None, ib_low=2 * axis - IB_HIGH_0828,
        ) if s["state"] == "FLOOR_FAILED"][0]
        assert t == '18:35'
        assert floor["edge_source"] == "VAL"
        assert floor["p1"] == 2 * axis - ceil["p1"]
        assert floor["p2"] == 2 * axis - ceil["p2"]
        assert floor["confirm_level"] == 2 * axis - ceil["confirm_level"]
        assert floor["confirm_bar_high"] == 2 * axis - ceil["confirm_bar_low"]
        assert floor["bars_between"] == ceil["bars_between"]
        assert floor["bars_to_confirm"] == ceil["bars_to_confirm"]


class TestPurity:
    """Same input ⇒ byte-identical output in unit, replay and shadow. That
    holds only if the module cannot read the clock, the env or the DB."""

    def test_repeated_calls_are_identical(self):
        bars = _bars(BARS_0828[:32])
        atr = atr_5min(bars, period=14)
        lv = {"vah": VAH_0828, "session_high": 7782.5, "ib_high": IB_HIGH_0828}
        first = detect_ceiling_floor(bars, lv, atr)
        for _ in range(5):
            assert detect_ceiling_floor(bars, lv, atr) == first
        assert first is not None and first["state"] == "CEILING_FAILED"

    def test_module_has_no_io_no_clock_no_env(self):
        src = pathlib.Path(
            REPO / "backend" / "v9" / "systems" / "ceiling_floor_state.py"
        ).read_text()
        tree = ast.parse(src)
        banned_mods = {"os", "time", "datetime", "random", "sqlite3",
                       "requests", "backend.v9.db.read"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert a.name.split(".")[0] not in banned_mods, (
                        f"ceiling_floor_state imports {a.name} — it must stay pure")
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned_mods, (
                    f"ceiling_floor_state imports from {node.module} — must stay pure")
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("getenv", "environ", "now", "utcnow", "today"), (
                    f"ceiling_floor_state calls .{node.attr}() — must stay pure")

    def test_input_is_not_mutated(self):
        bars = _bars(BARS_0828[:32])
        snapshot = [dict(b) for b in bars]
        lv = {"vah": VAH_0828, "session_high": 7782.5}
        detect_ceiling_floor(bars, lv, 8.0)
        assert bars == snapshot
        assert lv == {"vah": VAH_0828, "session_high": 7782.5}


class TestConfigIsTheSourceOfThresholds:
    """"הכל config-tunable" — and the code default must equal the ruled YAML,
    so a missing file degrades to the same numbers instead of to a surprise."""

    def test_yaml_baseline_round_trips_to_the_code_defaults(self):
        loaded = load_ceiling_floor("baseline")
        assert loaded is not None, "config/ceiling_floor.yaml failed to load"
        assert loaded == DEFAULTS

    def test_unknown_variant_is_rejected_not_guessed(self):
        assert load_ceiling_floor("no_such_variant") is None

    def test_no_absolute_price_threshold_anywhere(self):
        """Every default is either an ATR MULTIPLE or a BAR COUNT. Anything
        in the 1000-10000 range would be a hard-coded MES price."""
        for k, v in DEFAULTS.items():
            if isinstance(v, (int, float)):
                assert v < 100, f"DEFAULTS[{k}]={v} looks like an absolute price"

    def test_variants_exist_for_replay_only(self):
        for name in ("tight_tol", "wide_tol", "va_only"):
            assert load_ceiling_floor(name) is not None


# ── wiring ────────────────────────────────────────────────────────────────

def _src_of(func) -> str:
    return inspect.getsource(func)


class TestWiring:
    """Mutation traps. Delete the call site, the flag or the detector call and
    these go red — the detector cannot quietly become dead code."""

    def test_process_bar_calls_the_detector_method(self):
        """AST, not substring: the call must really be inside process_bar."""
        tree = ast.parse(FIVE_MIN_SRC.read_text())
        target = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name == "process_bar":
                target = node
        assert target is not None, "process_bar not found"
        called = {
            n.func.attr for n in ast.walk(target)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        assert "_maybe_ceiling_floor_state" in called, (
            "process_bar no longer calls _maybe_ceiling_floor_state — the "
            "detector is wired to nothing")

    def test_method_reads_the_flag_at_call_time(self):
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        src = _src_of(FiveMinSystem._maybe_ceiling_floor_state)
        assert 'os.getenv("CEILING_FLOOR_STATE_V1"' in src
        assert '"0")' in src, "flag must default to OFF"
        assert '"shadow"' in src, "shadow mode is part of the contract"

    def test_method_calls_the_pure_detector(self):
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        src = _src_of(FiveMinSystem._maybe_ceiling_floor_state)
        assert "detect_ceiling_floor(" in src
        assert "load_ceiling_floor(" in src, "thresholds must come from YAML"

    def test_method_never_trades(self):
        """This build detects and reports. It must not route a setup, emit an
        exit or move a stop — op=EXIT is broken (ruling 07-13) and the three
        consumers are separate, separately-ruled flags."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        # scan the CODE, not the prose — the docstring names these on purpose
        fn = ast.parse(_src_of(FiveMinSystem._maybe_ceiling_floor_state).lstrip()).body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)):
            fn.body = fn.body[1:]
        code = ast.dump(ast.Module(body=fn.body, type_ignores=[]))
        for forbidden in ("route_setup", "_emit_exit", "write_exit",
                          "MODIFY_STOP", "FLATTEN_ACCOUNT"):
            assert forbidden not in code, (
                f"_maybe_ceiling_floor_state references {forbidden} — this "
                f"build must not touch the execution path")

    def test_publication_target_is_actually_read(self):
        """Anti-dead-wrapper: prove backend/main.py assigns the instance the
        reader resolves (CLAUDE.md § Codebase Index — backend/main.py is the
        real entrypoint, backend/v9/app.py is the dead wrapper)."""
        main_src = (REPO / "backend" / "main.py").read_text()
        assert "app.state.five_min_system = five_min_system" in main_src
        from backend.v9.services import trade_context
        reader = _src_of(trade_context._live_five_min_system)
        assert 'sys.modules.get("backend.main")' in reader.replace("_sys", "sys")
        assert '"five_min_system"' in reader


def _fake_rows(rows, *, age_s=330.0):
    """The frozen 28.08 OHLC, re-stamped so the newest bar is `age_s` old —
    i.e. closed (>= 300s) but not phantom (< 600s), the live wiring's window.

    Returned NEWEST-FIRST, because the production query is `ORDER BY ts DESC`
    and the wiring `reversed()`s it. Handing back oldest-first here silently
    inverted the series and made every wiring test read the OLDEST bar as the
    candidate — a fixture bug that looks exactly like a detector bug.
    """
    import time as _t
    now = _t.time()
    n = len(rows)
    out = [{"ets": now - age_s - 300.0 * (n - 1 - i),
            "o": o, "h": h, "l": lo, "c": c}
           for i, (il, o, h, lo, c) in enumerate(rows)]
    return list(reversed(out))


class _FakeSelf:
    """Minimal stand-in for FiveMinSystem: the method only touches
    _cf_date / _cf_fired / ceiling_floor_state on self."""


def _run_wiring(rows, mode, *, tpo=None, obj=None):
    """Call the REAL production method with the DB and TPO reads stubbed."""
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    env = {} if mode is None else {"CEILING_FLOOR_STATE_V1": mode}
    obj = _FakeSelf() if obj is None else obj
    read_all = lambda *a, **k: _fake_rows(rows)  # noqa: E731
    calls = []

    def _spy(*a, **k):
        calls.append(a)
        return read_all(*a, **k)

    with patch.dict(os.environ, env, clear=False):
        if mode is None:
            os.environ.pop("CEILING_FLOOR_STATE_V1", None)
        with patch("backend.v9.db.read.read_all", _spy), \
             patch("backend.v9.systems.five_min.five_min_system._load_sierra_tpo",
                   lambda *a, **k: (tpo if tpo is not None else
                                    {"vah": VAH_0828, "val": 7740.0,
                                     "ib_high": IB_HIGH_0828, "ib_low": 7726.5})):
            FiveMinSystem._maybe_ceiling_floor_state(obj)
    return obj, calls


# The live wiring always evaluates the NEWEST closed bar. To put the anchor's
# confirm bar (18:35 IL) in that position, feed the session up to and
# including it — index 31.
ANCHOR_SLICE = BARS_0828[:32]
assert ANCHOR_SLICE[-1][0] == '18:35'


class TestFlagOffIsByteIdentical:
    def test_flag_unset_touches_nothing(self):
        obj, calls = _run_wiring(ANCHOR_SLICE, None)
        assert calls == [], "flag OFF still hit the DB"
        assert not hasattr(obj, "ceiling_floor_state")
        assert not hasattr(obj, "_cf_fired")

    @pytest.mark.parametrize("mode", ["0", "off", "no", ""])
    def test_explicit_off_values_touch_nothing(self, mode):
        obj, calls = _run_wiring(ANCHOR_SLICE, mode)
        assert calls == []
        assert not hasattr(obj, "ceiling_floor_state")


class TestFlagOnPublishesTheAnchor:
    def test_shadow_detects_but_publishes_nothing(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="mems26.systems.five_min"):
            obj, calls = _run_wiring(ANCHOR_SLICE, "shadow")
        assert calls, "shadow mode must still read bars"
        assert getattr(obj, "ceiling_floor_state", None) is None, (
            "shadow must not publish a state to consumers")
        msgs = [r.getMessage() for r in caplog.records]
        hit = [m for m in msgs if m.startswith("[CeilingFloor] CEILING_FAILED")]
        assert hit, caplog.text
        # the structured WARNING must carry every field a consumer needs
        for field in ("edge=VAH", "P1=7782.50", "P2=7781.50",
                      "confirm_level=7767.25", "SHADOW"):
            assert field in hit[0], hit[0]

    def test_live_mode_publishes_the_28_08_state(self):
        obj, _ = _run_wiring(ANCHOR_SLICE, "1")
        st = getattr(obj, "ceiling_floor_state", None)
        assert st is not None, "flag=1 detected nothing on the anchor session"
        assert st["state"] == "CEILING_FAILED"
        assert st["p1"] == 7782.50 and st["p2"] == 7781.50
        assert st["confirm_level"] == 7767.25
        assert st["edge_source"] == "VAH"

    def test_state_survives_the_next_silent_bar(self):
        """The edge-lock consumer needs "the ceiling failed at 7782.50" to
        stay true for the rest of the session, not evaporate one bar later.
        The 18:40 bar reports nothing new (same structure, already fired) —
        the published state must still be there."""
        obj, _ = _run_wiring(ANCHOR_SLICE, "1")
        first = dict(obj.ceiling_floor_state)
        _run_wiring(BARS_0828[:33], "1", obj=obj)   # next bar, 18:40 IL
        assert obj.ceiling_floor_state == first

    def test_reader_returns_what_the_wiring_published(self):
        """End-to-end through the documented read path, with the LIVE app
        object stubbed exactly where backend/main.py puts it."""
        import sys
        from types import SimpleNamespace
        from backend.v9.services.trade_context import get_ceiling_floor_state

        obj, _ = _run_wiring(ANCHOR_SLICE, "1")
        fake_main = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(five_min_system=obj)))
        with patch.dict(sys.modules, {"backend.main": fake_main}):
            got = get_ceiling_floor_state()
        assert got == obj.ceiling_floor_state
        assert got is not obj.ceiling_floor_state, "reader must return a copy"

    def test_reader_is_none_without_a_running_app(self):
        import sys
        from types import SimpleNamespace
        from backend.v9.services.trade_context import get_ceiling_floor_state
        fake_main = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(five_min_system=None)))
        with patch.dict(sys.modules, {"backend.main": fake_main}):
            assert get_ceiling_floor_state() is None

    def test_building_bar_is_dropped(self):
        """A bar younger than one slot is the CURRENT building bar (T-118
        race). Confirming a ceiling on half-formed OHLC is a lie."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        obj = _FakeSelf()
        with patch.dict(os.environ, {"CEILING_FLOOR_STATE_V1": "1"}), \
             patch("backend.v9.db.read.read_all",
                   lambda *a, **k: _fake_rows(ANCHOR_SLICE, age_s=30.0)), \
             patch("backend.v9.systems.five_min.five_min_system._load_sierra_tpo",
                   lambda *a, **k: {"vah": VAH_0828, "ib_high": IB_HIGH_0828}):
            FiveMinSystem._maybe_ceiling_floor_state(obj)
        # newest bar dropped ⇒ candidate becomes 18:30, which has NOT broken
        # the neckline ⇒ no state
        assert getattr(obj, "ceiling_floor_state", None) is None

    def test_stale_feed_raises_no_state(self):
        """Anti-phantom: replay / hydration bars must never report a state."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        obj = _FakeSelf()
        with patch.dict(os.environ, {"CEILING_FLOOR_STATE_V1": "1"}), \
             patch("backend.v9.db.read.read_all",
                   lambda *a, **k: _fake_rows(ANCHOR_SLICE, age_s=3600.0)), \
             patch("backend.v9.systems.five_min.five_min_system._load_sierra_tpo",
                   lambda *a, **k: {"vah": VAH_0828, "ib_high": IB_HIGH_0828}):
            FiveMinSystem._maybe_ceiling_floor_state(obj)
        assert getattr(obj, "ceiling_floor_state", None) is None
