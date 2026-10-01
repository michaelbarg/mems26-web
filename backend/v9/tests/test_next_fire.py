# -*- coding: utf-8 -*-
"""NEXT_FIRE (Michael 01.10): live-only · tree decides · the level is the producer's trigger geometry."""
import os

import pytest

from backend.v9.services import next_fire as nf


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    for k, v in {"ZLR_SHADOW_V1": "1", "CEILING_FLIP_TOUCH2_V1": "shadow", "CEILING_FLIP_SHORT_V1": "1",
                 "DALTON_EDGE_V1": "live", "OPENING_ENTRY_V1": "1", "TREND_STEP_ENTRY_V1": "shadow",
                 "S2_DELTA_DBL_V1": "shadow", "RE_ACCEPTANCE_V1": "shadow"}.items():
        monkeypatch.setenv(k, v)


def _plan(long_take, short_take):
    kinds = ["WITH_DRIVE", "REVERSAL", "EDGE_FADE", "PULLBACK", "BREAK", "VALUE_RETURN"]
    return {"LONG": {k: {"leaf": "TAKE" if long_take else "SKIP", "id": "x" if long_take else "bias"} for k in kinds},
            "SHORT": {k: {"leaf": "TAKE" if short_take else "SKIP", "id": "x" if short_take else "bias"} for k in kinds}}


CTX = {"price": 7704.75, "va": [7680.75, 7709.25], "ib": [7682.25, 7740.25], "session": [7672.75, 7740.25],
       "poc": 7698.75, "phase": "C"}
BARS = [{"h": 7700 + i, "l": 7690 + i, "c": 7695 + i} for i in range(13)]  # lo12 = 7691, hi12 = 7712


def test_live_capability_registry():
    assert nf.live_capability("ZLR") == (False, "ZLR_SHADOW_V1")
    assert nf.live_capability("CEILING_FLIP_TOUCH2")[0] is False
    assert nf.live_capability("CEILING_FLIP_SHORT")[0] is True
    assert nf.live_capability("DALTON_EDGE_LONG")[0] is True
    assert nf.live_capability("FAILED_BREAK_LONG")[0] is False
    assert nf.live_capability("VA_FADE_SHORT")[0] is False
    assert nf.live_capability("REACTIVE_LONG") == (True, "live producer")
    assert nf.live_capability("footprint_absorption")[0] is False


def test_short_only_day_headline_names_the_price_and_refuses_long():
    out = nf.assemble(ctx=CTX, plan=_plan(False, True), plan_he={"LONG": "נגד ההטיה של הסשן", "SHORT": "ייקח: היפוך"},
                      bars=BARS, inspector={})
    assert out["allowed"] == {"LONG": False, "SHORT": True}
    n = out["nearest"]
    assert n is not None and n["direction"] == "SHORT" and n["live"] and n["allowed"]
    # nearest SHORT trigger above the price: VAH 7709.25 (4.50 above) beats the 12-bar high 7712
    assert n["pattern"] == "CEILING_FLIP_SHORT" and n["level"] == 7709.25 and n["dist"] == 4.5 and n["side"] == "above"
    assert "שורט: CEILING_FLIP_SHORT ב-7709.25 (VAH) — 4.50 נק׳ מעל למחיר" in out["headline_he"]
    assert "לונג: העץ מסרב — נגד ההטיה של הסשן" in out["headline_he"]
    # every LONG candidate is marked not-allowed; no LONG ever reaches live_allowed
    assert all(not c["allowed"] for c in out["candidates"] if c["direction"] == "LONG")


def test_shadow_only_producers_never_become_the_nearest_fire(monkeypatch):
    monkeypatch.setenv("CEILING_FLIP_SHORT_V1", "shadow")
    out = nf.assemble(ctx=CTX, plan=_plan(True, True), plan_he={}, bars=BARS, inspector={})
    assert out["nearest"] is not None
    assert out["nearest"]["pattern"] != "CEILING_FLIP_SHORT" and out["nearest"]["pattern"] != "CEILING_FLIP_LONG"
    cf = [c for c in out["candidates"] if c["pattern"].startswith("CEILING_FLIP")]
    assert cf and all(not c["live"] for c in cf)


def test_s2_neckline_from_inspector_becomes_a_level():
    inspector = {"systems": [{"id": "five_min", "patterns": [
        {"id": "DOUBLE_TOP_AA_SHORT", "status": "armed",
         "reason": "Awaiting: neckline_breakout — close=7693.50 · neckline=7677.25 · gap=16.25pts ✗"},
        {"id": "INITIATIVE_SHORT", "status": "armed", "reason": "Awaiting: b1_expansion — b1 range=9.25 · need [12.3, 23.6] ✗"},
    ]}]}
    out = nf.assemble(ctx=CTX, plan=_plan(False, True), plan_he={}, bars=BARS, inspector=inspector)
    dt = next(c for c in out["candidates"] if c["pattern"] == "DOUBLE_TOP_AA_SHORT")
    assert dt["level"] == 7677.0 and dt["level_name"] == "NECKLINE" and dt["side"] == "below"
    ini = next(c for c in out["candidates"] if c["pattern"] == "INITIATIVE_SHORT")
    assert ini["level"] is None and ini["awaiting"].startswith("b1_expansion")


def test_opening_extreme_only_in_phase_ab():
    out_c = nf.assemble(ctx=dict(CTX, phase="C"), plan=_plan(True, True), plan_he={}, bars=BARS, inspector={})
    assert not any(c["pattern"] == "OPENING_EXTREME_REJECT" for c in out_c["candidates"])
    out_b = nf.assemble(ctx=dict(CTX, phase="B"), plan=_plan(True, True), plan_he={}, bars=BARS, inspector={})
    oer = [c for c in out_b["candidates"] if c["pattern"] == "OPENING_EXTREME_REJECT"]
    assert {c["level"] for c in oer} == {7672.75, 7740.25}


def test_no_price_no_invention():
    out = nf.assemble(ctx={"price": None, "phase": "C"}, plan=_plan(True, True), plan_he={}, bars=[], inspector={})
    assert out["nearest"] is None and all(c["level"] is None for c in out["candidates"])


def test_s4_direction_follows_trend_colour():
    inspector = {"systems": [{"id": "woodies", "live_inputs": [{"field": "trend_state", "value": "BLUE"}],
                              "patterns": [{"id": "TLB", "status": "armed", "reason": "Data ready, trend BLUE · TLB not yet detected"}]}]}
    out = nf.assemble(ctx=CTX, plan=_plan(False, True), plan_he={}, bars=BARS, inspector=inspector)
    tlb = [c for c in out["candidates"] if c["pattern"] == "TLB"]
    assert len(tlb) == 1 and tlb[0]["direction"] == "LONG" and tlb[0]["allowed"] is False
