"""W6 — HIGHER_LOW_SECOND_TEST_V1: higher-low second test pattern (2026-07-25).

Tests:
1. Flag OFF → no detection (byte-identical)
2. Flag ON + valid structure → LONG detected with correct L1/L2/entry
3. Flag ON + L2 <= L1 (not higher-low) → no detection
4. Flag ON + insufficient recovery → no detection
5. Flag ON + SHORT symmetric structure → SHORT detected
6. Rejection bar not in upper half → no detection
7. revert→RED: tests 2,5 fail without the code
"""
import os
import pytest


def _bars_higher_low_long():
    """Synthetic fixture: push up 7440→7460 (20pt), pullback to L1=7448,
    recovery to 7458, second dip to L2=7451 (higher-low: 7451 > 7448+0.5),
    rejection bar with close at 7455 (upper half, above L2).
    """
    return [
        # Push up phase
        {"high": 7445, "low": 7438, "close": 7444, "open": 7440},
        {"high": 7450, "low": 7443, "close": 7449, "open": 7444},
        {"high": 7456, "low": 7448, "close": 7455, "open": 7449},
        {"high": 7462, "low": 7454, "close": 7460, "open": 7455},  # peak
        # First pullback to L1=7448
        {"high": 7458, "low": 7452, "close": 7453, "open": 7460},
        {"high": 7454, "low": 7448, "close": 7449, "open": 7453},  # L1=7448
        # Recovery (7449 → 7458 = 10pt, recovery 10/20 = 50% > 33%)
        {"high": 7455, "low": 7449, "close": 7454, "open": 7449},
        {"high": 7458, "low": 7453, "close": 7457, "open": 7454},  # recovery peak
        # Second dip to L2=7451 (higher-low: 7451 > 7448 + 0.5)
        {"high": 7456, "low": 7451, "close": 7452, "open": 7457},
        # Rejection bar: close in upper half above L2
        {"high": 7456, "low": 7451, "close": 7455, "open": 7452},  # close=7455, upper half
    ]


def _bars_not_higher_low():
    """Structure where L2 <= L1 (not a higher-low)."""
    return [
        {"high": 7445, "low": 7438, "close": 7444, "open": 7440},
        {"high": 7450, "low": 7443, "close": 7449, "open": 7444},
        {"high": 7456, "low": 7448, "close": 7455, "open": 7449},
        {"high": 7462, "low": 7454, "close": 7460, "open": 7455},
        {"high": 7458, "low": 7452, "close": 7453, "open": 7460},
        {"high": 7454, "low": 7448, "close": 7449, "open": 7453},  # L1=7448
        {"high": 7455, "low": 7449, "close": 7454, "open": 7449},
        {"high": 7458, "low": 7453, "close": 7457, "open": 7454},
        # L2=7447 <= L1=7448 (NOT higher-low)
        {"high": 7456, "low": 7447, "close": 7452, "open": 7457},
        {"high": 7456, "low": 7447, "close": 7455, "open": 7452},
    ]


def _bars_higher_low_short():
    """Symmetric SHORT fixture: push down 7480→7460 (20pt), rally to H1=7472,
    drop, second rally to H2=7469 (lower-high: 7469 < 7472-0.5),
    rejection bar closing in lower half below H2.
    """
    return [
        # Push down phase
        {"high": 7482, "low": 7476, "close": 7477, "open": 7480},
        {"high": 7478, "low": 7470, "close": 7471, "open": 7477},
        {"high": 7472, "low": 7464, "close": 7465, "open": 7471},
        {"high": 7466, "low": 7458, "close": 7460, "open": 7465},  # trough
        # First rally to H1=7472
        {"high": 7466, "low": 7460, "close": 7464, "open": 7460},
        {"high": 7472, "low": 7463, "close": 7471, "open": 7464},  # H1=7472
        # Drop (recovery for SHORT)
        {"high": 7470, "low": 7462, "close": 7463, "open": 7471},
        {"high": 7464, "low": 7458, "close": 7459, "open": 7463},  # drop trough
        # Second rally to H2=7469 (lower-high: 7469 < 7472 - 0.5)
        {"high": 7469, "low": 7460, "close": 7467, "open": 7459},
        # Rejection bar: close in lower half, below H2
        {"high": 7469, "low": 7462, "close": 7463, "open": 7467},  # close in lower half
    ]


# ── Test 1: Flag OFF → no detection ──────────────────────────────────────────

def test_flag_off_no_detection(monkeypatch):
    monkeypatch.delenv("HIGHER_LOW_SECOND_TEST_V1", raising=False)
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
    )
    d, c, info = detect_higher_low_second_test_long(_bars_higher_low_long())
    assert d is None
    assert c == 0.0
    assert info == {}


# ── Test 2: Flag ON + valid structure → LONG ─────────────────────────────────

def test_higher_low_long_detected(monkeypatch):
    monkeypatch.setenv("HIGHER_LOW_SECOND_TEST_V1", "1")
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
    )
    d, c, info = detect_higher_low_second_test_long(_bars_higher_low_long())
    assert d == "LONG"
    assert c > 0
    assert info["kind"] == "HIGHER_LOW_SECOND_TEST"
    assert info["pattern_name"] == "HIGHER_LOW_SECOND_TEST_LONG"
    assert info["L2"] > info["L1"]  # higher-low
    assert info["recovery_pct"] >= 0.33
    assert info["structural_anchor"] == info["L2"]


# ── Test 3: L2 <= L1 → no detection ──────────────────────────────────────────

def test_not_higher_low_rejected(monkeypatch):
    monkeypatch.setenv("HIGHER_LOW_SECOND_TEST_V1", "1")
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
    )
    d, c, info = detect_higher_low_second_test_long(_bars_not_higher_low())
    assert d is None


# ── Test 4: Insufficient recovery → no detection ─────────────────────────────

def test_insufficient_recovery_rejected(monkeypatch):
    monkeypatch.setenv("HIGHER_LOW_SECOND_TEST_V1", "1")
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
    )
    # Build a structure where recovery < 33%: push 20pt, pullback to L1=7448,
    # then recover only 4pt (20% < 33%)
    bars = [
        {"high": 7445, "low": 7438, "close": 7444, "open": 7440},
        {"high": 7450, "low": 7443, "close": 7449, "open": 7444},
        {"high": 7456, "low": 7448, "close": 7455, "open": 7449},
        {"high": 7462, "low": 7454, "close": 7460, "open": 7455},  # peak 7462
        {"high": 7458, "low": 7452, "close": 7453, "open": 7460},
        {"high": 7454, "low": 7442, "close": 7443, "open": 7453},  # L1=7442
        # Recovery only to 7446 = 4pt / 24pt push = 17% < 33%
        {"high": 7446, "low": 7443, "close": 7445, "open": 7443},
        {"high": 7446, "low": 7444, "close": 7445, "open": 7445},  # recovery peak only 7446
        {"high": 7446, "low": 7443, "close": 7444, "open": 7445},
        {"high": 7446, "low": 7443, "close": 7445, "open": 7444},
    ]
    d, c, info = detect_higher_low_second_test_long(bars)
    assert d is None


# ── Test 5: SHORT symmetric → detected ───────────────────────────────────────

def test_higher_low_short_detected(monkeypatch):
    monkeypatch.setenv("HIGHER_LOW_SECOND_TEST_V1", "1")
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_short,
    )
    d, c, info = detect_higher_low_second_test_short(_bars_higher_low_short())
    assert d == "SHORT"
    assert info["kind"] == "HIGHER_LOW_SECOND_TEST"
    assert info["pattern_name"] == "HIGHER_LOW_SECOND_TEST_SHORT"
    # For SHORT: H2 < H1 (lower-high)
    assert info["L2"] < info["L1"]  # L1=H1, L2=H2 in the info dict


# ── Test 6: Rejection bar not in upper half → no detection ────────────────────

def test_bad_rejection_bar_rejected(monkeypatch):
    monkeypatch.setenv("HIGHER_LOW_SECOND_TEST_V1", "1")
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
    )
    bars = _bars_higher_low_long()
    # Make last bar close in lower half (bearish, not bullish rejection)
    bars[-1] = {"high": 7456, "low": 7451, "close": 7452, "open": 7455}
    d, c, info = detect_higher_low_second_test_long(bars)
    assert d is None
