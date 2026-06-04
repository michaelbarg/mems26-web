"""Round-trip equality tests: YAML config == hardcoded constants.

Proves that loading from YAML produces byte-for-byte identical values
to the hardcoded const-dicts. No trading behavior change.
"""

import pytest


def test_auth_matrix_roundtrip():
    """YAML auth_matrix.yaml == _AUTH_TABLE_V1 hardcoded dict (70 cells)."""
    from backend.v9.config_loader import load_auth_matrix
    from backend.v9.systems.five_min.auth_table_v1 import _AUTH_TABLE_V1

    loaded = load_auth_matrix()
    assert loaded is not None, "auth_matrix.yaml failed to load"
    assert len(loaded) == 70, f"expected 70 cells, got {len(loaded)}"

    for key, expected in _AUTH_TABLE_V1.items():
        actual = loaded.get(key)
        assert actual is not None, f"missing cell: {key}"
        assert actual == expected, (
            f"mismatch at {key}: yaml={actual} vs hardcoded={expected}"
        )


def test_targets_roundtrip():
    """YAML targets.yaml == _TARGETS hardcoded dict (7 day types)."""
    from backend.v9.config_loader import load_targets
    from backend.v9.systems.day_type.targets_table import _TARGETS

    loaded = load_targets()
    assert loaded is not None, "targets.yaml failed to load"
    assert len(loaded) >= 7, f"expected >=7 day_types, got {len(loaded)}"

    for dt, expected in _TARGETS.items():
        actual = loaded.get(dt)
        assert actual is not None, f"missing day_type: {dt}"
        # Compare all keys that exist in both
        for key in expected:
            if key == "reasoning_notes":
                continue  # YAML doesn't carry this
            exp_val = expected[key]
            act_val = actual.get(key)
            assert act_val == exp_val, (
                f"mismatch at {dt}.{key}: yaml={act_val} vs hardcoded={exp_val}"
            )


def test_stop_params_roundtrip():
    """YAML stop_params.yaml == hardcoded constants in adaptive_stop.py."""
    from backend.v9.config_loader import load_stop_params

    data = load_stop_params()
    assert data is not None, "stop_params.yaml failed to load"

    s2 = data.get("s2_adaptive", {})
    assert s2.get("mes_tick") == 0.25
    assert s2.get("floor_ticks") == 4
    assert s2.get("floor_ticks_min_backstop") == 4
    assert s2.get("floor_atr_k") == 1.75
    assert s2.get("atr_multipliers") == {
        "Reactive": 1.0, "OFA": 1.5, "Flag": 1.5,
        "Double_BT": 2.0, "HnS": 2.0,
    }

    # S4 patterns
    s4 = data.get("s4_patterns", {})
    assert s4["ZLR"] == {"stop_ticks": 8, "t1_ticks": 12, "t2_ticks": 24}
    assert s4["TLB"] == {"stop_ticks": 10, "t1_ticks": 15, "t2_ticks": 30}
    assert s4["VEGAS"] == {"stop_ticks": 12, "t1_ticks": 16, "t2_ticks": 32}

    # min_r_t1_threshold
    assert data.get("min_r_t1_threshold") == 0.0


def test_auth_matrix_schema_rejects_bad_config(tmp_path):
    """Schema validation rejects invalid auth_matrix → fallback."""
    import os
    import yaml
    from backend.v9.config_loader import load_auth_matrix

    bad_yaml = tmp_path / "auth_matrix.yaml"
    bad_yaml.write_text(yaml.dump({
        "cells": {
            "REACTIVE_LONG": {
                "Trend_Normal": {"verdict": "INVALID_VERDICT", "high": 99, "medium": 0, "low": 0}
            }
        }
    }))

    old_dir = os.environ.get("MEMS26_CONFIG_DIR")
    os.environ["MEMS26_CONFIG_DIR"] = str(tmp_path)
    try:
        # Reload to pick up the env change
        import importlib
        import backend.v9.config_loader as cl
        cl._CONFIG_DIR = tmp_path
        result = load_auth_matrix()
        assert result is None, "invalid config should return None (fallback)"
    finally:
        cl._CONFIG_DIR = cl.Path(cl.os.getenv(
            "MEMS26_CONFIG_DIR",
            str(cl.Path(__file__).resolve().parent.parent.parent / "config"),
        ))
        if old_dir:
            os.environ["MEMS26_CONFIG_DIR"] = old_dir
        else:
            os.environ.pop("MEMS26_CONFIG_DIR", None)


def test_stop_params_guardrail_rejects_excessive_ticks(tmp_path):
    """Guardrail: stop_ticks > max_stop_ticks → rejected."""
    import yaml
    from backend.v9 import config_loader as cl

    bad_yaml = tmp_path / "stop_params.yaml"
    bad_yaml.write_text(yaml.dump({
        "s2_adaptive": {
            "mes_tick": 0.25, "floor_ticks": 4,
            "floor_ticks_min_backstop": 4, "floor_atr_k": 1.75,
            "atr_multipliers": {"Reactive": 1.0, "OFA": 1.5, "Flag": 1.5, "Double_BT": 2.0, "HnS": 2.0},
        },
        "s4_patterns": {
            "ZLR": {"stop_ticks": 999, "t1_ticks": 12, "t2_ticks": 24},  # exceeds guardrail
        },
        "min_r_t1_threshold": 0.0,
        "guardrails": {"max_stop_ticks": 20, "max_t2_ticks": 50, "max_atr_multiplier": 5.0},
    }))

    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path
    try:
        result = cl.load_stop_params()
        assert result is None, "excessive stop_ticks should be rejected"
    finally:
        cl._CONFIG_DIR = old_dir


def test_contracts_cap_enforced(tmp_path):
    """Guardrail: contracts > max_contracts → rejected."""
    import yaml
    from backend.v9 import config_loader as cl

    bad_yaml = tmp_path / "auth_matrix.yaml"
    # Build a "valid" structure but with contracts exceeding cap
    cells = {}
    for p in ["REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT",
              "INVERSE_HNS_LONG", "HNS_TOP_SHORT", "DOUBLE_BOTTOM_EE_LONG",
              "DOUBLE_TOP_AA_SHORT", "BULL_FLAG_LONG", "BEAR_FLAG_SHORT"]:
        cells[p] = {}
        for dt in ["Trend_Normal", "Trend_DD", "Neutral_Extreme", "Variation",
                    "Neutral_Center", "Normal", "Nontrend"]:
            cells[p][dt] = {"verdict": "FULL", "high": 10, "medium": 0, "low": 0}  # 10 > max_contracts=3

    bad_yaml.write_text(yaml.dump({"max_contracts": 3, "cells": cells}))

    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path
    try:
        result = cl.load_auth_matrix()
        assert result is None, "contracts exceeding max should be rejected"
    finally:
        cl._CONFIG_DIR = old_dir
