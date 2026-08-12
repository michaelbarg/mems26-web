"""F6 (2026-08-12) — gateway_decisions.jsonl rotates daily with archive.

The file grew unbounded since 2026-07-22 (1.5 MB) and every reader scanned all
of it. Contract: on the first append of a new UTC day the old file MOVES to
decisions_archive/gateway_decisions.<last-day>.jsonl (never deleted) and a
fresh file starts. Same-day appends never rotate.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.gateway.trading_gateway import TradingGateway  # noqa: E402


def _gw(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_DECISIONS_PATH",
                       str(tmp_path / "gateway_decisions.jsonl"))
    monkeypatch.delenv("GATEWAY_DECISIONS_HYDRATE", raising=False)
    return TradingGateway()


def test_yesterdays_file_archived_on_first_append(tmp_path, monkeypatch):
    p = tmp_path / "gateway_decisions.jsonl"
    p.write_text(json.dumps({"ts": "old-day", "verdict": "blocked"}) + "\n")
    old = time.time() - 86_400
    os.utime(p, (old, old))
    yesterday = datetime.fromtimestamp(old, tz=timezone.utc).strftime("%Y-%m-%d")

    gw = _gw(monkeypatch, tmp_path)
    gw._persist_decision({"ts": "today", "verdict": "PASSED"})

    arch = sorted((tmp_path / "decisions_archive").glob("gateway_decisions.*.jsonl"))
    assert len(arch) == 1, f"old file must be archived, got {arch}"
    assert yesterday in arch[0].name
    assert "old-day" in arch[0].read_text()
    lines = p.read_text().splitlines()
    assert len(lines) == 1 and "today" in lines[0], (
        "fresh file must hold ONLY the new day's decisions")

    # Second append the same day: no second rotation, plain append.
    gw._persist_decision({"ts": "today-2", "verdict": "blocked"})
    assert len(list((tmp_path / "decisions_archive").glob("*.jsonl"))) == 1
    assert len(p.read_text().splitlines()) == 2


def test_todays_file_is_never_rotated(tmp_path, monkeypatch):
    p = tmp_path / "gateway_decisions.jsonl"
    p.write_text(json.dumps({"ts": "earlier-today"}) + "\n")

    gw = _gw(monkeypatch, tmp_path)
    gw._persist_decision({"ts": "now"})

    assert not (tmp_path / "decisions_archive").exists(), (
        "a same-day file must not rotate")
    assert len(p.read_text().splitlines()) == 2


def test_rotation_never_clobbers_existing_archive(tmp_path, monkeypatch):
    p = tmp_path / "gateway_decisions.jsonl"
    old = time.time() - 86_400
    yesterday = datetime.fromtimestamp(old, tz=timezone.utc).strftime("%Y-%m-%d")
    arch_dir = tmp_path / "decisions_archive"
    arch_dir.mkdir()
    (arch_dir / f"gateway_decisions.{yesterday}.jsonl").write_text("keep-me\n")

    p.write_text(json.dumps({"ts": "old"}) + "\n")
    os.utime(p, (old, old))

    gw = _gw(monkeypatch, tmp_path)
    gw._persist_decision({"ts": "new"})

    files = sorted(f.name for f in arch_dir.glob("*.jsonl"))
    assert f"gateway_decisions.{yesterday}.jsonl" in files
    assert f"gateway_decisions.{yesterday}.1.jsonl" in files, files
    assert (arch_dir / f"gateway_decisions.{yesterday}.jsonl").read_text() == "keep-me\n"
