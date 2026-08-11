#!/usr/bin/env python3
"""Consolidated replay acceptance for C2 / C3 / C4 / E2 (2026-08-11).

READ-ONLY: never writes to the DB, never touches ~/SierraChart_Data, never
enables a flag in the running backend. It only reads bars/trades and prints.

  C2  RE_PULLBACK_ENTRY_V1        — retest of a broken IB edge
  C3  extreme_chase_guard         — env-tunable calibration grid sweep
  C4  NEUTRAL_PLAYBOOK_V1         — edges-only / POC / opposite-edge / time-stop
  E2  S6_TREND_BE_DELAY_V1        — later (structure) BE on Trend days

Usage:
  python3 scripts/replay_c2_c3_c4_e2.py --part all
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import OrderedDict, defaultdict
from datetime import time as dtime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── .env must be loaded: without it the day-type classifier mislabels days ──
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
MES = 5.0            # $ per point per contract
TICK = 0.25
SINCE = "2026-07-15"
UNTIL = "2026-08-10"
RTH_OPEN, RTH_END = dtime(9, 30), dtime(16, 15)


# ══════════════════════════════════════════════════════════════════════
# Shared data loading
# ══════════════════════════════════════════════════════════════════════
def load_days(since: str = SINCE, until: str = UNTIL) -> "OrderedDict[str, List[Dict]]":
    """RTH 5-min bars per ET trading date from v9_bars_5min_woodies."""
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies "
        "WHERE ts >= :a AND ts < :b ORDER BY ts",
        {"a": f"{since}T00:00:00+00:00", "b": f"{until}T23:59:59+00:00"})
    days: "OrderedDict[str, List[Dict]]" = OrderedDict()
    for r in rows or []:
        et = r["ts"].astimezone(ET)
        if not (RTH_OPEN <= et.time() < RTH_END):
            continue
        days.setdefault(et.strftime("%Y-%m-%d"), []).append({
            "et": et, "hhmm": et.strftime("%H:%M"),
            "o": float(r["open"]), "h": float(r["high"]),
            "l": float(r["low"]), "c": float(r["close"]),
            "v": int(r["volume"] or 0),
        })
    # drop stub days (need at least the IB)
    return OrderedDict((d, b) for d, b in days.items() if len(b) >= 13)


def ib_of(bars: List[Dict]) -> Tuple[float, float]:
    return (max(b["h"] for b in bars[:12]), min(b["l"] for b in bars[:12]))


def struct_stop(bars_so_far: List[Dict], direction: str,
                lookback: int = 3, lo: float = 3.0, hi: float = 12.0) -> float:
    """Structure stop: beyond the extreme of the last `lookback` closed bars."""
    win = bars_so_far[-lookback:] if len(bars_so_far) >= lookback else bars_so_far
    entry = bars_so_far[-1]["c"]
    if direction == "LONG":
        s = min(b["l"] for b in win) - 2 * TICK
        risk = min(max(entry - s, lo), hi)
        return round((entry - risk) * 4) / 4
    s = max(b["h"] for b in win) + 2 * TICK
    risk = min(max(s - entry, lo), hi)
    return round((entry + risk) * 4) / 4


def sim_two_contracts(entry: float, stop: float, t1: float, t2: float,
                      direction: str, future: List[Dict],
                      be_after_t1: bool = True,
                      max_bars: Optional[int] = None) -> Dict[str, Any]:
    """2-contract simulation: C1 -> T1, C2 -> T2, stop->BE after T1.
    Conservative: within a bar, the stop is assumed hit before the target."""
    sign = 1.0 if direction == "LONG" else -1.0
    pnl_pts = 0.0
    open_c = 2
    cur_stop = stop
    t1_done = False
    outcome = []
    bars_held = 0
    for i, b in enumerate(future):
        if max_bars is not None and i >= max_bars:
            break
        bars_held = i + 1
        h, l = b["h"], b["l"]
        hit_stop = (l <= cur_stop) if direction == "LONG" else (h >= cur_stop)
        if hit_stop:
            pnl_pts += open_c * (cur_stop - entry) * sign
            outcome.append("BE" if (t1_done and abs(cur_stop - entry) < 0.3) else "STOP")
            open_c = 0
            break
        if not t1_done:
            if (h >= t1) if direction == "LONG" else (l <= t1):
                pnl_pts += 1 * (t1 - entry) * sign
                open_c -= 1
                t1_done = True
                outcome.append("T1")
                if be_after_t1:
                    cur_stop = entry
        if t1_done and open_c > 0:
            if (h >= t2) if direction == "LONG" else (l <= t2):
                pnl_pts += open_c * (t2 - entry) * sign
                outcome.append("T2")
                open_c = 0
                break
    if open_c > 0:
        last_c = future[bars_held - 1]["c"] if bars_held else entry
        pnl_pts += open_c * (last_c - entry) * sign
        outcome.append("MTM")
    return {"pnl_pts": round(pnl_pts, 2), "pnl_usd": round(pnl_pts * MES, 2),
            "outcome": "+".join(outcome) or "NONE", "bars_held": bars_held}


def fmt_money(x: float) -> str:
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


# ══════════════════════════════════════════════════════════════════════
# C2 — RE_PULLBACK_ENTRY_V1
# ══════════════════════════════════════════════════════════════════════
C2_COOLDOWN_BARS = 6
C2_MAX_PER_DAY = 2


def part_c2(days) -> Dict[str, Any]:
    from backend.v9.systems.five_min.patterns.pullback_retest import (
        detect_pullback_retest)

    trades: List[Dict] = []
    for d, bars in days.items():
        ibh, ibl = ib_of(bars)
        last_fire = -99
        n_day = 0
        for i in range(12, len(bars)):
            if i - last_fire < C2_COOLDOWN_BARS or n_day >= C2_MAX_PER_DAY:
                continue
            direction, conf, info = detect_pullback_retest(
                bars[:i + 1], ib_high=ibh, ib_low=ibl,
                ib_locked=True, session_min=i * 5)
            if direction is None:
                continue
            entry, stop = info["entry_price"], info["stop"]
            t1, t2 = info["t1"], info["t2"]
            sim = sim_two_contracts(entry, stop, t1, t2, direction, bars[i + 1:])
            rr = abs(t1 - entry) / max(abs(entry - stop), 0.25)
            trades.append({
                "date": d, "time": bars[i]["hhmm"], "dir": direction,
                "entry": entry, "stop": stop, "t1": t1, "t2": t2,
                "rr_t1": round(rr, 2), "conf": round(conf, 2),
                "ib_w": info["ib_width"], **sim})
            last_fire = i
            n_day += 1
    return {"trades": trades}


# ══════════════════════════════════════════════════════════════════════
# C3 — extreme_chase_guard calibration grid
# ══════════════════════════════════════════════════════════════════════
BLOCK_RE = re.compile(
    r"^\[(?P<ts>[\d\-T:]+)[+-]\d\d:\d\d\].*BLOCKED (?P<pat>\S+) (?P<dir>LONG|SHORT) "
    r"@(?P<px>[\d.]+) gate=extreme_chase_guard")


def _family(pattern: str) -> str:
    from backend.v9.systems.daytype_position_gate import _pattern_family
    try:
        return _pattern_family(pattern) or "OTHER"
    except Exception:
        return "OTHER"


def c3_candidates(days) -> List[Dict]:
    """Universe = (A) chase-guard-blocked entries from the ops logs +
    (B) trades that actually fired (v9_trades, live preferred over shadow)."""
    cands: List[Dict] = []
    seen = set()

    # (A) ops logs
    for p in sorted((ROOT / "docs" / "reports").glob("OPS_LOG_2026-0*.md")):
        for line in p.read_text(errors="ignore").splitlines():
            m = BLOCK_RE.match(line.strip())
            if not m:
                continue
            ts = m.group("ts")
            d, hhmmss = ts.split("T")
            if not (SINCE <= d <= UNTIL) or d not in days:
                continue
            hh, mm = int(hhmmss[:2]), int(hhmmss[3:5])
            bar_hhmm = f"{hh:02d}:{(mm // 5) * 5:02d}"
            key = (d, bar_hhmm, m.group("pat"), m.group("dir"), m.group("px"))
            if key in seen:
                continue
            seen.add(key)
            cands.append({"date": d, "hhmm": bar_hhmm, "pattern": m.group("pat"),
                          "dir": m.group("dir"), "entry": float(m.group("px")),
                          "src": "BLOCKED", "actual_pnl": None})

    # (B) real trades
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT id,mode,direction,entry_ts,entry_price,pnl_usd,pattern_id_at_entry "
        "FROM v9_trades WHERE entry_ts>=:a AND entry_ts<:b AND entry_price IS NOT NULL "
        "ORDER BY entry_ts", {"a": f"{SINCE}T00:00:00+00:00",
                              "b": f"{UNTIL}T23:59:59+00:00"})
    by_key: Dict[Tuple, Dict] = {}
    for r in rows or []:
        et = r["entry_ts"].astimezone(ET)
        d = et.strftime("%Y-%m-%d")
        if d not in days or not (RTH_OPEN <= et.time() < RTH_END):
            continue
        bar_hhmm = f"{et.hour:02d}:{(et.minute // 5) * 5:02d}"
        k = (d, bar_hhmm, r["pattern_id_at_entry"] or "?", r["direction"],
             float(r["entry_price"]))
        prev = by_key.get(k)
        if prev is None or (r["mode"] == "live" and prev["mode"] != "live"):
            by_key[k] = {"date": d, "hhmm": bar_hhmm,
                         "pattern": r["pattern_id_at_entry"] or "?",
                         "dir": r["direction"], "entry": float(r["entry_price"]),
                         "src": "FIRED", "mode": r["mode"],
                         "actual_pnl": float(r["pnl_usd"]) if r["pnl_usd"] is not None else None}
    cands.extend(by_key.values())

    # enrich with session context + uniform simulated outcome
    for c in cands:
        bars = days[c["date"]]
        idx = None
        for i, b in enumerate(bars):
            if b["hhmm"] <= c["hhmm"]:
                idx = i
            else:
                break
        if idx is None:
            c["skip"] = True
            continue
        upto = bars[:idx + 1]
        c["idx"] = idx
        c["n_bars"] = len(upto)
        c["sess_high"] = max(b["h"] for b in upto)
        c["sess_low"] = min(b["l"] for b in upto)
        c["open0"] = bars[0]["o"]
        c["ib_w"] = (max(b["h"] for b in bars[:12]) - min(b["l"] for b in bars[:12])
                     if len(bars) >= 12 else 0.0)
        c["family"] = _family(c["pattern"])
        c["dist"] = round((c["sess_high"] - c["entry"]) if c["dir"] == "LONG"
                          else (c["entry"] - c["sess_low"]), 2)
        hi_i = max(range(len(upto)), key=lambda i: upto[i]["h"])
        lo_i = min(range(len(upto)), key=lambda i: upto[i]["l"])
        c["bars_since_extreme"] = (len(upto) - 1 - hi_i) if c["dir"] == "LONG" \
            else (len(upto) - 1 - lo_i)
        # pullback presence in the last 3 bars (guard's second check)
        rec = upto[-3:]
        c["has_pullback_3"] = (any(b["l"] <= c["sess_high"] - 3.0 for b in rec)
                               if c["dir"] == "LONG"
                               else any(b["h"] >= c["sess_low"] + 3.0 for b in rec))
        st = struct_stop(upto, c["dir"])
        risk = abs(c["entry"] - st)
        t1 = c["entry"] + (risk if c["dir"] == "LONG" else -risk)
        t2 = c["entry"] + (2 * risk if c["dir"] == "LONG" else -2 * risk)
        sim = sim_two_contracts(c["entry"], st, t1, t2, c["dir"], bars[idx + 1:])
        c["sim_stop"], c["sim_t1"], c["sim_t2"] = st, round(t1, 2), round(t2, 2)
        c["sim_pnl"] = sim["pnl_usd"]
        c["sim_outcome"] = sim["outcome"]
        # blended: measured P&L where the trade really ran, simulated only for
        # the counterfactual (entries the guard actually blocked live).
        c["blend_pnl"] = (c["actual_pnl"] if (c["src"] == "FIRED"
                                              and c["actual_pnl"] is not None)
                          else c["sim_pnl"])
    return [c for c in cands if not c.get("skip")]


def c3_guard_blocks(c: Dict, base: float, frac: float, scope: str,
                    min_bars: int = 6, pb_min: float = 3.0) -> Tuple[bool, str]:
    """Faithful re-implementation of the gateway's extreme_chase_guard.
    (_live_leg is live-only state and is not modelled — noted in the report.)"""
    fam = c["family"]
    in_scope = (fam == "CONT") or (scope == "CONT+REV" and fam == "REV")
    if not in_scope:
        return (False, "out-of-scope")
    min_dist = max(base, frac * c["ib_w"])
    if c["n_bars"] < min_bars:
        return (False, "maturity-bypass")
    bypass = False
    try:
        from backend.v9.systems.release_gate import trend_bypass
        bypass = bool(trend_bypass(c["open0"], c["entry"], c["dir"]))
    except Exception:
        bypass = False
    if bypass and c["dist"] < min_dist:      # K3d tip-revocation
        bypass = False
    if bypass:
        return (False, "trend-bypass")
    if c["dist"] < min_dist:
        return (True, f"dist {c['dist']:.2f} < {min_dist:.2f}")
    if not c["has_pullback_3"]:
        return (True, f"no pullback >= {pb_min:.1f}")
    return (False, "pass")


def part_c3(days) -> Dict[str, Any]:
    cands = c3_candidates(days)
    grid = []
    for scope in ("CONT", "CONT+REV"):
        for base in (3.0, 4.0, 5.0, 6.0):
            for frac in (0.0, 0.15, 0.20, 0.25, 0.30):
                passed = [c for c in cands
                          if not c3_guard_blocks(c, base, frac, scope)[0]]
                net = sum(c["sim_pnl"] for c in passed)
                net_actual = sum(c["blend_pnl"] for c in passed)
                grid.append({"scope": scope, "base": base, "frac": frac,
                             "min_bars": 6,
                             "n_pass": len(passed), "n_block": len(cands) - len(passed),
                             "net_sim": round(net, 2), "net_actual": round(net_actual, 2)})
    # second sweep: session-maturity bars (CHASE_MIN_SESSION_BARS) at the
    # current distance defaults — the "maturity" lever from workorder T5.
    grid2 = []
    for scope in ("CONT", "CONT+REV"):
        for mb in (6, 7, 8, 9, 10, 12):
            passed = [c for c in cands
                      if not c3_guard_blocks(c, 6.0, 0.30, scope, min_bars=mb)[0]]
            grid2.append({"scope": scope, "base": 6.0, "frac": 0.30, "min_bars": mb,
                          "n_pass": len(passed), "n_block": len(cands) - len(passed),
                          "net_sim": round(sum(c["sim_pnl"] for c in passed), 2),
                          "net_actual": round(sum(c["blend_pnl"] for c in passed), 2)})
    return {"cands": cands, "grid": grid, "grid2": grid2}


# ══════════════════════════════════════════════════════════════════════
# C4 — NEUTRAL_PLAYBOOK_V1
# ══════════════════════════════════════════════════════════════════════
C4_TIME_STOP_BARS = 12
C4_CONTRACTS = 2
C4_COOLDOWN = 6
C4_MAX_PER_DAY = 3


def developing_profile(bars: List[Dict]) -> Tuple[float, float, float]:
    """Developing POC / VAH / VAL from 5-min bars (volume spread over range)."""
    hist: Dict[float, float] = defaultdict(float)
    for b in bars:
        lo, hi = b["l"], b["h"]
        n = max(int(round((hi - lo) / TICK)) + 1, 1)
        share = (b["v"] or 1) / n
        for k in range(n):
            hist[round(lo + k * TICK, 2)] += share
    if not hist:
        return (0.0, 0.0, 0.0)
    levels = sorted(hist)
    poc = max(levels, key=lambda p: hist[p])
    total = sum(hist.values())
    target = 0.70 * total
    lo_i = hi_i = levels.index(poc)
    acc = hist[poc]
    while acc < target and (lo_i > 0 or hi_i < len(levels) - 1):
        up = hist[levels[hi_i + 1]] if hi_i < len(levels) - 1 else -1
        dn = hist[levels[lo_i - 1]] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1
            acc += max(up, 0)
        else:
            lo_i -= 1
            acc += max(dn, 0)
    return (poc, levels[hi_i], levels[lo_i])


def neutral_days(days) -> Dict[str, str]:
    from backend.v9.db.read import read_all
    rows = read_all("SELECT date, day_type FROM v9_day_type_history "
                    "WHERE date>=:a AND date<=:b", {"a": SINCE, "b": UNTIL})
    out = {}
    for r in rows or []:
        d = str(r["date"])
        if d in days and str(r["day_type"] or "").startswith("Neutral"):
            out[d] = r["day_type"]
    return out


def part_c4(days) -> Dict[str, Any]:
    nd = neutral_days(days)
    trades: List[Dict] = []
    for d, label in sorted(nd.items()):
        bars = days[d]
        last_fire, n_day = -99, 0
        for i in range(12, len(bars) - 1):
            if i - last_fire < C4_COOLDOWN or n_day >= C4_MAX_PER_DAY:
                continue
            upto = bars[:i + 1]
            poc, vah, val = developing_profile(upto)
            b = bars[i]
            sh = max(x["h"] for x in upto)
            sl = min(x["l"] for x in upto)
            direction = None
            if b["h"] >= vah and b["c"] < vah:
                direction = "SHORT"
            elif b["l"] <= val and b["c"] > val:
                direction = "LONG"
            if direction is None:
                continue
            entry = b["c"]
            if direction == "SHORT":
                stop = max(sh, b["h"]) + 1.0
                t1, t2 = poc, val
                if not (t1 < entry and t2 < entry):
                    continue
            else:
                stop = min(sl, b["l"]) - 1.0
                t1, t2 = poc, vah
                if not (t1 > entry and t2 > entry):
                    continue
            risk = abs(entry - stop)
            if risk > 12.0 or risk < 1.0:
                continue
            sim = sim_two_contracts(entry, stop, t1, t2, direction,
                                    bars[i + 1:], max_bars=C4_TIME_STOP_BARS)
            trades.append({"date": d, "label": label, "time": b["hhmm"],
                           "dir": direction, "entry": entry, "stop": round(stop, 2),
                           "t1_poc": round(t1, 2), "t2_edge": round(t2, 2),
                           "risk": round(risk, 2), "rr_t1": round(abs(t1 - entry) / risk, 2),
                           **sim})
            last_fire, n_day = i, n_day + 1
    # what actually happened on those days
    from backend.v9.db.read import read_all
    actual: Dict[str, float] = {}
    for d in nd:
        rows = read_all(
            "SELECT mode, pnl_usd FROM v9_trades WHERE (entry_ts AT TIME ZONE "
            "'America/New_York')::date = :d AND pnl_usd IS NOT NULL", {"d": d})
        live = [float(r["pnl_usd"]) for r in rows or [] if r["mode"] == "live"]
        sh_ = [float(r["pnl_usd"]) for r in rows or [] if r["mode"] != "live"]
        actual[d] = round(sum(live) if live else sum(sh_), 2)
    return {"trades": trades, "days": nd, "actual": actual}


# ══════════════════════════════════════════════════════════════════════
# E2 — S6_TREND_BE_DELAY_V1
# ══════════════════════════════════════════════════════════════════════
def part_e2(days) -> Dict[str, Any]:
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT id,mode,direction,entry_ts,entry_price,stop,t1,t2,t1_hit_ts,"
        "t2_hit_ts,exit_price,exit_reason,pnl_usd,day_type_at_entry,"
        "pattern_id_at_entry FROM v9_trades WHERE entry_ts>=:a AND entry_ts<:b "
        "AND day_type_at_entry LIKE 'Trend%' AND t1_hit_ts IS NOT NULL "
        "ORDER BY entry_ts", {"a": f"{SINCE}T00:00:00+00:00",
                              "b": f"{UNTIL}T23:59:59+00:00"})
    out: List[Dict] = []
    for r in rows or []:
        et = r["entry_ts"].astimezone(ET)
        d = et.strftime("%Y-%m-%d")
        if d not in days:
            continue
        bars = days[d]
        entry = float(r["entry_price"])
        direction = r["direction"]
        t1 = float(r["t1"]) if r["t1"] is not None else None
        if t1 is None:
            continue
        t1et = r["t1_hit_ts"].astimezone(ET) if r["t1_hit_ts"] else None
        if t1et is None:
            continue
        t1_hhmm = f"{t1et.hour:02d}:{(t1et.minute // 5) * 5:02d}"
        idx = None
        for i, b in enumerate(bars):
            if b["hhmm"] <= t1_hhmm:
                idx = i
            else:
                break
        if idx is None or idx + 1 >= len(bars):
            continue
        # runner target stays intact under E2 — only the STOP handling changes.
        tgt = float(r["t2"]) if r["t2"] is not None else None
        if tgt is not None and abs(tgt - t1) < 0.01:
            tgt = None
        # actual runner result (1 contract): BE when exit ~= entry after T1
        actual_exit = float(r["exit_price"]) if r["exit_price"] is not None else None
        if r["t2_hit_ts"] and tgt is not None:
            actual_exit, actual_tag = tgt, "T2"
        elif actual_exit is not None:
            actual_tag = "BE" if abs(actual_exit - entry) <= 0.3 else (r["exit_reason"] or "exit")
        else:
            actual_exit, actual_tag = bars[-1]["c"], "open/MTM"
        actual_runner = ((actual_exit - entry) if direction == "LONG"
                         else (entry - actual_exit))
        # E2 alternative: no BE move. Stop = structure trail (last 2 closed
        # bars, never widens); the T2 target is untouched.
        cur = struct_stop(bars[:idx + 1], direction, lookback=2)
        alt_exit, alt_tag = None, "MTM"
        for j in range(idx + 1, len(bars)):
            b = bars[j]
            if direction == "LONG" and b["l"] <= cur:
                alt_exit, alt_tag = cur, "TRAIL_STOP"
                break
            if direction == "SHORT" and b["h"] >= cur:
                alt_exit, alt_tag = cur, "TRAIL_STOP"
                break
            if tgt is not None:
                if (b["h"] >= tgt) if direction == "LONG" else (b["l"] <= tgt):
                    alt_exit, alt_tag = tgt, "T2"
                    break
            new = struct_stop(bars[:j + 1], direction, lookback=2)
            cur = max(cur, new) if direction == "LONG" else min(cur, new)
        if alt_exit is None:
            alt_exit = bars[-1]["c"]
        alt_runner = ((alt_exit - entry) if direction == "LONG"
                      else (entry - alt_exit))
        out.append({
            "id": r["id"], "mode": r["mode"], "date": d, "time": et.strftime("%H:%M"),
            "pattern": r["pattern_id_at_entry"], "dir": direction, "entry": entry,
            "day_type": r["day_type_at_entry"],
            "actual_runner_pts": round(actual_runner, 2), "actual_tag": actual_tag,
            "alt_runner_pts": round(alt_runner, 2), "alt_tag": alt_tag,
            "alt_exit": round(alt_exit, 2),
            "delta_usd": round((alt_runner - actual_runner) * MES, 2),
        })
    return {"rows": out}


# ══════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all",
                    choices=["all", "c2", "c3", "c4", "e2"])
    args = ap.parse_args()

    days = load_days()
    print(f"=== REPLAY ACCEPTANCE C2/C3/C4/E2 — {SINCE} .. {UNTIL} ===")
    print(f"trading days: {len(days)}  ({', '.join(days)})")
    print()

    if args.part in ("all", "c2"):
        r = part_c2(days)
        t = r["trades"]
        print("── C2 RE_PULLBACK_ENTRY_V1 ──")
        print(f"n triggers = {len(t)}   NET = {fmt_money(sum(x['pnl_usd'] for x in t))}")
        print(f"{'date':<11}{'time':<7}{'dir':<6}{'entry':>9}{'stop':>9}{'t1':>9}"
              f"{'t2':>9}{'rr':>6}{'outcome':>14}{'pnl$':>10}")
        for x in t:
            print(f"{x['date']:<11}{x['time']:<7}{x['dir']:<6}{x['entry']:>9.2f}"
                  f"{x['stop']:>9.2f}{x['t1']:>9.2f}{x['t2']:>9.2f}{x['rr_t1']:>6.2f}"
                  f"{x['outcome']:>14}{x['pnl_usd']:>10.2f}")
        acc10 = [x for x in t if x["date"] == "2026-08-10" and abs(x["entry"] - 7791.25) <= 3]
        acc07 = [x for x in t if x["date"] == "2026-08-07" and x["time"] in ("10:45", "10:50", "10:55")]
        print(f"ACCEPTANCE 2026-08-10 ~7791.25 : {'PASS ' + str(acc10) if acc10 else 'FAIL (no trigger)'}")
        print(f"ACCEPTANCE 2026-08-07 10:45/10:55: {'PASS' if acc07 else 'FAIL (no trigger)'}")
        print()

    if args.part in ("all", "c3"):
        r = part_c3(days)
        cands, grid = r["cands"], r["grid"]
        print("── C3 extreme_chase_guard calibration ──")
        print(f"candidate universe = {len(cands)} "
              f"(BLOCKED-in-log {sum(1 for c in cands if c['src'] == 'BLOCKED')}, "
              f"FIRED {sum(1 for c in cands if c['src'] == 'FIRED')})")
        base_row = [g for g in grid if g["scope"] == "CONT" and g["base"] == 6.0
                    and g["frac"] == 0.30][0]
        print(f"LIVE default (CONT, base 6.0, frac 0.30, min_bars 6): "
              f"n_pass={base_row['n_pass']} net_sim={fmt_money(base_row['net_sim'])} "
              f"net_blend={fmt_money(base_row['net_actual'])}")
        print()
        # acceptance cases
        AC = {
            "block_0807_zlr_7783.75": lambda c: (c["date"] == "2026-08-07"
                                                 and abs(c["entry"] - 7783.75) < .01
                                                 and c["dir"] == "LONG"),
            "block_0810_655_7795": lambda c: (c["date"] == "2026-08-10"
                                              and abs(c["entry"] - 7795.0) < .01
                                              and c["dir"] == "LONG"),
            "allow_0810_7777.75": lambda c: (c["date"] == "2026-08-10"
                                             and abs(c["entry"] - 7777.75) < .01),
            "allow_0810_7778.25": lambda c: (c["date"] == "2026-08-10"
                                             and abs(c["entry"] - 7778.25) < .01),
        }
        print(f"{'scope':<10}{'base':>6}{'frac':>6}{'pass':>6}{'block':>7}"
              f"{'net_sim$':>12}{'net_blend$':>13}  acceptance(b0807/b0810/a7777/a7778)")
        for g in grid:
            marks = []
            ok_all = True
            for name, sel in AC.items():
                targets = [c for c in cands if sel(c)]
                if not targets:
                    marks.append("-")
                    continue
                blocked = all(c3_guard_blocks(c, g["base"], g["frac"], g["scope"])[0]
                              for c in targets)
                want_block = name.startswith("block")
                good = (blocked == want_block)
                ok_all = ok_all and good
                marks.append("Y" if good else "n")
            print(f"{g['scope']:<10}{g['base']:>6.1f}{g['frac']:>6.2f}{g['n_pass']:>6}"
                  f"{g['n_block']:>7}{g['net_sim']:>12.2f}{g['net_actual']:>13.2f}  "
                  f"{'/'.join(marks)}{'  <== ALL PASS' if ok_all else ''}")
        print()
        print("maturity sweep (base 6.0 / frac 0.30 fixed, CHASE_MIN_SESSION_BARS varies):")
        print(f"{'scope':<10}{'min_bars':>9}{'pass':>6}{'block':>7}{'net_sim$':>12}"
              f"{'net_blend$':>13}  acceptance(b0807/b0810/a7777/a7778)")
        for g in r["grid2"]:
            marks, ok_all = [], True
            for name, sel in AC.items():
                targets = [c for c in cands if sel(c)]
                if not targets:
                    marks.append("-"); continue
                blocked = all(c3_guard_blocks(c, g["base"], g["frac"], g["scope"],
                                              min_bars=g["min_bars"])[0] for c in targets)
                good = (blocked == name.startswith("block"))
                ok_all = ok_all and good
                marks.append("Y" if good else "n")
            print(f"{g['scope']:<10}{g['min_bars']:>9}{g['n_pass']:>6}{g['n_block']:>7}"
                  f"{g['net_sim']:>12.2f}{g['net_actual']:>13.2f}  "
                  f"{'/'.join(marks)}{'  <== ALL PASS' if ok_all else ''}")
        print()
        print("acceptance-case detail:")
        for name, sel in AC.items():
            for c in [c for c in cands if sel(c)]:
                print(f"  {name:<24} {c['date']} {c['hhmm']} {c['pattern']:<22}"
                      f"fam={c['family']:<6} dist={c['dist']:>6.2f} ib_w={c['ib_w']:>6.2f} "
                      f"bars_since_extreme={c['bars_since_extreme']:>2} "
                      f"sim_pnl={c['sim_pnl']:>8.2f} actual={c['actual_pnl']}")
        print()

    if args.part in ("all", "c4"):
        r = part_c4(days)
        t = r["trades"]
        print("── C4 NEUTRAL_PLAYBOOK_V1 ──")
        print(f"neutral days in window: {r['days']}")
        print(f"n triggers = {len(t)}   NET = {fmt_money(sum(x['pnl_usd'] for x in t))}")
        print(f"{'date':<11}{'time':<7}{'dir':<6}{'entry':>9}{'stop':>9}{'T1=POC':>9}"
              f"{'T2=edge':>9}{'rr':>6}{'outcome':>14}{'pnl$':>10}")
        for x in t:
            print(f"{x['date']:<11}{x['time']:<7}{x['dir']:<6}{x['entry']:>9.2f}"
                  f"{x['stop']:>9.2f}{x['t1_poc']:>9.2f}{x['t2_edge']:>9.2f}"
                  f"{x['rr_t1']:>6.2f}{x['outcome']:>14}{x['pnl_usd']:>10.2f}")
        print("actual P&L on those days (live if any, else shadow):", r["actual"])
        d10 = [x for x in t if x["date"] == "2026-08-10"]
        print(f"ACCEPTANCE 2026-08-10 (Neutral_Center): n={len(d10)} "
              f"NET={fmt_money(sum(x['pnl_usd'] for x in d10))} "
              f"(actual that day {r['actual'].get('2026-08-10')})")
        print()

    if args.part in ("all", "e2"):
        r = part_e2(days)
        rows = r["rows"]
        print("── E2 S6_TREND_BE_DELAY_V1 ──")
        print(f"n Trend-day trades that reached T1 = {len(rows)}")
        print(f"{'id':>5} {'date':<11}{'time':<7}{'mode':<7}{'dir':<6}{'pattern':<24}"
              f"{'actual_run':>11}{'tag':>10}{'alt_run':>9}{'alt_tag':>12}{'delta$':>10}")
        for x in rows:
            print(f"{x['id']:>5} {x['date']:<11}{x['time']:<7}{x['mode']:<7}{x['dir']:<6}"
                  f"{str(x['pattern'])[:23]:<24}{x['actual_runner_pts']:>11.2f}"
                  f"{x['actual_tag'][:9]:>10}{x['alt_runner_pts']:>9.2f}"
                  f"{x['alt_tag']:>12}{x['delta_usd']:>10.2f}")
        res = [x for x in rows if x["actual_tag"] != "open/MTM"]
        unres = [x for x in rows if x["actual_tag"] == "open/MTM"]
        be = [x for x in res if x["actual_tag"] == "BE"]
        live = [x for x in res if x["mode"] == "live"]
        print(f"excluded (no recorded exit, actual unmeasurable): n={len(unres)} "
              f"ids={[x['id'] for x in unres]}")
        print(f"TOTAL delta (resolved n={len(res)})   = "
              f"{fmt_money(sum(x['delta_usd'] for x in res))}")
        print(f"TOTAL delta (live only n={len(live)}) = "
              f"{fmt_money(sum(x['delta_usd'] for x in live))}")
        print(f"TOTAL delta (BE-clipped n={len(be)})  = "
              f"{fmt_money(sum(x['delta_usd'] for x in be))}")
        for d in ("2026-08-03", "2026-08-04"):
            sub = [x for x in res if x["date"] == d]
            print(f"  {d}: n={len(sub)} delta={fmt_money(sum(x['delta_usd'] for x in sub))}")
        acc = [x for x in res if x["date"] in ("2026-08-03", "2026-08-04")]
        print(f"ACCEPTANCE 08-03+08-04: n={len(acc)} "
              f"delta={fmt_money(sum(x['delta_usd'] for x in acc))}")
        print()


if __name__ == "__main__":
    main()
