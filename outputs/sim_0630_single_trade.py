"""06-30 simulation: single WITH-TREND trade at a time, bar-by-bar walk.

Rules (Michael):
1. Only LONG (with-trend on this Variation/uptrend day)
2. Only CONT patterns (ZLR, TLB, TT, GB100) — REV blocked by design
3. ONE trade at a time — skip signals while a position is open
4. 3 contracts: C1→T1 (1R), C2→T2 (2R), C3→T3 (4R) or trail
5. After T1 → stop moves to BE+1T
6. After T2 → trail C3 at HWM - 1R
7. End of day → close at market
"""
import os, sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
os.environ.setdefault("BRIDGE_TOKEN", "x")

from backend.v9.db.read import read_all

bars = read_all("""
    SELECT ts AT TIME ZONE 'America/New_York' as et,
           open, high, low, close, cci_14, trend_state
    FROM v9_bars_5min_woodies
    WHERE (ts AT TIME ZONE 'America/New_York')::date = '2026-06-30'
      AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
      AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
    ORDER BY ts
""", {})

signals = read_all("""
    SELECT id, ts::timestamptz AT TIME ZONE 'America/New_York' as et,
           signal_type, direction, cci_14
    FROM v9_woodies_signals
    WHERE ts::timestamptz >= '2026-06-30'::timestamptz
      AND ts::timestamptz < '2026-07-01'::timestamptz
      AND direction = 'LONG'
    ORDER BY ts
""", {})

bar_list = []
for b in bars:
    bar_list.append({
        "et": str(b["et"])[:16], "o": float(b["open"]), "h": float(b["high"]),
        "l": float(b["low"]), "c": float(b["close"]),
        "cci": float(b["cci_14"]) if b.get("cci_14") else 0,
        "trend": b.get("trend_state", "GRAY"),
    })

# Index signals by bar time (truncated to minute)
sig_by_bar = {}
for s in signals:
    key = str(s["et"])[:16]
    if s["signal_type"] in ("ZLR", "TLB", "TT", "GB100"):  # CONT only
        sig_by_bar.setdefault(key, []).append(s)

print(f"Bars: {len(bar_list)}, WITH-TREND CONT signals: {len(signals)}")
print(f"Session: {bar_list[0]['o']:.2f} → {bar_list[-1]['c']:.2f}")
print(f"Range: {min(b['l'] for b in bar_list):.2f} — {max(b['h'] for b in bar_list):.2f}")
print()

TICK = 0.25
MES_PT = 5.0

# Active trade state
trade = None  # {entry, stop, current_stop, risk, t1, t2, t3, contracts, t1_hit, t2_hit, hwm, pnl, bar_et}
trades_done = []

for i, bar in enumerate(bar_list):
    # 1. Manage active trade
    if trade is not None:
        # Update HWM
        if bar["h"] > trade["hwm"]:
            trade["hwm"] = bar["h"]

        # Check stop (on bar low)
        if bar["l"] <= trade["current_stop"]:
            stop_pnl = (trade["current_stop"] - trade["entry"]) * trade["contracts"]
            trade["pnl"] += stop_pnl
            print(f"  {bar['et']}: STOP @ {trade['current_stop']:.2f} ({trade['contracts']}C) → {stop_pnl:+.2f}pt")
            trade["contracts"] = 0

        # Check T1
        if trade["contracts"] > 0 and not trade["t1_hit"] and bar["h"] >= trade["t1"]:
            trade["t1_hit"] = True
            c1_pnl = trade["t1"] - trade["entry"]
            trade["pnl"] += c1_pnl
            trade["contracts"] -= 1
            trade["current_stop"] = trade["entry"] + TICK  # BE+1T
            print(f"  {bar['et']}: T1 HIT @ {trade['t1']:.2f} → C1 +{c1_pnl:.2f}pt, stop→{trade['current_stop']:.2f}")

        # Check T2
        if trade["contracts"] > 0 and trade["t1_hit"] and not trade["t2_hit"] and bar["h"] >= trade["t2"]:
            trade["t2_hit"] = True
            c2_pnl = trade["t2"] - trade["entry"]
            trade["pnl"] += c2_pnl
            trade["contracts"] -= 1
            trail = trade["hwm"] - trade["risk"]
            if trail > trade["current_stop"]:
                trade["current_stop"] = trail
            print(f"  {bar['et']}: T2 HIT @ {trade['t2']:.2f} → C2 +{c2_pnl:.2f}pt, trail→{trade['current_stop']:.2f}")

        # Check T3
        if trade["contracts"] > 0 and trade["t2_hit"] and bar["h"] >= trade["t3"]:
            c3_pnl = trade["t3"] - trade["entry"]
            trade["pnl"] += c3_pnl
            trade["contracts"] -= 1
            print(f"  {bar['et']}: T3 HIT @ {trade['t3']:.2f} → C3 +{c3_pnl:.2f}pt")

        # Trail C3 stop after T2
        if trade["contracts"] > 0 and trade["t2_hit"]:
            trail = trade["hwm"] - trade["risk"]
            if trail > trade["current_stop"]:
                trade["current_stop"] = trail

        # EOD close
        if trade["contracts"] > 0 and i == len(bar_list) - 1:
            eod_pnl = (bar["c"] - trade["entry"]) * trade["contracts"]
            trade["pnl"] += eod_pnl
            print(f"  {bar['et']}: EOD CLOSE @ {bar['c']:.2f} ({trade['contracts']}C) → {eod_pnl:+.2f}pt")
            trade["contracts"] = 0

        # Close trade if no contracts left
        if trade["contracts"] == 0:
            trades_done.append(trade)
            trade = None

    # 2. Check for new signal (only if no active trade)
    if trade is None and bar["et"] in sig_by_bar:
        for sig in sig_by_bar[bar["et"]]:
            entry = bar["c"]
            stop = bar["l"] - 3 * TICK
            risk = entry - stop
            if risk <= 0 or risk > 15:
                print(f"\n  SKIP {sig['signal_type']} @ {bar['et']} — risk {risk:.2f}pt (>15 cap)")
                continue

            t1 = entry + risk
            t2 = entry + 2 * risk
            t3 = entry + 4 * risk

            trade = {
                "id": sig["id"], "pattern": sig["signal_type"],
                "entry": entry, "stop": stop, "current_stop": stop,
                "risk": risk, "t1": t1, "t2": t2, "t3": t3,
                "contracts": 3, "t1_hit": False, "t2_hit": False,
                "hwm": entry, "pnl": 0.0, "bar_et": bar["et"],
            }
            print(f"\n>>> ENTER {sig['signal_type']} LONG @ {entry:.2f} ({bar['et']})")
            print(f"    Stop={stop:.2f} T1={t1:.2f} T2={t2:.2f} T3={t3:.2f} R={risk:.2f}pt")
            break  # one signal per bar

# Summary
print("\n" + "=" * 70)
print("RESULTS — WITH-TREND CONT, SINGLE TRADE AT A TIME")
print("=" * 70)

total_pts = sum(t["pnl"] for t in trades_done)
total_usd = total_pts * MES_PT

for t in trades_done:
    r_mult = t["pnl"] / t["risk"] if t["risk"] > 0 else 0
    targets = f"T1={'✓' if t['t1_hit'] else '✗'} T2={'✓' if t['t2_hit'] else '✗'}"
    print(f"  {t['pattern']:6s} LONG @ {t['entry']:.2f} ({t['bar_et']}) | "
          f"R={t['risk']:.1f}pt | {targets} | "
          f"P&L {t['pnl']:+.2f}pt = ${t['pnl']*MES_PT:+.0f} ({r_mult:+.1f}R)")

print(f"\nTotal: {total_pts:+.2f}pt = ${total_usd:+.0f}")
print(f"Trades: {len(trades_done)}")
if trades_done:
    wins = sum(1 for t in trades_done if t["pnl"] > 0)
    print(f"Win rate: {wins}/{len(trades_done)} = {100*wins/len(trades_done):.0f}%")
