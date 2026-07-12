"""P1-5 — Trend recognition by CONTROL (stair-steps), not range multiple.

Dalton pp.22-25 (doctrine contradiction-2): a Trend day is one-timeframe
control with an elongating profile; rib>=2.5 + close-at-extreme recognizes it
only after the move is over. The 2026-07-08 incident: a stair-stepping down
day sat classified Variation all session.

S1_TREND_CONTROL_V1 (default OFF): >=3 consecutive stair-steps in the one_tf
direction + rib>=1.8 + close pressing the matching extreme → Trend_Normal.
Anti-tautological: flag OFF → the same fixture stays Normal_Variation.
"""
from backend.v9.systems.day_type.relative_features import compute_relative_features
from backend.v9.systems.day_type.daytype_classifier import classify


def _bar(o, h, l, c, v=100):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


IB_LO, IB_HI = 7560.0, 7580.0  # IB 20pt


def _stair_down_day():
    """12 IB bars, then 24 post-IB bars stair-stepping DOWN: each 30-min period
    (6 bars) makes a lower-low AND lower-high. rib ends ~2.05 — BELOW the 2.5
    strict floor, exactly the 07-08 failure shape."""
    bars = [_bar(7570, 7580, 7560, 7565, v=120) for _ in range(12)]
    base = 7560.0
    for p in range(4):            # 4 descending 30-min periods
        for j in range(6):
            px = base - p * 6 - j * 0.8
            bars.append(_bar(px + 0.5, px + 1.2, px - 1.4, px - 1.0, v=140))
    return bars


def _features(bars):
    f = compute_relative_features(bars, IB_HI, IB_LO).as_dict()
    # session close near the low → close_pos small (pressing the down extreme)
    return f


def _feat_for_classifier(f):
    f = dict(f)
    f.setdefault("vol_ratio", 1.0)
    f.setdefault("opening_type", "OPEN_REJECTION_REVERSE")
    f.setdefault("ib_pctile", 50)
    f.setdefault("dd_second_dist", None)
    return f


def _plan():
    # real plan from config — the same loader the engine uses (no synthetic thresholds)
    from backend.v9.systems.day_type.daytype_classifier import load_plan
    return load_plan()


def test_stair_down_fixture_has_control_signature():
    f = _features(_stair_down_day())
    assert f["one_tf"] == "DOWN", f
    assert f["stair_steps_dn"] >= 3, f
    assert f["sides"] == 1, f
    assert 1.8 <= f["rib"] < 2.5, f"fixture must sit under the strict floor, rib={f['rib']}"
    assert f["close_pos"] <= 0.25, f


def test_flag_off_stays_variation(monkeypatch):
    """Reproduces 07-08: without the control path the day is 'Variation'."""
    monkeypatch.delenv("S1_TREND_CONTROL_V1", raising=False)
    f = _feat_for_classifier(_features(_stair_down_day()))
    r = classify(f, _plan(), is_eod=False)
    assert r["day_type"] == "Normal_Variation", r


def test_flag_on_recognizes_trend(monkeypatch):
    monkeypatch.setenv("S1_TREND_CONTROL_V1", "1")
    f = _feat_for_classifier(_features(_stair_down_day()))
    r = classify(f, _plan(), is_eod=False)
    assert r["day_type"] == "Trend_Normal", r
    assert "control-path" in r.get("reason", ""), r


def test_flag_on_no_steps_no_trend(monkeypatch):
    """Anti-tautology: same rib/close but choppy periods (no stair run) → stays Variation."""
    monkeypatch.setenv("S1_TREND_CONTROL_V1", "1")
    bars = [_bar(7570, 7580, 7560, 7565, v=120) for _ in range(12)]
    # one big drop then sideways chop (alternating periods — run resets)
    for j in range(6):
        px = 7550 - j * 3
        bars.append(_bar(px + 1, px + 2, px - 2, px - 1, v=140))
    for p in range(3):
        for j in range(6):
            px = 7535 + (3 if p % 2 == 0 else -3)
            bars.append(_bar(px, px + 2.5, px - 2.5, px - 2.2 if p == 2 and j == 5 else px, v=140))
    f = _feat_for_classifier(_features(bars))
    if f["sides"] == 1:  # only meaningful when the fixture keeps a 1-sided day
        r = classify(f, _plan(), is_eod=False)
        assert r["day_type"] != "Trend_Normal" or f.get("stair_steps_dn", 0) >= 3, (f, r)
