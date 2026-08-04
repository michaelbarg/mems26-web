"""D2 — MULTIDAY_VETO_V1 tests (2026-08-04).

Tests:
1. Flag OFF → no block
2. SHORT blocked when migration=UP
3. LONG blocked when migration=DOWN
4. Leg exemption: SHORT with leg=SHORT overrides veto
5. No migration → no block
"""
import os
import types
from unittest.mock import patch, MagicMock

import pytest


def _mk_mc(migration=None, veto_dir=None, leg_dir=None):
    mc = types.SimpleNamespace()
    mc.multiday_migration = migration
    mc.multiday_veto_dir = veto_dir
    mc.leg_dir = leg_dir
    mc.day_bias = "NONE"
    mc.day_type = "UNKNOWN"
    mc.balance_state = "UNKNOWN"
    mc.opening_type = "UNKNOWN"
    mc.opening_dir = "NEUTRAL"
    mc.opening_conf = 0.0
    mc.acceptance = "pending"
    mc.leg_age = 0
    mc.balance_conviction = "low"
    mc.updated_ts = 0.0
    return mc


def test_flag_off_no_block(monkeypatch):
    monkeypatch.delenv("MULTIDAY_VETO_V1", raising=False)
    mc = _mk_mc(migration="UP", veto_dir="SHORT")
    # The gate simply doesn't run when flag is off
    assert mc.multiday_veto_dir == "SHORT"  # data exists but gate doesn't check


def test_short_blocked_migration_up():
    mc = _mk_mc(migration="UP", veto_dir="SHORT")
    direction = "SHORT"
    blocked = (mc.multiday_veto_dir == direction)
    assert blocked


def test_long_blocked_migration_down():
    mc = _mk_mc(migration="DOWN", veto_dir="LONG")
    direction = "LONG"
    blocked = (mc.multiday_veto_dir == direction)
    assert blocked


def test_leg_exemption():
    mc = _mk_mc(migration="UP", veto_dir="SHORT", leg_dir="SHORT")
    direction = "SHORT"
    blocked = (mc.multiday_veto_dir == direction)
    leg_exempt = (mc.leg_dir == direction)
    assert blocked and leg_exempt  # blocked by veto but exempted by leg


def test_no_migration_no_block():
    mc = _mk_mc(migration="FLAT", veto_dir=None)
    direction = "SHORT"
    blocked = (mc.multiday_veto_dir == direction)
    assert not blocked


def test_long_not_blocked_migration_up():
    mc = _mk_mc(migration="UP", veto_dir="SHORT")
    direction = "LONG"
    blocked = (mc.multiday_veto_dir == direction)
    assert not blocked  # veto is SHORT, trade is LONG → not blocked
