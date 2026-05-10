"""W12 Daily Quality Agent tests — >85% coverage.

Tests: EOD batch processing, grade assignment (A/B/C/D), idempotency,
timing quality in killzones, execution quality scoring, context quality
with system agreement, skipping active trades.
"""

import os
import pytest
from datetime import date, datetime, timezone

# Set env before any backend imports
os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.session import Base
from backend.v9.db.models.trades import V9Trade
from backend.v9.services.daily_quality_agent.agent import DailyQualityAgent
from backend.v9.services.daily_quality_agent.scoring import (
    compute_grade,
    context_quality,
    execution_quality,
    outcome_quality,
    timing_quality,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """In-memory SQLite for tests."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    """Yield a DB session, rollback after test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def agent(db):
    return DailyQualityAgent(db=db)


def _make_trade(
    db,
    outcome="WIN",
    exit_reason="T3_HIT",
    entry_ts=None,
    entry_price=5245.0,
    stop=5240.0,
    direction="LONG",
    firing_system=1,
    cross_context=None,
    mode="shadow",
):
    """Helper to create a completed V9Trade row."""
    if entry_ts is None:
        # Default: 2026-05-10 15:00 UTC = ~11:00 ET (NY_PRIME killzone)
        entry_ts = datetime(2026, 5, 10, 15, 0, 0, tzinfo=timezone.utc)

    trade = V9Trade(
        mode=mode,
        firing_system=firing_system,
        direction=direction,
        state="CLOSED",
        entry_ts=entry_ts,
        entry_price=entry_price,
        stop=stop,
        t1=5250.0,
        t2=5255.0,
        t3=5260.0,
        exit_ts=entry_ts,
        exit_price=5260.0 if outcome == "WIN" else stop,
        exit_reason=exit_reason,
        pnl_usd=150.0 if outcome == "WIN" else (-75.0 if outcome == "LOSS" else 0.0),
        pnl_r=2.0 if outcome == "WIN" else (-1.0 if outcome == "LOSS" else 0.0),
        outcome=outcome,
        cross_context=cross_context,
    )
    db.add(trade)
    db.flush()
    return trade


# ── EOD Batch Tests ───────────────────────────────────────────────

class TestEodBatchProcessesAll:

    def test_eod_batch_processes_all(self, db, agent):
        """Batch processes multiple trades for the same date."""
        _make_trade(db, outcome="WIN", exit_reason="T3_HIT")
        _make_trade(db, outcome="LOSS", exit_reason="STOP_HIT")
        _make_trade(db, outcome="BE", exit_reason="manual")

        results = agent.run_eod_batch(date(2026, 5, 10))

        assert len(results) == 3
        for r in results:
            assert "grade" in r
            assert "dimensions" in r
            assert r["grade"] in ("A", "B", "C", "D")

    def test_eod_batch_writes_quality_to_db(self, db, agent):
        """Quality JSON is persisted to V9Trade.quality."""
        trade = _make_trade(db, outcome="WIN", exit_reason="T3_HIT")
        agent.run_eod_batch(date(2026, 5, 10))

        refreshed = db.query(V9Trade).filter(V9Trade.id == trade.id).first()
        assert refreshed.quality is not None
        assert refreshed.quality["grade"] in ("A", "B", "C", "D")
        assert "dimensions" in refreshed.quality

    def test_eod_batch_empty_day(self, db, agent):
        """No trades for the date returns empty list."""
        results = agent.run_eod_batch(date(2026, 1, 1))
        assert results == []


class TestNoActiveTradesSkipped:

    def test_no_active_trades_skipped(self, db, agent):
        """Trades without outcome (active) are skipped."""
        # Active trade — no outcome
        active_trade = V9Trade(
            mode="shadow",
            firing_system=1,
            direction="LONG",
            state="FILLED",
            entry_ts=datetime(2026, 5, 10, 15, 0, 0, tzinfo=timezone.utc),
            entry_price=5245.0,
            stop=5240.0,
            t1=5250.0,
            t2=5255.0,
            t3=5260.0,
            outcome=None,  # not completed
        )
        db.add(active_trade)

        # Completed trade
        _make_trade(db, outcome="WIN", exit_reason="T3_HIT")

        db.flush()

        results = agent.run_eod_batch(date(2026, 5, 10))

        # Only the completed trade is graded
        assert len(results) == 1

        # Active trade has no quality set
        refreshed_active = db.query(V9Trade).filter(
            V9Trade.id == active_trade.id
        ).first()
        assert refreshed_active.quality is None


class TestIdempotent:

    def test_idempotent(self, db, agent):
        """Rerunning same day produces identical result."""
        _make_trade(
            db, outcome="WIN", exit_reason="T3_HIT",
            cross_context={"sys2": "bullish", "sys4": "neutral"},
        )

        results_1 = agent.run_eod_batch(date(2026, 5, 10))
        results_2 = agent.run_eod_batch(date(2026, 5, 10))

        assert len(results_1) == len(results_2)
        for r1, r2 in zip(results_1, results_2):
            assert r1["grade"] == r2["grade"]
            assert r1["dimensions"] == r2["dimensions"]


# ── Grade Assignment Tests ────────────────────────────────────────

class TestGradesABCD:

    def test_grade_a(self):
        """A >= 0.8 weighted average."""
        dims = {"timing": 1.0, "execution": 1.0, "outcome": 1.0, "context": 1.0}
        assert compute_grade(dims) == "A"

    def test_grade_b(self):
        """B >= 0.6, < 0.8."""
        dims = {"timing": 0.5, "execution": 0.75, "outcome": 0.75, "context": 0.5}
        assert compute_grade(dims) == "B"

    def test_grade_c(self):
        """C >= 0.4, < 0.6."""
        dims = {"timing": 0.5, "execution": 0.5, "outcome": 0.5, "context": 0.0}
        assert compute_grade(dims) == "C"

    def test_grade_d(self):
        """D < 0.4."""
        dims = {"timing": 0.0, "execution": 0.0, "outcome": 0.0, "context": 0.0}
        assert compute_grade(dims) == "D"

    def test_grade_boundary_a(self):
        """Exactly 0.8 = A."""
        dims = {"timing": 0.8, "execution": 0.8, "outcome": 0.8, "context": 0.8}
        assert compute_grade(dims) == "A"

    def test_grade_boundary_b(self):
        """Exactly 0.6 = B."""
        dims = {"timing": 0.6, "execution": 0.6, "outcome": 0.6, "context": 0.6}
        assert compute_grade(dims) == "B"

    def test_grade_boundary_c(self):
        """Exactly 0.4 = C."""
        dims = {"timing": 0.4, "execution": 0.4, "outcome": 0.4, "context": 0.4}
        assert compute_grade(dims) == "C"


# ── Timing Quality Tests ─────────────────────────────────────────

class TestTimingInKillzone:

    def test_timing_in_killzone(self):
        """NY_PRIME (10:30-11:30 ET) = HIGH = 1.0."""
        assert timing_quality(10, 45) == 1.0

    def test_ny_open_ib(self):
        """NY_OPEN_IB (9:45-10:30 ET) = HIGH = 1.0."""
        assert timing_quality(9, 50) == 1.0

    def test_pm_prime(self):
        """PM_PRIME (14:00-15:00 ET) = HIGH = 1.0."""
        assert timing_quality(14, 30) == 1.0

    def test_lunch_low(self):
        """LUNCH (12:00-13:00 ET) = LOW = 0.2."""
        assert timing_quality(12, 30) == 0.2

    def test_ny_open_volatility_medium(self):
        """NY_OPEN_VOLATILITY (9:30-9:45 ET) = MEDIUM = 0.5."""
        assert timing_quality(9, 35) == 0.5

    def test_pre_market_low(self):
        """PRE_MARKET (5:00-9:30 ET) = LOW = 0.2."""
        assert timing_quality(7, 0) == 0.2

    def test_after_hours_off(self):
        """After hours (16:00+) = OFF = 0.0."""
        assert timing_quality(18, 0) == 0.0

    def test_close_final_low(self):
        """CLOSE_FINAL (15:45-16:00 ET) = LOW = 0.2."""
        assert timing_quality(15, 50) == 0.2


# ── Execution Quality Tests ──────────────────────────────────────

class TestExecutionQualityScoring:

    def test_execution_quality_scoring(self):
        """Zero slippage = 1.0."""
        assert execution_quality(5245.0, 5245.0, 5240.0) == 1.0

    def test_half_risk_slippage(self):
        """Slippage = half of risk distance = 0.5."""
        # Risk = |5245 - 5240| = 5, slippage = |5247.5 - 5245| = 2.5
        assert execution_quality(5247.5, 5245.0, 5240.0) == 0.5

    def test_full_risk_slippage(self):
        """Slippage = full risk distance = 0.0."""
        assert execution_quality(5250.0, 5245.0, 5240.0) == 0.0

    def test_no_expected_price(self):
        """No expected price = 1.0 (no measurable slippage)."""
        assert execution_quality(5245.0, None, 5240.0) == 1.0

    def test_zero_risk_distance(self):
        """Zero risk distance = 1.0 (prevent division by zero)."""
        assert execution_quality(5245.0, 5245.0, 5245.0) == 1.0

    def test_over_risk_slippage(self):
        """Slippage > risk = clamped to 0.0."""
        assert execution_quality(5255.0, 5245.0, 5240.0) == 0.0


# ── Outcome Quality Tests ────────────────────────────────────────

class TestOutcomeQuality:

    def test_win_t3_hit(self):
        assert outcome_quality("WIN", "T3_HIT") == 1.0

    def test_win_partial(self):
        assert outcome_quality("WIN", "manual") == 0.75

    def test_be(self):
        assert outcome_quality("BE", "manual") == 0.5

    def test_loss_stop(self):
        assert outcome_quality("LOSS", "STOP_HIT") == 0.0


# ── Context Quality Tests ────────────────────────────────────────

class TestContextQualityWithAgreement:

    def test_context_quality_with_agreement(self):
        """All systems agree (bullish) = 1.0."""
        ctx = {"sys2": "bullish", "sys4": "bullish", "sys5": "bullish"}
        assert context_quality(ctx) == 1.0

    def test_mixed_agreement(self):
        """Mix of bullish and neutral = 0.75."""
        ctx = {"sys2": "bullish", "sys4": "neutral"}
        assert context_quality(ctx) == 0.75

    def test_all_neutral(self):
        """All neutral = 0.5."""
        ctx = {"sys2": "neutral", "sys4": "neutral"}
        assert context_quality(ctx) == 0.5

    def test_no_context(self):
        """No cross_context = 0.5 (neutral default)."""
        assert context_quality(None) == 0.5

    def test_empty_context(self):
        """Empty dict = 0.5."""
        assert context_quality({}) == 0.5

    def test_disagreement(self):
        """Unknown stances = 0.0 per entry."""
        ctx = {"sys2": "conflicting"}
        assert context_quality(ctx) == 0.0

    def test_nested_context(self):
        """Nested dict with direction key."""
        ctx = {"sys2": {"direction": "bullish", "confidence": 0.9}}
        assert context_quality(ctx) == 1.0


# ── Integration: Full Scoring Pipeline ────────────────────────────

class TestFullPipeline:

    def test_win_in_prime_zone_gets_high_grade(self, db, agent):
        """WIN + T3_HIT + NY_PRIME entry + agreement = grade A."""
        _make_trade(
            db,
            outcome="WIN",
            exit_reason="T3_HIT",
            # 15:00 UTC = 11:00 ET = NY_PRIME
            entry_ts=datetime(2026, 5, 10, 15, 0, 0, tzinfo=timezone.utc),
            cross_context={"sys2": "bullish", "sys4": "bullish"},
        )

        results = agent.run_eod_batch(date(2026, 5, 10))
        assert len(results) == 1
        assert results[0]["grade"] == "A"

    def test_loss_in_lunch_gets_low_grade(self, db, agent):
        """LOSS + STOP_HIT + LUNCH entry + no agreement = grade D."""
        _make_trade(
            db,
            outcome="LOSS",
            exit_reason="STOP_HIT",
            # 16:30 UTC = 12:30 ET = LUNCH
            entry_ts=datetime(2026, 5, 10, 16, 30, 0, tzinfo=timezone.utc),
            cross_context={"sys2": "conflicting", "sys4": "conflicting"},
        )

        results = agent.run_eod_batch(date(2026, 5, 10))
        assert len(results) == 1
        assert results[0]["grade"] == "D"
