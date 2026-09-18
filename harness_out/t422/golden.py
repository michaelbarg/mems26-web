#!/usr/bin/env python3
"""T-422 golden — LIVE decisions (from the log) vs the FIXED gate (canonical bars).

Honest by construction:
  * the OLD column is NOT a simulation — it is what the live gate actually
    logged that day ("OPENING_FIRST_TRADE_STRICT held ... (o=... c=...)"),
    parsed out of /tmp/backend.err.log;
  * the NEW column runs the REAL opening_first_trade_ok() against the canonical
    closed bars that existed at that same instant (ts <= now - 5min, the same
    definition the fix and fwd_harness --oe-closed use).

Usage: python3 harness_out/t422/golden.py 2026-09-18 SHORT
"""
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.systems.opening_entry import opening_first_trade_ok  # noqa: E402

PSQL = "/Applications/Postgres.app/Contents/Versions/18/bin/psql"
DSN = "postgresql://localhost/mems26"
LOG = "/tmp/backend.err.log"
IL = timezone(timedelta(hours=3))          # Asia/Jerusalem in September (IDT)

HELD = re.compile(
    r"^(?P<d>\d{4}-\d{2}-\d{2}) (?P<t>\d{2}:\d{2}:\d{2}).*OPENING_FIRST_TRADE_STRICT "
    r"held (?P<typ>\S+) (?P<dir>\S+) . (?P<why>.*)$")


def canonical_bars(session):
    sql = ("SELECT ts, open, close FROM v9_bars_5min_woodies WHERE symbol='MES' "
           f"AND (ts AT TIME ZONE 'America/New_York')::date = '{session}' "
           "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
           "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' ORDER BY ts")
    out = subprocess.run([PSQL, DSN, "-X", "-A", "-F", "\t", "-t", "-c", sql],
                         capture_output=True, text=True, check=True).stdout
    bars = []
    for line in out.strip().splitlines():
        ts_s, o, c = line.split("\t")
        # py3.9's fromisoformat needs a 2-part offset ("+03" -> "+03:00")
        if re.search(r"[+-]\d{2}$", ts_s):
            ts_s += ":00"
        ts = datetime.fromisoformat(ts_s)
        bars.append({"ts": ts.astimezone(timezone.utc).isoformat(),
                     "_dt": ts.astimezone(timezone.utc),
                     "_il": ts.astimezone(IL).strftime("%H:%M"),
                     "o": float(o), "c": float(c)})
    return bars


def live_held_lines(session):
    rows = []
    with open(LOG, "r", errors="replace") as fh:
        for line in fh:
            if "OPENING_FIRST_TRADE_STRICT held" not in line:
                continue
            m = HELD.match(line.rstrip("\n"))
            if m and m.group("d") == session:
                rows.append(m.groupdict())
    return rows


def main():
    session, direction = sys.argv[1], sys.argv[2]
    bars = canonical_bars(session)
    held = live_held_lines(session)
    print("=== T-422 GOLDEN - session %s - direction %s ===" % (session, direction))
    print("canonical opening bars (IL): " +
          " | ".join("%s o%g/c%g" % (b["_il"], b["o"], b["c"]) for b in bars[:7]))
    print()
    print("%-9s %-54s %s" % ("IL time", "LIVE (what actually happened)",
                             "FIXED gate (canonical closed bars)"))
    print("-" * 150)
    first_ok = None
    for h in held:
        now = datetime.fromisoformat("%sT%s" % (h["d"], h["t"])).replace(tzinfo=IL)
        cutoff = now.astimezone(timezone.utc) - timedelta(minutes=5)
        closed = [b for b in bars if b["_dt"] <= cutoff]
        ok, why = opening_first_trade_ok([], h["dir"], None,
                                         closed_bars=closed, now_utc=now)
        if ok and first_ok is None:
            first_ok = (h["t"], closed[-1] if closed else None)
        print("%-9s %-54s %s - %s" % (h["t"], ("HELD: " + h["why"])[:54],
                                      "CONFIRMED" if ok else "held", why))
    print()
    if first_ok:
        b = first_ok[1]
        print("=> FIXED gate confirms at %s IL on the closed %s bar "
              "(o=%g c=%g); entry ~%g instead of the live entry."
              % (first_ok[0], b["_il"], b["o"], b["c"], b["c"]))
    else:
        print("=> FIXED gate did NOT confirm at any logged instant.")

    # HYPOTHETICAL: the gate at every bar-open instant (+5s), regardless of
    # whether a trigger actually reached it that day. Answers "when WOULD the
    # confirmation land", separately from "did anything ask".
    print()
    print("--- HYPOTHETICAL: fixed gate at every bar open +5s (assumes a %s "
          "trigger is present; it may not have been) ---" % direction)
    for b in bars[1:7]:
        now = b["_dt"] + timedelta(seconds=5)
        closed = [x for x in bars if x["_dt"] <= now - timedelta(minutes=5)]
        ok, why = opening_first_trade_ok([], direction, None,
                                         closed_bars=closed, now_utc=now)
        print("%-9s %s - %s" % (b["_il"] + ":05", "CONFIRMED" if ok else "held", why))


if __name__ == "__main__":
    main()
