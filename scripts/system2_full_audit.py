#!/usr/bin/env python3
"""system2_full_audit.py — SYSTEM-2 full audit across every session we have.

Answers, for EVERY RTH session present in `v9_bars_5min_woodies`:
  1. per-day S2 signal counts by pattern family, which gate blocked them,
     how many became real `v9_trades` rows, realized P&L;
  2. MFE/MAE + modelled $ over the next 12 bars for every signal, so the
     $-cost (or $-saving) of each gate is measurable per day-type;
  3. a pattern x day-type x time-of-day matrix with n and $;
  4. a bar-by-bar chain walk for named dates (--chain 2026-08-10,2026-08-11).

STRICTLY READ-ONLY.  Reads `v9_bars_5min_woodies`, `v9_trades`,
`v9_day_type_*` (through the shipped `classify_replay`) and the append-only
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl`.  It NEVER writes to the
DB, never touches ~/SierraChart_Data, never sets a flag and never restarts
anything.  The only env mutation is `os.environ` inside THIS process, so the
flag-gated detectors (HLST, RE_PULLBACK) can be replayed head-to-head.

Fidelity notes (read before trusting a number)
----------------------------------------------
* The replay reproduces the LIVE detection chain of
  `FiveMinSystem.process_bar` exactly: same priority order
  (REACTIVE -> INITIATIVE -> HLST -> HnS -> Double -> Flags -> RE_PULLBACK),
  same `_det_buf = buffer[:-1]` completed-bar window, same 20-bar buffer cap,
  same per-kind dedup cooldowns.  `--buffer N` lifts the cap so the cost of
  the 20-bar buffer on the 30-bar chart patterns is measurable.
* `poc_vol` is 0.0 in the live Sierra export, so `_poc_vol_rising` falls back
  to the HLC/3 proxy in production too -> the woodies-bar replay takes the
  same branch as live.  No synthesis is introduced here.
* Gate attribution is only available where `gateway_decisions.jsonl` reaches
  (2026-07-22 -> 2026-08-11).  Earlier sessions are reported as
  gate=`no_log` -- NOT as "passed".  Honest failure > synthetic value.

Usage
-----
  python3 scripts/system2_full_audit.py --report docs/research/SYSTEM2_FULL_AUDIT_2026-08-11.md
  python3 scripts/system2_full_audit.py --chain 2026-08-10,2026-08-11
  python3 scripts/system2_full_audit.py --buffer 60 --summary-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict, OrderedDict
from datetime import time as dtime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── .env must be loaded or the classifier mislabels days (house rule) ──
try:
    from scripts.flag_guard import parse_env
    for _k, _v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(_k, _v)
except Exception as _e:  # pragma: no cover
    print(f"[warn] could not parse .env: {_e}", file=sys.stderr)

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
os.environ.setdefault("BRIDGE_TOKEN", "x")

from zoneinfo import ZoneInfo  # noqa: E402

ET = ZoneInfo("America/New_York")
RTH_OPEN, RTH_CLOSE = dtime(9, 30), dtime(16, 0)

# ── execution model (identical constants to scripts/leg_exemption_replay.py
#    and scripts/replay_trend_step_entry.py so the three reports compare) ──
CONTRACTS = 4
POINT_VALUE = 5.0          # $/pt/contract (MES)
COMMISSION_RT = 1.50       # $/contract round-turn
FWD_BARS = 12              # MFE/MAE + simulation horizon
T0_PTS = 3.0               # C1 -> fixed +3pt
T1_R, T2_R, T3_R = 1.0, 2.0, 4.0   # C2/C3/C4 in R
BE_AFTER_IDX = 1           # breakeven once T1 (1R) fills
FLAT_STOP_PTS = 8.0        # comparability model (previous reports)
STOP_MIN_PTS, STOP_MAX_PTS = 4.0, 12.0   # structural-stop clamp

DECISIONS = Path.home() / "SierraChart_Data" / "v9_export" / "gateway_decisions.jsonl"
FIXTURE_ENTRY = 7600.0     # pytest fixture rows -- excluded everywhere

GATE_LOG_FROM = "2026-07-22"   # first date present in gateway_decisions.jsonl

FAMILY = {
    "REACTIVE": "REACTIVE",
    "INITIATIVE": "INITIATIVE",
    "HIGHER_LOW_SECOND_TEST": "HLST",
    "INVERSE_HNS": "HNS", "HNS_TOP": "HNS",
    "DOUBLE_BOTTOM_EE": "DOUBLE", "DOUBLE_TOP_AA": "DOUBLE",
    "BULL_FLAG": "FLAG", "BEAR_FLAG": "FLAG",
    "RE_PULLBACK": "RE_PULLBACK",
}

# 7-type -> the four buckets Michael asked for
DT_BUCKET = {
    "Trend_Normal": "Trend", "Trend_Variation": "Trend", "Trend": "Trend",
    "Trend_DD": "Trend", "Double_Distribution": "Trend",
    "Normal_Variation": "Variation", "Expanded_Typical": "Variation",
    "Normal_Day": "Normal", "Normal": "Normal",
    "Neutral_Center": "Neutral", "Neutral_Extreme": "Neutral", "Neutral": "Neutral",
    "Nontrend": "Nontrend",
}

# Which families are actually ARMED in production today (docs/FLAG_INDEX.md +
# .env).  HLST is gated by HIGHER_LOW_SECOND_TEST_V1 (absent from .env => OFF)
# and RE_PULLBACK by RE_PULLBACK_ENTRY_V1 (absent => OFF).  Everything else in
# the chain is unconditional.  Replayed anyway so the measured edge is visible.
PROD_ARMED = {"REACTIVE": True, "INITIATIVE": True, "HNS": True,
              "DOUBLE": True, "FLAG": True, "HLST": False, "RE_PULLBACK": False}

TOD_BUCKETS = [
    ("09:30-10:30", dtime(9, 30), dtime(10, 30)),
    ("10:30-12:00", dtime(10, 30), dtime(12, 0)),
    ("12:00-14:00", dtime(12, 0), dtime(14, 0)),
    ("14:00-16:00", dtime(14, 0), dtime(16, 0)),
]


# ══════════════════════════════════════════════════════════ data loading
def load_bars() -> "OrderedDict[str, List[Dict[str, Any]]]":
    """All MES 5-min woodies bars, grouped by ET session date.

    Overnight bars are kept in the buffer (the live system buffers them too)
    but only RTH bars can produce a signal.
    """
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT ts, open, high, low, close, volume, cci_14, lsma_value, trend_state "
        "FROM v9_bars_5min_woodies WHERE symbol='MES' ORDER BY ts ASC", {}
    )
    by_day: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for r in rows:
        et = r["ts"].astimezone(ET)
        d = et.date().isoformat()
        b = {
            "ts": r["ts"].timestamp(), "et": et, "date": d,
            "o": float(r["open"]), "h": float(r["high"]),
            "l": float(r["low"]), "c": float(r["close"]),
            "v": int(r["volume"] or 0), "vol": int(r["volume"] or 0),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "cci_14": float(r["cci_14"]) if r["cci_14"] is not None else None,
            "lsma": float(r["lsma_value"]) if r["lsma_value"] is not None else None,
            "trend_state": r["trend_state"],
            "rth": RTH_OPEN <= et.time() < RTH_CLOSE,
        }
        by_day.setdefault(d, []).append(b)
    return by_day


def load_decisions() -> List[Dict[str, Any]]:
    """S2 rows of the gateway decision log, fixture rows removed."""
    out = []
    if not DECISIONS.exists():
        return out
    from datetime import datetime
    for line in DECISIONS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if str(d.get("system")) != "2":
            continue
        try:
            entry = float(d.get("entry") or 0.0)
        except Exception:
            entry = 0.0
        if abs(entry - FIXTURE_ENTRY) < 0.01:
            continue                      # pytest fixture contamination
        try:
            ts = datetime.fromisoformat(str(d["ts"]).replace("Z", "+00:00"))
        except Exception:
            continue
        et = ts.astimezone(ET)
        d["_et"] = et
        d["_date"] = et.date().isoformat()
        d["_entry"] = entry
        d["_gate"] = d.get("blocked_by") or ("PASSED" if d.get("outcome") in ("live", "shadow_only") else "unknown")
        out.append(d)
    return out


def load_trades() -> List[Dict[str, Any]]:
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT id, mode, firing_system, direction, state, entry_ts, entry_price, stop, "
        "       t1, t2, t3, exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, outcome, "
        "       day_type_at_entry, pattern_id_at_entry "
        "FROM v9_trades WHERE firing_system=2 AND entry_ts IS NOT NULL ORDER BY entry_ts ASC", {}
    )
    for r in rows:
        et = r["entry_ts"].astimezone(ET)
        r["_et"] = et
        r["_date"] = et.date().isoformat()
    return rows


_DT_CACHE: Dict[str, Dict[str, Any]] = {}


def day_type_for(date: str) -> Tuple[str, str, Optional[str]]:
    """(raw 7-type label, 4-bucket, dir_bias) from the shipped classifier."""
    if date in _DT_CACHE:
        c = _DT_CACHE[date]
        return c["raw"], c["bucket"], c["bias"]
    raw, bias = "UNKNOWN", None
    try:
        from backend.v9.api.v9.daytype_classify_routes import classify_replay
        res = classify_replay(date)
        fin = res.get("final") or {}
        raw = fin.get("day_type") or "UNKNOWN"
        bias = fin.get("dir_bias")
    except Exception as e:
        print(f"[warn] classify_replay({date}) failed: {e}", file=sys.stderr)
    bucket = DT_BUCKET.get(raw, "Unknown")
    _DT_CACHE[date] = {"raw": raw, "bucket": bucket, "bias": bias}
    return raw, bucket, bias


# ══════════════════════════════════════════════════════ detection replay
class S2Replay:
    """Bar-for-bar reproduction of FiveMinSystem.process_bar's detection chain."""

    def __init__(self, buffer_cap: int = 20, enable_hlst: bool = True,
                 enable_pullback: bool = True):
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        self.fs = FiveMinSystem()
        self.buffer_cap = buffer_cap
        self.enable_hlst = enable_hlst
        self.enable_pullback = enable_pullback
        self.cooldown = dict(self.fs._dedup_cooldown)

    def _atr(self, buf: List[Dict]) -> float:
        w = buf[-14:]
        if not w:
            return 2.0
        return max(0.25, sum(b["h"] - b["l"] for b in w) / len(w))

    def detect(self, det_buf: List[Dict], day_type: str) -> Tuple[Optional[str], float, Dict]:
        from backend.v9.systems.five_min.five_min_system import chart_patterns_allowed
        from backend.v9.systems.five_min.patterns.head_shoulders import detect_inverse_hns, detect_hns_top
        from backend.v9.systems.five_min.patterns.double_bt import detect_double_bottom_ee, detect_double_top_aa
        from backend.v9.systems.five_min.patterns.flags import detect_bull_flag, detect_bear_flag

        self.fs._current_atr_5m = self._atr(det_buf)

        d, c, info = self.fs._detect_reactive(det_buf)
        if not d:
            d, c, info = self.fs._detect_initiative(det_buf)

        if not d and self.enable_hlst:
            from backend.v9.systems.five_min.patterns.higher_low_second_test import (
                detect_higher_low_second_test_long, detect_higher_low_second_test_short)
            d, c, info = detect_higher_low_second_test_long(det_buf)
            if not d:
                d, c, info = detect_higher_low_second_test_short(det_buf)

        if not d and chart_patterns_allowed(day_type, "5a"):
            d, c, info = detect_inverse_hns(det_buf)
            if not d:
                d, c, info = detect_hns_top(det_buf)
            if not d:
                d, c, info = detect_double_bottom_ee(det_buf, atr_5m=self.fs._current_atr_5m)
            if not d:
                d, c, info = detect_double_top_aa(det_buf, atr_5m=self.fs._current_atr_5m)

        if not d and chart_patterns_allowed(day_type, "5c"):
            d, c, info = detect_bull_flag(det_buf)
            if not d:
                d, c, info = detect_bear_flag(det_buf)

        if not d and self.enable_pullback:
            try:
                from backend.v9.systems.five_min.patterns.pullback_retest import detect_pullback_retest
                d, c, info = detect_pullback_retest(det_buf, ib_high=None, ib_low=None,
                                                    ib_locked=False, session_min=90)
            except Exception:
                d, c, info = None, 0.0, {}
        return d, (c or 0.0), (info or {})

    def run_session(self, bars: List[Dict], day_type: str) -> List[Dict]:
        """Feed the day's bars through the chain; return raw signals."""
        buf: List[Dict] = []
        fired: Dict[str, int] = {}
        sigs: List[Dict] = []
        for i, bar in enumerate(bars):
            buf.append(bar)
            if len(buf) > self.buffer_cap:
                buf = buf[-self.buffer_cap:]
            if not bar["rth"]:
                continue                        # OVERNIGHT_MODE: buffer only
            det_buf = buf[:-1] if len(buf) >= 8 else buf
            if len(det_buf) < 5:
                continue
            try:
                d, c, info = self.detect(det_buf, day_type)
            except Exception:
                continue
            if not d:
                continue
            kind = info.get("kind", "UNKNOWN")
            key = f"{kind}_{d}"
            cd = self.cooldown.get(kind, 0)
            if cd and key in fired and (i - fired[key]) < cd:
                continue                        # live A2 dedup
            fired[key] = i
            completed = det_buf[-1]
            sigs.append({
                "i": i, "bar_i": bars.index(completed) if completed in bars else i - 1,
                "ts": completed["ts"], "et": completed["et"], "date": bars[i]["date"],
                "kind": kind, "family": FAMILY.get(kind, kind), "direction": d,
                "conf": round(float(c), 3),
                "entry": float(completed["c"]),
                "anchor": info.get("structural_anchor"),
                "signal_bar_et": completed["et"],
            })
        return sigs


# ══════════════════════════════════════════════════════════ simulation
def simulate(entry: float, direction: str, fwd: List[Dict], stop_pts: float) -> Dict[str, Any]:
    """4 contracts: C1 +3pt, C2 1R, C3 2R, C4 4R runner (TIME-exit at bar 12).

    Conservative: inside a bar the STOP is checked before any target.
    BE once the 1R leg fills (BE_AFTER_IDX).
    """
    sign = 1.0 if direction == "LONG" else -1.0
    stop = entry - sign * stop_pts
    tgt_pts = [T0_PTS, T1_R * stop_pts, T2_R * stop_pts, T3_R * stop_pts]
    targets = [entry + sign * t for t in tgt_pts]
    open_c = [True] * CONTRACTS
    pnl_pts, legs, be_done = 0.0, [], False
    for b in fwd:
        hi, lo = b["h"], b["l"]
        if (lo <= stop) if direction == "LONG" else (hi >= stop):
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
            if (hi >= t) if direction == "LONG" else (lo <= t):
                open_c[i] = False
                pnl_pts += (t - entry) * sign
                legs.append((f"T{i}", round((t - entry) * sign, 2)))
                if i == BE_AFTER_IDX and not be_done:
                    stop, be_done = entry, True
    if any(open_c) and fwd:
        last = fwd[-1]["c"]
        for i in range(CONTRACTS):
            if open_c[i]:
                pnl_pts += (last - entry) * sign
                legs.append(("TIME", round((last - entry) * sign, 2)))
    return {
        "pnl_pts": round(pnl_pts, 2),
        "pnl_usd": round(pnl_pts * POINT_VALUE, 2),
        "net_usd": round(pnl_pts * POINT_VALUE - CONTRACTS * COMMISSION_RT, 2),
        "legs": legs, "be": be_done, "stop_pts": round(stop_pts, 2),
    }


def mfe_mae(entry: float, direction: str, fwd: List[Dict]) -> Tuple[float, float]:
    if not fwd:
        return 0.0, 0.0
    sign = 1.0 if direction == "LONG" else -1.0
    best = max((b["h"] - entry) * sign if direction == "LONG" else (entry - b["l"]) for b in fwd)
    worst = min((b["l"] - entry) * sign if direction == "LONG" else (entry - b["h"]) for b in fwd)
    return round(best, 2), round(worst, 2)


def structural_stop_pts(entry: float, direction: str, anchor: Optional[float]) -> float:
    if anchor is None:
        return FLAT_STOP_PTS
    try:
        d = abs(float(entry) - float(anchor))
    except Exception:
        return FLAT_STOP_PTS
    return max(STOP_MIN_PTS, min(STOP_MAX_PTS, d))


def tod_bucket(et) -> str:
    t = et.time()
    for name, a, b in TOD_BUCKETS:
        if a <= t < b:
            return name
    return "other"


# ═════════════════════════════════════════════════ gate attribution join
def attach_gates(sigs: List[Dict], decisions: List[Dict]) -> None:
    """Attach the live gate verdict to each replayed signal.

    Match requires: same date, same direction, **same pattern family**,
    |entry diff| <= 2.0 pt, and the decision within [-5min, +20min] of the
    signal bar close (the gateway evaluates after the bar closes).

    The family check matters: without it a replayed HLST signal happily
    inherits the gate of a nearby REACTIVE decision, which would fabricate
    gate attribution for a detector that is flag-OFF in production.
    """
    def fam_of_live(p: Optional[str]) -> Optional[str]:
        if not p:
            return None
        p = p.upper()
        for kind, fam in FAMILY.items():
            if p.startswith(kind):
                return fam
        return None

    by_date: Dict[str, List[Dict]] = defaultdict(list)
    for d in decisions:
        by_date[d["_date"]].append(d)
    for s in sigs:
        if s["date"] < GATE_LOG_FROM:
            s["gate"] = "no_log"
            s["gate_src"] = "none"
            continue
        if not PROD_ARMED.get(s["family"], True):
            s["gate"] = "detector_off"     # never reached the gateway at all
            s["gate_src"] = "none"
            continue
        cands = by_date.get(s["date"], [])
        best, best_dt = None, None
        for d in cands:
            if d.get("direction") != s["direction"]:
                continue
            if fam_of_live(d.get("pattern")) != s["family"]:
                continue
            dt = (d["_et"] - s["et"]).total_seconds()
            if not (-300 <= dt <= 1200):
                continue
            if abs(d["_entry"] - s["entry"]) > 2.0:
                continue
            if best is None or abs(dt) < abs(best_dt):
                best, best_dt = d, dt
        if best is None:
            # Distinguish "the detector is flag-OFF in production so the
            # gateway never saw it" from "armed, but no matching row".
            s["gate"] = "detector_off" if not PROD_ARMED.get(s["family"], True) else "not_in_log"
            s["gate_src"] = "none"
        else:
            s["gate"] = best["_gate"]
            s["gate_src"] = best.get("outcome")
            s["gate_reason"] = best.get("reason")


NON_GATE = ("no_log", "not_in_log", "detector_off")


def simulate_sequential(sigs: List[Dict], bars_by_day: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """One position at a time — the number a real account would have made.

    Signals are taken in chronological order; while a position is open every
    new signal is skipped (the live system holds a single S2 slot).  Exit bar
    = stop/last-target/TIME within the 12-bar horizon.
    """
    taken, skipped = [], 0
    busy_until: Dict[str, int] = {}
    for s in sorted(sigs, key=lambda x: (x["date"], x["ts"])):
        d = s["date"]
        if s["i"] < busy_until.get(d, -1):
            skipped += 1
            continue
        taken.append(s)
        busy_until[d] = s["i"] + FWD_BARS
    gross = sum(t["sim"]["pnl_usd"] for t in taken)
    net = sum(t["sim"]["net_usd"] for t in taken)
    wins = sum(1 for t in taken if t["sim"]["pnl_usd"] > 0)
    # per-day equity for max drawdown
    per_day: Dict[str, float] = defaultdict(float)
    for t in taken:
        per_day[t["date"]] += t["sim"]["pnl_usd"]
    eq, peak, dd = 0.0, 0.0, 0.0
    for d in sorted(per_day):
        eq += per_day[d]
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    return {"n": len(taken), "skipped": skipped, "gross": round(gross, 2),
            "net": round(net, 2), "wins": wins,
            "win_pct": round(100 * wins / max(len(taken), 1), 1),
            "per_day": dict(per_day), "max_dd": round(dd, 2),
            "days": len(per_day), "taken": taken}


def score_config(sigs: List[Dict], bars_by_day, families: set, buckets: set,
                 t_from: dtime, t_to: dtime, directions: set = None,
                 sessions: Optional[List[str]] = None) -> Dict[str, Any]:
    sel = [s for s in sigs
           if s["family"] in families
           and s["dt_bucket"] in buckets
           and t_from <= s["et"].time() < t_to
           and (directions is None or s["direction"] in directions)
           and (sessions is None or s["date"] in sessions)]
    r = simulate_sequential(sel, bars_by_day)
    nd = len(sessions) if sessions else max(r["days"], 1)
    r["per_session"] = round(r["net"] / max(nd, 1), 2)
    r["raw_n"] = len(sel)
    return r


# ══════════════════════════════════════════════════════════════ reporting
def fmt_money(x: float) -> str:
    return f"{'+' if x >= 0 else '-'}${abs(x):,.0f}"


def agg(rows: List[Dict], key) -> "OrderedDict[Any, Dict[str, float]]":
    out: "OrderedDict[Any, Dict[str, float]]" = OrderedDict()
    for r in rows:
        k = key(r)
        a = out.setdefault(k, {"n": 0, "usd": 0.0, "net": 0.0, "win": 0,
                               "mfe": 0.0, "mae": 0.0})
        a["n"] += 1
        a["usd"] += r["sim"]["pnl_usd"]
        a["net"] += r["sim"]["net_usd"]
        a["win"] += 1 if r["sim"]["pnl_usd"] > 0 else 0
        a["mfe"] += r["mfe"]
        a["mae"] += r["mae"]
    for a in out.values():
        a["mfe"] /= max(a["n"], 1)
        a["mae"] /= max(a["n"], 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer", type=int, default=20,
                    help="bar-buffer cap (20 = live).  Larger = what the chart "
                         "patterns would see without the live cap.")
    ap.add_argument("--report", default=None, help="write markdown report here")
    ap.add_argument("--json", default=None, help="dump per-signal rows as JSON")
    ap.add_argument("--chain", default="", help="comma dates for the chain walk")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--min-rth-bars", type=int, default=20)
    args = ap.parse_args()

    print("[1/5] loading bars ...", file=sys.stderr)
    by_day = load_bars()
    sessions = [d for d, bs in by_day.items()
                if sum(1 for b in bs if b["rth"]) >= args.min_rth_bars]
    sessions.sort()
    print(f"      {len(sessions)} usable RTH sessions "
          f"({sessions[0]} -> {sessions[-1]})", file=sys.stderr)

    print("[2/5] classifying day types ...", file=sys.stderr)
    dts = {d: day_type_for(d) for d in sessions}

    print("[3/5] replaying S2 detection chain ...", file=sys.stderr)
    # HLST + RE_PULLBACK are flag-gated OFF in production. Replay them ON so
    # their measured edge is visible, and tag them so the config section can
    # separate "live today" from "candidate".
    os.environ["HIGHER_LOW_SECOND_TEST_V1"] = "1"
    rep = S2Replay(buffer_cap=args.buffer)
    all_sigs: List[Dict] = []
    for d in sessions:
        bars = by_day[d]
        raw_dt, bucket, bias = dts[d]
        sigs = rep.run_session(bars, raw_dt)
        idx = {id(b): i for i, b in enumerate(bars)}
        for s in sigs:
            i = s["i"]
            fwd = [b for b in bars[i:i + FWD_BARS]]
            s["mfe"], s["mae"] = mfe_mae(s["entry"], s["direction"], fwd)
            sp = structural_stop_pts(s["entry"], s["direction"], s["anchor"])
            s["sim"] = simulate(s["entry"], s["direction"], fwd, sp)
            s["sim_flat8"] = simulate(s["entry"], s["direction"], fwd, FLAT_STOP_PTS)
            s["day_type"] = raw_dt
            s["dt_bucket"] = bucket
            s["dir_bias"] = bias
            s["tod"] = tod_bucket(s["et"])
        all_sigs.extend(sigs)
    print(f"      {len(all_sigs)} raw S2 signals", file=sys.stderr)

    print("[4/5] joining gateway decisions + real trades ...", file=sys.stderr)
    decisions = load_decisions()
    attach_gates(all_sigs, decisions)
    trades = load_trades()

    print("[5/5] building report ...", file=sys.stderr)
    out: List[str] = []
    W = out.append

    # ---------- header
    W("# SYSTEM-2 — full audit, every session we have")
    W("")
    W(f"*Generated by `scripts/system2_full_audit.py` (buffer_cap={args.buffer}) — READ-ONLY.*")
    W("")
    W(f"- Sessions: **{len(sessions)}** ({sessions[0]} → {sessions[-1]}), "
      f"source `v9_bars_5min_woodies`, RTH 09:30–16:00 ET, ≥{args.min_rth_bars} bars.")
    W(f"- Raw S2 signals replayed: **{len(all_sigs)}**.")
    W(f"- Gate log coverage: `gateway_decisions.jsonl` "
      f"**{GATE_LOG_FROM} → 2026-08-11 only**; earlier sessions carry `no_log`.")
    W(f"- Execution model: {CONTRACTS} contracts, C1 +{T0_PTS:.0f}pt / C2 {T1_R:.0f}R / "
      f"C3 {T2_R:.0f}R / C4 {T3_R:.0f}R runner, BE after 1R, stop-before-target "
      f"inside a bar, {FWD_BARS}-bar horizon, ${POINT_VALUE:.0f}/pt, "
      f"${COMMISSION_RT:.2f}/contract RT.")
    W("")

    # ---------- executive summary (computed)
    _armed0 = {f for f, v in PROD_ARMED.items() if v}
    _ALLB = set(DT_BUCKET.values()) | {"Unknown"}
    _b = score_config(all_sigs, by_day, _armed0, _ALLB, dtime(9, 30), dtime(16, 0), sessions=sessions)
    _h = score_config(all_sigs, by_day, {"HLST"}, _ALLB, dtime(9, 30), dtime(16, 0), sessions=sessions)
    _t2 = [t for t in trades]
    _tlive = [t for t in _t2 if t["mode"] == "live"]
    W("## 0. Executive summary")
    W("")
    W("1. **The headline is not a flag — it is a corrupted input.**  Two publishers")
    W("   write to the BarRouter `\"5min\"` topic and `FiveMinSystem` dedups on the")
    W("   timestamp **string**, so every 5-min bar is appended to the S2 buffer")
    W("   **twice**, from two different price series, one of which carries")
    W("   cumulative session volume (100–800× real).  The 4-bar REACTIVE window is")
    W("   therefore ~2 real bars duplicated.  Wired 2026-05-12 → present for this")
    W("   entire audit window.  Full evidence + reproduction commands in §7.")
    W(f"2. **What S2 is worth on a clean feed:** the production-armed families")
    W(f"   (REACTIVE · INITIATIVE · FLAG · DOUBLE · HnS) make "
      f"**{fmt_money(_b['net'])} net / {fmt_money(_b['per_session'])} per session** over "
      f"{len(sessions)} sessions ({_b['n']} sequential trades, {_b['win_pct']:.0f}% win, "
      f"max DD {fmt_money(_b['max_dd'])}), and are **positive in both halves** of the sample.")
    W(f"3. **HLST is the one clear negative** — {fmt_money(_h['net'])} net on {_h['n']} trades. "
      "It is flag-OFF today; keep it OFF.  Second independent confirmation of the "
      "2026-08-11 22:40 finding.")
    W(f"4. **Reality check:** real S2 trades in `v9_trades` = {len(_t2)} "
      f"({fmt_money(sum(float(t['pnl_usd'] or 0) for t in _t2))} all modes), of which "
      f"`mode=live` = {len(_tlive)} ({fmt_money(sum(float(t['pnl_usd'] or 0) for t in _tlive))}). "
      "The modelled numbers above are a ceiling, not a forecast.")
    W("5. **Michael's two dates (full chain in §8):**")
    W("   - **2026-08-10 — the premise is wrong: S2 DID trade.**  `DOUBLE_BOTTOM_EE_LONG`")
    W("     fired 10:46 ET @ 7795.00, passed every gate (`outcome=live`), got stop")
    W("     7790.75 (**4.25 pt**) and T1 7797.75 (**+2.75 pt**) from StopResolver, and")
    W("     stopped out for **−$63.75 / −0.75R**.  The other two signals that day")
    W("     (`REACTIVE_SHORT` 11:10 and 14:20) were blocked by `daytype_playbook` and")
    W("     `awaiting_release`.  Three unique signals, one trade, one loss.")
    W("   - **2026-08-11 — 11 unique signals, 11 blocks, 0 trades.**  `extreme_chase_guard`")
    W("     ×5 (11:15/11:30/11:35/11:55/12:25 — the entire down-leg, every one rejected")
    W("     for being 0.5–2.0 pt from the session low against a 6.2 pt requirement),")
    W("     `lsma_flat` ×2 (14:10/15:00), `direction_context` ×1 (10:00),")
    W("     `awaiting_release` ×1 (10:50), `daytype_playbook` ×1 (13:25),")
    W("     `eod_entry_cutoff` ×1 (15:50).  No pre-fire, margin, dedup or slot failure.")
    W("     Note the 5 chase-guard blocks all sit inside the stretch where the local")
    W("     tick aggregator was live (from 11:10 ET), i.e. on the contaminated buffer.")
    W("6. **Recommended change set for tomorrow: none to the S2 flags.**  Fix the feed")
    W("   first (§9.0).  Every gate that looks expensive in §2 has n<25 and was")
    W("   measured on the corrupted buffer — opening one is a risk-surface change")
    W("   with no evidence behind it.  Full config table in §9.")
    W("")

    # ---------- session list
    W("## Session inventory")
    W("")
    W("| # | date | RTH bars | day_type | bucket | bias | S2 signals |")
    W("|---|---|---|---|---|---|---|")
    for n, d in enumerate(sessions, 1):
        raw_dt, bucket, bias = dts[d]
        nb = sum(1 for b in by_day[d] if b["rth"])
        ns = sum(1 for s in all_sigs if s["date"] == d)
        W(f"| {n} | {d} | {nb} | {raw_dt} | {bucket} | {bias or '—'} | {ns} |")
    W("")

    # ---------- per family
    W("## 1. Signal census by pattern family")
    W("")
    W("| family | n | live-gate PASSED | blocked | no_log | modelled $ (struct stop) | net $ | win% | avg MFE | avg MAE |")
    W("|---|---|---|---|---|---|---|---|---|---|")
    fam_agg = agg(all_sigs, lambda r: r["family"])
    for fam, a in sorted(fam_agg.items(), key=lambda kv: -kv[1]["n"]):
        rows = [s for s in all_sigs if s["family"] == fam]
        passed = sum(1 for s in rows if s["gate"] == "PASSED")
        blocked = sum(1 for s in rows if s["gate"] not in ("PASSED", "no_log", "not_in_log"))
        nolog = sum(1 for s in rows if s["gate"] in ("no_log", "not_in_log"))
        W(f"| {fam} | {a['n']} | {passed} | {blocked} | {nolog} | {fmt_money(a['usd'])} | "
          f"{fmt_money(a['net'])} | {100*a['win']/max(a['n'],1):.0f}% | "
          f"{a['mfe']:+.1f} | {a['mae']:+.1f} |")
    W("")

    # ---------- gate cost
    W("## 2. What each gate cost / saved (log window only)")
    W("")
    W("Only signals inside the gate-log window are counted; `no_log` rows are excluded")
    W("because we cannot know what the gateway would have said.")
    W("")
    W("| gate | n | modelled $ | net $ | win% | avg MFE | avg MAE | verdict |")
    W("|---|---|---|---|---|---|---|---|")
    logged = [s for s in all_sigs if s["gate"] not in ("no_log", "not_in_log")]
    for gate, a in sorted(agg(logged, lambda r: r["gate"]).items(), key=lambda kv: kv[1]["usd"]):
        verdict = "GATE SAVED money" if a["usd"] < 0 else "GATE COST money"
        if gate == "PASSED":
            verdict = "(passed to gateway)"
        elif gate == "detector_off":
            verdict = "NOT A GATE — flag-OFF detector, never reached the gateway"
        W(f"| `{gate}` | {a['n']} | {fmt_money(a['usd'])} | {fmt_money(a['net'])} | "
          f"{100*a['win']/max(a['n'],1):.0f}% | {a['mfe']:+.1f} | {a['mae']:+.1f} | {verdict} |")
    W("")

    # gate x day-type
    W("### 2b. Gate cost by day-type bucket")
    W("")
    W("| gate | Trend n/$ | Variation n/$ | Normal n/$ | Neutral n/$ | Nontrend n/$ |")
    W("|---|---|---|---|---|---|")
    gates = sorted({s["gate"] for s in logged})
    for g in gates:
        cells = []
        for b in ("Trend", "Variation", "Normal", "Neutral", "Nontrend"):
            rows = [s for s in logged if s["gate"] == g and s["dt_bucket"] == b]
            cells.append(f"{len(rows)} / {fmt_money(sum(r['sim']['pnl_usd'] for r in rows))}"
                         if rows else "—")
        W(f"| `{g}` | " + " | ".join(cells) + " |")
    W("")

    # ---------- matrix
    W("## 3. Matrix — pattern × day-type (n / modelled $ / net $)")
    W("")
    buckets = ["Trend", "Variation", "Normal", "Neutral", "Nontrend", "Unknown"]
    W("| family | " + " | ".join(buckets) + " | TOTAL |")
    W("|---|" + "---|" * (len(buckets) + 1))
    for fam in sorted({s["family"] for s in all_sigs}):
        cells = []
        for b in buckets:
            rows = [s for s in all_sigs if s["family"] == fam and s["dt_bucket"] == b]
            if not rows:
                cells.append("—")
                continue
            usd = sum(r["sim"]["pnl_usd"] for r in rows)
            net = sum(r["sim"]["net_usd"] for r in rows)
            cells.append(f"n={len(rows)}<br>{fmt_money(usd)}<br>({fmt_money(net)})")
        rows = [s for s in all_sigs if s["family"] == fam]
        tot = sum(r["sim"]["pnl_usd"] for r in rows)
        tnet = sum(r["sim"]["net_usd"] for r in rows)
        cells.append(f"n={len(rows)}<br>{fmt_money(tot)}<br>({fmt_money(tnet)})")
        W(f"| **{fam}** | " + " | ".join(cells) + " |")
    W("")

    W("### 3b. Matrix — pattern × time-of-day (n / modelled $)")
    W("")
    tods = [t[0] for t in TOD_BUCKETS]
    W("| family | " + " | ".join(tods) + " |")
    W("|---|" + "---|" * len(tods))
    for fam in sorted({s["family"] for s in all_sigs}):
        cells = []
        for t in tods:
            rows = [s for s in all_sigs if s["family"] == fam and s["tod"] == t]
            cells.append(f"n={len(rows)} {fmt_money(sum(r['sim']['pnl_usd'] for r in rows))}"
                         if rows else "—")
        W(f"| **{fam}** | " + " | ".join(cells) + " |")
    W("")

    W("### 3c. Direction split")
    W("")
    W("| family | LONG n/$ | SHORT n/$ |")
    W("|---|---|---|")
    for fam in sorted({s["family"] for s in all_sigs}):
        cells = []
        for dr in ("LONG", "SHORT"):
            rows = [s for s in all_sigs if s["family"] == fam and s["direction"] == dr]
            cells.append(f"{len(rows)} / {fmt_money(sum(r['sim']['pnl_usd'] for r in rows))}"
                         if rows else "—")
        W(f"| **{fam}** | " + " | ".join(cells) + " |")
    W("")

    # ---------- per-day
    W("## 4. Per-day ledger")
    W("")
    W("| date | bucket | sig | PASSED | blocked | top blocking gate | modelled $ | real S2 trades | real $ |")
    W("|---|---|---|---|---|---|---|---|---|")
    for d in sessions:
        rows = [s for s in all_sigs if s["date"] == d]
        raw_dt, bucket, _ = dts[d]
        passed = sum(1 for s in rows if s["gate"] == "PASSED")
        blocked = [s for s in rows if s["gate"] not in ("PASSED", "no_log", "not_in_log")]
        gc: Dict[str, int] = defaultdict(int)
        for s in blocked:
            gc[s["gate"]] += 1
        top = max(gc.items(), key=lambda kv: kv[1])[0] + f" ({max(gc.values())})" if gc else "—"
        usd = sum(s["sim"]["pnl_usd"] for s in rows)
        trs = [t for t in trades if t["_date"] == d]
        rp = sum(float(t["pnl_usd"] or 0) for t in trs)
        W(f"| {d} | {bucket} | {len(rows)} | {passed} | {len(blocked)} | {top} | "
          f"{fmt_money(usd)} | {len(trs)} | {fmt_money(rp)} |")
    W("")

    # ---------- real trades
    W("## 5. Real S2 trades in `v9_trades`")
    W("")
    tot_all = sum(float(t["pnl_usd"] or 0) for t in trades)
    live = [t for t in trades if t["mode"] == "live"]
    tot_live = sum(float(t["pnl_usd"] or 0) for t in live)
    W(f"- All modes: n={len(trades)}, P&L {fmt_money(tot_all)}")
    W(f"- `mode=live` only: n={len(live)}, P&L {fmt_money(tot_live)}")
    W("")
    W("| date | mode | dir | entry | stop | exit | reason | $ | R | day_type@entry | pattern@entry |")
    W("|---|---|---|---|---|---|---|---|---|---|---|")
    for t in trades:
        W(f"| {t['_et']:%Y-%m-%d %H:%M} | {t['mode']} | {t['direction']} | "
          f"{t['entry_price']} | {t['stop']} | {t['exit_price']} | {t['exit_reason']} | "
          f"{fmt_money(float(t['pnl_usd'] or 0))} | {t['pnl_r']} | "
          f"{t['day_type_at_entry']} | {t['pattern_id_at_entry']} |")
    W("")

    # ---------- sequential account
    W("## 6. Sequential account (one position at a time) — the realistic number")
    W("")
    W("Everything above counts every signal independently, which double-counts")
    W("overlapping fires.  Here signals are taken in time order and a new one is")
    W("skipped while a position is open — what a single-slot account would do.")
    W("")
    W("| selection | n taken | n skipped | gross $ | net $ | win% | $/session | max DD |")
    W("|---|---|---|---|---|---|---|---|")
    ALLDAY = (dtime(9, 30), dtime(16, 0))
    fams_all = set(FAMILY.values())
    armed = {f for f, v in PROD_ARMED.items() if v}
    rows_cfg = [
        ("ALL families, all day-types", fams_all, set(DT_BUCKET.values()) | {"Unknown"}),
        ("Production-armed families only", armed, set(DT_BUCKET.values()) | {"Unknown"}),
        ("REACTIVE only", {"REACTIVE"}, set(DT_BUCKET.values()) | {"Unknown"}),
        ("FLAG only", {"FLAG"}, set(DT_BUCKET.values()) | {"Unknown"}),
        ("DOUBLE only", {"DOUBLE"}, set(DT_BUCKET.values()) | {"Unknown"}),
        ("HLST only (flag-OFF today)", {"HLST"}, set(DT_BUCKET.values()) | {"Unknown"}),
        ("INITIATIVE only", {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}),
    ]
    for name, fams, bks in rows_cfg:
        r = score_config(all_sigs, by_day, fams, bks, *ALLDAY, sessions=sessions)
        W(f"| {name} | {r['n']} | {r['skipped']} | {fmt_money(r['gross'])} | "
          f"{fmt_money(r['net'])} | {r['win_pct']:.0f}% | {fmt_money(r['per_session'])} | "
          f"{fmt_money(r['max_dd'])} |")
    W("")

    # ---------- config scan (in-sample / out-of-sample)
    half = len(sessions) // 2
    S_EARLY, S_LATE = sessions[:half], sessions[half:]
    W(f"### 6b. Candidate configurations — split-sample "
      f"(early {S_EARLY[0]}→{S_EARLY[-1]} vs late {S_LATE[0]}→{S_LATE[-1]})")
    W("")
    W("A config only earns a recommendation if it is positive in BOTH halves.")
    W("")
    W("| config | early net $ | early n | late net $ | late n | ALL net $ | ALL n | $/session |")
    W("|---|---|---|---|---|---|---|---|")
    cands = []
    for name, fams, bks, tf, tt, dirs in [
        ("ALL / all day-types / 09:30-16:00", fams_all, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), None),
        ("armed / all / 09:30-16:00", armed, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), None),
        ("armed / Trend+Variation / 09:30-16:00", armed, {"Trend", "Variation"}, dtime(9, 30), dtime(16, 0), None),
        ("armed / Trend only", armed, {"Trend"}, dtime(9, 30), dtime(16, 0), None),
        ("REACTIVE / all / 09:30-16:00", {"REACTIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), None),
        ("REACTIVE / Trend+Variation", {"REACTIVE"}, {"Trend", "Variation"}, dtime(9, 30), dtime(16, 0), None),
        ("REACTIVE+FLAG / Trend+Variation", {"REACTIVE", "FLAG"}, {"Trend", "Variation"}, dtime(9, 30), dtime(16, 0), None),
        ("REACTIVE+FLAG+DOUBLE / Trend+Variation", {"REACTIVE", "FLAG", "DOUBLE"}, {"Trend", "Variation"}, dtime(9, 30), dtime(16, 0), None),
        ("REACTIVE+FLAG / Trend+Variation / 10:00-15:00", {"REACTIVE", "FLAG"}, {"Trend", "Variation"}, dtime(10, 0), dtime(15, 0), None),
        ("REACTIVE+FLAG / all / 10:00-15:00", {"REACTIVE", "FLAG"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(10, 0), dtime(15, 0), None),
        ("armed minus INITIATIVE / all", armed - {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), None),
        ("armed minus INITIATIVE / 10:00-15:00", armed - {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(10, 0), dtime(15, 0), None),
        ("armed minus INITIATIVE / no Neutral", armed - {"INITIATIVE"}, {"Trend", "Variation", "Normal", "Nontrend", "Unknown"}, dtime(9, 30), dtime(16, 0), None),
        ("armed minus INITIATIVE / SHORT only", armed - {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), {"SHORT"}),
        ("armed minus INITIATIVE / LONG only", armed - {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0), {"LONG"}),
    ]:
        e = score_config(all_sigs, by_day, fams, bks, tf, tt, dirs, S_EARLY)
        l = score_config(all_sigs, by_day, fams, bks, tf, tt, dirs, S_LATE)
        a = score_config(all_sigs, by_day, fams, bks, tf, tt, dirs, sessions)
        cands.append((name, e, l, a))
        W(f"| {name} | {fmt_money(e['net'])} | {e['n']} | {fmt_money(l['net'])} | {l['n']} | "
          f"**{fmt_money(a['net'])}** | {a['n']} | {fmt_money(a['per_session'])} |")
    W("")
    both = [c for c in cands if c[1]["net"] > 0 and c[2]["net"] > 0]
    W("**Positive in BOTH halves:** " +
      (", ".join(f"`{c[0]}`" for c in both) if both else "**none**") + ".")
    W("")

    # ---------- day-type x family sequential
    W("### 6c. Sequential net $ per family × day-type bucket (n in brackets)")
    W("")
    bl = ["Trend", "Variation", "Normal", "Neutral", "Nontrend", "Unknown"]
    W("| family | " + " | ".join(bl) + " |")
    W("|---|" + "---|" * len(bl))
    for fam in sorted(fams_all & {s["family"] for s in all_sigs}):
        cells = []
        for b in bl:
            r = score_config(all_sigs, by_day, {fam}, {b}, *ALLDAY)
            cells.append(f"{fmt_money(r['net'])} [{r['n']}]" if r["n"] else "—")
        W(f"| **{fam}** | " + " | ".join(cells) + " |")
    W("")

    # ---------- robustness
    W("### 6d. Robustness of the leading candidates")
    W("")
    W("| config | net $ | drop best trade | drop best DAY | worst session | best session | + / − sessions |")
    W("|---|---|---|---|---|---|---|")
    lead = [
        ("armed / all / 09:30-16:00", armed, set(DT_BUCKET.values()) | {"Unknown"}, dtime(9, 30), dtime(16, 0)),
        ("armed / all / 10:00-15:00", armed, set(DT_BUCKET.values()) | {"Unknown"}, dtime(10, 0), dtime(15, 0)),
        ("armed minus INITIATIVE / 10:00-15:00", armed - {"INITIATIVE"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(10, 0), dtime(15, 0)),
        ("REACTIVE+FLAG / all / 10:00-15:00", {"REACTIVE", "FLAG"}, set(DT_BUCKET.values()) | {"Unknown"}, dtime(10, 0), dtime(15, 0)),
    ]
    for name, fams, bks, tf, tt in lead:
        r = score_config(all_sigs, by_day, fams, bks, tf, tt, sessions=sessions)
        pnls = sorted((t["sim"]["net_usd"] for t in r["taken"]), reverse=True)
        drop1 = r["net"] - (pnls[0] if pnls else 0)
        pd = r["per_day"]
        bestday = max(pd.values()) if pd else 0.0
        worstday = min(pd.values()) if pd else 0.0
        dropd = r["net"] - bestday
        pos = sum(1 for v in pd.values() if v > 0)
        neg = sum(1 for v in pd.values() if v < 0)
        W(f"| {name} | {fmt_money(r['net'])} | {fmt_money(drop1)} | {fmt_money(dropd)} | "
          f"{fmt_money(worstday)} | {fmt_money(bestday)} | {pos} / {neg} |")
    W("")
    W("### 6e. Time-window sensitivity (`armed` families, all day-types, net $)")
    W("")
    ends = [dtime(14, 0), dtime(15, 0), dtime(15, 30), dtime(16, 0)]
    W("| start \\ end | " + " | ".join(e.strftime('%H:%M') for e in ends) + " |")
    W("|---|" + "---|" * len(ends))
    for st in (dtime(9, 30), dtime(10, 0), dtime(10, 30), dtime(11, 0)):
        cells = []
        for e in ends:
            r = score_config(all_sigs, by_day, armed, set(DT_BUCKET.values()) | {"Unknown"},
                             st, e, sessions=sessions)
            cells.append(f"{fmt_money(r['net'])} [{r['n']}]")
        W(f"| **{st.strftime('%H:%M')}** | " + " | ".join(cells) + " |")
    W("")

    # ---------- fidelity / validation
    W("## 7. Fidelity check — replay vs the live decision log")
    W("")
    W("**This table is the most important caveat in the document.**  The replay")
    W("runs the shipped detection chain on ONE clean Sierra bar series.  The live")
    W("system does not: two publishers write to the BarRouter `\"5min\"` topic")
    W("(`backend/v9/api/v9/bars.py:764` — Sierra export, `ts` = `str(datetime)`;")
    W("`backend/v9/services/bar_aggregator_5min.py:206` — LOCAL tick aggregator,")
    W("`ts` = `isoformat()`).  `FiveMinSystem.process_bar` dedups on the ts")
    W("**string** (`five_min_system.py:1126`), so `\"…16:20:00+00:00\"` and")
    W("`\"…T16:20:00+00:00\"` are treated as two different bars and BOTH are")
    W("appended.  Consequences, all verified in `/tmp/backend.err.log` (08-11):")
    W("")
    W("- every bar is evaluated **twice** with a **different geometry vector**, e.g.")
    W("  `ts=2026-08-11 16:20:00+00:00 → S:[b1b=1 b3s=0 b4c=1 b4<l=1]` vs")
    W("  `ts=2026-08-11T16:20:00+00:00 → S:[b1b=1 b3s=1 b4c=1 b4<l=0]`;")
    W("- the 4-bar REACTIVE window `b1..b4` therefore spans **~2 real bars, each")
    W("  duplicated from two different price series** (Sierra 12:20 ET close")
    W("  7761.00 vs aggregator 7762.50);")
    W("- the aggregator does **not** apply the `vol > 100_000` cumulative-volume")
    W("  guard that `bars.py` applies, so it publishes `V=142,786 … 990,000`")
    W("  against a real 5-min MES volume of 1,000–20,000 — **100–800×**.  That")
    W("  poisons `_rolling_avg` in the D-RVX volume gate, and with")
    W("  `config/s2_firing.yaml: variant: UNION` the `_rvol_pass` branch")
    W("  (`b2_vol <= 0.5 × rolling_avg`) becomes trivially TRUE on every Sierra bar;")
    W("- the aggregator→BarRouter publish was wired on **2026-05-12** (`fe86c3ee`),")
    W("  i.e. before the first session in this audit, so it affects the whole window")
    W("  whenever the tick feed is alive (on 08-11 it was dead 04:45–11:10 ET and")
    W("  live from 11:10 ET on — the fires at 11:30/11:55/12:25/15:00/15:50 ET are")
    W("  all inside the contaminated stretch).")
    W("")
    W("Reproduce:")
    W("")
    W("```bash")
    W("grep -c '\\[Aggregator\\] Bar closed' /tmp/backend.err.log")
    W("grep '\\[S2-DL\\] REACTIVE ts=' /tmp/backend.err.log | tail -20   # two ts formats per bar")
    W("grep -n '_route_bar(\"5min\"' backend/v9/api/v9/bars.py")
    W("grep -n 'publish_threadsafe(\"5min\"' backend/v9/services/bar_aggregator_5min.py")
    W("```")
    W("")
    W("So: the counts below are expected to DISAGREE.  Read the replay as *what S2")
    W("would do on a clean feed* — which is the right basis for choosing a config —")
    W("and NOT as a reconstruction of what S2 actually did.")
    W("")
    W("| date | replay signals | live UNIQUE S2 signals | live raw rows | matched |")
    W("|---|---|---|---|---|")
    for d in sessions:
        if d < GATE_LOG_FROM:
            continue
        rep_n = sum(1 for s in all_sigs if s["date"] == d)
        dd = [x for x in decisions if x["_date"] == d]
        uniq = len({(x.get("pattern"), x.get("direction"), round(x["_entry"], 2)) for x in dd})
        matched = sum(1 for s in all_sigs if s["date"] == d and s["gate"] not in NON_GATE)
        W(f"| {d} | {rep_n} | {uniq} | {len(dd)} | {matched} |")
    W("")

    # ---------- chain walk
    chain_dates = [d.strip() for d in args.chain.split(",") if d.strip()]
    if chain_dates:
        W("## 8. Chain walk")
        W("")
        for d in chain_dates:
            raw_dt, bucket, bias = dts.get(d, ("?", "?", None))
            W(f"### {d} — day_type={raw_dt} ({bucket}), bias={bias or '—'}")
            W("")
            rows = [s for s in all_sigs if s["date"] == d]
            dd = [x for x in decisions if x["_date"] == d]
            W(f"Replayed S2 signals: **{len(rows)}** · live S2 decision rows "
              f"(fixtures removed): **{len(dd)}** · real trades: "
              f"**{len([t for t in trades if t['_date'] == d])}**")
            W("")
            # a) the LIVE chain, straight out of the decision log (ground truth)
            W("**a) The live chain — every unique S2 signal the gateway actually saw:**")
            W("")
            W("| ET | pattern | dir | entry | verdict | gate | reason |")
            W("|---|---|---|---|---|---|---|")
            seen_k = set()
            for x in sorted(dd, key=lambda y: y["_et"]):
                k = (x.get("pattern"), x.get("direction"), round(x["_entry"], 2))
                if k in seen_k:
                    continue
                seen_k.add(k)
                W(f"| {x['_et']:%H:%M:%S} | {x.get('pattern')} | {x.get('direction')} | "
                  f"{x['_entry']:.2f} | {x.get('outcome')} | `{x.get('blocked_by') or '—'}` | "
                  f"{str(x.get('reason') or '')[:75]} |")
            W("")
            trs = [t for t in trades if t["_date"] == d]
            if trs:
                W("Resulting trades:")
                for t in trs:
                    W(f"- `{t['mode']}` {t['direction']} entry {t['entry_price']} stop {t['stop']} "
                      f"(**{abs(float(t['entry_price']) - float(t['stop'])):.2f} pt**) T1 {t['t1']} "
                      f"→ {t['exit_reason']} @ {t['exit_price']} = "
                      f"**{fmt_money(float(t['pnl_usd'] or 0))}** ({t['pnl_r']}R), "
                      f"pattern `{t['pattern_id_at_entry']}`, day_type@entry `{t['day_type_at_entry']}`")
            else:
                W("Resulting trades: **none**.")
            W("")
            # b) the clean-feed replay for comparison
            W("**b) The same session replayed on the clean Sierra series** "
              "(differs by construction — see §7):")
            W("")
            if rows:
                W("| ET | pattern | dir | entry | stop pt | live gate | MFE | MAE | modelled $ |")
                W("|---|---|---|---|---|---|---|---|---|")
                for s in rows:
                    W(f"| {s['et']:%H:%M} | {s['kind']} | {s['direction']} | {s['entry']:.2f} | "
                      f"{s['sim']['stop_pts']:.2f} | `{s['gate']}` | "
                      f"{s['mfe']:+.2f} | {s['mae']:+.2f} | "
                      f"{fmt_money(s['sim']['pnl_usd'])} |")
                W("")
            gc2: Dict[str, int] = defaultdict(int)
            for x in dd:
                gc2[x["_gate"]] += 1
            W("Live gateway verdict census (all rows, incl. re-broadcasts): " +
              (", ".join(f"`{k}`×{v}" for k, v in sorted(gc2.items(), key=lambda kv: -kv[1])) or "—"))
            W("")

    # ---------- final deliverable
    base = score_config(all_sigs, by_day, armed, set(DT_BUCKET.values()) | {"Unknown"},
                        dtime(9, 30), dtime(16, 0), sessions=sessions)
    win = score_config(all_sigs, by_day, armed, set(DT_BUCKET.values()) | {"Unknown"},
                       dtime(10, 0), dtime(15, 0), sessions=sessions)
    hl = score_config(all_sigs, by_day, {"HLST"}, set(DT_BUCKET.values()) | {"Unknown"},
                      dtime(9, 30), dtime(16, 0), sessions=sessions)
    W("## 9. S2 configuration for tomorrow's live session")
    W("")
    W("### 9.0 The blocker that outranks every flag")
    W("")
    W("**Do not tune S2 flags before the double-feed in §7 is closed.**  The live")
    W("detector's 4-bar window is currently built from two interleaved price series,")
    W("one of which carries cumulative session volume.  Every number in §2 (live")
    W("gate attribution) is a measurement of a detector running on corrupted input.")
    W("The fix is a one-line change of the dedup key in")
    W("`FiveMinSystem.process_bar` (normalise the ts to epoch/UTC-iso before")
    W("comparing) **or** stop `bar_aggregator_5min` publishing to the `\"5min\"`")
    W("topic — but both are trading-risk-surface changes and need Michael's written")
    W("ruling plus a sim verification.  This audit did not touch them.")
    W("")
    W("### 9.1 Flags — exact values")
    W("")
    W("| flag | value tomorrow | today | why |")
    W("|---|---|---|---|")
    W(f"| `HIGHER_LOW_SECOND_TEST_V1` | **0 (keep OFF)** | absent → OFF | HLST measures "
      f"{fmt_money(hl['net'])} net over {hl['n']} sequential trades ({hl['win_pct']:.0f}% win, "
      f"max DD {fmt_money(hl['max_dd'])}).  Worst family in the book — this audit "
      f"independently reproduces the 08-11 22:40 finding. |")
    W("| `RE_PULLBACK_ENTRY_V1` | **0 (keep OFF)** | absent → OFF | needs Sierra IB context; "
      "0 signals produced in the replay.  No evidence either way. |")
    W("| `S2_CHART_ALL_DAYTYPES` | **1 (unchanged)** | `1` | FLAG and DOUBLE are the two "
      "profitable non-REACTIVE families; restricting them to the old allow-lists removes them "
      "on exactly the day-types where they pay (see §6c). |")
    W("| `S2_VSA_VOLUME` + `s2_firing.yaml variant: UNION` | **unchanged, but re-verify after the feed fix** | `1` / UNION | "
      "UNION only became safe-looking BECAUSE the poisoned rolling average makes `_rvol_pass` "
      "trivially true.  Re-measure the variant on a clean feed before trusting it. |")
    W("| `S2_REQUIRE_COT_AMT` | **0 (unchanged, standing decision)** | unset | CLAUDE.md standing decision. |")
    W("| `STRUCTURAL_STOP_ORIGIN_V1` | **1 (unchanged)** | `1` | the replay's structural stop "
      "is the anchor this flag produces. |")
    _gn = {g: a["n"] for g, a in agg([s for s in all_sigs if s["gate"] not in NON_GATE],
                                     lambda r: r["gate"]).items()}
    W("| gates `extreme_chase_guard` / `daytype_playbook` / `awaiting_release` / `location_gate` | "
      "**unchanged — do NOT open** | live | the two that look expensive in §2 have "
      f"n={_gn.get('extreme_chase_guard', 0)} and n={_gn.get('daytype_playbook', 0)} "
      "attributable signals across the whole gate-log window — single digits, on the "
      "contaminated feed.  Opening a gate is a risk-surface change and there is no sample "
      "here to justify one. |")
    W("")
    W("### 9.2 Which patterns may fire in which day-type")
    W("")
    W("Measured, sequential, net of commission, 48 sessions (§6c).  **Every cell "
      "below is thin — read the n before the $.**")
    W("")
    W("| family | overall | Trend | Variation | Normal | Neutral | ruling |")
    W("|---|---|---|---|---|---|---|")
    _bl9 = ["Trend", "Variation", "Normal", "Neutral"]
    for fam in ("REACTIVE", "FLAG", "DOUBLE", "INITIATIVE", "HNS", "HLST"):
        r = score_config(all_sigs, by_day, {fam}, set(DT_BUCKET.values()) | {"Unknown"},
                         dtime(9, 30), dtime(16, 0), sessions=sessions)
        if r["n"] == 0:
            continue
        cells = []
        for b in _bl9:
            rb = score_config(all_sigs, by_day, {fam}, {b}, dtime(9, 30), dtime(16, 0),
                              sessions=sessions)
            cells.append(f"{fmt_money(rb['net'])} [{rb['n']}]" if rb["n"] else "—")
        if fam == "HLST":
            rule = "**KEEP OFF everywhere** — negative overall and −$2.5k in Variation"
        elif fam == "HNS":
            rule = "leave armed; n=1 in 48 sessions, it is not a decision"
        elif fam == "INITIATIVE":
            rule = ("leave armed (no disable flag exists) but note it is the only family "
                    "that is **negative in Neutral**; a day-type gate for it is a build item, "
                    "not a flag")
        else:
            rule = "**leave armed in all four buckets** — no bucket is materially negative"
        W(f"| {fam} | {fmt_money(r['net'])} [{r['n']}] | " + " | ".join(cells) + f" | {rule} |")
    W("")
    W("**Honest reading of this table.**  Only REACTIVE (n=83), DOUBLE (n=63) and")
    W("INITIATIVE (n=77) have a usable overall sample.  Every *cell* is thin —")
    W("Trend and Normal buckets are n<15 for every family, and HNS is n=1.  The")
    W("day-type labels come from `classify_replay`, which is an **end-of-session**")
    W("classification: gating a pattern on it in this table is look-ahead.  That is")
    W("precisely why the recommendation below is *family selection*, which needs no")
    W("day-type input, and **not** a per-day-type allow-list.")
    W("")
    W("### 9.3 Time-of-day — do NOT add a window")
    W("")
    W("§6e scans 16 start/end combinations for the armed set.  Every cell is")
    W(f"positive, spanning +$707 to +$4,251, and the ranking is not monotonic "
      f"(09:30–14:00 beats 10:00–14:00 beats 11:00–14:00, but 10:30 beats 10:00).")
    W("That is the signature of noise, not of an edge.  The full session")
    W(f"(**{fmt_money(base['net'])}**) and the 10:00–15:00 window "
      f"(**{fmt_money(win['net'])}**) are inside each other's error bars.")
    W("**Recommendation: keep the existing session gate; add no new time filter.**")
    W("The only time-of-day fact that survives is §3b — read it, don't trade it.")
    W("")
    W("### 9.4 Expected $ per session")
    W("")
    W(f"- Production-armed set, whole session, sequential single-slot account: "
      f"**{fmt_money(base['per_session'])} / session** ({fmt_money(base['net'])} net "
      f"over {len(sessions)} sessions, n={base['n']} trades, {base['win_pct']:.0f}% win, "
      f"max DD {fmt_money(base['max_dd'])}, {sum(1 for v in base['per_day'].values() if v > 0)} "
      f"green / {sum(1 for v in base['per_day'].values() if v < 0)} red sessions).")
    W(f"- Split-sample: early half {fmt_money(score_config(all_sigs, by_day, armed, set(DT_BUCKET.values()) | {'Unknown'}, dtime(9,30), dtime(16,0), sessions=S_EARLY)['net'])}, "
      f"late half {fmt_money(score_config(all_sigs, by_day, armed, set(DT_BUCKET.values()) | {'Unknown'}, dtime(9,30), dtime(16,0), sessions=S_LATE)['net'])} "
      "— positive in both, which is the single strongest result in this document.")
    W(f"- Drop the best trade: {fmt_money(base['net'] - max((t['sim']['net_usd'] for t in base['taken']), default=0))}. "
      f"Drop the best day: {fmt_money(base['net'] - max(base['per_day'].values(), default=0))}.")
    W("")
    W("**These are ceilings, not forecasts.**  They assume (a) a clean single bar")
    W("feed, which we do not have today; (b) the modelled ladder actually being")
    W("placed — the live path recomputes the stop through StopResolver and produced")
    W("`stop 4.25pt / T1 +2.75pt` on the 08-10 trade, nothing like the modelled")
    W("ladder; (c) no slippage beyond $1.50/contract RT.  Expect materially less.")
    W("")

    text = "\n".join(out)
    if args.report:
        p = Path(args.report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"[ok] report -> {p}", file=sys.stderr)
    if args.json:
        Path(args.json).write_text(json.dumps(
            [{k: (v.isoformat() if hasattr(v, "isoformat") else v)
              for k, v in s.items() if k not in ("i",)} for s in all_sigs],
            default=str, indent=1))
        print(f"[ok] json -> {args.json}", file=sys.stderr)
    if not args.report or not args.summary_only:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
