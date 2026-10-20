# -*- coding: utf-8 -*-
"""T-616 — the 20.10 doctrine gaps (Michael 20.10: "do Dalton's doctrine and what I defined approve trades like
these, mainly the losers? I think not — I want the gaps plus their fixes").

Each fix ships behind its own flag (default OFF ⇒ byte-identical) and is measured in the base-20.10 replay before
it goes on in demo:
  1. OPENING_DRIVE_STRICT_V1 — an Open-Drive never trades back to the open (Dalton); a tested open is a Test-Drive.
     20.10 16:40: open 7726.75, bar 2 high 7731.00, bar 3 close 7713.00 < OR low → fired DRIVE SHORT (#3540).
  2. STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1 — a producer stop at/beyond its own structural_anchor is structural
     (09.09: never compressed, size derived). #3558: 7795.50 beyond 7791.75 was cut to 7767.75 by the step ladder.
  3. config/decision_tree_v3.t616_edge.yaml (replay variant) — the T-329 failed-extension flip only at the edge.
     #3558 took it at mid_value, 34pt under the double top.
  4. SCALE_IN_MIN_EXEMPT_V1 — RISK_MIN_CONTRACTS is the floor of a new entry, not of a SCALE_IN add (#3550).
"""
from __future__ import annotations

import importlib
import os

import pytest

from backend.v9.systems.opening_entry import evaluate_opening_entry

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def B(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


# ── 1. opening: Drive vs Test-Drive ────────────────────────────────────────────────────────────────
# 20.10 RTH, IL 16:30 / 16:35 / 16:40 (v9_bars_5min_woodies)
OPEN_1 = B(7726.75, 7727.00, 7718.50, 7723.25)
OPEN_2 = B(7723.25, 7731.00, 7720.00, 7725.50)   # trades 4.25 ABOVE the open → the open was tested
OPEN_3 = B(7725.50, 7726.25, 7711.25, 7713.00)   # closes below the OR low 7718.50


def test_2010_open_reads_drive_without_the_flag(monkeypatch):
    monkeypatch.delenv("OPENING_DRIVE_STRICT_V1", raising=False)
    t = evaluate_opening_entry([OPEN_1, OPEN_2, OPEN_3])
    assert t and t["type"] == "DRIVE" and t["direction"] == "SHORT"


def test_2010_open_reads_test_drive_with_the_flag(monkeypatch):
    monkeypatch.setenv("OPENING_DRIVE_STRICT_V1", "1")
    t = evaluate_opening_entry([OPEN_1, OPEN_2, OPEN_3])
    assert t and t["type"] == "TEST_DRIVE" and t["direction"] == "SHORT"
    assert t["excursion"] == pytest.approx(4.25)


def test_clean_drive_is_still_a_drive_with_the_flag(monkeypatch):
    monkeypatch.setenv("OPENING_DRIVE_STRICT_V1", "1")
    b1 = B(7530.0, 7533.0, 7528.25, 7531.0)          # bar-1 wick below the open does not count
    b2 = B(7531.0, 7536.0, 7530.5, 7535.0)           # never back to the open, closes above the OR high
    t = evaluate_opening_entry([b1, b2])
    assert t and t["type"] == "DRIVE" and t["direction"] == "LONG"


def test_one_tick_beyond_the_open_is_not_a_test(monkeypatch):
    monkeypatch.setenv("OPENING_DRIVE_STRICT_V1", "1")
    b1 = B(7530.0, 7533.0, 7528.25, 7531.0)
    b2 = B(7531.0, 7536.0, 7529.75, 7535.0)          # low = open − 1 tick
    t = evaluate_opening_entry([b1, b2])
    assert t and t["type"] == "DRIVE"


def test_tested_open_without_reclaim_is_no_drive(monkeypatch):
    """A drive-close after a test that did not reach the TD excursion threshold produces no initiating entry."""
    monkeypatch.setenv("OPENING_DRIVE_STRICT_V1", "1")
    b1 = B(7530.0, 7531.0, 7526.0, 7528.0)           # OR 5pt → TD needs ≥ 2.5pt excursion from bar 2
    b2 = B(7528.0, 7531.0, 7527.0, 7529.0)           # +1.0 above the open (a test, below the TD threshold)
    b3 = B(7529.0, 7529.5, 7522.0, 7523.0)           # closes below the OR low
    t = evaluate_opening_entry([b1, b2, b3])
    assert t is None or t["type"] not in ("DRIVE", "TEST_DRIVE")


# ── 2. gateway: the producer's structural stop ────────────────────────────────────────────────────
def test_anchor_short_stop_beyond_the_anchor_is_structural():
    from backend.v9.gateway.trading_gateway import t616_anchor_stop_is_structural as f
    s = {"stop": 7795.50, "metadata": {"structural_anchor": 7791.75}}          # #3558 as emitted
    assert f(s, "SHORT") == (7795.50, 7791.75)


def test_anchor_short_stop_inside_the_structure_is_not():
    from backend.v9.gateway.trading_gateway import t616_anchor_stop_is_structural as f
    s = {"stop": 7767.75, "metadata": {"structural_anchor": 7791.75}}          # #3558 after the step ladder
    assert f(s, "SHORT") is None


def test_anchor_long_mirrors():
    from backend.v9.gateway.trading_gateway import t616_anchor_stop_is_structural as f
    assert f({"stop": 7700.0, "metadata": {"structural_anchor": 7702.5}}, "LONG") == (7700.0, 7702.5)
    assert f({"stop": 7705.0, "metadata": {"structural_anchor": 7702.5}}, "LONG") is None


@pytest.mark.parametrize("setup", [
    {"stop": 7795.5, "metadata": {}},
    {"stop": None, "metadata": {"structural_anchor": 7791.75}},
    {"stop": 7795.5, "metadata": {"structural_anchor": "x"}},
    {"stop": 7795.5, "metadata": {"structural_anchor": 0}},
    {"stop": 7795.5},
])
def test_anchor_missing_or_bad_is_not_structural(setup):
    from backend.v9.gateway.trading_gateway import t616_anchor_stop_is_structural as f
    assert f(setup, "SHORT") is None


def test_anchor_unknown_direction_is_not_structural():
    from backend.v9.gateway.trading_gateway import t616_anchor_stop_is_structural as f
    assert f({"stop": 7795.5, "metadata": {"structural_anchor": 7791.75}}, None) is None


# ── 3. tree variant: the failed-extension flip only at the edge ───────────────────────────────────
# #3558 as the gateway walked it: hour=*(18)/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/
#   pattern=*(DOUBLE_TOP_AA_SHORT)/rel_bias=against/edge=failed_extension → TAKE
VEC_3558 = {"hour": 18, "opening_type": "OPEN_REJECTION_REVERSE", "phase": "C", "day_type": "Variation",
            "structure": "up", "pattern": "DOUBLE_TOP_AA_SHORT", "kind": "REVERSAL", "direction": "SHORT",
            "rel_bias": "against", "zone": "mid_value", "edge": "failed_extension"}


def _walk(name, vec):
    from backend.v9.services import decision_tree as dt
    return dt.walk(dt.load_tree(os.path.join(ROOT, "config", name)), vec)


def test_live_tree_takes_3558():
    leaf, _path = _walk("decision_tree_v3.yaml", VEC_3558)
    assert leaf.get("leaf") == "TAKE"


def test_variant_skips_3558_mid_value():
    leaf, _path = _walk("decision_tree_v3.t616_edge.yaml", VEC_3558)
    assert leaf.get("leaf") == "SKIP" and leaf.get("id") == "failed_ext_far"


@pytest.mark.parametrize("zone", ["near_vah", "above_value"])
def test_variant_takes_the_flip_at_the_edge(zone):
    leaf, _path = _walk("decision_tree_v3.t616_edge.yaml", dict(VEC_3558, zone=zone))
    assert leaf.get("leaf") == "TAKE"


def test_variant_long_mirrors():
    vec = dict(VEC_3558, pattern="DOUBLE_BOTTOM_EE_LONG", direction="LONG", zone="near_val")
    leaf, _ = _walk("decision_tree_v3.t616_edge.yaml", vec)
    assert leaf.get("leaf") == "TAKE"
    leaf, _ = _walk("decision_tree_v3.t616_edge.yaml", dict(vec, zone="mid_value"))
    assert leaf.get("leaf") == "SKIP"


# ── 4. sizing: a SCALE_IN add is not a new entry ──────────────────────────────────────────────────
@pytest.fixture
def sizing(monkeypatch):
    mod = importlib.import_module("backend.v9.services.sierra_command")
    cs = importlib.import_module("backend.v9.services.contract_size")
    monkeypatch.setattr(cs, "ruled_contracts", lambda *a, **k: 5)
    monkeypatch.setenv("RISK_BUDGET_SIZING_V1", "1")
    monkeypatch.setenv("RISK_BUDGET_USD", "225")
    monkeypatch.setenv("RISK_MIN_CONTRACTS", "3")
    monkeypatch.setenv("RISK_MAX_PTS_HARD", "30")
    return mod._effective_contracts_raw


ADD_3550 = {"classification": "SCALE_IN", "direction": "LONG", "entry_price": 7747.5, "stop": 7729.12,
            "contracts": 2, "metadata": {"scale_in_parent": 3544}}


def test_scale_in_add_refused_without_the_flag(sizing, monkeypatch):
    monkeypatch.delenv("SCALE_IN_MIN_EXEMPT_V1", raising=False)
    assert sizing(dict(ADD_3550)) == 0


def test_scale_in_add_ships_with_the_flag(sizing, monkeypatch):
    monkeypatch.setenv("SCALE_IN_MIN_EXEMPT_V1", "1")
    assert sizing(dict(ADD_3550)) == 2


def test_scale_in_add_capped_by_the_budget(sizing, monkeypatch):
    monkeypatch.setenv("SCALE_IN_MIN_EXEMPT_V1", "1")
    assert sizing(dict(ADD_3550, stop=7747.5 - 25.0)) == 1          # 225 / (25 × 5) = 1.8 → 1


def test_scale_in_add_beyond_the_hard_max_refused(sizing, monkeypatch):
    monkeypatch.setenv("SCALE_IN_MIN_EXEMPT_V1", "1")
    assert sizing(dict(ADD_3550, stop=7747.5 - 31.0)) == 0


def test_new_entry_still_needs_three(sizing, monkeypatch):
    monkeypatch.setenv("SCALE_IN_MIN_EXEMPT_V1", "1")
    entry = {"classification": "DOUBLE_TOP_AA_SHORT", "direction": "SHORT", "entry_price": 7757.0,
             "stop": 7775.4, "contracts": 5, "metadata": {}}
    assert sizing(entry) == 0                                           # 18.4pt → n=2 < 3
