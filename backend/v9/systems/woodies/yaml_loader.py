"""Woodies Decision Tree YAML config loader (PROMPT 2 · 2.1).

Loads woodies_config.yaml and returns typed stage specs for the
entry and active phase engines.

Source: Decision Tree V1 § Section 2 Configuration Block.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

# ── Valid enums per Decision Tree V1 ──────────────────────────────

VALID_STAGE_TYPES = {"woodies_core", "touch_point"}

# Ordered by hierarchy: highest priority first (per Decision Tree V1 § Core Principles)
PRIORITY_HIERARCHY = [
    "ABSOLUTE_EXIT",
    "STRATEGIC_EXIT",
    "ADVISORY_EXIT",
    "TIME_EXIT",
    "TARGET",
    "TIGHTEN",
    "PARTIAL",
    "TRAIL",
    "NO_ACTION",
]

VALID_PRIORITY_CLASSES = set(PRIORITY_HIERARCHY)

EXPECTED_ENTRY_IDS = {
    "A1_strategic_gate",
    "A2_day_type_query",
    "A3_pattern_detection",
    "A4_poc_suffering_query",
    "A5_otf_clarity_query",
    "A6_entry_classification",
    "A7_universal_checks",
}

EXPECTED_ACTIVE_IDS = {
    "B1_stop_check",
    "B2_eod_check",
    "B3_color_flip",
    "B4_poc_migration_query",
    "B5_otf_mid_trade_query",
    "B6_news_window",
    "B7_time_stop",
    "B8_counter_pattern",
    "B9_market_state_query",
    "B10_t1_milestone",
    "B11_t2_milestone",
    "B12_t3_milestone",
    "B13_trail_check",
    "B14_hold",
}

ALL_EXPECTED_IDS = EXPECTED_ENTRY_IDS | EXPECTED_ACTIVE_IDS


class ConfigError(Exception):
    """Raised when woodies_config.yaml is invalid."""


@dataclass
class StageSpec:
    """Typed representation of a single stage from YAML config."""
    id: str
    type: str
    enabled: bool
    reorder_priority: Optional[int] = None
    priority_class: Optional[str] = None
    target_system: Optional[str] = None
    query: Optional[Union[str, list]] = None
    blocking: Optional[bool] = None
    always_last: bool = False


@dataclass
class WoodiesConfig:
    """Full parsed config with entry + active phase stage lists."""
    entry_phase: List[StageSpec] = field(default_factory=list)
    active_phase: List[StageSpec] = field(default_factory=list)

    @property
    def all_stages(self) -> List[StageSpec]:
        return self.entry_phase + self.active_phase


# ── Default config path ──────────────────────────────────────────

_DEFAULT_CONFIG = Path(__file__).parent / "config" / "woodies_config.yaml"


def load(config_path: Optional[Path] = None) -> WoodiesConfig:
    """Load woodies_config.yaml, validate, return typed config.

    Raises ConfigError on any schema violation.
    """
    path = config_path or _DEFAULT_CONFIG
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if not raw or "woodies_tree_v1" not in raw:
        raise ConfigError("Missing top-level 'woodies_tree_v1' key")

    tree = raw["woodies_tree_v1"]
    entry_raw = tree.get("entry_phase", [])
    active_raw = tree.get("active_phase", [])

    entry_specs = [_parse_stage(s, phase="entry") for s in entry_raw]
    active_specs = [_parse_stage(s, phase="active") for s in active_raw]

    config = WoodiesConfig(entry_phase=entry_specs, active_phase=active_specs)
    _validate_completeness(config)
    return config


def get_entry_stages(config: WoodiesConfig) -> List[StageSpec]:
    """Return enabled entry stages sorted by reorder_priority."""
    enabled = [s for s in config.entry_phase if s.enabled]
    return sorted(enabled, key=lambda s: s.reorder_priority or 0)


def get_active_stages(config: WoodiesConfig) -> List[StageSpec]:
    """Return enabled active stages sorted by priority_class rank, then YAML order."""
    priority_rank = {cls: i for i, cls in enumerate(PRIORITY_HIERARCHY)}
    enabled = [s for s in config.active_phase if s.enabled]
    return sorted(
        enabled,
        key=lambda s: (priority_rank.get(s.priority_class or "NO_ACTION", 99), 0),
    )


# ── Internal helpers ─────────────────────────────────────────────

def _parse_stage(raw: dict, phase: str) -> StageSpec:
    """Parse a single stage dict into StageSpec with validation."""
    stage_id = raw.get("id")
    if not stage_id:
        raise ConfigError(f"Stage missing 'id' field: {raw}")

    stage_type = raw.get("type")
    if stage_type not in VALID_STAGE_TYPES:
        raise ConfigError(
            f"Stage {stage_id}: invalid type '{stage_type}'. "
            f"Must be one of {VALID_STAGE_TYPES}"
        )

    # Touch-point validation per Decision Tree V1
    if stage_type == "touch_point":
        if "target_system" not in raw:
            raise ConfigError(
                f"Stage {stage_id}: touch_point must have 'target_system'"
            )
        if "query" not in raw:
            raise ConfigError(
                f"Stage {stage_id}: touch_point must have 'query'"
            )
        if raw.get("blocking", False) is True:
            raise ConfigError(
                f"Stage {stage_id}: touch_point blocking must be false "
                f"(advisory only per Decision Tree V1 § Core Principles)"
            )

    # Active phase must have priority_class
    if phase == "active":
        pc = raw.get("priority_class")
        if pc and pc not in VALID_PRIORITY_CLASSES:
            raise ConfigError(
                f"Stage {stage_id}: invalid priority_class '{pc}'. "
                f"Must be one of {VALID_PRIORITY_CLASSES}"
            )

    return StageSpec(
        id=stage_id,
        type=stage_type,
        enabled=raw.get("enabled", True),
        reorder_priority=raw.get("reorder_priority"),
        priority_class=raw.get("priority_class"),
        target_system=raw.get("target_system"),
        query=raw.get("query"),
        blocking=raw.get("blocking"),
        always_last=raw.get("always_last", False),
    )


def _validate_completeness(config: WoodiesConfig) -> None:
    """Ensure all 21 expected stage IDs are present."""
    found_ids = {s.id for s in config.all_stages}
    missing = ALL_EXPECTED_IDS - found_ids
    if missing:
        raise ConfigError(
            f"Missing required stages: {sorted(missing)}. "
            f"All 21 stages must be present in config."
        )
    logger.info(
        "[Woodies] Config loaded: %d entry + %d active stages",
        len(config.entry_phase),
        len(config.active_phase),
    )
