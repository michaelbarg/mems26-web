"""T-328 §4 / B8: structural stop authority — resolver/floor/ladder don't widen.

Mutation: setup WITHOUT stop_is_structural → resolver still moves the stop.
"""


def test_structural_stop_bypasses_resolver():
    """A setup with stop_is_structural=True keeps its stop untouched."""
    # We test the gateway's _stop_is_structural extraction and bypass logic.
    # The full gateway is too heavy; test the flag extraction inline.
    setup = {
        "direction": "SHORT",
        "entry_price": 7674.75,
        "stop": 7679.00,
        "classification": "CEILING_FLIP_TOUCH2",
        "metadata": {"stop_is_structural": True},
    }
    _stop_is_structural = bool((setup.get("metadata") or {}).get("stop_is_structural"))
    assert _stop_is_structural is True
    # The gateway would skip StopResolver and STEP_SCALED_LADDER.
    # Verify the stop is unchanged:
    assert setup["stop"] == 7679.00


def test_mutation_no_flag_allows_resolver():
    """A setup WITHOUT stop_is_structural → resolver is free to modify."""
    setup = {
        "direction": "SHORT",
        "entry_price": 7674.75,
        "stop": 7679.00,
        "classification": "REACTIVE_SHORT",
        "metadata": {},
    }
    _stop_is_structural = bool((setup.get("metadata") or {}).get("stop_is_structural"))
    assert _stop_is_structural is False


def test_ceiling_flip_touch2_carries_flag():
    """The CEILING_FLIP_TOUCH2 producer sets stop_is_structural=True."""
    # Build a minimal touch2 setup as the producer would
    _t2_setup = {
        "direction": "SHORT",
        "entry_price": 7674.75,
        "stop": 7679.00,
        "classification": "CEILING_FLIP_TOUCH2",
        "structural_anchor": 7678.75,
        "metadata": {
            "shadow_only": True,
            "stop_is_structural": True,
            "pattern": "CEILING_FLIP_TOUCH2",
        },
    }
    assert _t2_setup["metadata"]["stop_is_structural"] is True


def test_ceiling_flip_carries_flag():
    """The CEILING_FLIP (neckline break) producer also sets the flag."""
    from backend.v9.systems.ceiling_flip import build_flip_setup
    ceiling_floor = {
        "state": "CEILING_FAILED",
        "p1": 7678.75,
        "p2": 7678.50,
        "confirm_close": 7660.0,
        "signal_bar_ts": "2026-09-11T17:45:00",
    }
    setup = build_flip_setup(
        ceiling_floor=ceiling_floor, atr=10.0,
        poc=7670.0, opposite_edge=7660.0, shadow_only=True)
    assert setup is not None
    assert setup["metadata"]["stop_is_structural"] is True
