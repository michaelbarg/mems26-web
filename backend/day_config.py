"""Day-Adaptive Configuration Module — MEMS26 Phase 5"""

from typing import Dict, Optional

QUALITY_WEIGHTS = {
    "TREND_DAY": {"vegas": 40, "tpo": 20, "fvg": 25, "footprint": 15},
    "RANGE_DAY": {"vegas": 20, "tpo": 35, "fvg": 25, "footprint": 20},
    "GAP_FILL":  {"vegas": 25, "tpo": 30, "fvg": 25, "footprint": 20},
    "NORMAL":    {"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20},
    "DEVELOPING":{"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20},
}

SIZE_THRESHOLDS = {
    "TREND_DAY": {"full": 60, "half": 45},
    "RANGE_DAY": {"full": 70, "half": 55},
    "GAP_FILL":  {"full": 65, "half": 50},
    "NORMAL":    {"full": 70, "half": 50},
    "DEVELOPING":{"full": 70, "half": 50},
}

TARGET_RULES = {
    "TREND_DAY": {"c1_R": 1.0, "c2_R": 3.0, "c3_enabled": True,  "c2_special": None},
    "RANGE_DAY": {"c1_R": 0.8, "c2_R": 1.5, "c3_enabled": False, "c2_special": None},
    "GAP_FILL":  {"c1_R": 1.0, "c2_R": 2.0, "c3_enabled": False, "c2_special": "PDC"},
    "NORMAL":    {"c1_R": 1.0, "c2_R": 2.0, "c3_enabled": True,  "c2_special": None},
    "DEVELOPING":{"c1_R": 1.0, "c2_R": 2.0, "c3_enabled": True,  "c2_special": None},
}

BE_RULES = {
    "TREND_DAY": "after_c2_plus_half_R",
    "RANGE_DAY": "on_c1_fill",
    "GAP_FILL":  "on_c1_fill",
    "NORMAL":    "on_c2_fill",
    "DEVELOPING":"on_c2_fill",
}

VEGAS_MIN_WIDTH_PT = 0.5


def get_config(day_type: Optional[str]) -> Dict:
    if not day_type or day_type not in QUALITY_WEIGHTS:
        day_type = "NORMAL"
    return {
        "day_type": day_type,
        "weights": QUALITY_WEIGHTS[day_type],
        "thresholds": SIZE_THRESHOLDS[day_type],
        "targets": TARGET_RULES[day_type],
        "be_rule": BE_RULES[day_type],
        "vegas_min_width": VEGAS_MIN_WIDTH_PT,
    }


def validate_weights() -> bool:
    for day, weights in QUALITY_WEIGHTS.items():
        total = sum(weights.values())
        if total != 100:
            raise ValueError(f"Day {day} weights sum to {total}, expected 100")
    return True


validate_weights()
