"""Regression test: exit_reason varchar(30) overflow guard (ea868cc).

Trade 303 crashed the DB session because exit_reason='ORDER_FAILED:-1:GENERAL_ERROR_OR_NOT_ENABLED'
(42 chars) exceeded varchar(30). The @validates guard on V9Trade must silently truncate.
"""
from backend.v9.db.models.trades import V9Trade


def test_exit_reason_truncated_at_30():
    """Long exit_reason is truncated, not rejected (anti-tautological: fails without the guard)."""
    t = V9Trade(mode="demo", firing_system=4, direction="LONG", state="CLOSED")
    t.exit_reason = "ORDER_FAILED:-1:GENERAL_ERROR_OR_NOT_ENABLED"
    assert len(t.exit_reason) == 30
    assert t.exit_reason == "ORDER_FAILED:-1:GENERAL_ERROR_"


def test_exit_reason_short_unchanged():
    """Normal-length exit_reason passes through untouched."""
    t = V9Trade(mode="demo", firing_system=4, direction="LONG", state="CLOSED")
    t.exit_reason = "STOP_HIT"
    assert t.exit_reason == "STOP_HIT"


def test_exit_reason_none_ok():
    """None exit_reason is not truncated."""
    t = V9Trade(mode="demo", firing_system=4, direction="LONG", state="PENDING")
    t.exit_reason = None
    assert t.exit_reason is None
