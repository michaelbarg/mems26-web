# -*- coding: utf-8 -*-
"""T-590 (18.10): TPO letters from the bar clock (TPO_LETTER_BY_TS_V1, default OFF).

Live finding (mems26, v9_tpo_sessions / v9_tpo_journal, 21.09-09.10): the TPO letter advanced every 6 PUSHES of
`process_bar` — developing pushes arrive every ~3 s (7,438 journal rows for 78 bars on 08.10) — and froze for
good once `bar_buffer` reached its cap of 100 (100 % 6 != 0). Result: a full RTH day was either letters A..Q
inside the first five minutes (21.09, 25.09, 28.09) or letter 'A' all day (every other day), and the persisted
poc/vah/val — the tree's prior-day value area (`_load_previous_cash_session`) and S1's pd_poc/pd_vah/pd_val —
came from that one-letter profile (01.10: VA 7727.75-7730.25 for a whole session).
"""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from backend.v9.systems.tpo import tpo_system as T
from backend.v9.systems.tpo.tpo_system import TPOSystem, _letter_idx_by_ts, _session_open_et


def _bar(ts_iso, high, low):
    return SimpleNamespace(payload={"ts": ts_iso, "high": high, "low": low, "close": low},
                           ts=ts_iso, session="CASH_HOURS", mode="REPLAY")


def _quiet(sys_):
    """No Sierra reads, no DB writes: the test drives the profile only."""
    sys_._update_ib = lambda bar, session: None
    sys_._update_va_from_sierra = lambda: None
    return sys_


class TestLetterIndexByTs(unittest.TestCase):
    def test_cash_periods_from_0930_et(self):
        # 08.10.2026 is EDT: 13:30 UTC == 09:30 ET
        self.assertEqual(_letter_idx_by_ts("2026-10-08T13:30:00+00:00", "CASH"), 0)
        self.assertEqual(_letter_idx_by_ts("2026-10-08T13:59:59+00:00", "CASH"), 0)
        self.assertEqual(_letter_idx_by_ts("2026-10-08T14:00:00+00:00", "CASH"), 1)
        self.assertEqual(_letter_idx_by_ts("2026-10-08T19:55:00+00:00", "CASH"), 12)   # 'M'
        self.assertEqual(_letter_idx_by_ts("2026-10-08T13:25:00+00:00", "CASH"), 0)   # pre-open → clamp

    def test_globex_periods_from_1600_et_previous_day(self):
        self.assertEqual(_letter_idx_by_ts("2026-10-08T20:00:00+00:00", "GLOBEX"), 0)    # 16:00 ET
        self.assertEqual(_letter_idx_by_ts("2026-10-08T23:30:00+00:00", "GLOBEX"), 7)    # 19:30 ET
        self.assertEqual(_letter_idx_by_ts("2026-10-09T12:00:00+00:00", "GLOBEX"), 32)   # 08:00 ET next day
        et, open_et = _session_open_et("2026-10-09T12:00:00+00:00", "GLOBEX")
        self.assertEqual(open_et.isoformat(), "2026-10-08T16:00:00-04:00")

    def test_epoch_seconds_via_norm_and_garbage(self):
        self.assertEqual(_letter_idx_by_ts(T._norm_bar_ts(1790352900), "CASH"), 5)       # 25.09 12:15 ET → 'F'
        self.assertIsNone(_letter_idx_by_ts("", "CASH"))
        self.assertIsNone(_letter_idx_by_ts("not-a-time", "CASH"))
        self.assertIsNone(_session_open_et(None, "CASH"))


def _drive(sys_, pushes_per_bar=95):
    """Three 30-minute periods, one 5-min bar each, every bar pushed `pushes_per_bar` times (developing pushes)."""
    bars = [("2026-10-08T13:30:00+00:00", 7831.0, 7829.0),   # 09:30 ET → 'A'
            ("2026-10-08T14:00:00+00:00", 7832.0, 7830.0),   # 10:00 ET → 'B'
            ("2026-10-08T14:30:00+00:00", 7831.0, 7828.0)]   # 10:30 ET → 'C'
    for ts, hi, lo in bars:
        for _ in range(pushes_per_bar):
            asyncio.run(sys_.process_bar(_bar(ts, hi, lo)))


class TestProcessBarLetters(unittest.TestCase):
    def setUp(self):
        self._se = mock.patch("backend.v9.db.safe_writer.safe_execute", lambda *a, **k: None)
        self._se.start()
        self._ra = mock.patch("backend.v9.db.read.read_all", lambda *a, **k: [])
        self._ra.start()

    def tearDown(self):
        self._se.stop()
        self._ra.stop()

    def test_flag_on_letters_follow_the_clock(self):
        with mock.patch.dict(os.environ, {"TPO_LETTER_BY_TS_V1": "1"}):
            s = _quiet(TPOSystem())
            _drive(s)
        self.assertEqual(s.current_state["letter_count"], 3)
        self.assertEqual(s.profile["7830.50"], ["A", "B", "C"])     # inside all three bars
        self.assertEqual(s.profile["7828.00"], ["C"])
        self.assertTrue(all(len(v) == len(set(v)) for v in s.profile.values()))

    def test_flag_off_keeps_the_legacy_push_counter(self):
        """Flag-off parity with live: the letter advances at pushes 6, 12, ..., 96 and freezes once the 100-push
        buffer is full — 17 'letters' inside three periods (the live 21.09/25.09/28.09 rows)."""
        with mock.patch.dict(os.environ, {"TPO_LETTER_BY_TS_V1": "0"}):
            s = _quiet(TPOSystem())
            _drive(s)
        self.assertEqual(s.current_state["letter_count"], 17)
        self.assertEqual(len(s.bar_buffer), s.max_buffer)

    def test_flag_on_seeds_the_profile_from_stored_bars_on_restart(self):
        from datetime import datetime, timedelta, timezone
        t0 = datetime(2026, 10, 8, 13, 30, tzinfo=timezone.utc)
        stored = [{"ts": t0 + timedelta(minutes=5 * i), "high": 7840.0 + i, "low": 7830.0 + i}
                  for i in range(12)]                                  # 09:30 .. 10:25 ET → 'A' x6, 'B' x6
        with mock.patch("backend.v9.db.read.read_all", lambda *a, **k: stored), \
                mock.patch.dict(os.environ, {"TPO_LETTER_BY_TS_V1": "1"}):
            s = _quiet(TPOSystem())
            s._open_session("CASH_2026-10-08", "CASH", "2026-10-08", "2026-10-08T14:30:00+00:00")
            self.assertEqual(s.current_letter_idx, 1)
            self.assertEqual(s.profile["7841.00"], ["A", "B"])        # bars 1..11
            self.assertEqual(s.profile["7851.00"], ["B"])             # bar 11 only
            asyncio.run(s.process_bar(_bar("2026-10-08T14:30:00+00:00", 7842.0, 7840.0)))   # restart bar → 'C'
        self.assertEqual(s.current_state["letter_count"], 3)
        self.assertEqual(s.profile["7841.00"], ["A", "B", "C"])

    def test_flag_off_does_not_touch_the_bars_table(self):
        def _boom(*a, **k):
            raise AssertionError("read_all must not be called while T-590 is off")
        with mock.patch("backend.v9.db.read.read_all", _boom), mock.patch.dict(os.environ, {"TPO_LETTER_BY_TS_V1": "0"}):
            s = _quiet(TPOSystem())
            s._open_session("CASH_2026-10-08", "CASH", "2026-10-08", "2026-10-08T14:30:00+00:00")
        self.assertEqual(s.profile, {})
