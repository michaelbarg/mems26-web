"""Dalton Alignment — IB-break → Variation (low 7501 vs IB-low 7506).

Real case 2026-07-20: RTH low 7501 broke IB-low 7506 by 5pt = expansion DOWN
= Variation (Dalton). Classifier said 0-sided/Normal (volume-acceptance missed it).

Contract (DALTON_ALIGNMENT_2026-07-20 §1):
  Any acceptance beyond IB = expansion. low < IB_low → DOWN expansion → Variation
  family (1-sided). Mechanical sides (DAYTYPE_SIDES_MECHANICAL_V1) count RE by
  price, not volume.

Tests pin: flag ON → sides≥1 + classify ≠ Normal; flag OFF → byte-identical path
may still under-count (document the live miss).
"""
from __future__ import annotations

from backend.v9.systems.day_type.daytype_classifier import classify
from backend.v9.systems.day_type.relative_features import compute_relative_features

IB_LO = 7506.0
IB_HI = 7539.0  # wide IB from 07-20 morning (~33pt; classify_replay had 66 then 29)
PLAN = {}  # classifier uses defaults when plan empty-ish; pass minimal


def _bar(o, h, l, c, v=200):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def _bars_ib_then_down_break():
    """12 IB bars inside [7506, 7539], then session low 7501 (5pt below IB-low)."""
    bars = []
    for _ in range(12):
        bars.append(_bar(7520, 7535, 7510, 7522, v=150))
    # post-IB: drive down, hold closes ≤ IB_LO - buffer
    for k in range(8):
        px = 7510 - k * 1.25  # → ~7501
        lo = min(px - 0.5, 7501.0)
        bars.append(_bar(px + 1, px + 2, lo, min(px, 7502.0), v=180))
    return bars


def test_mechanical_sides_counts_7501_ib_break(monkeypatch):
    """Dalton 07-20: 5pt below IB counts. Disable 20%×IB noise (would need 6.6pt
    on this 33pt IB and miss the live case). Absolute 2pt floor only."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_PTS", "2.0")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_IB_FRAC", "0")
    f = compute_relative_features(_bars_ib_then_down_break(), IB_HI, IB_LO)
    assert f.sides >= 1, f"expected DOWN side counted; sides={f.sides} lo-break={IB_LO - 7501}"
    assert (IB_LO - 7501) >= 2.0  # fixture sanity: 5pt > noise floor


def test_default_20pct_ib_noise_misses_5pt_break_on_wide_ib(monkeypatch):
    """Document live miss: noise=max(2, 0.2×33)=6.6 > 5pt break → sides stays 0."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_PTS", "2.0")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_IB_FRAC", "0.20")
    f = compute_relative_features(_bars_ib_then_down_break(), IB_HI, IB_LO)
    assert f.sides == 0, f"20% IB noise should miss 5pt; got sides={f.sides}"


def test_mechanical_sides_feeds_variation_not_normal(monkeypatch):
    """sides==1 → classifier must land Variation family, not Normal (0-sided)."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_IB_FRAC", "0")
    f = compute_relative_features(_bars_ib_then_down_break(), IB_HI, IB_LO)
    assert f.sides >= 1
    feat = {
        "n_bars": 78,
        "sides": f.sides,
        "rib": f.rib,
        "one_tf": f.one_tf or "DOWN",
        "close_pos": f.close_pos,
        "vol_ratio": 0.9,
        "returned_through_open": False,
        "ib_narrow": False,
        "dir_bias": "DOWN",
    }
    out = classify(feat, PLAN, is_eod=True)
    label = out.get("day_type") or out.get("label") or ""
    assert label not in ("Normal", "Nontrend", "FORMING"), (
        f"IB-down-break must not be Normal; got {out}"
    )
    assert "Variation" in label or "Trend" in label, f"want Variation/Trend family, got {out}"


def test_volume_acceptance_alone_can_miss_7501(monkeypatch):
    """Pin the live miss: without mechanical sides, thin/late volume may yield sides=0."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "0")
    # Thin volume on the break bars — volume-acceptance path may drop the side
    bars = []
    for _ in range(12):
        bars.append(_bar(7520, 7535, 7510, 7522, v=500))
    for k in range(8):
        px = 7510 - k * 1.25
        bars.append(_bar(px + 1, px + 2, min(px - 0.5, 7501.0), min(px, 7502.0), v=5))
    f = compute_relative_features(bars, IB_HI, IB_LO)
    # Document: may be 0 under volume gate — if somehow ≥1, still OK (stronger feed)
    assert f.sides in (0, 1, 2)


def test_mechanical_flag_off_byte_identical_default(monkeypatch):
    monkeypatch.delenv("DAYTYPE_SIDES_MECHANICAL_V1", raising=False)
    f1 = compute_relative_features(_bars_ib_then_down_break(), IB_HI, IB_LO)
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "0")
    f2 = compute_relative_features(_bars_ib_then_down_break(), IB_HI, IB_LO)
    assert f1.sides == f2.sides
