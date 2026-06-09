# Consultation: Trade Management on Live Price + Stale-Bar Guard | 2026-06-03

## Problem (discovered today, verified)

The system can **enter trades** via `current_bar` (live tick-level data from Sierra) but **cannot manage them** (stops/targets) when 5-min bar export is stale. Today's timeline:

```
11:10 ET  Last 5-min bar in DB (Sierra export stuck)
11:19 ET  S4 fires TLB/FAMIR → trade #401 SHORT entry=7591
11:30 ET  S4 fires ZLR/VEGAS
11:45 ET  Trade #403 SHORT entry=7579
11:50 ET  Trade mgmt sees T1/T2 HIT (one-time check)
12:29 ET  Price=7571 — trades in profit but stops never checked again
```

`live_price.json` updates every 200ms (price=7571.5) but trade management only runs on bar events from DB. No bars → no stop/target checks → open trades unmanaged.

## Current Architecture

```
Sierra DLL → 5min.json → bridge → POST /bars/5min → DB (v9_bars_5min)
                                                        ↓
Sierra DLL → live_price.json → bridge → POST /live_price → Redis only (no DB)
                                                        
BarRouter → S4.process_bar() → fire → TradingGateway.persist_trade() → DB
                                                        ↓
TradeManager → on each bar event → check stops/targets vs bar.high/bar.low
```

**Gap:** TradeManager checks stops only when a new bar arrives. If bars stop, trades float.

## Proposed Fix (for consultation)

### Fix 3 — Trade management on live_price (tick-level stop check)

Option A: TradeManager subscribes to live_price updates (every 200ms). On each tick, checks all open trades' stops/targets against current price. Heavy but real-time.

Option B: TradeManager runs a periodic check (e.g., every 5s) reading `live_price` from the API or Redis. Lighter, 5s latency acceptable for shadow/paper.

Option C: The `/live_price` POST endpoint itself checks open trades against the incoming price. Co-located, no extra polling.

### Fix 4 — Stale-bar guard (prevent firing without management capability)

When `MAX(ts) FROM v9_bars_5min` is more than N minutes behind `now()`:
- S2/S4 `can_fire()` returns False
- Log warning: "bars stale by Xmin — firing blocked"
- This prevents entering trades that can't be managed

**Question for consultation:** which approach for Fix 3? And what's the right staleness threshold for Fix 4 (10min? 15min?)?

## Key Files

| File | Role |
|------|------|
| `backend/v9/systems/five_min/five_min_system.py` | S2 pattern detection + firing |
| `backend/v9/systems/woodies/woodies_system.py` | S4 pattern detection + firing |
| `backend/v9/api/v9/bars.py` | `/live_price` endpoint, `/5min` endpoint |
| `backend/v9/services/trade_excursion.py` | Trade excursion tracking |
| `backend/main.py:~390` | Trade management loop (on bar events) |
| `backend/v9/api/v9/trades.py` | Trade CRUD |

## Today's Context

- DB Root Fix done (safe_writer, all writes serialized) — commits `d38444d`, `edab3c0`, `9255bfa`
- B4 volume fix done (RTH time-gate 09:30-16:00 ET) — commit `0ece0fa`
- sc_study v9.4.5-wc-fix adopted — commit `816dd1a`
- S1 working correctly (IB=WIDE 40.75pt, Normal day type)
- Sierra export currently catching up after study re-add
- 5 open SHORT trades unmanaged (price=7571, all in profit)
