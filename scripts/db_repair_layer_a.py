#!/usr/bin/env python3
"""Layer-A CVD repair — workorder docs/handoff/CC_WORKORDER_DB_REPAIR_2026-08-25.md.

Scope: the 9 Layer-A sessions whose bars are already byte-identical to SCID and
only CVD failed (D3a conflicts / D3b :59 stamps / D3c missing rows):
07-07 07-08 07-09 07-10 07-13 08-07 08-10 08-11 08-13.

Truth source: backend/v9/replay/scid_validator.py ONLY (the workorder forbids
rebuild_bar_truth.py). delta = ask_volume - bid_volume summed per 5-min bucket;
cumulative = running sum anchored at RTH open — exactly load_rth(), which is
also what live-good sessions (08-14..08-20) already match (cum_mm=0).

Plan per truth slot (78 per session):
  * rows mapping to the slot (exact grid ts, or :M4:59 + 1s == slot):
    keep lowest id, set (ts, delta, cumulative, direction) to truth,
    source_version='scid_repair' if anything changed; DELETE the rest.
  * no row -> INSERT bar_id='cvdfix_<date>_<ET HHMM>', source_version='scid_repair'.
  * rows outside the truth grid are LEFT untouched and reported (honest).

Schema step (workorder step 3): ADD COLUMN symbol DEFAULT 'MES',
source_version DEFAULT 'live'; tag table-wide exact-ts duplicate rows rank>1
as 'legacy_dup_<rn>' (value-neutral — D1-session CVD values untouched, they
wait for Michael's ruling); then UNIQUE (ts, symbol, source_version).

Default = dry-run (prints full plan, writes NOTHING).
--execute: SET LOCAL lock_timeout='3s', one transaction per session,
pg_isready + backend-health probe after each batch.
"""
import argparse
import datetime as dt
import subprocess
import sys
import time

sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/backend")

import psycopg2  # noqa: E402

from v9.replay.scid_validator import SCIDValidator  # noqa: E402

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo

DSN = "postgresql://localhost/mems26"
SCID = "~/SierraChart/Data/MESU26_FUT_CME.scid"
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
TABLE = "v9_bars_cumulative_delta"
LAYER_A = ["2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10",
           "2026-07-13", "2026-08-07", "2026-08-10", "2026-08-11",
           "2026-08-13"]
PG_BIN = "/Applications/Postgres.app/Contents/Versions/18/bin"


def direction(d):
    return "UP" if d > 0 else ("DOWN" if d < 0 else "FLAT")


def slot_of(ts_utc):
    """Map a row ts to its 5-min grid slot. Writer stamps :00 or :M4:59."""
    if ts_utc.second == 59 and ts_utc.microsecond == 0:
        ts_utc = ts_utc + dt.timedelta(seconds=1)
    if (ts_utc.second == 0 and ts_utc.microsecond == 0
            and ts_utc.minute % 5 == 0):
        return ts_utc
    return None


def plan_session(cur, val, date):
    truth = {
        b.ts: (float(b.delta), float(b.cumulative_delta))
        for b in val.load_rth(dt.date.fromisoformat(date))
    }
    cur.execute(
        "SELECT id, ts, delta, cumulative FROM %s WHERE "
        "(ts AT TIME ZONE 'America/New_York')::date = %%s ORDER BY id"
        % TABLE, (date,))
    rows = cur.fetchall()
    by_slot = {}
    odd = []
    for rid, ts, delta, cum in rows:
        ts_utc = ts.astimezone(UTC)
        s = slot_of(ts_utc)
        if s is None or s not in truth:
            odd.append((rid, ts_utc.isoformat()))
            continue
        by_slot.setdefault(s, []).append((rid, ts_utc, delta, cum))
    updates, deletes, inserts = [], [], []
    keep_ok = 0
    for s in sorted(truth):
        td, tc = truth[s]
        group = by_slot.get(s, [])
        if not group:
            inserts.append((s, td, tc))
            continue
        keep = group[0]                       # lowest id, deterministic
        deletes.extend(g[0] for g in group[1:])
        rid, ts_utc, delta, cum = keep
        same = (delta is not None and cum is not None
                and abs(float(delta) - td) <= 0.01
                and abs(float(cum) - tc) <= 0.01
                and ts_utc == s)
        if same:
            keep_ok += 1
        else:
            updates.append((rid, s, td, tc))
    return {"date": date, "db_rows": len(rows), "truth_slots": len(truth),
            "keep_ok": keep_ok, "updates": updates, "deletes": deletes,
            "inserts": inserts, "out_of_grid_left": odd}


def show_plan(p):
    print("%s  db_rows=%-4d truth=%d  keep_ok=%-3d update=%-3d delete=%-3d "
          "insert=%-3d out_of_grid_left=%d" % (
              p["date"], p["db_rows"], p["truth_slots"], p["keep_ok"],
              len(p["updates"]), len(p["deletes"]), len(p["inserts"]),
              len(p["out_of_grid_left"])))
    for tag, items, fmt in (
            ("UPDATE", p["updates"],
             lambda u: "id=%s ts->%s delta->%.1f cum->%.1f" % (
                 u[0], u[1].isoformat(), u[2], u[3])),
            ("DELETE", p["deletes"], lambda d: "id=%s" % d),
            ("INSERT", p["inserts"],
             lambda i: "%s delta=%.1f cum=%.1f" % (
                 i[0].isoformat(), i[1], i[2]))):
        for item in items[:3]:
            print("    %s %s" % (tag, fmt(item)))
        if len(items) > 3:
            print("    %s ... (%d total)" % (tag, len(items)))
    for rid, ts in p["out_of_grid_left"][:5]:
        print("    LEFT id=%s ts=%s (outside truth grid)" % (rid, ts))


def health_probe(label):
    ok1 = subprocess.run([PG_BIN + "/pg_isready", "-h", "localhost"],
                         capture_output=True, text=True)
    ok2 = subprocess.run(
        ["curl", "-s", "-m", "3", "-o", "/dev/null", "-w", "%{http_code}",
         "http://localhost:8000/api/v9/health"],
        capture_output=True, text=True)
    print("  [probe %s] pg_isready=%s backend=%s" % (
        label, ok1.stdout.strip(), ok2.stdout.strip()))
    return "accepting connections" in ok1.stdout and ok2.stdout.strip() == "200"


def exec_session(conn, p):
    t0 = time.time()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='3s'")
            if p["deletes"]:
                cur.execute("DELETE FROM %s WHERE id = ANY(%%s)" % TABLE,
                            (p["deletes"],))
            for rid, s, td, tc in p["updates"]:
                cur.execute(
                    "UPDATE %s SET ts=%%s, delta=%%s, cumulative=%%s, "
                    "direction=%%s, source_version='scid_repair' "
                    "WHERE id=%%s" % TABLE,
                    (s, td, tc, direction(td), rid))
            for s, td, tc in p["inserts"]:
                cur.execute(
                    "INSERT INTO %s (ts, bar_id, delta, cumulative, "
                    "direction, session, source_version) "
                    "VALUES (%%s,%%s,%%s,%%s,%%s,NULL,'scid_repair')" % TABLE,
                    (s, "cvdfix_%s_%s" % (
                        p["date"], s.astimezone(ET).strftime("%H%M")),
                     td, tc, direction(td)))
    return time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="perform writes (default: dry-run)")
    args = ap.parse_args()

    val = SCIDValidator(SCID)
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT count(*), max(ts) FROM " + TABLE)
    total_before, max_ts_before = cur.fetchone()
    print("table=%s rows_before=%s max_ts_before=%s" % (
        TABLE, total_before, max_ts_before))

    plans = []
    for date in LAYER_A:
        p = plan_session(cur, val, date)
        plans.append(p)
        show_plan(p)
    conn.rollback()   # planning reads only

    tu = sum(len(p["updates"]) for p in plans)
    td_ = sum(len(p["deletes"]) for p in plans)
    ti = sum(len(p["inserts"]) for p in plans)
    print("TOTAL updates=%d deletes=%d inserts=%d" % (tu, td_, ti))

    cur.execute("""
        SELECT count(*) FROM (
          SELECT ts FROM %s GROUP BY ts HAVING count(*) > 1) g""" % TABLE)
    dup_groups = cur.fetchone()[0]
    cur.execute("""
        SELECT coalesce(sum(c - 1), 0) FROM (
          SELECT count(*) c FROM %s GROUP BY ts HAVING count(*) > 1) g"""
                % TABLE)
    dup_extra_rows = cur.fetchone()[0]
    conn.rollback()
    print("table-wide exact-ts dup groups=%s extra_rows=%s "
          "(rank>1 -> 'legacy_dup_<rn>' tag before UNIQUE)" % (
              dup_groups, dup_extra_rows))

    if not args.execute:
        print("DRY-RUN ONLY — nothing written.")
        return

    print("== EXECUTE ==")
    if not health_probe("pre"):
        print("ABORT: pre-flight probe failed")
        sys.exit(2)

    with conn:
        with conn.cursor() as c:
            c.execute("SET LOCAL lock_timeout='3s'")
            c.execute("ALTER TABLE %s ADD COLUMN IF NOT EXISTS symbol "
                      "varchar NOT NULL DEFAULT 'MES'" % TABLE)
            c.execute("ALTER TABLE %s ADD COLUMN IF NOT EXISTS "
                      "source_version varchar NOT NULL DEFAULT 'live'"
                      % TABLE)
    print("DDL columns added (symbol/'MES', source_version/'live')")

    for p in plans:
        took = exec_session(conn, p)
        print("%s written in %.2fs (upd=%d del=%d ins=%d)" % (
            p["date"], took, len(p["updates"]), len(p["deletes"]),
            len(p["inserts"])))
        if not health_probe(p["date"]):
            print("ABORT after %s: probe failed" % p["date"])
            sys.exit(2)

    with conn:
        with conn.cursor() as c:
            c.execute("SET LOCAL lock_timeout='3s'")
            c.execute("""
                WITH d AS (
                  SELECT id, row_number() OVER (
                    PARTITION BY ts, symbol ORDER BY id) rn
                  FROM %s)
                UPDATE %s t SET source_version = 'legacy_dup_' || d.rn
                FROM d WHERE d.id = t.id AND d.rn > 1""" % (TABLE, TABLE))
            tagged = c.rowcount
    print("legacy dup rows tagged=%d" % tagged)

    with conn:
        with conn.cursor() as c:
            c.execute("SET LOCAL lock_timeout='3s'")
            c.execute("ALTER TABLE %s ADD CONSTRAINT "
                      "uq_v9_cvd_ts_symbol_source "
                      "UNIQUE (ts, symbol, source_version)" % TABLE)
    print("UNIQUE (ts, symbol, source_version) created")

    cur.execute("SELECT count(*), max(ts) FROM " + TABLE)
    total_after, max_ts_after = cur.fetchone()
    conn.rollback()
    print("rows_after=%s (delta=%+d) max_ts_after=%s (unchanged=%s)" % (
        total_after, total_after - total_before, max_ts_after,
        max_ts_after == max_ts_before))
    health_probe("post")


if __name__ == "__main__":
    main()
