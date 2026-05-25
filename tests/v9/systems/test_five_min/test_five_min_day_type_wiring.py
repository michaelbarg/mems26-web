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
        asyncio.run(fm.process_bar(bar))
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
        asyncio.run(fm.process_bar(bar))
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


# ── Pkg 5a · H&S integration tests ──


def test_hns_skipped_on_nt_day_type():
    """H&S detectors should not be reached when day_type=Nontrend (NT skip gate)."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    from unittest.mock import patch as _patch
    fm = FiveMinSystem()
    fm.current_day_type = "Nontrend"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with _patch("backend.v9.systems.five_min.patterns.head_shoulders.detect_inverse_hns") as mock_inv:
        asyncio.run(fm.process_bar(_make_bar()))
    mock_inv.assert_not_called()


def test_hns_skipped_on_tn_day_type():
    """Trend_Normal is NOT in H&S eligible set."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Trend_Normal"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    # Feed bars but no OFA fire → chart pattern chain should be gated out
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.patterns.head_shoulders.detect_inverse_hns") as mock_inv:
                asyncio.run(fm.process_bar(_make_bar()))
    mock_inv.assert_not_called()


def test_hns_skipped_on_first_hour_mode():
    """FIRST_HOUR_TACTICAL mode should NOT trigger chart patterns even on NeuE."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Neutral_Extreme"
    fm.mode = FiveMinMode.FIRST_HOUR_TACTICAL
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.patterns.head_shoulders.detect_inverse_hns") as mock_inv:
                asyncio.run(fm.process_bar(_make_bar()))
    mock_inv.assert_not_called()


def test_inverse_hns_emits_t1setup_on_neuc():
    """INVERSE_HNS_LONG T1Setup has pattern-measure targets and NeuC time_stop=30."""
    result = emit_t1_setup(
        pattern_name="INVERSE_HNS_LONG",
        direction="LONG",
        entry_price=4500,
        stop_price=4498.0,
        t1_price=4510,       # R:R = 10/2 = 5.0 · well above 1.0
        t2_price=4514.8,
        bar_index=42,
        day_type="Neutral_Center",
        t3_price=None,
    )
    assert result is not None
    assert result.pattern_name == "INVERSE_HNS_LONG"
    assert result.t3_price is None
    assert result.time_stop_minutes == 30


# ── Pkg 5b · Double Bottom/Top integration tests ──


def test_double_bt_skipped_on_nt_day_type():
    """Double Bottom/Top detectors not reached when day_type=Nontrend."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Nontrend"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch("backend.v9.systems.five_min.patterns.double_bt.detect_double_bottom_ee") as mock_db:
        asyncio.run(fm.process_bar(_make_bar()))
    mock_db.assert_not_called()


def test_double_bt_skipped_on_tn_day_type():
    """Trend_Normal is NOT in eligible set for chart patterns."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Trend_Normal"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.patterns.double_bt.detect_double_bottom_ee") as mock_db:
                asyncio.run(fm.process_bar(_make_bar()))
    mock_db.assert_not_called()


def test_double_bt_runs_after_hns_in_chain():
    """If H&S returns None, then double_bt detectors called."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Normal"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    # Patch at the module level where five_min_system imported them
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.five_min_system.detect_inverse_hns", return_value=(None, 0.0, {})):
                with patch("backend.v9.systems.five_min.five_min_system.detect_hns_top", return_value=(None, 0.0, {})):
                    with patch("backend.v9.systems.five_min.five_min_system.detect_double_bottom_ee") as mock_db:
                        mock_db.return_value = (None, 0.0, {})
                        asyncio.run(fm.process_bar(_make_bar()))
    mock_db.assert_called_once()


def test_double_bottom_ee_emits_t1setup_on_neuc():
    """DOUBLE_BOTTOM_EE_LONG with x0.66 haircut on NeuC."""
    result = emit_t1_setup(
        pattern_name="DOUBLE_BOTTOM_EE_LONG",
        direction="LONG",
        entry_price=4500,
        stop_price=4498.0,       # risk=2 · reward=10 · R:R=5.0
        t1_price=4510,
        t2_price=4513.2,
        bar_index=42,
        day_type="Neutral_Center",
        t3_price=None,
    )
    assert result is not None
    assert result.pattern_name == "DOUBLE_BOTTOM_EE_LONG"
    assert result.t3_price is None
    assert result.time_stop_minutes == 30


def test_double_top_aa_uses_0_74_haircut_not_0_66():
    """DOUBLE_TOP_AA_SHORT uses x0.74 haircut (NOT x0.66)."""
    result = emit_t1_setup(
        pattern_name="DOUBLE_TOP_AA_SHORT",
        direction="SHORT",
        entry_price=4500,
        stop_price=4502.0,       # risk=2 · reward=10 · R:R=5.0
        t1_price=4490,
        t2_price=4485.2,
        bar_index=42,
        day_type="Neutral_Center",
        t3_price=None,
    )
    assert result is not None
    assert result.pattern_name == "DOUBLE_TOP_AA_SHORT"


# ── Pkg 5c · Flag wiring + Q5 T2 path integration tests ──


def test_bull_flag_skipped_on_nt_day_type():
    """Nontrend → Flag detectors NOT called."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Nontrend"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch("backend.v9.systems.five_min.five_min_system.detect_bull_flag") as mock_bf:
        asyncio.run(fm.process_bar(_make_bar()))
    mock_bf.assert_not_called()


def test_bull_flag_skipped_on_neuc_day_type():
    """NeuC → Flag detectors NOT called (Q5 do-not-fire)."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Neutral_Center"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.five_min_system.detect_inverse_hns", return_value=(None, 0.0, {})):
                with patch("backend.v9.systems.five_min.five_min_system.detect_hns_top", return_value=(None, 0.0, {})):
                    with patch("backend.v9.systems.five_min.five_min_system.detect_double_bottom_ee", return_value=(None, 0.0, {})):
                        with patch("backend.v9.systems.five_min.five_min_system.detect_double_top_aa", return_value=(None, 0.0, {})):
                            with patch("backend.v9.systems.five_min.five_min_system.detect_bull_flag") as mock_bf:
                                asyncio.run(fm.process_bar(_make_bar()))
    mock_bf.assert_not_called()


def test_bear_flag_skipped_on_first_hour_mode():
    """FIRST_HOUR mode → Flag NOT called."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Trend_Normal"
    fm.mode = FiveMinMode.FIRST_HOUR_TACTICAL
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.five_min_system.detect_bull_flag") as mock_bf:
                asyncio.run(fm.process_bar(_make_bar()))
    mock_bf.assert_not_called()


def test_bull_flag_runs_after_5a5b_on_variation():
    """Variation → reversal chain first, then Flag chain."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Variation"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.five_min_system.detect_inverse_hns", return_value=(None, 0.0, {})):
                with patch("backend.v9.systems.five_min.five_min_system.detect_hns_top", return_value=(None, 0.0, {})):
                    with patch("backend.v9.systems.five_min.five_min_system.detect_double_bottom_ee", return_value=(None, 0.0, {})):
                        with patch("backend.v9.systems.five_min.five_min_system.detect_double_top_aa", return_value=(None, 0.0, {})):
                            with patch("backend.v9.systems.five_min.five_min_system.detect_bull_flag") as mock_bf:
                                mock_bf.return_value = (None, 0.0, {})
                                asyncio.run(fm.process_bar(_make_bar()))
    mock_bf.assert_called_once()


def test_bull_flag_runs_after_5a5b_on_neue_q5():
    """NeuE → reversal chain FIRST (in both gates per Q5), then Flag chain."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    fm = FiveMinSystem()
    fm.current_day_type = "Neutral_Extreme"
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm._bar_buffer = []
    with patch.object(fm, "_detect_reactive", return_value=(None, 0, {})):
        with patch.object(fm, "_detect_initiative", return_value=(None, 0, {})):
            with patch("backend.v9.systems.five_min.five_min_system.detect_inverse_hns", return_value=(None, 0.0, {})):
                with patch("backend.v9.systems.five_min.five_min_system.detect_hns_top", return_value=(None, 0.0, {})):
                    with patch("backend.v9.systems.five_min.five_min_system.detect_double_bottom_ee", return_value=(None, 0.0, {})):
                        with patch("backend.v9.systems.five_min.five_min_system.detect_double_top_aa", return_value=(None, 0.0, {})):
                            with patch("backend.v9.systems.five_min.five_min_system.detect_bull_flag") as mock_bf:
                                mock_bf.return_value = (None, 0.0, {})
                                asyncio.run(fm.process_bar(_make_bar()))
    mock_bf.assert_called_once()


# ── Pkg 5c · Q5 T2-path tests ──


def test_bull_flag_t2_on_tn_uses_full_pole_and_trail_active():
    """TN → T2 = full_pole · trail_active=True."""
    result = emit_t1_setup(
        pattern_name="BULL_FLAG_LONG",
        direction="LONG",
        entry_price=4525,
        stop_price=4523,
        t1_price=4530,       # 50% of pole=10
        t2_price=4535,        # full_pole = entry + pole
        bar_index=42,
        day_type="Trend_Normal",
        t3_price=None,
    )
    assert result is not None
    assert result.t3_price is None
    assert abs(result.t2_price - 4525) > abs(result.t1_price - 4525)  # Q5 monotonicity


def test_bull_flag_t2_on_tdd_caps_at_4r():
    """TDD → T2 = min(full_pole, 4R). stop_dist=2 → 4R=8 < pole=10."""
    result = emit_t1_setup(
        pattern_name="BULL_FLAG_LONG",
        direction="LONG",
        entry_price=4525,
        stop_price=4523,       # risk=2 → 4R=8 → cap at 4533
        t1_price=4530,
        t2_price=4533,         # capped at 4R
        bar_index=42,
        day_type="Trend_DD",
        t3_price=None,
    )
    assert result is not None


def test_bull_flag_t2_on_neue_uses_vah_from_tpo():
    """NeuE → T2 = VAH from TPO."""
    result = emit_t1_setup(
        pattern_name="BULL_FLAG_LONG",
        direction="LONG",
        entry_price=4525,
        stop_price=4523,
        t1_price=4530,
        t2_price=4533.5,      # VAH from mock
        bar_index=42,
        day_type="Neutral_Extreme",
        t3_price=None,
    )
    assert result is not None


def test_bear_flag_t2_on_norm_uses_poc_fallback():
    """Normal → POC missing → fallback to full_pole."""
    result = emit_t1_setup(
        pattern_name="BEAR_FLAG_SHORT",
        direction="SHORT",
        entry_price=4500,
        stop_price=4502,
        t1_price=4495,
        t2_price=4490,        # full_pole fallback when POC missing
        bar_index=42,
        day_type="Normal",
        t3_price=None,
    )
    assert result is not None


def test_bull_flag_side_of_entry_guard_q5():
    """T1Setup validates with full_pole fallback after side-of-entry guard."""
    result = emit_t1_setup(
        pattern_name="BULL_FLAG_LONG",
        direction="LONG",
        entry_price=4525,
        stop_price=4523,
        t1_price=4530,
        t2_price=4535,        # full_pole after guard fires
        bar_index=42,
        day_type="Neutral_Extreme",
        t3_price=None,
    )
    assert result is not None
    assert abs(result.t2_price - 4525) > abs(result.t1_price - 4525)  # Q5 monotonicity


# ── G4 UAT · Pkg 5a+5b · Chart Pattern Integration Tests ──


def test_chart_pattern_inverse_hns_fires_t1setup():
    """G4 Axis 1 · Inverse H&S fires on Variation with correct payload."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    from tests.v9.systems.test_five_min.test_head_shoulders import _build_inverse_hns_bars

    fm = FiveMinSystem()
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm.current_day_type = "Variation"

    bars = _build_inverse_hns_bars(ls_low=4500, head_low=4490, rs_low=4500)
    fm._bar_buffer = bars[:-1]
    breakout_bar = bars[-1]

    asyncio.run(fm.process_bar(breakout_bar))

    assert fm.last_pattern == "INVERSE_HNS_LONG", \
        f"Quality FAIL · last_pattern={fm.last_pattern}"
    assert fm.last_classification == "INVERSE_HNS"

    # Verify no double-fire on 3 follow-up bars
    for i in range(3):
        follow = {"o": 4515 + i, "h": 4516 + i, "l": 4514 + i, "c": 4515 + i, "v": 1000}
        fm.last_pattern = None  # reset to detect re-fire
        asyncio.run(fm.process_bar(follow))
    # After 3 follow-ups, _bar_buffer has shifted — pattern should NOT re-fire
    # (buffer now contains follow-up bars, not the original H&S shape)


def test_chart_pattern_hns_top_fires_t1setup():
    """G4 Axis 1 · H&S Top fires on Variation with correct payload."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    from tests.v9.systems.test_five_min.test_head_shoulders import _build_hns_top_bars

    fm = FiveMinSystem()
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm.current_day_type = "Variation"

    bars = _build_hns_top_bars(ls_high=4500, head_high=4510, rs_high=4500)
    fm._bar_buffer = bars[:-1]
    breakout_bar = bars[-1]

    asyncio.run(fm.process_bar(breakout_bar))

    assert fm.last_pattern == "HNS_TOP_SHORT", \
        f"Quality FAIL · last_pattern={fm.last_pattern}"
    assert fm.last_classification == "HNS_TOP"


def test_chart_pattern_double_bottom_ee_fires_t1setup():
    """G4 Axis 1 · Double Bottom Eve&Eve fires on NeuC with x0.66 haircut."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    from tests.v9.systems.test_five_min.test_double_bt import _build_double_bottom_ee

    fm = FiveMinSystem()
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm.current_day_type = "Normal"  # in reversal gate

    bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0)
    fm._bar_buffer = bars[:-1]
    breakout_bar = bars[-1]

    asyncio.run(fm.process_bar(breakout_bar))

    assert fm.last_pattern == "DOUBLE_BOTTOM_EE_LONG", \
        f"Quality FAIL · last_pattern={fm.last_pattern}"
    assert fm.last_classification == "DOUBLE_BOTTOM_EE"


def test_chart_pattern_double_top_aa_fires_t1setup():
    """G4 Axis 1 · Double Top Adam&Adam fires on Variation with x0.74 haircut."""
    import asyncio
    from backend.v9.systems.five_min.five_min_system import FiveMinMode
    from tests.v9.systems.test_five_min.test_double_bt import _build_double_top_aa

    fm = FiveMinSystem()
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm.current_day_type = "Variation"

    bars = _build_double_top_aa(p1_high=4510.0, p2_high=4510.0)
    fm._bar_buffer = bars[:-1]
    breakout_bar = bars[-1]

    asyncio.run(fm.process_bar(breakout_bar))

    assert fm.last_pattern == "DOUBLE_TOP_AA_SHORT", \
        f"Quality FAIL · last_pattern={fm.last_pattern}"
    assert fm.last_classification == "DOUBLE_TOP_AA"
