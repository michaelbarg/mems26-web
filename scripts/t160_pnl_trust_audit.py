#!/usr/bin/env python3
"""T-160: P&L trust audit — marks trades without exit_price as untrusted.

Adds pnl_trusted=false to quality JSON for trades closed without exit_price.
Does NOT change pnl_usd (the work order forbids it).

Usage:
  python3 scripts/t160_pnl_trust_audit.py              # dry-run (report only)
  python3 scripts/t160_pnl_trust_audit.py --apply       # mark untrusted
  python3 scripts/t160_pnl_trust_audit.py --report      # truth report only
"""
import json
import os
import sys

# Bootstrap: ensure the project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# T-161 (2026-08-30): בלי טעינת .env אין DATABASE_URL, ו-backend/v9/db/read.py
# נופל ל-SQLite (data/mems26_local.db — מראה בת-28.08) ⇒ הדוח הראה
# **0 עסקאות / phantom $0.00** במקום 46 / +$855. מסוכן כפליים: ‏--apply על
# המסלול השבור מסמן **כלום** ונראה "נקי". קונבנציה כמו scripts/fire_drill.py;
# ממוגן כך שייבוא המודול לא ירעיל את סביבת-התהליך.
if __name__ == "__main__" or os.getenv("T160_AUDIT_LOAD_ENV", "0") == "1":
    from scripts.flag_guard import parse_env  # noqa: E402
    for _k, _v in parse_env(os.path.join(ROOT, ".env")).items():
        os.environ.setdefault(_k, _v)


def _connect():
    from backend.v9.db.read import read_all
    return read_all


def report():
    """Print net P&L with and without untrusted rows."""
    read_all = _connect()
    rows = read_all(
        "SELECT id, mode, exit_price, exit_reason, pnl_usd, quality "
        "FROM v9_trades WHERE mode IN ('live', 'demo') "
        "AND (entry_ts AT TIME ZONE 'America/New_York')::date >= "
        "(now() AT TIME ZONE 'America/New_York')::date - 20 "
        "ORDER BY id", {})

    total_n = len(rows)
    total_pnl = sum(float(r["pnl_usd"] or 0) for r in rows)
    untrusted = [r for r in rows if r["exit_price"] is None]
    untrusted_pnl = sum(float(r["pnl_usd"] or 0) for r in untrusted)
    trusted = [r for r in rows if r["exit_price"] is not None]
    trusted_pnl = sum(float(r["pnl_usd"] or 0) for r in trusted)

    print(f"=== T-160 P&L TRUTH REPORT (last 20 days, live+demo) ===")
    print(f"Total trades:    {total_n:>4}   net: ${total_pnl:>+10.2f}")
    print(f"Trusted:         {len(trusted):>4}   net: ${trusted_pnl:>+10.2f}")
    print(f"Untrusted:       {len(untrusted):>4}   net: ${untrusted_pnl:>+10.2f}")
    print(f"Delta (phantom): ${total_pnl - trusted_pnl:>+10.2f}")
    print()
    if untrusted:
        print("Untrusted trades (no exit_price):")
        for r in untrusted:
            q = r["quality"] if isinstance(r["quality"], dict) else {}
            print(f"  #{r['id']:>4} {r['exit_reason'] or '?':20s} "
                  f"pnl=${float(r['pnl_usd'] or 0):>+8.2f} "
                  f"trusted={q.get('pnl_trusted', 'unmarked')}")


def mark_untrusted(dry_run=True):
    """Add pnl_trusted=false to quality for trades without exit_price."""
    read_all = _connect()
    rows = read_all(
        "SELECT id, quality FROM v9_trades "
        "WHERE mode IN ('live', 'demo') AND exit_price IS NULL "
        "AND state = 'CLOSED'", {})

    to_mark = []
    for r in rows:
        q = r["quality"] if isinstance(r["quality"], dict) else {}
        if q.get("pnl_trusted") is not False:
            to_mark.append(r)

    print(f"Trades to mark untrusted: {len(to_mark)}")
    for r in to_mark:
        print(f"  #{r['id']}")

    if dry_run:
        print("DRY-RUN: no changes made. Use --apply to mark.")
        return

    from backend.v9.db.safe_writer import safe_execute
    for r in to_mark:
        q = r["quality"] if isinstance(r["quality"], dict) else {}
        q["pnl_trusted"] = False
        safe_execute(
            "UPDATE v9_trades SET quality = :q WHERE id = :id",
            {"q": json.dumps(q), "id": r["id"]})
    print(f"Marked {len(to_mark)} trades as pnl_trusted=false")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    elif "--apply" in sys.argv:
        mark_untrusted(dry_run=False)
    else:
        report()
        print()
        mark_untrusted(dry_run=True)
