"""Michael 07-15 ("אין מחסם לתבניות במיקום הנכון"): the responsive-fade
exemption from direction-context covers Variation days, not only Neutral.
Anti-tautological: CONT on Variation stays filtered; REV on Trend stays filtered."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.daytype_position_gate import _pattern_family  # noqa: E402


def _exempt(day_type, pattern):  # mirror of the gateway expression
    return (str(day_type).startswith(("Neutral", "Variation", "Normal_Variation"))
            and _pattern_family(pattern) == "REV")


def test_rev_fade_exempt_on_variation():
    assert _exempt("Variation", "REACTIVE_SHORT") is True
    assert _exempt("Normal_Variation", "HFE") is True


def test_rev_exempt_on_neutral_still():
    assert _exempt("Neutral_Extreme", "REACTIVE_LONG") is True


def test_cont_still_filtered_on_variation():
    assert _exempt("Variation", "ZLR") is False        # CONT family stays gated


def test_rev_not_exempt_on_trend():
    assert _exempt("Trend_Normal", "REACTIVE_SHORT") is False
