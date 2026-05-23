"""Tests for FiveMin day_type wiring + NT skip gate (Pkg 3a Stream 2)."""
import logging
from unittest.mock import patch

from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup


def _make_bar(o=5248, h=5249, l=5247, c=5248, v=500):
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "open": o, "high": h, "low": l, "close": c, "volume": v}


def test_current_day_type_starts_none():
    fm = FiveMinSystem()
    assert fm.current_day_type is None


def test_on_day_type_update_sets_current_day_type():
    fm = FiveMinSystem()
    fm._on_day_type_update({
        "event_type": "day_type",
        "payload": {"day_type": "Trend_Normal"},
    })
    assert fm.current_day_type == "Trend_Normal"


def test_on_day_type_update_logs_transition(caplog):
    fm = FiveMinSystem()
    with caplog.at_level(logging.INFO):
        fm._on_day_type_update({"payload": {"day_type": "Trend_Normal"}})
        fm._on_day_type_update({"payload": {"day_type": "Nontrend"}})
    transitions = [r for r in caplog.records if "current_day_type" in r.getMessage()]
    assert len(transitions) >= 2


def test_nt_skip_increments_counter():
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Nontrend"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    bar = _make_bar()
    for _ in range(3):
        asyncio.get_event_loop().run_until_complete(fm.process_bar(bar))
    assert fm._nt_skip_count == 3


def test_nt_skip_counter_accumulates_across_bars():
    """Counter accumulates per bar; NT skip returns early (no pattern detection)."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Nontrend"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    bar = _make_bar()
    for _ in range(10):
        asyncio.get_event_loop().run_until_complete(fm.process_bar(bar))
    assert fm._nt_skip_count == 10
    # Bars still buffered (gate is after buffering)
    assert len(fm._bar_buffer) > 0


def test_emit_t1_setup_refuses_nontrend(caplog):
    with caplog.at_level(logging.WARNING):
        result = emit_t1_setup(
            pattern_name="REACTIVE_LONG",
            direction="LONG",
            entry_price=4500,
            stop_price=4490,
            t1_price=4510,
            t2_price=4520,
            bar_index=10,
            day_type="Nontrend",
        )
    assert result is None
    assert any("NO_TRADE" in r.getMessage() for r in caplog.records)


def test_emit_t1_setup_includes_t3_price():
    result = emit_t1_setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500,
        stop_price=4490,
        t1_price=4510,
        t2_price=4520,
        bar_index=10,
        day_type="Trend_Normal",
        t3_price=4525.0,
    )
    assert result is not None
    assert result.t3_price == 4525.0


def test_emit_t1_setup_accepts_none_time_stop():
    result = emit_t1_setup(
        pattern_name="REACTIVE_LONG",
        direction="LONG",
        entry_price=4500,
        stop_price=4490,
        t1_price=4510,
        t2_price=4520,
        bar_index=10,
        day_type="Trend_Normal",
    )
    assert result is not None
    assert result.time_stop_minutes is None
