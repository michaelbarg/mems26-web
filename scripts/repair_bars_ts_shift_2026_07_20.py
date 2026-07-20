"""One-shot repair — 2026-07-20 morning bars written -1h into PG (Michael approved 22:44 IL).

Root (LIVE_CHANNEL 22:35): pre-restart backend wrote today's RTH bars 1h early;
the true first RTH hour (09:30-10:25 ET) was mislabeled pre-RTH and dropped by
the RTH gate. classify_replay's first-12-bars → wrong IB → false Neutral_Extreme.

Method (empirical, no TZ assumptions):
  Ground truth = Sierra export 5min.json. Its epoch E maps to the true instant
  E+5h (verified: last-bar epoch renders 17:25 IL while live_price shows the
  same close at 22:25 IL; OHLC cross-match confirms across the day).
  For every DB row of today, OHLC-match (unique matches only) to a Sierra bar
  → delta = stored_epoch − true_epoch. The post-restart tail defines the
  table's CORRECT storage convention D. Rows at D−3600 are the −1h victims →
  UPDATE ts += 1h. True RTH bars with no row at their D-slot → INSERT backfill
  (OHLCV only; study fields stay NULL — honest missing, Rule 1).
  Backup affected day-slice to *_bak_0720 before any write.

Usage:  python3 scripts/repair_bars_ts_shift_2026_07_20.py [--apply]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

EXPORT = Path.home() / "SierraChart_Data/v9_export/5min.json"
DB_URL = "postgresql://localhost/mems26"
IL = timezone(timedelta(hours=3))
SIERRA_TRUE_SHIFT = 5 * 3600          # file epoch + 5h = true instant (UTC epoch)
DAY = "2026-07-20"
APPLY = "--apply" in sys.argv


def il_str(ep: int) -> str:
    return datetime.fromtimestamp(ep, tz=IL).strftime("%H:%M")


def sierra_true_bars() -> dict:
    """true_utc_epoch -> bar dict, today (IL) only."""
    d = json.loads(EXPORT.read_text())
    out = {}
    for b in d["bars"]:
        ep = int(b["ts"]) + SIERRA_TRUE_SHIFT
        if datetime.fromtimestamp(ep, tz=IL).strftime("%Y-%m-%d") == DAY:
            out[ep] = b
    return out


def ohlc_key(o, h, l, c):
    return (round(float(o), 2), round(float(h), 2), round(float(l), 2), round(float(c), 2))


def main():
    sbars = sierra_true_bars()
    print(f"Sierra true bars {DAY}: {len(sbars)} ({il_str(min(sbars))}-{il_str(max(sbars))} IL)")
    # true RTH window = 09:30-16:00 ET = 16:30-23:00 IL
    rth_true = [ep for ep in sorted(sbars)
                if "16:30" <= il_str(ep) < "23:00"]
    print(f"  of which true-RTH: {len(rth_true)} ({il_str(rth_true[0])}-{il_str(rth_true[-1])} IL)")

    key2eps = {}
    for ep, b in sbars.items():
        key2eps.setdefault(ohlc_key(b["o"], b["h"], b["l"], b["c"]), []).append(ep)

    eng = create_engine(DB_URL)
    with eng.begin() as conn:
        for table in ("v9_bars_5min", "v9_bars_5min_woodies"):
            cols = [c[0] for c in conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
                {"t": table}).fetchall()]
            rows = conn.execute(text(
                f"SELECT ts, open, high, low, close FROM {table} "
                f"WHERE ts >= :d0 AND ts < :d1 ORDER BY ts"),
                {"d0": f"{DAY} 00:00:00+03", "d1": f"{DAY} 23:59:59+03"}).fetchall()

            db = []
            for r in rows:
                ts = r[0] if r[0].tzinfo else r[0].replace(tzinfo=timezone.utc)
                db.append((int(ts.timestamp()), r))
            db_epochs = {ep for ep, _ in db}

            deltas = []          # (db_epoch, delta)
            for ep, r in db:
                matches = key2eps.get(ohlc_key(r[1], r[2], r[3], r[4]), [])
                if len(matches) == 1:
                    deltas.append((ep, ep - matches[0]))
            hist = Counter(d for _, d in deltas)
            print(f"\n=== {table}: {len(rows)} rows today | uniquely matched {len(deltas)} ===")
            print("  delta histogram (stored − true, hours):",
                  {d / 3600: n for d, n in sorted(hist.items())})
            if not deltas:
                print("  no unique matches — skipping table")
                continue

            # correct convention D = delta of the newest matched rows (post-restart tail)
            tail = [d for _, d in sorted(deltas)[-8:]]
            D = Counter(tail).most_common(1)[0][0]
            victims = sorted(ep for ep, d in deltas if d == D - 3600)
            others = sorted((ep, d) for ep, d in deltas if d not in (D, D - 3600))
            print(f"  convention D = {D / 3600:+.1f}h | victims(-1h) = {len(victims)}"
                  + (f" ({il_str(victims[0])}-{il_str(victims[-1])} stored)" if victims else ""))
            if others:
                print(f"  other deltas (untouched): {[(il_str(e), d / 3600) for e, d in others][:6]}")
            collisions = [ep for ep in victims if ep + 3600 in db_epochs]
            if collisions:
                print(f"  !! collisions (will skip): {[il_str(e) for e in collisions]}")

            if not APPLY:
                continue

            bak = f"{table}_bak_0720"
            conn.execute(text(f"DROP TABLE IF EXISTS {bak}"))
            conn.execute(text(
                f"CREATE TABLE {bak} AS SELECT * FROM {table} WHERE ts >= :d0 AND ts < :d1"),
                {"d0": f"{DAY} 00:00:00+03", "d1": f"{DAY} 23:59:59+03"})
            print(f"  backup {bak}: "
                  f"{conn.execute(text(f'SELECT count(*) FROM {bak}')).scalar()} rows")

            if table == "v9_bars_5min":
                # 3 stored conventions today (-3h/-1h/0) with duplicated content.
                # Export carries every column this table needs (OHLCV+vp+cum_delta)
                # → delete ALL matched-wrong rows, re-insert canonical.
                wrong = sorted(ep for ep, d in deltas if d != 0)
                n_del = 0
                for ep in wrong:
                    n_del += conn.execute(text(
                        f"DELETE FROM {table} WHERE ts >= to_timestamp(:a) "
                        f"AND ts < to_timestamp(:b)"), {"a": ep, "b": ep + 1}).rowcount
                print(f"  DELETE wrong-ts rows: {n_del}")
                has_symbol = "symbol" in cols
                vp = [c for c in ("poc_vol", "vah", "val", "cumulative_delta") if c in cols]
                n_ins = 0
                for tep in rth_true:
                    b = sbars[tep]
                    fields = {"ts": datetime.fromtimestamp(tep, tz=timezone.utc),
                              "open": b["o"], "high": b["h"], "low": b["l"],
                              "close": b["c"], "volume": b.get("vol") or 0}
                    if has_symbol:
                        fields["symbol"] = "MES"
                    for c in vp:
                        if b.get(c) is not None:
                            fields[c] = b[c]
                    names = ", ".join(fields)
                    marks = ", ".join(f":{k}" for k in fields)
                    n_ins += conn.execute(text(
                        f"INSERT INTO {table} ({names}) VALUES ({marks}) "
                        f"ON CONFLICT DO NOTHING"), fields).rowcount
                print(f"  INSERT canonical from export: {n_ins} rows")
            else:
                # woodies: preserve study fields (CCI/LSMA/...) → shift victims
                # +1h DESC; if the target slot already holds the same true bar
                # (post-restart tail), the victim is a duplicate → DELETE.
                n_upd = n_del = 0
                for ep in sorted(victims, reverse=True):
                    tgt_exists = conn.execute(text(
                        f"SELECT 1 FROM {table} WHERE ts >= to_timestamp(:a) "
                        f"AND ts < to_timestamp(:b) LIMIT 1"),
                        {"a": ep + 3600, "b": ep + 3601}).scalar()
                    if tgt_exists:
                        n_del += conn.execute(text(
                            f"DELETE FROM {table} WHERE ts >= to_timestamp(:a) "
                            f"AND ts < to_timestamp(:b)"), {"a": ep, "b": ep + 1}).rowcount
                    else:
                        n_upd += conn.execute(text(
                            f"UPDATE {table} SET ts = ts + interval '1 hour' "
                            f"WHERE ts >= to_timestamp(:a) AND ts < to_timestamp(:b)"),
                            {"a": ep, "b": ep + 1}).rowcount
                print(f"  UPDATE +1h: {n_upd} | DELETE dup-content: {n_del}")

        print("\nAPPLIED (committed)." if APPLY else "\nDRY-RUN only. Re-run with --apply.")


if __name__ == "__main__":
    main()
