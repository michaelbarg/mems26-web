"""S2_REACTIVE_EDGE_FIX_V1 — Michael live ruling 2026-07-17 ~20:00.

Bug: calculate_size (S2 legacy fallback) rejected a valid REACTIVE fade at the
value-area EDGE because it demanded location=="at"/"near" the POC (a fade at VAH
is FAR from POC), and hard-required COT/AMT (violating the S2⟂S3 standing
decision). Both silently rejected → setup never emitted → no trade, no decisions
entry. Michael was at VAH and a SHORT was correct.
"""
import backend.v9.systems.five_min.five_min_system as fm


def _sys():
    return fm.FiveMinSystem() if hasattr(fm, "FiveMinSystem") else fm.FiveMinuteSystem()


def _state(direction="SHORT", bars=4, cot=0, amt=0, loc="far"):
    return {"bars_formed": bars, "pattern_type": "reactive", "direction": direction,
            "cot": cot, "amt": amt, "location_vs_poc_vol": loc}


def test_edge_fade_at_vah_not_rejected(monkeypatch):
    """VAH short (location=far from POC) + no flow data (CVD empty) → still trades."""
    monkeypatch.setenv("S2_REACTIVE_EDGE_FIX_V1", "1")
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    s = _sys()
    assert s.calculate_size(_state(direction="SHORT", bars=3, cot=0, amt=0, loc="far")) != "reject"


def test_edge_full_size_with_flow(monkeypatch):
    monkeypatch.setenv("S2_REACTIVE_EDGE_FIX_V1", "1")
    s = _sys()
    # SHORT strong flow: cot < amt*0.8
    assert s.calculate_size(_state("SHORT", bars=4, cot=10, amt=100, loc="far")) == "full"


def test_flow_still_gates_when_explicitly_required(monkeypatch):
    monkeypatch.setenv("S2_REACTIVE_EDGE_FIX_V1", "1")
    monkeypatch.setenv("S2_REQUIRE_COT_AMT", "1")
    s = _sys()
    # SHORT but cot>amt (no flow support) → reject only because re-required
    assert s.calculate_size(_state("SHORT", bars=4, cot=100, amt=10, loc="far")) == "reject"


def test_immature_still_rejects(monkeypatch):
    monkeypatch.setenv("S2_REACTIVE_EDGE_FIX_V1", "1")
    s = _sys()
    assert s.calculate_size(_state("SHORT", bars=2)) == "reject"


def test_flag_off_is_legacy(monkeypatch):
    """Byte-identical legacy: far-from-POC + no flow → reject (the old bug)."""
    monkeypatch.setenv("S2_REACTIVE_EDGE_FIX_V1", "0")
    s = _sys()
    assert s.calculate_size(_state("SHORT", bars=4, cot=0, amt=0, loc="far")) == "reject"
