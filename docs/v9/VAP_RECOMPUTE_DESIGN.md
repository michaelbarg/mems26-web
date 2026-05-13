# VAP Recompute Design — Python-Side Footprint from SCID Ticks

## Problem
DLL v9.2.0 set `MaintainVolumeAtPriceData=0` to fix memory leak.
Result: footprint.json uses proportional bid/ask distribution (DEGRADED).
DATA_INTEGRITY_PRINCIPLE §7 blocks SHADOW until resolved.

## Solution
Read raw ticks from Sierra SCID file → compute real bid/ask per price level.

## Tick Source

**File:** `~/SierraChart/Data/MESH26_FUT_CME.scid`
- Format: Sierra SCID v56, 40-byte records
- Record: `SCDateTimeMS(int64) Open(f32) High(f32) Low(f32) Close(f32) NumTrades(u32) Volume(u32) BidVolume(u32) AskVolume(u32)`
- Timestamp: microseconds since 1899-12-30
- Price scale: raw value / 100 = USD price
- Tick size: 0.25 points ($1.25 per tick for MES)
- File size: ~1.8 GB, ~45M records

## Bid/Ask Classification

Already classified by Sierra at the exchange level:
- `bid_volume > 0` → trade hit the bid (SELL aggressor)
- `ask_volume > 0` → trade lifted the ask (BUY aggressor)
- Both > 0 → split trade (rare, both counted)

No inference needed — Sierra provides ground truth.

## Bar Aggregation

1. Bridge polls SCID file every 3 seconds (matching DLL export interval)
2. Track file offset — read only NEW ticks since last poll
3. Bucket ticks into 3-minute chart bars (matching Sierra chart timeframe)
4. Each bar accumulates: `{price_level: {bid_vol, ask_vol}}` per tick price

## Output Schema (matches FOOTPRINT_TICK_SPEC_V3)

```json
{
  "type": "footprint",
  "version": "v9.2.1-python",
  "export_ts": 1746806400,
  "bar_count": 30,
  "cumulative_delta": 4521.00,
  "bars": [{
    "idx": 0,
    "o": 5412.50, "h": 5413.25, "l": 5411.75, "c": 5412.75,
    "vol": 856, "delta": 122,
    "poc_price": 5412.50, "poc_vol": 234,
    "stacked_buy": 0, "stacked_sell": 0,
    "levels": [{
      "p": 5411.75,
      "bid": 45,    // REAL bid volume
      "ask": 120,   // REAL ask volume
      "d": 75,      // delta = ask - bid
      "ib": true,   // buy imbalance (ask/bid >= 2.5)
      "is": false   // sell imbalance (bid/ask >= 2.5)
    }]
  }]
}
```

## Memory Bounds

- Max bars retained: 30 (deque with maxlen)
- Max levels per bar: 500 (safety cap, typical ~20-50)
- Total: 30 × 500 = 15,000 levels max
- Per level: ~40 bytes → 600 KB max
- SCID read buffer: 4096 records × 40 bytes = 160 KB

## Failure Handling

- SCID file missing/locked → log warning, skip cycle, retry next poll
- Malformed record (wrong size) → log + skip record, continue
- Gap in timestamps (>5 min) → close current bar, start new session
- Tick with 0 volume → skip (padding record)
- File truncated → seek back to last valid offset
