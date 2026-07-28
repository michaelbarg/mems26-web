#!/usr/bin/env python3
"""Read-only sim harness for ORPHAN_AUTO_STOP_V1 (Michael 2026-07-20 doctrine).

Legacy (WRONG): resting PLACE_STOP · working_orders 0→1 · PLACE_STOP_OK.
Current (RIGHT): hold orphan with virtual STRUCTURAL stop + $200 cap;
                  FLATTEN_ORPHAN only on stop-cross OR loss >= ORPHAN_MAX_LOSS_USD.

cc/Michael create the orphan in sim first. Cursor/cowork run this script to verify.
No orders are placed from here.

Exit codes: 0=PASS · 1=FAIL · 2=INDETERMINATE (missing inputs / stale feed)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
STATE_MAX_AGE_S = 15.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class HarnessResult:
    phase: str
    verdict: str  # PASS | FAIL | INDETERMINATE
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


def _export_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("MEMS26_SIGNALS_DIR", DEFAULT_EXPORT)))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text().strip() or "{}")
    except (OSError, json.JSONDecodeError):
        return None


def _state_fresh(path: Path) -> tuple[Optional[Dict[str, Any]], Optional[float]]:
    try:
        if not path.exists():
            return None, None
        age = time.time() - path.stat().st_mtime
        if age > STATE_MAX_AGE_S:
            return None, age
        return _read_json(path), age
    except OSError:
        return None, None


def _scan_ops_log(since_ts: float, needles: tuple[str, ...]) -> List[str]:
  hits: List[str] = []
  log_dir = Path(ROOT) / "docs" / "reports"
  for path in sorted(log_dir.glob("OPS_LOG_*.md"), reverse=True)[:3]:
      try:
          for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
              if not any(n in line for n in needles):
                  continue
              # Best-effort timestamp parse from "[2026-07-20T..."
              if line.startswith("[") and "]" in line:
                  ts_part = line[1: line.index("]")]
                  try:
                      from datetime import datetime
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


def _recent_result_status(result_path: Path, since_ts: float) -> Optional[str]:
    try:
        if not result_path.exists():
            return None
        if result_path.stat().st_mtime < since_ts:
            return None
        data = _read_json(result_path) or {}
        return str(data.get("status") or "")
    except OSError:
        return None


def _unrealized_loss_usd(side: str, entry: float, last_price: float, qty: int) -> float:
    if side == "LONG":
        pts = max(0.0, entry - last_price)
    else:
        pts = max(0.0, last_price - entry)
    return pts * qty * 12.50


def verify_hold(
    state: Dict[str, Any],
    *,
    baseline_qty: Optional[int],
    since_ts: float,
    export: Path,
) -> HarnessResult:
    from backend.v9.services.sierra_position_reconciler import recommend_orphan_stop

    result = HarnessResult(phase="hold", verdict="FAIL")
    qty = state.get("position_qty")
    working = state.get("working_orders")
    avg = state.get("avg_price")
    is_sim = state.get("is_sim")
    last_price = state.get("last_price") or state.get("last_trade_price")

    result.add("is_sim", is_sim in (1, True, "1"), f"is_sim={is_sim} (require sim)")
    result.add("orphan_held", qty not in (None, 0), f"position_qty={qty} (must be non-zero)")
    if baseline_qty is not None and qty is not None:
        result.add(
            "position_not_grown",
            abs(int(qty)) <= abs(int(baseline_qty)),
            f"|qty|={abs(int(qty))} baseline={abs(int(baseline_qty))}",
        )

    # New doctrine: working_orders MAY stay 0 — no resting stop in Sierra.
    result.add(
        "no_resting_stop_required",
        True,
        f"working_orders={working} — OK at 0 (virtual stop, not PLACE_STOP)",
    )

    rec = recommend_orphan_stop(int(qty) if qty is not None else 0, avg)
    if rec:
        side = rec["side"]
        stop = rec["stop"]
        result.add(
            "structural_stop_computed",
            True,
            f"{side} {rec['qty']}c @ {rec['entry']} → stop @ {stop} ({rec['points']}pt)",
        )
        if last_price is not None:
            lp = float(last_price)
            crossed = (side == "LONG" and lp <= stop) or (side == "SHORT" and lp >= stop)
            loss = _unrealized_loss_usd(side, float(rec["entry"]), lp, int(rec["qty"]))
            result.add(
                "not_yet_flatten_trigger",
                not crossed and loss < float(os.getenv("ORPHAN_MAX_LOSS_USD", "200")),
                f"price={lp} crossed={crossed} unrealized_loss=${loss:.2f}",
            )
    else:
        result.add("structural_stop_computed", False, f"recommend_orphan_stop None (qty={qty} avg={avg})")

    result_path = export / "trade_result.json"
    status = _recent_result_status(result_path, since_ts)
    result.add(
        "no_place_stop_ok",
        status is None or "PLACE_STOP" not in (status or ""),
        f"trade_result.status={status or 'none/recent'}",
    )
    result.add(
        "no_immediate_flatten",
        status is None or "FLATTEN_ORPHAN" not in (status or ""),
        f"trade_result.status={status or 'none/recent'} (hold phase)",
    )

    ops_hits = _scan_ops_log(since_ts, ("VIRTUAL STOP SET", "VIRTUAL_STOP_SET", "ORPHAN VIRTUAL"))
    result.add(
        "virtual_stop_evidence",
        bool(ops_hits),
        ops_hits[-1] if ops_hits else "no VIRTUAL_STOP_SET in recent ops_log (enable ORPHAN_AUTO_STOP_V1?)",
    )

    result.finalize()
    return result


def verify_flatten(
    state: Dict[str, Any],
    *,
    since_ts: float,
    export: Path,
) -> HarnessResult:
    result = HarnessResult(phase="flatten", verdict="FAIL")
    qty = state.get("position_qty")
    is_sim = state.get("is_sim")

    result.add("is_sim", is_sim in (1, True, "1"), f"is_sim={is_sim}")
    result.add("qty_zero", qty in (0, 0.0, None), f"position_qty={qty} (must be 0 after FLATTEN)")

    result_path = export / "trade_result.json"
    status = _recent_result_status(result_path, since_ts)
    result.add(
        "flatten_orphan_ok",
        status == "FLATTEN_ORPHAN_OK",
        f"trade_result.status={status or 'missing/stale'}",
    )
    result.add(
        "no_place_stop_ok",
        status is None or "PLACE_STOP_OK" not in (status or ""),
        f"legacy PLACE_STOP_OK must not appear (got {status})",
    )

    ops_hits = _scan_ops_log(since_ts, ("ORPHAN FLATTENED", "FLATTEN_ORPHAN", "FLATTEN_TRIGGERED"))
    result.add(
        "flatten_evidence",
        bool(ops_hits),
        ops_hits[-1] if ops_hits else "no FLATTEN evidence in recent ops_log",
    )

    result.finalize()
    return result


def infer_phase(state: Dict[str, Any], export: Path, since_ts: float) -> Optional[str]:
    """Return hold/flatten, or None when there is nothing to verify."""
    status = _recent_result_status(export / "trade_result.json", since_ts)
    if status == "FLATTEN_ORPHAN_OK":
        return "flatten"
    qty = state.get("position_qty")
    if qty not in (None, 0, 0.0):
        return "hold"
    return None


def print_result(result: HarnessResult) -> None:
    icon = {"PASS": "🟢", "FAIL": "🔴", "INDETERMINATE": "🟡"}.get(result.verdict, "?")
    print(f"ORPHAN sim harness · phase={result.phase} · {icon} {result.verdict}")
    for check in result.checks:
        mark = "✅" if check.ok else "❌"
        print(f"  {mark} {check.name}: {check.detail}")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("hold", "flatten", "auto"),
        default="auto",
        help="hold=orphan monitored · flatten=qty→0 after trigger · auto=infer",
    )
    parser.add_argument(
        "--since",
        type=float,
        default=600.0,
        help="only trust trade_result/ops_log newer than this many seconds (default 600)",
    )
    parser.add_argument(
        "--baseline-qty",
        type=int,
        default=None,
        help="optional |qty| at orphan creation — fail if position grew",
    )
    parser.add_argument(
        "--export-dir",
        default=None,
        help="override v9_export directory (default MEMS26_SIGNALS_DIR or ~/SierraChart_Data/v9_export)",
    )
    args = parser.parse_args(argv)

    export = Path(args.export_dir).expanduser() if args.export_dir else _export_dir()
    state_path = export / "sierra_state.json"
    state, age = _state_fresh(state_path)
    since_ts = time.time() - max(0.0, args.since)

    if state is None:
        print_result(HarnessResult(
            phase=args.phase,
            verdict="INDETERMINATE",
            checks=[Check("state_fresh", False, f"sierra_state missing or stale (age={age})")],
            exit_code=2,
        ))
        return 2

    phase = args.phase
    if phase == "auto":
        inferred = infer_phase(state, export, since_ts)
        if inferred is None:
            print_result(HarnessResult(
                phase="auto",
                verdict="INDETERMINATE",
                checks=[Check(
                    "orphan_scenario",
                    False,
                    "flat + no recent FLATTEN_ORPHAN_OK — create orphan in sim first",
                )],
                exit_code=2,
            ))
            return 2
        phase = inferred

    if phase == "hold":
        result = verify_hold(state, baseline_qty=args.baseline_qty, since_ts=since_ts, export=export)
    else:
        result = verify_flatten(state, since_ts=since_ts, export=export)

    print_result(result)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
