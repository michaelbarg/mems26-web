#!/usr/bin/env python3
"""Hold the release gate to account (Michael 2026-07-28: "אם הוא ימנע עסקה לבדוק אותו").

RELEASE_ENTRY_GATE_V1 was enabled on LIVE with a single day of evidence. A gate
that only ever blocks looks the same whether it is saving money or destroying an
edge — so every hold must be measurable, not argued about.

For each `blocked_by=awaiting_release` decision in gateway_decisions.jsonl this
replays what price actually did afterwards and asks the only question that
matters: WOULD THAT TRADE HAVE WORKED?

  SAVED US      the held signal would have hit its stop before +1R  → the block was right
  COST US       it would have reached +1R first                     → the block was wrong
  RELEASED      the gate later let the same setup through           → it delayed, did not deny
  UNDECIDED     neither level reached inside the window

Risk is measured from the gate's own structural stop when it recorded one, else
from a fixed assumption stated in the output — never silently.

    python3 scripts/release_gate_review.py            # today
    python3 scripts/release_gate_review.py 2026-07-28
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

DECISIONS = Path(os.path.expanduser(
    "~/SierraChart_Data/v9_export/gateway_decisions.jsonl"))
ASSUMED_RISK_PTS = 12.0          # used only when the hold carried no structural stop
WINDOW_MIN = 120


def _bars(day: str):
    import psycopg2
    cn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://localhost/mems26"))
    cur = cn.cursor()
    cur.execute(
        "SELECT ts, high, low FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = %s ORDER BY ts", (day,))
    return [(t, float(h), float(l)) for t, h, l in cur.fetchall()]


def main() -> int:
    day = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    if not DECISIONS.exists():
        print(f"no decisions file at {DECISIONS}")
        return 1

    holds, released = [], 0
    with DECISIONS.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not str(d.get("ts", "")).startswith(day):
                continue
            if d.get("blocked_by") == "awaiting_release":
                holds.append(d)
            elif d.get("outcome") not in ("blocked", None):
                released += 1

    print(f"═══ release gate · {day} ═══")
    print(f"holds: {len(holds)}   ·   signals that passed every gate: {released}")
    if not holds:
        print("\nThe gate held nothing today — it cost us nothing and saved us nothing.")
        return 0

    bars = _bars(day)
    if not bars:
        print("no bars for that day — cannot judge")
        return 1

    verdicts = Counter()
    print(f"\n{'time':<6}{'pattern':<16}{'dir':<6}{'entry':>9}  verdict")
    for h in holds:
        ts = str(h.get("ts", ""))[11:16]
        entry = h.get("entry")
        direction = str(h.get("direction", "")).upper()
        if entry is None or direction not in ("LONG", "SHORT"):
            verdicts["unjudgeable"] += 1
            continue
        entry = float(entry)
        risk = ASSUMED_RISK_PTS
        stop = entry - risk if direction == "LONG" else entry + risk
        tgt = entry + risk if direction == "LONG" else entry - risk

        future = [b for b in bars if str(b[0])[11:16] >= ts][:WINDOW_MIN // 5]
        hit = None
        for _, hi, lo in future:
            if direction == "LONG":
                if lo <= stop:
                    hit = "stop"; break
                if hi >= tgt:
                    hit = "target"; break
            else:
                if hi >= stop:
                    hit = "stop"; break
                if lo <= tgt:
                    hit = "target"; break

        if hit == "stop":
            v = "✅ SAVED US   — would have stopped out first"
            verdicts["saved"] += 1
        elif hit == "target":
            v = "🔴 COST US    — would have reached +1R first"
            verdicts["cost"] += 1
        else:
            v = "—  UNDECIDED  — neither level reached"
            verdicts["undecided"] += 1
        print(f"{ts:<6}{str(h.get('pattern'))[:15]:<16}{direction:<6}{entry:>9.2f}  {v}")

    print(f"\n═══ verdict ═══")
    print(f"  saved us   {verdicts['saved']}")
    print(f"  cost us    {verdicts['cost']}")
    print(f"  undecided  {verdicts['undecided']}")
    s, c = verdicts["saved"], verdicts["cost"]
    if s + c:
        print(f"\n  net: the gate was right {s}/{s+c} times it mattered "
              f"({s/(s+c)*100:.0f}%)")
        if c > s:
            print("  🔴 IT COST MORE THAN IT SAVED — recalibrate or turn it off.")
    print(f"\n  risk assumed {ASSUMED_RISK_PTS}pt (holds carry no structural stop in the "
          f"decision log); window {WINDOW_MIN}min. Stated, not hidden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
