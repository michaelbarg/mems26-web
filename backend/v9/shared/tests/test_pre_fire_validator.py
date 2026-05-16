"""Tests for pre_fire_validator (M18 · D-063)."""
import pytest
from pydantic import ValidationError

from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire


def test_valid_long():
    req = FireRequest(
        system_id='T1_NUMBER_BAR', direction='LONG',
        entry_price=5250.0, stop_price=5248.0,
        t1_price=5252.0, t2_price=5254.0,
        time_stop_minutes=60, confidence=75,
    )
    resp = validate_fire(req)
    assert resp.valid is True
    assert resp.fail_reason is None


def test_valid_short():
    req = FireRequest(
        system_id='T2_WOODIES', direction='SHORT',
        entry_price=5250.0, stop_price=5252.0,
        t1_price=5248.0, t2_price=5246.0,
        time_stop_minutes=30, confidence=80,
    )
    resp = validate_fire(req)
    assert resp.valid is True


def test_invalid_stop_side():
    req = FireRequest(
        system_id='T1_NUMBER_BAR', direction='LONG',
        entry_price=5250.0, stop_price=5252.0,  # stop above entry for LONG
        t1_price=5252.0, t2_price=5254.0,
        time_stop_minutes=60, confidence=75,
    )
    resp = validate_fire(req)
    assert resp.valid is False
    assert "stop must be < entry" in resp.fail_reason


def test_invalid_rr():
    req = FireRequest(
        system_id='T1_NUMBER_BAR', direction='LONG',
        entry_price=5250.0, stop_price=5248.0,  # risk = 2
        t1_price=5251.0, t2_price=5252.0,  # reward = 1 (R:R = 0.5)
        time_stop_minutes=60, confidence=75,
    )
    resp = validate_fire(req)
    assert resp.valid is False
    assert "R:R < 1.0" in resp.fail_reason


def test_invalid_system_id():
    with pytest.raises(ValidationError):
        FireRequest(
            system_id='INVALID_SYSTEM', direction='LONG',
            entry_price=5250.0, stop_price=5248.0,
            t1_price=5252.0, t2_price=5254.0,
            time_stop_minutes=60, confidence=75,
        )
