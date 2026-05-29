"""Tests for build_status/woodies_inspector.py — 9 Woodies pattern status objects.

Uses real WoodiesSystem instances per anti-mock constraint.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.v9.systems.build_status import row_helpers, woodies_inspector
from backend.v9.systems.build_status.auth_table_lookup import WOODIES_PATTERN_IDS
from backend.v9.systems.build_status.row_helpers import clear_fires_today_cache
from backend.v9.systems.woodies.woodies_system import WoodiesSystem


@pytest.fixture(autouse=True)
def _isolate_fires_cache():
    """Each test starts and ends with a clean fires_today cache so
    inter-test bleed (e.g. a cached empty dict masking a fresh fixture)
    can't make the assertions racy.
    """
    clear_fires_today_cache()
    yield
    clear_fires_today_cache()


class TestWoodiesPatternList:
    def test_woodies_inspector_returns_9_patterns(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """Test #5: inspect() returns exactly 9 patterns with IDs from D-092 §2.

        Exact IDs: ZLR, TLB, TT, GB100, Vegas, Ghost, FaMir, HTLB, HFE
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        pattern_ids = [p.id for p in result.patterns]
        assert len(pattern_ids) == 9
        assert pattern_ids == WOODIES_PATTERN_IDS

    def test_woodies_inspector_returns_unknown_when_system_none(
        self, tmp_path, monkeypatch
    ):
        """System=None → all 9 patterns have status='unknown', running=False."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=None)

        assert result.running is False
        assert result.hydrated is False
        assert len(result.patterns) == 9
        for p in result.patterns:
            assert p.status == "unknown"

    def test_woodies_system_is_real_instance(self, real_woodies_system):
        """Anti-mock constraint: real_woodies_system must be a WoodiesSystem instance."""
        assert isinstance(real_woodies_system, WoodiesSystem), (
            "real_woodies_system must be a real WoodiesSystem — no MagicMock!"
        )

    def test_woodies_state_keys_match_real_source(self, real_woodies_system):
        """Verify get_current() returns expected field names (anti-typo guard).

        Source: woodies_system.py lines 54-75 (current_state dict definition).
        """
        state = real_woodies_system.get_current()
        expected_keys = {
            "cci_14", "cci_6_tcci", "trend_state", "active_patterns",
            "ready_to_route", "classification", "running", "hydrated",
        }
        for key in expected_keys:
            assert key in state, (
                f"Key {key!r} missing from WoodiesSystem.get_current() — "
                f"field name mismatch would cause silent None reads"
            )


class TestWoodiesStatusLogic:
    def test_cci_not_present_gives_unknown(self, tmp_path, monkeypatch):
        """CCI=None → status='unknown' for all patterns."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        ws = WoodiesSystem()
        ws.current_state.update({
            "running": True,
            "hydrated": False,
            "cci_14": None,  # not computed
            "cci_6_tcci": None,
            "trend_state": "GRAY",
            "active_patterns": [],
            "ready_to_route": False,
        })

        result = woodies_inspector.inspect(woodies_system=ws)

        for p in result.patterns:
            assert p.status == "unknown", (
                f"Pattern {p.id}: expected unknown when CCI=None, got {p.status!r}"
            )

    def test_gray_trend_state_gives_blocked(self, tmp_path, monkeypatch):
        """GRAY trend state → stage_a1 fails → status='blocked' for all patterns.

        Source: MEMS26_WOODIES_DECISION_TREE_V1.md §4 A1:
        "IF cci_14 crosses 0 frequently in last 10 bars → color = GREY → wait"
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        ws = WoodiesSystem()
        ws.current_state.update({
            "running": True,
            "hydrated": True,
            "cci_14": 12.5,
            "cci_6_tcci": 8.0,
            "trend_state": "GRAY",  # A1 blocks
            "active_patterns": [],
            "ready_to_route": False,
        })

        result = woodies_inspector.inspect(woodies_system=ws)

        for p in result.patterns:
            assert p.status == "blocked", (
                f"Pattern {p.id}: expected blocked on GRAY trend, got {p.status!r}"
            )
            strategic_gate = next(
                c for c in p.components if c.key == "strategic_gate"
            )
            assert strategic_gate.present is False

    def test_pattern_in_active_patterns_gives_armed(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """Pattern detected but ready_to_route=False → status='armed'."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        # Set ZLR as active
        real_woodies_system.current_state["active_patterns"] = [
            {"pattern_id": "ZLR", "direction": "LONG", "confidence": 0.75, "group": "CONTINUATION",
             "entry_price": 4700.0, "stop": 4698.0, "targets": [4705.0, 4710.0]},
        ]
        real_woodies_system.current_state["ready_to_route"] = False

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        zlr_pattern = next(p for p in result.patterns if p.id == "ZLR")
        assert zlr_pattern.status == "armed", (
            f"ZLR in active_patterns with ready_to_route=False → should be armed, got {zlr_pattern.status!r}"
        )

    def test_pattern_in_active_patterns_with_ready_gives_fired(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """Pattern detected + ready_to_route=True → status='fired'.

        Post-2026-05-28: `fired_today` is sourced from v9_trades, not the
        momentary in-memory state. With no v9_trades row yet (race window
        between emit and insert), `fired_today` stays False but the status
        still reads 'fired' with a '🟢 Firing now' label — the race-safe
        path in woodies_inspector.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        real_woodies_system.current_state["active_patterns"] = [
            {"pattern_id": "ZLR", "direction": "LONG", "confidence": 0.82, "group": "CONTINUATION",
             "entry_price": 4700.0, "stop": 4698.0, "targets": [4705.0, 4710.0]},
        ]
        real_woodies_system.current_state["ready_to_route"] = True

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        zlr_pattern = next(p for p in result.patterns if p.id == "ZLR")
        assert zlr_pattern.status == "fired"
        # No v9_trades row → fired_today=False (DB-authoritative).
        assert zlr_pattern.fired_today is False
        assert "Firing now" in zlr_pattern.label

    def test_components_include_decision_tree_stages(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """Each Woodies pattern must have stage_a1 component."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        for p in result.patterns:
            keys = {c.key for c in p.components}
            assert "strategic_gate" in keys, (
                f"Pattern {p.id} missing stage_a1/strategic_gate component"
            )
            assert "cci_14_present" in keys, (
                f"Pattern {p.id} missing cci_14_present component"
            )


class TestWoodiesRowContract:
    """Every Woodies row must expose live + required + freshness."""

    def test_every_row_has_live_required_freshness(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        for p in result.patterns:
            for c in p.components:
                assert c.live is not None, f"{p.id}/{c.key}: live missing"
                assert c.required is not None, f"{p.id}/{c.key}: required missing"
                assert c.freshness is not None, f"{p.id}/{c.key}: freshness missing"

    def test_passing_row_has_machine_friendly_live_value(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """cci_14=45.3 → live='45.30', required='!= null', present=True."""
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        zlr = next(
            p for p in woodies_inspector.inspect(woodies_system=real_woodies_system).patterns
            if p.id == "ZLR"
        )
        cci_row = next(c for c in zlr.components if c.key == "cci_14_present")
        assert cci_row.present is True
        assert cci_row.live == "45.30"
        assert cci_row.required == "!= null"

    def test_failing_row_still_exposes_live(self, tmp_path, monkeypatch):
        """trend_state=GRAY fails the strategic_gate but live must still
        show 'GRAY' and required must show 'in {BLUE, RED}'.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        ws = WoodiesSystem()
        ws.current_state.update({
            "running": True, "hydrated": True,
            "cci_14": 12.5, "cci_6_tcci": 8.0,
            "trend_state": "GRAY",
            "active_patterns": [], "ready_to_route": False,
        })

        zlr = next(
            p for p in woodies_inspector.inspect(woodies_system=ws).patterns
            if p.id == "ZLR"
        )
        gate = next(c for c in zlr.components if c.key == "strategic_gate")
        assert gate.present is False
        assert gate.live == "GRAY"
        assert gate.required == "in {BLUE, RED}"


class TestWoodiesRecencyLagFix:
    """Regression for the live screenshot bug:
        5min_bar_recency  Present=✓  Value: lag=-2291025250.0s  (~ -72y)

    Root cause: v9_bars_5min_woodies contains sentinel rows with
    ts='2099-01-02 ...'. The old `SELECT MAX(ts)` lex-sorted text and
    picked those sentinels, yielding a datetime in 2099 → -72y lag.
    """

    def test_fresh_bar_yields_small_positive_lag(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)
        recency = next(
            c for c in result.patterns[0].components if c.key == "5min_bar_recency"
        )
        lag = result.data_freshness.lag_seconds
        assert lag is not None
        assert lag >= 0.0, f"lag must never be negative, got {lag}"
        assert lag < 120.0, f"fresh bar should yield <120s lag, got {lag}"
        # recency.live mirrors that lag
        num = float(recency.live.rstrip("s"))
        assert 0.0 <= num < 120.0

    def test_future_sentinel_row_does_not_poison_lag(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """The exact production-bug repro: a '2099-01-02 04:00:00' row
        sitting in the table must NOT make the lag negative or astronomical.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        conn = sqlite3.connect(db_path)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
        conn.execute(
            "INSERT INTO v9_bars_5min_woodies (ts, open, high, low, close, volume) "
            "VALUES (?,?,?,?,?,?)",
            (now_ts, 4700.0, 4705.0, 4695.0, 4702.0, 1000),
        )
        # 5 sentinel rows like the real DB has
        for h in range(5):
            conn.execute(
                "INSERT INTO v9_bars_5min_woodies (ts, open, high, low, close, volume) "
                "VALUES (?,?,?,?,?,?)",
                (f"2099-01-02 0{h}:00:00", 0.0, 0.0, 0.0, 0.0, 0),
            )
        conn.commit()
        conn.close()
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        lag = result.data_freshness.lag_seconds
        assert lag is not None, "freshness must resolve to a real row"
        assert lag >= 0.0, f"NEVER negative — was {lag}"
        # Bounded reasonable value: well under 1 day (was -2.29e9 before fix).
        assert lag < 86_400.0, f"poisoned by sentinel: {lag}s"

        # Per-row recency must also surface the safe value
        recency = next(
            c for c in result.patterns[0].components if c.key == "5min_bar_recency"
        )
        live_num = float(recency.live.rstrip("s"))
        assert live_num >= 0.0
        assert live_num < 86_400.0


# ── helpers ─────────────────────────────────────────────────────────────────

def _insert_fresh_woodies_bar(db_path: str) -> None:
    """Insert one bar with a recent UTC ts so freshness resolves."""
    conn = sqlite3.connect(db_path)
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    conn.execute(
        "INSERT INTO v9_bars_5min_woodies (ts, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?)",
        (now_ts, 4700.0, 4705.0, 4695.0, 4702.0, 1000),
    )
    conn.commit()
    conn.close()


def _create_minimal_woodies_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS v9_bars_5min_woodies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER
    )""")
    # v9_trades is the authoritative "fired today" source for the inspector.
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


def _insert_woodies_fire(
    db_path: str,
    *,
    engine_pattern_ids,
    direction: str = "LONG",
    minutes_ago: int = 30,
    trigger=None,
) -> str:
    """Insert a synthetic v9_trades fire row mirroring the live 17:45 layout.

    Returns the iso entry_ts string used for the row.
    """
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    aps = [{"pattern_id": p, "direction": direction, "confidence": 0.66}
           for p in engine_pattern_ids]
    cc = [{
        "trigger": trigger or engine_pattern_ids[0],
        "metadata": {"pattern": engine_pattern_ids[0]},
        "systems": {"woodies_system": {
            "active_patterns": aps,
            "ready_to_route": True,
        }},
    }]
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_trades (firing_system, direction, entry_ts, cross_context) "
        "VALUES (?,?,?,?)",
        (4, direction, ts, json.dumps(cc)),
    )
    conn.commit()
    conn.close()
    return ts


class TestWoodiesFiredTodaySurface:
    """Pre-LIVE regression: 'fired today' must survive the in-memory
    active_patterns clearing one second after the fire."""

    def test_fired_earlier_today_no_current_activity(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """A v9_trades row for GB100 exists today; active_patterns is now
        empty (frozen-tail bug repro). Inspector must report status='fired'.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        entry_ts = _insert_woodies_fire(db_path, engine_pattern_ids=["GB100"])
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        # System has nothing active right now — mirrors the post-fire state.
        real_woodies_system.current_state["active_patterns"] = []
        real_woodies_system.current_state["ready_to_route"] = False

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        gb = next(p for p in result.patterns if p.id == "GB100")
        assert gb.status == "fired", f"expected fired, got {gb.status!r}"
        assert gb.fired_today is True
        assert gb.last_fire_ts is not None
        # last_fire_ts in DB-derived ISO form should match what we inserted.
        # Be tolerant of formatting: both should parse to the same instant.
        from datetime import datetime as _dt
        assert _dt.fromisoformat(gb.last_fire_ts).isoformat() == _dt.fromisoformat(entry_ts).isoformat()
        assert "Fired today" in gb.label

    def test_fired_earlier_plus_currently_firing_uses_firing_now_label(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """When a fire is in v9_trades AND the pattern is currently in
        active_patterns + ready_to_route, status stays 'fired' (history
        wins) but the label switches to '🟢 Firing now'.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        _insert_woodies_fire(db_path, engine_pattern_ids=["GB100"], minutes_ago=10)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        real_woodies_system.current_state["active_patterns"] = [
            {"pattern_id": "GB100", "direction": "LONG", "confidence": 0.7,
             "group": "CONTINUATION", "entry_price": 7579.0, "stop": 7577.75,
             "targets": [7582.0, 7585.0]},
        ]
        real_woodies_system.current_state["ready_to_route"] = True

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        gb = next(p for p in result.patterns if p.id == "GB100")
        assert gb.status == "fired"
        assert gb.fired_today is True
        assert "Firing now" in gb.label, (
            f"expected '🟢 Firing now' label when currently firing, got {gb.label!r}"
        )

    def test_no_fire_today_falls_back_to_armed_or_blocked(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        for p in result.patterns:
            assert p.fired_today is False
            assert p.last_fire_ts is None
            assert p.status in ("armed", "blocked"), (
                f"{p.id}: unexpected status {p.status!r}"
            )

    def test_multi_pattern_same_fire_increments_both(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """Mirrors the live 17:45 fire: one v9_trades row carries BOTH
        GB100 and HTLB under active_patterns. Both patterns must surface
        as fired today.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        _insert_woodies_fire(
            db_path,
            engine_pattern_ids=["GB100", "HTLB"],
            direction="LONG",
            minutes_ago=20,
        )
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        gb = next(p for p in result.patterns if p.id == "GB100")
        htlb = next(p for p in result.patterns if p.id == "HTLB")
        assert gb.fired_today is True
        assert htlb.fired_today is True
        assert gb.last_fire_ts == htlb.last_fire_ts

    def test_system_aggregate_matches_pattern_roll_up(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """`system.fired_today_count` = sum of per-pattern counts.
        `system.last_fire_ts` = max of per-pattern last_fire_ts.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        _insert_woodies_fire(db_path, engine_pattern_ids=["HTLB"], direction="SHORT", minutes_ago=240)
        _insert_woodies_fire(db_path, engine_pattern_ids=["GB100", "HTLB"], direction="LONG", minutes_ago=10)
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        # HTLB fired twice (240m ago + 10m ago); GB100 once → sum = 3.
        assert result.fired_today_count == 3, (
            f"expected 3 fires summed across patterns, got {result.fired_today_count}"
        )
        # last_fire_ts must equal the max of any per-pattern last_fire_ts.
        per_pattern_ts = [p.last_fire_ts for p in result.patterns if p.last_fire_ts]
        assert result.last_fire_ts == max(per_pattern_ts)

    def test_lifecycle_event_row_does_not_register_as_fire(
        self, real_woodies_system, tmp_path, monkeypatch
    ):
        """A `[{"event":"stop_move",...}]` cross_context append (the
        production row 156 layout) must NOT register as a fire — those
        are post-fire audit appends, not new fires.
        """
        db_path = str(tmp_path / "test.db")
        _create_minimal_woodies_db(db_path)
        _insert_fresh_woodies_bar(db_path)
        ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO v9_trades (firing_system, direction, entry_ts, cross_context) "
            "VALUES (?,?,?,?)",
            (4, "LONG", ts, json.dumps([
                {"event": "stop_move", "from": 7577.75, "to": 7579.25,
                 "reason": "BE+1T after T1 hit"},
            ])),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(woodies_inspector, "DB_PATH", db_path)

        result = woodies_inspector.inspect(woodies_system=real_woodies_system)

        assert result.fired_today_count == 0
        for p in result.patterns:
            assert p.fired_today is False, (
                f"{p.id} mis-credited a stop_move audit row as a fire"
            )
