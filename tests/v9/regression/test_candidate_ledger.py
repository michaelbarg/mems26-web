"""T-103 Candidate Ledger — observability writer, flag default OFF."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from backend.v9.services import candidate_ledger as CL


@pytest.fixture(autouse=True)
def _reset_ledger(monkeypatch, tmp_path):
    CL.reset_seen()
    monkeypatch.setenv("GATEWAY_DECISIONS_PATH", str(tmp_path / "gateway_decisions.jsonl"))
    monkeypatch.setenv("MEMS26_TEST_MODE", "1")
    monkeypatch.delenv("CANDIDATE_LEDGER_V1", raising=False)
    yield
    CL.reset_seen()


def _lines(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_flag_off_writes_nothing(tmp_path):
    path = Path(os.environ["GATEWAY_DECISIONS_PATH"])
    cid = CL.record(
        "DETECTED",
        system_id=2,
        pattern="REACTIVE_LONG",
        direction="LONG",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    assert cid is None
    assert _lines(path) == []


def test_candidate_id_is_stable_across_pid_and_commit(monkeypatch):
    a = CL.make_candidate_id(
        system_id=2,
        pattern="REACTIVE_LONG",
        direction="LONG",
        signal_bar_ts="2026-08-18T13:47:12+00:00",
        variant_tag="A_VSA",
    )
    b = CL.make_candidate_id(
        system_id=2,
        pattern="REACTIVE_LONG",
        direction="long",
        signal_bar_ts="2026-08-18T13:49:59+00:00",
        variant_tag="A_VSA",
    )
    assert a == b
    assert len(a) == 64
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    cid = CL.record(
        "DETECTED",
        system_id=2,
        pattern="REACTIVE_LONG",
        direction="LONG",
        signal_bar_ts="2026-08-18T13:47:12+00:00",
        variant_tag="A_VSA",
    )
    assert cid == a


def test_detected_then_emit_reject_same_id(monkeypatch, tmp_path):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    path = Path(os.environ["GATEWAY_DECISIONS_PATH"])
    ts = "2026-08-18T14:00:00+00:00"
    cid = CL.record(
        "DETECTED",
        system_id=2,
        pattern="DOUBLE_BOTTOM_EE_LONG",
        direction="LONG",
        signal_bar_ts=ts,
        family="REV",
    )
    same = CL.record(
        "EMIT_DECISION",
        system_id=2,
        pattern="DOUBLE_BOTTOM_EE_LONG",
        direction="LONG",
        signal_bar_ts=ts,
        candidate_id=cid,
        verdict="REJECT",
        blocked_by="fhb",
    )
    rows = _lines(path)
    assert same == cid
    assert [r["event_type"] for r in rows] == ["DETECTED", "EMIT_DECISION"]
    assert all(r["candidate_id"] == cid for r in rows)
    assert rows[1]["decision"]["blocked_by"] == "fhb"
    assert "pid" in rows[0]["source"]
    assert rows[0]["source"]["code_commit"]


def test_same_bar_repush_does_not_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    path = Path(os.environ["GATEWAY_DECISIONS_PATH"])
    kwargs = dict(
        event_type="DETECTED",
        system_id=4,
        pattern="ZLR",
        direction="SHORT",
        signal_bar_ts="2026-08-18T15:10:00+00:00",
        family="CONTINUATION",
    )
    CL.record("DETECTED", **{k: v for k, v in kwargs.items() if k != "event_type"})
    CL.record("DETECTED", **{k: v for k, v in kwargs.items() if k != "event_type"})
    assert len(_lines(path)) == 1


def test_writer_exception_does_not_raise(monkeypatch):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    monkeypatch.setattr(CL, "_append_jsonl", lambda *_a, **_k: (_ for _ in ()).throw(OSError("disk")))
    cid = CL.record(
        "DETECTED",
        system_id=2,
        pattern="X",
        direction="LONG",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    assert cid is None


def test_pytest_refuses_live_export_path(monkeypatch, tmp_path):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    live = str(Path.home() / "SierraChart_Data/v9_export/gateway_decisions.jsonl")
    monkeypatch.setenv("GATEWAY_DECISIONS_PATH", live)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/v9/regression/test_candidate_ledger.py")
    before = Path(live).read_text() if Path(live).exists() else None
    CL.record(
        "DETECTED",
        system_id=2,
        pattern="REACTIVE_LONG",
        direction="LONG",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    after = Path(live).read_text() if Path(live).exists() else None
    assert after == before


def test_is_ui_decision_filters_detected():
    assert CL.is_ui_decision({"blocked_by": "playbook"}) is True
    assert CL.is_ui_decision({"event_type": "GATE_DECISION"}) is True
    assert CL.is_ui_decision({"event_type": "ROUTED"}) is True
    assert CL.is_ui_decision({"event_type": "DETECTED"}) is False
    assert CL.is_ui_decision({"event_type": "EMIT_DECISION"}) is False
    assert CL.is_ui_decision({"event_type": "RESOLVED"}) is False


def test_emit_skip_via_quality_tier(monkeypatch, tmp_path):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    monkeypatch.setenv("AUTH_LOWCONF_REDUCED_V1", "0")
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "0")
    monkeypatch.setattr(
        "backend.v9.systems.five_min.setup_emitter.get_quality_tier_v2",
        lambda *a, **k: ("SKIP", "LOW", 0),
    )
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup

    result = emit_t1_setup(
        "REACTIVE_LONG",
        "LONG",
        entry_price=7700.0,
        stop_price=7690.0,
        t1_price=7710.0,
        t2_price=7720.0,
        bar_index=10,
        day_type="Normal",
        candidate_id="cid-skip",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    assert result is None
    rows = _lines(Path(os.environ["GATEWAY_DECISIONS_PATH"]))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "EMIT_DECISION"
    assert rows[0]["candidate_id"] == "cid-skip"
    assert rows[0]["decision"]["blocked_by"] == "auth_skip"


def test_emit_survives_ledger_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("CANDIDATE_LEDGER_V1", "1")
    monkeypatch.setattr(
        "backend.v9.services.candidate_ledger.record",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ledger down")),
    )
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup

    result = emit_t1_setup(
        "REACTIVE_LONG",
        "LONG",
        entry_price=5250.0,
        stop_price=5248.0,
        t1_price=5252.0,
        t2_price=5254.0,
        bar_index=100,
        day_type="Variation",
        tpo_data={"poc": 5250.0, "vah": 5260.0, "val": 5240.0},
        candidate_id="should-not-matter",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    assert result is not None
    assert result.direction == "LONG"


def test_migration_024_rejects_remote_dsn():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m024",
        "backend/v9/db/migrations/versions/024_candidate_ledger_columns.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod._local_dsn("postgresql://localhost/mems26") is True
    assert mod._local_dsn("postgresql://127.0.0.1/mems26") is True
    assert mod._local_dsn("postgresql://evil.example/mems26") is False
    assert mod._local_dsn("postgresql://localhost/mems26?hostaddr=203.0.113.7") is False


def test_flag_off_emit_does_not_write(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.v9.systems.five_min.setup_emitter.get_quality_tier_v2",
        lambda *a, **k: ("SKIP", "LOW", 0),
    )
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup

    result = emit_t1_setup(
        "REACTIVE_LONG",
        "LONG",
        entry_price=7700.0,
        stop_price=7690.0,
        t1_price=7710.0,
        t2_price=7720.0,
        bar_index=10,
        day_type="Normal",
        candidate_id="cid-off",
        signal_bar_ts="2026-08-18T13:45:00+00:00",
    )
    assert result is None
    assert _lines(Path(os.environ["GATEWAY_DECISIONS_PATH"])) == []


# ── T-103B §3 blocker tests ──


def test_rotation_not_broken_by_ledger_write(monkeypatch, tmp_path):
    """§3a: ledger writing first on a new day must NOT prevent rotation."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    import json as _json
    # Simulate yesterday's file with a ts from yesterday
    decisions_path = tmp_path / "gateway_decisions.jsonl"
    yesterday_row = _json.dumps({
        "ts": "2026-08-17T14:30:00+00:00", "pattern": "ZLR", "blocked_by": None
    })
    decisions_path.write_text(yesterday_row + "\n")
    # The ledger appends a DETECTED event — this updates mtime to today
    ledger_row = _json.dumps({
        "event_type": "DETECTED", "observed_at": "2026-08-18T13:30:00+00:00",
        "candidate_id": "abc", "pattern": "REACTIVE_LONG",
    })
    with open(decisions_path, "a") as f:
        f.write(ledger_row + "\n")
    # Now try to rotate — the fix should read the first line's ts (yesterday)
    # and rotate despite the mtime being today
    gw = TradingGateway.__new__(TradingGateway)
    gw._decisions_path = decisions_path
    gw._decisions_rotated_day = None
    gw._rotate_decisions_if_new_day()
    # After rotation, the file should be gone (renamed to archive)
    arch = tmp_path / "decisions_archive"
    assert arch.exists() or not decisions_path.exists() or \
        decisions_path.read_text().strip() == "", \
        "rotation should have moved yesterday's file"


def test_radar_window_not_swallowed_by_detected(tmp_path):
    """§3b: 200 DETECTED events must not hide an awaiting_release decision."""
    import json as _json
    from backend.v9.api.v9.context_radar import _is_gate_line
    # A gate decision line
    gate_line = _json.dumps({
        "ts": "2026-08-18T14:00:00+00:00",
        "blocked_by": "awaiting_release",
        "reason": "zone not released",
    })
    # A detected line
    detected_line = _json.dumps({
        "event_type": "DETECTED",
        "candidate_id": "abc",
        "pattern": "ZLR",
    })
    assert _is_gate_line(gate_line) is True
    assert _is_gate_line(detected_line) is False
    # 200 DETECTED + 1 gate → filter must preserve the gate
    all_lines = [detected_line] * 200 + [gate_line]
    filtered = [ln for ln in all_lines if _is_gate_line(ln)]
    assert len(filtered) == 1
    assert "awaiting_release" in filtered[0]
