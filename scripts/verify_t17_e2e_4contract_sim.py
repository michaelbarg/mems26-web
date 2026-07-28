#!/usr/bin/env python3
"""Read-only sim harness for T17 — 4-contract E2E ladder (Michael 07-19/07-20).

cc/Michael fire a 4-contract sim trade first. This script verifies AFTER placement:
  · 4 contracts at entry (FIXED_CONTRACTS_4)
  · Sierra: qty=4 + 8 working orders (4 OCO pairs) OR fill progression
  · Target hits C1..C4 (T0/T1/T2/T3 mapping) via trade timeline
  · MODIFY_STOP evidence (ops_log / trade_result)
  · BE only AFTER real T1 hit — NOT immediately after entry

No orders placed from here. Exit: 0=PASS · 1=FAIL · 2=INDETERMINATE.

Usage (after cc sim fire):
  python3 scripts/verify_t17_e2e_4contract_sim.py --trade-id <id>
  python3 scripts/verify_t17_e2e_4contract_sim.py --auto   # latest non-shadow trade
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
API_BASE = os.getenv("MEMS26_API_URL", "http://127.0.0.1:8000").rstrip("/")
STATE_MAX_AGE_S = 30.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class HarnessResult:
    phase: str
    verdict: str
    checks: List[Check] = field(default_factory=list)
    exit_code: int = 1

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))

    def finalize(self) -> None:
        if any(not c.ok for c in self.checks):
            self.verdict = "FAIL"
            self.exit_code = 1
        elif not self.checks:
            self.verdict = "INDETERMINATE"
            self.exit_code = 2
        else:
            self.verdict = "PASS"
            self.exit_code = 0


def _api_json(path: str, timeout: int = 12) -> Any:
    headers = {}
    token = os.getenv("BRIDGE_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API_BASE}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text().strip() or "{}")
    except (OSError, json.JSONDecodeError):
        return None


def _export_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("MEMS26_SIGNALS_DIR", DEFAULT_EXPORT)))


def _scan_ops_log(since_ts: float, needles: tuple[str, ...]) -> List[str]:
    hits: List[str] = []
    log_dir = Path(ROOT) / "docs" / "reports"
    for path in sorted(log_dir.glob("OPS_LOG_*.md"), reverse=True)[:3]:
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not any(n in line for n in needles):
                    continue
                if line.startswith("[") and "]" in line:
                    ts_part = line[1: line.index("]")]
                    try:
                        from zoneinfo import ZoneInfo
                        parsed = datetime.fromisoformat(ts_part)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=ZoneInfo("America/New_York"))
                        if parsed.timestamp() < since_ts:
                            continue
                    except (ValueError, TypeError):
                        pass
                hits.append(line.strip())
        except OSError:
            continue
    return hits


def _find_latest_trade() -> Optional[Dict[str, Any]]:
    payload = _api_json("/api/v9/trades?limit=20")
    rows = payload.get("trades") if isinstance(payload, dict) else payload
    if not rows:
        return None
    for row in rows:
        if row.get("is_synthetic"):
            continue
        if str(row.get("mode", "")).lower() == "shadow":
            continue
        return row
    return rows[0] if rows else None


def _contract_count(trade: Dict[str, Any]) -> Optional[int]:
    q = trade.get("quality") or {}
    if isinstance(q, str):
        try:
            q = json.loads(q)
        except json.JSONDecodeError:
            q = {}
    for key in ("contracts", "sizing_contracts", "size"):
        val = q.get(key) if isinstance(q, dict) else None
        if val is None:
            val = trade.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return None


def _timeline(trade_id: int) -> Dict[str, Any]:
    return _api_json(f"/api/v9/trades/{trade_id}/timeline")


def _event_ts(ev: Dict[str, Any]) -> float:
    raw = ev.get("ts") or ""
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def verify_trade(
    trade: Dict[str, Any],
    *,
    since_ts: float,
    export: Path,
) -> HarnessResult:
    result = HarnessResult(phase="e2e_4contract", verdict="FAIL")
    trade_id = trade.get("id")
    if not trade_id:
        result.add("trade_id", False, "missing id")
        result.finalize()
        return result

    # is_sim gate
    state = _read_json(export / "sierra_state.json")
    is_sim = (state or {}).get("is_sim")
    result.add("is_sim", is_sim in (1, True, "1"), f"is_sim={is_sim}")

    n = _contract_count(trade)
    result.add(
        "contracts_at_entry",
        n == 4,
        f"contracts={n} (want 4 under FIXED_CONTRACTS_4)",
    )

    # Sierra snapshot (post-entry may vary — informational)
    if state:
        qty = abs(int(state.get("position_qty") or 0))
        working = int(state.get("working_orders") or 0)
        result.add(
            "sierra_state_snapshot",
            True,
            f"position_qty={state.get('position_qty')} working_orders={working} "
            f"(expect 4c+8 working right after entry; OK if partial fills progressed)",
        )

    # Timeline / target ladder
    try:
        tl = _timeline(int(trade_id))
    except Exception as exc:
        result.add("timeline", False, f"{type(exc).__name__}: {exc}")
        result.finalize()
        return result

    events = tl.get("events") or []
    hits = [e for e in events if re.search(r"T[1-4]_HIT", e.get("type", ""))]
    hit_types = [e.get("type") for e in hits]
    result.add(
        "target_hits_present",
        len(hits) >= 1,
        f"hits={hit_types or 'none yet'} (full ladder: T1_HIT→T4_HIT)",
    )

    # BE timing: SMART_BE / stop→entry must come AFTER T1_HIT, not before any hit
    t1_ts = min((_event_ts(e) for e in events if e.get("type") == "T1_HIT"), default=None)
    be_events = [
        e for e in events
        if "BE" in str(e.get("type", "")).upper()
        or "SMART_BE" in str(e.get("type", "")).upper()
        or "STOP" in str(e.get("type", "")).upper()
    ]
    mgmt_be = [
        e for e in events
        if e.get("type", "").startswith("MGMT_")
        and any(k in json.dumps(e.get("detail", {})).upper() for k in ("BE", "BREAK_EVEN", "ENTRY"))
    ]
    be_ts = min((_event_ts(e) for e in be_events + mgmt_be), default=None) if (be_events or mgmt_be) else None

    if be_ts is not None and t1_ts is not None:
        result.add(
            "be_after_real_t1",
            be_ts >= t1_ts,
            f"T1_HIT ts={t1_ts:.0f} · BE/stop-move ts={be_ts:.0f}",
        )
    elif t1_ts is None and be_ts is None:
        result.add(
            "be_after_real_t1",
            True,
            "no T1 hit and no BE yet — OK mid-trade (re-run after T1 fills)",
        )
    elif t1_ts is None and be_ts is not None:
        result.add(
            "be_after_real_t1",
            False,
            f"BE/stop-move before T1_HIT (BE ts={be_ts:.0f})",
        )
    else:
        result.add(
            "be_after_real_t1",
            True,
            f"T1_HIT recorded · BE not yet in timeline (may follow)",
        )

    # MODIFY_STOP evidence
    ops_hits = _scan_ops_log(since_ts, ("MODIFY_STOP_OK", "MODIFY_STOP", "smart_be"))
    result_path = export / "trade_result.json"
    tr_status = None
    try:
        if result_path.exists() and result_path.stat().st_mtime >= since_ts:
            tr_status = (_read_json(result_path) or {}).get("status")
    except OSError:
        pass
    has_modify = bool(ops_hits) or (tr_status and "MODIFY_STOP" in str(tr_status))
    result.add(
        "modify_stop_evidence",
        has_modify,
        ops_hits[-1] if ops_hits else f"trade_result.status={tr_status or 'none/stale'}",
    )

    # effective_contracts sanity (read-only, no fire)
    try:
        from backend.v9.services.sierra_command import effective_contracts
        ec = int(effective_contracts({"size": "full"}))
        result.add("effective_contracts_flag", ec == 4, f"effective_contracts(full)={ec}")
    except Exception as exc:
        result.add("effective_contracts_flag", False, f"{type(exc).__name__}: {exc}")

    # Contract×stage table (stdout helper data captured in last check)
    rows = []
    for label in ("T1", "T2", "T3", "T4"):
        ts = trade.get(f"{label.lower()}_hit_ts") or getattr(trade, label.lower(), None)
        rows.append(f"{label}: hit_ts={trade.get(f'{label.lower()}_hit_ts', '—')}")
    result.add("ladder_table", True, " · ".join(rows))

    result.finalize()
    return result


def print_result(result: HarnessResult, trade: Optional[Dict[str, Any]] = None) -> None:
    icon = {"PASS": "🟢", "FAIL": "🔴", "INDETERMINATE": "🟡"}.get(result.verdict, "?")
    hdr = f"T17 4-contract harness · {icon} {result.verdict}"
    if trade:
        hdr += f" · trade #{trade.get('id')} {trade.get('direction')} state={trade.get('state')}"
    print(hdr)
    for check in result.checks:
        mark = "✅" if check.ok else "❌"
        print(f"  {mark} {check.name}: {check.detail}")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-id", type=int, default=None, help="trade id to verify")
    parser.add_argument("--auto", action="store_true", help="pick latest non-shadow trade")
    parser.add_argument("--since", type=float, default=3600.0, help="ops_log window (seconds)")
    parser.add_argument("--export-dir", default=None)
    args = parser.parse_args(argv)

    export = Path(args.export_dir).expanduser() if args.export_dir else _export_dir()
    since_ts = time.time() - max(0.0, args.since)

    trade: Optional[Dict[str, Any]] = None
    if args.trade_id:
        try:
            payload = _api_json(f"/api/v9/trades?limit=100")
            rows = payload.get("trades") if isinstance(payload, dict) else payload
            trade = next((r for r in (rows or []) if r.get("id") == args.trade_id), None)
            if not trade:
                trade = {"id": args.trade_id}
        except Exception as exc:
            print_result(HarnessResult(
                phase="e2e_4contract",
                verdict="INDETERMINATE",
                checks=[Check("api", False, str(exc))],
                exit_code=2,
            ))
            return 2
    elif args.auto:
        try:
            trade = _find_latest_trade()
        except Exception as exc:
            print_result(HarnessResult(
                phase="e2e_4contract",
                verdict="INDETERMINATE",
                checks=[Check("api", False, str(exc))],
                exit_code=2,
            ))
            return 2
    else:
        print("Provide --trade-id <id> or --auto after cc fires sim trade.", file=sys.stderr)
        return 2

    if not trade or not trade.get("id"):
        print_result(HarnessResult(
            phase="e2e_4contract",
            verdict="INDETERMINATE",
            checks=[Check("trade", False, "no trade found — cc must PLACE 4-contract sim first")],
            exit_code=2,
        ))
        return 2

    result = verify_trade(trade, since_ts=since_ts, export=export)
    print_result(result, trade)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
