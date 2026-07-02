#!/usr/bin/env python3
"""
Bar-by-bar trading simulation for 2026-06-30 RTH session.
MES futures, Woodies CCI + S2 pattern signals.
"""

import psycopg2
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DB = "postgresql://localhost/mems26"

# ── helpers ──────────────────────────────────────────────────────────────────

def ts_to_et(ts):
    """Convert aware or naive ts to ET string HH:MM"""
    if isinstance(ts, str):
        # ISO format from woodies_signals
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET)

def fmt_et(ts):
    return ts_to_et(ts).strftime("%H:%M")

# ── load data ────────────────────────────────────────────────────────────────

def load_data():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    # RTH bars
    cur.execute("""
        SELECT ts, open, high, low, close, volume, cci_14, cci_6_tcci, trend_state, zlr_detected
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = '2026-06-30'
          AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
          AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
        ORDER BY ts
    """)
    bars = []
    for row in cur.fetchall():
        bars.append({
            'ts': row[0], 'open': row[1], 'high': row[2], 'low': row[3],
            'close': row[4], 'volume': row[5], 'cci_14': row[6],
            'tcci': row[7], 'trend': row[8], 'zlr': row[9]
        })

    # Woodies signals (ts is varchar ISO)
    cur.execute("""
        SELECT id, ts, signal_type, direction, cci_14, signal_confidence
        FROM v9_woodies_signals
        WHERE ts LIKE '2026-06-30%%'
        ORDER BY ts
    """)
    woodies = []
    for row in cur.fetchall():
        woodies.append({
            'id': row[0], 'ts': row[1], 'signal_type': row[2],
            'direction': row[3], 'cci_14': row[4], 'confidence': row[5],
            'source': 'S4_WOODIES'
        })

    # S2 setups
    cur.execute("""
        SELECT id, ts, pattern, direction, entry_price, stop_price, t1_price, t2_price,
               day_type_at_fire, confidence
        FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date = '2026-06-30'
        ORDER BY ts
    """)
    s2 = []
    for row in cur.fetchall():
        s2.append({
            'id': row[0], 'ts': row[1], 'pattern': row[2],
            'direction': row[3], 'entry_price': row[4], 'stop_price': row[5],
            't1_price': row[6], 't2_price': row[7],
            'day_type': row[8], 'confidence': row[9],
            'source': 'S2_SETUP'
        })

    # TPO
    cur.execute("""
        SELECT poc_price, vah_price, val_price, ib_high, ib_low
        FROM v9_tpo_sessions
        WHERE trading_date = '2026-06-30' AND session_type = 'CASH'
    """)
    tpo_row = cur.fetchone()
    tpo = {
        'poc': tpo_row[0], 'vah': tpo_row[1], 'val': tpo_row[2],
        'ib_high': tpo_row[3], 'ib_low': tpo_row[4]
    } if tpo_row else {}

    # Day-type (grab last RTH entry)
    cur.execute("""
        SELECT day_type, lock_state FROM v9_day_type_state
        WHERE ts::date = '2026-06-30'
        ORDER BY ts DESC LIMIT 1
    """)
    dt_row = cur.fetchone()
    day_type = dt_row[0] if dt_row else 'UNKNOWN'

    conn.close()
    return bars, woodies, s2, tpo, day_type


# ── match signal ts to bar index ─────────────────────────────────────────────

def find_bar_index(bars, signal_ts):
    """Find the bar that contains this signal timestamp.
    Signal fires at/after bar open; we enter on the NEXT bar.
    Returns index of the signal bar (entry would be next bar's open/close).
    """
    sig_dt = ts_to_et(signal_ts)
    for i, b in enumerate(bars):
        bar_et = ts_to_et(b['ts'])
        bar_end = bar_et + timedelta(minutes=5)
        if bar_et <= sig_dt < bar_end:
            return i
    # If exact match not found, find closest prior bar
    for i in range(len(bars) - 1, -1, -1):
        if ts_to_et(bars[i]['ts']) <= sig_dt:
            return i
    return None


# ── simulate one trade ───────────────────────────────────────────────────────

def simulate_trade(bars, entry_idx, direction, entry_price, stop_price):
    """
    Walk forward from entry_idx through bars.
    Returns dict with outcome details.

    3-contract scaling:
      Contract 1: exit at T1, trail stop to BE
      Contract 2: exit at T2, trail stop to T1
      Contract 3: exit at T3 or EOD, trail stop to T2

    R = |entry - stop|
    T1 = entry +/- 1R
    T2 = entry +/- 2R
    T3 = entry +/- 4R
    """
    is_long = direction == 'LONG'
    R = abs(entry_price - stop_price)

    if R < 0.25:
        return {'outcome': 'SKIP', 'reason': 'R too small', 'pnl': 0, 'r_mult': 0,
                'entry': entry_price, 'stop': stop_price, 'R': R,
                't1': entry_price, 't2': entry_price, 't3': entry_price}

    if is_long:
        t1 = entry_price + R
        t2 = entry_price + 2 * R
        t3 = entry_price + 4 * R
    else:
        t1 = entry_price - R
        t2 = entry_price - 2 * R
        t3 = entry_price - 4 * R

    # Track 3 contracts
    c1_open = True
    c2_open = True
    c3_open = True

    current_stop = stop_price
    total_pnl = 0.0

    trace = []
    outcome_parts = []

    for i in range(entry_idx, len(bars)):
        b = bars[i]
        bar_time = fmt_et(b['ts'])

        if is_long:
            # Check stop first (worst case), then targets
            # Stop hit?
            if b['low'] <= current_stop:
                # All remaining contracts stopped
                if c1_open:
                    pnl1 = (current_stop - entry_price)
                    total_pnl += pnl1
                    outcome_parts.append(f"C1 stopped {current_stop:.2f}")
                    c1_open = False
                if c2_open:
                    pnl2 = (current_stop - entry_price)
                    total_pnl += pnl2
                    outcome_parts.append(f"C2 stopped {current_stop:.2f}")
                    c2_open = False
                if c3_open:
                    pnl3 = (current_stop - entry_price)
                    total_pnl += pnl3
                    outcome_parts.append(f"C3 stopped {current_stop:.2f}")
                    c3_open = False
                trace.append(f"  {bar_time} H={b['high']:.2f} L={b['low']:.2f} -> STOP HIT @ {current_stop:.2f}")
                break

            # T3 hit?
            if c3_open and b['high'] >= t3:
                if c1_open:
                    total_pnl += (t1 - entry_price)
                    outcome_parts.append(f"C1 T1 {t1:.2f}")
                    c1_open = False
                if c2_open:
                    total_pnl += (t2 - entry_price)
                    outcome_parts.append(f"C2 T2 {t2:.2f}")
                    c2_open = False
                total_pnl += (t3 - entry_price)
                outcome_parts.append(f"C3 T3 {t3:.2f}")
                c3_open = False
                trace.append(f"  {bar_time} H={b['high']:.2f} -> T3 HIT! Full target")
                break

            # T2 hit?
            if c2_open and b['high'] >= t2:
                if c1_open:
                    total_pnl += (t1 - entry_price)
                    outcome_parts.append(f"C1 T1 {t1:.2f}")
                    c1_open = False
                total_pnl += (t2 - entry_price)
                outcome_parts.append(f"C2 T2 {t2:.2f}")
                c2_open = False
                current_stop = t1  # trail to T1
                trace.append(f"  {bar_time} H={b['high']:.2f} -> T2 HIT, trail stop to {current_stop:.2f}")
                continue

            # T1 hit?
            if c1_open and b['high'] >= t1:
                total_pnl += (t1 - entry_price)
                outcome_parts.append(f"C1 T1 {t1:.2f}")
                c1_open = False
                current_stop = entry_price + 0.25  # BE + 1 tick
                trace.append(f"  {bar_time} H={b['high']:.2f} -> T1 HIT, trail stop to BE+1T ({current_stop:.2f})")
                continue

            trace.append(f"  {bar_time} H={b['high']:.2f} L={b['low']:.2f} (hold)")

        else:  # SHORT
            # Stop hit?
            if b['high'] >= current_stop:
                if c1_open:
                    total_pnl += (entry_price - current_stop)
                    outcome_parts.append(f"C1 stopped {current_stop:.2f}")
                    c1_open = False
                if c2_open:
                    total_pnl += (entry_price - current_stop)
                    outcome_parts.append(f"C2 stopped {current_stop:.2f}")
                    c2_open = False
                if c3_open:
                    total_pnl += (entry_price - current_stop)
                    outcome_parts.append(f"C3 stopped {current_stop:.2f}")
                    c3_open = False
                trace.append(f"  {bar_time} H={b['high']:.2f} L={b['low']:.2f} -> STOP HIT @ {current_stop:.2f}")
                break

            # T3 hit?
            if c3_open and b['low'] <= t3:
                if c1_open:
                    total_pnl += (entry_price - t1)
                    outcome_parts.append(f"C1 T1 {t1:.2f}")
                    c1_open = False
                if c2_open:
                    total_pnl += (entry_price - t2)
                    outcome_parts.append(f"C2 T2 {t2:.2f}")
                    c2_open = False
                total_pnl += (entry_price - t3)
                outcome_parts.append(f"C3 T3 {t3:.2f}")
                c3_open = False
                trace.append(f"  {bar_time} L={b['low']:.2f} -> T3 HIT! Full target")
                break

            # T2 hit?
            if c2_open and b['low'] <= t2:
                if c1_open:
                    total_pnl += (entry_price - t1)
                    outcome_parts.append(f"C1 T1 {t1:.2f}")
                    c1_open = False
                total_pnl += (entry_price - t2)
                outcome_parts.append(f"C2 T2 {t2:.2f}")
                c2_open = False
                current_stop = t1
                trace.append(f"  {bar_time} L={b['low']:.2f} -> T2 HIT, trail stop to {current_stop:.2f}")
                continue

            # T1 hit?
            if c1_open and b['low'] <= t1:
                total_pnl += (entry_price - t1)
                outcome_parts.append(f"C1 T1 {t1:.2f}")
                c1_open = False
                current_stop = entry_price - 0.25
                trace.append(f"  {bar_time} L={b['low']:.2f} -> T1 HIT, trail stop to BE+1T ({current_stop:.2f})")
                continue

            trace.append(f"  {bar_time} H={b['high']:.2f} L={b['low']:.2f} (hold)")

    # End of day - close remaining contracts at last bar close
    last_close = bars[-1]['close']
    if c1_open or c2_open or c3_open:
        remaining = sum([c1_open, c2_open, c3_open])
        if is_long:
            eod_pnl = (last_close - entry_price) * remaining
        else:
            eod_pnl = (entry_price - last_close) * remaining
        total_pnl += eod_pnl
        outcome_parts.append(f"{remaining}x EOD close @ {last_close:.2f}")
        trace.append(f"  EOD: closed {remaining} contracts @ {last_close:.2f}")

    # Determine outcome label
    if total_pnl > R:
        outcome = 'WIN'
    elif total_pnl > 0:
        outcome = 'PARTIAL'
    elif total_pnl == 0:
        outcome = 'FLAT'
    else:
        outcome = 'LOSS'

    r_mult = total_pnl / R if R > 0 else 0

    return {
        'outcome': outcome,
        'pnl': total_pnl,
        'pnl_per_contract': total_pnl / 3.0,
        'r_mult': r_mult,
        'entry': entry_price,
        'stop': stop_price,
        'R': R,
        't1': t1, 't2': t2, 't3': t3,
        'trace': trace,
        'parts': outcome_parts
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    bars, woodies, s2_setups, tpo, day_type = load_data()

    print("=" * 100)
    print(f"  MEMS26 TRADING SIMULATION — 2026-06-30 RTH SESSION")
    print(f"  Day Type: {day_type}  |  Bars: {len(bars)}  |  Woodies Signals: {len(woodies)}  |  S2 Setups: {len(s2_setups)}")
    print(f"  TPO: POC={tpo.get('poc')}, VAH={tpo.get('vah')}, VAL={tpo.get('val')}, IB_H={tpo.get('ib_high')}, IB_L={tpo.get('ib_low')}")
    print(f"  Open: {bars[0]['open']:.2f}  High: {max(b['high'] for b in bars):.2f}  Low: {min(b['low'] for b in bars):.2f}  Close: {bars[-1]['close']:.2f}")
    print("=" * 100)

    # Determine trend direction from price action
    # Day opened ~7500, closed ~7545; IB broke up. Variation day = uptrend
    session_high = max(b['high'] for b in bars)
    session_low = min(b['low'] for b in bars)
    trend_dir = 'LONG' if bars[-1]['close'] > bars[0]['open'] else 'SHORT'
    print(f"  Session Trend: {trend_dir} (open {bars[0]['open']:.2f} -> close {bars[-1]['close']:.2f})")
    print()

    # ── Process ALL signals ──────────────────────────────────────────────

    all_signals = []

    # Woodies signals
    for sig in woodies:
        bar_idx = find_bar_index(bars, sig['ts'])
        if bar_idx is None:
            continue

        signal_bar = bars[bar_idx]
        # Entry on NEXT bar's open (or signal bar close as proxy)
        entry_idx = bar_idx + 1
        if entry_idx >= len(bars):
            continue

        entry_price = bars[entry_idx]['open']

        # Stop: for ZLR LONG, signal bar low - 0.75; for SHORT, signal bar high + 0.75
        # For GHOST, use 1.5 pts from entry
        if sig['direction'] == 'LONG':
            stop_price = signal_bar['low'] - 0.75
        else:
            stop_price = signal_bar['high'] + 0.75

        all_signals.append({
            'id': f"W-{sig['id']}",
            'source': 'S4_WOODIES',
            'ts': sig['ts'],
            'pattern': sig['signal_type'],
            'direction': sig['direction'],
            'entry_price': entry_price,
            'stop_price': stop_price,
            'entry_idx': entry_idx,
            'confidence': sig['confidence'],
            'bar_time': fmt_et(signal_bar['ts']),
        })

    # S2 setups
    for s in s2_setups:
        bar_idx = find_bar_index(bars, s['ts'])
        if bar_idx is None:
            continue

        entry_idx = bar_idx + 1
        if entry_idx >= len(bars):
            continue

        # S2 provides explicit entry/stop
        all_signals.append({
            'id': f"S2-{s['id']}",
            'source': 'S2_SETUP',
            'ts': s['ts'],
            'pattern': s['pattern'],
            'direction': s['direction'],
            'entry_price': s['entry_price'],
            'stop_price': s['stop_price'],
            'entry_idx': entry_idx,
            'confidence': s['confidence'],
            'bar_time': fmt_et(bars[bar_idx]['ts']),
        })

    # Sort by time
    all_signals.sort(key=lambda x: str(x['ts']))

    print(f"{'='*100}")
    print(f"  DETAILED TRADE-BY-TRADE SIMULATION ({len(all_signals)} signals)")
    print(f"{'='*100}")
    print()

    results = []

    for sig in all_signals:
        is_with_trend = sig['direction'] == trend_dir

        result = simulate_trade(
            bars, sig['entry_idx'], sig['direction'],
            sig['entry_price'], sig['stop_price']
        )

        if result['outcome'] == 'SKIP':
            print(f"  [{sig['id']}] {sig['bar_time']} {sig['pattern']:25s} {sig['direction']:5s} -- SKIPPED (R={result['R']:.2f})")
            print()
            continue

        # MES tick value = $1.25 per 0.25 point = $5 per point
        pnl_dollars = result['pnl'] * 5.0  # per contract total across 3 contracts

        with_trend_tag = "WITH-TREND" if is_with_trend else "COUNTER"

        print(f"  [{sig['id']}] {sig['bar_time']}  {sig['pattern']:25s} {sig['direction']:5s}  ({sig['source']}, conf={sig['confidence']:.2f})")
        print(f"  {with_trend_tag} | Entry: {result['entry']:.2f}  Stop: {result['stop']:.2f}  R={result['R']:.2f}")
        print(f"  T1={result['t1']:.2f}  T2={result['t2']:.2f}  T3={result['t3']:.2f}")
        print(f"  Bar-by-bar trace:")
        for line in result['trace'][:20]:  # limit trace output
            print(f"    {line}")
        if len(result['trace']) > 20:
            print(f"    ... ({len(result['trace']) - 20} more bars)")
        print(f"  >> OUTCOME: {result['outcome']}  |  Parts: {', '.join(result['parts'])}")
        print(f"  >> P&L: {result['pnl']:+.2f} pts (3 contracts)  |  ${pnl_dollars:+.2f}  |  R-multiple: {result['r_mult']:+.2f}R")
        print()

        results.append({
            'id': sig['id'],
            'pattern': sig['pattern'],
            'direction': sig['direction'],
            'source': sig['source'],
            'with_trend': is_with_trend,
            'entry': result['entry'],
            'stop': result['stop'],
            'R': result['R'],
            'outcome': result['outcome'],
            'pnl_pts': result['pnl'],
            'pnl_dollars': pnl_dollars,
            'r_mult': result['r_mult'],
            'parts': result['parts'],
        })

    # ── Summary ──────────────────────────────────────────────────────────

    print()
    print("=" * 100)
    print("  SUMMARY TABLE")
    print("=" * 100)
    print()
    print(f"  {'ID':<10} {'Pattern':<25} {'Dir':<6} {'Trend?':<8} {'Entry':>8} {'Stop':>8} {'R':>6} {'Result':<8} {'P&L pts':>9} {'P&L $':>9} {'R-mult':>8}")
    print(f"  {'-'*10} {'-'*25} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*9} {'-'*9} {'-'*8}")

    for r in results:
        trend_tag = "WITH" if r['with_trend'] else "CTR"
        print(f"  {r['id']:<10} {r['pattern']:<25} {r['direction']:<6} {trend_tag:<8} {r['entry']:>8.2f} {r['stop']:>8.2f} {r['R']:>6.2f} {r['outcome']:<8} {r['pnl_pts']:>+9.2f} {r['pnl_dollars']:>+9.2f} {r['r_mult']:>+8.2f}")

    print()

    # Totals
    total_pnl_pts = sum(r['pnl_pts'] for r in results)
    total_pnl_dollars = sum(r['pnl_dollars'] for r in results)
    wins = [r for r in results if r['outcome'] in ('WIN', 'PARTIAL')]
    losses = [r for r in results if r['outcome'] == 'LOSS']

    # With-trend only (CONT signals for Variation day)
    wt = [r for r in results if r['with_trend']]
    wt_pnl = sum(r['pnl_pts'] for r in wt)
    wt_dollars = sum(r['pnl_dollars'] for r in wt)

    # Counter-trend
    ct = [r for r in results if not r['with_trend']]
    ct_pnl = sum(r['pnl_pts'] for r in ct)
    ct_dollars = sum(r['pnl_dollars'] for r in ct)

    print(f"  ALL SIGNALS ({len(results)} trades):")
    print(f"    Total P&L: {total_pnl_pts:+.2f} pts  |  ${total_pnl_dollars:+.2f}")
    print(f"    Wins/Partials: {len(wins)}  |  Losses: {len(losses)}  |  Win rate: {len(wins)/max(len(results),1)*100:.0f}%")
    print()

    print(f"  WITH-TREND ONLY ({len(wt)} trades) — Variation day, LONG bias:")
    print(f"    Total P&L: {wt_pnl:+.2f} pts  |  ${wt_dollars:+.2f}")
    for r in wt:
        print(f"      {r['id']}: {r['pattern']} -> {r['outcome']} {r['pnl_pts']:+.2f} pts ({r['r_mult']:+.2f}R)")
    print()

    print(f"  COUNTER-TREND ({len(ct)} trades) — would NOT trade on Variation day:")
    print(f"    Total P&L: {ct_pnl:+.2f} pts  |  ${ct_dollars:+.2f}")
    for r in ct:
        print(f"      {r['id']}: {r['pattern']} -> {r['outcome']} {r['pnl_pts']:+.2f} pts ({r['r_mult']:+.2f}R)")
    print()

    if results:
        best = max(results, key=lambda r: r['pnl_pts'])
        worst = min(results, key=lambda r: r['pnl_pts'])
        print(f"  BEST TRADE:  {best['id']} {best['pattern']} {best['direction']} -> {best['pnl_pts']:+.2f} pts (${best['pnl_dollars']:+.2f})")
        print(f"  WORST TRADE: {worst['id']} {worst['pattern']} {worst['direction']} -> {worst['pnl_pts']:+.2f} pts (${worst['pnl_dollars']:+.2f})")

    print()
    print("=" * 100)
    print("  CONCLUSION")
    print("=" * 100)

    print(f"""
  Day Type: {day_type} (uptrend, IB broke to upside)
  Session: {bars[0]['open']:.2f} -> {bars[-1]['close']:.2f} ({bars[-1]['close'] - bars[0]['open']:+.2f} pts)

  IF trading ALL signals (both S4+S2): {total_pnl_pts:+.2f} pts across {len(results)} trades = ${total_pnl_dollars:+.2f}
  IF trading WITH-TREND only (correct for Variation): {wt_pnl:+.2f} pts across {len(wt)} trades = ${wt_dollars:+.2f}

  Counter-trend shorts on a Variation/uptrend day: {ct_pnl:+.2f} pts = ${ct_dollars:+.2f} (avoid!)

  Note: P&L is for 3-contract scaling (MES, $5/pt per contract).
  Total dollar P&L = pts * $5 * 3 contracts (already included in the 3-contract P&L above).
""")


if __name__ == '__main__':
    main()
