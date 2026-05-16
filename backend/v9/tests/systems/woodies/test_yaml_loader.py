"""Tests for Woodies YAML config loader (PROMPT 2 · 2.1).

Acceptance criteria per PROMPT 2 § COMMIT 2.1:
- Load default config · 21 stages returned
- Disable A2 in YAML · loader skips it
- Reorder A6 before A3 · loader respects new order
- Invalid YAML (missing stage) → raises ConfigError
- blocking=true on touch_point → raises ConfigError
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import copy
import textwrap
from pathlib import Path

import pytest
import yaml

from backend.v9.systems.woodies.yaml_loader import (
    ConfigError,
    StageSpec,
    WoodiesConfig,
    get_active_stages,
    get_entry_stages,
    load,
    EXPECTED_ENTRY_IDS,
    EXPECTED_ACTIVE_IDS,
    ALL_EXPECTED_IDS,
    VALID_PRIORITY_CLASSES,
)


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def default_config():
    """Load the real default config."""
    return load()


@pytest.fixture
def config_dir(tmp_path):
    """Provide a temp dir for custom YAML configs."""
    return tmp_path


def _write_yaml(path: Path, data: dict) -> Path:
    """Helper: write YAML to a file and return path."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


# ── Test: Load default config · 21 stages ────────────────────────

class TestLoadDefault:
    def test_loads_21_stages(self, default_config):
        total = len(default_config.all_stages)
        assert total == 21, f"Expected 21 stages, got {total}"

    def test_7_entry_stages(self, default_config):
        assert len(default_config.entry_phase) == 7

    def test_14_active_stages(self, default_config):
        assert len(default_config.active_phase) == 14

    def test_all_expected_ids_present(self, default_config):
        found = {s.id for s in default_config.all_stages}
        assert found == ALL_EXPECTED_IDS

    def test_entry_ids_correct(self, default_config):
        found = {s.id for s in default_config.entry_phase}
        assert found == EXPECTED_ENTRY_IDS

    def test_active_ids_correct(self, default_config):
        found = {s.id for s in default_config.active_phase}
        assert found == EXPECTED_ACTIVE_IDS

    def test_all_stages_enabled_by_default(self, default_config):
        for s in default_config.all_stages:
            assert s.enabled is True, f"Stage {s.id} not enabled"


# ── Test: Disable A2 · loader skips it ───────────────────────────

class TestDisableStage:
    def test_disable_a2_skips_in_entry_stages(self, default_config):
        # Mutate config to disable A2
        for s in default_config.entry_phase:
            if s.id == "A2_day_type_query":
                s.enabled = False

        enabled = get_entry_stages(default_config)
        ids = [s.id for s in enabled]
        assert "A2_day_type_query" not in ids
        assert len(ids) == 6


# ── Test: Reorder A6 before A3 · loader respects ─────────────────

class TestReorder:
    def test_reorder_a6_before_a3(self, default_config):
        # Swap priorities: A6 gets priority 2.5 (before A3=3)
        for s in default_config.entry_phase:
            if s.id == "A6_entry_classification":
                s.reorder_priority = 2  # move before A3 (priority 3)
            if s.id == "A2_day_type_query":
                s.reorder_priority = 3  # push A2 after A6

        ordered = get_entry_stages(default_config)
        ids = [s.id for s in ordered]
        a6_idx = ids.index("A6_entry_classification")
        a3_idx = ids.index("A3_pattern_detection")
        assert a6_idx < a3_idx, f"A6 at {a6_idx} should be before A3 at {a3_idx}"


# ── Test: Missing stage → ConfigError ────────────────────────────

class TestMissingStage:
    def test_missing_stage_raises_config_error(self, config_dir):
        # Build config with A1 removed
        incomplete = {
            "woodies_tree_v1": {
                "entry_phase": [
                    # A1 missing!
                    {"id": "A2_day_type_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 2,
                     "target_system": "multi_system", "query": "day_type",
                     "blocking": False},
                    {"id": "A3_pattern_detection", "type": "woodies_core",
                     "enabled": True, "reorder_priority": 3},
                    {"id": "A4_poc_suffering_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 4,
                     "target_system": "multi_system",
                     "query": ["poc_location", "suffering_side"],
                     "blocking": False},
                    {"id": "A5_otf_clarity_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 5,
                     "target_system": "multi_system",
                     "query": "otf_clarity_state", "blocking": False},
                    {"id": "A6_entry_classification", "type": "woodies_core",
                     "enabled": True, "reorder_priority": 6},
                    {"id": "A7_universal_checks", "type": "woodies_core",
                     "enabled": True, "reorder_priority": 7},
                ],
                "active_phase": [
                    {"id": "B1_stop_check", "type": "woodies_core",
                     "enabled": True, "priority_class": "ABSOLUTE_EXIT"},
                    {"id": "B2_eod_check", "type": "woodies_core",
                     "enabled": True, "priority_class": "ABSOLUTE_EXIT"},
                    {"id": "B3_color_flip", "type": "woodies_core",
                     "enabled": True, "priority_class": "STRATEGIC_EXIT"},
                    {"id": "B4_poc_migration_query", "type": "touch_point",
                     "enabled": True, "target_system": "multi_system",
                     "query": "poc_migration", "blocking": False,
                     "priority_class": "ADVISORY_EXIT"},
                    {"id": "B5_otf_mid_trade_query", "type": "touch_point",
                     "enabled": True, "target_system": "multi_system",
                     "query": "otf_clarity_state", "blocking": False,
                     "priority_class": "ADVISORY_EXIT"},
                    {"id": "B6_news_window", "type": "woodies_core",
                     "enabled": True, "priority_class": "ABSOLUTE_EXIT"},
                    {"id": "B7_time_stop", "type": "woodies_core",
                     "enabled": True, "priority_class": "TIME_EXIT"},
                    {"id": "B8_counter_pattern", "type": "woodies_core",
                     "enabled": True, "priority_class": "TIGHTEN"},
                    {"id": "B9_market_state_query", "type": "touch_point",
                     "enabled": True, "target_system": "multi_system",
                     "query": "market_state", "blocking": False,
                     "priority_class": "PARTIAL"},
                    {"id": "B10_t1_milestone", "type": "woodies_core",
                     "enabled": True, "priority_class": "TARGET"},
                    {"id": "B11_t2_milestone", "type": "woodies_core",
                     "enabled": True, "priority_class": "TARGET"},
                    {"id": "B12_t3_milestone", "type": "woodies_core",
                     "enabled": True, "priority_class": "TARGET"},
                    {"id": "B13_trail_check", "type": "woodies_core",
                     "enabled": True, "priority_class": "TRAIL"},
                    {"id": "B14_hold", "type": "woodies_core",
                     "enabled": True, "priority_class": "NO_ACTION"},
                ],
            }
        }
        path = _write_yaml(config_dir / "bad.yaml", incomplete)
        with pytest.raises(ConfigError, match="Missing required stages"):
            load(path)


# ── Test: blocking=true on touch_point → ConfigError ─────────────

class TestBlockingViolation:
    def test_blocking_true_raises_config_error(self, config_dir):
        bad_stage = {
            "woodies_tree_v1": {
                "entry_phase": [
                    {"id": "A1_strategic_gate", "type": "woodies_core",
                     "enabled": True, "reorder_priority": 1},
                    {"id": "A2_day_type_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 2,
                     "target_system": "multi_system", "query": "day_type",
                     "blocking": True},  # VIOLATION
                ],
                "active_phase": [],
            }
        }
        path = _write_yaml(config_dir / "blocking.yaml", bad_stage)
        with pytest.raises(ConfigError, match="blocking must be false"):
            load(path)


# ── Test: Touch-point missing target_system → ConfigError ────────

class TestTouchPointValidation:
    def test_missing_target_system_raises(self, config_dir):
        bad = {
            "woodies_tree_v1": {
                "entry_phase": [
                    {"id": "A2_day_type_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 2,
                     "query": "day_type", "blocking": False},
                ],
                "active_phase": [],
            }
        }
        path = _write_yaml(config_dir / "no_target.yaml", bad)
        with pytest.raises(ConfigError, match="target_system"):
            load(path)

    def test_missing_query_raises(self, config_dir):
        bad = {
            "woodies_tree_v1": {
                "entry_phase": [
                    {"id": "A2_day_type_query", "type": "touch_point",
                     "enabled": True, "reorder_priority": 2,
                     "target_system": "multi_system", "blocking": False},
                ],
                "active_phase": [],
            }
        }
        path = _write_yaml(config_dir / "no_query.yaml", bad)
        with pytest.raises(ConfigError, match="query"):
            load(path)


# ── Test: Invalid priority_class → ConfigError ───────────────────

class TestInvalidPriorityClass:
    def test_bad_priority_class_raises(self, config_dir):
        bad = {
            "woodies_tree_v1": {
                "entry_phase": [],
                "active_phase": [
                    {"id": "B1_stop_check", "type": "woodies_core",
                     "enabled": True, "priority_class": "INVALID_CLASS"},
                ],
            }
        }
        path = _write_yaml(config_dir / "bad_priority.yaml", bad)
        with pytest.raises(ConfigError, match="invalid priority_class"):
            load(path)


# ── Test: Active stages sorted by priority hierarchy ─────────────

class TestActivePrioritySorting:
    def test_absolute_exit_before_target(self, default_config):
        ordered = get_active_stages(default_config)
        ids = [s.id for s in ordered]
        b1_idx = ids.index("B1_stop_check")      # ABSOLUTE_EXIT
        b10_idx = ids.index("B10_t1_milestone")   # TARGET
        assert b1_idx < b10_idx

    def test_trail_before_no_action(self, default_config):
        ordered = get_active_stages(default_config)
        ids = [s.id for s in ordered]
        b13_idx = ids.index("B13_trail_check")  # TRAIL
        b14_idx = ids.index("B14_hold")         # NO_ACTION
        assert b13_idx < b14_idx

    def test_strategic_exit_after_absolute(self, default_config):
        ordered = get_active_stages(default_config)
        ids = [s.id for s in ordered]
        # All ABSOLUTE_EXIT stages before STRATEGIC_EXIT
        abs_stages = [i for i, s in enumerate(ordered)
                      if s.priority_class == "ABSOLUTE_EXIT"]
        strat_stages = [i for i, s in enumerate(ordered)
                        if s.priority_class == "STRATEGIC_EXIT"]
        if abs_stages and strat_stages:
            assert max(abs_stages) < min(strat_stages)


# ── Test: Config file not found ──────────────────────────────────

class TestFileNotFound:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load(tmp_path / "nonexistent.yaml")


# ── Test: StageSpec dataclass ────────────────────────────────────

class TestStageSpec:
    def test_stage_spec_fields(self):
        spec = StageSpec(id="A1_strategic_gate", type="woodies_core", enabled=True)
        assert spec.id == "A1_strategic_gate"
        assert spec.type == "woodies_core"
        assert spec.enabled is True
        assert spec.blocking is None
        assert spec.always_last is False
