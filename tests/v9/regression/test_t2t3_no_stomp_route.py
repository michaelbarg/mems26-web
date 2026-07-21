"""Task#4 route-level verification (cursor, anti-tautological).

cc's test_t2t3_no_stomp.py re-implements the gateway arithmetic inline —
it can pass even if the gateway wiring is wrong. These tests run the REAL
`TradingGateway.route_setup` fire path end-to-end:

  real resolve_structural_targets (Variation REV SHORT → C2=POC, C3=VAL)
  → real PATTERN_T1_OVERRIDE (REACTIVE_SHORT × Variation = 9.0pt from
    config/targets.yaml)
  → assert the final setup dict the gateway would hand to execution.

Case #420 day (07-20): entry 7508.75 SHORT, poc=7505, val=7490, vah=7527.5.
"""
from __future__ import annotations

import zoneinfo

import pytest

from backend.v9.gateway import trading_gateway as tg


TPO = {
    "ib_high": 7520.0,
    "ib_low": 7480.0,
    "poc": 7505.0,
    "vah": 7527.5,
    "val": 7490.0,
    "ib_width": 40.0,
}


def _isolate_gates(monkeypatch):
    """Pin production-ON gates OFF (same set as test_gateway_block_reason_precise)."""
    for flag in (
        "DIRECTION_CONTEXT", "CONT_TREND_FILTER", "ZONE_LIMIT_ENTRY_V1",
        "LSMA_FLAT_GATE_V1", "DAYTYPE_POSITION_GATE", "RR_ENTRY_GATE_V1",
        "RISK_CONSECUTIVE_LOSS_LIMIT", "EOD_RISK_WINDOW_V1", "NEWS_BLACKOUT_V1",
        "OPENING_TYPE_GATE", "RISK_HALT_V1", "DAYTYPE_PLAYBOOK",
        "TARGET_ZONES_V1",
    ):
        monkeypatch.setenv(flag, "0")


class _TZBoom:
    """Force the gateway's IB-lock wall-clock probe into its fail-open branch
    (`except → _st_ib_locked=True`) so the structural block runs at any test
    hour. Only the gateway's in-function `from zoneinfo import ZoneInfo`
    resolves to this stub; gates that would also consult the clock are
    explicitly OFF via _isolate_gates."""
    def __init__(self, *a, **k):
        raise RuntimeError("test: force IB-locked fail-open")


def _gw(monkeypatch):
    _isolate_gates(monkeypatch)
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")
    monkeypatch.setattr(zoneinfo, "ZoneInfo", _TZBoom)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    monkeypatch.setattr(
        tg, "extract_g1_entry_context",
        lambda cc: {"day_type_at_entry": "Variation"},
    )
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: "REACTIVE_SHORT")
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": "Variation"},
            "woodies_system": {"trend_state": "RED"},
            "tpo_system": dict(TPO),
        },
    )
    return gw


def _setup():
    return {
        "direction": "SHORT",
        "classification": "REACTIVE_SHORT",
        "metadata": {"pattern": "REACTIVE_SHORT"},
        "entry_price": 7508.75,
        "stop": 7515.0,
        "t1": 7500.0,
    }


def test_route_flag_on_t1_pattern_t2t3_structural(monkeypatch):
    """Flag ON: t1 = pattern table (entry−9), t2/t3 = EXACTLY what the real
    structural resolver produced (immune to resolver-internal caps/monotonic
    reorder — e.g. POC gets promoted to C1 when the raw C1 is cap-clamped).

    Reference run: route once with a pattern that has NO targets.yaml row →
    the structural targets survive untouched. Then the real run must keep the
    same t2/t3 while t1 moves to the pattern value.
    """
    monkeypatch.setenv("T2T3_NO_STOMP_V1", "1")
    gw = _gw(monkeypatch)

    # Reference: pattern unknown to pattern_t1_points → no override at all.
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: "REACTIVE_SHORT")
    ref = _setup()
    ref["classification"] = "NO_SUCH_PATTERN"
    res_ref = gw.route_setup(ref, 2)
    assert res_ref.get("blocked_by") is None, f"unexpected block: {res_ref}"
    struct_t2, struct_t3 = ref["t2"], ref["t3"]
    assert struct_t2 is not None and struct_t3 is not None
    assert struct_t3 == 7490.0  # VAL — the Variation REV runner

    # Real run: REACTIVE_SHORT×Variation=9.0pt override + no-stomp flag.
    setup = _setup()
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    assert setup["t1"] == 7499.75          # entry − 9 (pattern table)
    assert setup["t2"] == struct_t2, f"t2 stomped: {setup['t2']} != structural {struct_t2}"
    assert setup["t3"] == struct_t3, f"t3 stomped: {setup['t3']} != structural {struct_t3}"


def test_route_flag_off_legacy_stomp(monkeypatch):
    """Flag OFF: byte-identical legacy — ×2/×3 overwrite the structural t2/t3."""
    monkeypatch.delenv("T2T3_NO_STOMP_V1", raising=False)
    gw = _gw(monkeypatch)
    setup = _setup()
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    assert setup["t1"] == 7499.75
    assert setup["t2"] == 7490.75          # entry − 2×9
    assert setup["t3"] == 7481.75          # entry − 3×9


def test_route_no_structural_falls_through(monkeypatch):
    """Flag ON but structural OFF → pattern table sets t1/t2/t3 as today."""
    monkeypatch.setenv("T2T3_NO_STOMP_V1", "1")
    gw = _gw(monkeypatch)
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "0")
    setup = _setup()
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    assert setup["t1"] == 7499.75
    assert setup["t2"] == 7490.75
    assert setup["t3"] == 7481.75
