"""Candidate Ledger — observability-only event writer (T-103).

Appends DETECTED / EMIT_DECISION events to the existing gateway_decisions
JSONL. GATE_DECISION / ROUTED reuse the gateway's existing route_setup row.

Flag CANDIDATE_LEDGER_V1 default OFF. Failure never raises into detection,
gateway verdict, size, order, stop or target.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SCHEMA = "candidate_ledger.v1"
UI_EVENT_TYPES = {None, "GATE_DECISION", "ROUTED"}
_LIVE_PATH_MARKERS = (
    "SierraChart_Data/v9_export",
    "SierraChart/Data/v9_export",
)

_lock = threading.Lock()
_seen_event_ids = set()
_cached_commit: Optional[str] = None
_warned = False


def enabled() -> bool:
    return os.getenv("CANDIDATE_LEDGER_V1", "0").strip().lower() in (
        "1", "true", "yes", "shadow",
    )


def is_ui_decision(row: Optional[dict]) -> bool:
    """True for legacy route_setup rows and GATE/ROUTED ledger events.

    DETECTED / EMIT_DECISION / RESOLVED must not enter the fire panel.
    """
    if not isinstance(row, dict):
        return False
    return row.get("event_type") in UI_EVENT_TYPES


def floor_bar_ts(value: Any) -> str:
    """UTC ISO seconds, floored to the canonical 5-minute grid."""
    dt = _as_utc(value)
    floored = dt.replace(second=0, microsecond=0)
    minute = (floored.minute // 5) * 5
    floored = floored.replace(minute=minute)
    return floored.isoformat(timespec="seconds")


def make_candidate_id(
    *,
    system_id: int,
    pattern: str,
    direction: str,
    signal_bar_ts: Any,
    variant_tag: str = "",
) -> str:
    identity = {
        "schema_version": SCHEMA,
        "system_id": int(system_id),
        "pattern": str(pattern or ""),
        "direction": str(direction or "").upper(),
        "signal_bar_ts": floor_bar_ts(signal_bar_ts),
        "variant_tag": str(variant_tag or ""),
    }
    blob = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def make_event_id(candidate_id: str, event_type: str, stage_key: str = "") -> str:
    raw = f"{candidate_id}|{event_type}|{stage_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record(
    event_type: str,
    *,
    system_id: int,
    pattern: str,
    direction: str,
    signal_bar_ts: Any,
    variant_tag: str = "",
    family: Optional[str] = None,
    candidate_id: Optional[str] = None,
    verdict: Optional[str] = None,
    blocked_by: Optional[str] = None,
    reason: Optional[str] = None,
    prices: Optional[dict] = None,
    policy_id: Optional[str] = None,
    mode: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Optional[str]:
    """Append one ledger event. Returns candidate_id, or None if skipped.

    Never raises.
    """
    try:
        if not enabled():
            return None
        cid = candidate_id or make_candidate_id(
            system_id=system_id,
            pattern=pattern,
            direction=direction,
            signal_bar_ts=signal_bar_ts,
            variant_tag=variant_tag,
        )
        stage_key = _stage_key(event_type, verdict=verdict, blocked_by=blocked_by)
        eid = make_event_id(cid, event_type, stage_key)
        with _lock:
            if eid in _seen_event_ids:
                return cid
            _seen_event_ids.add(eid)
        event = {
            "schema": SCHEMA,
            "event_id": eid,
            "candidate_id": cid,
            "event_type": event_type,
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "signal_bar_ts": floor_bar_ts(signal_bar_ts),
            "system": int(system_id),
            "pattern": pattern,
            "family": family,
            "direction": str(direction or "").upper(),
            "source": {
                "pid": os.getpid(),
                "machine_tag": os.getenv("MEMS26_MACHINE_TAG") or socket.gethostname(),
                "code_commit": _code_commit(),
                "mode": mode or os.getenv("MEMS26_MODE") or "live",
            },
            "policy_id": policy_id or f"s{system_id}_live",
        }
        if verdict or blocked_by or reason:
            event["decision"] = {
                "stage": event_type,
                "verdict": verdict,
                "blocked_by": blocked_by,
                "reason": reason,
            }
        if prices:
            event["prices"] = prices
        if extra:
            event.update(extra)
        if not _append_jsonl(event):
            with _lock:
                _seen_event_ids.discard(eid)
        return cid
    except Exception as exc:
        _swallow(f"candidate_ledger:{event_type}", exc)
        return None


def reset_seen() -> None:
    """Test helper."""
    with _lock:
        _seen_event_ids.clear()


def _stage_key(event_type: str, *, verdict: Optional[str], blocked_by: Optional[str]) -> str:
    if event_type == "EMIT_DECISION":
        return str(verdict or blocked_by or "emit")
    if event_type == "GATE_DECISION":
        return str(blocked_by or "allow")
    if event_type == "ROUTED":
        return str(verdict or "routed")
    return event_type.lower()


def _append_jsonl(event: dict) -> bool:
    path = _jsonl_path()
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, separators=(",", ":"), default=str)
        with _lock:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return True
    except Exception as exc:
        _swallow("candidate_ledger:append", exc)
        return False


def _jsonl_path() -> Optional[Path]:
    raw = os.environ.get(
        "GATEWAY_DECISIONS_PATH",
        os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl"),
    )
    if _is_live_path(raw) and (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("MEMS26_TEST_MODE") == "1"
    ):
        return None
    return Path(raw)


def _is_live_path(raw: str) -> bool:
    normalized = raw.replace("\\", "/")
    return any(marker in normalized for marker in _LIVE_PATH_MARKERS)


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _code_commit() -> str:
    global _cached_commit
    if _cached_commit:
        return _cached_commit
    try:
        root = Path(__file__).resolve().parents[3]
        _cached_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            timeout=2,
            stderr=subprocess.DEVNULL,
        ).decode().strip()[:40]
    except Exception:
        _cached_commit = "unknown"
    return _cached_commit


def _swallow(location: str, exc: BaseException) -> None:
    global _warned
    try:
        from backend.v9.services.swallow_counter import swallowed
        swallowed(location, exc)
    except Exception:
        if not _warned:
            _warned = True
            logger.warning("[candidate_ledger] %s failed: %s", location, exc)
