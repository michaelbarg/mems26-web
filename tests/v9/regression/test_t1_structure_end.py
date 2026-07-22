"""Rulings C+D (Michael 2026-07-21/22) — T1 = entry-structure END · stop behind
structure EXTREME.

C (07-21 ~18:15): "T1 בסוף מבנה-הכניסה; לבטל את האופן שבו הוא מחושב."
D (07-21 22:22): stop behind the structure extreme, not a single bar.

Fixtures = the LIVE blocked decisions of 2026-07-21 (raw from gateway/decisions):
  17:45:05 S4 ZLR LONG entry 7530.25 stop_dist 7.50 T1_dist 3.00 → R:R 0.40 BLOCKED
  17:45:07 S4 ZLR LONG entry 7531.00 stop_dist 8.25 T1_dist 2.25 → R:R 0.27 BLOCKED
  17:30:03 S4 GB100 LONG entry 7532.25 stop_dist 23.25 T1_dist 0.25 → R:R 0.01 BLOCKED
The 17:30-17:45 structure high was 7535.75 (bar 17:30) — the structure end a
with-trend CONT should have targeted; price then ran to 7546.75.
"""
import pytest

from backend.v9.systems.stop_anchors import resolver as SA

RR_MIN_ROTATION = 0.65


class B:  # minimal bar
    def __init__(self, h, l):
        self.h = h
        self.l = l
        self.high = h
        self.low = l


# window replicating 16:50-17:45 (completed bars around the 17:45 ZLR)
WIN = [B(7521.0, 7515.5), B(7523.5, 7517.0), B(7527.0, 7521.0), B(7529.0, 7522.75),
       B(7533.25, 7526.0), B(7535.75, 7529.0), B(7533.75, 7524.25)]


# ── C: structure_end_t1 ─────────────────────────────────────────────

def test_structure_end_long_is_window_high():
    assert SA.structure_end_t1(WIN, "LONG") == 7535.75


def test_structure_end_short_is_window_low():
    assert SA.structure_end_t1(WIN, "SHORT") == 7515.5


def test_structure_end_empty_raises():
    with pytest.raises(ValueError):
        SA.structure_end_t1([], "LONG")


def test_zlr_1745_with_structure_t1_passes_rr():
    """The blocked 17:45 ZLR: ladder T1 3.00pt vs stop 7.50 → 0.40 BLOCKED.
    Structure-end T1 (7535.75 from entry 7530.25) = 5.50pt → 0.73 ≥ 0.65 PASSES."""
    entry, stop_dist = 7530.25, 7.50
    t1 = SA.structure_end_t1(WIN, "LONG")
    t1_dist = t1 - entry
    assert t1_dist == pytest.approx(5.50)
    assert t1_dist / stop_dist >= RR_MIN_ROTATION  # 0.733
    # yesterday's ladder numbers really were blocked:
    assert 3.00 / stop_dist < RR_MIN_ROTATION


def test_gb100_1730_structure_exhausted_case():
    """GB100 17:30 entry 7532.25 — window high 7535.75 gives only 3.5pt vs a
    23.25pt stop → still fails rr (honest structure geometry, no invented T1).
    And when entry sits AT the structure end → t1_structure_valid=False."""
    entry = 7532.25
    t1 = SA.structure_end_t1(WIN, "LONG")
    assert (t1 - entry) / 23.25 < RR_MIN_ROTATION  # honest: structure has no room vs that stop
    at_end = SA.structure_end_t1(WIN, "LONG")
    assert SA.t1_structure_valid(at_end, at_end, "LONG") is False  # entry at end → exhausted
    assert SA.t1_structure_valid(at_end - 0.25, at_end, "LONG") is False  # 1T < min 2T
    assert SA.t1_structure_valid(at_end - 0.50, at_end, "LONG") is True   # 2T ok


def test_t1_valid_short_side():
    end = SA.structure_end_t1(WIN, "SHORT")  # 7515.5
    assert SA.t1_structure_valid(7520.0, end, "SHORT") is True
    assert SA.t1_structure_valid(7515.5, end, "SHORT") is False


# ── D: widen_stop_to_structure ──────────────────────────────────────

def test_widen_long_takes_lower():
    # single-bar stop 7528 vs structure low 7515.5-6T=7514.0 → structure wins
    struct = SA.apply_offset(SA.window_extreme(WIN, "LONG"), "LONG", 6)
    assert struct == 7514.0
    assert SA.widen_stop_to_structure(7528.0, struct, "LONG") == 7514.0


def test_widen_never_tightens():
    # current stop already wider than structure → unchanged
    assert SA.widen_stop_to_structure(7510.0, 7514.0, "LONG") == 7510.0
    assert SA.widen_stop_to_structure(7540.0, 7536.0, "SHORT") == 7540.0


def test_d_kills_single_bar_stop_class():
    """Michael 22:22 evidence class: 1.75-3.5pt stops vs a real structure edge.
    entry 7531, last-bar low 7529 (+6T → 7527.5 = 3.5pt stop) → structure low
    7515.5+6T → 7514.0 = 17pt honest structural stop."""
    entry = 7531.0
    single_bar_stop = SA.apply_offset(7529.0, "LONG", 6)
    assert entry - single_bar_stop == pytest.approx(3.0, abs=0.51)
    final = SA.widen_stop_to_structure(single_bar_stop, SA.apply_offset(SA.window_extreme(WIN, "LONG"), "LONG", 6), "LONG")
    assert final == 7514.0
    assert entry - final == pytest.approx(17.0)


# ── flags OFF = modules import + helpers unused (no behavior change path) ──

def test_flags_off_no_import_errors():
    import importlib
    import backend.v9.systems.stop_anchors.resolver as r
    importlib.reload(r)
    assert hasattr(r, "structure_end_t1") and hasattr(r, "widen_stop_to_structure")


def test_breakout_exhausted_falls_to_1r_viability():
    """18:51 live blocks (Michael 'תקלה חמורה'): at new highs the structure end
    is ~entry (2.75pt vs 5.75 stop → rr 0.48 blocked). The viability rule:
    structural T1 only when dist >= rr_min×risk; else exhausted → T1=1R.
    Yesterday's fixture must STILL choose structural (5.5 >= 0.65×7.5)."""
    # yesterday's pullback: structural viable → kept
    entry, stop = 7530.25, 7522.75  # risk 7.5
    t1 = SA.structure_end_t1(WIN, "LONG")  # 7535.75 → dist 5.5
    assert (t1 - entry) >= 0.65 * (entry - stop)  # structural stays
    # today's breakout: structure end 2.75 away, stop 5.75 → NOT viable
    entry2, stop2 = 7557.0, 7551.25  # risk 5.75
    win_break = WIN + [B(7559.75, 7552.0, 7557.0)]  # window high 7559.75 → dist 2.75
    t1b = SA.structure_end_t1(win_break, "LONG")
    assert t1b - entry2 < 0.65 * (entry2 - stop2)  # viability fails → caller uses 1R
    # 1R target passes the rr gate by construction: dist == risk → rr 1.0
