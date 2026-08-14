#!/usr/bin/env python3
"""replay_day.py — replay all detectors on a day's bars from DB.

Reports RAW fires (every detection event) and DISTINCT fires (deduped
per pattern+direction, 30-bar cooldown). The distinction matters because
stateless detectors (Double Top) fire on every bar after breakout.

Usage: python3 scripts/replay_day.py [--date 2026-06-08]
Output: docs/reports/REPLAY_<date>_RAW.txt
"""
import os
import sys
from datetime import datetime

# 14.08 ROOT-FIX (Michael: "אני רוצה הוכחה שהמערכת מזהה"): without these two
# lines the script silently fell back to a stale/corrupt SQLite file
# ("database disk image is malformed" swallowed by read_all) and reported
# "0 patterns" — which is what made us believe on 13.08 that no engine-replay
# module existed. It existed; it was querying an empty database.
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATE = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else "2026-06-08"
OUT = f"docs/reports/REPLAY_{DATE}_RAW.txt"


def main():
    from backend.v9.db.read import read_all
    from backend.v9.systems.woodies.schemas import WoodiesBar
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem

    # ── S4 Woodies ──
    from backend.v9.systems.woodies.patterns.zlr import detect as detect_zlr
    from backend.v9.systems.woodies.patterns.tlb import detect as detect_tlb
    from backend.v9.systems.woodies.patterns.tt import detect as detect_tt
    from backend.v9.systems.woodies.patterns.gb100 import detect as detect_gb100
    from backend.v9.systems.woodies.patterns.vegas import detect as detect_vegas
    from backend.v9.systems.woodies.patterns.ghost import detect as detect_ghost
    from backend.v9.systems.woodies.patterns.famir import detect as detect_famir
    from backend.v9.systems.woodies.patterns.htlb import detect as detect_htlb
    from backend.v9.systems.woodies.patterns.hfe import detect as detect_hfe
    from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
    from backend.v9.systems.five_min.patterns.double_bt import detect_double_bottom_ee, detect_double_top_aa
    from backend.v9.systems.five_min.patterns.flags import detect_bull_flag, detect_bear_flag

    lines = [f"REPLAY {DATE} — raw + distinct fire counts\n{'='*70}\n"]

    # Load woodies bars
    w_rows = read_all(f"SELECT * FROM v9_bars_5min_woodies WHERE ts >= '{DATE}' ORDER BY ts ASC", {})
    w_bars = []
    for r in w_rows:
        w_bars.append(WoodiesBar(
            ts=float(r['ts'].timestamp()), open=float(r['open']), high=float(r['high']),
            low=float(r['low']), close=float(r['close']), volume=int(r['volume'] or 0),
            cci_14=float(r['cci_14']), cci_6_tcci=float(r['cci_6_tcci'] or 0),
            trend_state=r['trend_state'] or 'GRAY',
        ))

    lines.append(f"\nS4 Woodies: {len(w_bars)} bars\n{'-'*40}")

    s4_detectors = [
        ("ZLR", detect_zlr, 13), ("TLB", detect_tlb, 10), ("TT", detect_tt, 3),
        ("GB100", detect_gb100, 3), ("VEGAS", detect_vegas, 20), ("GHOST", detect_ghost, 20),
        ("FAMIR", detect_famir, 5), ("HTLB", detect_htlb, 15), ("HFE", detect_hfe, 20),
    ]

    total_raw_s4 = 0
    total_distinct_s4 = 0
    for name, fn, min_b in s4_detectors:
        raw_fires = []
        for i in range(min_b, len(w_bars)):
            try:
                r = fn(w_bars[:i+1])
                if r.detected:
                    ts = str(w_rows[i]['ts'])[:19]
                    raw_fires.append(f"  {ts} {r.direction:>5} cci={w_bars[i].cci_14:.0f} stop={r.stop:.2f}")
            except Exception:
                pass
        # Distinct: dedup by direction, 30-bar cooldown
        distinct = []
        last_fire = {}
        for i in range(min_b, len(w_bars)):
            try:
                r = fn(w_bars[:i+1])
                if r.detected:
                    key = f"{name}_{r.direction}"
                    if key not in last_fire or (i - last_fire[key]) >= 6:
                        distinct.append(f"  {str(w_rows[i]['ts'])[:19]} {r.direction:>5} cci={w_bars[i].cci_14:.0f}")
                        last_fire[key] = i
            except Exception:
                pass

        total_raw_s4 += len(raw_fires)
        total_distinct_s4 += len(distinct)
        lines.append(f"\n{name}: {len(raw_fires)} raw / {len(distinct)} distinct")
        for f in raw_fires:
            lines.append(f)

    # ── S2 Five-Min ──
    f_rows = read_all(f"SELECT ts, open, high, low, close, volume, poc_vol FROM v9_bars_5min WHERE ts >= '{DATE}' ORDER BY ts ASC", {})
    f_bars = [{'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']),
               'c': float(r['close']), 'vol': int(r['volume'] or 0), 'v': int(r['volume'] or 0),
               'poc_vol': float(r.get('poc_vol') or 0), 'poc': float(r.get('poc_vol') or 0),
               'ts': str(r['ts'])} for r in f_rows]

    lines.append(f"\n\nS2 Five-Min: {len(f_bars)} bars\n{'-'*40}")

    fs = FiveMinSystem()
    s2_detectors = [
        ("Reactive", fs._detect_reactive, 7),
        ("Initiative", fs._detect_initiative, 7),
        ("Inv_HnS", detect_inverse_hns, 30),
        ("HnS_Top", detect_hns_top, 30),
        ("Double_Bot", lambda b: detect_double_bottom_ee(b, atr_5m=3.0), 30),
        ("Double_Top", lambda b: detect_double_top_aa(b, atr_5m=3.0), 30),
        ("Bull_Flag", detect_bull_flag, 20),
        ("Bear_Flag", detect_bear_flag, 20),
    ]

    total_raw_s2 = 0
    total_distinct_s2 = 0
    for name, fn, min_b in s2_detectors:
        raw_fires = []
        for i in range(min_b, len(f_bars)):
            try:
                d, c, info = fn(f_bars[:i])  # buffer[:-1] = completed bars
                if d:
                    raw_fires.append(f"  {f_bars[i-1]['ts'][:19]} {d:>5} conf={c:.2f} kind={info.get('kind','')}")
            except Exception:
                pass
        # Distinct
        distinct = []
        last_fire = {}
        for i in range(min_b, len(f_bars)):
            try:
                d, c, info = fn(f_bars[:i])
                if d:
                    key = f"{name}_{d}"
                    if key not in last_fire or (i - last_fire[key]) >= 6:
                        distinct.append(f"  {f_bars[i-1]['ts'][:19]} {d:>5}")
                        last_fire[key] = i
            except Exception:
                pass

        total_raw_s2 += len(raw_fires)
        total_distinct_s2 += len(distinct)
        lines.append(f"\n{name}: {len(raw_fires)} raw / {len(distinct)} distinct")
        for f in raw_fires:
            lines.append(f)

    lines.append(f"\n\n{'='*70}")
    lines.append(f"TOTALS:")
    lines.append(f"  S4: {total_raw_s4} raw / {total_distinct_s4} distinct")
    lines.append(f"  S2: {total_raw_s2} raw / {total_distinct_s2} distinct")
    lines.append(f"  ALL: {total_raw_s4+total_raw_s2} raw / {total_distinct_s4+total_distinct_s2} distinct")
    lines.append(f"\n'raw' = every detection event (stateless detectors fire repeatedly)")
    lines.append(f"'distinct' = deduped per pattern+direction, 6-bar (30min) cooldown")

    text = "\n".join(lines)
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
