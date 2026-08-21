"""S6_MAE_SCRATCH_V1 — MAE-based scratch tests (2026-08-02).

Tests:
1. Flag OFF → (False, "")
2. Flag ON + MAE < threshold → no scratch
3. Flag ON + MAE >= threshold → scratch with reason
4. Post-T1 → never scratch (BE handles it)
5. ZLR gets 6pt threshold (per-pattern override)
6. REACTIVE gets 12pt (default 8 × 1.5 responsive multiplier)

S6_MAE_SCRATCH_ATR_V1 — ATR-relative thresholds (2026-08-21):
7. Flag OFF → the `atr=` kwarg is inert; every fixed-path result is unchanged
8. k reproduces the fixed points on a median-ATR (6.0pt) day
9. #756's exact shape (1.8pt MAE, 3.5pt stop, ATR 8.07) is NOT scratched
10. a genuine structural failure (MAE large vs ATR) IS still scratched
11. dead-ATR day → the 4.0pt floor binds
12. ATR unavailable (0.0 / None) → honest fallback to the fixed path
"""
import os
import pytest

from backend.v9.systems.mae_scratch import (
    should_scratch, get_threshold, get_threshold_atr, compute_mae, reset_cache,
    reset_atr_cache,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # The ATR flag must be OFF for every legacy test — it is default-OFF in code
    # and must never leak in from a developer shell or the baseline conftest env.
    monkeypatch.delenv("S6_MAE_SCRATCH_ATR_V1", raising=False)
    reset_cache()
    reset_atr_cache()
    yield
    reset_cache()
    reset_atr_cache()


def test_flag_off(monkeypatch):
    monkeypatch.delenv("S6_MAE_SCRATCH_V1", raising=False)
    ok, reason = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7440.0, bar_high=7455.0)
    assert ok is False
    assert reason == ""


def test_mae_below_threshold(monkeypatch):
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    ok, reason = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7445.0, bar_high=7455.0)
    # MAE = 7450 - 7445 = 5 < 6 (ZLR threshold)
    assert ok is False


def test_mae_at_threshold(monkeypatch):
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    ok, reason = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7444.0, bar_high=7455.0)
    # MAE = 7450 - 7444 = 6 >= 6 (ZLR threshold)
    assert ok is True
    assert "MAE scratch" in reason
    assert "6.0pt" in reason


def test_post_t1_never_scratch(monkeypatch):
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    ok, _ = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7430.0, bar_high=7455.0, t1_hit=True)
    # 20pt MAE but post-T1 → no scratch
    assert ok is False


def test_zlr_threshold():
    assert get_threshold("ZLR") == 6.0
    assert get_threshold("ZLR_LONG") == 6.0  # stripped suffix


def test_reactive_threshold():
    # REACTIVE is in responsive_patterns → default 8 × 1.5 = 12
    assert get_threshold("REACTIVE") == 12.0
    assert get_threshold("REACTIVE_SHORT") == 12.0


def test_gb100_threshold():
    assert get_threshold("GB100") == 10.0


def test_unknown_pattern_default():
    assert get_threshold("UNKNOWN_PATTERN") == 8.0


def test_compute_mae_long():
    assert compute_mae(7450.0, "LONG", 7440.0, 7460.0) == 10.0
    assert compute_mae(7450.0, "LONG", 7455.0, 7460.0) == 0.0  # no adverse


def test_compute_mae_short():
    assert compute_mae(7450.0, "SHORT", 7440.0, 7460.0) == 10.0
    assert compute_mae(7450.0, "SHORT", 7440.0, 7445.0) == 0.0  # no adverse


# ───────────────────────── S6_MAE_SCRATCH_ATR_V1 (2026-08-21) ────────────────

# #756, 2026-08-20, the only live trade of the day: TREND_STEP SHORT 7696.75,
# stop 7700.25 (3.5pt), scratched at MAE 1.8pt because the P2-9 clamp squeezed
# the 8.0pt default down to stop_dist - gap = 1.5pt. ATR14 on that bar = 8.07.
T756 = dict(pattern_name="TREND_STEP", entry_price=7696.75, direction="SHORT",
            bar_low=7694.25, bar_high=7698.55, stop_price=7700.25)


def _cases():
    """The shapes used to prove flag-OFF is byte-identical."""
    return [
        dict(pattern_name="ZLR", entry_price=7450.0, direction="LONG",
             bar_low=7444.0, bar_high=7455.0),
        dict(pattern_name="ZLR", entry_price=7450.0, direction="LONG",
             bar_low=7445.0, bar_high=7455.0),
        dict(pattern_name="GB100", entry_price=7450.0, direction="SHORT",
             bar_low=7440.0, bar_high=7462.0),
        dict(pattern_name="REACTIVE_SHORT", entry_price=7450.0, direction="SHORT",
             bar_low=7440.0, bar_high=7463.0),
        dict(**T756),
        dict(pattern_name="ZLR", entry_price=7450.0, direction="LONG",
             bar_low=7440.0, bar_high=7455.0, stop_price=7443.0),
    ]


def test_atr_flag_off_is_byte_identical(monkeypatch):
    """Flag OFF: passing `atr=` must not change ANY outcome vs not passing it."""
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.delenv("S6_MAE_SCRATCH_ATR_V1", raising=False)
    for case in _cases():
        without = should_scratch(**case)
        for atr in (0.0, 3.0, 8.07, 25.0):
            assert should_scratch(atr=atr, **case) == without, (
                f"flag OFF must ignore atr={atr} for {case['pattern_name']}")


def test_atr_flag_off_mae_1_8_still_scratches_756(monkeypatch):
    """The regression baseline: today's live code DOES scratch #756 at 1.5pt."""
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.delenv("S6_MAE_SCRATCH_ATR_V1", raising=False)
    ok, reason = should_scratch(atr=8.07, **T756)
    assert ok is True
    assert "1.5pt threshold" in reason


def test_k_reproduces_fixed_points_on_median_atr_day():
    """k was DERIVED as fixed/6.0 (live-era median ATR14) — prove the identity."""
    median_atr = 6.0
    for pattern in ("ZLR", "GB100", "INITIATIVE_SHORT", "INITIATIVE_LONG",
                    "UNKNOWN_PATTERN", "REACTIVE_SHORT"):
        rel = get_threshold_atr(pattern, median_atr)
        fixed = get_threshold(pattern)
        assert abs(rel - fixed) < 0.01, (
            f"{pattern}: ATR path {rel:.3f} != fixed {fixed:.3f} on a median-ATR day")


def test_756_not_scratched_under_atr_flag(monkeypatch):
    """THE case Michael flagged: 1.8pt adverse on an 8pt-ATR bar is noise.

    The ATR threshold for TREND_STEP at ATR 8.07 is 1.3333*8.07 = 10.76pt, which
    cannot fit under a 3.5pt stop with the 2pt gap → skip, the stop protects.
    """
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.setenv("S6_MAE_SCRATCH_ATR_V1", "1")
    ok, reason = should_scratch(atr=8.07, **T756)
    assert ok is False
    assert reason == ""
    # and it stays unscratched at the ATR ~10 the day reached later
    assert should_scratch(atr=10.0, **T756)[0] is False


def test_structural_failure_still_scratched_under_atr_flag(monkeypatch):
    """Large MAE relative to ATR, with a stop wide enough to leave room → scratch."""
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.setenv("S6_MAE_SCRATCH_ATR_V1", "1")
    # ATR 6.0 → GB100 threshold 1.6667*6 = 10.0pt; stop 20pt away leaves 18pt room
    ok, reason = should_scratch(
        pattern_name="GB100", entry_price=7450.0, direction="SHORT",
        bar_low=7445.0, bar_high=7461.0, stop_price=7470.0, atr=6.0)
    assert ok is True                      # MAE 11.0 >= 10.0
    assert "ATR-relative" in reason and "ATR14=6.00" in reason
    # and post-T1 it still never fires
    assert should_scratch(
        pattern_name="GB100", entry_price=7450.0, direction="SHORT",
        bar_low=7445.0, bar_high=7461.0, stop_price=7470.0, atr=6.0,
        t1_hit=True)[0] is False


def test_dead_atr_day_floors(monkeypatch):
    """Dead-ATR day: the 4.0pt floor (1.25 x winners' median MAE 3.2) binds."""
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.setenv("S6_MAE_SCRATCH_ATR_V1", "1")
    # ATR 1.0 → ZLR raw k*ATR = 1.0pt, far below the winners' median MAE
    assert get_threshold_atr("ZLR", 1.0) == 4.0
    assert get_threshold_atr("UNKNOWN_PATTERN", 0.5) == 4.0
    # a 3.0pt excursion on a dead-ATR day must NOT scratch (floor is 4.0)
    ok, _ = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7447.0, bar_high=7452.0, stop_price=7435.0, atr=1.0)
    assert ok is False
    # 4.5pt does
    ok, reason = should_scratch(
        pattern_name="ZLR", entry_price=7450.0, direction="LONG",
        bar_low=7445.5, bar_high=7452.0, stop_price=7435.0, atr=1.0)
    assert ok is True and "4.0pt threshold" in reason


def test_atr_unavailable_falls_back_to_fixed(monkeypatch):
    """Rule 1 honest-zero: no ATR → the fixed path, not a synthesised value."""
    monkeypatch.setenv("S6_MAE_SCRATCH_V1", "1")
    monkeypatch.setenv("S6_MAE_SCRATCH_ATR_V1", "1")
    monkeypatch.setattr("backend.v9.systems.mae_scratch.current_atr14", lambda: 0.0)
    ok, reason = should_scratch(atr=0.0, **T756)
    assert ok is True                                  # identical to flag-OFF
    assert "1.5pt threshold" in reason and "ATR-relative" not in reason
    # atr=None with a dead DB resolves through current_atr14() to the same place
    assert should_scratch(**T756)[0] is True


def test_atr_flag_off_never_reads_the_db(monkeypatch):
    """current_atr14() must short-circuit to 0.0 with the flag OFF (no DB hit)."""
    from backend.v9.systems import mae_scratch as m
    monkeypatch.delenv("S6_MAE_SCRATCH_ATR_V1", raising=False)

    def _boom(*a, **k):
        raise AssertionError("DB was read with the ATR flag OFF")

    monkeypatch.setattr("backend.v9.db.read.read_all", _boom)
    assert m.current_atr14() == 0.0
