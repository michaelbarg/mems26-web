"""P31-A: DayTypeConsumer write gate — refuse UNKNOWN/PENDING UPSERTs."""

import pytest
from unittest.mock import MagicMock, patch
from backend.v9.systems.day_type.consumer import DayTypeConsumer


def _make_event(day_type="Normal", lock_state="LOCKED", probability=0.68):
    return {
        "timestamp": "2026-05-29T14:00:00+00:00",
        "day_type": day_type,
        "lock_state": lock_state,
        "probability": probability,
        "directional_certainty": "LOW",
        "trading_confidence": "HIGH",
        "ib_h": 7574.0,
        "ib_l": 7525.5,
        "ib_width": 48.5,
        "ib_width_class": "WIDE",
        "opening_type": "INDETERMINATE",
        "last_updated_at": "2026-05-29T14:00:00+00:00",
        "reasoning_notes": "test",
        "active_zohar_rules": [],
    }


class TestShouldGateWrite:
    def test_gate_refuses_unknown_pending(self):
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "UNKNOWN", "lock_state": "PENDING"}
        ) is True

    def test_gate_refuses_none_pending(self):
        assert DayTypeConsumer._should_gate_write(
            {"day_type": None, "lock_state": "PENDING"}
        ) is True

    def test_gate_refuses_empty_pending(self):
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "", "lock_state": "PENDING"}
        ) is True

    def test_gate_allows_locked_classification(self):
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "Normal", "lock_state": "LOCKED"}
        ) is False

    def test_gate_allows_locked_low_conf(self):
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "Trend_Normal", "lock_state": "LOCKED_LOW_CONF"}
        ) is False

    def test_gate_allows_unknown_locked(self):
        """UNKNOWN + LOCKED is unusual but should NOT be gated (explicit lock)."""
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "UNKNOWN", "lock_state": "LOCKED"}
        ) is False

    def test_gate_does_not_swallow_real_first_bar_rth(self):
        """First RTH bar may have low probability but real day_type — must pass."""
        assert DayTypeConsumer._should_gate_write(
            {"day_type": "Normal", "lock_state": "PENDING", "probability": 0.3}
        ) is False


class TestConsumeWithGate:
    def test_consume_skips_unknown_pending(self):
        """consume() returns early without DB write when gated."""
        mock_factory = MagicMock()
        consumer = DayTypeConsumer(mock_factory)
        event = _make_event(day_type="UNKNOWN", lock_state="PENDING")
        consumer.consume(event)
        # DB session factory should never be called
        mock_factory.assert_not_called()

    def test_consume_writes_locked_classification(self):
        """consume() proceeds to DB write for locked classifications."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_factory = MagicMock(return_value=mock_session)
        consumer = DayTypeConsumer(mock_factory)
        event = _make_event(day_type="Normal", lock_state="LOCKED")
        consumer.consume(event)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
