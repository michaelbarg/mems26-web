#!/usr/bin/env python3
"""Trade Activity Log feeder — extracts fill/stop-move events from Sierra's binary log.

Runs periodically (cron or bridge poll). Extracts text from the binary
TradeActivityLog file via string patterns, looking for:
  - "Closed Trade Profit/Loss" → manual close detection
  - "Updated Internal Position Quantity" → position changes
  - "User order modification" → manual stop/target moves
  - "Parent base price" → bracket fill prices

Writes events to trade_activity_events.jsonl (append-only) for the
live_ledger_routes.py to consume.

Usage:
  python3 scripts/trade_activity_feed.py [--once] [--account 37138283]
  Default: polls every 60s; --once for single run.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

LIVE_ACCOUNT = os.getenv("SIERRA_LIVE_ACCOUNT", "37138283")
SIERRA_DIR = Path(os.path.expanduser("~/SierraChart/TradeActivityLogs"))
EXPORT_DIR = Path(os.path.expanduser("~/SierraChart_Data/v9_export"))
EVENTS_FILE = EXPORT_DIR / "trade_activity_events.jsonl"
POLL_INTERVAL = 60  # seconds


def _today_log_path(account: str) -> Path:
    """Path to today's TradeActivityLog for the given account.

    Sim accounts use pattern: TradeActivityLog_YYYY-MM-DD_UTC.Sim1.simulated.data
    Live accounts use: TradeActivityLog_YYYY-MM-DD_UTC.37138283.data
    """
    d = date.today().strftime("%Y-%m-%d")
    if account.lower().startswith("sim"):
        return SIERRA_DIR / f"TradeActivityLog_{d}_UTC.{account}.simulated.data"
    return SIERRA_DIR / f"TradeActivityLog_{d}_UTC.{account}.data"


def _extract_text(log_path: Path) -> list[str]:
    """Extract readable strings from Sierra's binary TradeActivityLog."""
    if not log_path.exists():
        return []
    result = subprocess.run(
        ["strings", str(log_path)],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def _parse_events(lines: list[str], last_offset: int = 0, account: str = "") -> tuple[list[dict], int]:
    """Parse text lines into structured events. Returns (events, new_offset)."""
    events = []
    ts_now = datetime.now(timezone.utc).isoformat()
    is_sim = account.lower().startswith("sim") if account else False

    for i, line in enumerate(lines):
        if i < last_offset:
            continue

        # Closed Trade P&L
        m = re.search(r"Closed Trade Profit/Loss: ([\d.-]+)\. Symbol: (\S+)", line)
        if m:
            events.append({
                "type": "CLOSED_TRADE_PNL",
                "pnl": float(m.group(1)),
                "symbol": m.group(2),
                "ts": ts_now,
                "line": i,
            })

        # Position quantity change
        m = re.search(
            r"Updated Internal Position Quantity to (-?\d+)\. Previous: (-?\d+)\. "
            r"Fill of InternalOrderID: (\d+)", line)
        if m:
            events.append({
                "type": "POSITION_CHANGE",
                "new_qty": int(m.group(1)),
                "prev_qty": int(m.group(2)),
                "order_id": int(m.group(3)),
                "ts": ts_now,
                "line": i,
            })

        # FIX-10 (2026-07-10, trade 337): async broker rejection — Sierra logs
        # "Teton CME Routing (Order reject). Info: Trade Order Error - ..."
        # AFTER a successful submit-ack. Without this event the backend recorded
        # a margin-rejected entry as CLOSED/BE. No order-id on the line → the
        # backend correlates to the submit-acked PENDING trade with no fill.
        m = re.search(r"\(Order reject\)\.\s*Info:\s*(.{0,140})", line)
        if m:
            events.append({
                "type": "ORDER_REJECT",
                "reason": m.group(1).strip(),
                "ts": ts_now,
                "line": i,
            })

        # User order modification (manual stop/target move)
        m = re.search(
            r"User order modification.*Requested Price: ([\d.]+?)\.?\s.*Requested Quantity: (\d+)",
            line)
        if m:
            events.append({
                "type": "USER_ORDER_MODIFY",
                "price": float(m.group(1)),
                "qty": int(m.group(2)),
                "ts": ts_now,
                "line": i,
            })

        # Parent base price from bracket
        m = re.search(r"Parent base price: ([\d.]+)\. New price: ([\d.]+)", line)
        if m:
            events.append({
                "type": "BRACKET_MODIFY",
                "parent_price": float(m.group(1)),
                "new_price": float(m.group(2)),
                "ts": ts_now,
                "line": i,
            })

    # Tag every event with account + sim flag
    for ev in events:
        ev["account"] = account
        ev["is_sim"] = is_sim

    return events, len(lines)


def _append_events(events: list[dict]):
    """Append events to the journal file."""
    if not events:
        return
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def run_once(account: str) -> list[dict]:
    """Single extraction run. Returns new events."""
    log_path = _today_log_path(account)
    if not log_path.exists():
        return []

    # Track offset per-account to avoid re-processing and cross-contamination
    offset_file = EXPORT_DIR / f".trade_activity_offset_{account}"
    last_offset = 0
    if offset_file.exists():
        try:
            last_offset = int(offset_file.read_text().strip())
        except (ValueError, OSError):
            pass

    lines = _extract_text(log_path)
    events, new_offset = _parse_events(lines, last_offset, account=account)

    if events:
        _append_events(events)
        print(f"[trade_activity_feed] {len(events)} new events from {log_path.name}")
        for ev in events:
            print(f"  {ev['type']}: {json.dumps({k: v for k, v in ev.items() if k != 'type'})}")

    offset_file.write_text(str(new_offset))
    return events


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sierra TradeActivityLog feeder")
    parser.add_argument("--once", action="store_true", help="Single run, no polling")
    parser.add_argument("--account", default=LIVE_ACCOUNT, help="Sierra account ID")
    args = parser.parse_args()

    if args.once:
        events = run_once(args.account)
        print(f"Total: {len(events)} events")
        return

    print(f"[trade_activity_feed] polling every {POLL_INTERVAL}s for account {args.account}")
    while True:
        try:
            run_once(args.account)
        except Exception as e:
            print(f"[trade_activity_feed] error: {e}", file=sys.stderr)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
