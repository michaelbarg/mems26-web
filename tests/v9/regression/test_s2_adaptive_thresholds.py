"""S2_ADAPTIVE_THRESHOLDS_V1 — adaptive S2 thresholds (Michael 2026-08-19 ~19:15).

Ruling: "לשלוח סוכן שיבצע התאמה לספים בהתאם לגודל הנר וסוג היום... אני רוצה
פיתרון חכם שמותאם לסוג היום ולגודל הנרות — זה יחסי בסוף".

Audit finding (2026-08-19): INITIATIVE's expansion floor (1.3×avg14) demanded
~7.5pt while the day's real closed-bar ranges ran 1.5-4.5pt (open bars inflate
the mean) — unreachable. REACTIVE's b2 volume gate demanded ≤10% of b1 (a 90%
drop) — near-impossible.

Under the flag:
  expansion: b1 range ≥ max(P80 of last-20 closed-bar ranges, 0.55×ATR14),
             ×0.85 on Trend*/Variation day types (None/UNKNOWN → ×1.0).
  b2 drop:   b2_vol < b1_vol AND b2_vol ≤ 0.8×avg20 (VSA-style, relative).

Flag OFF (default) MUST stay byte-identical to the legacy behavior.
"""
import pytest

from backend.v9.systems.five_min.five_min_system import (
    DROP_THRESHOLD_PCT,
    FiveMinSystem,
    _EXPANSION_MIN_K,
    adaptive_daytype_mult,
    adaptive_expansion_floor,
    get_expansion_range,
)

_S2_ENV_FLAGS = (
    "S2_ADAPTIVE_THRESHOLDS_V1", "S2_VSA_VOLUME", "S2_REQUIRE_COT_AMT",
    "S2_VOL_ADAPTIVE", "S2_CVD_DETECTION_V1", "S2_B4_VOL_V1", "S2_DETECTION_LOG",
)


def _clean_env(monkeypatch):
    for f in _S2_ENV_FLAGS:
        monkeypatch.delenv(f, raising=False)


def _sys_no_footprint(day_type=None):
    """FiveMinSystem with footprint (S3) fully unavailable — COT/AMT/belly None."""
    s = FiveMinSystem()
    s._get_cot_from_footprint = lambda: None
    s._get_amt_from_footprint = lambda: None
    s._get_belly_from_footprint = lambda: None
    s._get_belly_ratio_from_footprint = lambda d: None
    s._poc_vol_rising = lambda b: False
    s._poc_vol_falling = lambda b: False
    s.current_day_type = day_type
    return s


def _bar(o, h, l, c, v):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def _initiative_long_bars(b1_range: float):
    """20 closed bars shaped like 2026-08-19: mostly 1.5-4.5pt ranges (avg ~3
    ex-outliers) with three 9pt 'open' bars inside the last-14 window — the
    exact shape that inflates avg14 (old floor ≈5.6pt, unreachable) while the
    P80 of the last-20 ranges stays 4.5.
    """
    P = 7700.0
    bars = []
    # 6 quiet bars (outside the old avg14 window)
    for rng in (2.0, 2.5, 3.0, 2.0, 2.5, 3.0):
        bars.append(_bar(P, P + rng, P, P + 0.5, 100))
    # 3 big "open" bars — inside the last-14 window (mean-inflators)
    for _ in range(3):
        bars.append(_bar(P + 1.0, P + 9.0, P, P + 8.0, 100))
    # 7 grind bars (indices 9-15; 13-15 are the Pkg-2bc lookback → quiet vol)
    for _ in range(7):
        bars.append(_bar(P + 0.5, P + 2.5, P, P + 2.0, 100))
    # b1: the expansion candidate (range parameterized), bull, volume spike
    bars.append(_bar(P + 0.25, P + b1_range, P, P + b1_range - 0.25, 1000))
    # b2: test — higher low, small range
    bars.append(_bar(P + 1.5, P + 2.0, P + 0.5, P + 1.0, 300))
    # b3: joining — range 5.0 > any tested b1_range
    bars.append(_bar(P + 1.0, P + 5.5, P + 0.5, P + 5.0, 600))
    # b4: second test + entry: l ≥ b2.l, close above b1 high (range 4.5)
    bars.append(_bar(P + 1.5, P + 5.5, P + 1.0, P + 5.25, 700))
    return bars


def _reactive_long_bars(b2_vol: float):
    """3 quiet lookback bars + valid Reactive-LONG geometry; b2 vol param.

    avg20 (rolling, bars[:-3]) = mean(500, 500, 500, 1000) = 625.
    """
    pad = [_bar(5250, 5251, 5249, 5250, 500) for _ in range(3)]
    setup = [
        _bar(5250, 5250, 5247, 5247.5, 1000),        # b1 sellers, vol spike
        _bar(5248, 5248, 5247, 5247.75, b2_vol),     # b2 volume dry-up
        _bar(5247.25, 5249, 5247.25, 5248.75, 800),  # b3 buyers
        _bar(5248.5, 5250, 5248.5, 5249.75, 700),    # b4 confirm > b3 high
    ]
    return pad + setup


# ── Flag OFF — byte-identical legacy behavior ──────────────────────────────


def test_off_initiative_old_floor_unreachable(monkeypatch):
    """Flag OFF: today's shape keeps the OLD 1.3×avg14 gate — 4.5pt bar blocked."""
    _clean_env(monkeypatch)
    bars = _initiative_long_bars(4.5)
    lo, hi = get_expansion_range(bars)
    assert lo > 4.5, f"fixture must reproduce the unreachable old floor (lo={lo:.2f})"
    direction, conf, info = _sys_no_footprint()._detect_initiative(bars)
    assert direction is None, "flag OFF must keep the legacy (blocking) expansion gate"


def test_off_reactive_legacy_gate_unchanged(monkeypatch):
    """Flag OFF: b2 ≤ 10%×b1 still governs — 437.5 blocked, 80 fires."""
    _clean_env(monkeypatch)
    sys_ = _sys_no_footprint()
    d1, _, _ = sys_._detect_reactive(_reactive_long_bars(437.5))
    assert d1 is None, "flag OFF: b2=437.5 > 10% of b1 must NOT fire (legacy gate)"
    d2, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(80))
    assert d2 == "LONG", "flag OFF: the legacy 90%-drop pass must keep firing"


def test_legacy_constants_untouched():
    """Litmus: the legacy thresholds themselves were not edited."""
    assert _EXPANSION_MIN_K == 1.3
    assert DROP_THRESHOLD_PCT == 0.10


# ── Flag ON — adaptive expansion (INITIATIVE) ──────────────────────────────


def test_on_expansion_4_5pt_passes_2pt_fails(monkeypatch):
    """Flag ON, today's shape (ranges ~1.5-4.5, avg ~3): 4.5pt bar passes the
    adaptive floor (P80=4.5) while a 2pt bar fails."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("S2_ADAPTIVE_THRESHOLDS_V1", "1")
    d_pass, conf, info = _sys_no_footprint()._detect_initiative(_initiative_long_bars(4.5))
    assert d_pass == "LONG" and info.get("kind") == "INITIATIVE", (
        "adaptive floor must make a 4.5pt expansion bar fire on a 1.5-4.5pt day"
    )
    d_fail, _, _ = _sys_no_footprint()._detect_initiative(_initiative_long_bars(2.0))
    assert d_fail is None, "a 2pt bar is not an expansion — must still be blocked"


def test_on_expansion_floor_formula():
    """floor = max(P80 of last-20 ranges, 0.55×ATR14) × day-type multiplier."""
    bars = _initiative_long_bars(4.5)
    assert adaptive_expansion_floor(bars) == pytest.approx(4.5)          # P80 term
    assert adaptive_expansion_floor(bars, atr14=10.0) == pytest.approx(5.5)  # ATR binds
    flat = [_bar(7700, 7701, 7700, 7700.5, 100)] * 20                    # all-1pt tape
    assert adaptive_expansion_floor(flat, atr14=10.0) == pytest.approx(5.5)
    assert adaptive_expansion_floor(flat) == pytest.approx(1.0)          # ATR None → P80 only
    assert adaptive_expansion_floor([]) is None
    assert adaptive_expansion_floor(None) is None


def test_daytype_multiplier():
    """Trend*/Variation → ×0.85; None/UNKNOWN/others → neutral ×1.0."""
    for dt in ("Trend_Normal", "Trend_DD", "Variation", "Normal_Variation"):
        assert adaptive_daytype_mult(dt) == 0.85, dt
    for dt in (None, "UNKNOWN", "Normal", "Neutral_Extreme", "Neutral_Center", "Nontrend", ""):
        assert adaptive_daytype_mult(dt) == 1.0, dt
    bars = _initiative_long_bars(4.5)
    assert adaptive_expansion_floor(bars, day_type="Trend_Normal") == pytest.approx(0.85 * 4.5)


def test_on_trend_day_relaxes_expansion(monkeypatch):
    """Flag ON: a 4.0pt bar fails at ×1.0 (floor 4.5) but passes on a
    Trend day (floor 4.5×0.85=3.825) — the day-type wire is live."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("S2_ADAPTIVE_THRESHOLDS_V1", "1")
    bars = _initiative_long_bars(4.0)
    d_neutral, _, _ = _sys_no_footprint(day_type=None)._detect_initiative(bars)
    assert d_neutral is None
    d_unknown, _, _ = _sys_no_footprint(day_type="UNKNOWN")._detect_initiative(bars)
    assert d_unknown is None, "UNKNOWN must behave as neutral ×1.0"
    d_trend, _, info = _sys_no_footprint(day_type="Trend_Normal")._detect_initiative(bars)
    assert d_trend == "LONG" and info.get("kind") == "INITIATIVE"


# ── Flag ON — adaptive b2 volume drop (REACTIVE) ───────────────────────────


def test_on_reactive_vsa_variant(monkeypatch):
    """Flag ON: b2 < b1 AND b2 ≤ 0.8×avg20 — b2=0.7×avg20 (437.5 of 625) fires."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("S2_ADAPTIVE_THRESHOLDS_V1", "1")
    d, conf, info = _sys_no_footprint()._detect_reactive(_reactive_long_bars(437.5))
    assert d == "LONG" and info.get("kind") == "REACTIVE", (
        "adaptive VSA-style drop (b2<b1 AND b2≤0.8×avg20) must fire on b2=0.7×avg20"
    )
    # a 90%-drop bar remains valid under the adaptive gate (superset of legacy)
    d2, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(80))
    assert d2 == "LONG"


def test_on_reactive_rejects_loud_b2(monkeypatch):
    """Flag ON: b2 louder than 0.8×avg20 (or ≥ b1) is NOT a dry-up."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("S2_ADAPTIVE_THRESHOLDS_V1", "1")
    d, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(600))
    assert d is None, "b2=600 > 0.8×avg20 (500) must not count as a volume drop"
    d2, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(1000))
    assert d2 is None, "b2 == b1 vol must not count as a volume drop"


def test_on_vsa_volume_flag_precedence(monkeypatch):
    """S2_VSA_VOLUME=1 keeps its own variant machinery — adaptive only replaces
    the legacy 10% branch (no interaction between the flags)."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("S2_ADAPTIVE_THRESHOLDS_V1", "1")
    monkeypatch.setenv("S2_VSA_VOLUME", "1")
    # Under the config-selected variant (UNION today), _vsa_pass requires
    # b2 < b0 (500) and b2 ≤ 0.7×avg20 (~437.49 in float) → use 400.
    # The point: no exception/regression when both flags are on.
    d, _, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars(400))
    assert d == "LONG"
