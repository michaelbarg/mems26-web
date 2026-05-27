"""Tests for HFE Divergence Logger (W-4).

Validates: rate limiting, shadow sink, divergence type classification.
"""

import time
import pytest

from backend.v9.systems.woodies.hfe_divergence_logger import (
    HFEDivergence,
    HFEDivergenceLogger,
)


def _make_event(
    divergence_type="state_mismatch",
    dll_detected=True,
    dll_direction="LONG",
    dll_bars_ago=5,
    dll_confidence=0.7,
    python_detected=False,
    python_direction="NONE",
    python_bars_ago=0,
    python_confidence=0.0,
    notes="test",
):
    return HFEDivergence(
        timestamp=time.time(),
        bar_ts=1000.0,
        divergence_type=divergence_type,
        dll_detected=dll_detected,
        dll_direction=dll_direction,
        dll_bars_ago=dll_bars_ago,
        dll_confidence=dll_confidence,
        python_detected=python_detected,
        python_direction=python_direction,
        python_bars_ago=python_bars_ago,
        python_confidence=python_confidence,
        notes=notes,
    )


class TestHFEDivergenceLogger:
    """HFEDivergenceLogger tests."""

    def test_state_mismatch_dll_true_python_false(self):
        """DLL detects, Python does not -> state_mismatch logged."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(
            divergence_type="state_mismatch",
            dll_detected=True,
            python_detected=False,
        )
        assert logger.log_divergence(event) is True

    def test_state_mismatch_dll_false_python_true(self):
        """Python detects, DLL does not -> state_mismatch logged."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(
            divergence_type="state_mismatch",
            dll_detected=False,
            dll_direction="NONE",
            python_detected=True,
            python_direction="LONG",
        )
        assert logger.log_divergence(event) is True

    def test_direction_mismatch(self):
        """Both detect but different directions."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(
            divergence_type="direction_mismatch",
            dll_detected=True,
            dll_direction="LONG",
            python_detected=True,
            python_direction="SHORT",
        )
        assert logger.log_divergence(event) is True

    def test_bars_ago_mismatch(self):
        """Both detect but different bars_ago values."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(
            divergence_type="bars_ago_mismatch",
            dll_bars_ago=5,
            python_bars_ago=8,
            python_detected=True,
            python_direction="LONG",
        )
        assert logger.log_divergence(event) is True

    def test_confidence_drift(self):
        """Confidence differs by >0.1."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(
            divergence_type="confidence_drift",
            dll_confidence=0.7,
            python_confidence=0.55,
            python_detected=True,
            python_direction="LONG",
        )
        assert logger.log_divergence(event) is True

    def test_rate_limiting_same_type_within_window(self):
        """Same divergence_type within rate window -> second call returns False."""
        logger = HFEDivergenceLogger(rate_limit_seconds=60)
        event = _make_event(divergence_type="state_mismatch")
        assert logger.log_divergence(event) is True
        # Second call within window
        assert logger.log_divergence(event) is False

    def test_rate_limiting_different_types_independent(self):
        """Different divergence types have independent rate limits."""
        logger = HFEDivergenceLogger(rate_limit_seconds=60)
        e1 = _make_event(divergence_type="state_mismatch")
        e2 = _make_event(divergence_type="direction_mismatch")
        assert logger.log_divergence(e1) is True
        assert logger.log_divergence(e2) is True  # different type, not rate-limited

    def test_shadow_sink_receives_all_events(self):
        """Shadow sink gets every event regardless of rate limit."""
        received = []
        logger = HFEDivergenceLogger(
            rate_limit_seconds=60,
            shadow_sink=lambda e: received.append(e),
        )
        event = _make_event(divergence_type="state_mismatch")
        logger.log_divergence(event)
        logger.log_divergence(event)  # rate-limited for Python logger
        logger.log_divergence(event)  # rate-limited for Python logger
        assert len(received) == 3  # shadow sink got ALL three

    def test_shadow_sink_no_rate_limit(self):
        """Shadow sink is never rate-limited even when Python logger is."""
        received = []
        logger = HFEDivergenceLogger(
            rate_limit_seconds=60,
            shadow_sink=lambda e: received.append(e),
        )
        event = _make_event(divergence_type="confidence_drift")
        first = logger.log_divergence(event)
        second = logger.log_divergence(event)
        assert first is True
        assert second is False  # Python logger rate-limited
        assert len(received) == 2  # shadow sink got both

    def test_reset_rate_limit(self):
        """reset_rate_limit() clears state so next log goes through."""
        logger = HFEDivergenceLogger(rate_limit_seconds=60)
        event = _make_event(divergence_type="state_mismatch")
        assert logger.log_divergence(event) is True
        assert logger.log_divergence(event) is False  # rate-limited
        logger.reset_rate_limit()
        assert logger.log_divergence(event) is True  # cleared, goes through again

    def test_frozen_dataclass(self):
        """HFEDivergence is frozen -- attributes cannot be mutated."""
        event = _make_event()
        with pytest.raises(AttributeError):
            event.dll_detected = False  # type: ignore

    def test_zero_rate_limit_always_logs(self):
        """With rate_limit_seconds=0, every call is logged."""
        logger = HFEDivergenceLogger(rate_limit_seconds=0)
        event = _make_event(divergence_type="state_mismatch")
        assert logger.log_divergence(event) is True
        assert logger.log_divergence(event) is True
        assert logger.log_divergence(event) is True
