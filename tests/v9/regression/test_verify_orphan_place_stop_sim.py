"""Unit tests for scripts/verify_orphan_place_stop_sim.py (read-only sim harness)."""
import json
import time
from pathlib import Path

from scripts import verify_orphan_place_stop_sim as harness


def _write_state(export: Path, **fields):
    payload = {
        "position_qty": -2,
        "avg_price": 7513.75,
        "working_orders": 0,
        "is_sim": 1,
        "last_price": 7512.0,
    }
    payload.update(fields)
    (export / "sierra_state.json").write_text(json.dumps(payload))


def test_hold_passes_with_virtual_stop_doctrine(tmp_path, monkeypatch):
    export = tmp_path / "export"
    export.mkdir()
    _write_state(export)
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(export))
    log_dir = tmp_path / "docs" / "reports"
    log_dir.mkdir(parents=True)
    monkeypatch.setattr(harness, "ROOT", str(tmp_path))
    log_dir.joinpath("OPS_LOG_2026-07-20.md").write_text(
        "[2026-07-20T12:00:00-04:00] [reconciler] [WARNING] ORPHAN VIRTUAL STOP SET: SHORT stop @ 7523.75\n"
    )

    result = harness.verify_hold(
        json.loads((export / "sierra_state.json").read_text()),
        baseline_qty=2,
        since_ts=time.time() - 60,
        export=export,
    )
    result.finalize()

    assert result.verdict == "PASS"
    names = {c.name for c in result.checks if c.ok}
    assert "no_resting_stop_required" in names
    assert "no_place_stop_ok" in names
    assert "virtual_stop_evidence" in names


def test_hold_fails_if_place_stop_ok_present(tmp_path, monkeypatch):
    export = tmp_path / "export"
    export.mkdir()
    _write_state(export)
    (export / "trade_result.json").write_text(json.dumps({"status": "PLACE_STOP_OK"}))
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(export))
    monkeypatch.setattr(harness, "ROOT", str(tmp_path))

    result = harness.verify_hold(
        json.loads((export / "sierra_state.json").read_text()),
        baseline_qty=2,
        since_ts=time.time() - 60,
        export=export,
    )
    result.finalize()

    assert result.verdict == "FAIL"
    assert any(c.name == "no_place_stop_ok" and not c.ok for c in result.checks)


def test_flatten_passes_on_flatten_orphan_ok(tmp_path, monkeypatch):
    export = tmp_path / "export"
    export.mkdir()
    _write_state(export, position_qty=0)
    (export / "trade_result.json").write_text(json.dumps({"status": "FLATTEN_ORPHAN_OK"}))
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(export))
    monkeypatch.setattr(harness, "ROOT", str(tmp_path))
    log_dir = tmp_path / "docs" / "reports"
    log_dir.mkdir(parents=True)
    log_dir.joinpath("OPS_LOG_2026-07-20.md").write_text(
        "[2026-07-20T12:05:00-04:00] [reconciler] [CRITICAL] ORPHAN FLATTENED: STOP_CROSSED → FLATTEN_ORPHAN_OK\n"
    )

    result = harness.verify_flatten(
        json.loads((export / "sierra_state.json").read_text()),
        since_ts=time.time() - 60,
        export=export,
    )
    result.finalize()

    assert result.verdict == "PASS"
    assert any(c.name == "qty_zero" and c.ok for c in result.checks)
    assert any(c.name == "flatten_orphan_ok" and c.ok for c in result.checks)


def test_main_auto_indeterminate_when_flat(tmp_path, monkeypatch, capsys):
    export = tmp_path / "export"
    export.mkdir()
    _write_state(export, position_qty=0)
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(export))

    code = harness.main(["--export-dir", str(export), "--since", "120"])
    out = capsys.readouterr().out

    assert code == 2
    assert "INDETERMINATE" in out
    assert "create orphan in sim first" in out


def test_main_auto_infers_flatten(tmp_path, monkeypatch, capsys):
    export = tmp_path / "export"
    export.mkdir()
    _write_state(export, position_qty=0)
    (export / "trade_result.json").write_text(json.dumps({"status": "FLATTEN_ORPHAN_OK"}))
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(export))
    monkeypatch.setattr(harness, "ROOT", str(tmp_path))
    log_dir = tmp_path / "docs" / "reports"
    log_dir.mkdir(parents=True)
    log_dir.joinpath("OPS_LOG_2026-07-20.md").write_text(
        "[2026-07-20T12:05:00-04:00] [reconciler] [CRITICAL] ORPHAN FLATTENED\n"
    )

    code = harness.main(["--export-dir", str(export), "--since", "120"])
    out = capsys.readouterr().out

    assert code == 0
    assert "phase=flatten" in out
    assert "FLATTEN_ORPHAN_OK" in out
