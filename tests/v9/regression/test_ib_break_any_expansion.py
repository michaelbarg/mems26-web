"""Task#5: IB_BREAK_ANY_EXPANSION_V1 — any price beyond IB = expansion = Variation.

Real case 2026-07-20: RTH low 7501 broke IB low 7506 by 5pt. Classifier said
Normal (0-sided) because noise floor = max(2pt, 20%×40pt IB) = 8pt > 5pt.
Dalton rule: ANY acceptance beyond IB = expansion → at minimum Variation.

Fix: IB_BREAK_ANY_EXPANSION_V1 sets noise floor = fixed pts only (no IB-frac
gate), so 5pt > 2pt → counts as a side → Variation.

Anti-tautological:
  1. Flag ON + 5pt break on 40pt IB → sides=1 → Variation
  2. Flag OFF + same bars → sides=0 → Normal (legacy)
"""
import os
import pytest


def test_flag_on_5pt_break_counts_as_side(monkeypatch):
    """5pt break on 40pt IB: flag ON → sides=1 (noise=2pt, 5>2)."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.setenv("IB_BREAK_ANY_EXPANSION_V1", "1")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_PTS", "2.0")

    from backend.v9.systems.day_type.relative_features import compute_relative_features

    # IB: high 7546, low 7506 (IB width = 40pt)
    # Post-IB: price breaks DOWN to 7501 = 5pt below IB_low 7506
    bars = []
    for i in range(12):
        bars.append({"o": 7520, "h": 7546, "l": 7506, "c": 7520, "v": 500})
    for i in range(12):
        bars.append({"o": 7504, "h": 7510, "l": 7501, "c": 7502, "v": 400})

    f = compute_relative_features(
        bars, ib_bars=12, bars_per_30min=6,
        ib_high=7546, ib_low=7506,
    )
    # With flag ON: noise = 2pt (fixed only, no IB-frac). 5pt > 2pt → side counted
    assert f.sides >= 1, f"Expected sides>=1 (5pt break > 2pt noise), got {f.sides}"


def test_flag_off_5pt_break_not_counted(monkeypatch):
    """5pt break on 40pt IB: flag OFF → noise=8pt → sides=0 (legacy)."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.delenv("IB_BREAK_ANY_EXPANSION_V1", raising=False)
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_PTS", "2.0")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_IB_FRAC", "0.20")

    from backend.v9.systems.day_type.relative_features import compute_relative_features

    bars = []
    for i in range(12):
        bars.append({"o": 7520, "h": 7546, "l": 7506, "c": 7520, "v": 500})
    for i in range(12):
        bars.append({"o": 7504, "h": 7510, "l": 7501, "c": 7502, "v": 400})

    f = compute_relative_features(
        bars, ib_bars=12, bars_per_30min=6,
        ib_high=7546, ib_low=7506,
    )
    # Without flag: noise = max(2, 0.20×40) = 8pt. 5pt < 8pt → not counted
    assert f.sides == 0, f"Expected sides=0 (5pt < 8pt noise), got {f.sides}"


def test_large_break_counts_both_ways(monkeypatch):
    """A 10pt break always counts (> 8pt noise) regardless of flag."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.delenv("IB_BREAK_ANY_EXPANSION_V1", raising=False)

    from backend.v9.systems.day_type.relative_features import compute_relative_features

    bars = []
    for i in range(12):
        bars.append({"o": 7520, "h": 7546, "l": 7506, "c": 7520, "v": 500})
    # 10pt break below IB
    for i in range(12):
        bars.append({"o": 7495, "h": 7500, "l": 7496, "c": 7498, "v": 400})

    f = compute_relative_features(
        bars, ib_bars=12, bars_per_30min=6,
        ib_high=7546, ib_low=7506,
    )
    # 10pt break (7506-7496=10) > 8pt noise → counts even without flag
    assert f.sides >= 1
