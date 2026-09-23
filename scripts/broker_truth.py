#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""broker_truth.py — the broker's own closed-trade P&L, per system trade (Michael 23.09 07:40:
"הנתונים של יומן-המסחר לא נכונים … חייבים לאמת מול סיירה מה ההפסד ומה הרווח").

Source of truth: Sierra's trade-activity stream as exported by the DLL —
~/SierraChart_Data/v9_export/trade_activity_events.jsonl — records of type
POSITION_CHANGE (order_id, prev_qty→new_qty, ts) and CLOSED_TRADE_PNL (pnl NET of
commissions, ts). A round-trip = position leaves 0 (entry order) … returns to 0 (exit
order) + the CLOSED_TRADE_PNL logged at the same instant. This is what the account
statement shows; the fills journal (scripts/pnl_reconcile.py) repeats the books' own
prices and misses flatten exits (MAE_SCRATCH), so it cannot be the truth.

Matching (exact chain, no clock guessing): v9_trades row → the DLL's fills journal
(trade_fills_journal.jsonl, kind=ENTRY: fill ts + direction + price + Sierra order_id)
→ the round-trip whose POSITION_CHANGE carries that order_id. scan_ts is only the time
the DLL *noticed* the log line (02.09 the whole log was back-filled at 23:26), so it is
used only as a fallback (±5 min, same direction). A round-trip whose max qty exceeds the
trade's contracts is flagged mixed=True — Michael's manual contracts (T-402) sat in the same
position, so the broker figure is the position's, not the system's alone. (A multi-contract
entry is several Sierra orders — per-contract OCO — so the journal's first order id may not
be the one that opened the position; that is "order-joined", normal, not mixed.)
Unmatched round-trips are listed (manual trades). Trades with no broker record at all
(01.09: export not yet scanning; 15.09 evening: scanner gap) stay NULL — honest failure.

  python3 scripts/broker_truth.py [--since 2026-09-01] [--write] [--json out]
--write sets ONLY v9_trades.pnl_sierra (never pnl_usd); reversible.
"""
import os, sys, json, argparse, datetime as dt, subprocess
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
IL = ZoneInfo("Asia/Jerusalem")
EVENTS = os.path.expanduser("~/SierraChart_Data/v9_export/trade_activity_events.jsonl")
JOURNAL = os.path.expanduser("~/SierraChart_Data/v9_export/trade_fills_journal.jsonl")
PSQL = "/Applications/Postgres.app/Contents/Versions/18/bin/psql"

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="2026-09-01")
ap.add_argument("--write", action="store_true")
ap.add_argument("--json", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data", "broker.json"))
args = ap.parse_args()

def ts_of(e):
    s = e.get("scan_ts") or e.get("ts")
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None

evs = []
for line in open(EVENTS, encoding="utf-8"):
    line = line.strip()
    if not line: continue
    try: e = json.loads(line)
    except Exception: continue
    if e.get("is_sim") is True or (e.get("account") and e["account"] != "37138283"): continue
    t = ts_of(e)
    if t is None or t < dt.datetime.fromisoformat(args.since + "T00:00:00+00:00"): continue
    e["_t"] = t; evs.append(e)
evs.sort(key=lambda e: (e["_t"], e.get("line", 0)))

# round-trips from position changes; pnl from the CLOSED_TRADE_PNL at the same instant
rts = []; open_rt = None
for e in evs:
    if e["type"] == "POSITION_CHANGE":
        pq, nq = e.get("prev_qty") or 0, e.get("new_qty") or 0
        if pq == 0 and nq != 0:
            open_rt = {"entry_ts": e["_t"], "entry_order": e.get("order_id"), "dir": "LONG" if nq > 0 else "SHORT", "qty": abs(nq), "pnl": 0.0, "legs": 0, "orders": [e.get("order_id")]}
        elif nq == 0 and pq != 0 and open_rt:
            open_rt["exit_ts"] = e["_t"]; open_rt["exit_order"] = e.get("order_id"); open_rt["orders"].append(e.get("order_id")); rts.append(open_rt); open_rt = None
        elif open_rt is not None:
            open_rt["qty"] = max(open_rt["qty"], abs(nq), abs(pq)); open_rt["orders"].append(e.get("order_id"))
    elif e["type"] == "CLOSED_TRADE_PNL":
        target = open_rt if open_rt is not None else (rts[-1] if rts and abs((rts[-1]["exit_ts"] - e["_t"]).total_seconds()) <= 5 else None)
        if target is not None:
            target["pnl"] += float(e.get("pnl") or 0); target["legs"] += 1
by_entry_order = {r["entry_order"]: k for k, r in enumerate(rts)}
by_any_order = {}
for k, r in enumerate(rts):
    for o in r["orders"]: by_any_order.setdefault(o, k)

# DLL fills journal: ENTRY rows carry the Sierra order id of the system's entry fill
journal = []
if os.path.exists(JOURNAL):
    for line in open(JOURNAL, encoding="utf-8"):
        try: j = json.loads(line)
        except Exception: continue
        if j.get("kind") == "ENTRY" and j.get("ts"):
            journal.append((dt.datetime.fromtimestamp(int(j["ts"]), tz=dt.timezone.utc), j))

trades = read_all("""select id, mode, direction, entry_ts, exit_ts, entry_price, exit_price, exit_reason, pnl_usd, pnl_sierra, pattern_id_at_entry pat,
  coalesce((quality->>'contracts')::int, 1) contracts
  from v9_trades where mode='live' and state='CLOSED' and entry_ts >= :s order by entry_ts""", {"s": args.since})
used = set(); rows = []
for t in trades:
    k = None; how = None; order = None
    # 1) exact: journal ENTRY (±3 min, same direction, same price when present) → order id → round-trip
    cand = [(abs((jt - t["entry_ts"]).total_seconds()), j) for jt, j in journal
            if j.get("direction") == t["direction"] and abs((jt - t["entry_ts"]).total_seconds()) <= 180
            and (t["entry_price"] is None or j.get("price") is None or abs(float(j["price"]) - float(t["entry_price"])) < 0.01)]
    if cand:
        order = int(min(cand, key=lambda c: c[0])[1]["order_id"])
        if order in by_entry_order and by_entry_order[order] not in used: k, how = by_entry_order[order], "order"
        elif order in by_any_order and by_any_order[order] not in used: k, how = by_any_order[order], "order-joined"
    # 2) fallback: nearest round-trip by scan time (±5 min, same direction)
    if k is None:
        best = None
        for kk, r in enumerate(rts):
            if kk in used or r["dir"] != t["direction"]: continue
            dsec = abs((r["entry_ts"] - t["entry_ts"]).total_seconds())
            if dsec <= 300 and (best is None or dsec < best[0]): best = (dsec, kk)
        if best: k, how = best[1], "time"
    base = dict(id=t["id"], pat=t["pat"], dir=t["direction"], day=t["entry_ts"].astimezone(IL).date().isoformat(),
                entry=t["entry_ts"].astimezone(IL).strftime("%H:%M"), books=float(t["pnl_usd"]) if t["pnl_usd"] is not None else None,
                reason=t["exit_reason"], had_sierra=t["pnl_sierra"], contracts=int(t["contracts"]), entry_order=order, match=how)
    if k is not None:
        used.add(k); r = rts[k]
        # per-contract attached OCO ⇒ a multi-contract entry is several Sierra orders, so the journal's
        # first order id may not be the one that opened the position ("order-joined" is normal there);
        # mixed only when the position was bigger than the system's size (manual contracts, T-402)
        mixed = r["qty"] > int(t["contracts"])
        rows.append(dict(base, broker=round(r["pnl"], 2), delta=round(r["pnl"] - float(t["pnl_usd"] or 0), 2), qty=r["qty"],
                         exit_order=r["exit_order"], mixed=mixed, legs=r["legs"],
                         broker_exit=r["exit_ts"].astimezone(IL).strftime("%H:%M")))
    else:
        rows.append(dict(base, broker=None, delta=None, qty=None, exit_order=None, mixed=False, legs=0, broker_exit=None))
unmatched = [dict(day=r["entry_ts"].astimezone(IL).date().isoformat(), entry=r["entry_ts"].astimezone(IL).strftime("%H:%M"),
                  exit=r["exit_ts"].astimezone(IL).strftime("%H:%M"), dir=r["dir"], qty=r["qty"], pnl=round(r["pnl"], 2), order=r["entry_order"])
             for k, r in enumerate(rts) if k not in used]

print(f"events since {args.since}: {len(evs)} · round-trips {len(rts)} · journal entries {len(journal)} · live trades {len(trades)} · matched {sum(1 for r in rows if r['broker'] is not None)} (by order id {sum(1 for r in rows if (r['match'] or '').startswith('order'))})")
print(f"{'id':>6} {'day':10} {'entry':5} {'dir':5} {'pattern':20} {'c':>2} {'books':>8} {'broker':>8} {'Δ':>7} {'match':12} {'qty':>3}  reason")
for r in rows:
    b = "—" if r["books"] is None else f"{r['books']:+.2f}"; s = "—" if r["broker"] is None else f"{r['broker']:+.2f}"; d = "—" if r["delta"] is None else f"{r['delta']:+.2f}"
    print(f"{r['id']:>6} {r['day']:10} {r['entry']:5} {r['dir']:5} {(r['pat'] or '')[:20]:20} {r['contracts']:>2} {b:>8} {s:>8} {d:>7} {(r['match'] or '—'):12} {('' if r['qty'] is None else r['qty']):>3}  {r['reason'] or ''}{'  MIXED' if r['mixed'] else ''}")
tb = sum(r["books"] or 0 for r in rows); ts_ = sum(r["broker"] or 0 for r in rows if r["broker"] is not None)
print(f"\nΣ books {tb:+.2f} · Σ broker (matched) {ts_:+.2f} · book error {ts_ - tb:+.2f}")
print(f"unmatched broker round-trips (not the system's — T-402): {len(unmatched)} · Σ {sum(u['pnl'] for u in unmatched):+.2f}")
for u in unmatched[-12:]:
    print(f"   {u['day']} {u['entry']}→{u['exit']} {u['dir']} x{u['qty']} {u['pnl']:+.2f} (order {u['order']})")

# per-day totals
days = {}
for r in rows:
    d = days.setdefault(r["day"], {"books": 0.0, "broker": 0.0, "n": 0, "matched": 0})
    d["n"] += 1; d["books"] += r["books"] or 0
    if r["broker"] is not None: d["broker"] += r["broker"]; d["matched"] += 1
for u in unmatched:
    days.setdefault(u["day"], {"books": 0.0, "broker": 0.0, "n": 0, "matched": 0})["manual"] = days[u["day"]].get("manual", 0.0) + u["pnl"]
os.makedirs(os.path.dirname(args.json), exist_ok=True)
json.dump({"generated": dt.datetime.now(IL).isoformat(timespec="minutes"), "since": args.since, "trades": rows, "unmatched": unmatched, "days": days},
          open(args.json, "w"), ensure_ascii=False, indent=0, default=str)
if args.write:
    n = 0
    for r in rows:
        if r["broker"] is None or r["mixed"]: continue   # mixed = position P&L, not the system's → stays NULL (Rule 1)
        if r["had_sierra"] is not None and abs(float(r["had_sierra"]) - r["broker"]) < 0.005: continue
        subprocess.run([PSQL, os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"), "-X", "-q", "-c",
                        f"UPDATE v9_trades SET pnl_sierra = {r['broker']} WHERE id = {r['id']} AND state='CLOSED'"], check=True)
        n += 1
    print(f"wrote pnl_sierra on {n} rows (pnl_usd untouched)")
else:
    print("(dry-run — pass --write to persist pnl_sierra)")
