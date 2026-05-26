"""Tests for build_status/s2_inspector.py — 10 S2 pattern status objects.

Verifies pattern IDs, field names, and status logic.
Uses real FiveMinSystem where required (anti-mock constraint).
"""

import sqlite3
from datetime import date, datetime, timezone

import pytest

from backend.v9.systems.build_status import s2_inspector
from backend.v9.systems.build_status.auth_table_lookup import S2_PATTERN_IDS
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


class TestS2PatternList:
    def test_s2_inspector_returns_10_patterns(self, real_five_min_system, tmp_path, monkeypatch):
        """Test #4: inspect() returns exactly 10 patterns with correct IDs.

        Exact IDs: REACTIVE_LONG, REACTIVE_SHORT, INITIATIVE_LONG, INITIATIVE_SHORT,
        INVERSE_HNS_LONG, HNS_TOP_SHORT, DOUBLE_BOTTOM_EE_LONG, DOUBLE_TOP_AA_SHORT,
        BULL_FLAG_LONG, BEAR_FLAG_SHORT
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        pattern_ids = [p.id for p in result.patterns]
        assert len(pattern_ids) == 10
        assert pattern_ids == S2_PATTERN_IDS

    def test_s2_inspector_returns_unknown_when_system_none(self, tmp_path, monkeypatch):
        """System=None → all patterns have status='unknown'."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(five_min_system=None, day_type_str=None)

        assert result.running is False
        assert result.hydrated is False
        for p in result.patterns:
            assert p.status == "unknown", f"Pattern {p.id} should be unknown"

    def test_component_keys_match_spec(self, real_five_min_system, tmp_path, monkeypatch):
        """Each pattern must have five_min_bar_recency, cci_14_history, day_type_known,
        auth_table_cell, nt_skip components."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Trend_Normal",
        )

        required_keys = {
            "five_min_bar_recency", "cci_14_history",
            "day_type_known", "auth_table_cell", "nt_skip",
        }
        for p in result.patterns:
            pattern_keys = {c.key for c in p.components}
            assert required_keys.issubset(pattern_keys), (
                f"Pattern {p.id} missing component keys: {required_keys - pattern_keys}"
            )


class TestS2StatusLogic:
    def test_pattern_status_fired_when_setup_emitter_emitted_today(
        self, real_five_min_system, temp_db_with_today_fire, monkeypatch
    ):
        """Test #7: REACTIVE_LONG fire row in v9_five_min_setups → status='fired', fired_today=True."""
        db_path, today = temp_db_with_today_fire
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        reactive_long = next(p for p in result.patterns if p.id == "REACTIVE_LONG")
        assert reactive_long.status == "fired", (
            f"Expected fired, got {reactive_long.status!r}. "
            f"Table: v9_five_min_setups (setup_emitter.py write path)"
        )
        assert reactive_long.fired_today is True

    def test_pattern_status_armed_when_all_components_present_no_fire_yet(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Test #8: all components OK, no fire row → status='armed'."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        # Insert a recent bar to make freshness = fresh
        conn = sqlite3.connect(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            (now_ts, "MES", 4700.0, 4705.0, 4695.0, 4702.0, 1000),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        # Buffer has 14 bars → cci_ok = True
        # Day type known, not NT, not skip for NeuC + REACTIVE_LONG
        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,  # 14 bars in buffer
            day_type_str="Neutral_Center",
        )

        reactive_long = next(p for p in result.patterns if p.id == "REACTIVE_LONG")
        # REACTIVE_LONG × NeuC = FULL (not skip) → all components present → armed
        assert reactive_long.status == "armed", (
            f"Expected armed when no fire, got {reactive_long.status!r}"
        )
        assert reactive_long.fired_today is False

    def test_pattern_status_blocked_when_auth_table_cell_is_skip(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Test #9: BULL_FLAG_LONG × NeuC = SKIP → status='blocked'.

        S2_AUTH_TABLE_V1.md §1 typo fix: Bull Flag NeuC LOW → 0/0/0 (SKIP).
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        conn = sqlite3.connect(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            (now_ts, "MES", 4700.0, 4705.0, 4695.0, 4702.0, 1000),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        bull_flag = next(p for p in result.patterns if p.id == "BULL_FLAG_LONG")
        assert bull_flag.status == "blocked", (
            f"BULL_FLAG_LONG × NeuC should be blocked (SKIP cell), got {bull_flag.status!r}"
        )
        auth_cell_comp = next(c for c in bull_flag.components if c.key == "auth_table_cell")
        assert auth_cell_comp.present is False

    def test_pattern_status_vetoed_when_nt_day_type(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Test #10: NT day type → all patterns vetoed.

        S2_AUTH_TABLE_V1.md §6.1: "NT → global skip".
        D-091.Q2: "Nontrend → NO TRADE global gate".
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Nontrend",
        )

        for p in result.patterns:
            assert p.status == "vetoed", (
                f"Pattern {p.id} should be vetoed on NT day, got {p.status!r}"
            )

    def test_cci_14_history_component_reflects_real_buffer(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Buffer has 14 bars → cci_14_history.present must be True.

        Verifies _bar_buffer access path (anti-dead-code-wiring test).
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Trend_Normal",
        )

        for p in result.patterns:
            cci_comp = next(c for c in p.components if c.key == "cci_14_history")
            assert cci_comp.present is True, (
                f"Pattern {p.id}: cci_14_history.present should be True with 14 bars"
            )
            assert "14" in cci_comp.value or "buffer=14" in cci_comp.value


# ── helpers ─────────────────────────────────────────────────────────────────

def _create_minimal_db(db_path: str) -> None:
    """Create tables needed by s2_inspector with no data."""
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS v9_bars_5min (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        symbol TEXT NOT NULL DEFAULT 'MES',
        open REAL, high REAL, low REAL, close REAL, volume INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS v9_five_min_setups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        pattern TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL DEFAULT 0,
        stop_price REAL NOT NULL DEFAULT 0,
        confidence REAL NOT NULL DEFAULT 75.0
    )""")
    conn.commit()
    conn.close()
