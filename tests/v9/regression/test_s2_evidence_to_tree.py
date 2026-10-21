"""T-543 stage 4 — S2 evidence (vol_trig / delta_with) → the decision-tree vector, behind
S2_EVIDENCE_TO_TREE_V1 (default OFF).

CC_ORDER_2026-10-05_DAILY_DALTON §4 row 4: "the identity test on a vector without metadata —
fails if the vector changed without the flag". These tests call the REAL production helpers:
five_min_system.build_s2_gateway_setup (the one the fire site uses) and
decision_tree.features_of_setup (the one the gateway uses to build the vector the tree walks).

Litmus (anti-tautological):
- copy made unconditional (flag ignored)      → test_flag_off_is_byte_identical RED.
- copy never made / wrong key names           → test_flag_on_fills_volume_and_delta RED.
- None ("unknown") copied as a key            → test_flag_on_unknown_evidence_stays_absent RED.
- anything else in the setup touched when ON  → test_only_the_two_keys_change_when_on RED.
"""
import json
from datetime import datetime, timezone

import pytest

from backend.v9.services.decision_tree import features_of_setup
from backend.v9.systems.five_min.five_min_system import build_s2_gateway_setup
from backend.v9.systems.five_min.output_schema import T1Setup

FLAG = "S2_EVIDENCE_TO_TREE_V1"


def _t1():
    return T1Setup(pattern_name="REACTIVE_SHORT", direction="SHORT", entry_price=7811.0,
                   stop_price=7816.5, t1_price=7800.0, t2_price=7790.0, t3_price=None,
                   confidence=75, bar_index=10, fired_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
                   sizing_contracts=1)


def _info(vol_trig=True, delta_with=True):
    """What _detect_reactive / _detect_initiative return as `info` (evidence after the geometry passed)."""
    return {"variant": "A_VSA", "structural_anchor": 7816.0,
            "evidence": {"trigger": {"ok": True, "cp": 0.2}, "vol_trig": vol_trig,
                         "delta_with": delta_with, "location": {"zone": "near_vah"},
                         "absorption": False}}


def _no_evidence():
    return {k: v for k, v in _info().items() if k != "evidence"}


def _vec(setup):
    return features_of_setup(setup, opening_type="OPEN_AUCTION_IN", phase="C", day_type="Variation",
                             structure="up", dir_hint="SHORT", zone="near_vah", kind="REVERSAL",
                             atr=None, hour=19)


def _dump(d):
    return json.dumps(d, sort_keys=True, default=str)


@pytest.mark.parametrize("val", [None, "", "0", "false", "no", "off"])
def test_flag_off_is_byte_identical(monkeypatch, val):
    if val is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, val)
    with_ev = build_s2_gateway_setup(_t1(), _info())
    without_ev = build_s2_gateway_setup(_t1(), _no_evidence())
    assert _dump(with_ev) == _dump(without_ev)                      # the setup dict
    assert "vol_trig" not in with_ev["metadata"]
    assert "delta_with" not in with_ev["metadata"]
    vec = _vec(with_ev)
    assert (vec["volume"], vec["delta"]) == ("normal", "none")      # today's vector
    assert _dump(vec) == _dump(_vec(without_ev))


def test_flag_on_fills_volume_and_delta(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    s = build_s2_gateway_setup(_t1(), _info(vol_trig=True, delta_with=True))
    assert s["metadata"]["vol_trig"] is True
    assert s["metadata"]["delta_with"] is True
    vec = _vec(s)
    assert (vec["volume"], vec["delta"]) == ("high", "with")
    s_no = build_s2_gateway_setup(_t1(), _info(vol_trig=False, delta_with=False))
    assert s_no["metadata"]["vol_trig"] is False
    assert s_no["metadata"]["delta_with"] is False
    assert (_vec(s_no)["volume"], _vec(s_no)["delta"]) == ("normal", "none")


def test_flag_on_unknown_evidence_stays_absent(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    s = build_s2_gateway_setup(_t1(), _info(vol_trig=None, delta_with=None))   # unknown ⇒ absent
    assert "vol_trig" not in s["metadata"] and "delta_with" not in s["metadata"]
    s_empty = build_s2_gateway_setup(_t1(), {"variant": "A_VSA", "evidence": {}})  # evidence failed ⇒ {}
    assert "vol_trig" not in s_empty["metadata"] and "delta_with" not in s_empty["metadata"]
    s_none = build_s2_gateway_setup(_t1(), _no_evidence())                       # detector w/o evidence
    assert "vol_trig" not in s_none["metadata"] and "delta_with" not in s_none["metadata"]


def test_only_the_two_keys_change_when_on(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    off = build_s2_gateway_setup(_t1(), _info())
    monkeypatch.setenv(FLAG, "1")
    on = build_s2_gateway_setup(_t1(), _info())
    on_meta = dict(on["metadata"])
    on_meta.pop("vol_trig")
    on_meta.pop("delta_with")
    assert _dump({**on, "metadata": on_meta}) == _dump(off)
    v_off, v_on = _vec(off), _vec(on)
    assert {k for k in v_on if v_on[k] != v_off[k]} == {"volume", "delta"}
