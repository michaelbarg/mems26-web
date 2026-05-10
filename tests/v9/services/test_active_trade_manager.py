"""W15 Active Trade Manager tests — >85% coverage.

Tests: unrealized PnL (long/short), Smart BE on T1 hit, proximity
alerts (target/stop), time exit suggestion, closed trade filtering,
multiple simultaneous open trades.
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
from backend.v9.services.trade_manager.state_machine import TradeState
from backend.v9.services.trade_manager.events import TradeEventEmitter
from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.active_trade_manager.monitor import (
    ActiveTradeMonitor,
    MES_POINT_VALUE,
    PROXIMITY_THRESHOLD,
)
from backend.v9.services.active_trade_manager.alerts import (
    AlertEmitter,
    TRADE_ALERTS_CHANNEL,
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
def trade_manager(db, mock_redis):
    emitter = TradeEventEmitter(redis_client=mock_redis)
    return TradeManager(db=db, event_emitter=emitter)


@pytest.fixture
def alert_emitter(mock_redis):
    return AlertEmitter(redis_client=mock_redis)


@pytest.fixture
def monitor(trade_manager, alert_emitter):
    return ActiveTradeMonitor(
        trade_manager=trade_manager,
        alert_emitter=alert_emitter,
    )


def _make_filled_trade(trade_manager, direction="LONG", entry=5000.0,
                       stop=4990.0, t1=5005.0, t2=5010.0, t3=5015.0):
    """Helper: create and fill a trade."""
    setup = {
        "firing_system": 1,
        "direction": direction,
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "t3": t3,
    }
    trade_id = trade_manager.accept_setup(setup, mode="shadow")
    trade_manager.on_fill(trade_id, entry)
    return trade_id


# ── Tests ─────────────────────────────────────────────────────────

class TestMonitorOpenTrades:
    """test_monitor_open_trades — update with price, get unrealized PnL."""

    def test_get_open_trades_returns_filled(self, monitor, trade_manager):
        trade_id = _make_filled_trade(trade_manager, entry=5000.0)

        result = monitor.get_open_trades(current_price=5002.0)

        assert len(result) == 1
        assert result[0]["trade_id"] == trade_id
        assert result[0]["state"] == TradeState.FILLED.value
        assert result[0]["entry_price"] == 5000.0

    def test_update_returns_empty_when_no_proximity(self, monitor, trade_manager):
        _make_filled_trade(trade_manager, entry=5000.0, t1=5010.0, stop=4990.0)

        alerts = monitor.update(current_price=5003.0, ts=1000.0)

        # Price is in the middle — not close to target or stop
        # Distance to T1: 7/10 = 0.7 (>0.25), distance to stop: 13/10 = 1.3 (>0.25)
        assert len(alerts) == 0


class TestSmartBE:
    """test_smart_be_on_c2_fill — T1 hit triggers stop move to entry."""

    def test_smart_be_on_t1_hit(self, monitor, trade_manager, db):
        trade_id = _make_filled_trade(
            trade_manager, entry=5000.0, stop=4990.0,
            t1=5005.0, t2=5010.0, t3=5015.0,
        )

        # T1 hit -> PARTIAL state
        trade_manager.on_target_hit(trade_id, "T1")

        # Update triggers Smart BE
        alerts = monitor.update(current_price=5006.0, ts=1000.0)

        smart_be_alerts = [a for a in alerts if a["alert_type"] == "smart_be_triggered"]
        assert len(smart_be_alerts) == 1
        assert smart_be_alerts[0]["details"]["new_stop"] == 5000.0

        # Verify stop was moved in DB
        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()
        assert trade.stop == 5000.0

    def test_smart_be_only_applied_once(self, monitor, trade_manager):
        trade_id = _make_filled_trade(trade_manager, entry=5000.0, stop=4990.0)
        trade_manager.on_target_hit(trade_id, "T1")

        # First update triggers Smart BE
        alerts1 = monitor.update(current_price=5006.0, ts=1000.0)
        smart_be_1 = [a for a in alerts1 if a["alert_type"] == "smart_be_triggered"]
        assert len(smart_be_1) == 1

        # Second update does NOT trigger again
        alerts2 = monitor.update(current_price=5007.0, ts=2000.0)
        smart_be_2 = [a for a in alerts2 if a["alert_type"] == "smart_be_triggered"]
        assert len(smart_be_2) == 0

    def test_apply_smart_be_direct(self, monitor, trade_manager, db):
        trade_id = _make_filled_trade(trade_manager, entry=5000.0, stop=4990.0)
        trade_manager.on_target_hit(trade_id, "T1")

        result = monitor.apply_smart_be(trade_id)

        assert result is not None
        assert result["alert_type"] == "smart_be_triggered"
        assert result["details"]["new_stop"] == 5000.0

        trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()
        assert trade.stop == 5000.0


class TestAlertNearTarget:
    """test_alert_near_target — alert when within 25% of target distance."""

    def test_approaching_t1(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, entry=5000.0, t1=5010.0,
            t2=5020.0, t3=5030.0, stop=4990.0,
        )

        # Price at 5008 -> distance to T1 = 2/10 = 0.2 (< 0.25)
        alerts = monitor.update(current_price=5008.0, ts=1000.0)

        target_alerts = [a for a in alerts if a["alert_type"] == "approaching_target"]
        assert len(target_alerts) >= 1
        t1_alerts = [a for a in target_alerts if a["details"]["target_name"] == "T1"]
        assert len(t1_alerts) == 1
        assert t1_alerts[0]["details"]["distance_pct"] == 0.2

    def test_no_alert_when_far_from_target(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, entry=5000.0, t1=5010.0,
            t2=5020.0, t3=5030.0, stop=4990.0,
        )

        # Price at 5002 -> distance to T1 = 8/10 = 0.8 (> 0.25)
        alerts = monitor.update(current_price=5002.0, ts=1000.0)

        target_alerts = [a for a in alerts if a["alert_type"] == "approaching_target"]
        assert len(target_alerts) == 0


class TestAlertNearStop:
    """test_alert_near_stop — alert when within 25% of stop distance."""

    def test_approaching_stop_long(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
            stop=4990.0, t1=5010.0, t2=5020.0, t3=5030.0,
        )

        # Price at 4992 -> distance to stop = 2/10 = 0.2 (< 0.25)
        alerts = monitor.update(current_price=4992.0, ts=1000.0)

        stop_alerts = [a for a in alerts if a["alert_type"] == "approaching_stop"]
        assert len(stop_alerts) == 1
        assert stop_alerts[0]["details"]["distance_pct"] == 0.2

    def test_approaching_stop_short(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="SHORT", entry=5000.0,
            stop=5010.0, t1=4990.0, t2=4980.0, t3=4970.0,
        )

        # Price at 5008 -> distance to stop = 2/10 = 0.2 (< 0.25)
        alerts = monitor.update(current_price=5008.0, ts=1000.0)

        stop_alerts = [a for a in alerts if a["alert_type"] == "approaching_stop"]
        assert len(stop_alerts) == 1
        assert stop_alerts[0]["details"]["distance_pct"] == 0.2


class TestNoAlertOnClosedTrades:
    """test_no_alert_on_closed_trades — closed trades are ignored."""

    def test_closed_trade_ignored(self, monitor, trade_manager):
        trade_id = _make_filled_trade(
            trade_manager, entry=5000.0, stop=4990.0,
        )
        trade_manager.close_trade(trade_id, reason="MANUAL")

        # Price near where stop was — should produce no alerts
        alerts = monitor.update(current_price=4991.0, ts=1000.0)
        assert len(alerts) == 0

    def test_get_open_trades_excludes_closed(self, monitor, trade_manager):
        trade_id = _make_filled_trade(trade_manager, entry=5000.0)
        trade_manager.close_trade(trade_id, reason="MANUAL")

        result = monitor.get_open_trades(current_price=5000.0)
        assert len(result) == 0


class TestUnrealizedPnlLong:
    """test_unrealized_pnl_long — long trade PnL calculation."""

    def test_long_profit(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
        )

        result = monitor.get_open_trades(current_price=5002.0)

        assert len(result) == 1
        # 3 contracts * 2 points * $5/point = $30
        assert result[0]["unrealized_pnl"] == 30.0

    def test_long_loss(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
        )

        result = monitor.get_open_trades(current_price=4998.0)

        # 3 contracts * -2 points * $5/point = -$30
        assert result[0]["unrealized_pnl"] == -30.0

    def test_long_partial_pnl(self, monitor, trade_manager):
        """After T1 hit, C1 is realized, C2+C3 are unrealized."""
        trade_id = _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
            t1=5005.0, t2=5010.0, t3=5015.0,
        )
        trade_manager.on_target_hit(trade_id, "T1")

        result = monitor.get_open_trades(current_price=5008.0)

        assert len(result) == 1
        # C1 realized: (5005-5000) * 1 * $5 = $25
        # C2+C3 unrealized: (5008-5000) * 1 * $5 * 2 = $80
        # Total: $105
        assert result[0]["unrealized_pnl"] == 105.0


class TestUnrealizedPnlShort:
    """test_unrealized_pnl_short — short trade PnL calculation."""

    def test_short_profit(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="SHORT", entry=5000.0,
            stop=5010.0, t1=4995.0, t2=4990.0, t3=4985.0,
        )

        result = monitor.get_open_trades(current_price=4998.0)

        # 3 contracts * 2 points * $5/point = $30
        assert result[0]["unrealized_pnl"] == 30.0

    def test_short_loss(self, monitor, trade_manager):
        _make_filled_trade(
            trade_manager, direction="SHORT", entry=5000.0,
            stop=5010.0, t1=4995.0, t2=4990.0, t3=4985.0,
        )

        result = monitor.get_open_trades(current_price=5002.0)

        # 3 contracts * -2 points * $5/point = -$30
        assert result[0]["unrealized_pnl"] == -30.0


class TestTimeExitSuggestion:
    """test_time_exit_suggestion — alert near 14:30 ET cutoff."""

    def test_time_exit_at_1425(self, monitor, trade_manager):
        _make_filled_trade(trade_manager, entry=5000.0)

        alerts = monitor.update(
            current_price=5002.0, ts=1000.0,
            et_hour=14, et_minute=25,
        )

        time_alerts = [a for a in alerts if a["alert_type"] == "time_exit_suggestion"]
        assert len(time_alerts) == 1
        assert "14:25 ET" in time_alerts[0]["details"]["reason"]

    def test_time_exit_at_1429(self, monitor, trade_manager):
        _make_filled_trade(trade_manager, entry=5000.0)

        alerts = monitor.update(
            current_price=5002.0, ts=1000.0,
            et_hour=14, et_minute=29,
        )

        time_alerts = [a for a in alerts if a["alert_type"] == "time_exit_suggestion"]
        assert len(time_alerts) == 1

    def test_no_time_exit_at_1400(self, monitor, trade_manager):
        _make_filled_trade(trade_manager, entry=5000.0)

        alerts = monitor.update(
            current_price=5002.0, ts=1000.0,
            et_hour=14, et_minute=0,
        )

        time_alerts = [a for a in alerts if a["alert_type"] == "time_exit_suggestion"]
        assert len(time_alerts) == 0


class TestMultipleOpenTrades:
    """test_multiple_open_trades — monitor handles multiple trades."""

    def test_two_trades_both_monitored(self, monitor, trade_manager):
        t1_id = _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
            stop=4990.0, t1=5010.0, t2=5020.0, t3=5030.0,
        )
        t2_id = _make_filled_trade(
            trade_manager, direction="SHORT", entry=5050.0,
            stop=5060.0, t1=5040.0, t2=5030.0, t3=5020.0,
        )

        result = monitor.get_open_trades(current_price=5005.0)

        assert len(result) == 2
        ids = {r["trade_id"] for r in result}
        assert t1_id in ids
        assert t2_id in ids

    def test_close_one_keeps_other(self, monitor, trade_manager):
        t1_id = _make_filled_trade(trade_manager, entry=5000.0)
        t2_id = _make_filled_trade(trade_manager, entry=5010.0)

        trade_manager.close_trade(t1_id, reason="MANUAL")
        monitor.cleanup_trade(t1_id)

        result = monitor.get_open_trades(current_price=5005.0)
        assert len(result) == 1
        assert result[0]["trade_id"] == t2_id

    def test_alerts_for_multiple_trades(self, monitor, trade_manager):
        # Trade 1 (LONG): price near T1 at 5010
        _make_filled_trade(
            trade_manager, direction="LONG", entry=5000.0,
            stop=4990.0, t1=5010.0, t2=5020.0, t3=5030.0,
        )
        # Trade 2 (SHORT): entry=5000, stop=5010 — price at 5008 near stop
        # |5010 - 5008| / |5010 - 5000| = 2/10 = 0.2 < 0.25
        _make_filled_trade(
            trade_manager, direction="SHORT", entry=5000.0,
            stop=5010.0, t1=4990.0, t2=4980.0, t3=4970.0,
        )

        alerts = monitor.update(current_price=5008.0, ts=1000.0)

        target_alerts = [a for a in alerts if a["alert_type"] == "approaching_target"]
        stop_alerts = [a for a in alerts if a["alert_type"] == "approaching_stop"]

        assert len(target_alerts) >= 1
        assert len(stop_alerts) >= 1


class TestAlertEmitter:
    """Direct tests for AlertEmitter."""

    def test_emit_approaching_target(self, alert_emitter, mock_redis):
        result = alert_emitter.emit_approaching_target(1, "T1", 0.15)

        assert result["alert_type"] == "approaching_target"
        assert result["trade_id"] == 1
        assert result["details"]["target_name"] == "T1"
        assert result["details"]["distance_pct"] == 0.15
        assert "ts" in result
        mock_redis.publish.assert_called_once()

    def test_emit_approaching_stop(self, alert_emitter, mock_redis):
        result = alert_emitter.emit_approaching_stop(1, 0.10)

        assert result["alert_type"] == "approaching_stop"
        assert result["details"]["distance_pct"] == 0.10
        mock_redis.publish.assert_called_once()

    def test_emit_smart_be_triggered(self, alert_emitter, mock_redis):
        result = alert_emitter.emit_smart_be_triggered(1, 5000.0)

        assert result["alert_type"] == "smart_be_triggered"
        assert result["details"]["new_stop"] == 5000.0
        mock_redis.publish.assert_called_once()

    def test_emit_time_exit_suggestion(self, alert_emitter, mock_redis):
        result = alert_emitter.emit_time_exit_suggestion(1, "14:25 ET cutoff")

        assert result["alert_type"] == "time_exit_suggestion"
        assert result["details"]["reason"] == "14:25 ET cutoff"
        mock_redis.publish.assert_called_once()

    def test_emit_publishes_to_correct_channel(self, alert_emitter, mock_redis):
        alert_emitter.emit_approaching_target(1, "T1", 0.15)

        channel = mock_redis.publish.call_args[0][0]
        assert channel == TRADE_ALERTS_CHANNEL

    def test_emit_without_redis(self):
        """No Redis -> logs, no exception."""
        emitter = AlertEmitter(redis_client=None)
        result = emitter.emit_approaching_target(1, "T1", 0.15)

        assert result["alert_type"] == "approaching_target"

    def test_emit_redis_error_handled(self, mock_redis):
        """Redis publish error is caught and logged."""
        mock_redis.publish.side_effect = ConnectionError("Redis down")
        emitter = AlertEmitter(redis_client=mock_redis)

        result = emitter.emit_approaching_target(1, "T1", 0.15)

        assert result["alert_type"] == "approaching_target"


class TestCleanupTrade:
    """Verify cleanup_trade prevents unbounded growth."""

    def test_cleanup_removes_tracking(self, monitor, trade_manager):
        trade_id = _make_filled_trade(trade_manager, entry=5000.0, stop=4990.0)
        trade_manager.on_target_hit(trade_id, "T1")

        # Apply Smart BE
        monitor.apply_smart_be(trade_id)
        assert monitor._smart_be_applied.get(trade_id) is True

        # Cleanup
        monitor.cleanup_trade(trade_id)
        assert trade_id not in monitor._smart_be_applied
