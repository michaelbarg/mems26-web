#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live_pnl — the one number, and what it rests on.

Michael 08.09: "אני רוצה שנתקן את המנוע שעושה את הטעויות." The first thing to
fix is not the engine — it is that we could not say what the engine cost.

Before tonight, three different totals were all defensible: −$310 (broker rows
only), +$103.75 (books only), −$50.00 (whichever column happened to be
non-null). A 39-session audit ran on all three at once. You cannot manage what
you cannot measure, and you cannot measure with an OR in the SELECT.

**The rule this script enforces:** a live trade counts toward P&L only when the
BROKER priced it. `pnl_sierra` is written by `sierra_activity_join.py`, which
joins Sierra's own activity log on the InternalOrderID we persisted at submit —
never by price proximity (that was T-229's mistake). Everything else is
reported, loudly, as what it is:

  BROKER    pnl_sierra IS NOT NULL           → the number
  BOOKS     our own close path priced it     → shown, never summed into the number
  VOID      state=CANCELLED                  → an order that never happened, $0
  UNPRICED  closed with no price anywhere    → honest zero, Rule 1

`pnl_usd` never enters the headline. On the rows where the two disagree the
books are wrong more often than not: `phantom_reconcile` and `manual` closes
priced themselves, and together they carry most of the books-only profit.

    python3 scripts/live_pnl.py                  # all live sessions
    python3 scripts/live_pnl.py --since 2026-08-10
    python3 scripts/live_pnl.py --by-day
    python3 scripts/live_pnl.py --json
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# .env first — without it the reader falls back to SQLite and reports a
# confident zero (the trap logged as project_sot_health_sqlite_stale).
_env = ROOT / ".env"
if _env.exists():
    for _ln in open(_env, encoding="utf-8"):
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

from backend.v9.db.read import read_all  # noqa: E402

BUCKET_SQL = """
    CASE
      WHEN pnl_sierra IS NOT NULL              THEN 'BROKER'
      WHEN state = 'CANCELLED'                 THEN 'VOID'
      WHEN pnl_usd IS NOT NULL                 THEN 'BOOKS'
      ELSE 'UNPRICED'
    END
"""


def _rows(since, until):
    where = ["mode = 'live'"]
    params = {}
    if since:
        where.append("(entry_ts AT TIME ZONE 'Asia/Jerusalem')::date >= :a")
        params["a"] = since
    if until:
        where.append("(entry_ts AT TIME ZONE 'Asia/Jerusalem')::date <= :b")
        params["b"] = until
    return read_all(
        f"""SELECT {BUCKET_SQL} AS bucket,
                   COUNT(*) AS n,
                   COALESCE(SUM(pnl_sierra), 0) AS sierra,
                   COALESCE(SUM(pnl_usd), 0)    AS books
            FROM v9_trades WHERE {' AND '.join(where)}
            GROUP BY 1""", params)


def _by_day(since, until):
    where = ["mode = 'live'", "entry_ts IS NOT NULL"]
    params = {}
    if since:
        where.append("(entry_ts AT TIME ZONE 'Asia/Jerusalem')::date >= :a")
        params["a"] = since
    if until:
        where.append("(entry_ts AT TIME ZONE 'Asia/Jerusalem')::date <= :b")
        params["b"] = until
    return read_all(
        f"""SELECT (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date AS d,
                   COUNT(*) FILTER (WHERE pnl_sierra IS NOT NULL) AS bn,
                   COALESCE(SUM(pnl_sierra), 0) AS broker,
                   COUNT(*) FILTER (WHERE pnl_sierra IS NULL
                                      AND state <> 'CANCELLED') AS un,
                   COUNT(*) FILTER (WHERE state = 'CANCELLED') AS void
            FROM v9_trades WHERE {' AND '.join(where)}
            GROUP BY 1 ORDER BY 1""", params)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--by-day", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    buckets = {r["bucket"]: r for r in _rows(a.since, a.until)}
    g = lambda k, f: float(buckets.get(k, {}).get(f, 0) or 0)
    n = lambda k: int(buckets.get(k, {}).get("n", 0) or 0)

    headline = g("BROKER", "sierra")
    n_broker, n_books = n("BROKER"), n("BOOKS")
    n_void, n_unp = n("VOID"), n("UNPRICED")
    total = n_broker + n_books + n_void + n_unp
    traded = total - n_void
    cov = (n_broker / traded * 100.0) if traded else 0.0

    if a.json:
        print(json.dumps({
            "headline_broker_usd": headline, "n_broker": n_broker,
            "books_only_usd": g("BOOKS", "books"), "n_books_only": n_books,
            "n_void": n_void, "n_unpriced": n_unp,
            "n_total_rows": total, "n_traded": traded,
            "coverage_pct": round(cov, 1),
        }, indent=2))
        return

    print("═" * 66)
    print("  LIVE P&L — broker-priced rows only")
    print("═" * 66)
    print(f"  ►  {headline:+,.2f}   ({n_broker} trades the broker priced)")
    print()
    print(f"  books-only, NOT in the number : {g('BOOKS','books'):+,.2f}  ({n_books} rows)")
    print(f"  cancelled, never traded       :        —     ({n_void} rows)")
    print(f"  closed with no price anywhere :        —     ({n_unp} rows)")
    print(f"  coverage                      : {cov:.1f}% of {traded} traded rows")
    if cov < 100.0:
        print()
        print("  ⚠ every books-only row is a close our own code priced. Until it")
        print("    carries a broker fill it is not evidence. Run:")
        print("      python3 scripts/sierra_activity_join.py --date <d> --write")
    print("═" * 66)

    if a.by_day:
        print()
        print("  date        broker      n   unverified  void")
        print("  " + "-" * 50)
        for r in _by_day(a.since, a.until):
            print("  %s  %+9.2f  %3s   %5s      %s"
                  % (r["d"], float(r["broker"] or 0), r["bn"], r["un"], r["void"]))


if __name__ == "__main__":
    main()
