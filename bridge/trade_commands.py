"""TradeCommandHandler — file-based trade command/result communication with Sierra DLL.

Protocol:
  1. Backend writes trade_command.json (via API endpoint)
  2. Bridge (this module) reads it, validates, writes to SC_COMMAND_PATH for DLL
  3. DLL reads command, executes, writes result to SC_RESULT_PATH
  4. Bridge reads result, writes trade_result.json for backend
  5. sha256 checksum on command files for integrity

File paths:
  - trade_command.json:  /tmp/mems26_signals/trade_command.json (backend -> bridge)
  - trade_result.json:   /tmp/mems26_signals/trade_result.json  (bridge -> backend)
  - SC command:          V9_EXPORT_DIR/../trade_command.json     (bridge -> DLL)
  - SC result:           V9_EXPORT_DIR/../trade_result.json      (DLL -> bridge)
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("v9_bridge")

SIGNALS_DIR = Path("/tmp/mems26_signals")
COMMAND_FILE = SIGNALS_DIR / "trade_command.json"
RESULT_FILE = SIGNALS_DIR / "trade_result.json"

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
SC_COMMAND_PATH = Path(EXPORT_DIR).parent / "trade_command.json"
SC_RESULT_PATH = Path(EXPORT_DIR).parent / "trade_result.json"

VALID_ACTIONS = {"BUY", "SELL", "CANCEL", "MODIFY", "STATUS", "FLATTEN"}
POLL_TIMEOUT_S = 10.0
POLL_INTERVAL_S = 0.2


def _sha256(data: bytes) -> str:
    """Compute sha256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def _ensure_dir(path: Path):
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


class TradeCommandHandler:
    """Handles file-based trade command/result protocol with Sierra DLL.

    Watches for trade_command.json written by the backend API,
    validates it, forwards to DLL, and returns the DLL result.
    """

    def __init__(self):
        _ensure_dir(COMMAND_FILE)
        _ensure_dir(RESULT_FILE)
        self._last_command_hash: Optional[str] = None

    def submit_command(self, command: dict) -> dict:
        """Submit a trade command and wait for DLL result.

        Args:
            command: Trade command dict with at least {"action": str, "trade_id": str}.

        Returns:
            Result dict: {"status": "ACK"|"FILLED"|"REJECTED"|"TIMEOUT", ...}
        """
        # Validate
        action = command.get("action", "").upper()
        if action not in VALID_ACTIONS:
            return {
                "status": "REJECTED",
                "reason": f"Invalid action: {action}. Valid: {', '.join(sorted(VALID_ACTIONS))}",
                "ts": time.time(),
            }

        # Add metadata
        command["ts_submitted"] = time.time()
        command["action"] = action

        # Write command with checksum
        payload = json.dumps(command, indent=2).encode()
        checksum = _sha256(payload)
        command["checksum"] = checksum

        # Write to SC command path for DLL
        full_payload = json.dumps(command, indent=2)
        try:
            _ensure_dir(SC_COMMAND_PATH)
            with open(SC_COMMAND_PATH, "w") as f:
                f.write(full_payload)
            logger.info(f"[trade_cmd] Wrote command to {SC_COMMAND_PATH}: {action}")
        except IOError as e:
            logger.error(f"[trade_cmd] Failed to write SC command: {e}")
            return {
                "status": "REJECTED",
                "reason": f"Failed to write command file: {e}",
                "ts": time.time(),
            }

        # Also write to signals dir for backend visibility
        try:
            with open(COMMAND_FILE, "w") as f:
                f.write(full_payload)
        except IOError as e:
            logger.warning(f"[trade_cmd] Failed to write signal command: {e}")

        # For STATUS commands, return ACK immediately (no DLL interaction needed)
        if action == "STATUS":
            result = {
                "status": "ACK",
                "action": action,
                "trade_id": command.get("trade_id"),
                "ts": time.time(),
                "message": "Status request acknowledged",
            }
            self._write_result(result)
            return result

        # Poll for DLL result
        result = self._poll_for_result(command)
        self._write_result(result)
        return result

    def _poll_for_result(self, command: dict) -> dict:
        """Poll SC_RESULT_PATH for DLL response.

        Returns:
            Result dict from DLL, or TIMEOUT if no response within POLL_TIMEOUT_S.
        """
        start = time.time()
        # Clear any stale result
        if SC_RESULT_PATH.exists():
            try:
                SC_RESULT_PATH.unlink()
            except IOError:
                pass

        while time.time() - start < POLL_TIMEOUT_S:
            if SC_RESULT_PATH.exists():
                try:
                    with open(SC_RESULT_PATH, "r") as f:
                        result_data = json.load(f)

                    # Verify checksum if present
                    if "checksum" in result_data:
                        result_payload = json.dumps(
                            {k: v for k, v in result_data.items() if k != "checksum"},
                            indent=2,
                        ).encode()
                        expected = _sha256(result_payload)
                        if result_data["checksum"] != expected:
                            logger.warning("[trade_cmd] Result checksum mismatch")

                    logger.info(f"[trade_cmd] DLL result: {result_data.get('status', 'unknown')}")
                    return result_data
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"[trade_cmd] Result read error: {e}")

            time.sleep(POLL_INTERVAL_S)

        # Timeout — DLL did not respond
        logger.warning(f"[trade_cmd] DLL timeout after {POLL_TIMEOUT_S}s")
        return {
            "status": "TIMEOUT",
            "action": command.get("action"),
            "trade_id": command.get("trade_id"),
            "ts": time.time(),
            "message": f"DLL did not respond within {POLL_TIMEOUT_S}s",
        }

    def _write_result(self, result: dict):
        """Write result to signals dir for backend API."""
        try:
            _ensure_dir(RESULT_FILE)
            with open(RESULT_FILE, "w") as f:
                json.dump(result, f, indent=2)
        except IOError as e:
            logger.warning(f"[trade_cmd] Failed to write result: {e}")

    def get_last_result(self) -> Optional[dict]:
        """Read the most recent trade result."""
        if not RESULT_FILE.exists():
            return None
        try:
            with open(RESULT_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
