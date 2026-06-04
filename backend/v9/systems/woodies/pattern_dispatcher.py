"""Two-tier R_t1 Pattern Dispatcher (W-8).

Replaces the naive max(confidence) pattern selection with a two-tier
algorithm that uses R_t1 (reward-to-risk ratio at T1) as the primary
ranking metric, with trend-state-aware family preference.

Family hierarchy:
  BLUE/RED → prefer CONT family (ZLR, TLB, TT, GB100)
  GRAY     → best R_t1 across all families
  YELLOW   → ValueError (P-W5 blocks before dispatch)

Tie-break: raw_confidence (higher wins).
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging

import yaml

from backend.v9.systems.woodies.schemas import PatternResult, PatternId
from backend.v9.systems.woodies.stages.a1_strategic_gate import TrendState

logger = logging.getLogger("woodies.pattern_dispatcher")


class Family(str, Enum):
    CONT = "CONT"  # ZLR, TLB, TT, GB100
    REV = "REV"    # VEGAS, GHOST, FAMIR, HFE, HTLB (REV-ish grouped with REV)


FAMILY_MAP = {
    PatternId.ZLR: Family.CONT,
    PatternId.TLB: Family.CONT,
    PatternId.TT: Family.CONT,
    PatternId.GB100: Family.CONT,
    PatternId.VEGAS: Family.REV,
    PatternId.GHOST: Family.REV,
    PatternId.FAMIR: Family.REV,
    PatternId.HFE: Family.REV,
    PatternId.HTLB: Family.REV,  # REV-ish per D-092
}

DEFAULT_CONFIG = {
    "min_r_t1_threshold": 0.0,
    "tie_breaker": "raw_confidence",
    "gray_fallback_enabled": True,
    "yellow_assertion": True,
    "r_t1_missing_fallback": True,
    "log_dispatch_decisions": False,
}

# YAML override for min_r_t1_threshold (from config/stop_params.yaml)
try:
    from backend.v9.config_loader import load_stop_params as _load_sp
    _sp = _load_sp()
    if _sp is not None and "min_r_t1_threshold" in _sp:
        DEFAULT_CONFIG["min_r_t1_threshold"] = float(_sp["min_r_t1_threshold"])
        logging.getLogger(__name__).info(
            "[pattern_dispatcher] min_r_t1_threshold from YAML: %.2f",
            DEFAULT_CONFIG["min_r_t1_threshold"],
        )
except Exception:
    pass  # fallback to hardcoded 0.0

_DEFAULT_YAML = Path(__file__).parent / "config" / "dispatcher_config.yaml"


@dataclass(frozen=True)
class DispatchResult:
    """Result of pattern dispatch — which pattern won and why."""
    winner: Optional[PatternResult]
    winning_family: Optional[Family]
    selection_path: str
    # Possible paths:
    #   "within_family_max_r_t1"         — CONT family had candidates in BLUE/RED
    #   "cross_family_trend_preferred"   — no CONT in BLUE/RED, fell back across all
    #   "gray_fallback_max_r_t1"         — GRAY: best R_t1 across all families
    #   "single_pattern"                 — only one detected pattern
    #   "no_patterns"                    — zero detected patterns
    #   "r_t1_missing_fallback"          — R_t1 missing, used confidence fallback
    rejected_candidates: list
    config_source: str  # "python_default" or "yaml_override"
    metadata: dict


def _load_yaml_config(path: Path) -> dict:
    """Load dispatcher YAML config with fallback to defaults."""
    if not path.exists():
        logger.warning(
            "[PatternDispatcher] YAML config not found at %s — using Python defaults", path
        )
        return {}
    try:
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            logger.warning(
                "[PatternDispatcher] YAML config invalid (not a dict) — using Python defaults"
            )
            return {}
        return raw.get("pattern_dispatcher", raw)
    except Exception as e:
        logger.warning(
            "[PatternDispatcher] YAML config load error: %s — using Python defaults", e
        )
        return {}


def _get_family(pattern: PatternResult) -> Optional[Family]:
    """Map a PatternResult to its Family via PatternId enum."""
    try:
        pid = PatternId(pattern.pattern_id)
        return FAMILY_MAP.get(pid)
    except ValueError:
        logger.warning("[PatternDispatcher] Unknown pattern_id: %s", pattern.pattern_id)
        return None


def _sort_key(p: PatternResult):
    """Sort key: higher r_t1 first, then higher confidence as tie-break."""
    return (p.r_t1 or 0.0, p.confidence)


class PatternDispatcher:
    """Two-tier R_t1 pattern dispatcher.

    Replaces the naive max(confidence) selection with trend-aware,
    R_t1-ranked pattern selection.
    """

    def __init__(self, config_yaml_path: Optional[str] = None):
        yaml_path = Path(config_yaml_path) if config_yaml_path else _DEFAULT_YAML
        yaml_overrides = _load_yaml_config(yaml_path)
        self.config = {**DEFAULT_CONFIG, **yaml_overrides}
        self.config_source = "yaml_override" if yaml_overrides else "python_default"
        if yaml_overrides:
            logger.info("[PatternDispatcher] Config loaded from YAML: %s", yaml_path)
        else:
            logger.debug("[PatternDispatcher] Using Python default config")

    def select_winner(
        self, patterns: List[PatternResult], trend_state: TrendState
    ) -> DispatchResult:
        """Select the best pattern using two-tier R_t1 algorithm.

        Algorithm:
        1. Filter to detected patterns only.
        2. 0 detected → no_patterns (winner=None).
        3. 1 detected → single_pattern.
        4. YELLOW → raise ValueError (P-W5 should block before dispatch).
        5. If any r_t1 is None → fallback to max(confidence) with WARNING.
        6. Group by family (CONT / REV).
        7. BLUE/RED → prefer CONT family, select max(r_t1) within CONT.
           If no CONT candidates, fallback to max(r_t1) across all.
        8. GRAY → max(r_t1) across all families.
        9. Tie-break by raw_confidence.
        """
        detected = [p for p in patterns if p.detected]

        # Case: no patterns
        if not detected:
            return DispatchResult(
                winner=None,
                winning_family=None,
                selection_path="no_patterns",
                rejected_candidates=[],
                config_source=self.config_source,
                metadata={"trend_state": trend_state.value},
            )

        # Case: single pattern
        if len(detected) == 1:
            winner = detected[0]
            return DispatchResult(
                winner=winner,
                winning_family=_get_family(winner),
                selection_path="single_pattern",
                rejected_candidates=[],
                config_source=self.config_source,
                metadata={"trend_state": trend_state.value},
            )

        # YELLOW assertion — should never reach dispatcher
        if trend_state == TrendState.YELLOW:
            if self.config.get("yellow_assertion", True):
                raise ValueError(
                    "YELLOW trend state reached pattern dispatcher — "
                    "P-W5 strategic gate should block before dispatch"
                )

        # Check for missing r_t1 values
        if any(p.r_t1 is None for p in detected):
            if self.config.get("r_t1_missing_fallback", True):
                logger.warning(
                    "[PatternDispatcher] r_t1 missing on %d/%d patterns — "
                    "falling back to max(confidence)",
                    sum(1 for p in detected if p.r_t1 is None),
                    len(detected),
                )
                winner = max(detected, key=lambda p: p.confidence)
                rejected = [p for p in detected if p is not winner]
                return DispatchResult(
                    winner=winner,
                    winning_family=_get_family(winner),
                    selection_path="r_t1_missing_fallback",
                    rejected_candidates=rejected,
                    config_source=self.config_source,
                    metadata={
                        "trend_state": trend_state.value,
                        "fallback_reason": "r_t1_none",
                    },
                )

        # Group by family
        cont_patterns = [p for p in detected if _get_family(p) == Family.CONT]
        rev_patterns = [p for p in detected if _get_family(p) == Family.REV]

        # GRAY: max r_t1 across all families
        if trend_state == TrendState.GRAY:
            winner = max(detected, key=_sort_key)
            rejected = [p for p in detected if p is not winner]
            return DispatchResult(
                winner=winner,
                winning_family=_get_family(winner),
                selection_path="gray_fallback_max_r_t1",
                rejected_candidates=rejected,
                config_source=self.config_source,
                metadata={
                    "trend_state": trend_state.value,
                    "cont_count": len(cont_patterns),
                    "rev_count": len(rev_patterns),
                },
            )

        # BLUE/RED: prefer CONT family
        if cont_patterns:
            winner = max(cont_patterns, key=_sort_key)
            rejected = [p for p in detected if p is not winner]
            selection_path = "within_family_max_r_t1"
        else:
            # No CONT candidates — fall back to max r_t1 across all
            winner = max(detected, key=_sort_key)
            rejected = [p for p in detected if p is not winner]
            selection_path = "cross_family_trend_preferred"

        if self.config.get("log_dispatch_decisions", False):
            logger.info(
                "[PatternDispatcher] %s: winner=%s r_t1=%.2f family=%s path=%s "
                "(cont=%d rev=%d)",
                trend_state.value,
                winner.pattern_id,
                winner.r_t1 or 0.0,
                _get_family(winner),
                selection_path,
                len(cont_patterns),
                len(rev_patterns),
            )

        return DispatchResult(
            winner=winner,
            winning_family=_get_family(winner),
            selection_path=selection_path,
            rejected_candidates=rejected,
            config_source=self.config_source,
            metadata={
                "trend_state": trend_state.value,
                "cont_count": len(cont_patterns),
                "rev_count": len(rev_patterns),
            },
        )
