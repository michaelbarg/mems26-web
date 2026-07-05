"""System 6 decision journal — pure core (build_record + hit-rates)."""
import json

from backend.v9.systems.system6_journal import build_record, compute_hit_rates


def test_build_record_shape():
    r = build_record(trade_id=291, signal_kind="stall", score=0.6, fired=True,
                     recommendation="consider_exit", context={"bars_since": 3})
    assert r["trade_id"] == 291 and r["signal_kind"] == "stall"
    assert r["fired"] is True and r["decision"] == "pending"
    assert json.loads(r["context_json"]) == {"bars_since": 3}


def test_hit_rates_ignore_undecided():
    rows = [
        {"signal_kind": "stall", "fired": True, "outcome_helped": True},
        {"signal_kind": "stall", "fired": True, "outcome_helped": False},
        {"signal_kind": "stall", "fired": True, "outcome_helped": None},   # pending
    ]
    hr = compute_hit_rates(rows)
    assert hr["stall"]["n"] == 3 and hr["stall"]["fired"] == 3
    assert hr["stall"]["decided"] == 2 and hr["stall"]["helped"] == 1
    assert hr["stall"]["hit_rate"] == 0.5


def test_hit_rates_none_when_no_outcomes():
    rows = [{"signal_kind": "opposite_patterns", "fired": True, "outcome_helped": None}]
    hr = compute_hit_rates(rows)
    assert hr["opposite_patterns"]["hit_rate"] is None


def test_hit_rates_multi_signal():
    rows = [
        {"signal_kind": "stall", "fired": True, "outcome_helped": True},
        {"signal_kind": "counter_flow", "fired": True, "outcome_helped": False},
        {"signal_kind": "counter_flow", "fired": False, "outcome_helped": None},
    ]
    hr = compute_hit_rates(rows)
    assert hr["stall"]["hit_rate"] == 1.0
    assert hr["counter_flow"]["hit_rate"] == 0.0
    assert hr["counter_flow"]["fired"] == 1  # one fired, one not
