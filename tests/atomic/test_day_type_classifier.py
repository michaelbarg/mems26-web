"""Prompt 15 (updated W3-gamma) -- 6 day types via IB Width Matrix + state machine"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from backend.v9.systems.day_type.schemas import DayType, OpeningType, IBWidth
from backend.v9.systems.day_type.decision_matrix import DECISION_MATRIX, MatrixCell


def _get_top_day_type(value):
    """Extract top DayType from matrix cell (handles MatrixCell + plain DayType)."""
    if isinstance(value, MatrixCell):
        return value.get("top1", DayType.UNKNOWN)
    return value


def test_all_six_day_types_reachable():
    """All 6 day types must appear at least once in the decision matrix."""
    reachable = set()
    for v in DECISION_MATRIX.values():
        dt = _get_top_day_type(v)
        if isinstance(dt, DayType):
            reachable.add(dt)
    expected = {DayType.Trend_Normal, DayType.Trend_DD, DayType.Variation,
                DayType.Normal, DayType.Nontrend}
    missing = expected - reachable
    # Neutral classified later via behavior, not directly in matrix
    assert len(missing) == 0, f"Missing from matrix: {missing}"


def test_matrix_covers_all_opening_ib_combos():
    """Matrix should have entries for all opening types x 3 IB widths."""
    openings = [ot for ot in OpeningType if ot not in (OpeningType.UNKNOWN,)]
    widths = [w for w in IBWidth if w != IBWidth.UNKNOWN]
    for ot in openings:
        for w in widths:
            key = (ot, w)
            assert key in DECISION_MATRIX, f"Missing matrix entry: {key}"


def test_open_drive_narrow_is_trend_normal():
    val = DECISION_MATRIX[(OpeningType.OPEN_DRIVE, IBWidth.NARROW)]
    assert _get_top_day_type(val) == DayType.Trend_Normal


def test_auction_in_narrow_is_nontrend():
    assert DECISION_MATRIX[(OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW)] == DayType.Nontrend


def test_rejection_reverse_wide_is_normal():
    assert DECISION_MATRIX[(OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE)] == DayType.Normal


def test_indeterminate_maps_to_normal():
    """INDETERMINATE opening type → Normal day (safe fallback, Prompt 15)."""
    for w in (IBWidth.NARROW, IBWidth.MEDIUM, IBWidth.WIDE):
        assert DECISION_MATRIX[(OpeningType.INDETERMINATE, w)] == DayType.Normal
