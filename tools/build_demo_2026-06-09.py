#!/usr/bin/env python3
"""
build_demo_2026-06-09.py — assemble a REAL replay_data_2026-06-09.json from the
two real JSON exports that already live in the repo, so the renderer can be
demoed without a Mac DB run.

Inputs (real, committed):
  docs/reports/bars_woodies_0609_0611.json  -> list of {ts,o,h,l,c,cci}
                                               (+03:00 ts; NO volume, NO levels)
  docs/reports/trades_full.json             -> {"trades":[...]} rich per-trade

Output:
  tools/replay_data_2026-06-09.json  (same shape export_replay_data.py emits)

HONEST FAILURE: these source files do NOT carry volume, TPO levels, CVD, or a
per-bar day-type. We therefore emit:
    cvd      = []
    volume   = null  (per bar)
    day_type = the day_type stamped on 2026-06-09 trades, if any (else null)
…and NEVER synthesize them. The renderer will show those as "missing".

REAL IB (legitimate trading-logic-on-real-bars, allowed by CLAUDE.md):
    levels.ibh = max(high) over the first-hour RTH bars 08:30–09:30 CT
    levels.ibl = min(low)  over the same bars
computed from the REAL OHLC already in the source. This is NOT synthesis — it is
the Initial Balance definition applied to ingested bars (CLAUDE.md § Sierra
real-time data explicitly allows "trading logic on ingested bars"). The level
lines are labeled "IB (from bars)" so they are never confused with the Sierra
TPO export. POC/VAH/VAL are LEFT NULL — those need the volume/TPO profile from
canonical v9_tpo_sessions (Mac export) and are NOT computable from OHLC alone.

Bars + CCI + trades + the IB high/low are 100% REAL.
"""

import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BARS_SRC = os.path.join(REPO, "docs", "reports", "bars_woodies_0609_0611.json")
TRADES_SRC = os.path.join(REPO, "docs", "reports", "trades_full.json")
OUT = os.path.join(HERE, "replay_data_2026-06-09.json")

DATE = "2026-06-09"
CT = timezone(timedelta(hours=-5))   # America/Chicago in June (CDT, UTC-5)


def to_ct(ts_str):
    """'2026-06-09 14:55:00+03:00' or ISO 'T' -> aware datetime in CT."""
    s = ts_str.replace(" ", "T", 1) if " " in ts_str and "T" not in ts_str else ts_str
    dt = datetime.fromisoformat(s)
    return dt.astimezone(CT)


def compute_ib_from_bars(bars):
    """REAL Initial Balance from the first-hour RTH bars (08:30–09:30 CT).

    IB high = max(high), IB low = min(low) over bars whose CT wall-clock time is
    in [08:30:00, 09:30:00). This is the textbook IB definition applied to the
    REAL ingested OHLC — allowed by CLAUDE.md (trading logic on ingested bars),
    NOT synthesis. Returns (ibh, ibl, n_bars). If no first-hour bar is present
    (e.g. a half-day export), returns (None, None, 0) — honest, never faked.

    `bars` are the already-built per-bar dicts with CT-wall-clock "ts" strings.
    """
    his, los = [], []
    for b in bars:
        ts = b.get("ts")           # "YYYY-MM-DDTHH:MM:SS" CT wall clock
        if not ts or "T" not in ts:
            continue
        hhmm = ts[11:16]           # "HH:MM"
        # First-hour RTH window: 08:30 inclusive .. 09:30 exclusive (CT).
        if "08:30" <= hhmm < "09:30":
            if b.get("h") is not None:
                his.append(b["h"])
            if b.get("l") is not None:
                los.append(b["l"])
    if not his or not los:
        return None, None, 0
    return max(his), min(los), len(his)


def main():
    bars_raw = json.load(open(BARS_SRC))
    trades_doc = json.load(open(TRADES_SRC))
    trades_all = trades_doc.get("trades", trades_doc)

    # ── bars for 2026-06-09 CT ───────────────────────────────────────────────
    bars = []
    for r in bars_raw:
        ct = to_ct(r["ts"])
        if ct.strftime("%Y-%m-%d") != DATE:
            continue
        bars.append({
            "ts": ct.strftime("%Y-%m-%dT%H:%M:%S"),     # CT wall clock
            "epoch": int(ct.astimezone(timezone.utc).timestamp()),
            "o": r.get("o"), "h": r.get("h"), "l": r.get("l"), "c": r.get("c"),
            "volume": None,                # REAL source has no volume
            "cci": r.get("cci"),           # REAL
            "trend_state": None,           # not in this export
            "zlr": 0, "zlr_direction": None,
            "hfe": 0, "hfe_direction": None,
        })
    bars.sort(key=lambda b: b["epoch"])

    # ── trades for 2026-06-09 CT (by entry_ts) ───────────────────────────────
    trades = []
    daytypes = {}
    for t in trades_all:
        e = t.get("entry_ts")
        if not e:
            continue
        ct = to_ct(e)
        if ct.strftime("%Y-%m-%d") != DATE:
            continue
        xct = to_ct(t["exit_ts"]) if t.get("exit_ts") else None
        dt = t.get("day_type")
        if dt and dt != "UNKNOWN":
            daytypes[dt] = daytypes.get(dt, 0) + 1
        trades.append({
            "id": t.get("id"),
            "mode": t.get("mode"),
            "system": t.get("firing_system") or t.get("system"),
            "direction": t.get("direction"),
            "state": t.get("state"),
            "entry_ts": ct.strftime("%Y-%m-%dT%H:%M:%S"),
            "entry_epoch": int(ct.astimezone(timezone.utc).timestamp()),
            "entry_price": t.get("entry_price"),
            "stop": t.get("stop"),
            "t1": t.get("t1"), "t2": t.get("t2"), "t3": t.get("t3"),
            "exit_ts": xct.strftime("%Y-%m-%dT%H:%M:%S") if xct else None,
            "exit_epoch": int(xct.astimezone(timezone.utc).timestamp()) if xct else None,
            "exit_price": t.get("exit_price"),
            "exit_reason": t.get("exit_reason"),
            "pnl_usd": t.get("pnl_usd"),
            "pnl_r": t.get("pnl_r"),
            "outcome": t.get("outcome"),
            "pattern_id": t.get("pattern_id"),
            "day_type": t.get("day_type"),
        })
    trades.sort(key=lambda x: x["entry_epoch"])

    # Best-available day_type from the trades (honest: may be null/UNKNOWN-only).
    day_type = max(daytypes, key=daytypes.get) if daytypes else None

    # REAL Initial Balance from the first-hour RTH bars (trading logic on real
    # OHLC — allowed). POC/VAH/VAL stay null (need the Mac TPO export).
    ibh, ibl, ib_n = compute_ib_from_bars(bars)
    if ibh is not None and ibl is not None:
        levels = {
            "ibh": ibh,
            "ibl": ibl,
            "poc": None, "vah": None, "val": None,   # honest: need Mac TPO export
            # Tells the renderer to label these "IB (from bars)" not plain "IBH".
            "ib_source": "bars",
            "ib_label": "IB (from bars)",
            "ib_bars": ib_n,
        }
    else:
        levels = None   # no first-hour RTH bars → honest missing

    payload = {
        "date": DATE,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "build_demo_2026-06-09.py (REAL bars+cci+trades + IB-from-real-bars; "
                  "volume/POC/VAH/VAL/cvd NOT in source exports)",
        "day_type": day_type,
        "day_type_source": ("v9_trades.day_type (stamped) — from repo trades_full.json"
                            if day_type else "missing"),
        "day_type_timeline": None,   # per-bar 7-type timeline needs the Mac classify_replay endpoint
        "levels": levels,   # ibh/ibl REAL (IB from first-hour bars); poc/vah/val null
        "bars": bars,
        "cvd": [],          # honest: not in source exports
        "trades": trades,
        "_notes": {
            "real": ["bars(OHLC)", "cci", "trades", "IBH/IBL (computed from real "
                     "first-hour RTH bars 08:30-09:30 CT)"],
            "missing_needs_mac_export": ["volume", "POC/VAH/VAL (TPO profile)", "cvd",
                                          "trend_state", "zlr/hfe", "per-bar day_type"],
        },
    }

    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=1)

    print(f"Wrote {OUT}")
    print(f"  bars={len(bars)} trades={len(trades)} day_type={day_type or 'MISSING'}")
    if levels:
        print(f"  IB (from real 08:30-09:30 CT bars, n={levels['ib_bars']}): "
              f"IBH={levels['ibh']} IBL={levels['ibl']}  (POC/VAH/VAL=null, need Mac TPO)")
    else:
        print("  IB: MISSING (no first-hour RTH bars in source)")
    if bars:
        print(f"  bar range CT: {bars[0]['ts']} .. {bars[-1]['ts']}")
    for tr in trades:
        print(f"  trade #{tr['id']} {tr['direction']} {tr['pattern_id']} "
              f"entry {tr['entry_ts'][11:16]} @{tr['entry_price']} "
              f"exit @{tr['exit_price']} pnl={tr['pnl_usd']}")


if __name__ == "__main__":
    main()
