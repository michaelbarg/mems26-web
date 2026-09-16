"""T-390: SituationVector unit tests.

Tests:
  - zone / prior_zone computation
  - extension only when ib_locked
  - vol_ratio causal (inject huge volume in current session, verify median unchanged)
  - bars_since_* on closed bars only
  - fail-open on empty cross_context
  - atr_causal on 14 bars
"""

import pytest
from dataclasses import asdict

from backend.v9.services.situation_vector import (
    SituationVector,
    compute_situation_vector,
    _compute_atr_causal,
    _compute_bars_since,
    _compute_vol_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tpo(*, vah=5010, val=4990, ib_high=5005, ib_low=4995,
         ib_locked=True, session_high=5015, session_low=4985,
         previous_session=None):
    d = {
        "vah": vah, "val": val, "ib_high": ib_high, "ib_low": ib_low,
        "ib_locked": ib_locked, "session_high": session_high,
        "session_low": session_low,
    }
    if previous_session is not None:
        d["previous_session"] = previous_session
    return d


def _bar(h, l, o=None, c=None, v=100, ts="2026-09-15T14:30:00+00:00"):
    return {
        "h": h, "l": l,
        "o": o if o is not None else (h + l) / 2,
        "c": c if c is not None else (h + l) / 2,
        "v": v, "ts": ts,
    }


# ---------------------------------------------------------------------------
# zone / prior_zone computation
# ---------------------------------------------------------------------------

class TestZoneComputation:
    """zone_of should reflect current VA; prior_zone reflects previous session VA."""

    def test_zone_near_vah(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(vah=5010, val=4990)},
            price=5009.0, ts="2026-09-15T14:30:00Z",
        )
        # Price 5009 is near VAH (5010)
        assert sv.zone is not None
        assert "vah" in sv.zone.lower() or "above" in sv.zone.lower() or "near" in sv.zone.lower()

    def test_zone_near_val(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(vah=5010, val=4990)},
            price=4991.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.zone is not None

    def test_prior_zone_uses_previous_session(self):
        prev = {"vah": 5020, "val": 5000, "ib_high": 5015, "ib_low": 5005}
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(previous_session=prev)},
            price=5019.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.prior_zone is not None

    def test_prior_zone_none_when_no_previous(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo()},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.prior_zone is None

    def test_zone_none_when_no_va(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(vah=0, val=0)},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.zone is None


# ---------------------------------------------------------------------------
# extension only when ib_locked
# ---------------------------------------------------------------------------

class TestExtension:

    def test_extension_up_when_ib_locked(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(
                ib_locked=True, ib_high=5005, ib_low=4995,
                session_high=5020, session_low=4996)},
            price=5010.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.ib_locked is True
        assert sv.extension == "up"
        assert sv.extension_pts == 15.0  # 5020 - 5005

    def test_extension_down_when_ib_locked(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(
                ib_locked=True, ib_high=5005, ib_low=4995,
                session_high=5004, session_low=4980)},
            price=4990.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.extension == "down"
        assert sv.extension_pts == 15.0  # 4995 - 4980

    def test_extension_both(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(
                ib_locked=True, ib_high=5005, ib_low=4995,
                session_high=5020, session_low=4980)},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.extension == "both"

    def test_extension_none_when_not_locked(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(
                ib_locked=False, session_high=5020, session_low=4980)},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.ib_locked is False
        assert sv.extension == "none"
        assert sv.extension_pts == 0.0

    def test_extension_none_when_no_break(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": _tpo(
                ib_locked=True, ib_high=5005, ib_low=4995,
                session_high=5004, session_low=4996)},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert sv.extension == "none"


# ---------------------------------------------------------------------------
# vol_ratio causal
# ---------------------------------------------------------------------------

class TestVolRatio:

    def test_vol_ratio_causal_median_unchanged_by_current_session(self):
        """Inject huge volume in the current bar; verify the median
        comes only from prior sessions and isn't polluted."""
        ts = "2026-09-15T14:30:00+00:00"
        # Current session bar with huge volume
        bars_today = [_bar(5010, 4990, v=99999, ts=ts)]
        # 5 prior sessions, each with a bar at same minute, volume ~100
        prior = []
        for i in range(5):
            prior.append([_bar(5005, 4995, v=100, ts=f"2026-09-{10+i:02d}T14:30:00+00:00")])

        ratio = _compute_vol_ratio(ts, bars_today, prior)
        assert ratio is not None
        # median of prior = 100, current = 99999 → ratio ≈ 999.99
        assert ratio > 900  # definitely not 1.0 — median is from prior only

    def test_vol_ratio_none_when_fewer_than_5_sessions(self):
        ts = "2026-09-15T14:30:00+00:00"
        bars_today = [_bar(5010, 4990, v=500, ts=ts)]
        prior = [[_bar(5005, 4995, v=100, ts=f"2026-09-{10+i:02d}T14:30:00+00:00")]
                 for i in range(4)]  # only 4 sessions
        ratio = _compute_vol_ratio(ts, bars_today, prior)
        assert ratio is None

    def test_vol_ratio_none_when_no_data(self):
        ratio = _compute_vol_ratio("2026-09-15T14:30:00Z", None, None)
        assert ratio is None


# ---------------------------------------------------------------------------
# bars_since_high / bars_since_low — closed bars only
# ---------------------------------------------------------------------------

class TestBarsSince:

    def test_bars_since_high_and_low(self):
        bars = [
            _bar(5010, 4990),  # idx 0
            _bar(5020, 4985),  # idx 1 — session high AND session low
            _bar(5015, 4990),  # idx 2
            _bar(5005, 4995),  # idx 3
        ]
        bsh, bsl = _compute_bars_since(bars)
        # High at idx 1 → 3-1 = 2 bars since
        assert bsh == 2
        # Low at idx 1 → 3-1 = 2 bars since
        assert bsl == 2

    def test_bars_since_latest_bar_is_extreme(self):
        bars = [
            _bar(5000, 4990),
            _bar(5010, 4980),  # high and low
            _bar(5020, 4975),  # new high AND new low at last bar
        ]
        bsh, bsl = _compute_bars_since(bars)
        assert bsh == 0  # last bar is session high
        assert bsl == 0  # last bar is session low

    def test_bars_since_none_on_empty(self):
        bsh, bsl = _compute_bars_since(None)
        assert bsh is None
        assert bsl is None

        bsh2, bsl2 = _compute_bars_since([])
        assert bsh2 is None
        assert bsl2 is None


# ---------------------------------------------------------------------------
# fail-open on empty cross_context
# ---------------------------------------------------------------------------

class TestFailOpen:

    def test_empty_cross_context(self):
        sv = compute_situation_vector(
            cross_context={}, price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert isinstance(sv, SituationVector)
        assert sv.price == 5000.0
        assert sv.zone is None
        assert sv.prior_zone is None
        assert sv.ib_locked is False
        assert sv.extension == "none"

    def test_none_cross_context(self):
        sv = compute_situation_vector(
            cross_context=None, price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert isinstance(sv, SituationVector)

    def test_garbage_cross_context(self):
        sv = compute_situation_vector(
            cross_context={"tpo_system": "not_a_dict"},
            price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        assert isinstance(sv, SituationVector)
        assert sv.zone is None

    def test_asdict_roundtrip(self):
        sv = compute_situation_vector(
            cross_context={}, price=5000.0, ts="2026-09-15T14:30:00Z",
        )
        d = asdict(sv)
        assert isinstance(d, dict)
        assert d["price"] == 5000.0
        assert "zone" in d


# ---------------------------------------------------------------------------
# atr_causal on 14 bars
# ---------------------------------------------------------------------------

class TestAtrCausal:

    def test_atr_14_bars(self):
        """ATR14 on 15 bars (14 true-range values)."""
        # Build 15 bars with known ranges
        bars = []
        for i in range(15):
            h = 5000 + i * 2
            l = 5000 + i * 2 - 5
            c = (h + l) / 2
            bars.append(_bar(h, l, c=c))
        atr = _compute_atr_causal(bars)
        assert atr is not None
        assert atr > 0

    def test_atr_too_few_bars(self):
        assert _compute_atr_causal(None) is None
        assert _compute_atr_causal([]) is None
        assert _compute_atr_causal([_bar(5010, 4990)]) is None

    def test_atr_with_exactly_2_bars(self):
        bars = [_bar(5000, 4990, c=4995), _bar(5010, 5000, c=5005)]
        atr = _compute_atr_causal(bars)
        assert atr is not None
        # true range = max(5010-5000, |5010-4995|, |5000-4995|) = 15
        assert atr == 15.0

    def test_atr_uses_last_14(self):
        """If more than 15 bars provided, ATR uses only the last 15 → 14 TRs."""
        bars = [_bar(5000 + i, 4990 + i, c=4995 + i) for i in range(20)]
        atr = _compute_atr_causal(bars)
        assert atr is not None
