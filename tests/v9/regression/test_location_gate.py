"""DAYTYPE_LOCATION_GATE v1 (Michael 07-15): REV fades on rotation days only at
the correct value edge. Anti-tautological: the exact #372 trade blocks, the
mirror-correct fade passes, CONT/Trend/missing-data untouched."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.location_gate import decide_location, zone_of  # noqa: E402

# reconstruction of 07-14: VA roughly 7565-7597, IB 12pt; #372 LONG @7597.25 (VAH ceiling)
LV = {"vah": 7597.0, "val": 7565.0, "ib_width": 12.0}


def _d(**kw):
    base = dict(family="REV", direction="LONG", day_type="Variation",
                entry_price=7597.25, levels=LV)
    base.update(kw)
    return decide_location(**base)


def test_372_class_blocked(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = _d()                                  # LONG at the VAH ceiling
    assert allow is False and "wrong location" in reason


def test_correct_fade_short_at_vah_passes(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(direction="SHORT")                      # selling the ceiling
    assert allow is True


def test_correct_fade_long_at_val_passes(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(entry_price=7565.5)                     # buying the floor
    assert allow is True


def test_mid_range_fade_blocked(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(entry_price=7581.0)                     # mid-value fade
    assert allow is False


def test_cont_untouched(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(family="CONT")
    assert allow is True


def test_trend_day_not_this_gate(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(day_type="Trend_Normal")
    assert allow is True


def test_missing_levels_fail_open(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = _d(levels={})
    assert allow is True and "fail-open" in reason


def test_flag_off_inert(monkeypatch):
    monkeypatch.delenv("DAYTYPE_LOCATION_GATE", raising=False)
    allow, _ = _d()
    assert allow is True


def test_zones():
    assert zone_of(7600.5, **{"vah": 7597.0, "val": 7565.0, "ib_width": 12.0}) == "above_value"
    assert zone_of(7596.0, vah=7597.0, val=7565.0, ib_width=12.0) == "near_vah"
    assert zone_of(7581.0, vah=7597.0, val=7565.0, ib_width=12.0) == "mid_value"
    assert zone_of(7566.0, vah=7597.0, val=7565.0, ib_width=12.0) == "near_val"
    assert zone_of(7560.0, vah=7597.0, val=7565.0, ib_width=12.0) == "below_value"


# ═══ 07-15 addendum (Michael: "לוודא שהמערכת תדע לזהות הרחבה") ═══

def test_cont_against_expansion_blocked(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="CONT", direction="LONG", day_type="Variation",
        entry_price=7590.0, levels=LV, expansion={"dir": "DOWN", "ref": "PDL"})
    assert allow is False and "against detected expansion" in reason


def test_cont_with_expansion_passes(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = decide_location(
        family="CONT", direction="SHORT", day_type="Variation",
        entry_price=7570.0, levels=LV, expansion={"dir": "DOWN", "ref": "PDL"})
    assert allow is True


def test_cont_no_expansion_signal_fail_open(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = decide_location(
        family="CONT", direction="LONG", day_type="Variation",
        entry_price=7590.0, levels=LV, expansion=None)
    assert allow is True


def test_cont_expansion_check_variation_only(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = decide_location(
        family="CONT", direction="LONG", day_type="Trend_Normal",
        entry_price=7590.0, levels=LV, expansion={"dir": "DOWN", "ref": "IB"})
    assert allow is True
