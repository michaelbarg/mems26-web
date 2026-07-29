"""P2 — OPENING_RUNNER_RIDE_V1: structural trailing for opening runners (2026-07-29).

Tests:
1. Flag OFF → compute_structural_trail returns None (byte-identical)
2. LONG trail: lowest low of 6-bar window − 1pt buffer
3. SHORT trail: highest high of 6-bar window + 1pt buffer
4. LSMA cross: LONG + RED → exit; LONG + BLUE → hold
5. Insufficient bars → None (honest, Rule 1)
6. Replay 07-28: ORR-long from ~7433 should trail to hold past 7470
"""
import os
import pytest

from backend.v9.systems.opening_runner import (
    compute_structural_trail, should_exit_lsma_cross,
)


def _mk_bars(lows, highs):
    return [{"l": l, "h": h, "c": (l + h) / 2} for l, h in zip(lows, highs)]


def test_flag_off_returns_none(monkeypatch):
    monkeypatch.delenv("OPENING_RUNNER_RIDE_V1", raising=False)
    bars = _mk_bars([7440, 7442, 7445, 7448, 7450, 7452],
                    [7450, 7455, 7458, 7460, 7462, 7465])
    assert compute_structural_trail(direction="LONG", bars=bars) is None


def test_long_trail(monkeypatch):
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    bars = _mk_bars([7440, 7442, 7445, 7448, 7450, 7452],
                    [7450, 7455, 7458, 7460, 7462, 7465])
    trail = compute_structural_trail(direction="LONG", bars=bars)
    # min low = 7440, buffer = 4 ticks × 0.25 = 1pt → trail = 7439
    assert trail == 7439.0


def test_short_trail(monkeypatch):
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    bars = _mk_bars([7440, 7438, 7435, 7432, 7430, 7428],
                    [7450, 7448, 7445, 7442, 7440, 7438])
    trail = compute_structural_trail(direction="SHORT", bars=bars)
    # max high = 7450, buffer = 1pt → trail = 7451
    assert trail == 7451.0


def test_lsma_cross_exit(monkeypatch):
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    assert should_exit_lsma_cross(direction="LONG", trend_state="RED") is True
    assert should_exit_lsma_cross(direction="LONG", trend_state="BLUE") is False
    assert should_exit_lsma_cross(direction="SHORT", trend_state="BLUE") is True
    assert should_exit_lsma_cross(direction="SHORT", trend_state="RED") is False


def test_lsma_none_holds(monkeypatch):
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    assert should_exit_lsma_cross(direction="LONG", trend_state=None) is False


def test_insufficient_bars(monkeypatch):
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    bars = _mk_bars([7440, 7442], [7450, 7455])
    assert compute_structural_trail(direction="LONG", bars=bars) is None


def test_replay_0728_orr_long_holds(monkeypatch):
    """07-28 scenario: ORR LONG from ~7433 area. The 30-min trail should hold
    well below the rising price, allowing the runner to ride to 7470+."""
    monkeypatch.setenv("OPENING_RUNNER_RIDE_V1", "1")
    # Simulated bars from 07-28 afternoon rally: lows climbing from 7430→7460
    bars = _mk_bars(
        [7430, 7433, 7438, 7442, 7448, 7452, 7455, 7458, 7460, 7463],
        [7440, 7445, 7450, 7455, 7460, 7465, 7468, 7470, 7472, 7475],
    )
    trail = compute_structural_trail(direction="LONG", bars=bars, window=6)
    # Last 6 bars: lows = [7452, 7455, 7458, 7460, 7463] (min=7452) → trail = 7451
    # Price at 7475 → trail at 7451 = runner holds (24pt room)
    assert trail is not None
    assert trail < 7460  # trail well below current price
    assert trail > 7420  # not unreasonably far
