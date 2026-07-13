"""P2-9/10/11/12 context reads + IDEA-1 news blackout + IDEA-2 phone alerts
(Michael 2026-07-13). All flag-OFF-safe; anti-tautological where a gate exists.
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.day_type.day_context_extras import (  # noqa: E402
    profile_imbalance, range_estimate, va_rule_read, eod_continuation_tag)


def _bar(px, v=100.0, spread=1.0):
    return {"o": px, "h": px + spread, "l": px - spread, "c": px, "v": v}


# ── P2-9 profile imbalance ──────────────────────────────────────────────────

def test_imbalance_sign_follows_volume_side():
    bars = [_bar(5000, v=200)] * 4 + [_bar(5010, v=800)] * 2 + [_bar(5020, v=900)] * 6
    imb = profile_imbalance(bars)          # POC at 5020-heavy zone → volume below POC
    assert imb is not None and imb < 0
    bars2 = [_bar(5020, v=900)] * 6 + [_bar(5010, v=800)] * 2 + [_bar(5000, v=200)] * 4
    # same profile, order irrelevant → same sign
    assert profile_imbalance(bars2) == imb


def test_imbalance_none_on_empty():
    assert profile_imbalance([]) is None


# ── P2-10 range estimate ────────────────────────────────────────────────────

def test_range_estimate_projects_from_held_low():
    # low made in period 1, held through periods 2-3 while highs rise
    bars = ([_bar(5000)] * 3 + [_bar(4995)] * 3          # period 1: low 4994
            + [_bar(5005)] * 6                            # period 2 higher
            + [_bar(5012)] * 6)                           # period 3 higher
    r = range_estimate(bars, med_daily_range=30.0)
    assert r["held_side"] == "LOW"
    assert abs(r["est_target"] - (4994.0 + 30.0)) < 0.01
    assert r["est_lo"] < r["est_target"] < r["est_hi"]


def test_range_estimate_honest_none_without_median():
    bars = [_bar(5000)] * 18
    assert range_estimate(bars, None)["held_side"] is None


def test_range_estimate_no_hold_no_estimate():
    # both extremes keep moving — nothing held
    bars = ([_bar(5000)] * 6 + [_bar(4990)] * 6 + [_bar(5015)] * 6 + [_bar(4980)] * 6)
    assert range_estimate(bars, 30.0)["held_side"] is None


# ── P2-11 VA rule ───────────────────────────────────────────────────────────

def test_va_rule_open_above_accepted_inside_targets_val():
    vah, val = 5010.0, 4990.0
    bars = [_bar(5018)] * 2 + [_bar(5005), _bar(5002)] + [_bar(5000)] * 2
    r = va_rule_read(bars, vah, val, open_price=5018.0)
    assert r["active"] and r["target_side"] == "VAL" and r["target"] == val


def test_va_rule_inactive_when_open_inside_value():
    r = va_rule_read([_bar(5000)] * 6, 5010.0, 4990.0, open_price=5000.0)
    assert not r["active"]


def test_va_rule_inactive_without_acceptance():
    # opened above, never 2 consecutive closes inside
    bars = [_bar(5018)] * 3 + [_bar(5005)] + [_bar(5016)] * 3
    r = va_rule_read(bars, 5010.0, 4990.0, open_price=5018.0)
    assert not r["active"]


# ── P2-12 EOD tag ───────────────────────────────────────────────────────────

def test_eod_tags():
    assert eod_continuation_tag("Neutral_Extreme", 0.9) == "NE_CLOSE_UP"
    assert eod_continuation_tag("Trend_Normal", 0.1) == "TREND_CARRY_DOWN"
    assert eod_continuation_tag("Normal", 0.5) == "BALANCE_NO_CARRY"
    assert eod_continuation_tag("Normal_Variation", 0.8) == "VARIATION_LEAN_UP"
    assert eod_continuation_tag(None, 0.5) is None
    assert eod_continuation_tag("Normal", None) is None


# ── IDEA-1 news blackout ────────────────────────────────────────────────────

def test_news_blackout_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("NEWS_BLACKOUT_V1", raising=False)
    from backend.v9.services.news_blackout import enabled
    assert enabled() is False


def test_news_blackout_window_edges():
    """Michael FINAL 07-13 ruling: רק אדום חוסם — 10 לפני / 5 אחרי."""
    from backend.v9.services.news_blackout import check, window_for
    ET = ZoneInfo("America/New_York")
    assert window_for("red") == (10, 5)
    assert window_for("orange") == (0, 0)                                 # תצוגה-בלבד
    assert window_for("yellow") == (0, 0)                                 # תצוגה-בלבד
    # אנטי-טאוטולוגי: 08:19 בתוך חלון-ADP-הכתום (08:15) — חייב להיות פתוח,
    # כי רק אדום חוסם; חלון-ה-CPI-האדום נפתח רק ב-08:20.
    assert check(datetime(2026, 7, 14, 8, 19, tzinfo=ET)) is None
    r = check(datetime(2026, 7, 14, 8, 21, tzinfo=ET))                    # 9 דק' לפני CPI
    assert r and r["severity"] == "red", r
    assert check(datetime(2026, 7, 14, 8, 34, tzinfo=ET)) is not None    # 4 דק' אחרי → חסום
    assert check(datetime(2026, 7, 14, 8, 36, tzinfo=ET)) is None        # 6 דק' אחרי → פתוח
    assert check(datetime(2026, 7, 14, 11, 30, tzinfo=ET)) is None       # שעה נקייה → פתוח


# ── IDEA-2 phone alerts ─────────────────────────────────────────────────────

def test_phone_push_noop_when_flag_off(monkeypatch):
    monkeypatch.delenv("PHONE_ALERTS_V1", raising=False)
    import backend.v9.services.phone_alert as pa
    called = []
    monkeypatch.setattr(pa, "_send_pushover", lambda *a: called.append(1) or True)
    pa.push("k1", "t", "m")
    time.sleep(0.05)
    assert called == []          # flag off → nothing sent


def test_phone_push_rate_limited(monkeypatch):
    monkeypatch.setenv("PHONE_ALERTS_V1", "1")
    monkeypatch.setenv("PHONE_ALERT_PROVIDER", "pushover")
    import backend.v9.services.phone_alert as pa
    calls = []
    monkeypatch.setattr(pa, "_send_pushover", lambda *a: calls.append(a) or True)
    pa._last_sent.clear()
    pa.push("same_key", "t", "m1")
    pa.push("same_key", "t", "m2")     # inside 5-min window → suppressed
    pa.push("other_key", "t", "m3")
    time.sleep(0.2)                     # background threads
    assert len(calls) == 2, calls       # m1 + m3 only


def test_phone_push_never_raises_on_send_error(monkeypatch):
    monkeypatch.setenv("PHONE_ALERTS_V1", "1")
    import backend.v9.services.phone_alert as pa
    def boom(*a):
        raise RuntimeError("network down")
    monkeypatch.setattr(pa, "_send_pushover", boom)
    pa._last_sent.clear()
    pa.push("k_err", "t", "m")          # must not raise
    time.sleep(0.1)
