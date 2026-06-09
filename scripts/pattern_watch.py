#!/usr/bin/env python3
"""pattern_watch.py — poll build/pattern-status, log per-pattern blockers.
Read-only: GETs the diagnostic endpoint only; never routes trades. Michael 2026-06-08.
Usage: python3 scripts/pattern_watch.py [--once]"""
import json, sys, time, urllib.request
from collections import Counter
from datetime import datetime

URL = "http://localhost:8000/api/v9/build/pattern-status?systems=five_min,woodies"
INTERVAL_MIN = 15
END_HHMM = "22:00"            # local wall-clock stop (machine TZ)
LOG = "docs/reports/pattern_watch_{date}.log".format(date=datetime.now().strftime("%Y-%m-%d"))

def fetch():
    with urllib.request.urlopen(URL, timeout=5) as r:
        return json.load(r)

def render(data):
    out = []
    ts = datetime.now().strftime("%H:%M:%S")
    verdict = (data.get("readiness") or {}).get("verdict", "?")
    out.append(f"=== {ts}  readiness={verdict} ===")
    counter = Counter(); n_armed = n_blocked = n_fired = 0
    for so in data.get("systems", []):
        if so.get("id") not in ("five_min", "woodies"):
            continue
        out.append(f"  [{so.get('name', so.get('id'))}]")
        for p in so.get("patterns", []):
            st = p.get("status"); blk = p.get("blockers") or []
            n_armed  += st == "armed"
            n_blocked += st == "blocked"
            n_fired  += st == "fired"
            for b in blk: counter[b] += 1
            out.append(f"    {str(p.get('id')):<16} {str(st):<9} missing: {', '.join(blk) if blk else '—'}")
    out.append(f"  SUMMARY armed={n_armed} blocked={n_blocked} fired={n_fired} "
               f"| top blockers: {counter.most_common(3)}")
    return "\n".join(out)

def main():
    once = "--once" in sys.argv
    print(f"# pattern_watch start {datetime.now():%Y-%m-%d %H:%M %Z} → until {END_HHMM} local, every {INTERVAL_MIN}m")
    while True:
        try:
            block = render(fetch())
        except Exception as e:
            block = f"=== {datetime.now():%H:%M:%S}  ENDPOINT ERROR: {e} ==="
        print(block, flush=True)
        with open(LOG, "a") as f:
            f.write(block + "\n")
        if once:
            break
        if datetime.now().strftime("%H:%M") >= END_HHMM:
            print(f"# reached {END_HHMM} local — stopping.")
            break
        time.sleep(INTERVAL_MIN * 60)

if __name__ == "__main__":
    main()
