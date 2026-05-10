"""W11 Trade Manager tests — >90% coverage.

Tests: accept_setup, state transitions, invalid transitions, target hits,
stop hit, PnL calculation per-contract, event emission, DB persistence.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Set env before any backend imports
os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.session import Base
from backend.v9.db.models.trades import V9Trade
from backend.v9.services.trade_manager.state_machine import (
    InvalidTransition,
    TradeState,
    TradeStateMachine,
)
from backend.v9.services.trade_manager.events import (
    TRADE_EVENTS_CHANNEL,
    TradeEventEmitter,
)
from backend.v9.services.trade_manager.manager import (
    MES_POINT_VALUE,
    TradeManager,
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
def mock_redis():
    return MagicMock()


@pytest.fixture
def emitter(mock_redis):
    return TradeEventEmitter(redis_client=mock_redis)


@pytest.fixture
def manager(db, emitter):
    return TradeManager(db=db, event_emitter=emitter)


@pytest.fixture
def sample_setup():
    return {
        "firing_system": 1,
        "direction": "LONG",
        "stop": 5240.0,
        "t1": 5250.0,
        "t2": 5255.0,
        "t3": 5260.0,
        "cross_context": {"sys2": "neutral", "sys4": "bullish"},
    }


@pytest.fixture
def short_setup():
    return {
        "firing_system": 4,
        "direction": "SHORT",
        "stop": 5260.0,
        "t1": 5250.0,
        "t2": 5245.0,
        "t3": 5240.0,
    }


# ── State Machine Unit Tests ─────────────────────────────────────

class TestTradeStateMachine:

    def test_initial_state(self):
        sm = TradeStateMachine()
        assert sm.state == TradeState.PENDING

    def test_custom_initial_state(self):
        sm = TradeStateMachine(TradeState.FILLED)
        assert sm.state == TradeState.FILLED

    def test_pending_to_filled(self):
        sm = TradeStateMachine()
        prev = sm.transition(TradeState.FILLED)
        assert prev == TradeState.PENDING
        assert sm.state == TradeState.FILLED

    def test_pending_to_closed(self):
        sm = TradeStateMachine()
        sm.transition(TradeState.CLOSED)
        assert sm.state == TradeState.CLOSED

    def test_filled_to_partial(self):
        sm = TradeStateMachine(TradeState.FILLED)
        sm.transition(TradeState.PARTIAL)
        assert sm.state == TradeState.PARTIAL

    def test_filled_to_closed(self):
        sm = TradeStateMachine(TradeState.FILLED)
        sm.transition(TradeState.CLOSED)
        assert sm.state == TradeState.CLOSED

    def test_partial_to_closed(self):
        sm = TradeStateMachine(TradeState.PARTIAL)
        sm.transition(TradeState.CLOSED)
        assert sm.state == TradeState.CLOSED

    def test_is_terminal(self):
        sm = TradeStateMachine(TradeState.CLOSED)
        assert sm.is_terminal is True

    def test_not_terminal(self):
        sm = TradeStateMachine(TradeState.FILLED)
        assert sm.is_terminal is False

    def test_can_transition_true(self):
        sm = TradeStateMachine()
        assert sm.can_transition(TradeState.FILLED) is True

    def test_can_transition_false(self):
        sm = TradeStateMachine()
        assert sm.can_transition(TradeState.PARTIAL) is False


class TestInvalidTransitions:

    def test_pending_to_partial(self):
        sm = TradeStateMachine()
        with pytest.raises(InvalidTransition) as exc_info:
            sm.transition(TradeState.PARTIAL)
        assert exc_info.value.from_state == TradeState.PENDING
        assert exc_info.value.to_state == TradeState.PARTIAL

    def test_closed_to_anything(self):
        sm = TradeStateMachine(TradeState.CLOSED)
        for target in (TradeState.PENDING, TradeState.FILLED, TradeState.PARTIAL):
            with pytest.raises(InvalidTransition):
                sm.transition(target)

    def test_partial_to_filled(self):
        sm = TradeStateMachine(TradeState.PARTIAL)
        with pytest.raises(InvalidTransition):
            sm.transition(TradeState.FILLED)

    def test_filled_to_pending(self):
        sm = TradeStateMachine(TradeState.FILLED)
        with pytest.raises(InvalidTransition):
            sm.transition(TradeState.PENDING)


# ── Event Emitter Tests ──────────────────────────────────────────

class TestTradeEventEmitter:

    def test_emit_publishes_to_redis(self, mock_redis):
        emitter = TradeEventEmitter(redis_client=mock_redis)
        payload = emitter.emit("trade_created", 1, {"mode": "shadow"})

        assert payload["event"] == "trade_created"
        assert payload["trade_id"] == 1
        assert payload["data"]["mode"] == "shadow"
        assert "ts" in payload
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == TRADE_EVENTS_CHANNEL

    def test_emit_without_redis(self):
        emitter = TradeEventEmitter(redis_client=None)
        payload = emitter.emit("test", 1)
        assert payload["event"] == "test"

    def test_emit_redis_error_does_not_raise(self, mock_redis):
        mock_redis.publish.side_effect = ConnectionError("Redis down")
        emitter = TradeEventEmitter(redis_client=mock_redis)
        # Should not raise
        payload = emitter.emit("test", 1)
        assert payload["event"] == "test"


# ── Trade Manager Integration Tests ─────────────────────────────

class TestAcceptSetup:

    def test_creates_trade(self, manager, db, sample_setup):
        trade_id = manager.accept_setup(sample_setup, "shadow")
        assert trade_id is not None

        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()
        assert trade is not None
        assert trade.mode == "shadow"
        assert trade.firing_system == 1
        assert trade.direction == "LONG"
        assert trade.state == "PENDING"
        assert trade.stop == 5240.0
        assert trade.t1 == 5250.0
        assert trade.t2 == 5255.0
        assert trade.t3 == 5260.0
        assert trade.cross_context == {"sys2": "neutral", "sys4": "bullish"}

    def test_invalid_mode(self, manager, sample_setup):
        with pytest.raises(ValueError, match="Invalid mode"):
            manager.accept_setup(sample_setup, "paper")

    def test_invalid_firing_system(self, manager):
        setup = {"firing_system": 3, "direction": "LONG", "stop": 0, "t1": 0, "t2": 0, "t3": 0}
        with pytest.raises(ValueError, match="Invalid firing_system"):
            manager.accept_setup(setup, "shadow")

    def test_invalid_direction(self, manager):
        setup = {"firing_system": 1, "direction": "UP", "stop": 0, "t1": 0, "t2": 0, "t3": 0}
        with pytest.raises(ValueError, match="Invalid direction"):
            manager.accept_setup(setup, "shadow")

    def test_all_modes(self, manager, sample_setup):
        for mode in ("shadow", "demo", "live"):
            tid = manager.accept_setup(sample_setup, mode)
            assert tid is not None

    def test_all_firing_systems(self, manager):
        for sys_id in (1, 2, 4):
            setup = {"firing_system": sys_id, "direction": "LONG", "stop": 0, "t1": 1, "t2": 2, "t3": 3}
            tid = manager.accept_setup(setup, "shadow")
            assert tid is not None


class TestStateTransitions:

    def test_fill_trade(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "FILLED"
        assert trade.entry_price == 5245.0
        assert trade.entry_ts is not None

    def test_fill_then_partial(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "PARTIAL"
        assert trade.t1_hit_ts is not None

    def test_full_lifecycle(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "PARTIAL"
        assert trade.t2_hit_ts is not None

    def test_invalid_transition_pending_to_partial(self, manager, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        with pytest.raises(InvalidTransition):
            manager.on_target_hit(tid, "T1")

    def test_double_close_raises(self, manager, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_stop_hit(tid)
        with pytest.raises(InvalidTransition):
            manager.close_trade(tid, "manual")


class TestTargetHits:

    def test_t1_hit(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        ts = datetime(2026, 5, 10, 11, 30, tzinfo=timezone.utc)
        manager.on_target_hit(tid, "T1", fill_ts=ts)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # SQLite strips timezone — compare naive
        assert trade.t1_hit_ts.replace(tzinfo=None) == ts.replace(tzinfo=None)
        assert trade.state == "PARTIAL"

    def test_t2_hit_no_state_change(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.t2_hit_ts is not None
        assert trade.state == "PARTIAL"  # stays PARTIAL

    def test_t3_hit_closes(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")
        manager.on_target_hit(tid, "T3")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "CLOSED"
        assert trade.exit_reason == "T3_HIT"
        assert trade.outcome == "WIN"

    def test_invalid_target_name(self, manager, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        with pytest.raises(ValueError, match="Invalid target"):
            manager.on_target_hit(tid, "T4")


class TestStopHit:

    def test_stop_closes_trade(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        ts = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
        manager.on_stop_hit(tid, fill_ts=ts)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "CLOSED"
        # SQLite strips timezone — compare naive
        assert trade.stop_hit_ts.replace(tzinfo=None) == ts.replace(tzinfo=None)
        assert trade.exit_reason == "STOP_HIT"
        assert trade.exit_price == 5240.0
        assert trade.outcome == "LOSS"

    def test_stop_from_partial(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_stop_hit(tid)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "CLOSED"
        assert trade.exit_reason == "STOP_HIT"


class TestPnlCalculation:

    def test_full_win_pnl(self, manager, db, sample_setup):
        """T3 hit: c1@T1=5250, c2@T2=5255, c3@T3=5260, entry=5245."""
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")
        manager.on_target_hit(tid, "T3")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # c1: (5250-5245)*5 = 25
        # c2: (5255-5245)*5 = 50
        # c3: (5260-5245)*5 = 75
        # total = 150
        assert trade.pnl_usd == 150.0
        assert trade.outcome == "WIN"

    def test_stop_loss_pnl(self, manager, db, sample_setup):
        """Stop hit: all 3 contracts exit at stop=5240, entry=5245."""
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_stop_hit(tid)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # 3 * (5240-5245)*5 = 3 * -25 = -75
        assert trade.pnl_usd == -75.0
        assert trade.outcome == "LOSS"

    def test_short_stop_loss(self, manager, db, short_setup):
        """Short: stop at 5260, entry at 5255. Loss."""
        tid = manager.accept_setup(short_setup, "shadow")
        manager.on_fill(tid, 5255.0)
        manager.on_stop_hit(tid)

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # direction_mult = -1
        # 3 * (5260-5255)*5*(-1) = 3 * -25 = -75
        assert trade.pnl_usd == -75.0
        assert trade.outcome == "LOSS"

    def test_short_t3_win(self, manager, db, short_setup):
        """Short T3 win: entry=5255, T1=5250, T2=5245, T3=5240."""
        tid = manager.accept_setup(short_setup, "shadow")
        manager.on_fill(tid, 5255.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")
        manager.on_target_hit(tid, "T3")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # c1: (5250-5255)*(-1)*5 = 25
        # c2: (5245-5255)*(-1)*5 = 50
        # c3: (5240-5255)*(-1)*5 = 75
        # total = 150
        assert trade.pnl_usd == 150.0
        assert trade.outcome == "WIN"

    def test_pnl_r_calculation(self, manager, db, sample_setup):
        """pnl_r = total_pnl / total_risk."""
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        manager.on_target_hit(tid, "T1")
        manager.on_target_hit(tid, "T2")
        manager.on_target_hit(tid, "T3")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        # risk per contract = |5245-5240| * 5 = 25
        # total risk = 3 * 25 = 75
        # pnl_r = 150 / 75 = 2.0
        assert trade.pnl_r == 2.0

    def test_breakeven_pnl(self, manager, db):
        """Manual close at entry price = BE."""
        setup = {
            "firing_system": 2,
            "direction": "LONG",
            "stop": 5240.0,
            "t1": 5250.0,
            "t2": 5255.0,
            "t3": 5260.0,
        }
        tid = manager.accept_setup(setup, "shadow")
        manager.on_fill(tid, 5245.0)

        # Set exit_price to entry
        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        trade.exit_price = 5245.0
        manager.close_trade(tid, "manual")

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.pnl_usd == 0.0
        assert trade.outcome == "BE"


class TestEventEmission:

    def test_accept_emits_created(self, manager, mock_redis, sample_setup):
        manager.accept_setup(sample_setup, "shadow")
        # First publish call is trade_created
        call_args = mock_redis.publish.call_args_list[0]
        assert TRADE_EVENTS_CHANNEL in call_args[0]
        assert "trade_created" in call_args[0][1]

    def test_fill_emits_event(self, manager, mock_redis, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        mock_redis.reset_mock()
        manager.on_fill(tid, 5245.0)
        assert mock_redis.publish.called
        assert "trade_filled" in mock_redis.publish.call_args[0][1]

    def test_target_emits_event(self, manager, mock_redis, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        mock_redis.reset_mock()
        manager.on_target_hit(tid, "T1")
        assert "target_t1_hit" in mock_redis.publish.call_args[0][1]

    def test_stop_emits_event(self, manager, mock_redis, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        mock_redis.reset_mock()
        manager.on_stop_hit(tid)
        assert "stop_hit" in mock_redis.publish.call_args[0][1]

    def test_close_emits_event(self, manager, mock_redis, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        mock_redis.reset_mock()
        manager.close_trade(tid, "eod_flat")
        assert "trade_closed" in mock_redis.publish.call_args[0][1]


class TestDBPersistence:

    def test_trade_persisted(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        db.flush()

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade is not None
        assert trade.id == tid

    def test_state_persisted_after_fill(self, manager, db, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        db.flush()

        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "FILLED"

    def test_get_active_trades(self, manager, db, sample_setup):
        tid1 = manager.accept_setup(sample_setup, "shadow")
        tid2 = manager.accept_setup(sample_setup, "demo")
        manager.on_fill(tid1, 5245.0)
        manager.on_stop_hit(tid1)  # closes tid1

        active = manager.get_active_trades()
        assert len(active) == 1
        assert active[0].id == tid2

    def test_get_active_trades_by_mode(self, manager, db, sample_setup):
        manager.accept_setup(sample_setup, "shadow")
        manager.accept_setup(sample_setup, "demo")

        shadow_active = manager.get_active_trades(mode="shadow")
        assert len(shadow_active) == 1
        assert shadow_active[0].mode == "shadow"

    def test_machine_restored_from_db(self, manager, db, sample_setup):
        """After clearing in-memory machines, state restores from DB."""
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)

        # Simulate restart: clear in-memory machines
        manager._machines.clear()

        # Should still work — restores from DB
        manager.on_target_hit(tid, "T1")
        trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
        assert trade.state == "PARTIAL"

    def test_machine_cleaned_on_close(self, manager, sample_setup):
        tid = manager.accept_setup(sample_setup, "shadow")
        manager.on_fill(tid, 5245.0)
        assert tid in manager._machines
        manager.on_stop_hit(tid)
        assert tid not in manager._machines

    def test_trade_not_found(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.on_fill(999, 5245.0)
