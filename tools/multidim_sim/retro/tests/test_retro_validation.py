"""
Retro-Runner validation — compare retro outcomes to Worker's known outcomes.

Resolution difference: Retro uses tick-level data (.scid), Worker used
3-minute bar OHLC. Asymmetric mismatches expected (Worker conservatively
over-counts STOP when price briefly touched T1 within a bar).
"""

import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from tools.multidim_sim.retro.outcome_calculator import compute_outcome
from tools.multidim_sim.retro.scid_reader import ScidReader, get_default_scid_path


def _get_known_setups_balanced(database_url: str, per_outcome: int = 10) -> list:
    """
    Get balanced sample from each Worker outcome.
    Derives outcome from t1_hit_ts/stop_hit_ts (outcome column is NULL).
    Cross-matches setups ↔ setup_attempts by ts + direction + entry price.
    """
    conn = psycopg2.connect(
        database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgres://") else database_url
    )
    cur = conn.cursor()

    # Get CLOSED setups with their matched setup_attempts entry/stop/c1
    cur.execute("""
        SELECT
            s.setup_id, s.first_detected_ts, s.closed_ts,
            s.t1_hit_ts, s.stop_hit_ts,
            s.initial_entry, s.initial_stop, s.c1_target, s.direction,
            s.mae_pts, s.mfe_pts
        FROM setups s
        WHERE s.status = 'CLOSED'
          AND s.closed_ts IS NOT NULL
          AND s.initial_entry IS NOT NULL
          AND s.initial_entry > 0
          AND s.initial_stop IS NOT NULL
          AND s.c1_target IS NOT NULL
        ORDER BY s.first_detected_ts DESC
    """)

    by_outcome = {"HIT_C1": [], "HIT_STOP": [], "TIMEOUT": []}

    for r in cur.fetchall():
        # Derive outcome from hit timestamps
        if r[4] is not None:  # stop_hit_ts
            derived = "HIT_STOP"
        elif r[3] is not None:  # t1_hit_ts
            derived = "HIT_C1"
        else:
            derived = "TIMEOUT"

        if len(by_outcome.get(derived, [])) >= per_outcome:
            continue

        by_outcome[derived].append({
            "setup_id": r[0],
            "first_detected_ts": r[1],
            "closed_ts": r[2],
            "expected_outcome": derived,
            "entry_price": float(r[5]),
            "stop_price": float(r[6]),
            "c1_target": float(r[7]),
            "direction": r[8],
            "expected_mae": float(r[9]) if r[9] else 0,
            "expected_mfe": float(r[10]) if r[10] else 0,
        })

    cur.close()
    conn.close()

    all_setups = []
    for outcome, setups in by_outcome.items():
        all_setups.extend(setups)

    return all_setups


@pytest.fixture(scope="module")
def scid_reader():
    return ScidReader(get_default_scid_path())


# ── Unit Tests ─────────────────────────────────────────────────────────────

def test_scid_reader_basics(scid_reader):
    """Verify .scid file can be read and contains recent data."""
    assert scid_reader.n_records > 1_000_000
    ticks = scid_reader.read_ticks_after(1777600000, max_minutes=1)
    assert len(ticks) > 0, "No ticks found for May 1 2026"
    assert ticks[0]["high"] < 10000, f"Price not scaled: {ticks[0]['high']}"


def test_scid_price_scaling(scid_reader):
    """Verify prices are in correct range (÷100 applied)."""
    ticks = scid_reader.read_ticks_after(1777665600, max_minutes=1)
    assert len(ticks) > 0
    # MES prices should be in 6000-8000 range
    assert 6000 < ticks[0]["high"] < 8000, f"Bad price: {ticks[0]['high']}"


def test_outcome_calculator_long_hit_stop():
    """LONG trade hits stop when low <= stop_price."""
    entry_ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    ticks = [
        {"ts": datetime(2026, 5, 1, 12, 0, 1, tzinfo=timezone.utc),
         "high": 7250.0, "low": 7248.0, "close": 7249.0, "volume": 1},
        {"ts": datetime(2026, 5, 1, 12, 0, 2, tzinfo=timezone.utc),
         "high": 7249.0, "low": 7244.0, "close": 7245.0, "volume": 1},
    ]
    result = compute_outcome(ticks, entry_ts, 7250.0, 7245.0, 7255.0, "LONG")
    assert result["outcome"] == "HIT_STOP"
    assert result["pnl_pts"] == -5.0


def test_outcome_calculator_short_hit_c1():
    """SHORT trade hits C1 when low <= c1_target."""
    entry_ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    ticks = [
        {"ts": datetime(2026, 5, 1, 12, 0, 1, tzinfo=timezone.utc),
         "high": 7252.0, "low": 7248.0, "close": 7249.0, "volume": 1},
        {"ts": datetime(2026, 5, 1, 12, 0, 2, tzinfo=timezone.utc),
         "high": 7249.0, "low": 7244.0, "close": 7244.0, "volume": 1},
    ]
    result = compute_outcome(ticks, entry_ts, 7250.0, 7255.0, 7245.0, "SHORT")
    assert result["outcome"] == "HIT_C1"
    assert result["pnl_pts"] == 5.0


def test_outcome_calculator_timeout():
    """Neither stop nor target hit → TIMEOUT."""
    entry_ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    ticks = [
        {"ts": datetime(2026, 5, 1, 12, 0, 1, tzinfo=timezone.utc),
         "high": 7252.0, "low": 7248.0, "close": 7250.0, "volume": 1},
    ]
    result = compute_outcome(ticks, entry_ts, 7250.0, 7245.0, 7255.0, "LONG",
                             timeout_minutes=1)
    assert result["outcome"] == "TIMEOUT"


# ── Balanced Validation (documentation, not hard gate) ─────────────────────

def test_retro_balanced_validation(scid_reader):
    """
    Validate with balanced sample across all 3 Worker outcomes.
    Documents asymmetric mismatch pattern. Not a hard gate.
    """
    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL not set"

    setups = _get_known_setups_balanced(db_url, per_outcome=10)
    print(f"\n  Balanced sample: {len(setups)} setups")

    by_expected = {"HIT_C1": [], "HIT_STOP": [], "TIMEOUT": []}

    for setup in setups:
        ticks = scid_reader.read_ticks_after(
            float(setup["first_detected_ts"]), max_minutes=60
        )
        if not ticks:
            continue

        result = compute_outcome(
            ticks,
            entry_ts=datetime.fromtimestamp(
                setup["first_detected_ts"], tz=timezone.utc),
            entry_price=setup["entry_price"],
            stop_price=setup["stop_price"],
            c1_target=setup["c1_target"],
            direction=setup["direction"],
        )

        by_expected[setup["expected_outcome"]].append({
            "expected": setup["expected_outcome"],
            "got": result["outcome"],
            "match": setup["expected_outcome"] == result["outcome"],
        })

    # Report per outcome
    print("\n  === Match rate by Worker's outcome ===")
    total_compared = 0
    total_matched = 0
    for expected, results in by_expected.items():
        if not results:
            print(f"  {expected}: no samples")
            continue
        matches = sum(1 for r in results if r["match"])
        total = len(results)
        total_compared += total
        total_matched += matches
        print(f"  {expected}: {matches}/{total} ({100*matches/total:.0f}%)")

        mismatches = [r for r in results if not r["match"]]
        if mismatches:
            got_counts = Counter(r["got"] for r in mismatches)
            print(f"    Mismatches → Retro said: {dict(got_counts)}")

    overall = total_matched / total_compared if total_compared else 0
    print(f"\n  Overall: {total_matched}/{total_compared} = {overall:.0%}")
    print("  Retro is tick-level. Worker was bar-level. Differences expected.")

    # Soft assertion: at least some matches overall
    assert total_compared >= 10, f"Too few comparisons: {total_compared}"
    assert total_matched > 0, "Zero matches — something is fundamentally wrong"
