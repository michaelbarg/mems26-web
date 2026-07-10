"""FIX-14 — mechanical Range-Extension side counting (DAYTYPE_SIDES_MECHANICAL_V1).

Michael doctrine ruling 2026-07-10 (Dalton pp.27-29): Neutral = a messy day
with a breakout on BOTH sides — sides are counted MECHANICALLY by RE beyond
the IB; volume acceptance belongs to reclassification (accepted_break), not
to counting. Noise floor: an extension counts when >= max(2pt, 20% x IB).

Calibration pair (real days, real IB/extremes from the DB):
  2026-07-10: IB 7583.75-7589 (5.25pt), low 7552.25 (-31.5), high 7617 (+28).
      Live engine said sides=1 -> Variation conf 18 (the up side failed the
      8% volume-acceptance). Mechanically sides=2 -> Neutral.
  2026-07-09: IB 37pt wide, up-drive accepted, down poke 3pt (8% of IB).
      3 < max(2, 7.4) -> down NOT counted -> sides stays 1 (Variation family).

The classifier maps sides==2 -> Neutral_Center/Extreme by close position
(daytype_classifier.py:224) — feature-level tests cover the counting change.
"""
from backend.v9.systems.day_type.relative_features import compute_relative_features


def _bar(o, h, l, c, v=None):
    b = {"o": o, "h": h, "l": l, "c": c}
    if v is not None:
        b["v"] = v
    return b


# ── 07-10 fixture: IB 7583.75-7589, dn to 7552.25, up to 7617 ────────────────

IB_LO_0710, IB_HI_0710 = 7583.75, 7589.0


def _bars_0710():
    bars = []
    # 12 IB bars inside the (narrow) IB, moderate volume
    for i in range(12):
        bars.append(_bar(7585, 7589, 7583.75, 7586, v=100))
    # heavy down leg: closes hold far below IB-low (the accepted side)
    for k in range(10):
        px = 7575 - k * 2.5  # 7575 .. 7552.5
        bars.append(_bar(px + 1, px + 2, max(7552.25, px - 1), px, v=200))
    # recovery + evening up leg above IB-high — closes hold, but THIN volume
    # (v_above ≈ 90 of ~3390 session ≈ 2.7% < 8% acceptance → old code: not a side)
    for k in range(6):
        px = 7605 + k * 2  # 7605..7615, tp > 7589
        h = 7617 if k == 5 else px + 1.5
        bars.append(_bar(px - 1, h, px - 2, px, v=15))
    return bars


def test_0710_old_counting_misses_the_up_side(monkeypatch):
    """Reproduces the live bug: volume-acceptance kills the up side → sides=1."""
    monkeypatch.delenv("DAYTYPE_SIDES_MECHANICAL_V1", raising=False)
    f = compute_relative_features(_bars_0710(), IB_HI_0710, IB_LO_0710)
    assert f.sides == 1, f.as_dict()


def test_0710_mechanical_counts_both_sides(monkeypatch):
    """FIX-14: 31.5pt down + 28pt up on a 5.25 IB → noise max(2,1.05)=2 → sides=2."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    f = compute_relative_features(_bars_0710(), IB_HI_0710, IB_LO_0710)
    assert f.sides == 2, f.as_dict()
    # acceptance stays available for reclass: accepted_break inputs unchanged
    assert f.ext_dn_hold is True and f.ext_up_hold is False, f.as_dict()


# ── 07-09 fixture: IB 37pt, up-drive accepted, 3pt down poke ─────────────────

IB_LO_0709, IB_HI_0709 = 7540.0, 7577.0


def _bars_0709():
    bars = []
    for i in range(12):
        bars.append(_bar(7560, 7577, 7540, 7562, v=100))
    # one thin 3pt poke below IB-low, single close (no hold, no volume)
    bars.append(_bar(7542, 7543, 7537.0, 7539, v=10))
    # sustained accepted up-drive above IB-high
    for k in range(10):
        px = 7580 + k * 2  # 7580..7598
        bars.append(_bar(px - 1, px + 1.5, px - 2, px, v=150))
    return bars


def test_0709_noise_floor_rejects_3pt_poke(monkeypatch):
    """3pt < max(2, 0.2×37=7.4) → down NOT counted → sides=1 (Variation family)."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    f = compute_relative_features(_bars_0709(), IB_HI_0709, IB_LO_0709)
    assert f.sides == 1, f.as_dict()


def test_0709_flag_off_unchanged(monkeypatch):
    """Default: behavior byte-identical to the old counting."""
    monkeypatch.delenv("DAYTYPE_SIDES_MECHANICAL_V1", raising=False)
    f = compute_relative_features(_bars_0709(), IB_HI_0709, IB_LO_0709)
    assert f.sides == 1, f.as_dict()  # up accepted, down poke never held


def test_noise_floor_param_override(monkeypatch):
    """Raising the pts floor above both extensions kills both sides."""
    monkeypatch.setenv("DAYTYPE_SIDES_MECHANICAL_V1", "1")
    monkeypatch.setenv("DAYTYPE_SIDES_NOISE_PTS", "50")
    f = compute_relative_features(_bars_0710(), IB_HI_0710, IB_LO_0710)
    assert f.sides == 0, f.as_dict()
    monkeypatch.delenv("DAYTYPE_SIDES_NOISE_PTS", raising=False)
