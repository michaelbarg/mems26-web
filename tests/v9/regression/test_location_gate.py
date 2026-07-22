"""DAYTYPE_LOCATION_GATE v2 (Michael 07-15 + 07-22): REV fades on rotation days
only at the correct value edge AND after a mechanical probe (bar that pierced
the edge and closed back). Anti-tautological fixtures from live trades."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.location_gate import decide_location, zone_of, probe_detected  # noqa: E402

# reconstruction of 07-14: VA roughly 7565-7597, IB 12pt; #372 LONG @7597.25 (VAH ceiling)
LV = {"vah": 7597.0, "val": 7565.0, "ib_width": 12.0}

# A bar that probed VAH and closed back (valid probe for SHORT)
PROBE_VAH_BAR = {"high": 7599.0, "low": 7593.0, "close": 7595.0}  # H>=VAH, C<VAH
# A bar that probed VAL and closed back (valid probe for LONG)
PROBE_VAL_BAR = {"high": 7568.0, "low": 7563.0, "close": 7566.0}  # L<=VAL, C>VAL
# Bars without probe
NO_PROBE_BARS = [
    {"high": 7590.0, "low": 7582.0, "close": 7585.0},
    {"high": 7588.0, "low": 7580.0, "close": 7583.0},
]


def _d(**kw):
    base = dict(family="REV", direction="LONG", day_type="Variation",
                entry_price=7597.25, levels=LV, recent_bars=[PROBE_VAL_BAR])
    base.update(kw)
    return decide_location(**base)


# ═══ v1 tests (location) ═══

def test_372_class_blocked(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = _d()                                  # LONG at the VAH ceiling
    assert allow is False and "wrong location" in reason


def test_correct_fade_short_at_vah_passes(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(direction="SHORT", recent_bars=[PROBE_VAH_BAR])  # selling the ceiling after probe
    assert allow is True


def test_correct_fade_long_at_val_passes(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, _ = _d(entry_price=7565.5, recent_bars=[PROBE_VAL_BAR])  # buying the floor after probe
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


# ═══ v2 probe tests (07-22) ═══

def test_probe_detected_short_at_vah():
    found, desc = probe_detected("SHORT", 7597.0, 7565.0, [PROBE_VAH_BAR])
    assert found is True and "probed VAH" in desc


def test_probe_detected_long_at_val():
    found, desc = probe_detected("LONG", 7597.0, 7565.0, [PROBE_VAL_BAR])
    assert found is True and "probed VAL" in desc


def test_probe_not_detected_no_pierce():
    found, _ = probe_detected("SHORT", 7597.0, 7565.0, NO_PROBE_BARS)
    assert found is False


def test_probe_not_detected_no_bars():
    found, _ = probe_detected("SHORT", 7597.0, 7565.0, None)
    assert found is False


def test_correct_edge_no_probe_blocked(monkeypatch):
    """SHORT at VAH (correct edge) but no prior probe → BLOCK (v2)."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7597.25, levels=LV, recent_bars=NO_PROBE_BARS)
    assert allow is False and "no probe" in reason


def test_correct_edge_with_probe_passes(monkeypatch):
    """SHORT at VAH (correct edge) WITH prior probe → ALLOW (v2)."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7597.25, levels=LV, recent_bars=[PROBE_VAH_BAR])
    assert allow is True and "probe" in reason


# ═══ Live fixtures from 2026-07-21 (פסיקת-מייקל 22:18) ═══
# VA: VAH=7553.25, VAL=~7540, POC=7547.25

LV_0721 = {"vah": 7553.25, "val": 7540.0, "ib_width": 13.25}

# 19:55 IL bar: H=7554.25 > VAH, C=7550.25 < VAH = valid probe
BAR_1955_PROBE = {"high": 7554.25, "low": 7548.0, "close": 7550.25}

# Earlier bars (no probe — mid-range movement)
BARS_NO_PROBE_0721 = [
    {"high": 7549.0, "low": 7545.0, "close": 7547.0},
    {"high": 7550.0, "low": 7546.0, "close": 7548.0},
]


def test_fixture_449_zlr_short_poc_block(monkeypatch):
    """#449: ZLR SHORT @7548.75 on POC = mid-value → BLOCK."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7548.75, levels=LV_0721, recent_bars=BARS_NO_PROBE_0721)
    assert allow is False and "wrong location" in reason


def test_fixture_452_zlr_short_poc_block(monkeypatch):
    """#452: ZLR SHORT @7546 on POC = mid-value → BLOCK."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7546.0, levels=LV_0721, recent_bars=BARS_NO_PROBE_0721)
    assert allow is False and "wrong location" in reason


def test_fixture_456_zlr_short_poc_block(monkeypatch):
    """#456: ZLR SHORT @7545.50 on POC = mid-value → BLOCK."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7545.50, levels=LV_0721, recent_bars=BARS_NO_PROBE_0721)
    assert allow is False and "wrong location" in reason


def test_fixture_1955_vah_test_allow(monkeypatch):
    """19:55 VAH probe → SHORT@VAH after rejection = ALLOW."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7553.25, levels=LV_0721,
        recent_bars=BARS_NO_PROBE_0721 + [BAR_1955_PROBE])
    assert allow is True and "probe" in reason


def test_fixture_s4_mid_poc_variation_up_block(monkeypatch):
    """S4 mid-POC SHORT on Variation-UP = BLOCK (mid-value)."""
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type="Variation",
        entry_price=7547.25, levels=LV_0721, recent_bars=BARS_NO_PROBE_0721)
    assert allow is False and "wrong location" in reason
