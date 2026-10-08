# -*- coding: utf-8 -*-
"""T-567b (08.10): ELQ_PHASE_B_EXEMPT_V1 — a tree TAKE in phase B is exempt from entry_location_quality;
flag OFF = byte-identical behaviour (never exempt); never in phase A/C/D; never on SKIP/SHADOW leaves."""
import os
import pytest
from backend.v9.gateway.trading_gateway import _elq_phase_b_exempt

T3V_B = {"mode": "on", "leaf": "TAKE", "id": "auction_B_reversal",
         "path": "hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=REVERSAL"}


def test_flag_off_never_exempts(monkeypatch):
    monkeypatch.delenv("ELQ_PHASE_B_EXEMPT_V1", raising=False)
    assert _elq_phase_b_exempt(T3V_B) is False
    monkeypatch.setenv("ELQ_PHASE_B_EXEMPT_V1", "0")
    assert _elq_phase_b_exempt(T3V_B) is False


def test_flag_on_phase_b_take_exempt(monkeypatch):
    monkeypatch.setenv("ELQ_PHASE_B_EXEMPT_V1", "1")
    assert _elq_phase_b_exempt(T3V_B) is True


@pytest.mark.parametrize("phase", ["A", "C", "D"])
def test_other_phases_never_exempt(monkeypatch, phase):
    monkeypatch.setenv("ELQ_PHASE_B_EXEMPT_V1", "1")
    t = dict(T3V_B, path=T3V_B["path"].replace("phase=B", f"phase={phase}"))
    assert _elq_phase_b_exempt(t) is False


def test_skip_or_shadow_leaf_never_exempt(monkeypatch):
    monkeypatch.setenv("ELQ_PHASE_B_EXEMPT_V1", "1")
    assert _elq_phase_b_exempt(dict(T3V_B, leaf="SKIP")) is False
    assert _elq_phase_b_exempt(dict(T3V_B, leaf="SHADOW")) is False
    assert _elq_phase_b_exempt(dict(T3V_B, mode="shadow")) is False


def test_malformed_input_fail_closed(monkeypatch):
    monkeypatch.setenv("ELQ_PHASE_B_EXEMPT_V1", "1")
    assert _elq_phase_b_exempt(None) is False
    assert _elq_phase_b_exempt({}) is False
    assert _elq_phase_b_exempt({"mode": "on", "leaf": "TAKE", "path": "phase=BB"}) is False
