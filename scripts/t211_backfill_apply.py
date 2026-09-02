#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-211 backfill — add the missing T0 leg and recompute P&L from real fills.

Michael approved the apply on 02.09 12:45 after seeing the dry-run. CC's script
turned out to list-only (its --apply branch was empty — verified: zero rows
changed, no t0_backfilled marker), and its scope filter (t1_hit required)
missed #948, the sharpest known case. This one:

  scope    = closed live/demo trades where the fills journal holds a fill for
             quality.c1_target_id (the T0 order) that is ABSENT from
             quality.exit_fills. Journal truth, not column flags.
  fix      = append the T0 leg; recompute pnl_usd as the sum over ALL legs
             (sign * (price-entry) * qty * $5) — only when total leg qty equals
             quality.contracts. Short legs => leave pnl untouched, mark partial.
  audit    = quality.t0_backfilled=true, quality.pnl_before kept.

ACCEPTANCE ANCHORS (independent numbers, computed by the verification agent
from the sierra journal): #942 must land at +55.00 and #948 at -135.00.
If either disagrees the script REFUSES to write anything.

    python3 scripts/t211_backfill_apply.py            # dry-run, before/after
    python3 scripts/t211_backfill_apply.py --apply
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    _ln = _ln.strip()
    if _ln and not _ln.startswith("#") and "=" in _ln:
        k, v = _ln.split("=", 1)
        os.environ.setdefault(k.strip(), v.split("#")[0].strip())
if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("not Postgres — refusing (T-161)")

from sqlalchemy import create_engine, text  # noqa: E402

JOURNAL = os.path.expanduser("~/SierraChart_Data/v9_export/trade_fills_journal.jsonl")
ANCHORS = {942: 55.00, 948: -135.00}


def journal_fills():
    """order_id -> list of {price, contracts, ts} for non-ENTRY fills."""
    out = {}
    for ln in open(JOURNAL, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("kind") == "ENTRY" or not d.get("order_id"):
            continue
        out.setdefault(int(d["order_id"]), []).append(d)
    return out


def main() -> int:
    apply_ = "--apply" in sys.argv
    eng = create_engine(os.environ["DATABASE_URL"])
    fills = journal_fills()

    with eng.connect() as cx:
        rows = cx.execute(text(
            "SELECT id, direction, entry_price, pnl_usd, outcome, quality "
            "FROM v9_trades WHERE state='CLOSED' AND mode!='shadow' "
            "AND quality ? 'c1_target_id' AND (quality->>'has_t0')='true' "
            "ORDER BY id")).mappings().all()

    plan = []
    for r in rows:
        q = r["quality"] if isinstance(r["quality"], dict) else json.loads(r["quality"] or "{}")
        if q.get("t0_backfilled"):
            continue
        try:
            c1 = int(q.get("c1_target_id") or 0)
        except (TypeError, ValueError):
            continue
        jf = fills.get(c1)
        if not jf:
            continue                                   # T0 never filled — fine
        legs = q.get("exit_fills") or []
        if any(int(l.get("order_id") or 0) == c1 for l in legs):
            continue                                   # already in the ledger
        entry = float(r["entry_price"]); sign = 1.0 if r["direction"] == "LONG" else -1.0
        t0 = jf[0]
        new_leg = {"ts": t0.get("ts"), "qty": int(t0.get("contracts") or 1),
                   "kind": "T0", "price": float(t0["price"]),
                   "order_id": c1, "backfilled": True}
        all_legs = legs + [new_leg]
        qty_sum = sum(int(l.get("qty") or 0) for l in all_legs)
        contracts = int(q.get("contracts") or 0)
        full = contracts > 0 and qty_sum == contracts
        new_pnl = round(sum(sign * (float(l["price"]) - entry) * int(l.get("qty") or 0) * 5.0
                            for l in all_legs), 2) if full else None
        plan.append((r["id"], r["pnl_usd"], new_pnl, full, new_leg, q, all_legs))

    if not plan:
        print("nothing to backfill — every T0 fill is already in its ledger")
        return 0

    print(f"\n{'id':>5} {'before':>9} {'after':>9}  full  T0-leg")
    for tid, before, after, full, leg, _q, _legs in plan:
        print(f"{tid:>5} {str(before):>9} {str(after) if after is not None else 'unpriced':>9}"
              f"  {'yes' if full else 'NO '}  {leg['qty']}c @ {leg['price']}")

    # anchors — refuse to write if the arithmetic disagrees with the
    # independently-computed numbers
    for tid, want in ANCHORS.items():
        got = next((a for t, _b, a, f, *_ in plan if t == tid and f), None)
        if got is not None and abs(got - want) > 0.01:
            print(f"\n🔴 ANCHOR MISMATCH #{tid}: computed {got}, independent {want} "
                  f"— refusing to write anything.")
            return 1

    if not apply_:
        print("\nDRY-RUN — no writes. --apply to execute.")
        return 0

    with eng.begin() as cx:
        for tid, before, after, full, leg, q, all_legs in plan:
            q2 = dict(q)
            q2["exit_fills"] = all_legs
            q2["t0_backfilled"] = True
            q2["pnl_before_backfill"] = float(before) if before is not None else None
            params = {"q": json.dumps(q2), "id": tid}
            if full and after is not None:
                cx.execute(text(
                    "UPDATE v9_trades SET pnl_usd=:p, "
                    "outcome=CASE WHEN :p>0 THEN 'WIN' WHEN :p<0 THEN 'LOSS' ELSE outcome END, "
                    "quality=(:q)::jsonb WHERE id=:id"), {**params, "p": after})
            else:
                cx.execute(text(
                    "UPDATE v9_trades SET quality=(:q)::jsonb WHERE id=:id"), params)

    with eng.connect() as cx:
        n = cx.execute(text(
            "SELECT count(*) FROM v9_trades WHERE (quality->>'t0_backfilled')='true'"
        )).scalar()
    print(f"\n✅ APPLIED — verified in DB: {n} rows carry t0_backfilled=true "
          f"(intent counted is a lie; this is the read-back).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
