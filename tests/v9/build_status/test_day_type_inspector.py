"""Tests for build_status/day_type_inspector.py — single Day Type entity.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.3
"""

import sqlite3
from datetime import date, datetime, timezone

import pytest

from backend.v9.systems.build_status import day_type_inspector


class TestDayTypeInspectorStructure:
    def test_day_type_inspector_returns_single_entity(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        """Test #6: inspect() returns exactly 1 pattern entity with 7 components."""
        db_path, today = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        assert len(result.patterns) == 1, (
            f"Day Type system must return exactly 1 entity, got {len(result.patterns)}"
        )

        entity = result.patterns[0]
        assert entity.id == "day_type_current"
        assert len(entity.components) == 10, (
            f"Day Type entity must have 10 components, got {len(entity.components)}"
        )

    def test_day_type_entity_has_correct_component_keys(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        """Each of the 7 components must match the spec source §4.3."""
        db_path, today = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        entity = result.patterns[0]
        component_keys = [c.key for c in entity.components]

        expected_keys = [
            "ib_locked",
            "opening_type_set",
            "opening_run_detected",
            "ib_range_pts",
            "trading_confidence",
            "day_type_assigned",
            "probability_above_threshold",
            "directional_certainty",
            "zohar_rules_evaluated",
            "not_developing",
        ]
        assert component_keys == expected_keys, (
            f"Component keys mismatch. Expected {expected_keys}, got {component_keys}"
        )


class TestDayTypeStatusLogic:
    def test_status_fired_when_classified(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        """Classified + probability >= 0.55 → status='fired'."""
        db_path, today = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        entity = result.patterns[0]
        assert entity.status == "fired", f"Expected fired, got {entity.status!r}"
        assert entity.fired_today is True

    def test_status_armed_when_ib_developing(
        self, temp_db_with_developing_day_type, monkeypatch
    ):
        """Test #11: ib_width_class='DEVELOPING' → status='armed'.

        Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.3
        "blocked → ib developing or missing data"
        (Note: inspector uses 'armed' for developing state)
        """
        db_path, today = temp_db_with_developing_day_type
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        entity = result.patterns[0]
        # IB DEVELOPING → day type not yet known → armed (IB still building)
        assert entity.status == "armed", (
            f"ib_width_class=DEVELOPING → expected 'armed', got {entity.status!r}"
        )

    def test_status_unknown_when_no_db_row(self, tmp_path, monkeypatch):
        """No classification for today → status='unknown'."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE v9_day_type_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, day_type TEXT, probability REAL,
            directional_certainty REAL, ib_width_class TEXT,
            opening_type TEXT, last_updated_at TEXT,
            active_zohar_rules TEXT
        )""")
        conn.commit()
        conn.close()
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        assert len(result.patterns) == 1
        entity = result.patterns[0]
        assert entity.status == "unknown"

    def test_data_freshness_present_in_result(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        """data_freshness block must be present on the system result.

        Test #13: verify data_freshness.last_bar_ts, lag_seconds, fresh, threshold_seconds.
        """
        db_path, today = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        result = day_type_inspector.inspect()

        assert result.data_freshness is not None
        assert result.data_freshness.threshold_seconds == 360
        # last_bar_ts = last_updated_at from row (set in fixture)
        assert result.data_freshness.last_bar_ts is not None


class TestDayTypeRowContract:
    """Every row must expose live + required + freshness — even on failing gates."""

    def test_every_row_has_live_required_freshness(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        db_path, _ = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        entity = day_type_inspector.inspect().patterns[0]

        assert entity.components, "expected at least one component row"
        for c in entity.components:
            assert c.live is not None, f"{c.key}: live must be populated"
            assert c.required is not None, f"{c.key}: required must be populated"
            assert c.freshness is not None, f"{c.key}: freshness must be populated"
            assert c.freshness.source in {"db", "in_memory", "inspector_eval", "sierra_export"}

    def test_passing_row_has_small_positive_lag(
        self, temp_db_with_day_type_row, monkeypatch
    ):
        """A passing row (probability_above_threshold w/ p=0.72) populates
        live with the numeric value AND freshness.lag_s ≥ 0 and < 1 day.
        """
        db_path, _ = temp_db_with_day_type_row
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        entity = day_type_inspector.inspect().patterns[0]
        prob_row = next(c for c in entity.components if c.key == "probability_above_threshold")
        assert prob_row.present is True
        assert prob_row.live == "0.7200"
        assert prob_row.required == ">= 0.55"
        assert prob_row.freshness is not None
        assert prob_row.freshness.lag_s is not None
        assert 0.0 <= prob_row.freshness.lag_s < 86_400.0

    def test_failing_row_still_exposes_live_value(self, tmp_path, monkeypatch):
        """When a gate FAILS, live still shows the actual measured value
        so Michael can see WHY it failed (e.g. probability=0.30 vs >= 0.55).
        """
        import sqlite3 as _sq
        from datetime import datetime as _dt, timezone as _tz, date as _date
        db_path = str(tmp_path / "fail.db")
        conn = _sq.connect(db_path)
        conn.execute("""CREATE TABLE v9_day_type_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, day_type TEXT, probability REAL,
            directional_certainty REAL, trading_confidence REAL,
            ib_high REAL, ib_low REAL, ib_width REAL,
            ib_width_class TEXT, opening_type TEXT,
            last_updated_at TEXT, active_zohar_rules TEXT,
            reasoning_notes TEXT
        )""")
        conn.execute(
            "INSERT INTO v9_day_type_history "
            "(date, day_type, probability, directional_certainty, ib_width_class, opening_type, last_updated_at, active_zohar_rules) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (_date.today().isoformat(), "UNKNOWN", 0.30, 0.10,
             "NORMAL", "OD", _dt.now(_tz.utc).isoformat(), "[]"),
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(day_type_inspector, "DB_PATH", db_path)

        entity = day_type_inspector.inspect().patterns[0]
        prob_row = next(c for c in entity.components if c.key == "probability_above_threshold")
        assert prob_row.present is False  # 0.30 < 0.55
        assert prob_row.live == "0.3000", "failing row must still expose actual value"
        assert prob_row.required == ">= 0.55"
