#!/usr/bin/env python3
"""W8 PLACE_STOP v2 — SIM verification script (2026-07-28).

Three hard requirements to verify:
1. TradeAccount = sc.SelectedTradeAccount (root of r=-1 on 07-20)
2. Side check: LONG→SELL stop below, SHORT→BUY stop above
3. Never op=EXIT — standalone sc.SubmitOrder only

VERIFICATION PROTOCOL (Michael 07-28):
- orders[] BEFORE and AFTER in sim — green test suite is NOT evidence
- This script reads live sierra_state.json, sends PLACE_STOP, and
  compares working orders before/after

Prerequisites:
- Sierra in SIM mode (is_sim=1)
- A manual position open (create in Sierra before running)
- Backend NOT needed (writes directly to trade_command.json)

Usage:
  python3 scripts/verify_place_stop_v2_sim.py --side LONG --price 7450.0
  python3 scripts/verify_place_stop_v2_sim.py --side SHORT --price 7550.0
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

SIGNALS_DIR = Path(os.path.expanduser(
    os.getenv("MEMS26_SIGNALS_DIR", "~/SierraChart_Data/v9_export")))
STATE_FILE = SIGNALS_DIR / "sierra_state.json"
COMMAND_FILE = SIGNALS_DIR / "trade_command.json"
RESULT_FILE = SIGNALS_DIR / "trade_result.json"

import re as _re
def _safe_json(raw):
    return json.loads(_re.sub(r':\s*-?inf\b', ':null', raw))


def read_state():
    raw = STATE_FILE.read_text().strip()
    return _safe_json(raw)


def main():
    parser = argparse.ArgumentParser(description="W8 PLACE_STOP v2 SIM verification")
    parser.add_argument("--side", required=True, choices=["LONG", "SHORT"])
    parser.add_argument("--price", required=True, type=float)
    parser.add_argument("--qty", type=int, default=0, help="0 = use abs(position_qty)")
    args = parser.parse_args()

    print("=" * 60)
    print("W8 PLACE_STOP v2 — SIM VERIFICATION")
    print("=" * 60)

    # 1. Read state BEFORE
    state_before = read_state()
    is_sim = state_before.get("is_sim", 0)
    pos_qty = state_before.get("position_qty", 0)
    working_before = state_before.get("working_orders", 0)
    orders_before = state_before.get("orders", [])

    print(f"\n[BEFORE] is_sim={is_sim} position_qty={pos_qty} "
          f"working_orders={working_before} orders={json.dumps(orders_before)}")

    # Safety checks
    if is_sim != 1:
        print("\n❌ ABORT: is_sim != 1 — NOT in SIM mode. Will not send PLACE_STOP on live.")
        sys.exit(1)

    if pos_qty == 0:
        print("\n❌ ABORT: position_qty=0 — no position to protect. "
              "Open a manual position in Sierra SIM first.")
        sys.exit(1)

    # Verify side matches position
    if args.side == "LONG" and pos_qty < 0:
        print(f"\n❌ ABORT: side=LONG but position_qty={pos_qty} (SHORT). "
              "Side must match position.")
        sys.exit(1)
    if args.side == "SHORT" and pos_qty > 0:
        print(f"\n❌ ABORT: side=SHORT but position_qty={pos_qty} (LONG). "
              "Side must match position.")
        sys.exit(1)

    qty = args.qty if args.qty > 0 else abs(pos_qty)

    # 2. Record result file mtime before command
    pre_mtime = RESULT_FILE.stat().st_mtime if RESULT_FILE.exists() else 0.0

    # 3. Write PLACE_STOP command (no "account" field — DLL uses SelectedTradeAccount)
    command = {
        "op": "PLACE_STOP",
        "qty": qty,
        "price": round(args.price, 2),
        "side": args.side,
        "ts_submitted": time.time(),
    }
    print(f"\n[COMMAND] {json.dumps(command)}")
    COMMAND_FILE.write_text(json.dumps(command))

    # 4. Poll for result (5s timeout)
    print("\n[WAITING] Polling trade_result.json for PLACE_STOP result...")
    deadline = time.time() + 8.0
    result = None
    while time.time() < deadline:
        time.sleep(0.3)
        try:
            if RESULT_FILE.exists():
                mtime = RESULT_FILE.stat().st_mtime
                if mtime > pre_mtime:
                    raw = RESULT_FILE.read_text().strip()
                    if raw:
                        data = json.loads(raw)
                        status = data.get("status", "")
                        if "PLACE_STOP" in status:
                            result = data
                            break
        except Exception:
            pass

    if result is None:
        print("\n❌ TIMEOUT: No PLACE_STOP result within 8s. "
              "Check Sierra Message Log for errors.")
        sys.exit(1)

    print(f"\n[RESULT] {json.dumps(result)}")

    # 5. Wait 2s for state to update, then read AFTER
    time.sleep(2.0)
    state_after = read_state()
    working_after = state_after.get("working_orders", 0)
    orders_after = state_after.get("orders", [])

    print(f"\n[AFTER] position_qty={state_after.get('position_qty')} "
          f"working_orders={working_after} orders={json.dumps(orders_after)}")

    # 6. Verdict
    print("\n" + "=" * 60)
    status = result.get("status", "")
    if status == "PLACE_STOP_OK":
        if working_after > working_before:
            print(f"✅ PLACE_STOP_OK — working_orders {working_before}→{working_after}")
            print(f"   Stop placed: {args.side} stop @ {args.price} for {qty}c")
            print("   Verify in Sierra: Trade → Trade Orders — the stop should be visible")
        else:
            print(f"⚠️  PLACE_STOP_OK but working_orders unchanged "
                  f"({working_before}→{working_after})")
            print("   Check Sierra Trade Orders manually")
    else:
        error = result.get("error", "?")
        print(f"❌ {status} (error={error})")
        if "SIDE_MISMATCH" in status:
            print("   Side doesn't match position sign")
        elif "NO_POSITION" in status:
            print("   Position is flat — nothing to protect")
        elif "BAD_INPUT" in status:
            print("   Invalid qty/price/side")
        elif "FAIL" in status:
            print("   sc.SubmitOrder returned error. Check Sierra Message Log")

    print("=" * 60)


if __name__ == "__main__":
    main()
