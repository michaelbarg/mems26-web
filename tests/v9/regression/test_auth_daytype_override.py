"""D-0717-A — S2 auth/emit day_type must honor DAY_TYPE_MANUAL_OVERRIDE.

Live finding 2026-07-17 18:06 (Michael): S2's auth verdict showed
"INITIATIVE_LONG × Normal" (a SKIP row) while DAY_TYPE_MANUAL_OVERRIDE=
2026-07-17:Variation was live. Root: five_min_system fed the auth-cell
lookup (compute_v2_sizing → _auth_cell) and the build-status display from
self.current_day_type / v9_day_type_history — the OLD engine's event value —
instead of the canonical override-aware trade_context.get_live_day_type().

Anti-tautological: drives the REAL process_bar() fire path (same reactive-long
fixture as tests/v9/systems/five_min/tests/test_process_bar_emission.py) with
the stale event value set to "Normal" and the env override set to Variation,
then asserts each seam saw "Variation". If the D-0717-A wiring is reverted
(back to `self.current_day_type or "Normal"` / bare `_get_current_day_type()`),
these go RED with "Normal".

Env-level override semantics (date-scoping, malformed → inert) are already
pinned in test_day_type_manual_override.py — not duplicated here.
"""
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _today_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def _reactive_long_bars():
    """7 bars: 3 lookback + 4 pattern matching Reactive LONG criteria
    (same fixture as test_process_bar_emission.py)."""
    return [
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},
    ]


def _make_sys():
    sys_ = FiveMinSystem()
    sys_._hydrated = True
    sys_.current_state = {"last_reasoning_notes": ""}
    sys_.last_pattern = None
    sys_.last_classification = None
    sys_.last_confluence = 0
    sys_.opening_type = None
    # The BUG scenario: OLD-engine event/hydration value is stale "Normal"
    sys_.current_day_type = "Normal"
    sys_._bar_buffer = _reactive_long_bars()[:-1]
    return sys_


def _fire(sys_):
    asyncio.run(sys_.process_bar(_reactive_long_bars()[-1]))


@patch("backend.v9.systems.five_min.five_min_system.emit_t1_setup")
@patch.object(FiveMinSystem, "_get_cot_from_footprint", return_value=150.0)
@patch.object(FiveMinSystem, "_get_amt_from_footprint", return_value=100.0)
@patch.object(FiveMinSystem, "_get_belly_from_footprint", return_value=True)
@patch.object(FiveMinSystem, "_get_belly_ratio_from_footprint", return_value=2.0)
def test_emit_path_sees_override_label(_br, _belly, _amt, _cot, mock_emit,
                                       monkeypatch):
    """Override set → emit_t1_setup(day_type=...) gets the override label,
    NOT the stale current_day_type event value."""
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{_today_et()}:Variation")
    monkeypatch.delenv("DAYTYPE_GATE_LIVE_V1", raising=False)   # override wins without the gate flag
    monkeypatch.delenv("DAYTYPE_ANTIFLAP_V1", raising=False)
    monkeypatch.delenv("STOP_ANCHORS_V2", raising=False)        # legacy sizing branch
    mock_emit.return_value = MagicMock(pattern_name="REACTIVE_LONG")

    sys_ = _make_sys()
    _fire(sys_)

    assert mock_emit.called, "fixture must fire (precondition, same as emission test)"
    assert mock_emit.call_args.kwargs["day_type"] == "Variation", (
        f"emit path saw {mock_emit.call_args.kwargs['day_type']!r} — "
        "must consult get_live_day_type() (override-aware) before current_day_type"
    )


@patch("backend.v9.systems.five_min.five_min_system.emit_t1_setup")
@patch.object(FiveMinSystem, "_get_cot_from_footprint", return_value=150.0)
@patch.object(FiveMinSystem, "_get_amt_from_footprint", return_value=100.0)
@patch.object(FiveMinSystem, "_get_belly_from_footprint", return_value=True)
@patch.object(FiveMinSystem, "_get_belly_ratio_from_footprint", return_value=2.0)
def test_auth_sizing_path_sees_override_label(_br, _belly, _amt, _cot,
                                              mock_emit, monkeypatch):
    """THE 18:06 bug seam: compute_v2_sizing (auth-cell verdict) must get the
    override label. Reverting line `day_type=_live_day_type or ...` back to
    `self.current_day_type or "Normal"` turns this RED with "Normal"."""
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{_today_et()}:Variation")
    monkeypatch.delenv("DAYTYPE_GATE_LIVE_V1", raising=False)
    monkeypatch.delenv("DAYTYPE_ANTIFLAP_V1", raising=False)
    monkeypatch.setenv("STOP_ANCHORS_V2", "1")                  # activate the V2 auth/sizing branch
    mock_emit.return_value = MagicMock(pattern_name="REACTIVE_LONG")

    seen = {}

    def _spy_sizing(**kwargs):
        seen.update(kwargs)
        return None  # SKIP → falls back to legacy sizing; fire continues

    import backend.v9.systems.stop_anchors.sizing as sizing_mod
    monkeypatch.setattr(sizing_mod, "compute_v2_sizing", _spy_sizing)

    sys_ = _make_sys()
    _fire(sys_)

    assert seen, "compute_v2_sizing was not reached — STOP_ANCHORS_V2 branch must run"
    assert seen["day_type"] == "Variation", (
        f"auth/sizing path saw day_type={seen['day_type']!r} — the auth verdict "
        "must resolve pattern × OVERRIDE day_type (18:06 live bug)"
    )


def test_build_status_s2_display_sees_override_label(monkeypatch):
    """The display surface that showed 'INITIATIVE_LONG × Normal': the
    aggregator must hand s2_inspector the override-aware label, not the
    v9_day_type_history DB value."""
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{_today_et()}:Variation")
    monkeypatch.delenv("DAYTYPE_GATE_LIVE_V1", raising=False)
    monkeypatch.delenv("DAYTYPE_ANTIFLAP_V1", raising=False)

    from backend.v9.systems.build_status import aggregator as agg_mod

    seen = {}

    def _spy_inspect(five_min_system=None, day_type_str=None):
        seen["day_type_str"] = day_type_str
        from backend.v9.systems.build_status.types import SystemStatus
        return SystemStatus(id="five_min", name="S2", running=True, hydrated=True)

    monkeypatch.setattr(agg_mod.s2_inspector, "inspect", _spy_inspect)
    # DB history read must NOT be consulted when the live source answers
    monkeypatch.setattr(
        agg_mod.BuildStatusAggregator, "_get_current_day_type",
        lambda self: "Normal",
    )

    agg = agg_mod.BuildStatusAggregator()
    agg.get_status(systems=["five_min"])

    assert seen.get("day_type_str") == "Variation", (
        f"s2_inspector got day_type_str={seen.get('day_type_str')!r} — the auth "
        "display must show the SAME override-aware label the verdict trades on"
    )
