#!/usr/bin/env python3
"""LEG-EXEMPTION replay — quantify, per gate, what a leg exemption would have paid.

Michael's question (2026-08-11, Trend_DD / leg DOWN, 0 trades, 252pt of MFE left
on the table): the LEG_RIDE exemption already covers cont_trend_filter /
location_gate / extreme_chase / lsma_flat. Should `awaiting_release` (release
gate) and `zone_limit_late_entry` also become leg-exempt?

READ-ONLY. Reads:
  * ~/SierraChart_Data/v9_export/gateway_decisions.jsonl  (the real blocks)
  * v9_bars_5min_woodies                                  (canonical Sierra bars)
Writes nothing but stdout / an optional --json dump.

Method
  1. Every blocked decision on the target dates (fixture rows entry==7600 dropped,
     one signal per gate/pattern/direction per 5-min bar).
  2. `leg_state.detect_leg` on the 10 closed RTH bars up to that bar — exactly the
     window the live `_live_leg()` helper uses.
  3. Forward MFE/MAE over the next 12 bars, and a 4-contract P&L simulation:
       CURRENT  : C1 +3pt, C2 1R, C3 2R, C4 4R runner, stop 8pt (structural
                  fallback — the jsonl carries no stop), BE after T1(1R).
       STEP     : stop = max(4pt, 0.6 x median step), targets 0.5 / 1.0 / 1.5 x
                  step, C4 runner, BE after the 1.0x leg.
     Conservative intrabar order: STOP is checked before targets inside a bar.
  4. Two aggregations: PER-SIGNAL (upper bound, overlapping) and SEQUENTIAL
     (one trade at a time — the realistic number).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POINT_VALUE = 5.0          # MES $/pt/contract
CONTRACTS = 4
FWD_BARS = 12
FIXTURE_ENTRY = 7600.0
DEFAULT_STOP_PTS = 8.0     # structural fallback (no stop recorded in the jsonl)
COMMISSION_RT = 1.50       # $/contract round-turn (reported separately)

TREND_DAYS = ["2026-08-03", "2026-08-04", "2026-08-11"]
ROTATION_DAYS = ["2026-08-06", "2026-08-07", "2026-08-10"]
# The ONLY sessions in the whole decision log that carry real (non-fixture)
# zone_limit_late_entry blocks — the six August days have zero, so the gate has
# to be judged on this cohort or not at all.
ZONE_LIMIT_DAYS = ["2026-07-23", "2026-07-24", "2026-07-28", "2026-07-31"]


# ---------------------------------------------------------------- env / inputs
def load_env(repo_root: str) -> None:
    """Load .env exactly like scripts/flag_guard.py parse_env (inline comments are
    NOT stripped there either — mirror it so replay == live)."""
    path = os.path.join(repo_root, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def read_decisions(path: str, dates: set[str]) -> list[dict]:
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("ts") or ""
        if ts[:10] not in dates:
            continue
        if not r.get("blocked_by"):
            continue
        e = r.get("entry")
        if e is None or float(e) == FIXTURE_ENTRY:
            continue          # test-fixture rows
        r["_dt"] = datetime.fromisoformat(ts)
        out.append(r)
    out.sort(key=lambda r: r["_dt"])
    return out


def read_bars(dates: list[str]) -> dict[str, list[dict]]:
    from backend.v9.db.read import read_all
    bars: dict[str, list[dict]] = {}
    for d in dates:
        rows = read_all(
            "SELECT ts, open, high, low, close, volume, lsma_value, cci_14 "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d "
            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "AND (ts AT TIME ZONE 'America/New_York')::time <= '16:00' "
            "ORDER BY ts", {"d": d})
        bs = []
        for r in rows or []:
            ts = r["ts"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            bs.append({
                "ts": ts.astimezone(timezone.utc),
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
                "volume": float(r["volume"] or 0),
                "lsma_value": None if r["lsma_value"] is None else float(r["lsma_value"]),
                "cci_14": None if r["cci_14"] is None else float(r["cci_14"]),
            })
        bars[d] = bs
    return bars


# ------------------------------------------------------------------ structure
ZZ_THR = 3.0               # zigzag reversal threshold (pts) — --zigzag-thr


def zigzag_swings(bars: list[dict], thr: float | None = None) -> list[float]:
    """Magnitudes of alternating swings (>= thr pts). Causal — caller slices."""
    thr = ZZ_THR if thr is None else thr
    if len(bars) < 3:
        return []
    piv = [bars[0]["close"]]
    direction = 0
    ext = bars[0]["close"]
    for b in bars[1:]:
        if direction >= 0 and b["high"] > ext:
            ext = b["high"]
        if direction <= 0 and b["low"] < ext:
            ext = b["low"]
        if direction >= 0 and b["low"] <= ext - thr:
            piv.append(ext)
            direction, ext = -1, b["low"]
        elif direction <= 0 and b["high"] >= ext + thr:
            piv.append(ext)
            direction, ext = 1, b["high"]
    piv.append(ext)
    return [abs(b - a) for a, b in zip(piv, piv[1:]) if abs(b - a) >= thr]


def median_step(bars: list[dict]) -> float:
    sw = zigzag_swings(bars)
    if len(sw) >= 2:
        return float(statistics.median(sw))
    rng = [b["high"] - b["low"] for b in bars[-10:]] or [4.0]
    return max(4.0, 3.0 * float(statistics.median(rng)))


# ---------------------------------------------------------------- simulation
def simulate(entry: float, direction: str, fwd: list[dict],
             stop_pts: float, tgt_pts: list[float], be_after_idx: int) -> dict:
    """4 contracts, one target each (last = runner exited on the final bar).
    Conservative: inside a bar the STOP is checked first. BE after the target at
    index `be_after_idx` (0-based) fills."""
    sign = 1.0 if direction == "LONG" else -1.0
    stop = entry - sign * stop_pts
    targets = [entry + sign * t for t in tgt_pts]
    open_c = [True] * CONTRACTS
    pnl_pts = 0.0
    legs = []
    be_done = False
    for b in fwd:
        hi, lo = b["high"], b["low"]
        # stop first (conservative)
        hit_stop = (lo <= stop) if direction == "LONG" else (hi >= stop)
        if hit_stop:
            for i in range(CONTRACTS):
                if open_c[i]:
                    open_c[i] = False
                    pnl_pts += (stop - entry) * sign
                    legs.append(("STOP" if not be_done else "BE", round((stop - entry) * sign, 2)))
            break
        for i in range(CONTRACTS - 1):          # runner has no fixed target
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
    bars_used = len(fwd)
    return {"pnl_pts": round(pnl_pts, 2), "pnl_usd": round(pnl_pts * POINT_VALUE, 2),
            "legs": legs, "stop_pts": round(stop_pts, 2),
            "targets": [round(t, 2) for t in tgt_pts], "bars": bars_used,
            "be_hit": be_done}


def build_signals(decisions: list[dict], bars: dict[str, list[dict]]) -> list[dict]:
    from backend.v9.systems.leg_state import detect_leg
    seen = set()
    sigs = []
    for r in decisions:
        d = r["ts"][:10]
        bs = bars.get(d) or []
        if not bs:
            continue
        dt = r["_dt"].astimezone(timezone.utc)
        closed = [b for b in bs if b["ts"] + timedelta(minutes=5) <= dt]
        if len(closed) < 6:
            continue                      # not enough RTH history for a leg call
        bar_ts = closed[-1]["ts"]
        gate = r["blocked_by"]
        pat = r.get("pattern")
        dirn = str(r.get("direction") or "").upper()
        key = (d, gate, pat, dirn, bar_ts)
        if key in seen:
            continue                      # one signal per gate/pattern/dir/bar
        seen.add(key)
        leg, age, why = detect_leg(closed[-10:])
        want = "UP" if dirn == "LONG" else "DOWN"
        entry = float(r["entry"])
        fwd = [b for b in bs if b["ts"] > bar_ts][:FWD_BARS]
        if not fwd:
            continue
        mfe = max((b["high"] - entry) if dirn == "LONG" else (entry - b["low"]) for b in fwd)
        mae = max((entry - b["low"]) if dirn == "LONG" else (b["high"] - entry) for b in fwd)
        step = median_step(closed)
        sess_open = bs[0]["open"]
        disp = closed[-1]["close"] - sess_open
        # release-gate trend bypass, as the live gate computes it
        rg_thr = float(os.getenv("RELEASE_TREND_BYPASS_PTS", "15"))
        rg_bypass = abs(disp) >= rg_thr and (
            (disp < 0 and dirn == "SHORT") or (disp > 0 and dirn == "LONG"))
        cur = simulate(entry, dirn, fwd, DEFAULT_STOP_PTS,
                       [3.0, DEFAULT_STOP_PTS, 2 * DEFAULT_STOP_PTS, 4 * DEFAULT_STOP_PTS], 1)
        s_stop = max(4.0, 0.6 * step)
        alt = simulate(entry, dirn, fwd, s_stop,
                       [0.5 * step, 1.0 * step, 1.5 * step, 3.0 * step], 1)
        sigs.append({
            "date": d, "ts": r["ts"], "bar_ts": bar_ts.isoformat(), "gate": gate,
            "pattern": pat, "direction": dirn, "entry": entry, "system": r.get("system"),
            "reason": (r.get("reason") or "")[:120],
            "leg": leg, "leg_age": age, "leg_why": why, "with_leg": leg == want,
            "disp": round(disp, 2), "rg_trend_bypass": rg_bypass,
            # alternative qualifier: WITH the session displacement (the shape
            # release_gate.trend_bypass and the cont-trend displacement bypass
            # already use). 10pt = the level the 08-11 tape actually reached.
            "with_disp": abs(disp) >= 10.0 and (
                (disp < 0 and dirn == "SHORT") or (disp > 0 and dirn == "LONG")),
            "mfe": round(mfe, 2), "mae": round(mae, 2), "step": round(step, 2),
            "cur": cur, "alt": alt,
            "_bar_ts": bar_ts, "_fwd_end": fwd[-1]["ts"],
        })
    return sigs


def sequential(sigs: list[dict], key: str) -> dict:
    """One trade at a time: skip a signal that starts while the previous
    simulated trade is still inside its 12-bar window."""
    tot = 0.0
    n = 0
    wins = 0
    busy_until = {}
    for s in sorted(sigs, key=lambda x: x["_bar_ts"]):
        d = s["date"]
        if busy_until.get(d) and s["_bar_ts"] <= busy_until[d]:
            continue
        tot += s[key]["pnl_usd"]
        n += 1
        wins += 1 if s[key]["pnl_usd"] > 0 else 0
        busy_until[d] = s["_fwd_end"]
    return {"n": n, "net": round(tot, 2), "wins": wins,
            "net_after_comm": round(tot - n * CONTRACTS * COMMISSION_RT, 2)}


def agg(sigs: list[dict], key: str) -> dict:
    net = round(sum(s[key]["pnl_usd"] for s in sigs), 2)
    wins = sum(1 for s in sigs if s[key]["pnl_usd"] > 0)
    return {"n": len(sigs), "net": net, "wins": wins,
            "avg": round(net / len(sigs), 2) if sigs else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=os.path.expanduser(
        "~/SierraChart_Data/v9_export/gateway_decisions.jsonl"))
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--zigzag-thr", type=float, default=3.0,
                    help="zigzag reversal threshold in pts for the median step size")
    ap.add_argument("--detail-day", default=None,
                    help="print every unique signal of this date")
    args = ap.parse_args()
    global ZZ_THR
    ZZ_THR = args.zigzag_thr

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_env(repo)
    os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")

    all_days = TREND_DAYS + ROTATION_DAYS + ZONE_LIMIT_DAYS
    dec = read_decisions(args.jsonl, set(all_days))
    bars = read_bars(all_days)
    sigs = build_signals(dec, bars)

    print(f"decisions(blocked, non-fixture)={len(dec)}  unique signals={len(sigs)}")
    for d in all_days:
        bs = bars.get(d) or []
        if bs:
            print(f"  {d}: bars={len(bs)} open={bs[0]['open']} close={bs[-1]['close']} "
                  f"disp={bs[-1]['close']-bs[0]['open']:+.2f} step={median_step(bs):.2f} "
                  f"blocks={sum(1 for s in sigs if s['date']==d)}")

    groups = {"TREND": TREND_DAYS, "ROTATION": ROTATION_DAYS,
              "ZL_COHORT": ZONE_LIMIT_DAYS}
    print("\n=== PER GATE ===")
    rows = []
    for gname, days in groups.items():
        gsigs = [s for s in sigs if s["date"] in days]
        gates = sorted({s["gate"] for s in gsigs})
        for gate in gates:
            gs = [s for s in gsigs if s["gate"] == gate]
            wl = [s for s in gs if s["with_leg"]]
            nl = [s for s in gs if not s["with_leg"]]
            wd = [s for s in gs if s["with_disp"]]
            r = {
                "group": gname, "gate": gate, "n_all": len(gs), "n_with_leg": len(wl),
                "n_with_disp": len(wd), "disp_seq": sequential(wd, "cur"),
                "disp_seq_step": sequential(wd, "alt"),
                "disp_per_signal": agg(wd, "cur"),
                "cur_per_signal": agg(wl, "cur"), "alt_per_signal": agg(wl, "alt"),
                "cur_seq": sequential(wl, "cur"), "alt_seq": sequential(wl, "alt"),
                "noleg_cur_per_signal": agg(nl, "cur"),
                "mfe_median": round(statistics.median([s["mfe"] for s in wl]), 2) if wl else None,
                "mae_median": round(statistics.median([s["mae"] for s in wl]), 2) if wl else None,
            }
            rows.append(r)
            print(f"[{gname}] {gate}: n={len(gs)} with_leg={len(wl)} "
                  f"| CUR seq net=${r['cur_seq']['net']:.2f} (n={r['cur_seq']['n']}, "
                  f"w={r['cur_seq']['wins']}) per-signal=${r['cur_per_signal']['net']:.2f} "
                  f"| STEP seq net=${r['alt_seq']['net']:.2f} per-signal=${r['alt_per_signal']['net']:.2f} "
                  f"| MFE med={r['mfe_median']} MAE med={r['mae_median']} "
                  f"| no-leg CUR per-signal=${r['noleg_cur_per_signal']['net']:.2f} "
                  f"(n={len(nl)}) || WITH-DISP n={len(wd)} seq=${r['disp_seq']['net']:.2f} "
                  f"(n={r['disp_seq']['n']}, w={r['disp_seq']['wins']}) "
                  f"STEPseq=${r['disp_seq_step']['net']:.2f}")

    print("\n=== QUALIFIER TOTALS (sequential, one trade at a time) ===")
    print("  what an exemption keyed on WITH-LEG vs WITH-DISPLACEMENT(>=10pt) pays,")
    print("  across every gate, plus the 'take every block' ceiling.")
    for gname, days in groups.items():
        ds = [s for s in sigs if s["date"] in days]
        for label, sel in (("ALL blocks", ds),
                           ("with-LEG", [s for s in ds if s["with_leg"]]),
                           ("with-DISP", [s for s in ds if s["with_disp"]])):
            c, a = sequential(sel, "cur"), sequential(sel, "alt")
            print(f"  [{gname:<9}] {label:<11} pool={len(sel):<3} | CUR seq n={c['n']:<3} "
                  f"net=${c['net']:>9.2f} w={c['wins']:<3} | STEP seq net=${a['net']:>9.2f} "
                  f"w={a['wins']}")
    print("  per-day (all blocks, sequential):")
    for d in all_days:
        ds = [s for s in sigs if s["date"] == d]
        if not ds:
            continue
        c, a = sequential(ds, "cur"), sequential(ds, "alt")
        print(f"    {d}: pool={len(ds):<3} taken={c['n']:<3} CUR=${c['net']:>9.2f} "
              f"(w={c['wins']}) STEP=${a['net']:>9.2f} (w={a['wins']}) "
              f"with_leg={sum(1 for s in ds if s['with_leg'])} "
              f"with_disp={sum(1 for s in ds if s['with_disp'])}")

    print(f"\n=== STOP/TARGET SIZING — CURRENT vs STEP (zigzag thr={ZZ_THR}) ===")
    print("  CURRENT = stop 8pt, C1 +3pt / C2 1R / C3 2R / C4 4R runner, BE after 1R")
    print("  STEP    = stop max(4, 0.6*step), targets 0.5/1.0/1.5*step, C4 runner")
    for gname, days in groups.items():
        gs = [s for s in sigs if s["date"] in days and s["with_leg"]]
        if not gs:
            continue
        c, a = sequential(gs, "cur"), sequential(gs, "alt")
        cp, ap_ = agg(gs, "cur"), agg(gs, "alt")
        print(f"  [{gname:<9}] with-leg n={len(gs):<3} step_med="
              f"{statistics.median([s['step'] for s in gs]):.2f} | "
              f"CUR seq=${c['net']:>9.2f} (n={c['n']}, w={c['wins']}) per-sig=${cp['net']:>9.2f} "
              f"| STEP seq=${a['net']:>9.2f} (n={a['n']}, w={a['wins']}) per-sig=${ap_['net']:>9.2f}")

    print("\n=== RELEASE-GATE TREND-BYPASS SENSITIVITY (awaiting_release only) ===")
    print("  the leg exemption is one lever; RELEASE_TREND_BYPASS_PTS is the other.")
    ar = [s for s in sigs if s["gate"] == "awaiting_release"]
    for thr in (15.0, 12.0, 10.0, 8.0, 6.0):
        for gname, days in (("TREND", TREND_DAYS), ("ROTATION", ROTATION_DAYS)):
            gs = [s for s in ar if s["date"] in days]
            rel = [s for s in gs
                   if abs(s["disp"]) >= thr and ((s["disp"] < 0 and s["direction"] == "SHORT")
                                                 or (s["disp"] > 0 and s["direction"] == "LONG"))]
            seq = sequential(rel, "cur")
            seq_alt = sequential(rel, "alt")
            print(f"  thr={thr:>5} [{gname:<8}] released={len(rel):<3}/{len(gs):<3} "
                  f"CUR seq net=${seq['net']:>9.2f} (n={seq['n']}, w={seq['wins']})  "
                  f"STEP seq net=${seq_alt['net']:>9.2f}")

    print("\n=== RAW BLOCK CENSUS (before dedupe; fixture rows separated) ===")
    raw = defaultdict(lambda: [0, 0])
    for line in open(args.jsonl, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("ts", "")[:10] not in set(all_days) or not r.get("blocked_by"):
            continue
        idx = 1 if (r.get("entry") is not None and float(r["entry"]) == FIXTURE_ENTRY) else 0
        raw[(r["ts"][:10], r["blocked_by"])][idx] += 1
    for (d, g), (real, fix) in sorted(raw.items()):
        print(f"  {d} {g:<24} real={real:<4} fixture(7600)={fix}")

    print("\n=== CANDIDATE GATES — why no leg / would trend-bypass have fired? ===")
    for s in sorted(sigs, key=lambda x: x["ts"]):
        if s["gate"] not in ("awaiting_release", "zone_limit_late_entry"):
            continue
        print(f"{s['date']} {s['ts'][11:19]} {s['direction']:<5} {s['pattern']:<18} "
              f"leg={str(s['leg']):<5} with_leg={int(s['with_leg'])} disp={s['disp']:+7.2f} "
              f"rg_bypass={int(s['rg_trend_bypass'])} MFE={s['mfe']:<6} MAE={s['mae']:<6} "
              f"CUR=${s['cur']['pnl_usd']:<8} | {s['leg_why'][:60]}")

    if args.detail_day:
        print(f"\n=== ALL UNIQUE SIGNALS — {args.detail_day} ===")
        for s in sorted(sigs, key=lambda x: x["ts"]):
            if s["date"] != args.detail_day:
                continue
            print(f"{s['ts'][11:19]} {s['gate']:<22} {str(s['pattern']):<18} "
                  f"{s['direction']:<5} @{s['entry']:<9} leg={str(s['leg']):<5} "
                  f"with_leg={int(s['with_leg'])} MFE={s['mfe']:<6} MAE={s['mae']:<6} "
                  f"CUR=${s['cur']['pnl_usd']:<8} STEP=${s['alt']['pnl_usd']:<8}")

    print("\n=== SIGNAL DETAIL (with-leg only) ===")
    for s in sorted(sigs, key=lambda x: (x["gate"], x["ts"])):
        if not s["with_leg"]:
            continue
        print(f"{s['date']} {s['ts'][11:19]} {s['gate']:<22} {s['pattern']:<18} "
              f"{s['direction']:<5} @{s['entry']:<9} leg={s['leg']}({s['leg_age']}) "
              f"MFE={s['mfe']:<6} MAE={s['mae']:<6} step={s['step']:<5} "
              f"CUR=${s['cur']['pnl_usd']:<8} STEP=${s['alt']['pnl_usd']:<8}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump({"rows": rows, "signals": [
                {k: v for k, v in s.items() if not k.startswith("_")} for s in sigs]},
                fh, indent=1, default=str)
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
