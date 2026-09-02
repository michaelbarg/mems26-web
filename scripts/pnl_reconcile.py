#!/usr/bin/env python3
"""T-10 / T-62 — books vs broker, per trade, from the Sierra fills journal.

    python3 scripts/pnl_reconcile.py                    # read-only report
    python3 scripts/pnl_reconcile.py --divergent-only
    python3 scripts/pnl_reconcile.py --write            # persist pnl_sierra
    python3 scripts/pnl_reconcile.py --json             # for the daily report

`pnl_usd` is our arithmetic; `pnl_sierra` is what the broker actually filled.
Until both sit on the row, a divergence like #749 (books -$51.25 vs fills
+$1.25) can only be found by reading a journal by hand.

Reads Postgres through psycopg2 directly — `backend.v9.db.read` can fall back to
a stale SQLite file and would answer from the wrong decade of data.

`--write` touches ONE column, `pnl_sierra`, and only where it is currently NULL
or different; `pnl_usd` is never modified, so this can never launder a bad book
into looking right. Reversible with:
    UPDATE v9_trades SET pnl_sierra = NULL WHERE id IN (...);
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.services.sierra_pnl_reconcile import (  # noqa: E402
    DEFAULT_JOURNAL, divergence_summary, load_journal, reconcile,
)

DSN = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")


def fetch_rows(dsn: str, mode: str = "", since: str = ""):
    import psycopg2
    import psycopg2.extras
    where, params = ["state = 'CLOSED'"], []
    if mode:
        where.append("mode = %s")
        params.append(mode)
    if since:
        where.append("COALESCE(exit_ts, updated_at) >= %s")
        params.append(since)
    sql = ("SELECT id, mode, direction, entry_price, exit_price, exit_reason, "
           "pnl_usd, pnl_sierra, quality, "
           "COALESCE(exit_ts, updated_at) AS ts "
           "FROM v9_trades WHERE " + " AND ".join(where) + " ORDER BY id")
    with psycopg2.connect(dsn) as cn:
        with cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def write_back(dsn: str, findings) -> int:
    import psycopg2
    todo = [(f["pnl_sierra"], f["trade_id"]) for f in findings
            if f["pnl_sierra"] is not None]
    if not todo:
        return 0
    with psycopg2.connect(dsn) as cn:
        with cn.cursor() as cur:
            # The backend holds a long-lived session on this table (there is
            # history of an idle-in-transaction lock wedging it, 2026-07-22).
            # Fail fast rather than block the trading process.
            cur.execute("SET lock_timeout = '3s'")
            cur.executemany(
                "UPDATE v9_trades SET pnl_sierra = %s WHERE id = %s "
                "AND state = 'CLOSED' AND (pnl_sierra IS DISTINCT FROM %s)",
                [(p, i, p) for p, i in todo])
            n = cur.rowcount
        cn.commit()
    return len(todo) if n < 0 else n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dsn", default=DSN)
    ap.add_argument("--journal", default=str(DEFAULT_JOURNAL))
    ap.add_argument("--mode", default="", help="live / demo / shadow")
    ap.add_argument("--since", default="", help="YYYY-MM-DD")
    ap.add_argument("--tol", type=float, default=0.01, help="dollars")
    ap.add_argument("--divergent-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="default: report only, touch nothing")
    ap.add_argument("--write", action="store_true",
                    help="persist pnl_sierra (pnl_usd is never touched) — "
                         "REQUIRES --i-have-michaels-ruling")
    ap.add_argument("--i-have-michaels-ruling", action="store_true",
                    help="Michael 2026-09-02: retroactive changes to recorded "
                         "P&L need his written ruling. Without this flag "
                         "--write refuses.")
    ap.add_argument("--sierra-day", default="",
                    help="YYYY-MM-DD — also print Sierra's own account total "
                         "for that day from TradeActivityLog")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    # T-227 guardrail (Michael 2026-09-02): a retroactive P&L rewrite is a
    # ruling, not a chore. The tool exists so the delta can be SEEN; applying
    # it is a separate, explicit act.
    if a.write and not a.i_have_michaels_ruling:
        print("REFUSED: --write rewrites recorded P&L history. Michael's "
              "written ruling is required (2026-09-02, same rule as T-211). "
              "Re-run with --i-have-michaels-ruling once you have it, or drop "
              "--write for the read-only report.", file=sys.stderr)
        return 2

    fills = load_journal(a.journal)
    rows = fetch_rows(a.dsn, a.mode, a.since)
    findings = reconcile(rows, fills=fills, tol=a.tol)
    summary = divergence_summary(rows, fills=fills, tol=a.tol)

    if a.json:
        print(json.dumps({"summary": summary, "findings": findings},
                         default=str, indent=2))
        return 0 if summary["ok"] else 1

    print(f"journal: {a.journal}  ({len(fills)} fill lines)")
    print(f"trades:  {len(rows)} CLOSED"
          + (f" mode={a.mode}" if a.mode else "")
          + (f" since={a.since}" if a.since else ""))
    print(f"correlated by Sierra order id: {summary['checked']}\n")
    print(f"{'trade':>6} {'mode':<7} {'books':>10} {'sierra':>10} "
          f"{'delta':>9}  {'cov':>5}  status")
    print("-" * 66)
    for f in findings:
        if a.divergent_only and f["status"] != "DIVERGENT":
            continue
        print(f"{f['trade_id']:>6} {str(f['mode'] or ''):<7} "
              f"{_m(f['pnl_books']):>10} {_m(f['pnl_sierra']):>10} "
              f"{_m(f['delta']):>9}  {f['covered']}/{f['contracts']:<3} "
              f"{f['status']}")
    print("-" * 66)
    print(f"matched {summary['matched']} · DIVERGENT {summary['divergent']} · "
          f"incomplete {summary['incomplete']}")
    print(f"books total {_m(summary['books_total'])} vs "
          f"sierra total {_m(summary['sierra_total'])}  "
          f"→ net book error {_m(summary['net_error'])}")
    if summary["worst"]:
        w = summary["worst"]
        print(f"worst single trade: #{w['trade_id']} books {_m(w['books'])} "
              f"vs sierra {_m(w['sierra'])} (delta {_m(w['delta'])})")

    if a.sierra_day:
        _print_sierra_day(a.sierra_day, summary)

    if a.write:
        n = write_back(a.dsn, findings)
        print(f"\nwrote pnl_sierra on {n} row(s) — pnl_usd untouched")
    else:
        print("\n(dry-run: nothing was written — pnl_sierra untouched)")

    return 0 if summary["ok"] else 1


def _print_sierra_day(day: str, summary: dict) -> None:
    """Account-level truth for one day, straight out of Sierra's own log.

    NOT a per-trade attribution and must never be used as one: Sierra's binary
    TradeActivityLog carries no recoverable per-line timestamp (see
    backend/v9/services/daily_pnl.py), and account 37138283 is SHARED with Eti
    (Michael 2026-08-30), so an account total mixes her trades with the
    system's. This prints the one number that IS provable — the day's account
    total — and says out loud what it does not prove.
    """
    from pathlib import Path
    from backend.v9.services.daily_pnl import (
        LIVE_ACCOUNT, LOG_DIR, _strings, parse_day_log,
    )
    p = Path(LOG_DIR) / f"TradeActivityLog_{day}_UTC.{LIVE_ACCOUNT}.data"
    if not p.exists():
        print(f"\nSierra day log not found: {p}")
        return
    text = _strings(p)
    if text is None:
        print(f"\nSierra day log unreadable (strings failed): {p.name}")
        return
    d = parse_day_log(text)
    print(f"\nSierra account truth for {day} ({p.name}):")
    print(f"  closed-trade records : {d['closes']}")
    print(f"  account total        : {d['pnl']:+.2f}   "
          f"(= sierra_state.acct_daily_pl)")
    print(f"  books (this report)  : {summary.get('books_total'):+.2f} "
          f"over {summary.get('rows_read', '?')} CLOSED row(s)")
    print("  CAVEAT: shared account (Eti trades on it too) and the log has no "
          "per-line timestamps —\n          the account total is NOT a "
          "per-trade attribution and must not be used as one.")


def _m(v):
    return "—" if v is None else f"{v:+.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
