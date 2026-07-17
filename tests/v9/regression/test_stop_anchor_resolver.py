"""Stop-anchor V2 — resolver + loader unit tests.

Proves the spec numbers (config/stop_anchors.yaml) produce the right anchor /
T1 / contract / mode outputs. This is the foundation; the per-pattern wiring is
tested separately end-to-end. All flag-OFF — nothing here touches a live path.
"""
import os
from backend.v9.systems.stop_anchors import resolver as R


# ── anchor price ─────────────────────────────────────────────────────
def _bars(*lhs):  # list of (low, high)
    return [{"l": l, "h": h} for l, h in lhs]


def test_window_extreme_long_is_lowest_low():
    bars = _bars((7410.0, 7412.0), (7408.5, 7411.0), (7409.5, 7410.5))
    assert R.window_extreme(bars, "LONG") == 7408.5
    assert R.window_extreme(bars, "SHORT") == 7412.0


def test_apply_offset_3t_buffer():
    # LONG: stop 3 ticks (0.75) BELOW the cluster low
    assert R.apply_offset(7408.5, "LONG", 3) == 7407.75
    # SHORT: 3 ticks ABOVE the cluster high
    assert R.apply_offset(7412.0, "SHORT", 3) == 7412.75


def test_resolve_anchor_cluster_long():
    bars = _bars((7410, 7412), (7408.5, 7411), (7409.5, 7410.5))
    assert R.resolve_anchor_from_window(bars, "LONG", 3) == 7407.75


def test_empty_window_raises():
    try:
        R.window_extreme([], "LONG"); assert False
    except ValueError:
        pass


# ── contract ladder + min combiner ───────────────────────────────────
LADDER = [{"max_risk_points": 15, "contracts": 3},
          {"max_risk_points": 25, "contracts": 2},
          {"max_risk_points": 999, "contracts": 1}]


def test_contracts_from_risk_bands():
    assert R.contracts_from_risk(5, LADDER) == 3
    assert R.contracts_from_risk(15, LADDER) == 3
    assert R.contracts_from_risk(18, LADDER) == 2
    assert R.contracts_from_risk(25, LADDER) == 2
    assert R.contracts_from_risk(28, LADDER) == 1


def test_final_contracts_is_min_of_three():
    # risk small -> ladder 3, but auth says 2, mode strategic 3 -> min = 2
    assert R.final_contracts(4, LADDER, auth_contracts=2, mode_cap=3) == 2
    # tactical caps at 2 even when ladder+auth allow 3
    assert R.final_contracts(4, LADDER, auth_contracts=3, mode_cap=2) == 2
    # wide risk -> ladder 1 dominates
    assert R.final_contracts(20, LADDER, auth_contracts=3, mode_cap=3) == 2
    assert R.final_contracts(28, LADDER, auth_contracts=3, mode_cap=3) == 1


# ── T1 ladder ────────────────────────────────────────────────────────
T1L = [{"max_risk_points": 5, "t1_r": 1.00}, {"max_risk_points": 10, "t1_r": 0.75},
       {"max_risk_points": 15, "t1_r": 0.65}, {"max_risk_points": 20, "t1_r": 0.50},
       {"max_risk_points": 25, "t1_r": 0.40}]


def test_t1_ladder_continuation_long():
    # entry 7400, stop 7396 -> risk 4 -> band 1R -> T1 7404 (but floor 3 -> 4>=3 ok)
    assert R.t1_price(7400, 7396, "LONG", t1_ladder_cont=T1L, reversal=False,
                      reversal_mult=0.8, t1_floor_points=3) == 7404.0
    # risk 10 -> 0.75R -> 7.5 pts -> 7407.5
    assert R.t1_price(7400, 7390, "LONG", t1_ladder_cont=T1L, reversal=False,
                      reversal_mult=0.8, t1_floor_points=3) == 7407.5


def test_t1_floor_3pt_protects_tiny_stops():
    # risk 2 -> 1R = 2 pts, but floor 3 -> T1 must be +3, not +2 (6א)
    assert R.t1_price(7400, 7398, "LONG", t1_ladder_cont=T1L, reversal=False,
                      reversal_mult=0.8, t1_floor_points=3) == 7403.0


def test_t1_reversal_multiplier():
    # risk 10 cont = 0.75R = 7.5 ; reversal x0.8 = 6.0 pts -> 7406.0 SHORT below
    assert R.t1_price(7400, 7410, "SHORT", t1_ladder_cont=T1L, reversal=True,
                      reversal_mult=0.8, t1_floor_points=3) == 7394.0


def test_t1_ladder_shift_for_hfe():
    # risk 4 normally band0 (1R). shift -1 stays band0 (can't go lower) -> 1R
    v0 = R.t1_price(7400, 7396, "LONG", t1_ladder_cont=T1L, reversal=False,
                    reversal_mult=0.8, t1_floor_points=3, ladder_shift=-1)
    assert v0 == 7404.0
    # risk 12 normally band2 (0.65R). shift -1 -> band1 (0.75R) = 9 pts -> 7409
    v1 = R.t1_price(7400, 7388, "LONG", t1_ladder_cont=T1L, reversal=False,
                    reversal_mult=0.8, t1_floor_points=3, ladder_shift=-1)
    assert v1 == 7409.0


# ── mode classifier ──────────────────────────────────────────────────
def test_mode_trend_day():
    s = R.classify_mode(day_has_direction=True, trade_with_trend=True,
                        value_area_full_traverse=None, strategic_cap=3, tactical_cap=2)
    assert s.mode == "strategic" and s.cap == 3
    t = R.classify_mode(day_has_direction=True, trade_with_trend=False,
                        value_area_full_traverse=None, strategic_cap=3, tactical_cap=2)
    assert t.mode == "tactical" and t.cap == 2


def test_mode_value_day():
    s = R.classify_mode(day_has_direction=False, trade_with_trend=None,
                        value_area_full_traverse=True, strategic_cap=3, tactical_cap=2)
    assert s.mode == "strategic"
    t = R.classify_mode(day_has_direction=False, trade_with_trend=None,
                        value_area_full_traverse=False, strategic_cap=3, tactical_cap=2)
    assert t.mode == "tactical"


# ── the real YAML loads + validates + has all 15 anchors ─────────────
def test_real_stop_anchors_yaml_loads():
    from backend.v9.config_loader import load_stop_anchors
    data = load_stop_anchors()
    assert data is not None, "stop_anchors.yaml failed validation"
    assert data["risk_cap_points"] == 25
    assert data["mode_caps"] == {"strategic": 3, "tactical": 2}
    # 14 originals + CONFLUENCE_RI_ZLR (S2×S4 combined, 2026-07-17 spec)
    assert len(data["anchors"]) == 15
    # the research-changed ones are present as decided
    assert data["anchors"]["OFA_Initiative"]["type"] == "breakout_bar"   # stays tight
    assert data["anchors"]["Flag"]["type"] == "breakout_bar"               # Michael 2026-06-09: breakout bar
    # ZLR: Michael 2026-06-30 — stop on the breakout bar (window 1; was
    # cluster_low/4 which reached stale dips → 16.5pt SKIP). Pin was stale (4).
    assert data["anchors"]["ZLR"]["type"] == "breakout_bar"
    assert data["anchors"]["ZLR"]["window"] == 1
    # CONFLUENCE_RI_ZLR: deliberately tight 7pt cap (< ZLR's 15), same anchor
    assert data["anchors"]["CONFLUENCE_RI_ZLR"] == {
        "system": "S4", "group": "CONT", "type": "breakout_bar",
        "window": 1, "max_risk_points": 7,
    }
