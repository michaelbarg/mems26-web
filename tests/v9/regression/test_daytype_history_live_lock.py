# -*- coding: utf-8 -*-
"""DAYTYPE_HISTORY_LIVE_LOCK_V1 (19.10, Michael: "fix all the gaps"): the end-of-day history row records what the
system actually traded on.

Finding: `v9_day_type_history` is written on every bar by `DayTypeConsumer.consume` from the state machine's own A2
reading, so `opening_type` differs from the live T-314 lock (the one the gateway / tree / playbook act on) on 6 of 17
days and `locked_at` is NULL in 113 of 113 rows.

Fix (default OFF => the event is returned as the very same object, the writer is untouched): with the flag ON and the lock
held for the row's own ET date the event carries `opening_type` = the live locked type (after the last negation
re-read), `locked_at` = the lock time (UTC) and one token `live_lock=<type>/<dir>@<HH:MM> IL` appended to
`reasoning_notes`.  `day_type` (the EOD rewrite) is untouched.  No lock -> unchanged.
"""
import copy
import logging
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.models.day_type_history import V9DayTypeHistory
from backend.v9.db.session import Base
from backend.v9.systems.day_type import history_live_lock as hll
from backend.v9.systems.day_type.consumer import DayTypeConsumer
from backend.v9.systems.day_type.opening_lock import update_opening_lock
from backend.v9.systems.day_type.schemas import DayType
from tests.v9.regression._daytype_handler_harness import ROOT, Harness, et

FLAG = "DAYTYPE_HISTORY_LIVE_LOCK_V1"
MAIN = os.path.join(ROOT, "backend", "main.py")
TS = "2026-10-19T14:20:00+00:00"          # 10:20 ET, Monday 19.10.2026
LOCK_AT = "2026-10-19T09:45:04.123456-04:00"


@pytest.fixture
def factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _event(day_type="Trend_Normal", opening="OPEN_DRIVE", ts=TS, notes="Converted from DayTypeState stage=B2"):
    return {
        "timestamp": ts, "day_type": day_type, "probability": 0.7, "directional_certainty": "HIGH",
        "trading_confidence": "LOW", "ib_h": 5260.0, "ib_l": 5240.0, "ib_width": 20.0, "ib_width_class": "MEDIUM",
        "opening_type": opening, "last_updated_at": ts, "reasoning_notes": notes, "active_zohar_rules": [],
        "lock_state": "LOCKED",
    }


def _machine(val="OPEN_REJECTION_REVERSE", direction="DOWN", at=LOCK_AT, locked=True):
    """What `update_opening_lock` leaves on the day_type_machine (test_t314_opening_lock builds the same shape)."""
    return SimpleNamespace(_opening_type_locked=locked, _opening_locked_val=val, _opening_locked_dir=direction,
                           _opening_locked_at=at, _opening_negated=False, _opening_negated_at=None)


def _as_utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _only_row(factory):
    s = factory()
    try:
        return s.query(V9DayTypeHistory).one()
    finally:
        s.close()


# ── the flag ────────────────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("val,expected", [(None, False), ("", False), ("0", False), ("off", False),
                                          ("1", True), ("true", True), ("YES", True)])
def test_flag_is_read_at_call_time_and_defaults_off(monkeypatch, val, expected):
    if val is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, val)
    assert hll.FLAG == FLAG and hll.enabled() is expected


# ── flag OFF: the writer is untouched ───────────────────────────────────────────────────────────────────────────────


def test_flag_off_returns_the_very_same_event_even_when_a_lock_is_held(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    ev = _event()
    snapshot = copy.deepcopy(ev)
    assert hll.apply_live_lock(ev, _machine()) is ev
    assert ev == snapshot and "locked_at" not in ev


def test_flag_off_writer_output_is_unchanged(monkeypatch, factory):
    monkeypatch.setenv(FLAG, "0")
    DayTypeConsumer(factory).consume(hll.apply_live_lock(_event(), _machine()))
    row = _only_row(factory)
    assert row.opening_type == "OPEN_DRIVE"                      # the machine's own reading, as before
    assert row.locked_at is None                                 # NULL, as before
    assert row.reasoning_notes == "Converted from DayTypeState stage=B2"
    assert row.day_type == "Trend_Normal"


# ── flag ON ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_flag_on_locked_opening_row_carries_the_type_locked_at_and_token(monkeypatch, factory):
    monkeypatch.setenv(FLAG, "1")
    ev = _event()
    snapshot = copy.deepcopy(ev)
    out = hll.apply_live_lock(ev, _machine())
    assert ev == snapshot                                        # the input event is not mutated
    DayTypeConsumer(factory).consume(out)
    row = _only_row(factory)
    assert row.opening_type == "OPEN_REJECTION_REVERSE"          # the live lock, not the machine's OPEN_DRIVE
    assert _as_utc(row.locked_at) == datetime(2026, 10, 19, 13, 45, 4, 123456, tzinfo=timezone.utc)
    assert row.reasoning_notes == "Converted from DayTypeState stage=B2 live_lock=OPEN_REJECTION_REVERSE/DOWN@16:45 IL"
    assert row.day_type == "Trend_Normal"                        # the EOD rewrite keeps writing day_type as today
    assert row.probability == 0.7 and row.ib_high == 5260.0 and row.ib_width_class == "MEDIUM"


def test_flag_on_writes_the_value_after_the_last_negation_reread(monkeypatch):
    """T-314: a negated ORR/DRIVE is re-read once with the closed bars -> `_opening_locked_val` is the re-read value."""
    monkeypatch.setenv(FLAG, "1")
    bars = [{"o": 7599.00, "h": 7603.00, "l": 7595.00, "c": 7596.75}, {"o": 7597.00, "h": 7604.50, "l": 7593.75, "c": 7603.25},
            {"o": 7603.50, "h": 7606.50, "l": 7599.50, "c": 7600.25}, {"o": 7600.25, "h": 7609.25, "l": 7600.00, "c": 7605.50},
            {"o": 7605.75, "h": 7605.75, "l": 7591.50, "c": 7592.25}]
    m = _machine(val=None, direction=None, at=None, locked=False)
    reads = [{"opening_type": "OPEN_REJECTION_REVERSE", "direction": "UP"}, {"opening_type": "OPEN_AUCTION_IN", "direction": "NEUTRAL"}]
    with mock.patch("backend.v9.systems.day_type.opening_detector_v2.detect_opening_type", side_effect=reads):
        update_opening_lock(m, [dict(b, v=1000) for b in bars[:4]], False, "2026-10-19T09:45:04-04:00")
        assert (m._opening_locked_val, m._opening_negated) == ("OPEN_REJECTION_REVERSE", False)
        out_before = hll.apply_live_lock(_event(), m)
        update_opening_lock(m, [dict(b, v=1000) for b in bars], False, "2026-10-19T09:50:04-04:00")
    assert (m._opening_locked_val, m._opening_negated) == ("OPEN_AUCTION_IN", True)
    out_after = hll.apply_live_lock(_event(), m)
    assert out_before["opening_type"] == "OPEN_REJECTION_REVERSE" and out_after["opening_type"] == "OPEN_AUCTION_IN"
    assert out_after["reasoning_notes"].endswith("live_lock=OPEN_AUCTION_IN/NEUTRAL@16:45 IL")
    assert out_after["locked_at"] == datetime(2026, 10, 19, 13, 45, 4, tzinfo=timezone.utc)   # the lock time stays


def test_flag_on_no_lock_leaves_the_event_exactly_as_it_was(monkeypatch, factory):
    monkeypatch.setenv(FLAG, "1")
    for machine in (_machine(locked=False), _machine(val=None, at=None, locked=False), SimpleNamespace(), None):
        ev = _event()
        assert hll.apply_live_lock(ev, machine) is ev
        assert "locked_at" not in ev and ev["opening_type"] == "OPEN_DRIVE"
    DayTypeConsumer(factory).consume(hll.apply_live_lock(_event(), _machine(locked=False)))
    row = _only_row(factory)
    assert (row.opening_type, row.locked_at, row.reasoning_notes) == ("OPEN_DRIVE", None, "Converted from DayTypeState stage=B2")


def test_flag_on_row_follows_the_session_before_during_and_after_the_lock(monkeypatch, factory):
    monkeypatch.setenv(FLAG, "1")
    consumer = DayTypeConsumer(factory)
    consumer.consume(hll.apply_live_lock(_event(), _machine(locked=False)))              # before the lock: as today
    row = _only_row(factory)
    assert (row.opening_type, row.locked_at) == ("OPEN_DRIVE", None)
    consumer.consume(hll.apply_live_lock(_event(day_type="Normal"), _machine()))          # lock held: UPDATE the same row
    row = _only_row(factory)
    assert (row.opening_type, row.day_type) == ("OPEN_REJECTION_REVERSE", "Normal")
    assert _as_utc(row.locked_at) == datetime(2026, 10, 19, 13, 45, 4, 123456, tzinfo=timezone.utc)
    consumer.consume(hll.apply_live_lock(_event(day_type="Variation", ts="2026-10-19T19:55:00+00:00"), _machine()))   # EOD
    row = _only_row(factory)
    assert (row.opening_type, row.day_type) == ("OPEN_REJECTION_REVERSE", "Variation")    # day_type = the rewrite, as today
    assert row.reasoning_notes.count("live_lock=") == 1
    assert _as_utc(row.locked_at) == datetime(2026, 10, 19, 13, 45, 4, 123456, tzinfo=timezone.utc)


def test_flag_on_a_lock_stamped_on_another_et_date_is_not_todays_lock(monkeypatch):
    """The lock attributes live on the machine and `machine.reset()` does not clear them."""
    monkeypatch.setenv(FLAG, "1")
    ev = _event()
    assert hll.apply_live_lock(ev, _machine(at="2026-10-16T09:45:04-04:00")) is ev           # Friday's lock
    assert hll.apply_live_lock(ev, _machine(at=None)) is ev                                   # cannot prove it is today's
    assert hll.apply_live_lock(ev, _machine(val="  ")) is ev                                  # no type, no lock


def test_flag_on_the_row_date_is_the_et_date_of_the_event_timestamp(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    late = _event(ts="2026-10-20T01:30:00+00:00")      # 21:30 ET on 19.10 -- still the 19.10 row
    assert hll.apply_live_lock(late, _machine())["opening_type"] == "OPEN_REJECTION_REVERSE"
    next_day = _event(ts="2026-10-20T14:20:00+00:00")  # the 20.10 row: the 19.10 lock is not its lock
    assert hll.apply_live_lock(next_day, _machine()) is next_day


def test_token_shape_dir_none_dst_idempotence_and_length(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    out = hll.apply_live_lock(_event(), _machine(direction=None))
    assert out["reasoning_notes"].endswith(" live_lock=OPEN_REJECTION_REVERSE/NONE@16:45 IL")
    # 27.10.2026: Israel is back on winter time (+2) while New York is still on summer time (-4) -> 09:45 ET = 15:45 IL
    out = hll.apply_live_lock(_event(ts="2026-10-27T14:20:00+00:00"), _machine(at="2026-10-27T09:45:00-04:00"))
    assert out["reasoning_notes"].endswith("@15:45 IL")
    # applying it again never doubles the token
    assert hll.apply_live_lock(out, _machine(at="2026-10-27T09:45:00-04:00"))["reasoning_notes"].count("live_lock=") == 1
    # the column is VARCHAR(1024): the machine's text is trimmed, the token stays whole
    long_ev = _event(notes="x" * 1020)
    cut = hll.apply_live_lock(long_ev, _machine())["reasoning_notes"]
    assert len(cut) <= 1024 and cut.endswith("live_lock=OPEN_REJECTION_REVERSE/DOWN@16:45 IL")
    assert hll.apply_live_lock(_event(notes=None), _machine())["reasoning_notes"] == "live_lock=OPEN_REJECTION_REVERSE/DOWN@16:45 IL"


def test_bridge_failure_is_a_warning_and_the_event_goes_through_unchanged(monkeypatch, caplog):
    monkeypatch.setenv(FLAG, "1")
    no_ts = _event()
    del no_ts["timestamp"]
    with caplog.at_level(logging.WARNING, logger=hll.logger.name):
        assert hll.apply_live_lock(no_ts, _machine()) is no_ts
    assert any("live-lock bridge failed" in r.getMessage() for r in caplog.records)

    class _Bad:
        @property
        def _opening_type_locked(self):
            raise RuntimeError("boom")

    ev = _event()
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=hll.logger.name):
        assert hll.apply_live_lock(ev, _Bad()) is ev
    assert any("live-lock bridge failed" in r.getMessage() for r in caplog.records)


# ── DayTypeConsumer: locked_at is additive ──────────────────────────────────────────────────────────────────────────


def test_consumer_writes_locked_at_only_when_the_event_carries_it(factory):
    c = DayTypeConsumer(factory)
    c.consume(_event())                                                  # INSERT without the key: NULL, as always
    assert _only_row(factory).locked_at is None
    stamped = dict(_event(day_type="Normal"), locked_at=datetime(2026, 10, 19, 13, 45, 4, tzinfo=timezone.utc))
    c.consume(stamped)                                                   # UPDATE with it
    assert _as_utc(_only_row(factory).locked_at) == datetime(2026, 10, 19, 13, 45, 4, tzinfo=timezone.utc)
    c.consume(_event(day_type="Variation"))                              # UPDATE without it: the stamp is not erased
    row = _only_row(factory)
    assert row.day_type == "Variation"
    assert _as_utc(row.locked_at) == datetime(2026, 10, 19, 13, 45, 4, tzinfo=timezone.utc)


def test_consumer_insert_with_locked_at_text_and_datetime(factory):
    c = DayTypeConsumer(factory)
    c.consume(dict(_event(), locked_at="2026-10-19T13:45:04+00:00"))
    assert _as_utc(_only_row(factory).locked_at) == datetime(2026, 10, 19, 13, 45, 4, tzinfo=timezone.utc)


# ── the real `_day_type_on_bar` closure hands the consumer the bridged event ────────────────────────────────────────


def _fake_classification(opening="OPEN_DRIVE"):
    now = datetime(2026, 10, 19, 14, 20, tzinfo=timezone.utc)
    return SimpleNamespace(
        timestamp=now, day_type=DayType.Trend_Normal, probability=0.7, directional_certainty="HIGH",
        trading_confidence="LOW", ib_h=5260.0, ib_l=5240.0, ib_width=20.0, ib_width_class="MEDIUM", opening_type=opening,
        last_updated_at=now, reasoning_notes="Converted from DayTypeState stage=B2", active_zohar_rules=[])


def _handler_run(monkeypatch, flag):
    monkeypatch.delenv("DAYTYPE_MACHINE_CLOSED_BARS_V1", raising=False)     # this file is about the history row only
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    h = Harness(monkeypatch)
    h.machine.to_classification = lambda: _fake_classification()
    h.machine._opening_type_locked, h.machine._opening_locked_val = True, "OPEN_REJECTION_REVERSE"
    h.machine._opening_locked_dir, h.machine._opening_locked_at = "DOWN", LOCK_AT
    h.push(et(10, 20, 3), {"ts": "2026-10-19 14:20:00+00:00", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0,
                           "volume": 12.0})
    return h


def test_handler_flag_off_hands_the_consumer_the_event_as_built(monkeypatch):
    h = _handler_run(monkeypatch, None)
    (ev,) = h.consumed
    assert ev["opening_type"] == "OPEN_DRIVE" and "locked_at" not in ev
    assert ev["reasoning_notes"] == "Converted from DayTypeState stage=B2" and ev["day_type"] == "Trend_Normal"
    assert h.warnings == []


def test_handler_flag_on_hands_the_consumer_the_live_lock(monkeypatch):
    h = _handler_run(monkeypatch, "1")
    (ev,) = h.consumed
    assert ev["opening_type"] == "OPEN_REJECTION_REVERSE"
    assert ev["locked_at"] == datetime(2026, 10, 19, 13, 45, 4, 123456, tzinfo=timezone.utc)
    assert ev["reasoning_notes"] == "Converted from DayTypeState stage=B2 live_lock=OPEN_REJECTION_REVERSE/DOWN@16:45 IL"
    assert ev["day_type"] == "Trend_Normal" and h.warnings == []


def test_handler_flag_on_bridge_import_or_call_failure_writes_the_old_row(monkeypatch):
    def boom(event, machine):
        raise RuntimeError("boom")

    monkeypatch.setattr(hll, "apply_live_lock", boom)
    h = _handler_run(monkeypatch, "1")
    (ev,) = h.consumed
    assert ev["opening_type"] == "OPEN_DRIVE" and "locked_at" not in ev          # the row is written as before
    assert any("live-lock history bridge unavailable" in r.getMessage() for r in h.warnings)


# ── wiring (strings) ────────────────────────────────────────────────────────────────────────────────────────────────


def test_main_wiring_strings():
    s = open(MAIN, encoding="utf-8").read()
    assert "                        _hist_event = {\n                            \"timestamp\": classification.timestamp.isoformat()," in s
    assert "from backend.v9.systems.day_type.history_live_lock import apply_live_lock as _hist_live_lock" in s
    assert "_hist_event = _hist_live_lock(_hist_event, day_type_machine)" in s
    assert "_day_type_consumer.consume(_hist_event)" in s
    assert "_day_type_consumer.consume({" not in s                       # the event always goes through the bridge call
    c = open(os.path.join(ROOT, "backend", "v9", "systems", "day_type", "consumer.py"), encoding="utf-8").read()
    assert c.count('classification_event.get("locked_at") is not None') == 2     # UPDATE and INSERT, only when present
