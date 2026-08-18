#!/usr/bin/env python3
"""SIM drill: does the compiled ladder actually protect all five contracts?

2026-08-18. Michael rebuilt the DLL at 10:47 and the 5-contract ruling went
live. Everything up to the DLL was verified by execution — effective_contracts,
the bracket cap, the ladder table, the contract→target map. One link was not,
and could not be without an order: whether the COMPILED study builds four OCO
groups summing to five, or whether it still brackets four and leaves the fifth
naked. That is the whole risk of moving above four contracts.

This fires ONE entry through the production writer (`command_from_setup`, the
same call the gateway makes) and then reads what Sierra actually holds.

PASS requires all of:
  * position_qty == 5                       (the order was not clipped)
  * closing-side stop quantities sum to 5   (every contract is behind a stop)
  * at least two distinct target prices     (the ladder is a ladder, not one leg)

Refuses to run unless Sierra reports `is_sim=1` and a flat account. Flattens
what it opened.

  python3 scripts/sim_drill_5_contracts.py            # fire + verify + flatten
  python3 scripts/sim_drill_5_contracts.py --verify   # verify an open position
  python3 scripts/sim_drill_5_contracts.py --flatten  # clean up only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
EXPORT = Path(os.getenv("MEMS26_SIGNALS_DIR",
                        os.path.expanduser("~/SierraChart_Data/v9_export")))
os.environ.setdefault("MEMS26_SIGNALS_DIR", str(EXPORT))

WANT = int(os.getenv("SIM_DRILL_CONTRACTS", "5"))
STATE = EXPORT / "sierra_state.json"


def state(max_age_s: float = 30.0) -> dict:
    d = json.loads(STATE.read_text())
    age = time.time() - float(d.get("ts", 0))
    if age > max_age_s:
        raise SystemExit(f"🔴 sierra_state is {age:.0f}s old — Sierra is not writing")
    return d


def _closing_side_stop_qty(d: dict) -> int:
    """Sum the quantities of stops that would CLOSE this position.

    Deliberately the same test the live guard uses (type 2/3 on the closing
    side), so a PASS here means the guard will also stay quiet in production.
    """
    qty, total = int(d.get("position_qty") or 0), 0
    for o in d.get("orders") or []:
        typ, bs = o.get("type"), int(o.get("bs", 0))
        if typ is None:
            continue
        if int(typ) in (2, 3) and ((qty > 0 and bs == 2) or (qty < 0 and bs == 1)):
            total += abs(int(o.get("qty", 0) or 0))
    return total


def _target_prices(d: dict) -> list:
    qty = int(d.get("position_qty") or 0)
    out = []
    for o in d.get("orders") or []:
        if o.get("type") is None:
            continue
        bs = int(o.get("bs", 0))
        if int(o["type"]) == 1 and ((qty > 0 and bs == 2) or (qty < 0 and bs == 1)):
            out.append(float(o.get("price", 0) or 0))
    return sorted(set(out))


def fire() -> None:
    d = state()
    if not int(d.get("is_sim", 0)):
        raise SystemExit("🔴 REFUSING: Sierra reports is_sim=0. This drill places "
                         "an order — it runs on SIM only.")
    if int(d.get("position_qty") or 0) != 0:
        raise SystemExit(f"🔴 REFUSING: account is not flat "
                         f"(position_qty={d['position_qty']}). Nothing here may "
                         f"run on top of an existing position.")
    if not int(d.get("order_placement_armed", 0)):
        raise SystemExit("🔴 REFUSING: order placement is not armed (Input #21)")

    px = float(d["last_price"])
    tick = lambda x: round(round(x / 0.25) * 0.25, 2)
    # LONG, deliberately roomy: a 25pt stop and far targets so nothing fills
    # while we look at the bracket. The drill is about SHAPE, not P&L.
    setup = {
        "firing_system": 4, "direction": "LONG",
        "entry_price": tick(px), "stop": tick(px - 25.0),
        "t1": tick(px + 20.0), "t2": tick(px + 30.0), "t3": tick(px + 40.0),
        "contracts": WANT, "classification": "SIM_DRILL_%dC" % WANT,
        "metadata": {"sizing_contracts": WANT, "pattern": "SIM_DRILL_%dC" % WANT},
    }
    from backend.v9.services.sierra_command import command_from_setup, effective_contracts
    n = effective_contracts(setup)
    print(f"  backend resolves → {n} contracts")
    if n != WANT:
        raise SystemExit(f"🔴 the backend itself would send {n}, not {WANT} — "
                         f"fix that before asking the DLL anything")
    command_from_setup(setup, trade_id="SIMDRILL5",
                       account=str(d.get("trade_account") or "Sim1"), mode="demo")
    print(f"  → wrote the command: LONG {WANT} @market ~{setup['entry_price']:.2f} "
          f"stop {setup['stop']:.2f}")


def verify(settle_s: int = 25) -> int:
    print(f"  waiting {settle_s}s for the fill and the attached bracket…")
    time.sleep(settle_s)
    d = state()
    qty = int(d.get("position_qty") or 0)
    covered = _closing_side_stop_qty(d)
    targets = _target_prices(d)
    print(f"\n  Sierra holds : {qty:+d} contracts")
    print(f"  stops cover  : {covered}")
    print(f"  target prices: {targets}")
    print(f"  raw orders   : {json.dumps(d.get('orders') or [], ensure_ascii=False)}")

    checks = [
        (f"position == {WANT}", qty == WANT,
         f"got {qty} — the order was clipped somewhere" if qty != WANT else "ok"),
        (f"every contract behind a stop ({covered}/{abs(qty)})", covered >= abs(qty),
         f"{abs(qty) - covered} contract(s) NAKED" if covered < abs(qty) else "ok"),
        ("the ladder has ≥2 distinct targets", len(targets) >= 2,
         f"{len(targets)} target price(s) — not a ladder" if len(targets) < 2 else "ok"),
    ]
    print()
    bad = 0
    for name, ok, detail in checks:
        print(f"  {'✅' if ok else '🔴'} {name} — {detail}")
        bad += 0 if ok else 1
    print(f"\n{'🟢 PASS — the compiled ladder protects all %d.' % WANT if not bad else '🔴 FAIL — do NOT trade %d contracts.' % WANT}")
    return 0 if not bad else 1


def flatten() -> None:
    d = state()
    if int(d.get("position_qty") or 0) == 0:
        print("  already flat")
        return
    if not int(d.get("is_sim", 0)):
        raise SystemExit("🔴 REFUSING to flatten a non-sim account from a drill")
    from backend.v9.services.sierra_command import write_flatten_account
    write_flatten_account(trade_id="SIMDRILL5", reason="sim drill cleanup")
    time.sleep(8)
    print(f"  after flatten: position_qty={state()['position_qty']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--flatten", action="store_true")
    ap.add_argument("--keep", action="store_true", help="do not flatten after verifying")
    a = ap.parse_args()
    if a.flatten:
        flatten(); raise SystemExit(0)
    if a.verify:
        raise SystemExit(verify(settle_s=2))
    fire()
    rc = verify()
    if not a.keep:
        flatten()
    raise SystemExit(rc)
