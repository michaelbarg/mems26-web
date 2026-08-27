"""Binary-gates mutation tests — sites 1, 4, 5, 8 (HOWTO §3 contract).

Ruling: Michael 25.08 "להמשיך עם דלתון בינארי" + 26.08 "למה יש לשער הפתיחה
אחוזים… מי קובע את רמת הביטחון — בלתי אפשרי למדוד באופן לא שקוף".

Contract per site (HOWTO_BINARY_GATES §3):
  (א) live input  -> the decision flips when the FACT flips;
  (ב) dead input  -> explicit UNDETERMINED, never translated to 0.0/False,
                     and it does NOT veto;
  (ג) site-1 day reconstruction: an engine trigger + with-direction confirm
      bar passes; the same state with a POSITIVE opposite classification is
      vetoed.
"""
from __future__ import annotations

import logging

import pytest

from backend.v9.systems.opening_entry import opening_first_trade_ok
from backend.v9.systems.opening_type_gate import _early_bias
from backend.v9.systems.day_type.daytype_classifier import delta_ext_verdict


def _bars(n=3, direction="LONG"):
    """n closed bars, last one confirming `direction`."""
    if direction == "LONG":
        last = {"o": 7530.0, "c": 7534.0}
    else:
        last = {"o": 7534.0, "c": 7530.0}
    return [{"o": 7529.0, "c": 7530.0}] * (n - 1) + [last]


# ══════════════════════════ site 1 · opening_first_trade_ok ══════════════════

def test_site1_undetermined_classifier_does_not_veto(monkeypatch):
    """(ב) UNKNOWN / None / AUCTION-no-direction => UNDETERMINED => pass."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "0")
    for ot in (None, "", "UNKNOWN", "AUCTION"):
        ok, reason = opening_first_trade_ok(
            _bars(), "LONG", opening_conf=None, opening_type=ot)
        assert ok is True, (ot, reason)


def test_site1_positive_opposite_classification_vetoes(monkeypatch):
    """(א)+(ג) the classifier AFFIRMATIVELY names the opposite direction."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "0")
    ok, reason = opening_first_trade_ok(
        _bars(), "LONG", opening_conf=None, opening_type="OPEN_DRIVE_DOWN")
    assert ok is False and "positive opposing" in reason
    ok, reason = opening_first_trade_ok(
        _bars(direction="SHORT"), "SHORT", opening_conf=None,
        opening_type="OPEN_DRIVE_UP")
    assert ok is False and "positive opposing" in reason


def test_site1_with_direction_classification_passes(monkeypatch):
    """(א) same fact, right way round -> the decision flips to PASS."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "0")
    ok, _ = opening_first_trade_ok(
        _bars(), "LONG", opening_conf=None, opening_type="OPEN_DRIVE_UP")
    assert ok is True


def test_site1_conf_zero_day_reconstruction(monkeypatch):
    """(ג) the 27.08 kill class: DRIVE trigger, conf=0.0 (auction detector),
    confirm bar with-direction — the old gate blocked 7/7; binary passes."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "0")
    ok, reason = opening_first_trade_ok(
        _bars(), "LONG", opening_conf=0.0, trigger_type="DRIVE",
        opening_type="UNKNOWN")
    assert ok is True, reason


def test_site1_confirmation_is_still_physical(monkeypatch):
    """The physical condition survives the conf-gate removal: a last bar
    AGAINST the direction still fails, classifier or no classifier."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "0")
    bars = _bars(direction="SHORT")            # last bar closes down
    ok, reason = opening_first_trade_ok(
        bars, "LONG", opening_conf=None, opening_type="OPEN_DRIVE_UP")
    assert ok is False and "did not confirm" in reason


def test_site1_legacy_rollback_restores_conf_gate(monkeypatch):
    """LEGACY_CONF_GATES=1 => the old percentage path, wholesale."""
    monkeypatch.setenv("LEGACY_CONF_GATES", "1")
    monkeypatch.setenv("OPENING_MIN_CONF", "")   # code default 0.7
    ok, reason = opening_first_trade_ok(
        _bars(), "LONG", opening_conf=0.0, opening_type="OPEN_DRIVE_UP")
    assert ok is False and "no certainty" in reason
    ok, _ = opening_first_trade_ok(
        _bars(), "LONG", opening_conf=0.85, opening_type="OPEN_DRIVE_UP")
    assert ok is True


def test_site8_min_conf_read_only_inside_legacy_branch():
    """Site-8 source contract: OPENING_MIN_CONF is read exactly once, and
    only after the LEGACY_CONF_GATES check — the binary path is
    threshold-free."""
    import inspect
    from backend.v9.systems import opening_entry as oe
    src = inspect.getsource(oe.opening_first_trade_ok)
    assert src.count('getenv("OPENING_MIN_CONF"') == 1
    legacy_at = src.index("LEGACY_CONF_GATES")
    minconf_at = src.index('getenv("OPENING_MIN_CONF"')
    assert minconf_at > legacy_at, (
        "OPENING_MIN_CONF is read before the legacy gate — the binary path "
        "grew a confidence threshold back")


# ══════════════════════ site 4 · upper/lower third rule ══════════════════════

def _bias_bars(close_pos):
    """Bar-1 spikes down (bias DOWN by sign) but closes at `close_pos` of its
    own range. h=7800, l=7780, opening_print=7795."""
    close = 7780.0 + close_pos * 20.0
    return [{"o": 7795.0, "h": 7800.0, "l": 7780.0, "c": close,
             "close": close, "high": 7800.0, "low": 7780.0}]


def test_site4_flag_off_is_byte_identical(monkeypatch):
    """OFF: the geometric refresh never runs — sign(close-open_print) only."""
    monkeypatch.setenv("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "0")
    state, direction = _early_bias(_bias_bars(0.9), 7795.0)
    # close 7798 > print 7795 => diff +3 => UP (no flip logic involved)
    assert (state, direction) == ("EARLY_BIAS", "UP")
    state, direction = _early_bias(_bias_bars(0.1), 7795.0)
    # close 7782 < print => DOWN, and NOT flipped by the (disabled) rule
    assert (state, direction) == ("EARLY_BIAS", "DOWN")


def test_site4_upper_third_rule_flips_down_to_up(monkeypatch):
    """(א) geometry flips the fact: spike down, close in top third => UP."""
    monkeypatch.setenv("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "1")
    bars = _bias_bars(0.9)
    bars[0]["c"] = bars[0]["close"] = 7794.0   # below print => raw DOWN
    # pos = (7794-7780)/20 = 0.70 >= 0.66 => upper_third_rule flips to UP
    state, direction = _early_bias(bars, 7795.0)
    assert (state, direction) == ("EARLY_BIAS", "UP")


def test_site4_middle_of_range_does_not_flip(monkeypatch):
    monkeypatch.setenv("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "1")
    bars = _bias_bars(0.5)                     # close 7790 < print => DOWN
    state, direction = _early_bias(bars, 7795.0)
    assert (state, direction) == ("EARLY_BIAS", "DOWN")


def test_site4_is_named_in_the_log(monkeypatch, caplog):
    """The HOWTO asked for a NAME — the flip must be auditable as
    upper_third_rule from the log alone."""
    monkeypatch.setenv("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "1")
    bars = _bias_bars(0.9)
    bars[0]["c"] = bars[0]["close"] = 7794.0
    with caplog.at_level(logging.INFO,
                         logger="backend.v9.systems.opening_type_gate"):
        _early_bias(bars, 7795.0)
    assert any("upper_third_rule" in r.getMessage() for r in caplog.records)


# ═══════════════════ site 5 · delta_confirms_ext (3-valued) ══════════════════

def test_site5_true_passes():
    assert delta_ext_verdict(True, enabled=True) == "PASS"


def test_site5_false_with_flag_vetoes():
    """(א) the fact flips the decision."""
    assert delta_ext_verdict(False, enabled=True) == "VETO"


def test_site5_none_is_undetermined_not_veto():
    """(ב) starved input is UNDETERMINED — not False, not 0.0, not a veto."""
    assert delta_ext_verdict(None, enabled=True) == "UNDETERMINED"
    assert delta_ext_verdict(None, enabled=False) == "UNDETERMINED"


def test_site5_flag_off_never_vetoes():
    assert delta_ext_verdict(False, enabled=False) == "PASS"


def test_site5_wiring_logs_undetermined():
    """(ב) the classifier records UNDETERMINED(delta_confirms_ext) — the
    starved case is visible, not swallowed. Source-contract: the wiring calls
    the pure function and logs the exact token."""
    import inspect
    from backend.v9.systems.day_type import daytype_classifier as dc
    src = inspect.getsource(dc)
    assert "UNDETERMINED(delta_confirms_ext)" in src
    assert "delta_ext_verdict(" in src
    # the old inline translation must be gone
    assert src.count("_delta_ext is False") == 0
