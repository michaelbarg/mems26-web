"""S6_MAE_SCRATCH_V1 — MAE-based scratch tests (2026-08-02).

Tests:
1. Flag OFF → (False, "")
2. Flag ON + MAE < threshold → no scratch
3. Flag ON + MAE >= threshold → scratch with reason
4. Post-T1 → never scratch (BE handles it)
5. ZLR gets 6pt threshold (per-pattern override)
6. REACTIVE gets 12pt (default 8 × 1.5 responsive multiplier)
"""
import os
import pytest

from backend.v9.systems.mae_scratch import (
    should_scratch, get_threshold, compute_mae, reset_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_cache()
    yield
    reset_cache()


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
