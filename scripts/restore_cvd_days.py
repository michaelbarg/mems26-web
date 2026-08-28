#!/usr/bin/env python3
"""restore_cvd_days.py — rebuild the CVD rows that the bar_id-keyed writer ate.

Ruling f4bf481d (Michael, phone 2026-08-28, approving R0 / T-112): after the
writer root-fix (time-keyed upsert), restore 2026-08-14 + 2026-08-21 — both
lost ALL their v9_bars_cumulative_delta rows (89 each → 0, proven from the
pre-write pg_dump of 2026-08-27) to the chart-reload drag.

METHOD (engines reused, not rebuilt)
  * Tick source: ~/SierraChart/Data/MESU26_FUT_CME.scid (BidVolume/AskVolume
    per tick) — same source scripts/cvd_effort_result.py already validated.
  * Scid reader copied verbatim from scripts/entry_side_replay.py (class
    Scid) — copied, not imported, to avoid that module's heavier deps.
  * Grid: the live writer's own grid — 5-min slots 09:35→16:55 ET (89 slots,
    matches 08-20's 'live' rows; DB rows carry second-jitter like :39:59, so
    comparisons floor to the 5-min slot).
  * delta  = sum(AskVolume) − sum(BidVolume) per slot.
  * cumulative = Globex-session anchor: running sum from the PREVIOUS day's
    18:00 ET (session open) — matches the DLL's 24h-chart baseline (08-20
    live: cum[0]=4233 vs delta[0]=1324 ⇒ baseline is pre-RTH flow).

HONESTY (Rule 1): restored rows are written with
    source_version='scid_restore_0828'   (NEVER 'live')
so provenance is queryable forever. Rows are only written for (ts,'MES')
slots that have NO row in ANY source_version (no shadow-duplication).

VALIDATION (Rule 2, run first):
    python3 scripts/restore_cvd_days.py --validate 2026-08-20
rebuilds a healthy live day from ticks and prints per-bar delta/cum diffs
vs the DB 'live' rows. Restore only after this passes.

WRITE:
    python3 scripts/restore_cvd_days.py --restore 2026-08-14 --write
    (without --write: dry-run prints what would be inserted)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import struct
import sys

import psycopg2

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
SCID_PATH = os.path.expanduser("~/SierraChart/Data/MESU26_FUT_CME.scid")
ET = dt.timezone(dt.timedelta(hours=-4))          # EDT (whole live era)
SLOT0, SLOTN = dt.time(9, 35), dt.time(16, 55)    # live writer's grid
RESTORE_SV = "scid_restore_0828"


# ── Scid reader (copied from scripts/entry_side_replay.py, class Scid) ──
class Scid:
    HDR = 56
    EPOCH = dt.datetime(1899, 12, 30)

    def __init__(self, path):
        self.f = open(path, "rb")
        hdr = self.f.read(self.HDR)
        assert hdr[:4] == b"SCID", "not a .scid file"
        self.rec = struct.unpack("<I", hdr[8:12])[0]
        self.n = (os.path.getsize(path) - self.HDR) // self.rec

    def ts(self, i):
        self.f.seek(self.HDR + i * self.rec)
        return struct.unpack("<q", self.f.read(8))[0]

    def _us(self, t):
        return int((t - self.EPOCH).total_seconds() * 1_000_000)

    def find(self, t):
        lo, hi, tgt = 0, self.n, self._us(t)
        while lo < hi:
            m = (lo + hi) // 2
            if self.ts(m) < tgt:
                lo = m + 1
            else:
                hi = m
        return lo

    def bidask(self, t0_utc_naive, t1_utc_naive):
        """(sum_bid, sum_ask) over [t0, t1) — args are UTC-naive datetimes."""
        a, b = self.find(t0_utc_naive), self.find(t1_utc_naive)
        if b <= a:
            return 0.0, 0.0
        self.f.seek(self.HDR + a * self.rec)
        raw = self.f.read((b - a) * self.rec)
        sb = sa = 0.0
        for j in range(b - a):
            v = struct.unpack_from("<q4f4I", raw, j * self.rec)
            sb += v[7]
            sa += v[8]
        return sb, sa


def _slots(day: dt.date):
    """All 5-min ET slot-open datetimes 09:35..16:55 for the day (aware)."""
    t = dt.datetime.combine(day, SLOT0, tzinfo=ET)
    end = dt.datetime.combine(day, SLOTN, tzinfo=ET)
    out = []
    while t <= end:
        out.append(t)
        t += dt.timedelta(minutes=5)
    return out


def _utc_naive(t_aware):
    return t_aware.astimezone(dt.timezone.utc).replace(tzinfo=None)


def build_day(sc: Scid, day: dt.date):
    """[(slot_et_aware, delta, cumulative)] — cum anchored at prev-day 18:00 ET."""
    anchor = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(18, 0),
                                 tzinfo=ET)
    slots = _slots(day)
    # baseline: everything from Globex open to the first slot
    b, a = sc.bidask(_utc_naive(anchor), _utc_naive(slots[0]))
    cum = a - b
    rows = []
    for t in slots:
        b, a = sc.bidask(_utc_naive(t), _utc_naive(t + dt.timedelta(minutes=5)))
        d = a - b
        cum += d
        rows.append((t, int(round(d)), int(round(cum))))
    return rows


def validate(day_s: str):
    day = dt.date.fromisoformat(day_s)
    sc = Scid(SCID_PATH)
    print(f"[scid] {SCID_PATH} rec={sc.rec} ticks={sc.n:,}")
    rebuilt = build_day(sc, day)
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        "SELECT ts, delta, cumulative FROM v9_bars_cumulative_delta "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = %s "
        "AND source_version='live' ORDER BY ts", (day,))
    db = cur.fetchall()
    # Map DB ts to its 5-min slot by ROUNDING TO NEAREST boundary: the live
    # writer stamps some bars at open (:35:00) and some at next-open−1s
    # (:39:59 = the 16:40 bar) — verified on 08-20 where both stamps coexist
    # with different deltas. +30s then floor handles both.
    by_slot = {}
    for ts, d, c in db:
        et = ts.astimezone(ET) + dt.timedelta(seconds=30)
        slot = et.replace(minute=et.minute - et.minute % 5, second=0,
                          microsecond=0)
        by_slot[slot] = (float(d), float(c))
    n = hit = 0
    dd, dc = [], []
    for t, d, c in rebuilt:
        if t in by_slot:
            n += 1
            d0, c0 = by_slot[t]
            dd.append(abs(d - d0))
            dc.append(abs(c - c0))
            if abs(d - d0) <= max(2, 0.02 * max(1, abs(d0))):
                hit += 1
    dd.sort(); dc.sort()
    med = lambda xs: xs[len(xs) // 2] if xs else None
    print(f"[validate {day}] slots rebuilt={len(rebuilt)} db_live={len(db)} "
          f"matched={n}")
    print(f"  |Δdelta| median={med(dd)} p90={dd[int(len(dd)*0.9)] if dd else None} "
          f"max={dd[-1] if dd else None} · within-2%/2ct: {hit}/{n}")
    print(f"  |Δcum|   median={med(dc)} p90={dc[int(len(dc)*0.9)] if dc else None} "
          f"max={dc[-1] if dc else None}")
    worst = sorted(
        ((abs(d - by_slot[t][0]), t, d, by_slot[t][0])
         for t, d, c in rebuilt if t in by_slot), reverse=True)[:5]
    for w, t, d, d0 in worst:
        print(f"  worst delta: {t.strftime('%H:%M')} rebuilt={d} live={d0}")
    conn.close()


def restore(day_s: str, write: bool):
    day = dt.date.fromisoformat(day_s)
    sc = Scid(SCID_PATH)
    rebuilt = build_day(sc, day)
    nonzero = sum(1 for _, d, _ in rebuilt if d != 0)
    print(f"[restore {day}] rebuilt {len(rebuilt)} slots, nonzero-delta={nonzero}")
    if nonzero < 60:
        print("  ✗ ABORT: too few nonzero slots — SCID coverage suspect")
        sys.exit(2)
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    ins = skip = 0
    for t, d, c in rebuilt:
        cur.execute(
            "SELECT 1 FROM v9_bars_cumulative_delta WHERE ts=%s AND symbol='MES'",
            (t,))
        if cur.fetchone():
            skip += 1
            continue
        if write:
            cur.execute(
                "INSERT INTO v9_bars_cumulative_delta "
                "(ts, symbol, source_version, delta, cumulative, direction) "
                "VALUES (%s, 'MES', %s, %s, %s, %s) "
                "ON CONFLICT (ts, symbol, source_version) DO NOTHING",
                (t, RESTORE_SV, d, c,
                 "UP" if d > 0 else ("DOWN" if d < 0 else "FLAT")))
        ins += 1
    if write:
        conn.commit()
        print(f"  ✓ WROTE {ins} rows (source_version={RESTORE_SV}), "
              f"skipped-existing {skip}")
    else:
        print(f"  DRY-RUN: would write {ins}, skip-existing {skip} "
              f"(pass --write to apply)")
    print(f"  sample: {[(t.strftime('%H:%M'), d, c) for t, d, c in rebuilt[:3]]}"
          f" … {[(t.strftime('%H:%M'), d, c) for t, d, c in rebuilt[-2:]]}")
    conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--validate", metavar="DATE")
    p.add_argument("--restore", metavar="DATE")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    if args.validate:
        validate(args.validate)
    elif args.restore:
        restore(args.restore, args.write)
    else:
        p.print_help()
