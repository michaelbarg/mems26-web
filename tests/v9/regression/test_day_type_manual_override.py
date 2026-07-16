"""DAY_TYPE_MANUAL_OVERRIDE — Michael's date-scoped manual classification.

Live ruling 2026-07-16 21:20 ("היום הפך ליום נייטרלי") + dev directive
(AGENT_SYNC 21:35): env "YYYY-MM-DD:Label" overrides get_live_day_type()
ONLY while today (ET) equals the date — auto-expires at the ET day roll.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import backend.v9.services.trade_context as tc


def _today_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def test_override_today_applies(monkeypatch):
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{_today_et()}:Neutral_Center")
    assert tc.get_live_day_type() == "Neutral_Center"


def test_override_other_date_inert(monkeypatch):
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", "2020-01-01:Neutral_Center")
    monkeypatch.delenv("DAYTYPE_GATE_LIVE_V1", raising=False)  # → None path
    assert tc.get_live_day_type() is None


def test_override_malformed_inert(monkeypatch):
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", "not-a-date-no-colon")
    monkeypatch.delenv("DAYTYPE_GATE_LIVE_V1", raising=False)
    assert tc.get_live_day_type() is None
