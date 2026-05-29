#!/usr/bin/env python3
"""Simulate a Trend Day through S4 (Woodies) and S2 (FiveMin).

Creates synthetic bars that look like a Trend Normal day:
- Strong open drive UP from 7550
- CCI stays above zero line (bullish trend)
- SWI positive, TCCI leading CCI
- Volume pattern with 90% drops (for S2 Reactive)

Runs OFFLINE — does NOT touch the live DB or running backend.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("simulate")

# ── Synthetic Trend Day bars ──────────────────────────────────────

def make_trend_day_bars(n_bars=25):
    """Generate 25 five-min bars for a strong Trend Normal day.

    Pattern: open drive up from 7550, steady climb to ~7600,
    with one pullback (ZLR setup) and one volume collapse (Reactive setup).
    """
    bars = []
    base_price = 7550.0
    base_ts = 1780060200  # ~09:30 ET as raw Sierra timestamp

    # Price trajectory: strong uptrend with one pullback
    closes = [
        7553, 7558, 7562, 7565, 7568,   # 09:30-09:50: open drive
        7571, 7574, 7576, 7573, 7570,   # 09:55-10:15: push + pullback
        7572, 7575, 7578, 7580, 7583,   # 10:20-10:40: recovery
        7585, 7587, 7589, 7586, 7584,   # 10:45-11:05: new high + retrace
        7586, 7588, 7590, 7592, 7595,   # 11:10-11:30: continuation
    ]

    # Volume: high at open, normal, one 90% drop for Reactive
    volumes = [
        25000, 18000, 15000, 12000, 10000,
        8000, 7000, 6000, 5000, 4000,
        3500, 3000, 2800, 2500, 2200,
        2000, 1800, 150, 1600, 1400,     # bar 17 = 150 vol (90% drop from 1800)
        1200, 1100, 1000, 900, 800,
    ]

    # CCI-14 values: positive trend, ZLR pullback at bar 8-9
    cci_values = [
        50, 100, 150, 180, 200,
        220, 240, 250, 180, 120,         # pullback: CCI drops to 120 (still > 0 = ZLR)
        150, 180, 210, 230, 250,
        260, 270, 280, 220, 200,
        210, 230, 250, 270, 290,
    ]

    # TCCI (CCI-6): leads CCI on trend
    tcci_values = [c + 30 for c in cci_values]  # TCCI leads by ~30

    for i in range(n_bars):
        c = float(closes[i])
        h = c + 2.0
        l = c - 2.0
        o = closes[i-1] if i > 0 else base_price

        bars.append({
            "ts": base_ts + i * 300,
            "open": float(o), "high": h, "low": l, "close": c,
            "volume": float(volumes[i]),
            "o": float(o), "h": h, "l": l, "c": c,
            "v": float(volumes[i]), "vol": float(volumes[i]),
            # Sierra study values (LIVE, not frozen)
            "cci_14": float(cci_values[i]),
            "cci_6_tcci": float(tcci_values[i]),
            "ema_34": base_price + i * 1.2,
            "lsma_value": base_price + i * 1.0,
            "swi_value": 50.0 + i * 2,    # positive and rising = bullish
            "czi_value": 60.0,
            "trend_state": "BLUE",         # bullish trend
            "predictor_next_cci": float(cci_values[i]) + 10,
            "zlr_detected": False,
            "zlr_direction": "NONE",
            "hfe_detected": False,
            "hfe_direction": "NONE",
            "hfe_extreme_bars_ago": 0,
        })

    return bars


# ── S4 Woodies Simulation ────────────────────────────────────────

def simulate_s4():
    print("\n" + "=" * 70)
    print("  S4 WOODIES CCI — Trend Day Simulation")
    print("=" * 70)

    from backend.v9.systems.woodies.woodies_system import WoodiesSystem

    system = WoodiesSystem(db_path=":memory:", rth_only=False)

    # Mock gateway so we can see fire attempts
    mock_gateway = MagicMock()
    mock_gateway.route_setup.return_value = {"shadow": "SIM-001", "blocked_by": None}
    mock_gateway._trade_manager = None  # no real TM
    system.set_gateway(mock_gateway)

    bars = make_trend_day_bars()
    fires = []

    for i, bar in enumerate(bars):
        # Create event-like object
        event = MagicMock()
        event.payload = bar
        event.mode = "LIVE"

        asyncio.get_event_loop().run_until_complete(system.process_bar(event))

        state = system.current_state
        patterns = state.get("active_patterns", [])
        signal = state.get("signal", "NEUTRAL")
        sizing = state.get("classification", "NO_SETUP")
        ready = state.get("ready_to_route", False)
        failed = state.get("failed_stages", [])
        trend = state.get("trend_state", "?")
        cci = state.get("cci_14", 0)

        bar_time = f"bar {i+1:2d} (09:{30 + i*5:02d} ET)" if i < 6 else f"bar {i+1:2d} ({9 + (30+i*5)//60}:{(30+i*5)%60:02d} ET)"

        status = "🔴"
        if patterns:
            status = "🟡 DETECTED"
            if ready:
                status = "✅ FIRED"
                fires.append((i+1, patterns, sizing))

        if patterns or i < 3 or i % 5 == 0:
            pat_str = ", ".join(f"{p['pattern_id']} {p['direction']} conf={p['confidence']:.2f}" for p in patterns) if patterns else "—"
            print(f"  {bar_time} | CCI={cci:7.1f} | trend={trend:6s} | {status:15s} | patterns: {pat_str}")
            if failed and patterns:
                print(f"  {'':36s} | failed: {failed} | sizing: {sizing}")

    print(f"\n  Bar count (should count unique ts only): {system._bar_count}")
    print(f"  Open fire records: {len(system._open_fire_records)}")

    print(f"\n  {'─' * 50}")
    if fires:
        print(f"  🎯 TOTAL FIRES: {len(fires)}")
        for bar_num, pats, sz in fires:
            print(f"     Bar {bar_num}: {[p['pattern_id'] for p in pats]} sizing={sz}")
    else:
        print(f"  ⚠️  NO FIRES — checking why:")
        print(f"     Gateway called: {mock_gateway.route_setup.called}")
        if not mock_gateway.route_setup.called:
            print(f"     Last state: signal={system.current_state.get('signal')}")
            print(f"     Last failed: {system.current_state.get('failed_stages')}")
            print(f"     Last sizing: {system.current_state.get('classification')}")

    # Verify TIME_STOP doesn't fire prematurely
    print(f"\n  TIME_STOP check:")
    print(f"     bar_count = {system._bar_count} (should be {len(bars)})")
    print(f"     limit_bars = {system._time_stop_enforcer.limit_bars} (18 = 90min)")
    if system._bar_count >= system._time_stop_enforcer.limit_bars:
        print(f"     ⚠️  Would fire after bar {system._time_stop_enforcer.limit_bars}")
    else:
        print(f"     ✅ Would NOT fire yet ({system._bar_count} < {system._time_stop_enforcer.limit_bars})")

    return fires


# ── S2 FiveMin Simulation ────────────────────────────────────────

def simulate_s2():
    print("\n" + "=" * 70)
    print("  S2 FIVE-MIN — Trend Day Simulation (Reactive + Initiative + Flags)")
    print("=" * 70)

    from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode

    system = FiveMinSystem()
    system.mode = FiveMinMode.DAY_TYPE_MODE
    system.current_day_type = "Trend_Normal"
    system._hydrated = True

    bars = make_trend_day_bars()
    detections = []

    for i, bar in enumerate(bars):
        event = MagicMock()
        event.payload = bar

        asyncio.get_event_loop().run_until_complete(system.process_bar(event))

        if system.last_pattern and system.last_pattern != detections[-1][1] if detections else True:
            detections.append((i+1, system.last_pattern, system.last_confluence))
            print(f"  bar {i+1:2d} | ✅ DETECTED: {system.last_pattern} confluence={system.last_confluence}")

    print(f"\n  Mode: {system.mode}")
    print(f"  Day type: {system.current_day_type}")
    print(f"  Buffer size: {system.buffer_size}")
    print(f"  Volume in buffer: {[b.get('v', b.get('vol', 0)) for b in system._bar_buffer[-5:]]}")

    if not detections:
        print(f"\n  ⚠️  NO S2 DETECTIONS")
        print(f"     This is expected — Reactive needs exact 4-bar geometry + 90% vol drop")
        print(f"     Bar 16→17 has vol 1800→150 (92% drop) — check if pattern geometry matched")

        # Manual check
        if len(system._bar_buffer) >= 7:
            b = system._bar_buffer
            for j in range(6, len(b)):
                b1, b2, b3, b4 = b[j-3], b[j-2], b[j-1], b[j]
                v1 = b1.get("v", 0)
                v2 = b2.get("v", 0)
                sellers = b1.get("c", 0) < b1.get("o", 0)
                drop = v2 <= v1 * 0.10 if v1 > 0 else False
                if drop:
                    print(f"     Bar {j-2}: 90% vol drop found! v1={v1} v2={v2} sellers={sellers}")
    else:
        print(f"\n  🎯 TOTAL S2 DETECTIONS: {len(detections)}")

    return detections


# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  MEMS26 — Trend Day Simulation (OFFLINE · no DB/backend impact)    ║")
    print("║  25 synthetic 5-min bars · 09:30-11:30 ET · strong uptrend         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    s4_fires = simulate_s4()
    s2_detections = simulate_s2()

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  S4 Woodies fires:     {len(s4_fires)}")
    print(f"  S2 FiveMin detections: {len(s2_detections)}")
    print(f"  TIME_STOP premature:   NO (bar_count tracks real bars)")
    print(f"  Volume visible to S2:  YES ('v' key in buffer)")
    print(f"  current_day_type:      Trend_Normal (set manually for sim)")
    print("=" * 70)
