"""P31-STRAT-S3 #2 — AMT (Average Money Trade) is a 90-min rolling average.

Regression test for the fix that turned `_last_amt` from a per-bar instant
into a rolling window. Without rolling, S2 5-Min's `cot > amt` test compares
an accumulated COT to a single-bar number that bounces randomly between
0 and 300+, so S2 effectively never fires.

The 90-minute target is approximated by 18 tick_reversal bars (variable
length, but ~5 min each in normal flow).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from backend.v9.systems.footprint.footprint_system import FootprintSystem


def _bar(volume: float, trade_count: int, ask: float = 50.0, bid: float = 50.0) -> Dict[str, Any]:
    """Minimal bar payload — `_classify_forces_in_bar` requires `ask_vol` and
    `bid_vol` both non-None, else returns None and `_update_flow` exits early.
    Trade count comes from `trade_count` / `ticks_count` / `n`; volume from
    `v` / `volume`."""
    return {
        "ask_vol": ask,
        "bid_vol": bid,
        "v": volume,
        "trade_count": trade_count,
    }


@pytest.fixture
def fp() -> FootprintSystem:
    return FootprintSystem(db_path=":memory:")


def test_amt_window_starts_empty(fp: FootprintSystem) -> None:
    """Sanity: a fresh system has no AMT history yet."""
    assert fp._amt_window == []
    assert fp._AMT_WINDOW_BARS == 18


def test_amt_first_bar_is_just_per_bar_value(fp: FootprintSystem) -> None:
    """One bar in → AMT == per-bar AMT (no smoothing yet)."""
    fp._update_flow(_bar(volume=100, trade_count=10))
    assert fp._amt_window == [10.0]
    assert fp._last_amt == pytest.approx(10.0)


def test_amt_averages_across_window(fp: FootprintSystem) -> None:
    """Multiple bars with same per-bar AMT → rolling average is that constant."""
    for _ in range(5):
        fp._update_flow(_bar(volume=200, trade_count=20))
    assert len(fp._amt_window) == 5
    assert fp._last_amt == pytest.approx(10.0)


def test_amt_averages_mixed_values(fp: FootprintSystem) -> None:
    """3 bars, per-bar AMT = 5, 10, 15. Rolling avg = 10."""
    fp._update_flow(_bar(volume=50, trade_count=10))   # 5
    fp._update_flow(_bar(volume=100, trade_count=10))  # 10
    fp._update_flow(_bar(volume=150, trade_count=10))  # 15
    assert fp._amt_window == [5.0, 10.0, 15.0]
    assert fp._last_amt == pytest.approx(10.0)


def test_amt_window_caps_at_18_bars(fp: FootprintSystem) -> None:
    """Push 30 bars → window holds exactly the last 18, not 30."""
    for i in range(30):
        fp._update_flow(_bar(volume=100 * (i + 1), trade_count=10))
    assert len(fp._amt_window) == 18
    # The 30th bar is the last → per-bar AMT = 10 * 30 = 300.
    # Window holds bars 13..30 (per-bar AMT 130, 140, ..., 300).
    expected_avg = sum(10 * i for i in range(13, 31)) / 18
    assert fp._last_amt == pytest.approx(expected_avg)


def test_amt_smooths_a_zero_volume_bar(fp: FootprintSystem) -> None:
    """The original bug: a single quiet bar drove `_last_amt` to 0,
    which broke S2's `cot > amt` comparison.

    With rolling AMT, a zero bar drags the average toward 0 only slightly."""
    for _ in range(10):
        fp._update_flow(_bar(volume=200, trade_count=20))  # per-bar AMT = 10
    # Now a quiet bar
    fp._update_flow(_bar(volume=0, trade_count=1))  # per-bar AMT = 0
    # With rolling: avg of [10]*10 + [0] = 100/11 ≈ 9.09
    assert fp._last_amt == pytest.approx(100 / 11)
    # NOT 0 (which is what the old per-bar code returned)
    assert fp._last_amt > 5.0


def test_amt_handles_missing_volume_field(fp: FootprintSystem) -> None:
    """Bar without `v` field → total_vol=0 → per_bar_amt=0. The window
    still records it (the bar happened). Subsequent bars dilute it."""
    fp._update_flow({"ask_vol": 10.0, "bid_vol": 10.0})
    assert fp._amt_window == [0.0]
    fp._update_flow(_bar(volume=200, trade_count=20))  # per-bar AMT = 10
    assert fp._amt_window == [0.0, 10.0]
    assert fp._last_amt == pytest.approx(5.0)


def test_amt_reads_sierra_vol_field(fp: FootprintSystem) -> None:
    """Tick reversal bars from Sierra use 'vol', not 'v' or 'volume'.
    Regression test for P31-STRAT-S3 field-name fix (CC 2026-05-22)."""
    sierra_bar = {"ask_vol": 1043.0, "bid_vol": 1089.0, "vol": 2132.0, "trade_count": 15}
    fp._update_flow(sierra_bar)
    assert fp._last_amt == pytest.approx(2132.0 / 15)
    assert fp._last_amt > 0, "AMT must not be 0 when vol field is present"


def test_amt_skips_bars_with_no_classifiable_forces(fp: FootprintSystem) -> None:
    """If `_classify_forces_in_bar` returns None (no ask/bid volume),
    `_update_flow` exits early and the window is untouched."""
    # Reach state where the window has entries
    fp._update_flow(_bar(volume=200, trade_count=20))
    assert fp._amt_window == [10.0]

    # Now a bar with no flow signals at all — forces=None branch
    fp._update_flow({})
    # Window unchanged
    assert fp._amt_window == [10.0]
    assert fp._last_amt == pytest.approx(10.0)
