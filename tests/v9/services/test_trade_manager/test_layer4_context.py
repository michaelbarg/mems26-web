"""5 tests for Layer4Context — frozen dataclass behaviour."""
import pytest

from backend.v9.services.trade_manager.rules.base import Layer4Context


def test_layer4_context_is_frozen():
    """Layer4Context must be frozen — assignment raises FrozenInstanceError."""
    ctx = Layer4Context(cci_history=[1.0, 2.0])
    with pytest.raises(Exception):  # FrozenInstanceError (dataclasses) or AttributeError
        ctx.cci_history = [3.0]  # type: ignore[misc]


def test_layer4_context_defaults_all_none():
    """All four fields default to None."""
    ctx = Layer4Context()
    assert ctx.cci_history is None
    assert ctx.direction_change_event is None
    assert ctx.swi is None
    assert ctx.current_day_type is None


def test_layer4_context_stores_values():
    """Constructor stores supplied values on the right fields."""
    cci = [5.0, 6.0, 7.0]
    dce = {"type": "DIRECTION_CHANGE", "direction": "BEARISH"}
    swi = {"value": -0.5, "color": "red"}
    ctx = Layer4Context(
        cci_history=cci,
        direction_change_event=dce,
        swi=swi,
        current_day_type="TREND",
    )
    assert ctx.cci_history is cci
    assert ctx.direction_change_event is dce
    assert ctx.swi is swi
    assert ctx.current_day_type == "TREND"


def test_layer4_context_equality():
    """Two Layer4Context instances with identical field values are equal."""
    cci = [1.0, 2.0]
    ctx_a = Layer4Context(cci_history=cci, current_day_type="TREND")
    ctx_b = Layer4Context(cci_history=cci, current_day_type="TREND")
    assert ctx_a == ctx_b


def test_layer4_context_mutation_error_on_swi():
    """Attempting to set swi after construction raises an error."""
    ctx = Layer4Context(swi={"value": 1.0})
    with pytest.raises(Exception):
        ctx.swi = {}  # type: ignore[misc]
