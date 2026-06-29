"""Anti-tautological tests for CONT_TREND_FILTER (2026-06-25).

Continuation patterns fire only WITH a sustained K-bar LSMA trend; reversals exempt.
Fixes the BULL_FLAG_LONG chop bug (2026-06-24 10:25): a momentary 1-bar poke above
LSMA in chop passed the single-bar veto. sustained_lsma_side requires K consecutive
bars on the same side → chop returns NEUTRAL → the continuation is blocked.

if reverted -> RED because: removing the all-same-side check makes a mixed/chop
sequence return a direction (UP/DOWN) instead of NEUTRAL, so test_chop_mixed_is_neutral
and test_one_bar_poke_against_two_is_neutral fail.
"""
from backend.v9.systems.direction_context_live import sustained_lsma_side
from backend.v9.systems.woodies.pattern_engine import REVERSAL_PATTERNS


def _rows(sides):
    """sides: +1 (close above lsma) / -1 (below), MOST-RECENT FIRST (ORDER BY ts DESC)."""
    return [{"close": 100.0 + s, "lsma_value": 100.0} for s in sides]


def test_sustained_all_above_is_up():
    assert sustained_lsma_side(_rows([1, 1, 1]), 3) == "UP"


def test_sustained_all_below_is_down():
    assert sustained_lsma_side(_rows([-1, -1, -1]), 3) == "DOWN"


def test_chop_mixed_is_neutral():
    # The 2026-06-24 10:25 bull-flag bug: ABOVE / BELOW / ABOVE -> chop -> NEUTRAL (blocked)
    assert sustained_lsma_side(_rows([1, -1, 1]), 3) == "NEUTRAL"


def test_one_bar_poke_against_two_is_neutral():
    assert sustained_lsma_side(_rows([1, 1, -1]), 3) == "NEUTRAL"


def test_too_few_bars_is_neutral():
    assert sustained_lsma_side(_rows([1, 1]), 3) == "NEUTRAL"


def test_k1_reproduces_single_bar_behavior():
    # K=1 == the OLD single-bar veto (a momentary poke passes) — proves the filter
    # is what changes behavior, not the query.
    assert sustained_lsma_side(_rows([1]), 1) == "UP"
    assert sustained_lsma_side(_rows([-1, 1, 1]), 1) == "DOWN"  # only most-recent matters


def test_empty_is_neutral():
    assert sustained_lsma_side([], 3) == "NEUTRAL"
    assert sustained_lsma_side(None, 3) == "NEUTRAL"


# ── Reversal patterns are EXEMPT (fire against the trend by design) ──
def test_reversal_patterns_exempt():
    for p in ("VEGAS", "GHOST", "FAMIR", "HTLB"):
        assert p in REVERSAL_PATTERNS, "%s must be exempt — reversal fires against trend" % p


def test_continuation_patterns_filtered():
    for p in ("ZLR", "TLB", "TT", "GB100"):
        assert p not in REVERSAL_PATTERNS, "%s is continuation -> trend-filtered" % p


# ── Unified CONT/REV family (single source of truth in daytype_position_gate) ──
# if reverted → RED because removing the unified map re-introduces the S2 gap:
# REACTIVE is a reversal pattern that must be exempt from CONT_TREND_FILTER.

def test_unified_family_s2_rev_exempt():
    """S2 reversal patterns (REACTIVE, HnS, Double) are REV in the unified map.
    Without this, CONT_TREND_FILTER blocks REACTIVE against-trend fires (the bug)."""
    from backend.v9.systems.daytype_position_gate import _pattern_family
    for p in ("REACTIVE", "REACTIVE_LONG", "REACTIVE_SHORT",
              "INVERSE_HNS_LONG", "HNS_TOP_SHORT",
              "DOUBLE_BOTTOM_EE_LONG", "DOUBLE_TOP_AA_SHORT"):
        assert _pattern_family(p) == "REV", f"{p} must be REV (exempt from trend filter)"


def test_unified_family_s2_cont_filtered():
    """S2 continuation patterns (INITIATIVE, BULL_FLAG) are CONT in the unified map."""
    from backend.v9.systems.daytype_position_gate import _pattern_family
    for p in ("INITIATIVE", "INITIATIVE_LONG", "INITIATIVE_SHORT",
              "BULL_FLAG_LONG", "BEAR_FLAG_SHORT"):
        assert _pattern_family(p) == "CONT", f"{p} must be CONT (trend-filtered)"


def test_unified_family_s4_consistent():
    """S4 patterns in the unified map match pattern_engine classification."""
    from backend.v9.systems.daytype_position_gate import _pattern_family
    for p in ("ZLR", "TLB", "TT", "GB100"):
        assert _pattern_family(p) == "CONT", f"{p} must be CONT"
    for p in ("VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"):
        assert _pattern_family(p) == "REV", f"{p} must be REV"


def test_unknown_pattern_no_family():
    """Unknown pattern → None (fail-open, not filtered)."""
    from backend.v9.systems.daytype_position_gate import _pattern_family
    assert _pattern_family("UNKNOWN_SETUP") is None
    assert _pattern_family(None) is None
    assert _pattern_family("") is None
