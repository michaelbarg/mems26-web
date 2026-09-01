#!/usr/bin/env python3
"""T-153: Shadow promotion board — reads the unified ledger and reports.

Usage:
  python3 scripts/shadow_promotion_board.py              # print report
  python3 scripts/shadow_promotion_board.py --write      # write docs/reports/SHADOW_BOARD.md
  python3 scripts/shadow_promotion_board.py --alert      # alert if zero events today

T-152: unique event counting — counts per (pattern, direction, 30min window),
not raw rows, because shadow has no slot limit and inflates everything.
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# T-161 (2026-08-30): הלוח קורא מה-DB, אבל לא טען את .env — ובלי DATABASE_URL
# ‏backend/v9/db/read.py נופל ל-SQLite, שלא יודע לפרסר את ה-SQL של Postgres שכאן
# (‏"near '7 days': syntax error") ⇒ read_all מחזיר [] בשקט והלוח מדווח
# **אפס-כוזב** (0 במקום 146). חמור יותר: ‏--alert על המסלול השבור יורה
# התרעת-טלפון שקרית "צל ריק" בכל לילה. זו מחלקת-הכשל של sot_health (SQLite-stale
# ⇒ 🔴 כוזב) שמתועדת ב-CLAUDE.md.
# הקונבנציה זהה ל-scripts/fire_drill.py; ממוגן כך שייבוא המודול (טסטים/כלים)
# לעולם לא ירעיל את סביבת-התהליך.
if __name__ == "__main__" or os.getenv("SHADOW_BOARD_LOAD_ENV", "0") == "1":
    from scripts.flag_guard import parse_env  # noqa: E402
    for _k, _v in parse_env(os.path.join(ROOT, ".env")).items():
        os.environ.setdefault(_k, _v)


def _read():
    from backend.v9.db.read import read_all
    return read_all


def generate_report():
    read_all = _read()

    # ── silent-zero probe (2026-09-01) ─────────────────────────────────────
    # `read_all` returns [] on ANY exception, warning-log only
    # (backend/v9/db/read.py:36-37). So a DROPPED VIEW, a renamed column or a
    # dead connection is indistinguishable from a genuinely quiet shadow day —
    # and `--alert` would then push "צל ריק" for both. That is the exact
    # failure class of T-161 (three scripts read SQLite and reported a
    # confident zero) and of sot_health before it.
    #
    # One cheap probe closes it: a query that MUST return a row if the view is
    # reachable. If it comes back empty, the board refuses to report rather
    # than reporting nothing as if it were something.
    _probe = read_all("SELECT 1 AS ok FROM v9_shadow_ledger LIMIT 1", {})
    if _probe is None or (isinstance(_probe, list) and len(_probe) == 0):
        _probe2 = read_all("SELECT 1 AS ok", {})
        if _probe2:
            raise SystemExit(
                "v9_shadow_ledger is unreachable or empty at the source — the "
                "DB answers but the view does not. Refusing to report an empty "
                "board as if it were a quiet day. Check:  \\dv v9_shadow_ledger")
        raise SystemExit(
            "the database itself did not answer — refusing to report zero. "
            "This is not an empty shadow day.")

    # All shadow events from the unified view
    rows = read_all(
        "SELECT ts, source, flag, trade_id, pattern, direction, price, "
        "decision, pnl_sim, unit, outcome FROM v9_shadow_ledger "
        "WHERE ts >= now() - interval '7 days' ORDER BY ts DESC", {})

    # Today's events
    today = read_all(
        "SELECT ts, source, flag, trade_id, pattern, direction, decision, pnl_sim, unit "
        "FROM v9_shadow_ledger "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
        "(now() AT TIME ZONE 'America/New_York')::date "
        "ORDER BY ts DESC", {})

    # ── T-152 (2026-09-01): the 30-min bucket is REPLACED by a real slot scan ──
    # The old `_unique_count` bucketed (pattern, direction) into 30-minute
    # windows. That is a wrong correction wearing the shape of a right one: it
    # under-corrects whenever a trade is held longer than 30 min, over-corrects
    # when two genuinely independent signals land in one bucket, and lets two
    # signals 2 minutes apart both count across a bucket boundary.
    #
    # The real constraint is the accepted trade's ACTUAL holding period, so the
    # scan walks the stream in time order and lets each accepted trade hold the
    # slot until its recorded exit_ts. Measured 01.09: shadow inflation 2.42x
    # (N=412, K=170) against 1.16x on live, where the slot is already enforced.
    # That is the sanity check — a tool that reports ~1.0 on live is measuring
    # the slot and not something else.
    #
    # Rule 1: a row we cannot bound (no trade_id, or no exit_ts) is reported as
    # UNBOUNDED and excluded. It is never bucketed, never imputed.
    _bounds = {}
    for _r in (read_all(
            "SELECT id, entry_ts, exit_ts FROM v9_trades "
            "WHERE mode = 'shadow' AND exit_ts IS NOT NULL "
            "AND entry_ts >= now() - interval '8 days'", {}) or []):
        _bounds[str(_r["id"])] = (_r["entry_ts"], _r["exit_ts"])

    def _slot_accept(events):
        """Return (accepted, unbounded). `events` need not be sorted."""
        pairs, unbounded = [], []
        for e in events:
            b = _bounds.get(str(e.get("trade_id")))
            if b is None or b[0] is None:
                unbounded.append(e)
                continue
            pairs.append((b[0], b[1], e))
        pairs.sort(key=lambda x: x[0])
        accepted, free_at = [], None
        for ent, ext, e in pairs:
            if free_at is not None and ent < free_at:
                continue
            accepted.append(e)
            free_at = ext
        return accepted, unbounded

    lines = []
    lines.append("# Shadow Promotion Board")
    lines.append(f"\nGenerated: {datetime.now(timezone.utc).isoformat()}")
    _acc7, _unb7 = _slot_accept(rows)
    _accT, _unbT = _slot_accept(today)
    _infl = f"{len(rows)/len(_acc7):.2f}x" if _acc7 else "NOT_JUDGEABLE"
    lines.append(f"\n## Last 7 days: {len(rows)} raw (N), "
                 f"**{len(_acc7)} slot-accepted (K)**, inflation {_infl}")
    lines.append(f"## Today: {len(today)} raw (N), "
                 f"**{len(_accT)} slot-accepted (K)**")
    if _unb7:
        lines.append(f"\n> UNBOUNDED: {len(_unb7)} of {len(rows)} rows carry no "
                     f"resolvable trade_id/exit_ts and are excluded from K, not "
                     f"imputed (Rule 1).")
    _r20 = f"~{20/(len(rows)/len(_acc7)):.0f}" if _acc7 else "an unknown number of"
    lines.append(f"\n> **The promotion gate (20 entry / 15 exit / 10 blocking) "
                 f"reads K, never N.** At the inflation measured above, a "
                 f"mechanism \"reaching 20\" has had {_r20} real opportunities.")

    # Per-flag summary
    lines.append("\n## Per-flag summary (last 7 days)")
    lines.append("| Flag | N (raw) | K (slot) | N/K | Avg pnl_sim (on K) | unit |")
    lines.append("|---|---|---|---|---|---|")
    _acc_ids = {id(e) for e in _acc7}
    flags = {}
    for r in rows:
        f = r.get("flag") or "?"
        if f not in flags:
            flags[f] = {"n": 0, "k": 0, "pnl": [], "units": set()}
        flags[f]["n"] += 1
        if r.get("unit"):
            flags[f]["units"].add(r["unit"])
        # the average is taken over ACCEPTED rows only — averaging the raw set
        # re-introduces exactly the selection bias the scan exists to remove
        # (measured 01.09: +$19.01/trade, and the SIGN was not knowable from
        # the code — accepted trades turned out BETTER than the raw mean).
        if id(r) in _acc_ids:
            flags[f]["k"] += 1
            p = r.get("pnl_sim")
            if p is not None:
                try:
                    flags[f]["pnl"].append(float(p))
                except (TypeError, ValueError):
                    pass
    for f, data in sorted(flags.items()):
        # pnl_sim carried three different units before `unit` existed (S7 =
        # factor score, TSF = points of stop widening, DAYTYPE = NULL). Refuse
        # to average across units rather than print a meaningless number.
        if len(data["units"]) > 1:
            avg_s, unit_s = "MIXED_UNITS", "/".join(sorted(data["units"]))
        elif data["pnl"]:
            avg_s = f"{sum(data['pnl'])/len(data['pnl']):+.2f}"
            unit_s = (list(data["units"]) or ["?"])[0]
        else:
            avg_s, unit_s = "—", (list(data["units"]) or ["?"])[0]
        infl = f"{data['n']/data['k']:.2f}x" if data["k"] else "n/a"
        lines.append(f"| {f} | {data['n']} | **{data['k']}** | {infl} | "
                     f"{avg_s} | {unit_s} |")

    report = "\n".join(lines)
    return report, len(today)


def main():
    report, today_count = generate_report()
    print(report)

    if "--write" in sys.argv:
        out = "docs/reports/SHADOW_BOARD.md"
        with open(out, "w") as f:
            f.write(report)
        print(f"\nWritten to {out}")

    if "--alert" in sys.argv and today_count == 0:
        try:
            from backend.v9.services.phone_alert import push
            push("shadow_empty",
                 "\u26a0\ufe0f MEMS26: צל ריק",
                 "אפס אירועי-צל היום — תקלת-גלאי או דגלים כבויים",
                 priority=0)
            print("Alert sent: zero shadow events today")
        except Exception as e:
            print(f"Alert failed: {e}")


if __name__ == "__main__":
    main()
