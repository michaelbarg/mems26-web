"""Wrappers alignment with Master Matrix V1.0."""


def test_system_3_is_footprint_not_tick_reversal():
    """System 3 name must be 'footprint' per Master Matrix."""
    from backend.v9.systems.wrappers import TickReversalSystem
    sys3 = TickReversalSystem()
    assert sys3.system_id == 3
    assert sys3.name == "footprint", f"System 3 name is '{sys3.name}', should be 'footprint'"


def test_docstring_says_firing_for_s2_s3_s4():
    """Wrappers docstring must say Firing = S2/S3/S4."""
    with open("backend/v9/systems/wrappers.py") as f:
        header = f.read()[:500]
    assert "Firing" in header
    assert "5-Min (2)" in header or "Chart5Min (2)" in header
    assert "Footprint (3)" in header
    assert "Woodies (4)" in header


def test_docstring_says_observer_for_s1_s5_s6():
    """Wrappers docstring must say Observer = S1/S5/S6."""
    with open("backend/v9/systems/wrappers.py") as f:
        header = f.read()[:500]
    assert "Observer" in header
    assert "DayType (1)" in header
    assert "TPO (5)" in header
    assert "Killzone (6)" in header
