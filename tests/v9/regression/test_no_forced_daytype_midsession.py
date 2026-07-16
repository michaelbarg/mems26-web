"""07-16 (Michael: "תבדוק צינורות מה חסם למה — תתקן").

Root of today's 10 location_gate blocks: with live day_type=None, extract_g1's
fallback fed classify_replay's END-OF-DAY `final` (a FORCED terminal label on a
partial day, e.g. "Neutral_Center") into day_type_at_entry → gates acted on a
label S1 never published (Source-of-Truth Rule 1 violation).

Pins: MID-SESSION live-None ⇒ day_type_at_entry is None (honest missing) ⇒
location_gate fail-opens. POST-CLOSE the fallback is allowed (final is valid).
"""
import datetime as dt
from zoneinfo import ZoneInfo

import backend.v9.services.trade_context as tc
from backend.v9.systems.location_gate import decide_location

ET = ZoneInfo("America/New_York")


class _FakeDT(dt.datetime):
    _fixed = None

    @classmethod
    def now(cls, tz=None):
        return cls._fixed.astimezone(tz) if tz else cls._fixed


def _run_extract(monkeypatch, hour_et: int):
    monkeypatch.setenv("S1_NEW_CLASSIFIER", "1")
    monkeypatch.setattr(tc, "get_live_day_type", lambda: None)  # live is silent
    # replay-final would force a terminal label
    tc._NC_CACHE.update({"date": dt.datetime.now(ET).date().isoformat(),
                         "ts": 9e12, "day_type": "Neutral_Center"})
    _FakeDT._fixed = dt.datetime(2026, 7, 16, hour_et, 30, tzinfo=ET)
    monkeypatch.setattr(tc, "extract_g1_entry_context", tc.extract_g1_entry_context)
    import datetime as real_dt
    monkeypatch.setattr(real_dt, "datetime", _FakeDT)
    return tc.extract_g1_entry_context({"day_type_machine": {}, "woodies_system": {},
                                        "killzone_system": {}})


def test_midsession_live_none_stays_none(monkeypatch):
    g1 = _run_extract(monkeypatch, hour_et=13)  # 13:30 ET = mid-RTH (20:30 IL)
    assert g1["day_type_at_entry"] is None, (
        f"mid-session forced label leaked: {g1['day_type_at_entry']}")


def test_postclose_fallback_allowed(monkeypatch):
    g1 = _run_extract(monkeypatch, hour_et=17)  # 17:30 ET = post-close
    assert g1["day_type_at_entry"] == "Neutral_Center"


def test_location_gate_fail_opens_on_none(monkeypatch):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    allow, reason = decide_location(
        family="REV", direction="SHORT", day_type=None,
        entry_price=7600.0, levels={"vah": 7612.0, "val": 7580.0, "ib_width": 12.0})
    assert allow, f"gate must fail-open on unknown day, got block: {reason}"
