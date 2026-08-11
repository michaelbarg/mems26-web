#!/usr/bin/env python3
"""SYSTEM-4 (Woodies CCI) FULL AUDIT — every trading day we have.

Question (Michael, 2026-08-11): which S4 configuration makes money on LIVE tomorrow?

STRICTLY READ-ONLY.
  reads : v9_bars_5min_woodies, v9_trades, v9_day_type_history  (local Postgres)
          ~/SierraChart_Data/v9_export/gateway_decisions.jsonl
  writes: stdout + optional --json-out only.
  never : changes a flag, restarts a service, writes to ~/SierraChart_Data or the DB.

Sections (all run by default; pick with --only)
  sessions   inventory of every session in v9_bars_5min_woodies + day-type + character
  decisions  S4 decision-log census: unique signals / pattern / gate / day
  trades     v9_trades S4 realised P&L (live / demo / shadow)
  counter    counterfactual: every BLOCKED S4 signal -> MFE/MAE + 4-contract sim,
             aggregated per gate and per day-type ("what did this gate cost / save")
  zlr        ZLR deep-dive: when is ZLR profitable (day-type / distance-from-extreme /
             CCI / time-of-day / LSMA slope) -> the separating rule
  chain      per-signal gate-chain walk for the requested dates
  config     evaluate candidate S4 configurations on the measured history

Timezone contract (IMPORTANT — a double-cast here silently shifts the RTH window by
11h and was the first bug this audit hit): `v9_bars_5min_woodies.ts` is timestamptz.
The ONLY correct ET rendering is a SINGLE `ts AT TIME ZONE 'America/New_York'`.
`ts AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York'` is WRONG.

Signal-bar contract: the gateway logs a decision a few seconds *into* a forming bar
(`entry` = that forming bar's current price, verified: most entries sit inside the
forming bar's range, not on a close). So signal_bar = floor_5min(decision_ts) and the
strict forward window starts at signal_bar + 5min (no intra-bar look-ahead/behind).
`--fwd-mode leg` reproduces scripts/leg_exemption_replay.py's looser convention
(window starts at the forming bar) for cross-report comparability.

Usage
  python3 scripts/s4_full_audit.py                       # everything
  python3 scripts/s4_full_audit.py --only sessions,zlr
  python3 scripts/s4_full_audit.py --only chain --chain-dates 2026-08-10,2026-08-11
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── .env must be loaded — same contract as the other replay harnesses ──
try:
    from scripts.flag_guard import parse_env
    for _k, _v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(_k, _v)
except Exception as _e:  # pragma: no cover
    print(f"[warn] could not parse .env: {_e}")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
os.environ.setdefault("BRIDGE_TOKEN", "x")

from zoneinfo import ZoneInfo  # noqa: E402

ET = ZoneInfo("America/New_York")
RTH_OPEN_MIN, RTH_END_MIN = 9 * 60 + 30, 16 * 60 + 15
FIRE_WINDOW_END_MIN = 16 * 60          # 15:00 CT = 16:00 ET — the live firing window
MES = 5.0                              # $/pt/contract
CONTRACTS = 4
COMMISSION_RT = 1.50                   # $/contract round-turn — reported separately
FWD_BARS = 12
FIXTURE_ENTRY = 7600.0                 # pytest fixture rows that leak into the log
DEFAULT_STOP_PTS = 8.0
DECISIONS_PATH = os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")

S4_PATTERNS = ("ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE",
               "CONFLUENCE_RI_ZLR")
ROTATION_PREFIXES = ("Variation", "Normal_Variation", "Normal", "Neutral", "Nontrend")


# ══════════════════════════════════════════════════════════════════ data loading
def q(sql: str, params: Optional[dict] = None) -> List[dict]:
    from backend.v9.db.read import read_all
    return read_all(sql, params or {}) or []


def load_sessions(min_bars: int = 20) -> List[dict]:
    """Every ET date with >= min_bars RTH 5-min bars, plus its character."""
    rows = q("""
        SELECT (ts AT TIME ZONE 'America/New_York')::date AS d,
               COUNT(*) AS n, MIN(low) AS lo, MAX(high) AS hi,
               SUM(CASE WHEN zlr_detected<>0 THEN 1 ELSE 0 END) AS dll_zlr,
               SUM(CASE WHEN hfe_detected<>0 THEN 1 ELSE 0 END) AS dll_hfe
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
          AND (ts AT TIME ZONE 'America/New_York')::time <  '16:15'
        GROUP BY 1 ORDER BY 1""")
    out = []
    for r in rows:
        if int(r["n"]) < min_bars:
            continue
        out.append({"date": str(r["d"]), "n": int(r["n"]),
                    "lo": float(r["lo"]), "hi": float(r["hi"]),
                    "range": round(float(r["hi"]) - float(r["lo"]), 2),
                    "dll_zlr": int(r["dll_zlr"]), "dll_hfe": int(r["dll_hfe"])})
    return out


def load_day_types() -> Dict[str, dict]:
    """The label the LIVE gates recorded for that session (v9_day_type_history)."""
    out = {}
    for r in q("SELECT date, day_type, confidence, opening_type, ib_width "
               "FROM v9_day_type_history ORDER BY date"):
        out[str(r["date"])] = {"day_type": r["day_type"],
                               "confidence": r.get("confidence"),
                               "opening_type": r.get("opening_type"),
                               "ib_width": r.get("ib_width")}
    return out


_BAR_CACHE: Dict[str, List[dict]] = {}


def load_bars(date: str) -> List[dict]:
    """All RTH bars for one ET date, oldest first. ts is the bar START (verified)."""
    if date in _BAR_CACHE:
        return _BAR_CACHE[date]
    rows = q("""
        SELECT ts, open, high, low, close, volume, cci_14, cci_6_tcci, lsma_value,
               swi_value, czi_value, ema_34, trend_state, zlr_detected, zlr_direction,
               hfe_detected, hfe_direction
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
          AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
          AND (ts AT TIME ZONE 'America/New_York')::time <  '16:15'
        ORDER BY ts""", {"d": date})
    bars = []
    for r in rows:
        ts = r["ts"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        et = ts.astimezone(ET)
        bars.append({
            "ts": ts.astimezone(timezone.utc), "et": et,
            "min": et.hour * 60 + et.minute,
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "volume": float(r["volume"] or 0),
            "cci_14": _f(r["cci_14"]), "tcci": _f(r["cci_6_tcci"]),
            "lsma": _f(r["lsma_value"]), "swi": _f(r["swi_value"]),
            "czi": _f(r["czi_value"]), "ema34": _f(r["ema_34"]),
            "trend_state": str(r["trend_state"] or "GRAY"),
            "dll_zlr": bool(r["zlr_detected"]), "dll_zlr_dir": str(r["zlr_direction"] or "NONE"),
        })
    _BAR_CACHE[date] = bars
    return bars


def _f(v) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def read_decisions() -> List[dict]:
    """Every gateway decision, fixture rows dropped, decorated with ET time + signal bar."""
    out = []
    p = Path(DECISIONS_PATH)
    if not p.exists():
        print(f"[warn] no decision log at {p}")
        return out
    for line in p.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        e = r.get("entry")
        if e is None:
            continue
        if float(e) == FIXTURE_ENTRY:
            r["_fixture"] = True
        dt = datetime.fromisoformat(r["ts"]).astimezone(ET)
        r["_et"] = dt
        r["_date"] = dt.date().isoformat()
        fl = dt.replace(second=0, microsecond=0)
        r["_bar"] = fl.replace(minute=(fl.minute // 5) * 5)   # the FORMING bar
        r["_entry"] = float(e)
        out.append(r)
    out.sort(key=lambda x: x["_et"])
    return out


def unique_s4_signals(decisions: List[dict]) -> List[dict]:
    """One signal per (signal-bar, pattern, direction) — the live gateway re-evaluates
    the same setup on every mid-bar push, so raw rows massively over-count."""
    seen: Dict[Tuple, dict] = {}
    for r in decisions:
        if r.get("system") != 4 or r.get("_fixture"):
            continue
        key = (r["_bar"], r.get("pattern"), str(r.get("direction") or "").upper())
        if key not in seen:
            seen[key] = r
    return sorted(seen.values(), key=lambda x: x["_et"])


# ══════════════════════════════════════════════════════════ execution simulation
def simulate(entry: float, direction: str, fwd: List[dict], stop_pts: float,
             be_after_idx: int = 1) -> dict:
    """Michael's execution model.

    4 contracts: C1 -> T0 = +3.0 pt, C2 -> T1 = 1R, C3 -> T2 = 2R, C4 -> T3 = 4R.
    R = stop_pts. Break-even stop after T1 (1R) fills.
    Conservative intrabar ordering: the STOP is checked BEFORE the targets.
    Contracts still open after the 12-bar horizon exit at the last bar's close.
    """
    sign = 1.0 if direction == "LONG" else -1.0
    tgt_pts = [3.0, stop_pts, 2.0 * stop_pts, 4.0 * stop_pts]
    stop = entry - sign * stop_pts
    targets = [entry + sign * t for t in tgt_pts]
    open_c = [True] * CONTRACTS
    pnl_pts = 0.0
    legs: List[Tuple[str, float]] = []
    be_done = False
    mfe = mae = 0.0
    for b in fwd:
        hi, lo = b["high"], b["low"]
        mfe = max(mfe, (hi - entry) if direction == "LONG" else (entry - lo))
        mae = max(mae, (entry - lo) if direction == "LONG" else (hi - entry))
        hit_stop = (lo <= stop) if direction == "LONG" else (hi >= stop)
        if hit_stop:
            for i in range(CONTRACTS):
                if open_c[i]:
                    open_c[i] = False
                    pnl_pts += (stop - entry) * sign
                    legs.append(("BE" if be_done else "STOP", round((stop - entry) * sign, 2)))
            break
        for i in range(CONTRACTS):
            if not open_c[i]:
                continue
            t = targets[i]
            hit = (hi >= t) if direction == "LONG" else (lo <= t)
            if hit:
                open_c[i] = False
                pnl_pts += (t - entry) * sign
                legs.append((f"T{i}", round((t - entry) * sign, 2)))
                if i == be_after_idx and not be_done:
                    stop = entry
                    be_done = True
    if any(open_c):
        last = fwd[-1]["close"] if fwd else entry
        for i in range(CONTRACTS):
            if open_c[i]:
                pnl_pts += (last - entry) * sign
                legs.append(("TIME", round((last - entry) * sign, 2)))
    return {"pnl_pts": round(pnl_pts, 2), "pnl_usd": round(pnl_pts * MES, 2),
            "mfe": round(mfe, 2), "mae": round(mae, 2), "legs": legs,
            "be_hit": be_done, "bars": len(fwd),
            "net_usd": round(pnl_pts * MES - CONTRACTS * COMMISSION_RT, 2)}


def agg(sigs: List[dict], key: str = "sim") -> dict:
    if not sigs:
        return {"n": 0, "gross": 0.0, "net": 0.0, "wins": 0, "wr": 0.0, "avg": 0.0}
    gross = sum(s[key]["pnl_usd"] for s in sigs)
    wins = sum(1 for s in sigs if s[key]["pnl_usd"] > 0)
    return {"n": len(sigs), "gross": round(gross, 2),
            "net": round(gross - len(sigs) * CONTRACTS * COMMISSION_RT, 2),
            "wins": wins, "wr": round(100.0 * wins / len(sigs), 1),
            "avg": round(gross / len(sigs), 2)}


def sequential(sigs: List[dict], key: str = "sim") -> dict:
    """One trade at a time per session — the number a real single-slot account earns."""
    busy: Dict[str, Any] = {}
    taken = []
    for s in sorted(sigs, key=lambda x: x["bar_ts"]):
        d = s["date"]
        if busy.get(d) and s["bar_ts"] <= busy[d]:
            continue
        taken.append(s)
        busy[d] = s["fwd_end"]
    a = agg(taken, key)
    a["taken"] = len(taken)
    a["pool"] = len(sigs)
    return a


# ══════════════════════════════════════════════════════════ signal enrichment
def build_signal(r: dict, bars: List[dict], day_type: Optional[str],
                 stop_pts: float, fwd_mode: str, max_dev: float = 2.0,
                 drops: Optional[Counter] = None) -> Optional[dict]:
    """Attach causal context + forward simulation to one decision-log signal.

    `max_dev` rejects STALE decisions — the gateway re-broadcasts week-old setups after
    a restart (the leg-exemption audit found `signal age 566994s` = 6.5 days). Such a
    row carries a price from another session; simulating it produces nonsense (an MFE
    of 1890 pt was the tell). A live signal's `entry` is the forming bar's current
    price, so it must sit inside that bar's range (plus a small tick tolerance).
    """
    def drop(why):
        if drops is not None:
            drops[why] += 1
        return None

    date = r["_date"]
    if not bars:
        return drop("no RTH bars for that date (weekend/holiday/feed gap)")
    bar_ts = r["_bar"]
    idx = None
    for i, b in enumerate(bars):
        if b["et"] == bar_ts:
            idx = i
            break
    if idx is None:
        return drop("signal bar outside RTH 09:30-16:15")
    closed = bars[:idx]                       # strictly-closed history at signal time
    if len(closed) < 3:
        return drop("<3 closed bars of session history")
    fwd_start = idx if fwd_mode == "leg" else idx + 1
    fwd = bars[fwd_start:fwd_start + FWD_BARS]
    if len(fwd) < 2:
        return drop("<2 forward bars left in the session")
    entry = r["_entry"]
    dirn = str(r.get("direction") or "").upper()
    if dirn not in ("LONG", "SHORT"):
        return drop("no direction")
    sb = bars[idx]
    if not (sb["low"] - max_dev <= entry <= sb["high"] + max_dev):
        return drop("STALE: entry outside the signal bar's range (re-broadcast)")

    sess_hi = max(b["high"] for b in closed)
    sess_lo = min(b["low"] for b in closed)
    sess_open = bars[0]["open"]
    last = closed[-1]
    # distance from the extreme the trade is running INTO (the chase-guard geometry)
    dist_extreme = (sess_hi - entry) if dirn == "LONG" else (entry - sess_lo)
    # distance from the extreme the trade is running AWAY from
    dist_behind = (entry - sess_lo) if dirn == "LONG" else (sess_hi - entry)
    lsma_slope = None
    if len(closed) >= 4 and closed[-1]["lsma"] is not None and closed[-4]["lsma"] is not None:
        lsma_slope = (closed[-1]["lsma"] - closed[-4]["lsma"]) / 3.0
    sim = simulate(entry, dirn, fwd, stop_pts)
    return {
        "date": date, "ts": r["ts"], "et": r["_et"], "bar_ts": bar_ts,
        "min": bar_ts.hour * 60 + bar_ts.minute,
        "hhmm": bar_ts.strftime("%H:%M"),
        "pattern": r.get("pattern"), "direction": dirn, "entry": entry,
        "gate": r.get("blocked_by"), "outcome": r.get("outcome"),
        "reason": (r.get("reason") or "")[:140],
        "day_type": day_type, "regime": _regime(day_type),
        "sess_hi": sess_hi, "sess_lo": sess_lo, "sess_open": sess_open,
        "sess_range": round(sess_hi - sess_lo, 2),
        "disp": round(last["close"] - sess_open, 2),
        "dist_extreme": round(dist_extreme, 2), "dist_behind": round(dist_behind, 2),
        "cci": last["cci_14"], "tcci": last["tcci"], "swi": last["swi"],
        "trend_state": last["trend_state"],
        "lsma_slope": None if lsma_slope is None else round(lsma_slope, 4),
        "with_lsma": None if lsma_slope is None else
                     ((lsma_slope > 0) == (dirn == "LONG")),
        "bars_into_session": idx,
        "sim": sim, "fwd_end": fwd[-1]["et"],
    }


def _regime(day_type: Optional[str]) -> str:
    if not day_type:
        return "UNKNOWN"
    if day_type.startswith("Trend"):
        return "TREND"
    if day_type.startswith(("Neutral", "Nontrend", "Nonconviction")):
        return "NEUTRAL"
    return "ROTATION"


# ══════════════════════════════════════════════════════════════════ sections
def sec_sessions(sessions, day_types) -> None:
    print("\n" + "=" * 100)
    print("1. SESSION INVENTORY — every session in v9_bars_5min_woodies (RTH 09:30–16:15 ET)")
    print("=" * 100)
    print(f"{'date':<12}{'bars':>5}{'range':>8}{'open':>10}{'close':>10}{'disp':>8}  "
          f"{'day_type (live label)':<20}{'conf':>6}{'regime':>10}{'DLL_ZLR':>9}")
    n_full = 0
    for s in sessions:
        bars = load_bars(s["date"])
        if not bars:
            continue
        disp = bars[-1]["close"] - bars[0]["open"]
        dt = day_types.get(s["date"], {})
        lbl = dt.get("day_type") or "—"
        conf = dt.get("confidence")
        if s["n"] >= 70:
            n_full += 1
        print(f"{s['date']:<12}{s['n']:>5}{s['range']:>8.2f}{bars[0]['open']:>10.2f}"
              f"{bars[-1]['close']:>10.2f}{disp:>+8.2f}  {lbl:<20}"
              f"{('' if conf is None else f'{float(conf):.0f}'):>6}"
              f"{_regime(lbl):>10}{s['dll_zlr']:>9}")
    print(f"\nsessions with >=20 RTH bars: {len(sessions)}   (>=70 bars = full session: {n_full})")
    print(f"span: {sessions[0]['date']} .. {sessions[-1]['date']}")
    reg = Counter(_regime((day_types.get(s['date']) or {}).get('day_type')) for s in sessions)
    print("regime mix:", dict(reg))


def sec_decisions(usig, day_types) -> None:
    print("\n" + "=" * 100)
    print("2. DECISION-LOG CENSUS — the only ground truth for S4 signals + gates")
    print("=" * 100)
    days = sorted({s["_date"] for s in usig})
    print(f"decision log covers {len(days)} dates: {days[0]} .. {days[-1]}  "
          f"(unique S4 signals = {len(usig)})")
    print("\n--- unique signals per day x pattern ---")
    pats = [p for p, _ in Counter(s.get("pattern") for s in usig).most_common()]
    hdr = f"{'date':<12}{'day_type':<18}" + "".join(f"{p[:9]:>10}" for p in pats) + f"{'TOT':>7}"
    print(hdr)
    for d in days:
        row = [s for s in usig if s["_date"] == d]
        c = Counter(s.get("pattern") for s in row)
        lbl = (day_types.get(d) or {}).get("day_type") or "—"
        print(f"{d:<12}{lbl:<18}" + "".join(f"{c.get(p, 0) or '':>10}" for p in pats)
              + f"{len(row):>7}")
    print(f"{'TOTAL':<12}{'':<18}" + "".join(
        f"{sum(1 for s in usig if s.get('pattern') == p):>10}" for p in pats) + f"{len(usig):>7}")

    print("\n--- per pattern: gate histogram (first-match-wins) ---")
    for p in pats:
        row = [s for s in usig if s.get("pattern") == p]
        gates = Counter(s.get("blocked_by") or "PASSED" for s in row)
        out = Counter(s.get("outcome") for s in row)
        print(f"\n  {p}  n={len(row)}   outcomes={dict(out)}")
        for g, c in gates.most_common():
            print(f"      {g:<28} {c:>4}  ({100.0*c/len(row):.0f}%)")


def sec_trades(day_types) -> None:
    print("\n" + "=" * 100)
    print("3. v9_trades — S4 REALISED P&L (what actually happened to real orders)")
    print("=" * 100)
    rows = q("""SELECT id, mode, direction, entry_ts, entry_price, stop, exit_price,
                exit_reason, pnl_usd, pnl_r, outcome, day_type_at_entry,
                pattern_id_at_entry AS pat, state
                FROM v9_trades WHERE firing_system = 4 ORDER BY entry_ts NULLS LAST""")
    real = [r for r in rows if r["pat"] != "SIM_TEST"]
    for mode in ("live", "demo", "shadow"):
        sel = [r for r in real if r["mode"] == mode]
        if not sel:
            continue
        pnl = sum(float(r["pnl_usd"] or 0) for r in sel)
        wins = sum(1 for r in sel if float(r["pnl_usd"] or 0) > 0)
        print(f"\n  mode={mode:<7} n={len(sel):<4} net=${pnl:>10.2f}  "
              f"wins={wins} ({100.0*wins/len(sel):.0f}%)")
        bypat = defaultdict(lambda: [0, 0.0, 0])
        for r in sel:
            k = r["pat"] or "?"
            bypat[k][0] += 1
            bypat[k][1] += float(r["pnl_usd"] or 0)
            bypat[k][2] += 1 if float(r["pnl_usd"] or 0) > 0 else 0
        for k, v in sorted(bypat.items(), key=lambda kv: kv[1][1]):
            print(f"      {k:<20} n={v[0]:<4} net=${v[1]:>10.2f}  "
                  f"wins={v[2]} ({100.0*v[2]/max(1,v[0]):.0f}%)")

    print("\n  --- every LIVE S4 trade (chronological) ---")
    print(f"  {'entry (Israel tz)':<20}{'dir':<6}{'pattern':<20}{'entry':>9}{'stop':>9}"
          f"{'exit_reason':<20}{'pnl$':>9}{'R':>7}  day_type")
    live = [r for r in real if r["mode"] == "live" and r["entry_ts"]]
    for r in live:
        print(f"  {r['entry_ts'].strftime('%Y-%m-%d %H:%M'):<20}{r['direction'] or '':<6}"
              f"{(r['pat'] or ''):<20}{_num(r['entry_price']):>9}{_num(r['stop']):>9}"
              f"{(r['exit_reason'] or '')[:19]:<20}{_num(r['pnl_usd']):>9}{_num(r['pnl_r']):>7}"
              f"  {r['day_type_at_entry']}")
    bydate = defaultdict(float)
    for r in live:
        bydate[r["entry_ts"].date().isoformat()] += float(r["pnl_usd"] or 0)
    print("\n  LIVE S4 per day: " + "  ".join(f"{d}=${v:+.2f}" for d, v in sorted(bydate.items())))
    print(f"  LIVE S4 TOTAL: ${sum(bydate.values()):+.2f} over {len(live)} trades / "
          f"{len(bydate)} sessions")


def _num(v) -> str:
    return "—" if v is None else f"{float(v):.2f}"


def sec_counter(sigs) -> None:
    print("\n" + "=" * 100)
    print("4. COUNTERFACTUAL — what every BLOCKED S4 signal would have done")
    print("=" * 100)
    print("   model: 4 contracts, C1=+3pt C2=1R C3=2R C4=4R, BE after 1R, stop-before-target,")
    print(f"          12-bar horizon, MES $5/pt, commission ${COMMISSION_RT}/contract RT.")
    print("   'per-signal' = every blocked signal taken (overlapping, an upper bound).")
    print("   'sequential' = one trade at a time per session — the realistic account number.")
    blocked = [s for s in sigs if s["gate"]]
    passed = [s for s in sigs if not s["gate"]]
    print(f"\n   blocked signals with a usable forward window: {len(blocked)}   "
          f"(passed: {len(passed)})")

    print(f"\n   {'gate':<28}{'n':>5}{'per-signal $':>14}{'wr%':>7}{'seq n':>7}"
          f"{'seq $':>11}{'seq net $':>11}{'MFEmed':>8}{'MAEmed':>8}")
    rows = []
    for g, _ in Counter(s["gate"] for s in blocked).most_common():
        gs = [s for s in blocked if s["gate"] == g]
        a, sq = agg(gs), sequential(gs)
        rows.append((g, len(gs), a["gross"], a["wr"], sq["taken"], sq["gross"], sq["net"]))
        print(f"   {g:<28}{len(gs):>5}{a['gross']:>14.2f}{a['wr']:>7.1f}{sq['taken']:>7}"
              f"{sq['gross']:>11.2f}{sq['net']:>11.2f}"
              f"{st.median([s['sim']['mfe'] for s in gs]):>8.2f}"
              f"{st.median([s['sim']['mae'] for s in gs]):>8.2f}")
    tot_a, tot_s = agg(blocked), sequential(blocked)
    print(f"   {'ALL BLOCKED':<28}{len(blocked):>5}{tot_a['gross']:>14.2f}{tot_a['wr']:>7.1f}"
          f"{tot_s['taken']:>7}{tot_s['gross']:>11.2f}{tot_s['net']:>11.2f}")
    print("\n   reading: positive per-signal $ = the gate COST money (it blocked winners);")
    print("            negative = the gate SAVED money.")

    print("\n   --- per gate x regime (sequential $, n) ---")
    regs = ["TREND", "ROTATION", "NEUTRAL", "UNKNOWN"]
    print(f"   {'gate':<28}" + "".join(f"{r:>22}" for r in regs))
    for g, _ in Counter(s["gate"] for s in blocked).most_common():
        cells = []
        for rg in regs:
            gs = [s for s in blocked if s["gate"] == g and s["regime"] == rg]
            if not gs:
                cells.append(f"{'—':>22}")
                continue
            sq = sequential(gs)
            cells.append(f"{f'${sq[chr(103)+chr(114)+chr(111)+chr(115)+chr(115)]:+.0f} (n={sq[chr(116)+chr(97)+chr(107)+chr(101)+chr(110)]}/{len(gs)})':>22}")
        print(f"   {g:<28}" + "".join(cells))

    print("\n   --- per pattern x blocked/passed (sequential) ---")
    print(f"   {'pattern':<22}{'blocked n':>10}{'blocked seq $':>15}"
          f"{'passed n':>10}{'passed seq $':>15}")
    for p, _ in Counter(s["pattern"] for s in sigs).most_common():
        b = [s for s in blocked if s["pattern"] == p]
        pa = [s for s in passed if s["pattern"] == p]
        sb, sp = sequential(b), sequential(pa)
        print(f"   {str(p):<22}{len(b):>10}{sb['gross']:>15.2f}{len(pa):>10}{sp['gross']:>15.2f}")


def sec_zlr(sigs) -> None:
    print("\n" + "=" * 100)
    print("5. ZLR DEEP-DIVE — when is ZLR profitable?")
    print("=" * 100)
    z = [s for s in sigs if s["pattern"] == "ZLR"]
    if not z:
        print("   no ZLR signals")
        return
    a, sq = agg(z), sequential(z)
    print(f"   ALL ZLR signals (blocked + passed): n={len(z)}  per-signal ${a['gross']:.2f} "
          f"(wr {a['wr']}%)  sequential ${sq['gross']:.2f} net ${sq['net']:.2f} (n={sq['taken']})")
    print(f"   sessions: {len(set(s['date'] for s in z))}")

    def slice_report(title, keyfn, order=None):
        print(f"\n   --- ZLR by {title} ---")
        groups = defaultdict(list)
        for s in z:
            groups[keyfn(s)].append(s)
        keys = order or sorted(groups, key=lambda k: (k is None, str(k)))
        print(f"   {'bucket':<26}{'n':>5}{'per-sig $':>12}{'avg $':>9}{'wr%':>7}"
              f"{'seq n':>7}{'seq $':>11}{'MFEmed':>8}{'MAEmed':>8}")
        for k in keys:
            g = groups.get(k) or []
            if not g:
                continue
            aa, ss = agg(g), sequential(g)
            print(f"   {str(k):<26}{len(g):>5}{aa['gross']:>12.2f}{aa['avg']:>9.2f}"
                  f"{aa['wr']:>7.1f}{ss['taken']:>7}{ss['gross']:>11.2f}"
                  f"{st.median([x['sim']['mfe'] for x in g]):>8.2f}"
                  f"{st.median([x['sim']['mae'] for x in g]):>8.2f}")

    slice_report("DAY-TYPE (live label)", lambda s: s["day_type"] or "—")
    slice_report("REGIME", lambda s: s["regime"],
                 order=["TREND", "ROTATION", "NEUTRAL", "UNKNOWN"])
    slice_report("DIRECTION", lambda s: s["direction"])

    def dbucket(v):
        if v is None:
            return "?"
        if v < 0:      return "a. <0 (beyond extreme)"
        if v < 3:      return "b. 0–3 pt"
        if v < 6:      return "c. 3–6 pt"
        if v < 10:     return "d. 6–10 pt"
        if v < 20:     return "e. 10–20 pt"
        return "f. >=20 pt"
    slice_report("DISTANCE from the session extreme it runs INTO",
                 lambda s: dbucket(s["dist_extreme"]))

    def cbucket(s):
        c = s["cci"]
        if c is None:
            return "?"
        if s["direction"] == "LONG":
            if c < -100: return "a. CCI < -100"
            if c < 0:    return "b. CCI -100..0"
            if c < 100:  return "c. CCI 0..100"
            if c < 200:  return "d. CCI 100..200"
            return "e. CCI >= 200"
        if c > 100:  return "a. CCI > +100"
        if c > 0:    return "b. CCI 0..+100"
        if c > -100: return "c. CCI -100..0"
        if c > -200: return "d. CCI -200..-100"
        return "e. CCI <= -200"
    slice_report("CCI-14 at the signal bar (signed to the trade side)", cbucket)

    def tbucket(s):
        m = s["min"]
        if m < 10 * 60:        return "a. 09:30–10:00"
        if m < 11 * 60:        return "b. 10:00–11:00"
        if m < 12 * 60:        return "c. 11:00–12:00"
        if m < 13 * 60:        return "d. 12:00–13:00"
        if m < 14 * 60:        return "e. 13:00–14:00"
        if m < 15 * 60:        return "f. 14:00–15:00"
        return "g. 15:00–16:15"
    slice_report("TIME OF DAY (ET, signal bar)", tbucket)

    def lbucket(s):
        v = s["lsma_slope"]
        if v is None:
            return "?"
        d = v if s["direction"] == "LONG" else -v
        if d < -0.25: return "a. LSMA against, steep"
        if d < 0:     return "b. LSMA against, shallow"
        if d < 0.25:  return "c. LSMA with, flat (<0.25)"
        if d < 0.75:  return "d. LSMA with, 0.25–0.75"
        return "e. LSMA with, >=0.75"
    slice_report("LSMA slope vs trade direction (pt/bar over 3 bars)", lbucket)

    slice_report("SESSION DISPLACEMENT agrees with direction",
                 lambda s: "with-displacement (>=10pt)"
                 if abs(s["disp"]) >= 10 and ((s["disp"] > 0) == (s["direction"] == "LONG"))
                 else "no")

    # ── the separating rule search ────────────────────────────────────────────
    print("\n   --- CANDIDATE SEPARATING RULES (each evaluated on all ZLR signals) ---")
    print(f"   {'rule':<62}{'n':>5}{'seq n':>7}{'seq $':>11}{'seq net$':>11}{'wr%':>7}")

    def rule(name, fn):
        g = [s for s in z if fn(s)]
        if not g:
            print(f"   {name:<62}{0:>5}{'—':>7}{'—':>11}{'—':>11}{'—':>7}")
            return None
        ss = sequential(g)
        print(f"   {name:<62}{len(g):>5}{ss['taken']:>7}{ss['gross']:>11.2f}"
              f"{ss['net']:>11.2f}{ss['wr']:>7.1f}")
        return ss

    rule("R0  every ZLR (baseline)", lambda s: True)
    rule("R1  regime != NEUTRAL", lambda s: s["regime"] != "NEUTRAL")
    rule("R2  dist_extreme >= 6pt", lambda s: (s["dist_extreme"] or 0) >= 6)
    rule("R3  dist_extreme >= 10pt", lambda s: (s["dist_extreme"] or 0) >= 10)
    rule("R4  LSMA with direction (slope*dir > 0)", lambda s: bool(s["with_lsma"]))
    rule("R5  LSMA with direction, |slope| >= 0.25",
         lambda s: s["lsma_slope"] is not None and
         (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    rule("R6  before 12:00 ET", lambda s: s["min"] < 12 * 60)
    rule("R7  after 12:00 ET", lambda s: s["min"] >= 12 * 60)
    rule("R8  session displacement agrees, >=10pt",
         lambda s: abs(s["disp"]) >= 10 and ((s["disp"] > 0) == (s["direction"] == "LONG")))
    rule("R9  R2 + R5 (dist>=6 AND LSMA with, >=0.25)",
         lambda s: (s["dist_extreme"] or 0) >= 6 and s["lsma_slope"] is not None and
         (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    rule("R10 R1 + R2 + R5",
         lambda s: s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6 and
         s["lsma_slope"] is not None and
         (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    rule("R11 R10 + before 15:00 ET",
         lambda s: s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6 and
         s["min"] < 15 * 60 and s["lsma_slope"] is not None and
         (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    rule("R12 R8 + dist_extreme >= 6",
         lambda s: (s["dist_extreme"] or 0) >= 6 and abs(s["disp"]) >= 10 and
         ((s["disp"] > 0) == (s["direction"] == "LONG")))
    rule("R13 SHORT only", lambda s: s["direction"] == "SHORT")
    rule("R14 LONG only", lambda s: s["direction"] == "LONG")
    rule("R15 R2 + R8 + regime!=NEUTRAL",
         lambda s: s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6 and
         abs(s["disp"]) >= 10 and ((s["disp"] > 0) == (s["direction"] == "LONG")))

    print("\n   --- per-session P&L of the ZLR baseline vs the best rule ---")
    print(f"   {'date':<12}{'day_type':<18}{'all ZLR seq$':>14}{'n':>4}"
          f"{'R10 seq$':>11}{'n':>4}")
    for d in sorted({s["date"] for s in z}):
        ds = [s for s in z if s["date"] == d]
        r10 = [s for s in ds if s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6 and
               s["lsma_slope"] is not None and
               (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25]
        sa, sb = sequential(ds), sequential(r10)
        print(f"   {d:<12}{(ds[0]['day_type'] or '—'):<18}{sa['gross']:>14.2f}{sa['taken']:>4}"
              f"{sb['gross']:>11.2f}{sb['taken']:>4}")


def sec_chain(decisions, dates: List[str]) -> None:
    print("\n" + "=" * 100)
    print("6. GATE-CHAIN WALK — every S4 signal, in order, for " + ", ".join(dates))
    print("=" * 100)
    for d in dates:
        rows = [r for r in decisions if r.get("system") == 4 and r["_date"] == d
                and not r.get("_fixture")]
        if not rows:
            print(f"\n   {d}: no S4 decisions in the log")
            continue
        bars = load_bars(d)
        sess = {}
        print(f"\n   --- {d}  ({len(rows)} raw decisions) ---")
        print(f"   {'dec ET':<10}{'bar':<7}{'pattern':<20}{'dir':<6}{'entry':>9}"
              f"{'blocked_by':<24}{'outcome':<12} reason")
        seen = set()
        for r in sorted(rows, key=lambda x: x["_et"]):
            key = (r["_bar"], r.get("pattern"), r.get("direction"))
            dup = "" if key not in seen else "  (repeat push)"
            seen.add(key)
            print(f"   {r['_et'].strftime('%H:%M:%S'):<10}{r['_bar'].strftime('%H:%M'):<7}"
                  f"{str(r.get('pattern')):<20}{str(r.get('direction')):<6}{r['_entry']:>9.2f}"
                  f"{str(r.get('blocked_by')):<24}{str(r.get('outcome')):<12} "
                  f"{(r.get('reason') or '')[:80]}{dup}")
        uq = len(seen)
        gates = Counter(r.get("blocked_by") for r in rows
                        if (r["_bar"], r.get("pattern"), r.get("direction")) in seen)
        print(f"   => {uq} unique signals; first-blocking-gate histogram over raw rows: "
              f"{dict(Counter(r.get('blocked_by') for r in rows))}")


def sec_config(sigs) -> None:
    print("\n" + "=" * 100)
    print("7. CANDIDATE S4 CONFIGURATIONS — measured on the same history")
    print("=" * 100)
    print("   Every configuration is scored on the SAME signal population (all unique S4")
    print("   signals in the decision log, blocked or not) with the same execution model.")
    print("   'as-shipped' = only the signals the live gateway let through (outcome != blocked).")

    def cfg(name, fn):
        g = [s for s in sigs if fn(s)]
        if not g:
            print(f"   {name:<58}{0:>5}{'—':>8}{'—':>12}{'—':>12}{'—':>8}{'—':>10}")
            return
        ss = sequential(g)
        days = len({s["date"] for s in g})
        per_day = ss["net"] / days if days else 0.0
        print(f"   {name:<58}{len(g):>5}{ss['taken']:>8}{ss['gross']:>12.2f}"
              f"{ss['net']:>12.2f}{ss['wr']:>8.1f}{per_day:>10.2f}")

    print(f"\n   {'configuration':<58}{'pool':>5}{'taken':>8}{'gross $':>12}"
          f"{'net $':>12}{'wr%':>8}{'$/day':>10}")
    cfg("C0  as-shipped (only what the live gateway passed)",
        lambda s: not s["gate"])
    cfg("C1  all S4 signals, no gates at all", lambda s: True)
    cfg("C2  ZLR only, no gates", lambda s: s["pattern"] == "ZLR")
    cfg("C3  ZLR only + regime != NEUTRAL",
        lambda s: s["pattern"] == "ZLR" and s["regime"] != "NEUTRAL")
    cfg("C4  ZLR only + dist_extreme >= 6",
        lambda s: s["pattern"] == "ZLR" and (s["dist_extreme"] or 0) >= 6)
    cfg("C5  ZLR + regime!=NEUTRAL + dist>=6",
        lambda s: s["pattern"] == "ZLR" and s["regime"] != "NEUTRAL"
        and (s["dist_extreme"] or 0) >= 6)
    cfg("C6  C5 + LSMA with direction >= 0.25",
        lambda s: s["pattern"] == "ZLR" and s["regime"] != "NEUTRAL"
        and (s["dist_extreme"] or 0) >= 6 and s["lsma_slope"] is not None
        and (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    cfg("C7  C6 but ALL patterns (not just ZLR)",
        lambda s: s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6
        and s["lsma_slope"] is not None
        and (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    cfg("C8  CONT family only (ZLR/TLB/TT/GB100) + C6 filters",
        lambda s: s["pattern"] in ("ZLR", "TLB", "TT", "GB100", "TLB_LONG")
        and s["regime"] != "NEUTRAL" and (s["dist_extreme"] or 0) >= 6
        and s["lsma_slope"] is not None
        and (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    cfg("C9  REV family only (VEGAS/GHOST/FAMIR/HTLB) any filter",
        lambda s: s["pattern"] in ("VEGAS", "GHOST", "FAMIR", "HTLB"))
    cfg("C10 GB100 only", lambda s: s["pattern"] == "GB100")
    cfg("C11 C6 + before 15:00 ET",
        lambda s: s["pattern"] == "ZLR" and s["regime"] != "NEUTRAL"
        and (s["dist_extreme"] or 0) >= 6 and s["min"] < 15 * 60
        and s["lsma_slope"] is not None
        and (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25)
    cfg("C12 NOTHING (S4 off)", lambda s: False)


def replay_signals(sessions, day_types, stop_pts: float) -> List[dict]:
    """Re-detect S4 signals on EVERY session in v9_bars_5min_woodies.

    Two sources, exactly as the live `WoodiesSystem.process_bar` uses them
    (`backend/v9/systems/woodies/woodies_system.py:452-520`):
      * the Python detectors (`detect_all_patterns`, live .env flags — so
        ZLR_SPEC_V2=1, HFE stripped by HFE_DISABLED=1), and
      * the DLL's own `zlr_detected`/`zlr_direction` flag, which the live system
        trusts when Python missed it ("DLL is source of truth").

    HONEST LIMIT (do not read this table as ground truth): `v9_bars_5min_woodies`
    keeps only the LAST push of each bar, while the live gateway fires on ANY
    mid-bar push (verified: most logged entries sit inside the forming bar's range,
    not on a close). A DLL ZLR that was raised and cleared inside a bar is therefore
    invisible here — on 2026-08-10 the DB shows 0 DLL-ZLR bars while the live log
    holds 17 unique ZLR signals. So this replay UNDER-counts ZLR. It is used for
    breadth (48 sessions incl. a pre-log out-of-sample window), not for census.
    """
    from backend.v9.systems.woodies.schemas import WoodiesBar
    from backend.v9.systems.woodies.pattern_engine import detect_all_patterns
    hfe_off = os.environ.get("HFE_DISABLED", "0").lower() in ("1", "true", "yes")
    out = []
    for s in sessions:
        date = s["date"]
        bars = load_bars(date)
        if len(bars) < 20:
            continue
        dt = (day_types.get(date) or {}).get("day_type")
        wbs = [WoodiesBar(ts=b["ts"].timestamp(), open=b["open"], high=b["high"],
                          low=b["low"], close=b["close"], volume=b["volume"],
                          cci_14=b["cci_14"] or 0, cci_6_tcci=b["tcci"] or 0,
                          ema_34=b["ema34"] or 0, lsma_value=b["lsma"] or 0,
                          swi_value=b["swi"] or 0, czi_value=b["czi"] or 0,
                          trend_state=b["trend_state"],
                          zlr_detected=b["dll_zlr"], zlr_direction=b["dll_zlr_dir"])
               for b in bars]
        for i, b in enumerate(bars):
            if i < 15 or i + 2 >= len(bars):
                continue
            if b["min"] >= FIRE_WINDOW_END_MIN:      # live firing window ends 16:00 ET
                continue
            found: List[Tuple[str, str]] = []
            for p in detect_all_patterns(wbs[max(0, i - 59):i + 1], None):
                if hfe_off and p.pattern_id == "HFE":
                    continue
                found.append((p.pattern_id, p.direction))
            if b["dll_zlr"] and b["dll_zlr_dir"] in ("UP", "DOWN") and \
               not any(f[0] == "ZLR" for f in found):
                found.append(("ZLR", "LONG" if b["dll_zlr_dir"] == "UP" else "SHORT"))
            if not found:
                continue
            closed, fwd = bars[:i + 1], bars[i + 1:i + 1 + FWD_BARS]
            if len(fwd) < 2:
                continue
            sess_hi = max(x["high"] for x in closed)
            sess_lo = min(x["low"] for x in closed)
            lsma_slope = None
            if i >= 3 and closed[-1]["lsma"] is not None and closed[-4]["lsma"] is not None:
                lsma_slope = (closed[-1]["lsma"] - closed[-4]["lsma"]) / 3.0
            for pat, dirn in found:
                if dirn not in ("LONG", "SHORT"):
                    continue
                entry = b["close"]
                out.append({
                    "date": date, "bar_ts": b["et"], "min": b["min"],
                    "hhmm": b["et"].strftime("%H:%M"), "pattern": pat, "direction": dirn,
                    "entry": entry, "gate": None, "outcome": "replay",
                    "day_type": dt, "regime": _regime(dt),
                    "sess_hi": sess_hi, "sess_lo": sess_lo,
                    "sess_range": round(sess_hi - sess_lo, 2),
                    "disp": round(b["close"] - bars[0]["open"], 2),
                    "dist_extreme": round((sess_hi - entry) if dirn == "LONG"
                                          else (entry - sess_lo), 2),
                    "cci": b["cci_14"], "tcci": b["tcci"],
                    "lsma_slope": None if lsma_slope is None else round(lsma_slope, 4),
                    "with_lsma": None if lsma_slope is None else
                                 ((lsma_slope > 0) == (dirn == "LONG")),
                    "sim": simulate(entry, dirn, fwd, stop_pts),
                    "fwd_end": fwd[-1]["et"], "_fwd": fwd,
                })
    return out


def sec_replay(rsigs, log_dates) -> None:
    print("\n" + "=" * 100)
    print("9. FULL-HISTORY REPLAY — S4 signals re-detected on EVERY session (48), incl. the")
    print("   pre-decision-log window. See replay_signals() for the honest under-count caveat.")
    print("=" * 100)
    if not rsigs:
        print("   no replay signals")
        return
    days = sorted({s["date"] for s in rsigs})
    oos = [s for s in rsigs if s["date"] < min(log_dates)]
    ins = [s for s in rsigs if s["date"] >= min(log_dates)]
    print(f"   replay signals: {len(rsigs)} over {len(days)} sessions "
          f"({days[0]} .. {days[-1]})")
    print(f"   pre-log window (true out-of-sample vs the decision log): "
          f"{len(oos)} signals / {len({s['date'] for s in oos})} sessions")

    print(f"\n   --- per pattern (sequential, one trade at a time) ---")
    print(f"   {'pattern':<20}{'n':>6}{'per-sig $':>12}{'wr%':>7}{'seq n':>7}{'seq $':>11}{'net $':>11}")
    for p, _ in Counter(s["pattern"] for s in rsigs).most_common():
        g = [s for s in rsigs if s["pattern"] == p]
        a, ss = agg(g), sequential(g)
        print(f"   {p:<20}{len(g):>6}{a['gross']:>12.2f}{a['wr']:>7.1f}"
              f"{ss['taken']:>7}{ss['gross']:>11.2f}{ss['net']:>11.2f}")

    print(f"\n   --- per regime ---")
    print(f"   {'regime':<14}{'n':>6}{'per-sig $':>12}{'wr%':>7}{'seq n':>7}{'seq $':>11}")
    for rg in ("TREND", "ROTATION", "NEUTRAL", "UNKNOWN"):
        g = [s for s in rsigs if s["regime"] == rg]
        if not g:
            continue
        a, ss = agg(g), sequential(g)
        print(f"   {rg:<14}{len(g):>6}{a['gross']:>12.2f}{a['wr']:>7.1f}"
              f"{ss['taken']:>7}{ss['gross']:>11.2f}")

    print("\n   --- THE RULE, validated in and out of sample (ZLR only) ---")
    z = [s for s in rsigs if s["pattern"] == "ZLR"]

    def disp_rule(s, thr):
        return abs(s["disp"]) >= thr and ((s["disp"] > 0) == (s["direction"] == "LONG"))

    print(f"   {'variant':<46}{'window':<14}{'n':>5}{'seq n':>7}{'seq $':>11}"
          f"{'net $':>11}{'wr%':>7}{'$/sess':>9}")
    for thr in (0, 5, 8, 10, 12, 15, 20):
        for wname, pool in (("PRE-LOG (OOS)", [s for s in z if s["date"] < min(log_dates)]),
                            ("LOG window", [s for s in z if s["date"] >= min(log_dates)]),
                            ("ALL 48", z)):
            g = [s for s in pool if thr == 0 or disp_rule(s, thr)]
            if not g:
                continue
            ss = sequential(g)
            nd = len({s["date"] for s in pool})
            lbl = "every ZLR (no displacement rule)" if thr == 0 else \
                  f"ZLR with session displacement >= {thr}pt"
            print(f"   {lbl:<46}{wname:<14}{len(g):>5}{ss['taken']:>7}{ss['gross']:>11.2f}"
                  f"{ss['net']:>11.2f}{ss['wr']:>7.1f}{ss['net']/max(1,nd):>9.2f}")
        print()

    print("   --- same rule, ALL patterns, ALL 48 sessions ---")
    print(f"   {'variant':<46}{'n':>5}{'seq n':>7}{'seq $':>11}{'net $':>11}{'wr%':>7}{'$/sess':>9}")
    nd = len(days)
    for thr in (0, 10, 15):
        for lbl2, sel in (("all patterns", rsigs),
                          ("CONT only", [s for s in rsigs if s["pattern"] in
                                         ("ZLR", "TLB", "TT", "GB100")]),
                          ("REV only", [s for s in rsigs if s["pattern"] in
                                        ("VEGAS", "GHOST", "FAMIR", "HTLB")])):
            g = [s for s in sel if thr == 0 or disp_rule(s, thr)]
            if not g:
                continue
            ss = sequential(g)
            print(f"   {f'{lbl2}, disp>={thr}':<46}{len(g):>5}{ss['taken']:>7}"
                  f"{ss['gross']:>11.2f}{ss['net']:>11.2f}{ss['wr']:>7.1f}"
                  f"{ss['net']/max(1,nd):>9.2f}")

    print("\n   --- per-session net of the recommended rule (ZLR, disp>=10) ---")
    sel = [s for s in z if disp_rule(s, 10)]
    tot = 0.0
    for d in days:
        ds = [s for s in sel if s["date"] == d]
        if not ds:
            continue
        ss = sequential(ds)
        tot += ss["net"]
        print(f"   {d}  n={ss['taken']:<3} net=${ss['net']:>9.2f}  cum=${tot:>9.2f}   "
              f"[{(ds[0]['day_type'] or '—')}]")


def _split(rsigs, cut: str):
    """Chronological halves — the only honest hold-out available."""
    a = [s for s in rsigs if s["date"] < cut]
    b = [s for s in rsigs if s["date"] >= cut]
    return a, b


def sec_sweep(rsigs, cut: str) -> None:
    """Every pattern x every candidate filter, scored on BOTH chronological halves.

    A rule is only recommendable if it is positive in BOTH halves. Anything that is
    positive in one half only is in-sample fitting, and is labelled as such.
    """
    print("\n" + "=" * 100)
    print(f"11. PATTERN x RULE SWEEP — scored on both chronological halves (cut = {cut})")
    print("=" * 100)
    h1, h2 = _split(rsigs, cut)
    d1, d2 = len({s['date'] for s in h1}), len({s['date'] for s in h2})
    print(f"   half-1: {d1} sessions ({min(s['date'] for s in h1)} .. "
          f"{max(s['date'] for s in h1)})   half-2: {d2} sessions "
          f"({min(s['date'] for s in h2)} .. {max(s['date'] for s in h2)})")
    print("   A rule is BOTH-POSITIVE only if net$ > 0 in half-1 AND half-2.\n")

    def dagree(s, thr):
        return abs(s["disp"]) >= thr and ((s["disp"] > 0) == (s["direction"] == "LONG"))

    FILTERS = [
        ("no filter", lambda s: True),
        ("regime TREND only", lambda s: s["regime"] == "TREND"),
        ("regime != NEUTRAL", lambda s: s["regime"] != "NEUTRAL"),
        ("disp agrees >=10pt", lambda s: dagree(s, 10)),
        ("disp agrees >=15pt", lambda s: dagree(s, 15)),
        ("dist_extreme >= 6pt", lambda s: (s["dist_extreme"] or 0) >= 6),
        ("dist_extreme < 6pt", lambda s: (s["dist_extreme"] or 0) < 6),
        ("LSMA with dir >=0.25", lambda s: s["lsma_slope"] is not None and
         (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25),
        ("before 12:00 ET", lambda s: s["min"] < 12 * 60),
        ("10:30-15:00 ET", lambda s: 10 * 60 + 30 <= s["min"] < 15 * 60),
        ("LONG only", lambda s: s["direction"] == "LONG"),
        ("SHORT only", lambda s: s["direction"] == "SHORT"),
        ("disp>=10 AND !NEUTRAL", lambda s: dagree(s, 10) and s["regime"] != "NEUTRAL"),
        ("disp>=10 AND LSMA>=0.25", lambda s: dagree(s, 10) and s["lsma_slope"] is not None
         and (s["lsma_slope"] if s["direction"] == "LONG" else -s["lsma_slope"]) >= 0.25),
    ]
    pats = [p for p, c in Counter(s["pattern"] for s in rsigs).most_common() if c >= 20]
    winners = []
    for p in pats + ["<ALL S4>", "<CONT>", "<REV>"]:
        if p == "<ALL S4>":
            pool = rsigs
        elif p == "<CONT>":
            pool = [s for s in rsigs if s["pattern"] in ("ZLR", "TLB", "TT", "GB100")]
        elif p == "<REV>":
            pool = [s for s in rsigs if s["pattern"] in ("VEGAS", "GHOST", "FAMIR", "HTLB")]
        else:
            pool = [s for s in rsigs if s["pattern"] == p]
        print(f"   --- {p}  (n={len(pool)}) ---")
        print(f"   {'filter':<26}{'h1 n':>6}{'h1 net$':>11}{'h2 n':>6}{'h2 net$':>11}"
              f"{'both n':>7}{'both net$':>11}{'wr%':>7}  verdict")
        for fname, fn in FILTERS:
            a = [s for s in pool if s["date"] < cut and fn(s)]
            b = [s for s in pool if s["date"] >= cut and fn(s)]
            if len(a) + len(b) < 8:
                continue
            sa, sb, sall = sequential(a), sequential(b), sequential(a + b)
            ok = sa["net"] > 0 and sb["net"] > 0 and sa["taken"] >= 4 and sb["taken"] >= 4
            verdict = "BOTH-POSITIVE" if ok else ("in-sample only" if sall["net"] > 0 else "negative")
            if ok:
                winners.append((p, fname, sall["net"], sall["taken"], sa["net"], sb["net"]))
            print(f"   {fname:<26}{sa['taken']:>6}{sa['net']:>11.2f}{sb['taken']:>6}"
                  f"{sb['net']:>11.2f}{sall['taken']:>7}{sall['net']:>11.2f}"
                  f"{sall['wr']:>7.1f}  {verdict}")
        print()

    print("   " + "=" * 92)
    print("   RULES THAT SURVIVE BOTH HALVES (the only ones worth shipping)")
    print("   " + "=" * 92)
    if not winners:
        print("   NONE. Every candidate rule is positive in one half only.")
    else:
        print(f"   {'pattern':<14}{'filter':<26}{'trades':>7}{'net $ total':>13}"
              f"{'h1 net$':>11}{'h2 net$':>11}")
        for p, f, net, n, a, b in sorted(winners, key=lambda x: -x[2]):
            print(f"   {p:<14}{f:<26}{n:>7}{net:>13.2f}{a:>11.2f}{b:>11.2f}")


def sec_robust(rsigs, stop_pts: float, cut: str) -> None:
    """Stress the surviving candidates: slippage, stop, concentration, drawdown.

    A rule that only survives at 0 ticks of slippage, one stop value, or with its
    best trade included is not a rule — it is a story about the past.
    """
    print("\n" + "=" * 100)
    print("12. ROBUSTNESS — slippage / stop / concentration / drawdown on the candidates")
    print("=" * 100)

    def dagree(s, thr):
        return abs(s["disp"]) >= thr and ((s["disp"] > 0) == (s["direction"] == "LONG"))

    CANDS = [
        ("GB100 (no filter)", lambda s: s["pattern"] == "GB100"),
        ("GB100 + 10:30-15:00 ET", lambda s: s["pattern"] == "GB100"
         and 10 * 60 + 30 <= s["min"] < 15 * 60),
        ("GB100 + regime != NEUTRAL", lambda s: s["pattern"] == "GB100"
         and s["regime"] != "NEUTRAL"),
        ("HTLB (no filter)", lambda s: s["pattern"] == "HTLB"),
        ("HTLB + disp agrees >=10", lambda s: s["pattern"] == "HTLB" and dagree(s, 10)),
        ("GHOST + disp agrees >=10", lambda s: s["pattern"] == "GHOST" and dagree(s, 10)),
        ("ZLR (no filter)", lambda s: s["pattern"] == "ZLR"),
        ("ZLR + before 12:00 ET", lambda s: s["pattern"] == "ZLR" and s["min"] < 12 * 60),
        ("ALL S4 + disp>=10 & !NEUTRAL", lambda s: dagree(s, 10) and s["regime"] != "NEUTRAL"),
        ("GB100+HTLB, 10:30-15:00 ET", lambda s: s["pattern"] in ("GB100", "HTLB")
         and 10 * 60 + 30 <= s["min"] < 15 * 60),
    ]

    print(f"\n   --- concentration + drawdown (stop={stop_pts}pt, 0 slippage) ---")
    print(f"   {'candidate':<32}{'trades':>7}{'net $':>10}{'wr%':>7}{'drop-best':>11}"
          f"{'top3 share':>12}{'maxDD $':>10}{'$/sess':>9}")
    for name, fn in CANDS:
        pool = [s for s in rsigs if fn(s)]
        if not pool:
            continue
        busy, taken = {}, []
        for s in sorted(pool, key=lambda x: x["bar_ts"]):
            if busy.get(s["date"]) and s["bar_ts"] <= busy[s["date"]]:
                continue
            taken.append(s)
            busy[s["date"]] = s["fwd_end"]
        if not taken:
            continue
        pnl = [t["sim"]["pnl_usd"] - CONTRACTS * COMMISSION_RT for t in taken]
        net = sum(pnl)
        best = max(pnl)
        top3 = sum(sorted(pnl, reverse=True)[:3])
        eq, peak, dd = 0.0, 0.0, 0.0
        for x in pnl:
            eq += x
            peak = max(peak, eq)
            dd = min(dd, eq - peak)
        nsess = len({t["date"] for t in taken})
        wr = 100.0 * sum(1 for x in pnl if x > 0) / len(pnl)
        print(f"   {name:<32}{len(taken):>7}{net:>10.2f}{wr:>7.1f}{net - best:>11.2f}"
              f"{(100.0*top3/net if net else 0):>11.0f}%{dd:>10.2f}{net/max(1,nsess):>9.2f}")

    print(f"\n   --- SLIPPAGE sensitivity (net $, adverse fill vs the signal price) ---")
    print(f"   {'candidate':<32}{'0 tick':>11}{'1 tick':>11}{'2 ticks':>11}{'4 ticks':>11}")
    for name, fn in CANDS:
        pool = [s for s in rsigs if fn(s)]
        if not pool:
            continue
        cells = []
        for ticks in (0, 1, 2, 4):
            slip = ticks * 0.25
            busy, tot, n = {}, 0.0, 0
            for s in sorted(pool, key=lambda x: x["bar_ts"]):
                if busy.get(s["date"]) and s["bar_ts"] <= busy[s["date"]]:
                    continue
                e = s["entry"] + (slip if s["direction"] == "LONG" else -slip)
                sim = simulate(e, s["direction"], s["_fwd"], stop_pts)
                tot += sim["pnl_usd"] - CONTRACTS * COMMISSION_RT
                n += 1
                busy[s["date"]] = s["fwd_end"]
            cells.append(f"{tot:>11.2f}")
        print(f"   {name:<32}" + "".join(cells))

    print(f"\n   --- STOP sensitivity (net $) ---")
    print(f"   {'candidate':<32}" + "".join(f"{f'{sp}pt':>11}" for sp in (4, 5, 6.5, 8, 10, 12)))
    for name, fn in CANDS:
        pool = [s for s in rsigs if fn(s)]
        if not pool:
            continue
        cells = []
        for sp in (4.0, 5.0, 6.5, 8.0, 10.0, 12.0):
            busy, tot = {}, 0.0
            for s in sorted(pool, key=lambda x: x["bar_ts"]):
                if busy.get(s["date"]) and s["bar_ts"] <= busy[s["date"]]:
                    continue
                sim = simulate(s["entry"], s["direction"], s["_fwd"], sp)
                tot += sim["pnl_usd"] - CONTRACTS * COMMISSION_RT
                busy[s["date"]] = s["fwd_end"]
            cells.append(f"{tot:>11.2f}")
        print(f"   {name:<32}" + "".join(cells))

    print(f"\n   --- YEAR-MONTH walk-forward (net $ per month) ---")
    months = sorted({s["date"][:7] for s in rsigs})
    print(f"   {'candidate':<32}" + "".join(f"{m:>11}" for m in months))
    for name, fn in CANDS:
        pool = [s for s in rsigs if fn(s)]
        if not pool:
            continue
        cells = []
        for m in months:
            sel = [s for s in pool if s["date"][:7] == m]
            cells.append(f"{sequential(sel)['net']:>11.2f}" if sel else f"{'—':>11}")
        print(f"   {name:<32}" + "".join(cells))


def sec_reconcile(sigs) -> None:
    print("\n" + "=" * 100)
    print("10. MODEL vs REALITY — the signals the gateway PASSED, model P&L vs realised P&L")
    print("=" * 100)
    passed = [s for s in sigs if not s["gate"]]
    if not passed:
        print("   none")
        return
    days = sorted({s["date"] for s in passed})
    rows = q("""SELECT (entry_ts AT TIME ZONE 'America/New_York')::date d,
                SUM(COALESCE(pnl_usd,0)) pnl, COUNT(*) n
                FROM v9_trades WHERE firing_system=4 AND mode='live'
                  AND pattern_id_at_entry <> 'SIM_TEST'
                GROUP BY 1 ORDER BY 1""")
    real = {str(r["d"]): (float(r["pnl"]), int(r["n"])) for r in rows}
    print(f"   {'date':<12}{'passed sig':>11}{'model seq $':>13}{'model net $':>13}"
          f"{'LIVE trades':>12}{'LIVE $':>10}")
    mt = rt = 0.0
    for d in days:
        ps = [s for s in passed if s["date"] == d]
        ss = sequential(ps)
        rp, rn = real.get(d, (0.0, 0))
        mt += ss["net"]
        rt += rp
        print(f"   {d:<12}{len(ps):>11}{ss['gross']:>13.2f}{ss['net']:>13.2f}"
              f"{rn:>12}{rp:>10.2f}")
    print(f"   {'TOTAL':<12}{len(passed):>11}{'':>13}{mt:>13.2f}{'':>12}{rt:>10.2f}")
    print(f"\n   gap = ${mt - rt:+.2f}. Same signals, same days. The delta is NOT gate policy —")
    print("   it is stop placement + target ladder + partial-fill asymmetry in the live path.")
    lr = q("""SELECT pnl_r, pnl_usd, outcome, exit_reason FROM v9_trades
              WHERE firing_system=4 AND mode='live' AND pattern_id_at_entry='ZLR'
                AND pnl_usd IS NOT NULL""")
    if lr:
        wins = [float(r["pnl_usd"]) for r in lr if float(r["pnl_usd"]) > 0]
        loss = [float(r["pnl_usd"]) for r in lr if float(r["pnl_usd"]) < 0]
        print(f"\n   LIVE ZLR reality check: n={len(lr)}  net=${sum(float(r['pnl_usd']) for r in lr):.2f}")
        print(f"     wins  n={len(wins):<3} avg=${(sum(wins)/len(wins) if wins else 0):.2f}"
              f"  max=${max(wins) if wins else 0:.2f}")
        print(f"     losses n={len(loss):<3} avg=${(sum(loss)/len(loss) if loss else 0):.2f}"
              f"  max=${min(loss) if loss else 0:.2f}")
        print(f"     win rate {100.0*len(wins)/len(lr):.0f}%  |  payoff ratio "
              f"{(sum(wins)/len(wins))/abs(sum(loss)/len(loss)) if wins and loss else 0:.2f}")
        print(f"     exit reasons: {dict(Counter(r['exit_reason'] for r in lr))}")


def sec_stop_sweep(sigs) -> None:
    print("\n" + "=" * 100)
    print("8. STOP SENSITIVITY — the ladder is anchored on R, so the stop moves everything")
    print("=" * 100)
    print(f"   {'stop pt':>8}{'ZLR seq $':>13}{'ZLR net $':>13}{'ALL seq $':>13}{'ALL net $':>13}")
    z = [s for s in sigs if s["pattern"] == "ZLR"]
    for sp in (4.0, 5.0, 6.5, 8.0, 10.0, 12.0):
        zr, ar = [], []
        for s in sigs:
            sim = simulate(s["entry"], s["direction"], s["_fwd"], sp)
            row = dict(s); row["sim"] = sim
            ar.append(row)
            if s["pattern"] == "ZLR":
                zr.append(row)
        sz, sa = sequential(zr), sequential(ar)
        print(f"   {sp:>8.1f}{sz['gross']:>13.2f}{sz['net']:>13.2f}"
              f"{sa['gross']:>13.2f}{sa['net']:>13.2f}")


# ══════════════════════════════════════════════════════════════════════ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="comma list: sessions,decisions,trades,counter,zlr,chain,config,stops")
    ap.add_argument("--chain-dates", default="2026-08-10,2026-08-11")
    ap.add_argument("--stop-pts", type=float, default=DEFAULT_STOP_PTS)
    ap.add_argument("--max-dev", type=float, default=2.0,
                    help="max pt the logged entry may sit outside its signal bar's range "
                         "before the row is treated as a stale re-broadcast and dropped")
    ap.add_argument("--fwd-mode", choices=("strict", "leg"), default="strict",
                    help="strict = forward window starts AFTER the signal bar (default); "
                         "leg = starts at the signal bar (scripts/leg_exemption_replay.py)")
    ap.add_argument("--cut", default="2026-07-13",
                    help="chronological split date for the in/out-of-sample sweep")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()
    want = {w.strip() for w in args.only.split(",") if w.strip()} or {
        "sessions", "decisions", "trades", "counter", "zlr", "chain", "config", "stops",
        "reconcile", "replay", "sweep", "robust"}

    print("=" * 100)
    print("MEMS26 — SYSTEM-4 (Woodies CCI) FULL AUDIT")
    print(f"generated {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S %Z')}  "
          f"| stop={args.stop_pts}pt  fwd-mode={args.fwd_mode}")
    print("READ-ONLY: no flag changed, no restart, nothing written to ~/SierraChart_Data or the DB")
    print("=" * 100)
    live_flags = {k: os.environ.get(k) for k in (
        "ZLR_SPEC_V2", "HFE_DISABLED", "DAYTYPE_PLAYBOOK", "EXTREME_CHASE_GUARD_V1",
        "RELEASE_ENTRY_GATE_V1", "LSMA_FLAT_GATE_V1", "RR_ENTRY_GATE_V1",
        "LIVE_TRADING_V1", "LIVE_EXECUTION_V1", "CONT_TREND_FILTER", "DIRECTION_CONTEXT",
        "LEG_RIDE_V1", "S4_ENTRY_CONFIRM_V1", "ZONE_LIMIT_ENTRY_V1")}
    print("live flags read from .env:", json.dumps(live_flags))

    sessions = load_sessions()
    day_types = load_day_types()

    decisions = read_decisions()
    usig = unique_s4_signals(decisions)

    # enrich every unique S4 signal with context + forward simulation
    sigs = []
    drops: Counter = Counter()
    for r in usig:
        bars = load_bars(r["_date"])
        dt = (day_types.get(r["_date"]) or {}).get("day_type")
        s = build_signal(r, bars, dt, args.stop_pts, args.fwd_mode,
                         max_dev=args.max_dev, drops=drops)
        if s:
            idx = next((i for i, b in enumerate(bars) if b["et"] == r["_bar"]), None)
            fs = idx if args.fwd_mode == "leg" else idx + 1
            s["_fwd"] = bars[fs:fs + FWD_BARS]
            sigs.append(s)
    print(f"unique S4 signals: {len(usig)}  | simulatable: {len(sigs)}  | dropped: {sum(drops.values())}")
    for why, c in drops.most_common():
        print(f"    dropped {c:>4}  {why}")

    if "sessions" in want:
        sec_sessions(sessions, day_types)
    if "decisions" in want:
        sec_decisions(usig, day_types)
    if "trades" in want:
        sec_trades(day_types)
    if "counter" in want:
        sec_counter(sigs)
    if "zlr" in want:
        sec_zlr(sigs)
    if "chain" in want:
        sec_chain(decisions, [d.strip() for d in args.chain_dates.split(",") if d.strip()])
    if "config" in want:
        sec_config(sigs)
    if "stops" in want:
        sec_stop_sweep(sigs)
    if "reconcile" in want:
        sec_reconcile(sigs)
    if "replay" in want or "sweep" in want:
        rsigs = replay_signals(sessions, day_types, args.stop_pts)
        if "replay" in want:
            sec_replay(rsigs, sorted({s["_date"] for s in usig}))
        if "sweep" in want:
            sec_sweep(rsigs, args.cut)
        if "robust" in want:
            sec_robust(rsigs, args.stop_pts, args.cut)

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump({"signals": [{k: v for k, v in s.items()
                                    if not k.startswith("_") and k not in ("et", "bar_ts", "fwd_end")}
                                   for s in sigs],
                       "sessions": sessions,
                       "day_types": day_types}, fh, indent=1, default=str)
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
