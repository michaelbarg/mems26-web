"""Anti-tautological test: /trades/{id}/exit MUST flatten Sierra before closing.

Trade 318 incident (07-09): exit closed the DB record + freed slot but left the
Sierra position open. These tests verify _flatten_sierra_position behavior.
Old code (without the function) would fail tests 3+4: it never called write_cancel.
"""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

# trades module imports auth which requires BRIDGE_TOKEN at import time
if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.api.v9.trades import _flatten_sierra_position


class FakeTrade:
    def __init__(self, trade_id=1, mode="demo", sierra_order_id=8467):
        self.id = trade_id
        self.mode = mode
        self._sierra_order_id = sierra_order_id


class FakeTM:
    def _get_sierra_order_id(self, trade):
        return trade._sierra_order_id


def test_shadow_skipped():
    """Shadow trades have no Sierra position — flatten returns True immediately."""
    trade = FakeTrade(mode="shadow", sierra_order_id=8467)
    assert _flatten_sierra_position(trade, FakeTM(), None) is True


def test_no_sierra_id_skipped():
    """Trade without sierra_order_id (never acked) — returns True, no CANCEL."""
    trade = FakeTrade(mode="live", sierra_order_id=None)
    assert _flatten_sierra_position(trade, FakeTM(), None) is True


def test_demo_with_id_sends_cancel():
    """Demo trade with sierra_order_id MUST call write_cancel (anti-tautological)."""
    trade = FakeTrade(mode="demo", sierra_order_id=8467)
    # Create a temp result file that simulates Sierra ack
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"status": "CANCEL_OK", "ts": 1234}, f)
        ack_path = f.name
    try:
        with patch("backend.v9.services.sierra_command._write_command", return_value={"op": "CANCEL"}) as mock_cmd:
            # Write ack to the real result path
            result_path = "/Users/michael/SierraChart_Data/v9_export/trade_result.json"
            rp_backup = None
            if os.path.exists(result_path):
                with open(result_path) as f:
                    rp_backup = f.read()
            with open(result_path, "w") as f:
                json.dump({"status": "CANCEL_OK", "ts": 1234}, f)
            try:
                result = _flatten_sierra_position(trade, FakeTM(), None)
                assert mock_cmd.called, "write_cancel must send CANCEL for demo trade with sierra_order_id"
                assert result is True
            finally:
                with open(result_path, "w") as f:
                    f.write(rp_backup if rp_backup else "")
    finally:
        os.unlink(ack_path)


def test_live_sends_cancel_and_waits():
    """Live trade sends CANCEL; returns True only on ack (CANCEL_OK)."""
    trade = FakeTrade(mode="live", sierra_order_id=8500)
    cancel_calls = []

    with patch("backend.v9.services.sierra_command._write_command") as mock_cmd:
        mock_cmd.return_value = {"op": "CANCEL"}

        # Write ack file to the actual result path before calling
        result_path = "/Users/michael/SierraChart_Data/v9_export/trade_result.json"
        backup = None
        if os.path.exists(result_path):
            with open(result_path) as f:
                backup = f.read()
        with open(result_path, "w") as f:
            json.dump({"status": "CANCEL_OK", "ts": 9999}, f)

        try:
            result = _flatten_sierra_position(trade, FakeTM(), None)
            assert result is True, "Must return True when Sierra acks CANCEL_OK"
            assert mock_cmd.called, "Must have called _write_command (via write_cancel)"
            cmd = mock_cmd.call_args[0][0]
            assert cmd["op"] == "CANCEL"
            assert cmd["order_id"] == 8500
        finally:
            # Restore original file
            if backup is not None:
                with open(result_path, "w") as f:
                    f.write(backup)
            else:
                with open(result_path, "w") as f:
                    pass  # empty


def test_no_ack_returns_false():
    """No Sierra ack within timeout → returns False (CRITICAL, don't close)."""
    trade = FakeTrade(mode="live", sierra_order_id=8500)

    with patch("backend.v9.services.sierra_command._write_command", return_value={"op": "CANCEL"}):
        # Write empty/non-matching result
        result_path = "/Users/michael/SierraChart_Data/v9_export/trade_result.json"
        backup = None
        if os.path.exists(result_path):
            with open(result_path) as f:
                backup = f.read()
        with open(result_path, "w") as f:
            json.dump({"status": "ORDER_SUBMITTED", "ts": 1}, f)

        try:
            # Mock time to expire quickly
            import time as time_mod
            real_time = time_mod.time
            call_count = [0]

            def fast_time():
                call_count[0] += 1
                return real_time() + (call_count[0] * 6.0)  # jump past 5s deadline

            with patch("time.time", side_effect=fast_time), \
                 patch("time.sleep"):
                result = _flatten_sierra_position(trade, FakeTM(), None)
            assert result is False, "Must return False when Sierra doesn't ack CANCEL"
        finally:
            if backup is not None:
                with open(result_path, "w") as f:
                    f.write(backup)
            else:
                with open(result_path, "w") as f:
                    pass
