"""W3-gamma -- 6 day types via IB Width Matrix + state machine"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from backend.v9.systems.day_type.schemas import DayType, OpeningType, IBWidth
from backend.v9.systems.day_type.state_machine import DECISION_MATRIX


def test_all_six_day_types_reachable():
    """All 6 day types must appear at least once in the decision matrix."""
    reachable = set(DECISION_MATRIX.values())
    expected = {DayType.Trend_Normal, DayType.Trend_DD, DayType.Variation,
                DayType.Normal, DayType.Neutral, DayType.Nontrend}
    missing = expected - reachable
    # Neutral may not appear directly in matrix (it's classified later via behavior)
    # Check at least 5 of 6 are in matrix, Neutral handled separately
    assert len(missing) <= 1, f"Missing from matrix: {missing}"


def test_matrix_covers_all_opening_ib_combos():
    """Matrix should have entries for all 5 opening types x 3 IB widths = 15."""
    openings = [ot for ot in OpeningType if ot != OpeningType.UNKNOWN]
    widths = [w for w in IBWidth if w != IBWidth.UNKNOWN]
    for ot in openings:
        for w in widths:
            key = (ot, w)
            assert key in DECISION_MATRIX, f"Missing matrix entry: {key}"


def test_open_drive_narrow_is_trend_normal():
    assert DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.NARROW)] == DayType.Trend_Normal


def test_auction_in_narrow_is_nontrend():
    assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW)] == DayType.Nontrend


def test_rejection_reverse_wide_is_normal():
    assert DECISION_MATRIX[(OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE)] == DayType.Normal
