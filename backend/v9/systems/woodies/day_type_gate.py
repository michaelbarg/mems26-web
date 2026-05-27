"""Day-Type Matrix Gate — 63-cell advisory lookup (W-3).

Maps (PatternId, DayType) → MatrixVerdict with verdict/entry_hint/t1_ref.
ADVISORY ONLY — never raises, never vetoes. Degraded mode (UNAVAILABLE)
returns ⚠️ with is_degraded=True for all patterns.

Source of truth: config/day_type_matrix.yaml (generated from
docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple, Union

import yaml

from backend.v9.systems.woodies.schemas import PatternId  # W-6: canonical home

logger = logging.getLogger(__name__)

# Canonical YAML path relative to this module
_DEFAULT_YAML = Path(__file__).parent / "config" / "day_type_matrix.yaml"


class DayType(str, Enum):
    """Dalton Mind Over Markets day-type taxonomy + UNAVAILABLE sentinel."""
    TN = "TN"
    TDD = "TDD"
    NV = "NV"
    NeuE = "NeuE"
    NeuC = "NeuC"
    Norm = "Norm"
    NT = "NT"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class MatrixVerdict:
    """Single cell from the 63-cell day-type matrix."""
    verdict: Literal["✅", "⚠️", "❌"]
    entry_hint: str
    t1_ref: str
    pattern_id: PatternId
    day_type: DayType
    is_degraded: bool = False


class DayTypeGate:
    """Advisory-only day-type matrix gate.

    Loads the 63-cell matrix from YAML and provides O(1) lookup.
    UNAVAILABLE day type returns ⚠️ + is_degraded=True for every pattern.
    Never raises on lookup, never vetoes entry.
    """

    def __init__(self, matrix_yaml_path: Optional[Union[str, Path]] = None) -> None:
        path = Path(matrix_yaml_path) if matrix_yaml_path else _DEFAULT_YAML
        if not path.exists():
            raise FileNotFoundError(f"Day-type matrix YAML not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._matrix: Dict[Tuple[PatternId, DayType], MatrixVerdict] = {}
        for pattern_str, day_types in raw["patterns"].items():
            pid = PatternId(pattern_str)
            for dt_str, cell in day_types.items():
                dt = DayType(dt_str)
                self._matrix[(pid, dt)] = MatrixVerdict(
                    verdict=cell["verdict"],
                    entry_hint=cell["entry_hint"],
                    t1_ref=cell["t1_ref"],
                    pattern_id=pid,
                    day_type=dt,
                )

        logger.debug("[DayTypeGate] Loaded %d cells from %s", len(self._matrix), path)

    def get_verdict(self, pattern_id: PatternId, day_type: DayType) -> MatrixVerdict:
        """Look up matrix verdict. UNAVAILABLE → degraded ⚠️. Never raises."""
        if day_type == DayType.UNAVAILABLE:
            return MatrixVerdict(
                verdict="⚠️",
                entry_hint="Day type unavailable — degraded mode, proceed with caution",
                t1_ref="—",
                pattern_id=pattern_id,
                day_type=DayType.UNAVAILABLE,
                is_degraded=True,
            )
        return self._matrix[(pattern_id, day_type)]
