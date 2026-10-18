# -*- coding: utf-8 -*-
"""T-588 (18.10) — CLS_RESULT_SESSION_GUARD_V1: the gateway must not walk the tree on yesterday's classify_session
result. 06.10 16:30–17:05 live: ot=OPEN_AUCTION_IN / day_type Trend_Normal→Variation carried from 05.10 (the machine said
UNKNOWN, the replay FORMING) ⇒ OPENING_DRIVE LONG +95.60$ refused by tree:kind. Flag OFF ⇒ byte-identical."""
import pytest
from backend.v9.gateway.trading_gateway import _cls_session_guard

STALE = {"session_date": "2026-10-05", "opening_type": "OPEN_AUCTION_IN", "day_type": "Trend_Normal"}
FRESH = {"session_date": "2026-10-06", "opening_type": "UNKNOWN", "day_type": "FORMING"}
UNSTAMPED = {"opening_type": "OPEN_DRIVE"}


def test_flag_off_is_inert(monkeypatch):
    monkeypatch.delenv("CLS_RESULT_SESSION_GUARD_V1", raising=False)
    assert _cls_session_guard(STALE, "2026-10-06") is STALE
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", "0")
    assert _cls_session_guard(STALE, "2026-10-06") is STALE


@pytest.mark.parametrize("flag", ["1", "true", "YES"])
def test_stale_result_is_dropped(monkeypatch, flag):
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", flag)
    assert _cls_session_guard(STALE, "2026-10-06") is None


def test_todays_result_passes(monkeypatch):
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", "1")
    assert _cls_session_guard(FRESH, "2026-10-06") is FRESH


def test_unstamped_result_passes_fail_open(monkeypatch):
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", "1")
    assert _cls_session_guard(UNSTAMPED, "2026-10-06") is UNSTAMPED


def test_none_stays_none(monkeypatch):
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", "1")
    assert _cls_session_guard(None, "2026-10-06") is None


def test_datetime_stamp_prefix_compared(monkeypatch):
    monkeypatch.setenv("CLS_RESULT_SESSION_GUARD_V1", "1")
    assert _cls_session_guard({"session_date": "2026-10-06T13:35:00", "x": 1}, "2026-10-06") is not None
    assert _cls_session_guard({"session_date": "2026-10-05T20:55:00", "x": 1}, "2026-10-06") is None
