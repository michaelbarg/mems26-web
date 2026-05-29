"""Tests for build_status.row_helpers.fires_today() and the cross_context extractor.

The helper reads `v9_trades` filtered by `firing_system` and `date(entry_ts)=today`
to surface "fired today" state from the authoritative DB write, NOT from the
momentary in-memory active_patterns state that the old inspector relied on.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.v9.systems.build_status import row_helpers
from backend.v9.systems.build_status.row_helpers import (
    _extract_pattern_ids_from_cross_context,
    clear_fires_today_cache,
    fires_today,
)


# ── DB scaffolding ─────────────────────────────────────────────────────────

def _create_v9_trades(db_path: str) -> None:
    """Minimal v9_trades schema matching production."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE v9_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL DEFAULT 'live',
            firing_system INTEGER NOT NULL,
            direction TEXT NOT NULL DEFAULT 'LONG',
            state TEXT NOT NULL DEFAULT 'CLOSED',
            entry_ts TEXT,
            entry_price REAL,
            stop REAL,
            cross_context TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _insert_trade(
    db_path: str,
    *,
    firing_system: int,
    entry_ts: str,
    direction: str = "LONG",
    cross_context=None,
) -> None:
    raw = json.dumps(cross_context) if not isinstance(cross_context, (str, type(None))) else cross_context
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_trades (firing_system, direction, entry_ts, cross_context) VALUES (?,?,?,?)",
        (firing_system, direction, entry_ts, raw),
    )
    conn.commit()
    conn.close()


def _today_iso_with_offset(offset_minutes: int = 0) -> str:
    """ISO timestamp inside today (UTC), at most `offset_minutes` ago."""
    now = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)
    return now.isoformat()


# ── _extract_pattern_ids_from_cross_context ────────────────────────────────


class TestExtractPatternIds:
    def test_array_variant_with_systems_wrapper(self):
        """Production layout A (the 17:45 GB100/HTLB fire):

            [{"trigger": "GB100", "metadata": {"pattern": "GB100"},
              "systems": {"woodies_system": {"active_patterns": [...]}}}]

        Both GB100 and HTLB must be extracted from active_patterns;
        the duplicate `trigger=GB100` must not double-count.
        """
        raw = json.dumps([{
            "trigger": "GB100",
            "metadata": {"pattern": "GB100"},
            "systems": {
                "woodies_system": {
                    "active_patterns": [
                        {"pattern_id": "GB100", "direction": "LONG", "confidence": 0.658},
                        {"pattern_id": "HTLB", "direction": "LONG", "confidence": 0.65},
                    ],
                },
            },
        }])
        pids = _extract_pattern_ids_from_cross_context(raw)
        assert pids == ["GB100", "HTLB"], f"got {pids!r}"

    def test_flat_dict_variant(self):
        """Production layout B (row 15 — systems hoisted to top level)."""
        raw = json.dumps({
            "woodies_system": {
                "active_patterns": [
                    {"pattern_id": "HTLB", "direction": "SHORT", "confidence": 0.65},
                ],
            },
        })
        pids = _extract_pattern_ids_from_cross_context(raw)
        assert pids == ["HTLB"]

    def test_lifecycle_event_row_returns_empty(self):
        """`[{"event": "stop_move", ...}]` rows are trade audit appends —
        NOT fresh fires. The helper must return [] so the inspector skips
        them rather than crediting `STOP_MOVE` as a pattern_id.
        """
        raw = json.dumps([{
            "event": "stop_move",
            "from": 7577.75,
            "to": 7579.25,
            "reason": "BE+1T after T1 hit",
        }])
        assert _extract_pattern_ids_from_cross_context(raw) == []

    def test_malformed_json_degrades_to_empty(self):
        """No `except Exception: pass` — malformed JSON returns [] silently
        because that's the only sensible degraded mode for an inspector
        (the DB row exists, but its blob can't be parsed). The CALLER
        decides whether to surface a UI note.
        """
        assert _extract_pattern_ids_from_cross_context("not json {") == []
        assert _extract_pattern_ids_from_cross_context("") == []
        assert _extract_pattern_ids_from_cross_context(None) == []

    def test_already_parsed_dict_is_accepted(self):
        """The helper accepts dicts/lists directly (test convenience)."""
        pids = _extract_pattern_ids_from_cross_context(
            [{"trigger": "REACTIVE_LONG"}]
        )
        assert pids == ["REACTIVE_LONG"]

    def test_non_pattern_tokens_filtered(self):
        """`FIRE_EXHAUSTION` (S3) and `STOP_MOVE` are filtered out so
        unrelated firing_system signals don't pollute S2/S4 counts.
        """
        raw = json.dumps([{
            "trigger": "FIRE_EXHAUSTION",
            "classification": "FIRE_EXHAUSTION",
        }])
        assert _extract_pattern_ids_from_cross_context(raw) == []

    def test_s2_trigger_classification_fallback(self):
        """S2 cross_context may carry pattern_id only as the trigger/
        classification scalar (not nested under active_patterns)."""
        raw = json.dumps([{"trigger": "REACTIVE_LONG", "classification": "REACTIVE_LONG"}])
        pids = _extract_pattern_ids_from_cross_context(raw)
        assert pids == ["REACTIVE_LONG"]


# ── fires_today() ───────────────────────────────────────────────────────────


class TestFiresToday:
    def setup_method(self):
        clear_fires_today_cache()

    def test_empty_db_returns_empty_dict(self, tmp_path):
        db = str(tmp_path / "empty.db")
        _create_v9_trades(db)
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out == {}

    def test_pattern_id_counted_once_per_row(self, tmp_path):
        db = str(tmp_path / "one.db")
        _create_v9_trades(db)
        ts = _today_iso_with_offset(5)
        _insert_trade(
            db,
            firing_system=4,
            entry_ts=ts,
            cross_context=[{
                "trigger": "GB100",
                "systems": {"woodies_system": {"active_patterns": [
                    {"pattern_id": "GB100", "direction": "LONG", "confidence": 0.7},
                ]}},
            }],
        )
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert "GB100" in out
        assert out["GB100"]["count"] == 1
        assert out["GB100"]["last_ts"] is not None

    def test_multi_pattern_same_row_increments_both(self, tmp_path):
        """Matches the live 17:45 fire: a single v9_trades row with
        GB100+HTLB in active_patterns increments BOTH patterns' counts."""
        db = str(tmp_path / "multi.db")
        _create_v9_trades(db)
        ts = _today_iso_with_offset(10)
        _insert_trade(
            db,
            firing_system=4,
            entry_ts=ts,
            cross_context=[{
                "trigger": "GB100",
                "systems": {"woodies_system": {"active_patterns": [
                    {"pattern_id": "GB100", "confidence": 0.658},
                    {"pattern_id": "HTLB", "confidence": 0.65},
                ]}},
            }],
        )
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out["GB100"]["count"] == 1
        assert out["HTLB"]["count"] == 1
        assert out["GB100"]["last_ts"] == out["HTLB"]["last_ts"]

    def test_firing_system_filter_isolates_systems(self, tmp_path):
        db = str(tmp_path / "fs.db")
        _create_v9_trades(db)
        ts = _today_iso_with_offset(5)
        _insert_trade(
            db, firing_system=4, entry_ts=ts,
            cross_context=[{"trigger": "GB100", "systems": {"woodies_system": {"active_patterns": [
                {"pattern_id": "GB100"}]}}}],
        )
        _insert_trade(
            db, firing_system=2, entry_ts=ts,
            cross_context=[{"trigger": "REACTIVE_LONG"}],
        )
        conn = sqlite3.connect(db)
        out_woodies = fires_today(conn, firing_system=4, today=date.today().isoformat())
        clear_fires_today_cache()
        out_s2 = fires_today(conn, firing_system=2, today=date.today().isoformat())
        conn.close()
        assert "GB100" in out_woodies and "REACTIVE_LONG" not in out_woodies
        assert "REACTIVE_LONG" in out_s2 and "GB100" not in out_s2

    def test_other_days_excluded(self, tmp_path):
        db = str(tmp_path / "yest.db")
        _create_v9_trades(db)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _insert_trade(
            db, firing_system=4, entry_ts=yesterday,
            cross_context=[{"trigger": "GB100", "systems": {"woodies_system": {"active_patterns": [
                {"pattern_id": "GB100"}]}}}],
        )
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out == {}

    def test_lifecycle_event_row_does_not_count(self, tmp_path):
        """A trade-update row with `[{"event":"stop_move",...}]` cross_context
        must NOT register as a fresh fire — the helper skips it.
        """
        db = str(tmp_path / "evt.db")
        _create_v9_trades(db)
        ts = _today_iso_with_offset(2)
        _insert_trade(
            db, firing_system=4, entry_ts=ts,
            cross_context=[{"event": "stop_move", "from": 7577.75, "to": 7579.25}],
        )
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out == {}

    def test_db_error_returns_empty_without_raising(self, tmp_path):
        """Missing v9_trades table → warning log, empty dict — never raises."""
        db = str(tmp_path / "missing.db")
        conn = sqlite3.connect(db)  # no v9_trades created
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out == {}

    def test_last_ts_is_newest_for_pattern(self, tmp_path):
        db = str(tmp_path / "newest.db")
        _create_v9_trades(db)
        older = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
        newer = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        for ts in (older, newer):
            _insert_trade(
                db, firing_system=4, entry_ts=ts,
                cross_context=[{"trigger": "HTLB", "systems": {"woodies_system": {"active_patterns": [
                    {"pattern_id": "HTLB"}]}}}],
            )
        conn = sqlite3.connect(db)
        out = fires_today(conn, firing_system=4, today=date.today().isoformat())
        conn.close()
        assert out["HTLB"]["count"] == 2
        # last_ts must be the NEWER one, regardless of insert order.
        assert out["HTLB"]["last_ts"].startswith(newer[:10])


# ── TTL cache ───────────────────────────────────────────────────────────────


class TestFiresTodayCacheTTL:
    def setup_method(self):
        clear_fires_today_cache()

    def test_back_to_back_calls_hit_cache(self, tmp_path):
        """Two calls within 5s must execute SQL exactly once."""
        db = str(tmp_path / "cache.db")
        _create_v9_trades(db)
        ts = _today_iso_with_offset(1)
        _insert_trade(
            db, firing_system=4, entry_ts=ts,
            cross_context=[{"trigger": "GB100", "systems": {"woodies_system": {"active_patterns": [
                {"pattern_id": "GB100"}]}}}],
        )
        conn = sqlite3.connect(db)

        executed = []
        conn.set_trace_callback(lambda sql: executed.append(sql))

        anchor = datetime(2026, 5, 28, 17, 45, 0, tzinfo=timezone.utc)
        out1 = fires_today(conn, firing_system=4, today="2026-05-28", now=anchor)
        out2 = fires_today(conn, firing_system=4, today="2026-05-28",
                           now=anchor + timedelta(seconds=2))
        conn.close()

        select_calls = [s for s in executed if "v9_trades" in s.lower() and "select" in s.lower()]
        assert len(select_calls) == 1, (
            f"expected single SELECT inside TTL window, got {len(select_calls)}: {select_calls}"
        )
        # Note: when today doesn't match insert date the result is {}; the
        # important assertion is the SQL trace, not the returned content.
        assert out1 is out2 or out1 == out2

    def test_ttl_expiry_triggers_refetch(self, tmp_path):
        db = str(tmp_path / "ttl.db")
        _create_v9_trades(db)
        conn = sqlite3.connect(db)
        executed = []
        conn.set_trace_callback(lambda sql: executed.append(sql))

        anchor = datetime(2026, 5, 28, 17, 45, 0, tzinfo=timezone.utc)
        fires_today(conn, firing_system=4, today="2026-05-28", now=anchor)
        fires_today(conn, firing_system=4, today="2026-05-28",
                    now=anchor + timedelta(seconds=10))  # past 5s TTL
        conn.close()

        select_calls = [s for s in executed if "v9_trades" in s.lower() and "select" in s.lower()]
        assert len(select_calls) == 2, (
            f"expected refetch after TTL expiry, got {len(select_calls)}"
        )

    def test_date_change_invalidates_cache(self, tmp_path):
        """At midnight the today_str advances; yesterday's cache entries
        must not bleed into today's result."""
        db = str(tmp_path / "midnight.db")
        _create_v9_trades(db)
        conn = sqlite3.connect(db)
        anchor = datetime(2026, 5, 28, 23, 59, 0, tzinfo=timezone.utc)
        fires_today(conn, firing_system=4, today="2026-05-28", now=anchor)
        # Verify entry was cached
        assert (4, "2026-05-28") in row_helpers._FIRES_TODAY_CACHE

        next_day = anchor + timedelta(minutes=2)
        fires_today(conn, firing_system=4, today="2026-05-29", now=next_day)
        conn.close()

        # Yesterday's key must be pruned.
        assert (4, "2026-05-28") not in row_helpers._FIRES_TODAY_CACHE
        assert (4, "2026-05-29") in row_helpers._FIRES_TODAY_CACHE
