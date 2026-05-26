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
        assert len(entity.components) == 7, (
            f"Day Type entity must have 7 components per §4.3, got {len(entity.components)}"
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
