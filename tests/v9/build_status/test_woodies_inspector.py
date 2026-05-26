"""Tests for build_status/woodies_inspector.py — 9 Woodies pattern status objects.

Uses real WoodiesSystem instances per anti-mock constraint.
"""

import sqlite3

import pytest

from backend.v9.systems.build_status import woodies_inspector
from backend.v9.systems.build_status.auth_table_lookup import WOODIES_PATTERN_IDS
from backend.v9.systems.woodies.woodies_system import WoodiesSystem


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
        """Pattern detected + ready_to_route=True → status='fired'."""
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
        assert zlr_pattern.fired_today is True

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


# ── helpers ─────────────────────────────────────────────────────────────────

def _create_minimal_woodies_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS v9_bars_5min_woodies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER
    )""")
    conn.commit()
    conn.close()
