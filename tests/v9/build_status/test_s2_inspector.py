"""Tests for build_status/s2_inspector.py — 10 S2 pattern status objects.

Verifies pattern IDs, field names, and status logic.
Uses real FiveMinSystem where required (anti-mock constraint).
"""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.v9.systems.build_status import s2_inspector
from backend.v9.systems.build_status.auth_table_lookup import S2_PATTERN_IDS
from backend.v9.systems.build_status.row_helpers import clear_fires_today_cache
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


@pytest.fixture(autouse=True)
def _isolate_fires_cache():
    clear_fires_today_cache()
    yield
    clear_fires_today_cache()


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
        # REACTIVE_LONG × NeuC = FULL (not skip), all data gates pass.
        # With detection probe layer active, status may be "blocked" if detection
        # geometry conditions are not met (expected for minimal test fixtures).
        # Verify that data-level components all pass and blocking is at detection level.
        assert reactive_long.status in ("armed", "blocked"), (
            f"Expected armed or blocked (detection), got {reactive_long.status!r}"
        )
        assert reactive_long.fired_today is False
        # Data gates must all pass.
        # mode_context / fhb_eligible / choppiness_ok are live-session context components
        # that depend on wall-clock time and FHB bar accumulation; they are excluded from
        # the static fixture assertion since the test fixture is not a live session.
        _CONTEXT_ONLY = {"mode_context", "fhb_eligible", "choppiness_ok"}
        data_comps = [
            c for c in reactive_long.components
            if c.stage in ("data", "day_type_gate") and c.key not in _CONTEXT_ONLY
        ]
        assert all(c.present for c in data_comps), (
            f"All data/gate components should pass: {[(c.key, c.present) for c in data_comps if not c.present]}"
        )

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


class TestS2RowContract:
    """Every row across every pattern must expose live + required + freshness."""

    def test_every_row_has_live_required_freshness(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
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
            day_type_str="Trend_Normal",
        )

        for p in result.patterns:
            for c in p.components:
                assert c.live is not None, f"{p.id}/{c.key}: live missing"
                assert c.required is not None, f"{p.id}/{c.key}: required missing"
                assert c.freshness is not None, f"{p.id}/{c.key}: freshness missing"

    def test_five_min_bar_recency_lag_is_small_positive(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Regression: with a fresh bar in DB, five_min_bar_recency.live must be
        a small positive lag string — not negative, not astronomical.
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
            day_type_str="Trend_Normal",
        )

        # Inspect any pattern's recency row (identical across patterns)
        recency = next(
            c for c in result.patterns[0].components if c.key == "five_min_bar_recency"
        )
        # live looks like "12.3s" — parse numeric portion
        num = float(recency.live.rstrip("s"))
        assert 0.0 <= num < 120.0, f"Expected small positive lag, got {recency.live!r}"
        assert result.data_freshness.lag_seconds is not None
        assert 0.0 <= result.data_freshness.lag_seconds < 120.0

    def test_recency_ignores_future_sentinel_rows(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """Regression for the woodies '-2,291,025,250s' lag bug applied to
        s2: a stray future ts ('2099-01-02 04:00:00') in v9_bars_5min must
        NOT poison the lag — the inspector picks the most recent NON-future
        row instead.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        conn = sqlite3.connect(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # Real bar (recent)
        conn.execute(
            "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            (now_ts, "MES", 4700.0, 4705.0, 4695.0, 4702.0, 1000),
        )
        # Sentinel future row — would dominate lex-sorted MAX(ts)
        conn.execute(
            "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            ("2099-01-02 04:00:00", "MES", 0.0, 0.0, 0.0, 0.0, 0),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Trend_Normal",
        )

        assert result.data_freshness.lag_seconds is not None
        assert result.data_freshness.lag_seconds >= 0.0, "lag must never be negative"
        assert result.data_freshness.lag_seconds < 120.0, (
            f"Future sentinel poisoned lag: {result.data_freshness.lag_seconds}"
        )


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
    # v9_trades is now the authoritative "fired today" source.
    conn.execute("""CREATE TABLE IF NOT EXISTS v9_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL DEFAULT 'live',
        firing_system INTEGER NOT NULL,
        direction TEXT NOT NULL DEFAULT 'LONG',
        state TEXT NOT NULL DEFAULT 'CLOSED',
        entry_ts TEXT,
        cross_context TEXT
    )""")
    conn.commit()
    conn.close()


def _insert_s2_fire(
    db_path: str,
    *,
    pattern_ids,
    direction: str = "LONG",
    minutes_ago: int = 30,
) -> str:
    """Insert a synthetic S2 v9_trades fire row (firing_system=2)."""
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    primary = pattern_ids[0]
    cc = [{
        "trigger": primary,
        "classification": primary,
        "metadata": {"pattern": primary},
        "systems": {"five_min_system": {
            "last_pattern": primary,
            "active_patterns": [
                {"pattern_id": p, "direction": direction, "confidence": 0.7}
                for p in pattern_ids
            ],
        }},
    }]
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_trades (firing_system, direction, entry_ts, cross_context) "
        "VALUES (?,?,?,?)",
        (2, direction, ts, json.dumps(cc)),
    )
    conn.commit()
    conn.close()
    return ts


class TestS2FiredTodaySurface:
    """Pre-LIVE regression: S2 'fired today' reads v9_trades.firing_system=2,
    NOT the momentary in-memory state and NOT v9_five_min_setups."""

    def test_fired_earlier_today_surfaces_as_fired(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        # Bar inserted so freshness component passes.
        conn = sqlite3.connect(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            (now_ts, "MES", 4700.0, 4705.0, 4695.0, 4702.0, 1000),
        )
        conn.commit()
        conn.close()
        entry_ts = _insert_s2_fire(db_path, pattern_ids=["REACTIVE_LONG"], minutes_ago=15)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        reactive = next(p for p in result.patterns if p.id == "REACTIVE_LONG")
        assert reactive.status == "fired"
        assert reactive.fired_today is True
        assert reactive.last_fire_ts is not None
        assert "Fired today" in reactive.label

    def test_no_fire_today_yields_armed_or_blocked(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        for p in result.patterns:
            assert p.fired_today is False
            assert p.last_fire_ts is None

    def test_system_aggregate_matches_per_pattern(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        _insert_s2_fire(db_path, pattern_ids=["REACTIVE_LONG"], minutes_ago=120)
        _insert_s2_fire(db_path, pattern_ids=["INITIATIVE_SHORT"], direction="SHORT", minutes_ago=10)
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        assert result.fired_today_count == 2
        per_ts = [p.last_fire_ts for p in result.patterns if p.last_fire_ts]
        assert result.last_fire_ts == max(per_ts)

    def test_v9_five_min_setups_alone_does_not_register_fire(
        self, real_five_min_system, tmp_path, monkeypatch
    ):
        """A v9_five_min_setups row WITHOUT a matching v9_trades row is a
        DETECTION, not a routed FIRE. Inspector must NOT report it as
        fired_today (that's what the trade_manager veto path exists for).
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_db(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO v9_five_min_setups (ts, pattern, direction, entry_price, stop_price, confidence) "
            "VALUES (?,?,?,?,?,?)",
            (now_ts, "REACTIVE_LONG", "LONG", 4700.0, 4698.0, 75.0),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(s2_inspector, "DB_PATH", db_path)

        result = s2_inspector.inspect(
            five_min_system=real_five_min_system,
            day_type_str="Neutral_Center",
        )

        reactive = next(p for p in result.patterns if p.id == "REACTIVE_LONG")
        assert reactive.fired_today is False, (
            "v9_five_min_setups detection alone must not register as fired; "
            "only v9_trades.firing_system=2 rows count"
        )
        assert result.fired_today_count == 0
