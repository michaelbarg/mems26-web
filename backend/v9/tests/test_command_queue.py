"""Tests for P0-1: command queue with ACK.

Key invariants:
1. Two rapid commands don't overwrite each other
2. Commands are sequenced (numbered files)
3. Drain processes in order
4. ACK timeout doesn't block forever
5. Backward compat: single command still writes to trade_command.json

K1 (2026-08-08) protocol invariants — the queue jam that blocked Friday's
PLACE #652 + CANCEL:
6. A fast-pathed (already sent) command is NEVER re-sent by the drainer
7. An in-flight (sent, un-ACKed) head blocks the queue — never overwritten
8. A stale unsent command (> SIERRA_CMD_TTL_S) is archived, NEVER sent
9. Two rapid commands both reach the DLL file sequentially under ACK simulation
10. The sequence counter resumes from disk after a backend restart
11. PLACE with effective contracts <= 0 is refused at the choke point (#652)
"""

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def cmd_dir(tmp_path, monkeypatch):
    """Point sierra_command at a temp dir."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    # Reset the module's global sequence counter
    import backend.v9.services.sierra_command as sc
    sc._cmd_seq = 0
    return tmp_path


def _ack(cmd_dir, delay_s: float = 0.05):
    """Simulate the DLL ACK: trade_result.json mtime moves past the send ts."""
    time.sleep(delay_s)
    (cmd_dir / "trade_result.json").write_text(
        json.dumps({"status": "ORDER_SUBMITTED", "ts": time.time()}))


class TestCommandQueue:

    def test_single_command_writes_directly(self, cmd_dir):
        """Single command writes to both queue + trade_command.json."""
        from backend.v9.services.sierra_command import write_trade_command, command_file
        write_trade_command(action="BUY", trade_id="100", price=7600.0)

        # trade_command.json should exist
        assert command_file().exists()
        payload = json.loads(command_file().read_text())
        assert payload["action"] == "BUY"
        assert payload["_seq"] == 1

        # Queue file should exist
        queue_dir = cmd_dir / "command_queue"
        assert queue_dir.exists()
        queue_files = list(queue_dir.glob("cmd_*.json"))
        assert len(queue_files) == 1

    def test_two_rapid_commands_not_overwritten(self, cmd_dir):
        """Two commands in rapid succession: both preserved in queue."""
        from backend.v9.services.sierra_command import write_modify_stop, write_trade_command

        # Command 1: MODIFY_STOP
        write_modify_stop(trade_id="100", order_id=5001, new_stop=7595.0)

        # Command 2: immediately after — would overwrite in old system
        write_trade_command(action="MODIFY", trade_id="100", target_price=7610.0)

        queue_dir = cmd_dir / "command_queue"
        queue_files = sorted(queue_dir.glob("cmd_*.json"))
        assert len(queue_files) == 2, "Both commands must be preserved"

        # Verify they're different commands
        p1 = json.loads(queue_files[0].read_text())
        p2 = json.loads(queue_files[1].read_text())
        assert p1["op"] == "MODIFY_STOP"
        assert p2["op"] == "PLACE"  # write_trade_command uses op=PLACE
        assert p1["_seq"] < p2["_seq"]

    def test_drain_processes_in_order(self, cmd_dir):
        """Drain picks up oldest command first, gated on the DLL ACK."""
        from backend.v9.services.sierra_command import (
            write_trade_command, drain_command_queue, command_file,
        )

        write_trade_command(action="BUY", trade_id="101", price=7600.0)   # fast-pathed
        write_trade_command(action="SELL", trade_id="102", price=7700.0)  # queued

        queue_dir = cmd_dir / "command_queue"
        assert len(list(queue_dir.glob("cmd_*.json"))) == 2
        # The live file holds command 1 (fast path)
        assert json.loads(command_file().read_text())["_seq"] == 1

        # ACK command 1 → drain removes it and sends command 2
        _ack(cmd_dir)
        drained = drain_command_queue(timeout_s=0.2)
        assert drained == 1
        assert json.loads(command_file().read_text())["_seq"] == 2
        remaining = list(queue_dir.glob("cmd_*.json"))
        assert len(remaining) == 1 and remaining[0].name == "cmd_000002.json"

        # ACK command 2 → queue empties
        _ack(cmd_dir)
        drained = drain_command_queue(timeout_s=0.2)
        assert drained == 1
        assert list(queue_dir.glob("cmd_*.json")) == []

    def test_drain_timeout_doesnt_block(self, cmd_dir):
        """Drain with no ACK completes within timeout."""
        from backend.v9.services.sierra_command import write_trade_command, drain_command_queue

        write_trade_command(action="BUY", trade_id="103", price=7600.0)

        start = time.monotonic()
        drain_command_queue(timeout_s=0.3)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"Drain took {elapsed:.1f}s — should be ~0.3s"

    def test_sequence_numbers_increment(self, cmd_dir):
        """Each command gets a unique, incrementing sequence number."""
        from backend.v9.services.sierra_command import write_trade_command

        for i in range(5):
            write_trade_command(action="BUY", trade_id=str(i))

        queue_dir = cmd_dir / "command_queue"
        files = sorted(queue_dir.glob("cmd_*.json"))
        assert len(files) == 5

        seqs = [json.loads(f.read_text())["_seq"] for f in files]
        assert seqs == [1, 2, 3, 4, 5]

    def test_concurrent_commands_thread_safe(self, cmd_dir):
        """Commands from multiple threads don't corrupt each other."""
        import threading
        from backend.v9.services.sierra_command import write_trade_command

        results = []

        def write_cmd(idx):
            try:
                write_trade_command(action="BUY", trade_id=str(idx))
                results.append(idx)
            except Exception as e:
                results.append(f"error:{e}")

        threads = [threading.Thread(target=write_cmd, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        queue_dir = cmd_dir / "command_queue"
        files = list(queue_dir.glob("cmd_*.json"))
        assert len(files) == 10, f"Expected 10 files, got {len(files)}"
        assert len(results) == 10

    # ── K1 (2026-08-08) protocol tests ──────────────────────────────────

    def test_two_rapid_commands_reach_dll_sequentially(self, cmd_dir):
        """K1d integration: two rapid commands + a DLL simulator (ACK + clear,
        like MES_AI_DataExport_merged.cpp:3654-3661) → BOTH land in the
        DLL-format file, in _seq order, and the queue fully drains."""
        from backend.v9.services.sierra_command import (
            write_trade_command, write_modify_stop, drain_command_queue,
            command_file, pending_command_count,
        )

        observed = []
        stop_evt = threading.Event()

        def dll_simulator():
            last = ""
            while not stop_evt.is_set():
                try:
                    if command_file().exists():
                        content = command_file().read_text()
                        if len(content) > 10 and content != last:
                            observed.append(json.loads(content))
                            last = content
                            time.sleep(0.02)
                            (cmd_dir / "trade_result.json").write_text(
                                json.dumps({"status": "ORDER_SUBMITTED",
                                            "ts": time.time()}))
                            command_file().write_text("")  # DLL clears after processing
                except (OSError, ValueError):
                    pass
                time.sleep(0.02)

        sim = threading.Thread(target=dll_simulator, daemon=True)
        sim.start()
        try:
            # Rapid succession — the Friday shape (PLACE then MODIFY)
            write_trade_command(action="BUY", trade_id="801", price=7600.0,
                                contracts=3, stop_price=7594.0, target_price=7606.0)
            write_modify_stop(trade_id="801", order_id=9001, new_stop=7598.0)

            # Host-loop shape: repeated drain ticks until the queue is empty
            deadline = time.time() + 5.0
            while pending_command_count() > 0 and time.time() < deadline:
                drain_command_queue(timeout_s=1.0)
                time.sleep(0.02)
        finally:
            stop_evt.set()
            sim.join(timeout=2)

        assert pending_command_count() == 0, "queue must fully drain"
        assert len(observed) == 2, f"DLL must see BOTH commands, saw {len(observed)}"
        assert [p["_seq"] for p in observed] == [1, 2], "sequential order required"
        # DLL-format fields present (op-path contract)
        assert observed[0]["op"] == "PLACE" and observed[0]["contracts"] == 3
        assert observed[1]["op"] == "MODIFY_STOP" and observed[1]["new_stop"] == 7598.0

    def test_fastpathed_command_never_resent(self, cmd_dir):
        """Invariant 6: after the DLL processed + cleared a fast-pathed command,
        the drainer must only ACK-track it — re-writing it would double-place
        (the DLL op-path has no dedup)."""
        from backend.v9.services.sierra_command import (
            write_trade_command, drain_command_queue, command_file,
        )
        write_trade_command(action="BUY", trade_id="810", price=7600.0)
        command_file().write_text("")  # DLL processed + cleared
        _ack(cmd_dir)                  # DLL ACKed
        drained = drain_command_queue(timeout_s=0.2)
        assert drained == 1
        assert command_file().read_text() == "", \
            "drainer re-sent an already-executed command (double-place risk)"
        assert list((cmd_dir / "command_queue").glob("cmd_*.json")) == []

    def test_inflight_head_blocks_queue(self, cmd_dir):
        """Invariant 7: a sent, un-ACKed head (within grace) must hold the
        queue — the drainer may not overwrite the in-flight command."""
        from backend.v9.services.sierra_command import (
            write_trade_command, drain_command_queue, command_file,
        )
        write_trade_command(action="BUY", trade_id="820", price=7600.0)   # sent
        write_trade_command(action="SELL", trade_id="821", price=7590.0)  # queued
        drained = drain_command_queue(timeout_s=0.1)  # no ACK anywhere
        assert drained == 0
        assert json.loads(command_file().read_text())["trade_id"] == "820"
        assert len(list((cmd_dir / "command_queue").glob("cmd_*.json"))) == 2

    def test_stale_unsent_command_archived_not_sent(self, cmd_dir):
        """Invariant 8 — the Friday hazard: a stale queued command (PLACE/CANCEL
        from hours ago) must be archived, never written to the DLL file."""
        from backend.v9.services.sierra_command import (
            write_trade_command, drain_command_queue, command_file,
        )
        write_trade_command(action="BUY", trade_id="830", price=7600.0)   # fast-pathed
        write_trade_command(action="SELL", trade_id="831", price=7590.0)  # queued

        queue_dir = cmd_dir / "command_queue"
        stale = queue_dir / "cmd_000002.json"
        payload = json.loads(stale.read_text())
        payload["_ts_queued"] = time.time() - 3600  # Friday-class staleness
        stale.write_text(json.dumps(payload))

        _ack(cmd_dir)  # ACK for the fast-pathed head
        drained = drain_command_queue(timeout_s=0.2)
        assert drained == 2  # head ACK-removed + stale archived
        assert list(queue_dir.glob("cmd_*.json")) == []
        archived = queue_dir / "archived_stale" / "cmd_000002.json"
        assert archived.exists(), "stale command must be archived"
        # The DLL file was NEVER given the stale command
        live = command_file().read_text()
        assert json.loads(live)["trade_id"] == "830"

    def test_seq_resumes_from_disk_after_restart(self, cmd_dir):
        """Invariant 10: a fresh process (_cmd_seq=0) must continue the on-disk
        numbering — cmd_000001.json from the previous run must not be
        overwritten by the next command."""
        from backend.v9.services.sierra_command import write_trade_command
        queue_dir = cmd_dir / "command_queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        leftover = queue_dir / "cmd_000007.json"
        leftover.write_text(json.dumps({"op": "PLACE", "trade_id": "old", "_seq": 7}))

        write_trade_command(action="BUY", trade_id="840", price=7600.0)

        assert (queue_dir / "cmd_000008.json").exists()
        assert json.loads(leftover.read_text())["trade_id"] == "old", \
            "restart must not clobber a leftover queue file"

    def test_place_zero_contracts_refused(self, cmd_dir, monkeypatch):
        """Invariant 11 (#652): a PLACE whose effective contracts collapse to 0
        (margin cap / explicit SKIP) must raise — never reach the queue or the
        DLL file (the deployed DLL defaults contracts<=0 → 3 REAL contracts)."""
        import backend.v9.services.sierra_command as sc
        setup = {"direction": "SHORT", "entry_price": 7767.0, "stop": 7772.25,
                 "t1": 7763.5, "classification": "GHOST", "contracts": 2}

        monkeypatch.setattr(sc, "effective_contracts", lambda s: 0)
        with pytest.raises(ValueError, match="contracts=0"):
            sc.command_from_setup(setup, trade_id="900", account="X", mode="live")
        assert list((cmd_dir / "command_queue").glob("cmd_*.json")) == []
        assert not sc.command_file().exists()

    def test_place_explicit_skip_zero_refused_real_chain(self, cmd_dir, monkeypatch):
        """Same invariant through the REAL sizing chain: explicit contracts=0
        (a SKIP) under SIZE_CAP_OVER_FIXED_V1 stays 0 → PLACE refused."""
        from backend.v9.services.sierra_command import command_from_setup
        monkeypatch.setenv("SIZE_CAP_OVER_FIXED_V1", "1")
        setup = {"direction": "SHORT", "entry_price": 7767.0, "stop": 7772.25,
                 "t1": 7763.5, "classification": "GHOST", "contracts": 0}
        with pytest.raises(ValueError, match="contracts=0"):
            command_from_setup(setup, trade_id="901", account="X", mode="live")
        assert list((cmd_dir / "command_queue").glob("cmd_*.json")) == []
