"""Regression: TLB_SPEC_V2 source-spec gate (Zohar/Liran) — Stage 1.

Default OFF  -> TLB fires on the old linreg geometry (behaviour unchanged).
ON           -> a trendline-break with NO ±200 extreme on the trade side is
                rejected; and even WITH the extreme, a fire with no confirming
                CONT partner (GB100/ZLR/TT) is rejected. With both -> fires.

Anti-tautology: test_v2_off proves the SAME bars DO fire without the flag, so the
ON-rejections are caused by the gate, not by the bars failing the base geometry.
"""
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.patterns import tlb


def _bars(ccis):
    out = []
    for i, c in enumerate(ccis):
        px = 7000.0 + i
        out.append(WoodiesBar(ts=float(1_700_000_000 + i * 300),
                              open=px, high=px + 1, low=px - 1, close=px,
                              cci_14=float(c), trend_state="GRAY"))
    return out


# 14 bars; last-10 window rises then drops -> base TLB SHORT geometry.
# All CCI >= 0 -> NO -200 down-extreme -> v2 must reject on the extreme rule.
SHORT_NO_EXTREME = [0, 0, 0, 0, 0, 30, 60, 90, 120, 150, 180, 210, 240, 100]
# Same geometry, but a -210 sits inside the 12-bar lookback -> extreme satisfied.
SHORT_WITH_EXTREME = [0, 0, -210, -150, -30, 30, 90, 150, 210, 250, 270, 200, 250, 100]


def test_v2_off_fires_old_behavior(monkeypatch):
    monkeypatch.delenv("TLB_SPEC_V2", raising=False)
    r = tlb.detect(_bars(SHORT_NO_EXTREME))
    assert r.detected and r.direction == "SHORT", "v2 OFF must keep old geometry firing"


def test_v2_on_blocks_when_no_extreme(monkeypatch):
    monkeypatch.setenv("TLB_SPEC_V2", "1")
    r = tlb.detect(_bars(SHORT_NO_EXTREME))
    assert not r.detected, "v2 ON must reject a SHORT with no -200 extreme"
    assert "extreme" in (r.details or {}).get("v2_reject", "")


def test_v2_on_blocks_when_no_partner(monkeypatch):
    monkeypatch.setenv("TLB_SPEC_V2", "1")
    r = tlb.detect(_bars(SHORT_WITH_EXTREME))
    assert not r.detected, "v2 ON must reject when no confirming CONT partner"
    assert "partner" in (r.details or {}).get("v2_reject", "")


def test_v2_on_fires_with_extreme_and_partner(monkeypatch):
    monkeypatch.setenv("TLB_SPEC_V2", "1")
    from backend.v9.systems.woodies.patterns import gb100
    monkeypatch.setattr(
        gb100, "detect",
        lambda bars, context=None: PatternResult(detected=True, pattern_id="GB100", direction="SHORT"),
    )
    r = tlb.detect(_bars(SHORT_WITH_EXTREME))
    assert r.detected and r.direction == "SHORT", "v2 ON must fire with extreme + partner"
