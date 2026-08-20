#!/usr/bin/env python3
"""F4 / G2 replay — every setup A1 ever killed, re-routed through the REAL gateway.

`STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1` (A1) has been live since 2026-08-11. In
that whole window the decisions archive records exactly THREE blocks (two
opportunities — the 08-14 ZLR pushed twice). This script replays every one of
them through `TradingGateway.route_setup` with `TREND_STEP_STRUCT_EXEMPT_V1`
OFF and then ON, and — for anything that starts routing — measures what the
trade was worth against the real 5-minute bars.

Honesty rules this script obeys (CLAUDE.md Rule 1 / Rule 2 / Rule 5):
  * The population is READ from the archive, never hand-listed.
  * The reason string produced with the flag OFF must match the archived string
    BYTE FOR BYTE, otherwise the replay is not replaying the live event and the
    script says so and exits non-zero.
  * The risk is DERIVED from the archived c1 (which is entry ± 1R after the
    R-fallback), not assumed.
  * Bars come from `v9_bars_5min_woodies` (the canonical live table); no bars,
    no P&L claim.
  * Nothing is written anywhere. No env is changed outside this process.

Usage:
    python3 scripts/replay_f4_stair_struct_exempt.py
    python3 scripts/replay_f4_stair_struct_exempt.py --export-dir ~/SierraChart_Data/v9_export
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# .env first — the backend reads DATABASE_URL/BRIDGE_TOKEN at import time.
_ENV = os.path.join(ROOT, ".env")
if os.path.exists(_ENV):
    for _line in open(_ENV, encoding="utf-8", errors="replace"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

MES_PER_PT = 5.0
CONTRACTS = 4
BLOCK = "structural_targets_wrong_side"

# Fractions of the impulse the TREND_STEP model uses (scripts/replay_trend_step_entry.py
# §P: T0_PT / T1_FRAC / T2_FRAC / T3_FRAC), and the 08-19 impulse as measured there.
T0_PT, T1_FRAC, T2_FRAC, T3_FRAC = 3.0, 0.45, 0.80, 1.30
STAIR_0819_IMPULSE = 21.5
STAIR_0819_LEG_STOP = 7744.25


# ────────────────────────────────── population ────────────────────────────────
def load_wrong_side_decisions(export_dir: Path) -> List[Dict]:
    """Every A1 block the gateway ever wrote, from the live feed + archive + bak."""
    files: List[Path] = []
    for pat in ("gateway_decisions.jsonl", "gateway_decisions*.jsonl.bak"):
        files += sorted(export_dir.glob(pat))
    arch = export_dir / "decisions_archive"
    if arch.is_dir():
        files += sorted(arch.glob("*.jsonl"))
    seen, out = set(), []
    for f in files:
        try:
            for line in f.read_text(errors="replace").splitlines():
                if BLOCK not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("blocked_by") != BLOCK:
                    continue
                key = (d.get("ts"), d.get("entry"), d.get("direction"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(d)
        except Exception as e:
            print(f"  ! unreadable {f}: {e}")
    out.sort(key=lambda d: str(d.get("ts")))
    return out


_REASON_RX = re.compile(
    r"wrong side of (?P<dir>LONG|SHORT) entry=(?P<entry>[-\d.]+)\s*"
    r"\(c1=(?P<c1>[-\d.]+), c2=(?P<c2>[-\d.]+), c3=(?P<c3>[-\d.]+), "
    r"day_type=(?P<dt>[A-Za-z_]+)\)")


def parse_reason(reason: str) -> Optional[Dict]:
    m = _REASON_RX.search(reason or "")
    if not m:
        return None
    g = m.groupdict()
    entry, c1 = float(g["entry"]), float(g["c1"])
    return {"direction": g["dir"], "entry": entry, "day_type": g["dt"],
            "c1": c1, "c2": float(g["c2"]), "c3": float(g["c3"]),
            # after _fix_side, c1 == entry ± 1R  =>  R is recoverable exactly
            "risk": round(abs(c1 - entry), 4)}


# ─────────────────────────────── the real gateway ─────────────────────────────
def _isolated_gateway(day_type: str, pattern: str, entry: float, direction: str):
    """A real TradingGateway with every gate that is NOT A1 turned off, so the
    only verdict this replay can observe is A1's own."""
    import zoneinfo
    from backend.v9.gateway import trading_gateway as tg
    import inspect

    src = inspect.getsource(tg)
    under_test = {"TREND_STEP_STRUCT_EXEMPT_V1", "DAYTYPE_TARGETS_STRUCTURAL",
                  "STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1"}
    for flag in set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"\s*,\s*"0"\s*\)', src)):
        if flag not in under_test:
            os.environ[flag] = "0"
    for flag in ("RELEASE_ENTRY_GATE_V1", "NEWS_BLACKOUT_V1", "EXTREME_CHASE_GUARD",
                 "DIRECTION_COMPASS_V1", "OPENING_WINDOW_FIRE_V1",
                 "PATTERN_LOSS_BREAKER_V1", "S2_ADAPTIVE_THRESHOLDS_V1",
                 "LIVE_EXECUTION_V1", "LIVE_TRADING_ARMED", "DEMO_EXECUTION_ENABLED"):
        os.environ[flag] = "0"
    os.environ["DAYTYPE_TARGETS_STRUCTURAL"] = "1"
    os.environ["STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1"] = "1"

    class _TZBoom:                       # force the IB-lock check to fail-open
        def __init__(self, *a, **k):
            raise RuntimeError("replay: force IB-locked fail-open")

    from backend.v9.services import feed_watchdog as _fw
    from backend.v9.services import kill_switch as _ks
    _fw.is_feed_alive = lambda *a, **k: (True, "replay")
    _ks.is_engaged = lambda *a, **k: (False, None)
    zoneinfo.ZoneInfo = _TZBoom
    tg.is_within_firing_window = lambda: True
    tg.extract_g1_entry_context = lambda cc: {"day_type_at_entry": day_type}
    tg.resolve_pattern_id = lambda setup, g1: pattern

    # Structural levels: ALL behind the entry. That is the archived verdict
    # (all_wrong_side) restated as inputs — and it is verified, not assumed:
    # the OFF run below must reproduce the archived reason string byte for byte.
    if direction == "LONG":
        tpo = {"ib_high": entry - 5, "ib_low": entry - 45, "poc": entry - 20,
               "vah": entry - 9, "val": entry - 35, "ib_width": 40.0}
    else:
        tpo = {"ib_high": entry + 45, "ib_low": entry + 25, "poc": entry + 35,
               "vah": entry + 40, "val": entry + 30, "ib_width": 20.0}

    gw = tg.TradingGateway()
    gw._execute_shadow = lambda *a, **k: {"trade_id": "replay"}
    gw._capture_cross_context = lambda: {
        "day_type_machine": {"day_type": day_type},
        "woodies_system": {"trend_state": "GREEN"},
        "tpo_system": dict(tpo),
    }
    return gw


def route_once(setup: Dict, day_type: str, pattern: str, exempt: bool) -> Dict:
    os.environ["TREND_STEP_STRUCT_EXEMPT_V1"] = "1" if exempt else "0"
    gw = _isolated_gateway(day_type, pattern, setup["entry_price"], setup["direction"])
    return gw.route_setup(dict(setup), 4)


# ───────────────────────────────── the real bars ──────────────────────────────
def bars_after(entry_ts_iso: str, limit: int = 60) -> List[Dict]:
    """RTH 5-min bars of that session, strictly after the decision timestamp."""
    try:
        from backend.v9.db.read import read_all
    except Exception as e:
        print(f"  ! DB unavailable ({e}) — no P&L claim will be made")
        return []
    ts = datetime.fromisoformat(entry_ts_iso.replace("Z", "+00:00"))
    rows = read_all(
        "SELECT ts, high AS h, low AS l, close AS c FROM v9_bars_5min_woodies "
        "WHERE ts > :a AND ts <= :b "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "AND (ts AT TIME ZONE 'America/New_York')::time <= '16:00' "
        "ORDER BY ts ASC",
        {"a": ts.isoformat(), "b": (ts + timedelta(hours=6)).isoformat()}) or []
    return [{"h": float(r["h"]), "l": float(r["l"]), "c": float(r["c"]),
             "ts": str(r["ts"])} for r in rows[:limit]]


def simulate(direction: str, entry: float, stop: float, targets: List[float],
             future: List[Dict], be_after_t1: bool = True) -> Dict:
    """The TREND_STEP execution model, verbatim from scripts/replay_trend_step_entry.py:
    4 contracts, C1->T0 C2->T1 C3->T2 C4->T3, BE after T1, stop wins an
    ambiguous bar, MTM on the last bar."""
    sign = 1.0 if direction == "LONG" else -1.0
    open_c, cur_stop, nxt = CONTRACTS, stop, 0
    pnl, legs, held = 0.0, [], 0
    mfe, mae = 0.0, 0.0
    for k, b in enumerate(future):
        held = k + 1
        mfe = max(mfe, sign * ((b["h"] if direction == "LONG" else b["l"]) - entry))
        mae = min(mae, sign * ((b["l"] if direction == "LONG" else b["h"]) - entry))
        hit_stop = (b["l"] <= cur_stop) if direction == "LONG" else (b["h"] >= cur_stop)
        if hit_stop:
            pnl += open_c * (cur_stop - entry) * sign
            legs.append("BE" if abs(cur_stop - entry) < 0.26 else "STOP")
            open_c = 0
            break
        while nxt < len(targets) and open_c > 0:
            t = targets[nxt]
            if (b["h"] >= t) if direction == "LONG" else (b["l"] <= t):
                pnl += 1 * (t - entry) * sign
                open_c -= 1
                legs.append(f"T{nxt}")
                nxt += 1
                if nxt == 2 and be_after_t1:
                    cur_stop = entry
            else:
                break
        if open_c == 0:
            break
    if open_c > 0:
        last = future[held - 1]["c"] if held else entry
        pnl += open_c * (last - entry) * sign
        legs.append(f"MTM{open_c}")
    return {"pnl_pts": round(pnl, 2), "pnl_usd": round(pnl * MES_PER_PT, 2),
            "outcome": "+".join(legs) or "NONE", "bars": held,
            "mfe": round(mfe, 2), "mae": round(mae, 2)}


# ────────────────────────────────────── main ──────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir",
                    default=os.path.expanduser("~/SierraChart_Data/v9_export"))
    args = ap.parse_args()

    print("F4/G2 replay — every A1 kill, re-routed through the real gateway")
    print("=" * 78)
    decisions = load_wrong_side_decisions(Path(args.export_dir))
    if not decisions:
        print("NO-GO: no archived structural_targets_wrong_side decisions found.")
        return 1
    print(f"archived A1 blocks: {len(decisions)}  "
          f"({args.export_dir} + decisions_archive/)\n")

    fidelity_ok = True
    total_delta = 0.0
    for d in decisions:
        parsed = parse_reason(d.get("reason") or "")
        if not parsed:
            print(f"  ! unparsable reason, skipped: {d.get('reason')}")
            fidelity_ok = False
            continue
        pattern = d.get("pattern") or "?"
        is_stair = pattern.upper() == "TREND_STEP"
        entry, risk = parsed["entry"], parsed["risk"]
        direction, day_type = parsed["direction"], parsed["day_type"]
        sign = 1.0 if direction == "LONG" else -1.0
        live_stop = entry - sign * risk

        print(f"── {d['ts']}  {pattern} {direction} @{entry}  "
              f"day_type={day_type}  R={risk}pt  "
              f"{'STAIR' if is_stair else 'non-stair'}")

        setup = {
            "firing_system": 4, "direction": direction,
            "classification": pattern, "entry_price": entry, "stop": live_stop,
            "t1": entry + sign * max(3.0, risk), "metadata": {"pattern": pattern},
        }
        if is_stair:
            setup["stop_source"] = "TREND_STEP_LEG"
            setup["metadata"]["stop_source"] = "TREND_STEP_LEG"

        off = route_once(setup, day_type, pattern, exempt=False)
        same = off.get("reason") == d.get("reason")
        fidelity_ok = fidelity_ok and same and off.get("blocked_by") == BLOCK
        print(f"   flag OFF : blocked_by={off.get('blocked_by')}  "
              f"reason byte-identical to archive: {'YES' if same else 'NO'}")
        if not same:
            print(f"      archive: {d.get('reason')}")
            print(f"      replay : {off.get('reason')}")

        on = route_once(setup, day_type, pattern, exempt=True)
        print(f"   flag ON  : blocked_by={on.get('blocked_by')}"
              + ("  ← EXEMPTED, routes" if on.get("blocked_by") is None else "  (still blocked)"))
        if is_stair and on.get("blocked_by") is not None:
            fidelity_ok = False
            print("      NO-GO: a stair did not route with the exemption on")
        if (not is_stair) and on.get("blocked_by") != BLOCK:
            fidelity_ok = False
            print("      NO-GO: the non-stair SAVER lost its protection")

        # What was it worth? Real bars only — the leg ladder for the stair,
        # and (for the non-stair) the stop/target it actually carried.
        future = bars_after(d["ts"])
        if not future:
            print("   (no bars for this session — no P&L claim)\n")
            continue
        if is_stair:
            imp = STAIR_0819_IMPULSE
            stop = STAIR_0819_LEG_STOP if abs(entry - 7747.0) < 0.01 else live_stop
            targets = [round((entry + sign * x) * 4) / 4 for x in
                       (T0_PT, T1_FRAC * imp, T2_FRAC * imp, T3_FRAC * imp)]
            sim = simulate(direction, entry, stop, targets, future)
            total_delta += sim["pnl_usd"]
            print(f"   leg ladder stop={stop} targets={targets}")
            print(f"   REPLAY   : {sim['outcome']}  {sim['pnl_usd']:+.2f}  "
                  f"(MFE {sim['mfe']:+.2f}pt / MAE {sim['mae']:+.2f}pt, "
                  f"{sim['bars']} bars)  ← delta of exempting this one\n")
        else:
            targets = [entry + sign * x for x in (T0_PT, risk, 2 * risk, 3 * risk)]
            sim = simulate(direction, entry, live_stop, targets, future)
            print(f"   REPLAY   : would have been {sim['outcome']} "
                  f"{sim['pnl_usd']:+.2f} — STILL BLOCKED, so this is the "
                  f"SAVE the exemption preserves\n")

    print("=" * 78)
    print(f"delta of the exemption over the whole A1 era: {total_delta:+.2f} "
          f"(4 contracts, ${MES_PER_PT}/pt, before commission)")
    print("FIDELITY: " + ("PASS — every OFF run reproduced the archived block "
                          "byte-for-byte, stairs route ON, non-stairs stay blocked"
                          if fidelity_ok else
                          "FAIL — see the NO-GO lines above"))
    return 0 if fidelity_ok else 1


if __name__ == "__main__":
    sys.exit(main())
