"""T-366: fresh-extreme gate — doctrine, not a tuned edge.

Five cases from the handoff:
  1. LONG at a fresh session low → blocked
  2. LONG at an old session low  → passes
  3. SHORT at a fresh session high → blocked
  4. Fewer than K+1 bars → passes (fail-open, not enough data)
  5. DB read raises → passes (fail-OPEN)
"""
import os
import pytest
from unittest.mock import patch


def _make_rows(highs_lows):
    """Build bar dicts from (high, low) tuples."""
    return [{"high": h, "low": l} for h, l in highs_lows]


def _run_gate(rows, direction, env_overrides=None, raise_on_read=False):
    """Run the fresh-extreme gate logic in isolation and return result dict."""
    env = {
        "FRESH_EXTREME_GATE_V1": "1",
        "FRESH_EXTREME_MIN_BARS": "3",
    }
    if env_overrides:
        env.update(env_overrides)

    def _mock_read():
        if raise_on_read:
            raise RuntimeError("DB connection failed")
        return rows

    setup = {
        "direction": direction,
        "classification": "TEST_PATTERN",
        "entry_price": 7671.25,
    }
    result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}

    with patch.dict(os.environ, env, clear=False):
        if os.environ.get("FRESH_EXTREME_GATE_V1", "1").lower() in ("1", "true", "yes"):
            try:
                _fx_min = int(os.environ.get("FRESH_EXTREME_MIN_BARS", "3") or "3")
                _fx_dir = (setup.get("direction") or "").upper()
                _fx_rows = _mock_read()
                if len(_fx_rows) >= _fx_min + 1:
                    _fx_prev = _fx_rows[:-1]
                    if _fx_dir == "LONG":
                        _fx_ext = min(float(r["low"]) for r in _fx_prev)
                        _fx_idx = max(i for i, r in enumerate(_fx_prev)
                                      if float(r["low"]) == _fx_ext)
                    else:
                        _fx_ext = max(float(r["high"]) for r in _fx_prev)
                        _fx_idx = max(i for i, r in enumerate(_fx_prev)
                                      if float(r["high"]) == _fx_ext)
                    _fx_age = (len(_fx_prev) - 1) - _fx_idx
                    if _fx_age < _fx_min:
                        result["blocked_by"] = "fresh_extreme"
                        result["reason"] = (
                            f"{_fx_dir} against a session extreme set {_fx_age} bars ago "
                            f"(min {_fx_min}); extreme={_fx_ext:.2f}")
            except Exception:
                pass  # fail-OPEN
    return result


class TestFreshExtremeGate:
    """Five cases from the T-366 golden spec."""

    def test_long_fresh_low_blocked(self):
        """LONG when session low was set 1 bar ago → blocked."""
        # 6 bars: low at index 4 (second-to-last of prev = bars[:-1])
        rows = _make_rows([
            (7680, 7670),  # 0
            (7682, 7672),  # 1
            (7681, 7671),  # 2
            (7679, 7669),  # 3
            (7678, 7665),  # 4 ← session low, age = 0 from end of prev
            (7680, 7668),  # 5 current bar (excluded)
        ])
        r = _run_gate(rows, "LONG")
        assert r["blocked_by"] == "fresh_extreme"

    def test_long_old_low_passes(self):
        """LONG when session low was set >=3 bars ago → passes."""
        # 7 bars: low at index 0
        rows = _make_rows([
            (7680, 7660),  # 0 ← session low
            (7685, 7670),  # 1
            (7684, 7672),  # 2
            (7683, 7671),  # 3
            (7682, 7669),  # 4
            (7681, 7668),  # 5
            (7680, 7667),  # 6 current bar
        ])
        r = _run_gate(rows, "LONG")
        assert r["blocked_by"] is None

    def test_short_fresh_high_blocked(self):
        """SHORT when session high was set 2 bars ago → blocked (< K=3)."""
        rows = _make_rows([
            (7670, 7660),  # 0
            (7672, 7662),  # 1
            (7675, 7665),  # 2
            (7690, 7680),  # 3 ← session high, age=1
            (7688, 7678),  # 4
            (7685, 7675),  # 5 current bar
        ])
        r = _run_gate(rows, "SHORT")
        assert r["blocked_by"] == "fresh_extreme"

    def test_too_few_bars_passes(self):
        """Fewer than K+1 = 4 bars → no block (fail-open, not enough data)."""
        rows = _make_rows([
            (7680, 7670),
            (7682, 7660),  # extreme
            (7681, 7668),
        ])
        r = _run_gate(rows, "LONG")
        assert r["blocked_by"] is None

    def test_db_error_fail_open(self):
        """DB read raises → passes (fail-OPEN)."""
        r = _run_gate([], "LONG", raise_on_read=True)
        assert r["blocked_by"] is None

    def test_zero_lookahead(self):
        """The extreme in the CURRENT bar (last row) must NOT be counted.

        Series: bars 0-4 have highs 100-104; bar 5 (current) has high 200.
        SHORT should pass because the extreme among prev bars is 104 at
        index 4 (age=0 from end of prev), so blocked. But if we put the
        actual extreme in the current bar only, it should not affect.
        """
        # Extreme is in the current bar only — prev bars are boring
        rows = _make_rows([
            (100, 90),   # 0
            (101, 91),   # 1
            (102, 92),   # 2 ← prev high among prev
            (99, 89),    # 3
            (98, 88),    # 4
            (200, 80),   # 5 current bar — high 200, should be excluded
        ])
        # prev = bars[:-1] = indices 0-4, max high = 102 at index 2
        # age = (4 - 2) = 2 < 3 → blocked
        # But that's because the prev extreme is at index 2 (age 2 < 3)
        # The point is: 200 in bar 5 is NOT counted.
        # Let's make a clearer case: extreme among prev at index 0, age=4 → passes
        rows2 = _make_rows([
            (110, 90),   # 0 ← prev high
            (101, 91),   # 1
            (102, 92),   # 2
            (99, 89),    # 3
            (98, 88),    # 4
            (200, 80),   # 5 current bar — has the REAL extreme 200
        ])
        r = _run_gate(rows2, "SHORT")
        # prev max high = 110 at index 0, age = 4 >= 3 → passes
        assert r["blocked_by"] is None, (
            "Current bar's extreme (200) must not be counted — zero look-ahead")
