#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Opening type v2 — read the last N RTH sessions myself: bars, what the system said, what v2 says, what happened.

READ-ONLY (SELECT on v9_bars_5min_woodies, v9_day_type_history). Prints a Markdown table + the first 8 bars per day.

  python3 scripts/opening_v2_study.py --since 2026-09-08 [--until 2026-10-22] [--bars] [--md docs/reports/X.md]
"""
import os, sys, csv, argparse, collections, datetime as dt, statistics
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.systems.opening_classifier_v2 import classify_opening_v2, describe, TYPES, OpeningLock

TICK = 0.25

# my own reading of the first 8 bars of every day (cowork-iMac, 23.10 10:xx — Dalton pp.63-74), the yardstick for v2
MANUAL = {
    "2026-09-08": "TEST_DRIVE↓", "2026-09-09": "AUCT_OUT", "2026-09-10": "ORR↓", "2026-09-11": "AUCT_OUT", "2026-09-14": "TEST_DRIVE↑",
    "2026-09-15": "DRIVE↓", "2026-09-16": "ORR↑", "2026-09-17": "DRIVE↓", "2026-09-18": "DRIVE↓", "2026-09-21": "DRIVE↑",
    "2026-09-22": "AUCT_IN", "2026-09-23": "DRIVE↓", "2026-09-24": "DRIVE↑", "2026-09-25": "TEST_DRIVE↓", "2026-09-28": "AUCT_IN",
    "2026-09-29": "DRIVE↓", "2026-09-30": "AUCT_IN", "2026-10-01": "ORR↓", "2026-10-02": "AUCT_OUT", "2026-10-05": "DRIVE↑",
    "2026-10-06": "DRIVE↑", "2026-10-07": "DRIVE↓", "2026-10-08": "AUCT_IN", "2026-10-09": "AUCT_IN", "2026-10-12": "TEST_DRIVE↓",
    "2026-10-13": "DRIVE↑→AUCT_IN", "2026-10-14": "TEST_DRIVE↓", "2026-10-15": "TEST_DRIVE↑", "2026-10-16": "DRIVE↓", "2026-10-19": "AUCT_IN",
    "2026-10-20": "ORR↑", "2026-10-21": "AUCT_IN", "2026-10-22": "AUCT_OUT",
}


def q(sql, params=None):
    return read_all(sql, params or {}) or []


def rth_dates(since, until):
    rows = q("select distinct (ts at time zone 'America/New_York')::date as d from v9_bars_5min_woodies "
             "where symbol='MES' and (ts at time zone 'America/New_York')::time >= '09:30' and (ts at time zone 'America/New_York')::time < '16:00' "
             "and (ts at time zone 'America/New_York')::date between :a and :b order by d", {"a": since, "b": until})
    return [r["d"] for r in rows]


def rth_bars(d):
    rows = q("select ts, open, high, low, close, volume from v9_bars_5min_woodies where symbol='MES' "
             "and (ts at time zone 'America/New_York')::date = :d and (ts at time zone 'America/New_York')::time >= '09:30' "
             "and (ts at time zone 'America/New_York')::time < '16:00' order by ts", {"d": d})
    out, seen = [], set()
    for r in rows:                       # de-dup the DST-shift duplicates seen on 25.09
        k = r["ts"]
        if k in seen:
            continue
        seen.add(k)
        out.append({"ts": r["ts"], "o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"]), "v": float(r["volume"] or 0)})
    return out


def overnight(d, prev_d):
    rows = q("select max(high) as h, min(low) as l from v9_bars_5min_woodies where symbol='MES' and ts > "
             "((CAST(:p AS date) + time '16:00') at time zone 'America/New_York') and ts < ((CAST(:d AS date) + time '09:30') at time zone 'America/New_York')",
             {"p": prev_d, "d": d})
    if rows and rows[0]["h"] is not None:
        return float(rows[0]["h"]), float(rows[0]["l"])
    return None, None


def profile(bars):
    """TPO value area of a session from its 5-min bars (30-min letters, 70% around the POC) — same method as the 30D study."""
    if len(bars) < 30:
        return None
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6; p = b["l"]
        while p <= b["h"] + 1e-9:
            prof[round(p / TICK) * TICK].add(letter); p += TICK
    counts = {p: len(v) for p, v in prof.items()}; total = sum(counts.values())
    mid = (max(counts) + min(counts)) / 2
    poc = max(counts, key=lambda p: (counts[p], -abs(p - mid)))
    lo = hi = poc; acc = counts[poc]
    while acc < 0.7 * total:
        upn, dnn = counts.get(round((hi + TICK) / TICK) * TICK, 0), counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if upn >= dnn and upn > 0: hi = round((hi + TICK) / TICK) * TICK; acc += upn
        elif dnn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dnn
        else: break
    return {"poc": poc, "vah": hi, "val": lo, "high": max(b["h"] for b in bars), "low": min(b["l"] for b in bars),
            "close": bars[-1]["c"], "atr": statistics.mean(b["h"] - b["l"] for b in bars)}


def unit_atr(full_sessions):
    """the ATR unit = mean 5-min range over the last 3 FULL RTH sessions (holiday half-days excluded)."""
    return statistics.mean(full_sessions) if full_sessions else None


def system_label(d):
    rows = q("select opening_type, day_type from v9_day_type_history where date = :d order by created_at desc limit 1", {"d": d})
    return (rows[0]["opening_type"], rows[0]["day_type"]) if rows else (None, None)


def ref_labels():
    p = os.path.join(ROOT, "docs", "reports", "opening_type_30d_2026-10-19.csv")
    out = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                k = r.get("date") or r.get("day") or ""
                out[k] = r
    return out


def short(t):
    return {"OPEN_DRIVE": "DRIVE", "OPEN_TEST_DRIVE": "TEST_DRIVE", "OPEN_REJECTION_REVERSE": "ORR", "OPEN_AUCTION_IN": "AUCT_IN",
            "OPEN_AUCTION_OUT": "AUCT_OUT", "OPEN_AUCTION": "AUCT", None: "—", "": "—"}.get(t, str(t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-09-08"); ap.add_argument("--until", default=str(dt.date.today() - dt.timedelta(days=1)))
    ap.add_argument("--bars", action="store_true", help="print the first 8 bars of every day"); ap.add_argument("--md", default="")
    a = ap.parse_args()
    dates = rth_dates(a.since, a.until)
    refs = ref_labels()
    lines = []
    P = lines.append
    P("# סוג-הפתיחה v2 — קריאה של %d סשנים (%s → %s)" % (len(dates), a.since, a.until))
    P("")
    P("| תאריך | מערכת (S1) | ייחוס 19.10 | **הקריאה שלי** | **v2 נעול (בר)** | v2 @6 | v2 @12 | ביטולים | ATR | 30 דק׳: ↑ / ↓ (ATR) · רה-טרייד | 60 דק׳ סגירה−פתיחה | EOD סגירה−פתיחה | טווח-היום מול הפתיחה | סוג-יום (מערכת) |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    stats = collections.Counter(); agree = collections.Counter(); fore = collections.defaultdict(list); manual_agree = collections.Counter()
    per_day_bars = []
    prev_bars = None; prev_d = None; full_sessions = []
    for d in dates:
        bars = rth_bars(d)
        if len(bars) < 12:
            prev_bars, prev_d = (bars if len(bars) >= 30 else prev_bars), d
            if len(bars) >= 60:
                full_sessions.append(statistics.mean(b["h"] - b["l"] for b in bars)); full_sessions = full_sessions[-3:]
            continue
        prev = profile(prev_bars) if prev_bars else None
        if prev and prev_d:
            oh, ol = overnight(d, prev_d)
            prev["on_high"], prev["on_low"] = oh, ol
        atr = unit_atr(full_sessions)
        L = OpeningLock(); seq = []
        for k in range(1, 13):
            seq.append(L.update(bars[:k], prev, atr))
        r6 = seq[5]; r12 = seq[11]
        lock_bar = L.locked_bar; lock_type = (L.locked or {}).get("type")
        revoked = ", ".join("%s@%d" % (short(t), b) for b, t in L.revoked) or "—"
        used = L.locked or r12   # the reading the day ends with
        sys_ot, sys_dt = system_label(d)
        ref = (refs.get(str(d)) or {}).get("ref_opening_type") or ""
        o = bars[0]["o"]; m = r6["metrics"]
        c60 = bars[11]["c"] - o; eod = bars[-1]["c"] - o
        dh = max(b["h"] for b in bars) - o; dl = o - min(b["l"] for b in bars)
        stats[used["type"]] += 1
        if sys_ot: agree[(sys_ot == used["type"])] += 1
        fore[used["type"]].append((used["direction"], eod, dh, dl))
        man = MANUAL.get(str(d), "?")
        v2s = short(used["type"]) + ("↑" if used["direction"] == "up" else "↓" if used["direction"] == "down" else "")
        if man != "?": manual_agree[(man.split("→")[-1] == v2s) or (man.split("→")[0] == v2s)] += 1
        P("| %s | %s | %s | **%s** | **%s (%s)** | %s | %s | %s | %.1f | +%.2f / −%.2f (%.1f/%.1f) · %d | %+.2f | %+.2f | +%.2f / −%.2f | %s |" % (
            d, short(sys_ot), short(ref) if ref else "—", man, v2s, lock_bar if lock_bar else "—",
            short(r6["type"]) + ("↑" if r6["direction"] == "up" else "↓" if r6["direction"] == "down" else ""),
            short(r12["type"]) + ("↑" if r12["direction"] == "up" else "↓" if r12["direction"] == "down" else ""),
            revoked, atr or 0, m["max_up"], m["max_dn"], m["max_up_u"], m["max_dn_u"], m["retrades_of_open"],
            c60, eod, dh, dl, sys_dt or "—"))
        if a.bars:
            row = ["  %s  O=%.2f  unit=%.2f  prev H/L %s/%s VA %s/%s ON %s/%s" % (
                d, o, r12["unit"], prev and "%.2f" % prev["high"], prev and "%.2f" % prev["low"], prev and "%.2f" % prev["vah"], prev and "%.2f" % prev["val"],
                prev and prev.get("on_high") and "%.2f" % prev["on_high"], prev and prev.get("on_low") and "%.2f" % prev["on_low"])]
            for i, b in enumerate(bars[:8]):
                row.append("    b%-2d %s  h%+6.2f l%+6.2f c%+6.2f  v%6.0f" % (i + 1, b["ts"].astimezone(dt.timezone(dt.timedelta(hours=3))).strftime("%H:%M"), b["h"] - o, b["l"] - o, b["c"] - o, b["v"]))
            row.append("    v2@6: " + describe(r6)); row.append("    v2 used: " + describe(used) + ("  [revoked: %s]" % revoked if revoked != "—" else ""))
            per_day_bars.append("\n".join(row))
        prev_bars, prev_d = bars, d
        if len(bars) >= 60:
            full_sessions.append(statistics.mean(b["h"] - b["l"] for b in bars)); full_sessions = full_sessions[-3:]
    P("")
    P("## סיכום")
    P("- התפלגות v2 @12: " + " · ".join("%s %d" % (short(k), v) for k, v in sorted(stats.items(), key=lambda kv: -kv[1])))
    tot = sum(agree.values())
    if tot:
        P("- הסכמה עם תווית-המערכת (S1 סוף-יום): %d/%d" % (agree[True], tot))
    mt = sum(manual_agree.values())
    if mt:
        P("- **הסכמה עם הקריאה שלי (ידנית, מהברים): %d/%d**" % (manual_agree[True], mt))
    for t, rows in fore.items():
        if t.startswith("OPEN_DRIVE") or t == "OPEN_TEST_DRIVE":
            ok = sum(1 for d_, e, _, _ in rows if (e > 0) == (d_ == "up"))
            P("- %s: %d ימים · סגירת-היום בכיוון הדרייב %d/%d · ממוצע EOD−פתיחה בכיוון %+.2f" % (short(t), len(rows), ok, len(rows), statistics.mean((e if d_ == "up" else -e) for d_, e, _, _ in rows)))
        elif t == "OPEN_REJECTION_REVERSE":
            ok = sum(1 for d_, e, _, _ in rows if (e > 0) == (d_ == "up"))
            P("- ORR: %d ימים · סגירת-היום בצד ההיפוך %d/%d" % (len(rows), ok, len(rows)))
        else:
            P("- %s: %d ימים · |EOD−פתיחה| ממוצע %.2f · טווח ממוצע +%.2f/−%.2f" % (short(t), len(rows), statistics.mean(abs(e) for _, e, _, _ in rows),
                                                                             statistics.mean(h for _, _, h, _ in rows), statistics.mean(l for _, _, _, l in rows)))
    text = "\n".join(lines)
    print(text)
    if a.bars:
        print("\n## הברים (8 הראשונים, יחסית לפתיחה)\n")
        print("\n\n".join(per_day_bars))
    if a.md:
        with open(os.path.join(ROOT, a.md), "w", encoding="utf-8") as fh:
            fh.write(text + ("\n\n## הברים (8 הראשונים, יחסית לפתיחה)\n\n```\n" + "\n\n".join(per_day_bars) + "\n```\n" if a.bars else "\n"))
        print("wrote", a.md)


if __name__ == "__main__":
    main()
