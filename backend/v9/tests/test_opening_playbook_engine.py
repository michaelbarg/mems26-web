"""P1 — OPENING_PLAYBOOK_V1: per-opening-type trade templates (2026-07-29).

Tests:
1. Flag OFF → resolve() returns None (byte-identical)
2. Flag ON + known type → returns correct template
3. Flag ON + unknown type → returns None (fail-open)
4. Gate exemption: OPEN_DRIVE exempt from awaiting_release
5. Gate exemption: non-exempt gate returns False
6. AUCTION_IN has no runner
"""
import os
import pytest

from backend.v9.systems.opening_playbook_engine import (
    resolve, is_gate_exempt, reset_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_cache()
    yield
    reset_cache()


def test_flag_off_returns_none(monkeypatch):
    monkeypatch.delenv("OPENING_PLAYBOOK_V1", raising=False)
    assert resolve("OPEN_DRIVE") is None


def test_flag_on_open_drive(monkeypatch):
    monkeypatch.setenv("OPENING_PLAYBOOK_V1", "1")
    t = resolve("OPEN_DRIVE")
    assert t is not None
    assert t.opening_type == "OPEN_DRIVE"
    assert t.entry == "close_beyond_opening_range"
    assert t.stop == "opposite_side_of_opening_range"
    assert t.t1 == "1.5R"
    assert t.runner == "structural_trail_30min"
    assert t.invalidation == "return_through_opening"


def test_flag_on_unknown_type(monkeypatch):
    monkeypatch.setenv("OPENING_PLAYBOOK_V1", "1")
    assert resolve("NONEXISTENT_TYPE") is None


def test_gate_exempt_awaiting_release(monkeypatch):
    monkeypatch.setenv("OPENING_PLAYBOOK_V1", "1")
    assert is_gate_exempt("OPEN_DRIVE", "awaiting_release") is True
    assert is_gate_exempt("ORR", "lsma_flat") is True


def test_gate_not_exempt_chase(monkeypatch):
    monkeypatch.setenv("OPENING_PLAYBOOK_V1", "1")
    assert is_gate_exempt("OPEN_DRIVE", "chase") is False
    assert is_gate_exempt("OPEN_DRIVE", "margin") is False


def test_auction_in_no_runner(monkeypatch):
    monkeypatch.setenv("OPENING_PLAYBOOK_V1", "1")
    t = resolve("AUCTION_IN")
    assert t is not None
    assert t.runner == "none"
    assert t.t1 == "1.0R"
