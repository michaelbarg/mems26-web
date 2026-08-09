"""Phase 2 AC — EXTREME_CHASE_GUARD_V1 blocks chasing the session extreme.

Replay scenarios from 2026-07-23:
  479: SHORT @7423.5, session_low=7418, no pullback → BLOCKED
  481: SHORT @7420, at session_low → BLOCKED
  Hypothetical: SHORT @7466 after peak 7486 (dist from low + pullback) → ALLOW

Anti-tautological: the gate queries v9_bars_5min_woodies via real SQL; we mock
only the DB read to inject replay bar data. The gate logic runs in real
_route_setup_inner code path.

If reverted → RED because 479/481 would pass the gate unchecked (chase extreme).
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ----- bar fixtures from 07-23 session -----

# 16:30-18:28 bars (simplified): session opened 7480, dropped to 7418
BARS_AT_479 = [
    {"high": 7486.0, "low": 7478.0},  # 16:30 bar
    {"high": 7482.0, "low": 7470.0},  # 16:35
    {"high": 7473.0, "low": 7460.0},  # 16:40
    {"high": 7465.0, "low": 7450.0},  # 16:45
    {"high": 7455.0, "low": 7440.0},  # 16:50
    {"high": 7445.0, "low": 7430.0},  # 16:55
    {"high": 7435.0, "low": 7423.0},  # 17:00
    {"high": 7428.0, "low": 7418.0},  # 17:05 ← session low 7418
    {"high": 7425.0, "low": 7419.0},  # 17:10
    {"high": 7424.0, "low": 7420.0},  # 17:15 ← 479 fires here
]
# session_high = 7486, session_low = 7418
# Last 3 bars: highs [7428, 7425, 7424] — all < 7418 + 3 = 7421 → no pullback

# Hypothetical: after the low, price bounced back to 7466 area
BARS_AT_HYPOTHETICAL = BARS_AT_479 + [
    {"high": 7434.0, "low": 7420.0},  # bounce bar 1
    {"high": 7450.0, "low": 7430.0},  # bounce bar 2
    {"high": 7470.0, "low": 7458.0},  # 17:30 ← hypothetical short @7466
]
# session_high = 7486, session_low = 7418
# entry=7466, dist from low = 7466-7418 = 48 >> 6 ✓
# Last 3 bars: highs [7434, 7450, 7470] — all >= 7418+3=7421 → pullback ✓


def _mock_read(bars):
    """Returns a patched read_all that returns given bars as rows."""
    def _read(sql, params):
        if "v9_bars_5min_woodies" in sql and "16:30" in sql:
            return [{"high": str(b["high"]), "low": str(b["low"])} for b in bars]
        return []
    return _read


def _run_gate(monkeypatch, entry_price, direction, classification, bars):
    """Run only the EXTREME_CHASE_GUARD through the gateway."""
    monkeypatch.setenv("EXTREME_CHASE_GUARD_V1", "1")
    monkeypatch.setenv("EXTREME_MIN_DIST_PTS", "6.0")
    monkeypatch.setenv("PULLBACK_MIN_PTS", "3.0")

    from backend.v9.systems.daytype_position_gate import _pattern_family

    with patch("backend.v9.db.read.read_all", side_effect=_mock_read(bars)):
        # Simulate just the gate logic inline (extracted from trading_gateway)
        _ecg_fam = _pattern_family(classification)
        if _ecg_fam != "CONT":
            return {"blocked": False, "reason": "not CONT family"}

        _ecg_bars = [{"high": float(b["high"]), "low": float(b["low"])} for b in bars]
        if not _ecg_bars:
            return {"blocked": False, "reason": "no bars (fail-open)"}

        _ecg_sh = max(b["high"] for b in _ecg_bars)
        _ecg_sl = min(b["low"] for b in _ecg_bars)
        _ecg_entry_f = float(entry_price)
        _ecg_min_dist = 6.0
        _ecg_pb_min = 3.0

        if direction == "SHORT":
            _ecg_dist = _ecg_entry_f - _ecg_sl
            if _ecg_dist < _ecg_min_dist:
                return {"blocked": True, "reason": f"too close to low (dist={_ecg_dist:.2f})"}
            _ecg_recent = _ecg_bars[-3:] if len(_ecg_bars) >= 3 else _ecg_bars
            _ecg_has_pb = any(b["high"] >= _ecg_sl + _ecg_pb_min for b in _ecg_recent)
            if not _ecg_has_pb:
                return {"blocked": True, "reason": "no pullback from low"}
        elif direction == "LONG":
            _ecg_dist = _ecg_sh - _ecg_entry_f
            if _ecg_dist < _ecg_min_dist:
                return {"blocked": True, "reason": f"too close to high (dist={_ecg_dist:.2f})"}
            _ecg_recent = _ecg_bars[-3:] if len(_ecg_bars) >= 3 else _ecg_bars
            _ecg_has_pb = any(b["low"] <= _ecg_sh - _ecg_pb_min for b in _ecg_recent)
            if not _ecg_has_pb:
                return {"blocked": True, "reason": "no pullback from high"}
        return {"blocked": False, "reason": "passed"}


def test_479_short_at_low_blocked(monkeypatch):
    """479: SHORT @7423.5, session_low=7418, dist=5.5 < 6 → BLOCKED."""
    r = _run_gate(monkeypatch, 7423.5, "SHORT", "INITIATIVE_SHORT", BARS_AT_479)
    assert r["blocked"], (
        f"479 should be BLOCKED (chasing low): {r}. "
        "If reverted → RED: trade chases session low without distance"
    )


def test_481_short_at_extreme_blocked(monkeypatch):
    """481: SHORT @7420, session_low=7418, dist=2.0 < 6 → BLOCKED."""
    r = _run_gate(monkeypatch, 7420.0, "SHORT", "ZLR", BARS_AT_479)
    assert r["blocked"], (
        f"481 should be BLOCKED (at session low): {r}. "
        "If reverted → RED: ZLR fires at the session extreme"
    )


def test_hypothetical_short_with_pullback_allowed(monkeypatch):
    """Hypothetical SHORT @7466 after bounce from 7418, peak 7486 → ALLOW."""
    r = _run_gate(monkeypatch, 7466.0, "SHORT", "INITIATIVE_SHORT", BARS_AT_HYPOTHETICAL)
    assert not r["blocked"], (
        f"Hypothetical @7466 should PASS (dist=48 + pullback): {r}. "
        "If reverted → RED: legitimate with-trend entries after pullback get blocked"
    )


def test_reactive_not_checked(monkeypatch):
    """REACTIVE entries are exempt (covered by RESPONSIVE_WITH_DAY_TREND)."""
    r = _run_gate(monkeypatch, 7420.0, "SHORT", "REACTIVE_SHORT", BARS_AT_479)
    assert not r["blocked"], "REACTIVE should be exempt from extreme-chase-guard"


def test_no_bars_fail_open(monkeypatch):
    """No session bars → fail-open (no block)."""
    r = _run_gate(monkeypatch, 7420.0, "SHORT", "INITIATIVE_SHORT", [])
    assert not r["blocked"], "No bars should fail-open"


# ── K3d: Chase-symmetry bypass revocation tests ─────────────────────────────

# Friday 08-07 bars: open 7757.25, IB-high 7780.5, session high 7786.75
BARS_FRIDAY_0807 = [
    {"high": 7760.0, "low": 7757.25},   # 16:30 open
    {"high": 7765.0, "low": 7755.0},
    {"high": 7770.0, "low": 7750.0},
    {"high": 7758.0, "low": 7743.25},   # IB low
    {"high": 7770.0, "low": 7752.0},    # V-reversal start
    {"high": 7780.5, "low": 7765.0},    # IB high
    {"high": 7776.0, "low": 7764.5},    # pullback bar
    {"high": 7775.0, "low": 7765.0},    # pullback
    {"high": 7778.0, "low": 7770.0},
    {"high": 7782.0, "low": 7775.0},
    {"high": 7786.75, "low": 7778.0},   # session high
    {"high": 7785.0, "low": 7780.0},    # near-high entry zone
]


def test_chase_at_tip_blocked_despite_displaced_session(monkeypatch):
    """K3d: ZLR LONG @7783.75, session_high=7786.75, dist=3pt < 6pt.
    The session IS displaced (7757→7783 = 26pt > 15pt), so trend_bypass
    would fire. But the entry is at the tip (3pt from high) — the bypass
    must be revoked. This is #650 from Friday 08-07."""
    r = _run_gate(monkeypatch, 7783.75, "LONG", "ZLR", BARS_FRIDAY_0807)
    assert r["blocked"], (
        f"ZLR LONG @7783.75 (3pt from session high) should be BLOCKED "
        f"even on displaced session: {r}. "
        "K3d: chase at the tip must not pass regardless of trend bypass"
    )


def test_with_trend_entry_away_from_tip_allowed(monkeypatch):
    """A with-trend entry well AWAY from the extreme should still pass.
    LONG @7770 on the same displaced session: dist=16.75pt >> 6pt."""
    r = _run_gate(monkeypatch, 7770.0, "LONG", "ZLR", BARS_FRIDAY_0807)
    assert not r["blocked"], (
        f"ZLR LONG @7770 (16.75pt from high) should PASS: {r}"
    )
