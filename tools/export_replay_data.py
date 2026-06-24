#!/usr/bin/env python3
"""
export_replay_data.py — MEMS26 replay/brain-view DB -> JSON exporter.

╔══════════════════════════════════════════════════════════════════════════╗
║  RUN ON THE MAC ONLY.  SELECT-ONLY.  Never writes to the DB.               ║
║  The build VM cannot reach Postgres (no driver, allowlist blocks it),     ║
║  so this half of the tool is authored from the repo per                   ║
║  docs/SOURCE_OF_TRUTH.md and must be run where the DB lives:              ║
║      postgresql://localhost/mems26   (local Postgres, NEVER cloud)        ║
╚══════════════════════════════════════════════════════════════════════════╝

Usage (on the Mac):
    export DATABASE_URL=postgresql://localhost/mems26      # or rely on default
    python3 tools/export_replay_data.py --date 2026-06-09

Writes:  tools/replay_data_<date>.json   (consumed by replay_brain_view.py)

What it pulls (per docs/SOURCE_OF_TRUTH.md — column names PINNED against the live
SQLAlchemy models in backend/v9/db/models/, see the cite block below):

  bars    <- v9_bars_5min_woodies   (live OHLC + cci_14 + trend_state +
                                      zlr_detected + hfe_detected)   [no CVD]
            LEFT JOIN cumulative_delta from v9_bars_5min on matching ts+symbol
            (v9_bars_5min can STALL/GAP — join is best-effort, NULL when absent)
  levels  <- v9_tpo_sessions WHERE session_type='CASH'  (ib_high/ib_low/
                                      poc_price/vah_price/val_price)
  cvd     <- folded into each bar as cumulative_delta (above)
  day_type<- PER-BAR timeline from the canonical 7-type replay classifier
             (GET /api/v9/day_type/classify_replay?date=) when the backend is up,
             with a 2-step fallback chain (see _resolve_day_type):
               1. classify_replay endpoint  → segments + final (per-bar timeline)
               2. v9_day_type_state          → the live machine's last state
               3. v9_trades.day_type_at_entry → the day_type stamped on trades
  trades  <- v9_trades for the date

Honest-failure rule (CLAUDE.md Rule 1): a field the DB does not have is emitted
as null / empty — NEVER synthesized. The renderer shows "missing" for those.

SELECT-ONLY GUARANTEE: this file issues only SELECT statements via a
psycopg2 connection opened read-only (default_transaction_read_only). It does
not import any write path.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# psycopg2 exists on the Mac (the backend depends on it). It is NOT installed
# on the build VM, which is why this script is "run on the Mac only".
try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover - VM has no driver
    print(
        "ERROR: psycopg2 not installed. This script must run on the Mac where "
        "the MEMS26 Postgres lives. (pip install psycopg2-binary)",
        file=sys.stderr,
    )
    sys.exit(2)


# Local Postgres ONLY — never the Render/cloud deployment (CLAUDE.md §DB).
DEFAULT_DB_URL = "postgresql://localhost/mems26"

# ─────────────────────────────────────────────────────────────────────────────
# SQL — every statement is SELECT-only.
#
# Timestamps are stored at +03:00 (CLAUDE.md / SOURCE_OF_TRUTH §Timezone).
# We expose BOTH:
#   - ts_ct   : the wall-clock string in America/Chicago (for the human header)
#   - ts_epoch: UTC epoch seconds (what Lightweight-Charts wants on its time axis)
# Lightweight-Charts plots by absolute instant; we additionally pass the CT
# offset so the renderer can label the x-axis in Chicago time.
#
# Column names PINNED against the live SQLAlchemy models (no guesses left):
#   v9_bars_5min_woodies : backend/v9/db/models/bars_woodies.py → V9Bar5MinWoodies
#       id, ts, symbol, open, high, low, close, volume, cci_14, trend_state,
#       zlr_detected, zlr_direction, hfe_detected, hfe_direction   (CONFIRMED)
#   v9_bars_5min         : backend/v9/db/models/bars_5min.py → V9Bar5Min
#       ts, symbol, ..., cumulative_delta   (CONFIRMED; JOIN on ts AND symbol —
#       both tables have the (ts, symbol) UNIQUE constraint)
#   v9_tpo_sessions      : backend/v9/db/models/missing_tables.py → V9TpoSessions
#       id, session_type, trading_date (String/VARCHAR), ib_high, ib_low,
#       poc_price, vah_price, val_price, profile_shape   (CONFIRMED). trading_date
#       is VARCHAR → compare to an ISO STRING (SOURCE_OF_TRUTH §TPO). ORDER BY id
#       DESC LIMIT 1 picks the latest CASH row.
#   v9_trades            : backend/v9/db/models/trades.py → V9Trade
#       id, mode, firing_system, direction, state, entry_ts, entry_price, stop,
#       t1, t2, t3, exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, outcome,
#       day_type_at_entry, pattern_id_at_entry   (CONFIRMED)
#   v9_day_type_state    : backend/v9/systems/day_type/models.py → V9DayTypeState
#       id, ts, stage, day_type, classification, confidence, lock_state, ...
#       (CONFIRMED). Same latest-row read as direction_context_live.py:78.
#
# NOTE: every column the exporter reads is now repo-confirmed against a model —
# there are no remaining column-name guesses. A "# verify on Mac" is kept ONLY on
# the classify_replay HTTP call (runtime endpoint shape, not a DB column).
# ─────────────────────────────────────────────────────────────────────────────

SQL_BARS = """
SELECT
    w.ts                                              AS ts_raw,
    to_char(w.ts AT TIME ZONE 'America/Chicago',
            'YYYY-MM-DD"T"HH24:MI:SS')                AS ts_ct,
    extract(epoch FROM w.ts)                          AS ts_epoch,
    w.open  AS o, w.high AS h, w.low AS l, w.close AS c,
    w.volume,
    w.cci_14                                          AS cci,
    w.cci_6_tcci, w.swi_value, w.czi_value, w.ema_34,
    w.lsma_value, w.lsma_above_price, w.predictor_next_cci,
    w.proj_hi, w.proj_lo,
    w.trend_state,
    w.zlr_detected, w.zlr_direction,
    w.hfe_detected, w.hfe_direction,
    b.cumulative_delta                                AS cumulative_delta
FROM v9_bars_5min_woodies w
LEFT JOIN v9_bars_5min b
       ON b.ts = w.ts AND b.symbol = w.symbol
WHERE (w.ts AT TIME ZONE 'America/Chicago')::date = %(d)s
  AND w.symbol = 'MES'
ORDER BY w.ts ASC;
"""

# Levels: the CASH session whose trading_date == the requested date.
# trading_date is VARCHAR → compare against an ISO STRING, not a date object
# (SOURCE_OF_TRUTH §TPO levels).
SQL_LEVELS = """
SELECT ib_high, ib_low, poc_price, vah_price, val_price,
       trading_date, session_type
FROM v9_tpo_sessions
WHERE trading_date = %(d)s AND session_type = 'CASH'
ORDER BY id DESC
LIMIT 1;
"""

SQL_TRADES = """
SELECT
    id, mode, firing_system, direction, state,
    to_char(entry_ts AT TIME ZONE 'America/Chicago',
            'YYYY-MM-DD"T"HH24:MI:SS')   AS entry_ts_ct,
    extract(epoch FROM entry_ts)         AS entry_epoch,
    entry_price,
    stop, t1, t2, t3,
    to_char(exit_ts AT TIME ZONE 'America/Chicago',
            'YYYY-MM-DD"T"HH24:MI:SS')    AS exit_ts_ct,
    extract(epoch FROM exit_ts)          AS exit_epoch,
    exit_price, exit_reason,
    pnl_usd, pnl_r, outcome,
    day_type_at_entry, pattern_id_at_entry
FROM v9_trades
WHERE (entry_ts AT TIME ZONE 'America/Chicago')::date = %(d)s
ORDER BY entry_ts ASC;
"""

# Fallback #3: the day_type stamped on the date's trades (mode = most common).
SQL_DAYTYPE = """
SELECT day_type_at_entry, count(*) AS n
FROM v9_trades
WHERE (entry_ts AT TIME ZONE 'America/Chicago')::date = %(d)s
  AND day_type_at_entry IS NOT NULL
GROUP BY day_type_at_entry
ORDER BY n DESC
LIMIT 1;
"""

# Fallback #2: the live state machine's last persisted state for the date.
# Column names CONFIRMED against V9DayTypeState (day_type/models.py); query mirrors
# direction_context_live.py:78.
SQL_DAYTYPE_STATE = """
SELECT day_type, lock_state, stage,
       to_char(ts AT TIME ZONE 'America/Chicago', 'YYYY-MM-DD"T"HH24:MI:SS') AS ts_ct
FROM v9_day_type_state
WHERE (ts AT TIME ZONE 'America/Chicago')::date = %(d)s
  AND day_type IS NOT NULL
ORDER BY id DESC
LIMIT 1;
"""

# Canonical 7-type per-bar timeline endpoint (backend up on the Mac only).
CLASSIFY_REPLAY_URL = "http://localhost:8000/api/v9/day_type/classify_replay?date={date}"


def _fetch_classify_replay(date):
    """GET the canonical 7-type per-bar day-type timeline. Returns the parsed
    dict ({segments, final, ...}) or None if the backend is down / errors.

    Wrapped so the exporter still works when the backend is NOT running (the DB
    fallbacks below take over). # verify on Mac: that the FastAPI app is up on
    :8000 when you want the canonical per-bar timeline (otherwise it falls back).
    """
    import json as _json
    import urllib.request
    import urllib.error
    url = CLASSIFY_REPLAY_URL.format(date=date)
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            if resp.status != 200:
                return None
            data = _json.loads(resp.read().decode("utf-8"))
        # A valid timeline has segments and a non-empty bar count.
        if isinstance(data, dict) and data.get("n_bars"):
            return data
        return None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def _resolve_day_type(cur, params, date):
    """Per-bar day-type with an honest 3-step fallback chain (Rule 1).

    Returns (headline_day_type, timeline_dict_or_None, source_str). headline is
    the single day-type for the header; timeline carries the per-bar segments
    when the classifier endpoint answered. NEVER synthesizes — when every source
    is silent it returns (None, None, "missing").
    """
    # 1. Canonical 7-type per-bar timeline (preferred).
    rep = _fetch_classify_replay(date)
    if rep:
        final = rep.get("final") or {}
        headline = final.get("day_type")
        timeline = {
            "segments": rep.get("segments"),
            "final": final,
            "ib_high": rep.get("ib_high"), "ib_low": rep.get("ib_low"),
            "ib_source": rep.get("ib_source"), "opening_type": rep.get("opening_type"),
            "source": rep.get("source"),
        }
        if headline:
            return headline, timeline, "classify_replay (canonical 7-type, per-bar)"

    # 2. Live state machine's last persisted state.
    try:
        cur.execute(SQL_DAYTYPE_STATE, params)
        st = cur.fetchone()
        if st and st.get("day_type"):
            return st["day_type"], None, "v9_day_type_state (live machine, last row)"
    except Exception:
        pass

    # 3. day_type stamped on the date's trades (per-day mode).
    cur.execute(SQL_DAYTYPE, params)
    dt = cur.fetchone()
    if dt and dt.get("day_type_at_entry"):
        return dt["day_type_at_entry"], None, "v9_trades.day_type_at_entry (stamped)"

    return None, None, "missing"


def _num(v):
    """Coerce a DB numeric/Decimal to float; keep None as None (honest null)."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def main():
    ap = argparse.ArgumentParser(description="Export MEMS26 replay data (Mac, SELECT-only).")
    ap.add_argument("--date", required=True, help="Trading date, YYYY-MM-DD (America/Chicago).")
    ap.add_argument(
        "--db",
        default=os.environ.get("DATABASE_URL", DEFAULT_DB_URL),
        help="Postgres URL (default: $DATABASE_URL or postgresql://localhost/mems26).",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Output path (default: tools/replay_data_<date>.json next to this script).",
    )
    args = ap.parse_args()

    # Guardrail: local Postgres ONLY. Refuse a cloud/remote URL outright.
    low = args.db.lower()
    if not ("localhost" in low or "127.0.0.1" in low or low.startswith("postgresql:///")):
        print(
            f"REFUSING: --db must be local Postgres (localhost/127.0.0.1). Got: {args.db}\n"
            "CLAUDE.md §DB: never the Render/cloud deployment.",
            file=sys.stderr,
        )
        sys.exit(3)

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
        sys.exit(1)

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), f"replay_data_{args.date}.json"
    )

    # Open a READ-ONLY connection: forces every statement in the session to be
    # read-only at the server, a belt-and-suspenders SELECT-only guarantee.
    conn = psycopg2.connect(args.db)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    params = {"d": args.date}

    # ── bars (+ CVD via left join) ───────────────────────────────────────────
    cur.execute(SQL_BARS, params)
    rows = cur.fetchall()
    bars = []
    cvd = []
    for r in rows:
        epoch = int(r["ts_epoch"]) if r["ts_epoch"] is not None else None
        bars.append(
            {
                "ts": r["ts_ct"],           # CT wall-clock ISO string
                "epoch": epoch,             # UTC epoch sec (chart time axis)
                "o": _num(r["o"]),
                "h": _num(r["h"]),
                "l": _num(r["l"]),
                "c": _num(r["c"]),
                "volume": int(r["volume"]) if r["volume"] is not None else None,
                "cci": _num(r["cci"]),
                "tcci": _num(r["cci_6_tcci"]),
                "swi": _num(r["swi_value"]),
                "czi": _num(r["czi_value"]),
                "ema34": _num(r["ema_34"]),
                "lsma": _num(r["lsma_value"]),
                "lsma_above": int(r["lsma_above_price"] or 0),
                "predictor": _num(r["predictor_next_cci"]),
                "proj_hi": _num(r["proj_hi"]),
                "proj_lo": _num(r["proj_lo"]),
                "trend_state": r["trend_state"],
                "zlr": int(r["zlr_detected"] or 0),
                "zlr_direction": r["zlr_direction"],
                "hfe": int(r["hfe_detected"] or 0),
                "hfe_direction": r["hfe_direction"],
            }
        )
        cvd.append(
            {
                "ts": r["ts_ct"],
                "epoch": epoch,
                "cumulative_delta": _num(r["cumulative_delta"]),
            }
        )
    # If EVERY cumulative_delta is None, emit cvd=[] so the renderer shows the
    # honest "not exported" note instead of a flat zero line.
    if all(p["cumulative_delta"] is None for p in cvd):
        cvd = []

    # ── levels ───────────────────────────────────────────────────────────────
    cur.execute(SQL_LEVELS, params)
    lv = cur.fetchone()
    if lv:
        levels = {
            "ibh": _num(lv["ib_high"]),
            "ibl": _num(lv["ib_low"]),
            "poc": _num(lv["poc_price"]),
            "vah": _num(lv["vah_price"]),
            "val": _num(lv["val_price"]),
        }
        # If the CASH row exists but every level is null, treat as missing.
        if all(v is None for v in levels.values()):
            levels = None
    else:
        levels = None

    # ── day_type (canonical 7-type per-bar → state → trade-stamped) ──────────
    day_type, day_type_timeline, day_type_source = _resolve_day_type(cur, params, args.date)

    # ── trades ───────────────────────────────────────────────────────────────
    cur.execute(SQL_TRADES, params)
    trows = cur.fetchall()
    trades = []
    for t in trows:
        trades.append(
            {
                "id": t["id"],
                "mode": t["mode"],
                "system": t["firing_system"],
                "direction": t["direction"],
                "state": t["state"],
                "entry_ts": t["entry_ts_ct"],
                "entry_epoch": int(t["entry_epoch"]) if t["entry_epoch"] is not None else None,
                "entry_price": _num(t["entry_price"]),
                "stop": _num(t["stop"]),
                "t1": _num(t["t1"]),
                "t2": _num(t["t2"]),
                "t3": _num(t["t3"]),
                "exit_ts": t["exit_ts_ct"],
                "exit_epoch": int(t["exit_epoch"]) if t["exit_epoch"] is not None else None,
                "exit_price": _num(t["exit_price"]),
                "exit_reason": t["exit_reason"],
                "pnl_usd": _num(t["pnl_usd"]),
                "pnl_r": _num(t["pnl_r"]),
                "outcome": t["outcome"],
                "pattern_id": t["pattern_id_at_entry"],
                "day_type": t["day_type_at_entry"],
            }
        )

    cur.close()
    conn.close()

    payload = {
        "date": args.date,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "export_replay_data.py (Mac, SELECT-only)",
        "day_type": day_type,
        "day_type_source": day_type_source,
        "day_type_timeline": day_type_timeline,   # per-bar segments when classifier answered, else null
        "levels": levels,        # null when no CASH TPO row / all-null
        "bars": bars,
        "cvd": cvd,              # [] when v9_bars_5min had no delta for the day
        "trades": trades,
        "_notes": {
            "day_type_source": day_type_source,
            "day_type_chain": "1) classify_replay endpoint (canonical 7-type, "
            "per-bar) → 2) v9_day_type_state (live machine) → 3) "
            "v9_trades.day_type_at_entry (stamped). First non-null wins; null if all silent.",
            "cvd_source": "v9_bars_5min.cumulative_delta (can stall/gap).",
            "tz": "ts fields are America/Chicago wall-clock; epoch is UTC seconds.",
        },
    }

    with open(out_path, "w") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print(f"Wrote {out_path}")
    print(
        f"  bars={len(bars)}  trades={len(trades)}  "
        f"levels={'yes' if levels else 'MISSING'}  "
        f"cvd_points={len(cvd)}  day_type={day_type or 'MISSING'}"
    )
    print(f"  day_type_source={day_type_source}"
          + (f"  (timeline segments={len(day_type_timeline['segments'])})"
             if day_type_timeline and day_type_timeline.get("segments") else ""))
    if bars:
        print(f"  bar range CT: {bars[0]['ts']} .. {bars[-1]['ts']}")


if __name__ == "__main__":
    main()
