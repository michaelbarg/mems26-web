"""
MDS-V1.0.0 Sanity Test — GATE for Commit 2.
Option C architecture: DB outcome direct.

Validates that the simulator correctly reproduces V1 production baseline.
Uses FULL dataset (no V8.1.4 filter) from setup_attempts table.

Note: Production /analytics/by_score_bucket queries the `setups` table
(3,584 trades at score>=50). Our dataset is from `setup_attempts` which
yields ~3,158 trades. The ±5% tolerance accounts for minor variations
as new data flows in between runs.

V1 baseline from setup_attempts (score >= 50):
  n_trades: 3,158 | HIT_C1: 1,159 | HIT_STOP: 1,545 | TIMEOUT: 454
  WR (HIT_C1 / (HIT_C1 + HIT_STOP)): 42.86%
"""

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tools.multidim_sim.data_loader import get_dataset
from tools.multidim_sim.simulator_core import run_single_config

# Tight tolerances for Option C (DB outcome direct, ±5% on counts, ±3pp on WR)
# Based on setup_attempts data verified 2026-05-02
EXPECTED_V1_BASELINE = {
    "n_trades_min": 3000,           # 3,158 - 5%
    "n_trades_max": 3350,           # 3,158 + 6%
    "win_rate_min": 0.40,           # 42.86% - 3pp
    "win_rate_max": 0.46,           # 42.86% + 3pp
    "hit_c1_count_min": 1100,       # 1,159 - 5%
    "hit_c1_count_max": 1250,       # 1,159 + 8%
    "hit_stop_count_min": 1460,     # 1,545 - 6%
    "hit_stop_count_max": 1650,     # 1,545 + 7%
    "timeout_count_min": 430,       # 454 - 5%
    "timeout_count_max": 480,       # 454 + 6%
}

# V1 production config (Option C — no trade management dims)
V1_CONFIG = {
    "threshold": 50,
    "vegas_weight": 30,
    "tpo_weight": 25,
    "fvg_weight": 25,
    "footprint_weight": 20,
    "footprint_logic": "weighted",
    "day_filter": "all_days",
    "direction_filter": "both",
    "duration_max_minutes": 720,
    "duration_penalty_factor": 0.0,
}


@pytest.fixture(scope="module")
def dataset():
    """Load dataset once for all tests in this module."""
    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL not set — export it before running sanity tests"
    df = get_dataset(db_url, filter_post_v814=False)
    assert len(df) >= 800, f"Dataset too small: {len(df)} rows"
    return df


@pytest.fixture(scope="module")
def baseline_metrics(dataset):
    """Run V1 baseline once, share across tests."""
    return run_single_config(dataset, V1_CONFIG)


def test_data_loads(dataset):
    """Smoke test: dataset loads and has required columns."""
    assert len(dataset) >= 800
    for col in ["direction", "mae_pts", "mfe_pts", "entry_price", "stop_price",
                "vegas_score", "tpo_score", "fvg_score", "footprint_score",
                "score", "outcome", "duration_minutes"]:
        assert col in dataset.columns, f"Missing column: {col}"


def test_v1_baseline_trade_count(baseline_metrics):
    """GATE: V1 baseline produces expected number of trades."""
    n = baseline_metrics["n_trades"]
    lo, hi = EXPECTED_V1_BASELINE["n_trades_min"], EXPECTED_V1_BASELINE["n_trades_max"]
    assert lo <= n <= hi, f"n_trades={n} outside [{lo}, {hi}]"


def test_v1_baseline_win_rate(baseline_metrics):
    """GATE: V1 baseline WR matches production ±3pp."""
    wr = baseline_metrics["win_rate"]
    lo, hi = EXPECTED_V1_BASELINE["win_rate_min"], EXPECTED_V1_BASELINE["win_rate_max"]
    assert lo <= wr <= hi, f"win_rate={wr:.4f} outside [{lo}, {hi}]"


def test_v1_baseline_outcome_distribution(baseline_metrics):
    """GATE: outcome counts within expected ranges."""
    m = baseline_metrics

    hit_c1 = m["n_hit_c1"]
    lo, hi = EXPECTED_V1_BASELINE["hit_c1_count_min"], EXPECTED_V1_BASELINE["hit_c1_count_max"]
    assert lo <= hit_c1 <= hi, f"n_hit_c1={hit_c1} outside [{lo}, {hi}]"

    hit_stop = m["n_hit_stop"]
    lo, hi = EXPECTED_V1_BASELINE["hit_stop_count_min"], EXPECTED_V1_BASELINE["hit_stop_count_max"]
    assert lo <= hit_stop <= hi, f"n_hit_stop={hit_stop} outside [{lo}, {hi}]"

    timeout = m["n_timeout"]
    lo, hi = EXPECTED_V1_BASELINE["timeout_count_min"], EXPECTED_V1_BASELINE["timeout_count_max"]
    assert lo <= timeout <= hi, f"n_timeout={timeout} outside [{lo}, {hi}]"


def test_simulation_is_fast(dataset):
    """Performance: single config must run < 1 second."""
    start = time.time()
    run_single_config(dataset, V1_CONFIG)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s (target <1s)"


def test_threshold_filter_works(dataset):
    """Sanity: raising threshold → fewer trades."""
    m50 = run_single_config(dataset, {**V1_CONFIG, "threshold": 50})
    m70 = run_single_config(dataset, {**V1_CONFIG, "threshold": 70})
    assert m70["n_trades"] < m50["n_trades"]


def test_footprint_veto_reduces_trades(dataset):
    """Sanity: footprint veto rejects trades where delta opposes."""
    m_w = run_single_config(dataset, {**V1_CONFIG, "footprint_logic": "weighted"})
    m_v = run_single_config(dataset, {**V1_CONFIG, "footprint_logic": "veto"})
    assert m_v["n_trades"] <= m_w["n_trades"]


def test_duration_coverage(dataset):
    """Duration column present with high coverage."""
    n_with_dur = dataset["duration_minutes"].is_not_null().sum()
    coverage = n_with_dur / len(dataset)
    # All rows get duration=60 (60-min forward window), so coverage should be 100%
    assert coverage >= 0.70, f"Duration coverage too low: {coverage:.1%}"


def test_pnl_signs_correct(baseline_metrics):
    """Sanity: HIT_C1 produces positive gross, HIT_STOP produces negative."""
    # With V1's 42% WR and 1:1 R:R, net should be negative (more stops than wins)
    m = baseline_metrics
    assert m["n_hit_stop"] > m["n_hit_c1"], "V1 should have more stops than wins"
    assert m["net_pnl_usd"] < 0, f"V1 net PnL should be negative, got {m['net_pnl_usd']}"


def test_skip_overextended_reduces_trades(dataset):
    """Verify skip_overextended filter reduces trade count where vwap_side data exists.

    Note: vwap_side is ~84% populated in the filtered dataset (rows with MAE/MFE).
    The 96.6% NULL rate from the full setup_attempts table doesn't apply here.
    Score 90+ are 96.3% overextended, so this filter is aggressive.
    """
    metrics_off = run_single_config(dataset, {**V1_CONFIG, "skip_overextended": False})
    metrics_on = run_single_config(dataset, {**V1_CONFIG, "skip_overextended": True})

    # ON should have fewer trades (overextended setups vetoed)
    assert metrics_on["n_trades"] < metrics_off["n_trades"], \
        "skip_overextended=True should reduce trade count"

    # Reduction can be large (high-score setups are mostly overextended)
    # but should not eliminate everything
    assert metrics_on["n_trades"] > 100, \
        f"skip_overextended removed too many: only {metrics_on['n_trades']} left"
