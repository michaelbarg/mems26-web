"""Unit tests for scripts/verify_t17_e2e_4contract_sim.py."""
import json
from pathlib import Path

from scripts import verify_t17_e2e_4contract_sim as harness


def test_be_after_t1_passes_when_be_follows_t1():
    trade = {"id": 99, "quality": {"contracts": 4}, "direction": "LONG", "state": "PARTIAL"}
    export = Path("/tmp/unused")
    since = 0.0

    timeline = {
        "events": [
            {"ts": "2026-07-20T14:00:00+00:00", "type": "ENTRY_FILL", "detail": {}},
            {"ts": "2026-07-20T14:05:00+00:00", "type": "T1_HIT", "detail": {}},
            {"ts": "2026-07-20T14:05:01+00:00", "type": "MGMT_SMART_BE", "detail": {"stop": 7500}},
        ]
    }

    def fake_timeline(_tid):
        return timeline

    orig = harness._timeline
    harness._timeline = fake_timeline
    try:
        result = harness.verify_trade(trade, since_ts=since, export=export)
    finally:
        harness._timeline = orig

    result.finalize()
    assert any(c.name == "be_after_real_t1" and c.ok for c in result.checks)


def test_contracts_not_4_fails():
    trade = {"id": 1, "quality": {"contracts": 3}}
    result = harness.verify_trade(trade, since_ts=0.0, export=Path("/tmp/x"))
    result.finalize()
    assert result.verdict == "FAIL"
    assert any(c.name == "contracts_at_entry" and not c.ok for c in result.checks)


def test_main_indeterminate_without_trade(monkeypatch, capsys):
    monkeypatch.setattr(harness, "_find_latest_trade", lambda: None)
    code = harness.main(["--auto"])
    out = capsys.readouterr().out
    assert code == 2
    assert "INDETERMINATE" in out
