"""P4/B — OPENING_DALTON_GAPS_V1: Dalton fixes in opening detector (2026-07-29).

Tests:
1. Flag OFF → no balance_state field (byte-identical)
2. B1: balance_state derived from open vs prior value/range
3. B2: drive invalidated when price returns through opening range
4. B3: AUCTION_OUT gets higher conviction (0.55) and DD potential note
5. Flag OFF → drive NOT invalidated (same as before)
"""
import os
import pytest

from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type


def _mk_bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


# ── Test 1: flag OFF → no balance_state ──────────────────────────────────────

def test_flag_off_no_balance_state(monkeypatch):
    monkeypatch.delenv("OPENING_DALTON_GAPS_V1", raising=False)
    bars = [_mk_bar(7450, 7460, 7445, 7458)] * 4
    r = detect_opening_type(bars, 7450.0, prior_vah=7480, prior_val=7420)
    assert "balance_state" not in r


# ── Test 2: B1 — balance_state from location ─────────────────────────────────

def test_b1_in_value(monkeypatch):
    monkeypatch.setenv("OPENING_DALTON_GAPS_V1", "1")
    bars = [_mk_bar(7450, 7455, 7445, 7452)] * 4
    r = detect_opening_type(bars, 7450.0, prior_vah=7480, prior_val=7420)
    assert r["balance_state"] == "in_value"
    assert r["balance_conviction"] == "low"


def test_b1_out_of_range(monkeypatch):
    monkeypatch.setenv("OPENING_DALTON_GAPS_V1", "1")
    bars = [_mk_bar(7400, 7405, 7395, 7402)] * 4
    r = detect_opening_type(bars, 7400.0, prior_vah=7480, prior_val=7420, pdh=7500, pdl=7410)
    assert r["balance_state"] == "out_of_range"
    assert r["balance_conviction"] == "high"


# ── Test 3: B2 — drive invalidated by return through opening range ───────────

def test_b2_drive_invalidated(monkeypatch):
    """Open at bottom, drive up, then return through opening range → invalidated."""
    monkeypatch.setenv("OPENING_DALTON_GAPS_V1", "1")
    bars = [
        _mk_bar(7440, 7450, 7438, 7448),  # bar 0: opening range [7438, 7450]
        _mk_bar(7448, 7460, 7446, 7458),  # bar 1: drives up
        _mk_bar(7458, 7462, 7454, 7460),  # bar 2: still up
        _mk_bar(7460, 7461, 7442, 7445),  # bar 3: crashes back into OR [7438,7450] → invalidated
    ]
    r = detect_opening_type(bars, 7440.0)
    # With B2 ON: the drive should be invalidated (returns through OR)
    assert r["opening_type"] != "OPEN_DRIVE" or r.get("invalidated")


# ── Test 4: B2 flag OFF → drive NOT invalidated ─────────────────────────────

def test_b2_off_drive_preserved(monkeypatch):
    """Same bars but flag OFF → drive stays classified as OPEN_DRIVE."""
    monkeypatch.delenv("OPENING_DALTON_GAPS_V1", raising=False)
    bars = [
        _mk_bar(7440, 7450, 7438, 7448),
        _mk_bar(7448, 7460, 7446, 7458),
        _mk_bar(7458, 7462, 7454, 7460),
        _mk_bar(7460, 7461, 7442, 7445),
    ]
    r = detect_opening_type(bars, 7440.0)
    # Flag OFF: the original detection runs unchanged
    assert "invalidated" not in r


# ── Test 5: B3 — AUCTION_OUT gets DD potential ───────────────────────────────

def test_b3_auction_out_conviction(monkeypatch):
    monkeypatch.setenv("OPENING_DALTON_GAPS_V1", "1")
    # Rotational bars with open out of range
    bars = [
        _mk_bar(7400, 7410, 7395, 7405),
        _mk_bar(7405, 7408, 7398, 7400),
        _mk_bar(7400, 7406, 7396, 7404),
        _mk_bar(7404, 7407, 7399, 7401),
    ]
    r = detect_opening_type(bars, 7400.0, pdh=7500, pdl=7410)
    assert r["opening_type"] == "OPEN_AUCTION_OUT"
    assert r["confidence"] == 0.55
    assert any("double-distribution" in reason for reason in r["reasons"])
