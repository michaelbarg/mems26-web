"""Tests for T1Setup output schema (D-041)."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.v9.systems.five_min.output_schema import T1Setup


def test_valid_long():
    setup = T1Setup(
        pattern_name='REACTIVE_LONG', direction='LONG',
        entry_price=5250.0, stop_price=5248.0,
        t1_price=5252.0, t2_price=5254.0,
        time_stop_minutes=60, confidence=75,
        bar_index=100, fired_at=datetime.now(timezone.utc),
    )
    assert setup.system_id == 'T1_NUMBER_BAR'
    assert setup.provisional is True


def test_invalid_pattern_name():
    with pytest.raises(ValidationError):
        T1Setup(
            pattern_name='INVALID_PATTERN', direction='LONG',
            entry_price=5250.0, stop_price=5248.0,
            t1_price=5252.0, t2_price=5254.0,
            time_stop_minutes=60, confidence=75,
            bar_index=100, fired_at=datetime.now(timezone.utc),
        )


def test_sizing_range():
    setup = T1Setup(
        pattern_name='INITIATIVE_SHORT', direction='SHORT',
        entry_price=5250.0, stop_price=5252.0,
        t1_price=5248.0, t2_price=5246.0,
        time_stop_minutes=30, confidence=80,
        bar_index=50, fired_at=datetime.now(timezone.utc),
        sizing_contracts=3,
    )
    assert setup.sizing_contracts == 3
    with pytest.raises(ValidationError):
        T1Setup(
            pattern_name='INITIATIVE_SHORT', direction='SHORT',
            entry_price=5250.0, stop_price=5252.0,
            t1_price=5248.0, t2_price=5246.0,
            time_stop_minutes=30, confidence=80,
            bar_index=50, fired_at=datetime.now(timezone.utc),
            sizing_contracts=5,  # max is 3
        )
