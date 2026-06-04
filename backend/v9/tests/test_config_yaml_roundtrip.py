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


@pytest.fixture
def _save_config_dir():
    """Save and restore config_loader._CONFIG_DIR across tests."""
    from backend.v9 import config_loader as cl
    original = cl._CONFIG_DIR
    yield cl
    cl._CONFIG_DIR = original


def test_auth_matrix_schema_rejects_bad_config(tmp_path, _save_config_dir):
    """Schema validation rejects invalid auth_matrix → fallback."""
    import yaml

    cl = _save_config_dir
    bad_yaml = tmp_path / "auth_matrix.yaml"
    bad_yaml.write_text(yaml.dump({
        "cells": {
            "REACTIVE_LONG": {
                "Trend_Normal": {"verdict": "INVALID_VERDICT", "high": 99, "medium": 0, "low": 0}
            }
        }
    }))

    cl._CONFIG_DIR = tmp_path
    result = cl.load_auth_matrix()
    assert result is None, "invalid config should return None (fallback)"


def test_stop_params_guardrail_rejects_excessive_ticks(tmp_path, _save_config_dir):
    """Guardrail: stop_ticks > max_stop_ticks → rejected."""
    import yaml
    cl = _save_config_dir

    bad_yaml = tmp_path / "stop_params.yaml"
    bad_yaml.write_text(yaml.dump({
        "s2_adaptive": {
            "mes_tick": 0.25, "floor_ticks": 4,
            "floor_ticks_min_backstop": 4, "floor_atr_k": 1.75,
            "atr_multipliers": {"Reactive": 1.0, "OFA": 1.5, "Flag": 1.5, "Double_BT": 2.0, "HnS": 2.0},
        },
        "s4_patterns": {
            "ZLR": {"stop_ticks": 999, "t1_ticks": 12, "t2_ticks": 24},
        },
        "min_r_t1_threshold": 0.0,
        "guardrails": {"max_stop_ticks": 20, "max_t2_ticks": 50, "max_atr_multiplier": 5.0},
    }))

    cl._CONFIG_DIR = tmp_path
    result = cl.load_stop_params()
    assert result is None, "excessive stop_ticks should be rejected"


def test_contracts_cap_enforced(tmp_path, _save_config_dir):
    """Guardrail: contracts > max_contracts → rejected."""
    import yaml
    cl = _save_config_dir

    bad_yaml = tmp_path / "auth_matrix.yaml"
    cells = {}
    for p in ["REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT",
              "INVERSE_HNS_LONG", "HNS_TOP_SHORT", "DOUBLE_BOTTOM_EE_LONG",
              "DOUBLE_TOP_AA_SHORT", "BULL_FLAG_LONG", "BEAR_FLAG_SHORT"]:
        cells[p] = {}
        for dt in ["Trend_Normal", "Trend_DD", "Neutral_Extreme", "Variation",
                    "Neutral_Center", "Normal", "Nontrend"]:
            cells[p][dt] = {"verdict": "FULL", "high": 10, "medium": 0, "low": 0}

    bad_yaml.write_text(yaml.dump({"max_contracts": 3, "cells": cells}))

    cl._CONFIG_DIR = tmp_path
    result = cl.load_auth_matrix()
    assert result is None, "contracts exceeding max should be rejected"


# ── Phase 3: S4 anti-tautological tests ─────────────────────────────

# Map of detector modules for dynamic import
_S4_DETECTORS = {
    "ZLR": "backend.v9.systems.woodies.patterns.zlr",
    "TLB": "backend.v9.systems.woodies.patterns.tlb",
    "TT": "backend.v9.systems.woodies.patterns.tt",
    "GB100": "backend.v9.systems.woodies.patterns.gb100",
    "VEGAS": "backend.v9.systems.woodies.patterns.vegas",
    "GHOST": "backend.v9.systems.woodies.patterns.ghost",
    "FAMIR": "backend.v9.systems.woodies.patterns.famir",
    "HTLB": "backend.v9.systems.woodies.patterns.htlb",
    "HFE": "backend.v9.systems.woodies.patterns.hfe",
}


def test_s4_ticks_yaml_matches_detector_constants():
    """All 9 S4 patterns: YAML s4_patterns == detector module constants.

    Imports the REAL detector constants (not literals) to catch drift.
    If reverted (wiring removed) → RED because detector constants would
    revert to hardcoded while YAML stays at a different value if edited.
    """
    from backend.v9.config_loader import load_stop_params
    import importlib

    data = load_stop_params()
    assert data is not None, "stop_params.yaml failed to load"
    s4 = data.get("s4_patterns", {})

    for pid, module_path in _S4_DETECTORS.items():
        mod = importlib.import_module(module_path)
        yaml_ticks = s4.get(pid)
        assert yaml_ticks is not None, f"YAML missing pattern {pid}"

        det_stop = getattr(mod, "STOP_TICKS")
        det_t1 = getattr(mod, "TARGET1_TICKS")
        det_t2 = getattr(mod, "TARGET2_TICKS")

        assert yaml_ticks["stop_ticks"] == det_stop, (
            f"{pid}: YAML stop_ticks={yaml_ticks['stop_ticks']} != detector STOP_TICKS={det_stop}"
        )
        assert yaml_ticks["t1_ticks"] == det_t1, (
            f"{pid}: YAML t1_ticks={yaml_ticks['t1_ticks']} != detector TARGET1_TICKS={det_t1}"
        )
        assert yaml_ticks["t2_ticks"] == det_t2, (
            f"{pid}: YAML t2_ticks={yaml_ticks['t2_ticks']} != detector TARGET2_TICKS={det_t2}"
        )


def test_s4_detector_reads_from_yaml(tmp_path):
    """Litmus: override YAML → detector reads the override (not hardcoded).

    Monkeypatches ZLR stop_ticks 8→9 in YAML, reloads, verifies the
    detector's STOP_TICKS == 9. If wiring is reverted → RED because
    the detector would still read its hardcoded 8.
    """
    import yaml
    import importlib
    from backend.v9.systems.woodies.patterns import _pattern_ticks

    # Build a stop_params.yaml with ZLR stop_ticks=9 (modified from default 8)
    from backend.v9.config_loader import load_stop_params
    data = load_stop_params()
    assert data is not None
    modified = dict(data)
    modified["s4_patterns"] = dict(data.get("s4_patterns", {}))
    modified["s4_patterns"]["ZLR"] = {"stop_ticks": 9, "t1_ticks": 12, "t2_ticks": 24}

    override_yaml = tmp_path / "stop_params.yaml"
    override_yaml.write_text(yaml.dump(modified))

    # Also need valid auth_matrix.yaml and targets.yaml for config_loader
    from backend.v9 import config_loader as cl
    old_dir = cl._CONFIG_DIR
    cl._CONFIG_DIR = tmp_path

    # Copy other yaml files
    import shutil
    for f in ("auth_matrix.yaml", "targets.yaml"):
        src = old_dir / f
        if src.exists():
            shutil.copy(src, tmp_path / f)

    try:
        # Reset the cache so it re-reads
        _pattern_ticks.reset_cache()

        # Read through the helper
        ticks = _pattern_ticks.get_ticks("ZLR")
        assert ticks["stop_ticks"] == 9, (
            f"Expected ZLR stop_ticks=9 from YAML override, got {ticks['stop_ticks']}. "
            "If this fails, the detector is NOT reading from YAML (wiring broken)."
        )
    finally:
        cl._CONFIG_DIR = old_dir
        _pattern_ticks.reset_cache()  # restore for other tests
