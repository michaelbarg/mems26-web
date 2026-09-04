#!/usr/bin/env python3
"""T-256 — per-trade books-vs-broker, joined on Sierra's **InternalOrderID**.

    python3 scripts/sierra_activity_join.py                 # dry-run report
    python3 scripts/sierra_activity_join.py --date 2026-09-04
    python3 scripts/sierra_activity_join.py --json
    python3 scripts/sierra_activity_join.py --write         # persists pnl_sierra

Why this exists (2026-09-04): `pnl_sierra` was NULL on 6/6 of the day's live
rows, so the ONLY books-vs-broker check we had was the daily aggregate — and
that day proved the aggregate worthless: books said -97.50, the broker said
-116.25, and on other days the same two numbers agree **by luck** while
individual rows are wrong in both directions.

What it does NOT do (T-229's mistake, do not repeat): it never matches a fill
to a trade by price proximity. The join key is the InternalOrderID that Sierra
assigns at submit and that we already persist on the trade
(`v9_trades.quality->>'sierra_order_id'` + the c1..c4 target/stop ids).

Ground truth, in order of authority:
  1. `Closed Trade Profit/Loss` records in Sierra's TradeActivityLog — the money
     the broker actually moved. Their sum equals `acct_daily_pl` exactly.
  2. The fill price on each order (TLV field 113, price*100).
Both come from the same binary log, which — contrary to the comment in
scripts/trade_activity_feed.py — DOES carry a per-record microsecond timestamp
(TLV field 102, SCDateTime µs since 1899-12-30). `strings` throws it away.

`--write` touches ONE column, `pnl_sierra`, never `pnl_usd`, so it cannot
launder a bad book into looking right. Reversible with
`UPDATE v9_trades SET pnl_sierra = NULL WHERE id IN (...)`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import struct
import sys
from pathlib import Path

_CLOSED_PNL_RE = re.compile(r"Closed Trade Profit/Loss:\s*(-?\d+(?:\.\d+)?)")

SIERRA_DIR = Path(os.path.expanduser("~/SierraChart/TradeActivityLogs"))
LIVE_ACCOUNT = os.getenv("SIERRA_LIVE_ACCOUNT", "37138283")
DSN = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
POINT_VALUE = 5.0                     # MES = $5 / point
PRICE_SCALE = 100.0                   # TLV 113 stores price * 100

# ---- Sierra TradeActivityLog binary layout (TLV: <u32 field><u32 len><bytes>)
F_RECORD_HEAD = 100      # int64, always -1 — marks the start of a record
F_ACTIVITY_TYPE = 101    # int32: 1=order activity, 2=trade activity, 3=position, 4=cash
F_TS = 102               # int64  SCDateTime microseconds since 1899-12-30
F_SYMBOL = 103
F_TEXT = 104
F_INTERNAL_ORDER_ID = 105   # int64
F_ORDER_TYPE = 107          # "Market" / "Limit" / "Stop Limit"
F_FILL_PRICE = 113          # double, price * 100
F_FILL_QTY = 114            # double, CUMULATIVE filled qty on that order
F_ACCOUNT = 118
F_PARENT_TEXT = 130         # "Parent order" / "Attached order. Parent: <id>"
SC_EPOCH = dt.datetime(1899, 12, 30, tzinfo=dt.timezone.utc)
_HEAD = struct.pack("<II", F_RECORD_HEAD, 8)


# ------------------------------------------------------------------ parsing

def _tlv(buf: bytes):
    i, n = 0, len(buf)
    while i + 8 <= n:
        fid, ln = struct.unpack_from("<II", buf, i)
        if ln > n - (i + 8):
            return
        yield fid, buf[i + 8:i + 8 + ln]
        i += 8 + ln


def read_records(path: Path) -> list[dict]:
    """Split the binary log into records. Field 100 is the record header."""
    data = path.read_bytes()
    starts, p = [], data.find(_HEAD)
    while p != -1:
        starts.append(p)
        p = data.find(_HEAD, p + 1)
    starts.append(len(data))
    out = []
    for a, b in zip(starts, starts[1:]):
        rec: dict = {}
        for fid, raw in _tlv(data[a:b]):
            rec.setdefault(fid, raw)          # first wins; records never repeat
        out.append(rec)
    return out


def _s(rec, fid):
    raw = rec.get(fid)
    return raw.decode("ascii", "replace") if raw else None


def _f(rec, fid):
    raw = rec.get(fid)
    if not raw or len(raw) != 8:
        return None
    v = struct.unpack("<d", raw)[0]
    return None if abs(v) > 1e300 else v       # Sierra's DBL_MAX sentinel


def _i(rec, fid):
    raw = rec.get(fid)
    if not raw:
        return None
    if len(raw) == 8:
        return struct.unpack("<q", raw)[0]
    if len(raw) == 4:
        return struct.unpack("<i", raw)[0]
    return None


def _ts(rec):
    v = _i(rec, F_TS)
    return SC_EPOCH + dt.timedelta(microseconds=v) if v else None


def parse_activity(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (fill_events, closed_pnl_events), both in file order.

    A fill event is one execution: {order_id, price, qty, ts, order_type,
    parent_text}. `qty` is the DELTA for that execution — TLV 114 is cumulative
    per order, so a 2-lot that fills 1+1 shows up as cum 1 then cum 2 and must
    be differenced or the second lot is double-counted.
    """
    fills: list[dict] = []
    pnls: list[dict] = []
    cum: dict[int, float] = {}
    for rec in read_records(path):
        text = _s(rec, F_TEXT) or ""
        atype = _i(rec, F_ACTIVITY_TYPE)
        m = _CLOSED_PNL_RE.search(text)
        if m:
            pnls.append({"ts": _ts(rec), "amount": float(m.group(1)),
                         "text": text[:80]})
            continue
        # Only activity-type 2 ("trade activity") — type 1 is the order-side
        # echo of the same execution and would double every fill.
        if atype != 2 or ("Filled)" not in text and "Partial fill)" not in text):
            continue
        oid, raw_px, cum_qty = (_i(rec, F_INTERNAL_ORDER_ID),
                                _f(rec, F_FILL_PRICE), _f(rec, F_FILL_QTY))
        if oid is None or raw_px is None or cum_qty is None:
            continue
        delta = cum_qty - cum.get(oid, 0.0)
        cum[oid] = cum_qty
        if delta <= 0:
            continue
        fills.append({"order_id": oid, "price": raw_px / PRICE_SCALE,
                      "qty": delta, "ts": _ts(rec),
                      "order_type": _s(rec, F_ORDER_TYPE),
                      "parent": _s(rec, F_PARENT_TEXT) or ""})
    return fills, pnls


def attach_pnl(fills: list[dict], pnls: list[dict]) -> None:
    """Attach each Closed-Trade-P/L record to the execution that produced it.

    Sierra emits the cash record microseconds AFTER the fill that closed the
    lot, and before the next fill. So: most recent fill strictly earlier in
    time. Verified 2026-09-04 — all 22 records land on a fill and the
    per-fill arithmetic reproduces each amount to the cent.
    """
    for f in fills:
        f["broker_pnl"] = None
    for p in pnls:
        best = None
        for f in fills:
            if f["ts"] and p["ts"] and f["ts"] < p["ts"]:
                if best is None or f["ts"] > best["ts"]:
                    best = f
        if best is not None:
            best["broker_pnl"] = (best.get("broker_pnl") or 0.0) + p["amount"]


# ------------------------------------------------------------------- books

def fetch_trades(dsn: str, day: str) -> list[dict]:
    import psycopg2
    import psycopg2.extras
    sql = """
        SELECT id, mode, firing_system, direction, entry_price, exit_price,
               exit_reason, pnl_usd, pnl_sierra, quality
          FROM v9_trades
         WHERE mode IN ('live', 'demo')
           AND (entry_ts AT TIME ZONE 'America/New_York')::date = %s
         ORDER BY id
    """
    with psycopg2.connect(dsn) as cn:
        with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET lock_timeout = '3s'")
            cur.execute(sql, (day,))
            return [dict(r) for r in cur.fetchall()]


_EXIT_ID_KEYS = tuple(f"c{i}_{side}_id" for i in range(1, 7)
                      for side in ("target", "stop"))


def order_ids(trade: dict) -> tuple[int | None, set[int]]:
    q = trade.get("quality") or {}
    if not isinstance(q, dict):
        q = {}

    def as_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    entry = as_int(q.get("sierra_order_id"))
    exits = {i for i in (as_int(q.get(k)) for k in _EXIT_ID_KEYS)
             if i is not None and i != 0}
    return entry, exits


def reconcile(trades: list[dict], fills: list[dict]) -> list[dict]:
    by_oid: dict[int, list[dict]] = {}
    for f in fills:
        by_oid.setdefault(f["order_id"], []).append(f)
    out = []
    for t in trades:
        e_oid, x_oids = order_ids(t)
        e_fills = by_oid.get(e_oid, []) if e_oid else []
        x_fills = [f for o in sorted(x_oids) for f in by_oid.get(o, [])]
        qty = sum(f["qty"] for f in e_fills) or None
        broker_entry = (sum(f["price"] * f["qty"] for f in e_fills) / qty
                        if qty else None)
        sign = 1.0 if (t["direction"] or "").upper() == "LONG" else -1.0
        # (a) the broker's own money, summed from Closed Trade Profit/Loss
        booked = [f["broker_pnl"] for f in x_fills if f.get("broker_pnl") is not None]
        pnl_broker = round(sum(booked), 2) if booked else None
        # (b) independent reconstruction from fill prices — must agree with (a)
        pnl_recon = (round(sum((f["price"] - broker_entry) * sign * f["qty"]
                               * POINT_VALUE for f in x_fills), 2)
                     if broker_entry is not None and x_fills else None)
        d_entry = (round(t["entry_price"] - broker_entry, 4)
                   if broker_entry is not None and t["entry_price"] is not None
                   else None)
        out.append({
            "trade_id": t["id"], "mode": t["mode"], "direction": t["direction"],
            "entry_order_id": e_oid, "exit_order_ids": sorted(x_oids),
            "books_entry": t["entry_price"], "broker_entry": broker_entry,
            "entry_delta": d_entry, "entry_qty": qty,
            "exit_fills": [{"order_id": f["order_id"], "price": f["price"],
                            "qty": f["qty"], "broker_pnl": f.get("broker_pnl"),
                            "ts": f["ts"].isoformat() if f["ts"] else None}
                           for f in x_fills],
            "books_pnl": t["pnl_usd"], "pnl_sierra_now": t["pnl_sierra"],
            "pnl_broker": pnl_broker, "pnl_reconstructed": pnl_recon,
            "recon_agrees": (pnl_broker is not None and pnl_recon is not None
                             and abs(pnl_broker - pnl_recon) < 0.01),
            "pnl_delta": (round(t["pnl_usd"] - pnl_broker, 2)
                          if pnl_broker is not None and t["pnl_usd"] is not None
                          else None),
        })
    return out


def write_pnl_sierra(dsn: str, rows: list[dict]) -> int:
    """Persist pnl_sierra ONLY where the two independent computations agree."""
    import psycopg2
    todo = [(r["pnl_broker"], r["trade_id"]) for r in rows
            if r["pnl_broker"] is not None and r["recon_agrees"]]
    if not todo:
        return 0
    with psycopg2.connect(dsn) as cn:
        with cn.cursor() as cur:
            cur.execute("SET lock_timeout = '3s'")
            cur.executemany(
                "UPDATE v9_trades SET pnl_sierra = %s "
                " WHERE id = %s AND pnl_sierra IS DISTINCT FROM %s",
                [(p, i, p) for p, i in todo])
            return cur.rowcount if cur.rowcount and cur.rowcount > 0 else len(todo)


# -------------------------------------------------------------------- main

def log_path(day: str, account: str) -> Path:
    if account.lower().startswith("sim"):
        return SIERRA_DIR / f"TradeActivityLog_{day}_UTC.{account}.simulated.data"
    return SIERRA_DIR / f"TradeActivityLog_{day}_UTC.{account}.data"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None,
                    help="trading day YYYY-MM-DD (default: today, UTC filename)")
    ap.add_argument("--account", default=LIVE_ACCOUNT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="persist pnl_sierra (NEVER pnl_usd). Backfilling past "
                         "days needs Michael's ruling — default is dry-run.")
    a = ap.parse_args(argv)
    day = a.date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    p = log_path(day, a.account)
    if not p.exists():
        print(f"NO ACTIVITY LOG: {p}", file=sys.stderr)
        return 2
    fills, pnls = parse_activity(p)
    attach_pnl(fills, pnls)
    trades = fetch_trades(DSN, day)
    rows = reconcile(trades, fills)
    broker_day = round(sum(x["amount"] for x in pnls), 2)

    if a.json:
        print(json.dumps({"date": day, "account": a.account,
                          "source": str(p), "fills": len(fills),
                          "closed_pnl_records": len(pnls),
                          "broker_day_total": broker_day,
                          "trades": rows}, indent=2, default=str))
        return 0

    print(f"# T-256 books vs broker — {day} acct {a.account}")
    print(f"# source: {p}")
    print(f"# {len(fills)} executions · {len(pnls)} Closed-Trade-P/L records "
          f"· broker day total {broker_day:+.2f}")
    print()
    hdr = (f'{"trade":>6} {"dir":<5} {"books_entry":>11} {"fill_entry":>11} '
           f'{"Δentry":>7} {"books_pnl":>10} {"broker_pnl":>10} '
           f'{"recon":>10} {"ok":>3} {"Δ$":>8}')
    print(hdr)
    print("-" * len(hdr))
    def n2(v, sign=True):
        if v is None:
            return "-"
        return ("%+.2f" if sign else "%.2f") % v

    tb = tk = 0.0
    for r in rows:
        print("%6s %-5s %11s %11s %7s %10s %10s %10s %3s %8s" % (
            r["trade_id"], (r["direction"] or "?"),
            n2(r["books_entry"], False), n2(r["broker_entry"], False),
            n2(r["entry_delta"]), n2(r["books_pnl"]), n2(r["pnl_broker"]),
            n2(r["pnl_reconstructed"]),
            "OK" if r["recon_agrees"] else "!!", n2(r["pnl_delta"])))
        if r["books_pnl"] is not None:
            tb += r["books_pnl"]
        if r["pnl_broker"] is not None:
            tk += r["pnl_broker"]
    print("-" * len(hdr))
    print(f'{"TOTAL":>6} {"":<5} {"":>11} {"":>11} {"":>7} '
          f'{tb:>+10.2f} {tk:>+10.2f} {"":>10} {"":>3} {tb - tk:>+8.2f}')
    print()
    # COVERAGE GUARD — a join that silently sees only part of the day is worse
    # than no join, because its per-trade deltas look authoritative. The sum of
    # the trades we mapped MUST equal the broker's day total; whatever is left
    # over is either an unmapped exit order-id (Cancel/Replace re-issues a new
    # id that never lands in `quality`) or somebody else trading the shared
    # account. Either way the per-trade numbers below are NOT closed until this
    # residual is zero.
    resid = round(broker_day - tk, 2)
    print(f"COVERAGE: mapped {tk:+.2f} of broker day {broker_day:+.2f} "
          f"→ residual {resid:+.2f} "
          + ("(complete — every dollar the broker moved is attributed)"
             if abs(resid) < 0.01 else
             "(INCOMPLETE — per-trade deltas above are indicative only)"))
    unmapped = [r["trade_id"] for r in rows if r["pnl_broker"] is None]
    if unmapped:
        print(f"          trades with no broker exit mapped: {unmapped}")
    print()
    bad = [r for r in rows if r["entry_delta"] not in (None, 0.0)]
    print(f"entry_price != fill price on {len(bad)}/{len(rows)} trades"
          + (f' → {[(r["trade_id"], r["entry_delta"]) for r in bad]}' if bad else ""))
    if a.write:
        n = write_pnl_sierra(DSN, rows)
        print(f"pnl_sierra written on {n} rows")
    else:
        todo = [(r["trade_id"], r["pnl_broker"]) for r in rows
                if r["pnl_broker"] is not None and r["recon_agrees"]
                and r["pnl_sierra_now"] != r["pnl_broker"]]
        print(f"DRY-RUN — would set pnl_sierra on {len(todo)} rows: {todo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
