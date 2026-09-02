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

# T-227 (2026-09-02): per-line parse failures, surfaced instead of swallowed.
# Read by the regression test and printed by run_once so a parser bug can never
# again cost a silent trading day.
_PARSE_ERRORS: list[dict] = []


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
    # NOTE (2026-07-28): this is the SCAN time, not the trade time — Sierra's
    # binary log carries no recoverable per-line timestamp (`strings` finds zero
    # HH:MM:SS patterns). It is now named honestly and must NEVER be used to
    # place a close on a calendar day or to correlate it with a trade; for
    # per-day P&L read the per-day log FILES (backend/v9/services/daily_pnl.py),
    # whose day comes from the filename.
    ts_now = datetime.now(timezone.utc).isoformat()
    is_sim = account.lower().startswith("sim") if account else False

    for i, line in enumerate(lines):
        # T-227 ROOT-FIX (2026-09-02): ONE malformed line must never cost a
        # whole trading day. The greedy "New price" regex below used to raise
        # ValueError out of this loop, out of run_once, and out of the process —
        # so a single bracket-modify line silently stopped the entire Sierra
        # activity feed from 2026-08-27 onward. Parse defensively and SCREAM
        # (never `pass`) so the next parser bug is visible the same day.
        try:
            if i < last_offset:
                continue

            # Closed Trade P&L
            m = re.search(r"Closed Trade Profit/Loss: ([\d.-]+)\. Symbol: (\S+)", line)
            if m:
                events.append({
                    "type": "CLOSED_TRADE_PNL",
                    "pnl": float(m.group(1)),
                    "symbol": m.group(2),
                    "scan_ts": ts_now,
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
                    "scan_ts": ts_now,
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
                    "scan_ts": ts_now,
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
                    "scan_ts": ts_now,
                    "line": i,
                })

            # Parent base price from bracket
            # T-227 ROOT-FIX (2026-09-02): `([\d.]+)` is greedy and `.` is INSIDE the
            # class, so on the real Sierra line
            #     "... Parent base price: 7676.50. New price: 7673.50. Requested Price: ..."
            # group(2) captured "7673.50." — trailing sentence period included — and
            # `float()` raised `ValueError: could not convert string to float:
            # '7673.50.'`. That exception escaped `_parse_events`, killed `run_once`,
            # and with it the WHOLE day's feed: `trade_activity_events.jsonl` last
            # grew 2026-08-27, so the ruled-ON W2 exit tracker
            # (EXIT_TRACK_ACTIVITY_V1=1, Michael 2026-07-27) has been a no-op ever
            # since — which is why every MAE_SCRATCH/FLATTEN exit stayed UNPRICED and
            # `pnl_sierra` is NULL on 100% of rows. Anchor the number instead.
            m = re.search(r"Parent base price: (-?\d+(?:\.\d+)?)\. "
                          r"New price: (-?\d+(?:\.\d+)?)\.", line)
            if m:
                events.append({
                    "type": "BRACKET_MODIFY",
                    "parent_price": float(m.group(1)),
                    "new_price": float(m.group(2)),
                    "scan_ts": ts_now,
                    "line": i,
                })

            # Sim-account patterns (07-21): Sim1 logs contain NONE of the live-account
            # lines above (verified: 0/5 matches on a 49KB session log). The only fill
            # evidence `strings` recovers is "Trade simulation fill. Bid/Ask/Last" and
            # the Flatten&Cancel position line. Without these the feed is blind on sim
            # days and the events file looks stalled.
            if is_sim:
                m = re.search(
                    r"Trade simulation fill\. Bid: ([\d.]+) Ask: ([\d.]+) Last: ([\d.]+)", line)
                if m:
                    events.append({
                        "type": "SIM_FILL",
                        "bid": float(m.group(1)),
                        "ask": float(m.group(2)),
                        "last": float(m.group(3)),
                        "scan_ts": ts_now,
                        "line": i,
                    })

                m = re.search(
                    r"Flatten&CancelAllOrders \| Last: ([\d.]+)\. "
                    r"Current Position quantity: (-?\d+)", line)
                if m:
                    events.append({
                        "type": "SIM_FLATTEN",
                        "last": float(m.group(1)),
                        "position_qty": int(m.group(2)),
                        "scan_ts": ts_now,
                        "line": i,
                    })
        except Exception as e:  # noqa: BLE001 — one bad line, not one bad day
            _PARSE_ERRORS.append({"line": i, "error": repr(e),
                                  "text": line[:200]})
            print(f"[trade_activity_feed] PARSE ERROR on line {i}: {e!r} :: "
                  f"{line[:160]}", file=sys.stderr)
            continue

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
    """Single extraction run. Returns new events.

    P9 fix (2026-07-22): when a sim account log doesn't exist for today, fall
    back to the live account log. Sierra writes to the real account even when
    MEMS26_MODE=sim + send_orders_to_trade_service=1 (Sim1 log only exists
    when Sierra's own is_sim=1 AND using a simulated account).
    """
    log_path = _today_log_path(account)
    if not log_path.exists():
        # Sim fallback: try live account log
        if account.lower().startswith("sim"):
            live_path = _today_log_path(LIVE_ACCOUNT)
            if live_path.exists():
                import sys
                print(f"[trade_activity_feed] {log_path.name} not found, "
                      f"falling back to {live_path.name}", file=sys.stderr)
                account = LIVE_ACCOUNT
                log_path = live_path
            else:
                return []
        else:
            return []

    # Offset key includes the LOG DAY (cowork 2026-07-28). It used to be
    # per-account only, but the log file is per-DAY: every new day started with
    # yesterday's large offset, so `i < last_offset` skipped whole sessions and
    # the journal silently lost them. That is why cross-checking trades against
    # the journal showed "Sierra saw nothing" for real trading days.
    day_tag = log_path.name.split("_")[1] if "_" in log_path.name else "unknown"
    offset_file = EXPORT_DIR / f".trade_activity_offset_{account}_{day_tag}"
    legacy = EXPORT_DIR / f".trade_activity_offset_{account}"
    last_offset = 0
    src = offset_file if offset_file.exists() else (legacy if legacy.exists() else None)
    if src is not None:
        try:
            last_offset = int(src.read_text().strip())
        except (ValueError, OSError):
            pass
        if src is legacy:
            last_offset = 0  # legacy value belongs to some other day — distrust it

    lines = _extract_text(log_path)

    # `strings` failing (non-zero exit or the 10s timeout on a big log) used to
    # return [] → new_offset 0 → the offset file was overwritten with 0 → the
    # NEXT poll re-emitted the entire file. Measured damage: 2363 journal events
    # of which only 309 were unique; one −125.00 close appeared 117 times, which
    # inflated every P&L sum built on this file. An empty extraction is now a
    # no-op that leaves the offset untouched.
    if not lines:
        print(f"[trade_activity_feed] extraction returned nothing for "
              f"{log_path.name} — keeping offset {last_offset} (no re-emit)",
              file=sys.stderr)
        return []

    # A shrinking line count means the extraction is not comparable to the
    # previous one; re-emitting from a lower offset would duplicate. Skip.
    if len(lines) < last_offset:
        print(f"[trade_activity_feed] line count shrank "
              f"({len(lines)} < offset {last_offset}) for {log_path.name} — "
              f"skipping this poll", file=sys.stderr)
        return []

    _PARSE_ERRORS.clear()
    events, new_offset = _parse_events(lines, last_offset, account=account)
    if _PARSE_ERRORS:
        # No silent failures (CLAUDE.md): the feed keeps going, but the operator
        # and the ops log both hear about it on the same poll.
        print(f"[trade_activity_feed] {len(_PARSE_ERRORS)} line(s) failed to "
              f"parse in {log_path.name} — feed CONTINUED, events may be "
              f"incomplete", file=sys.stderr)
        try:
            from scripts.ops_log import log_event
            log_event("trade_activity_feed", "WARNING",
                      f"{len(_PARSE_ERRORS)} unparsable line(s) in "
                      f"{log_path.name}: {_PARSE_ERRORS[0]['error']}")
        except Exception:
            pass

    if events:
        _append_events(events)
        print(f"[trade_activity_feed] {len(events)} new events from {log_path.name}")
        for ev in events:
            print(f"  {ev['type']}: {json.dumps({k: v for k, v in ev.items() if k != 'type'})}")

    offset_file.write_text(str(new_offset))
    return events


def _account_from_env() -> str:
    """--account auto (07-13): resolve the account from .env INSIDE python.

    Root cause: the LaunchAgent's bash is TCC-blocked from reading .env in
    ~/Downloads ('Operation not permitted') → `source .env` failed SILENTLY →
    MEMS26_MODE always defaulted to live → the sim branch in the plist was
    dead wiring. Python (Full Disk Access) reads the file fine, so the mode
    resolution lives here now. sim → SIERRA_SIM_ACCOUNT (Sim1), else live.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    cfg = {}
    try:
        for ln in env_path.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                cfg[k.strip()] = v.strip()
    except Exception as e:
        print(f"[trade_activity_feed] .env read failed ({e}) → live default", file=sys.stderr)
    if cfg.get("MEMS26_MODE", "live").lower() == "sim":
        return cfg.get("SIERRA_SIM_ACCOUNT", "Sim1")
    return cfg.get("SIERRA_LIVE_ACCOUNT", LIVE_ACCOUNT)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sierra TradeActivityLog feeder")
    parser.add_argument("--once", action="store_true", help="Single run, no polling")
    parser.add_argument("--account", default=LIVE_ACCOUNT,
                        help="Sierra account ID, or 'auto' to resolve from .env (MEMS26_MODE)")
    args = parser.parse_args()
    if args.account == "auto":
        args.account = _account_from_env()
        print(f"[trade_activity_feed] auto account → {args.account}")

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
