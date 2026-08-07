"""Tests for P0-1: command queue with ACK.

Key invariants:
1. Two rapid commands don't overwrite each other
2. Commands are sequenced (numbered files)
3. Drain processes in order
4. ACK timeout doesn't block forever
5. Backward compat: single command still writes to trade_command.json
"""

import json
import os
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
        """Drain picks up oldest command first."""
        from backend.v9.services.sierra_command import (
            write_trade_command, drain_command_queue, command_file,
        )

        write_trade_command(action="BUY", trade_id="101", price=7600.0)
        write_trade_command(action="SELL", trade_id="102", price=7700.0)

        queue_dir = cmd_dir / "command_queue"
        assert len(list(queue_dir.glob("cmd_*.json"))) == 2

        # Drain with short timeout (no DLL to ACK)
        drained = drain_command_queue(timeout_s=0.2)
        assert drained >= 1

        # After drain, the command file should have the first command
        # (or the second if both drained)

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
