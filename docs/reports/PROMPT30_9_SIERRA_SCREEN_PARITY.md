# P30.9 — Sierra Screen Parity Data Contract

**Date:** 2026-05-18
**Status:** PARTIAL — live exports verified, TPO current API wired, UI still blocked on period-scoped POC
**No SHADOW/DEMO/LIVE enabled. No trade_command writes.**

---

## Source Of Truth

Michael provided 5 Sierra screenshots showing the visual contract:

1. **5-min chart** — TPO VAH/VAL (magenta dashed), POC (magenta solid), IB Mid/Low (cyan), Cumulative Delta Bars below
2. **TPO Profile** — Letter-based market profile A-M, volume histogram, POC arrow, IB lines (blue)
3. **Woodies CCI 5m** — CCI-14 (black), TCCI (yellow), histogram bars, ZLR markers, data values column
4. **Tick Reversal 15** — Numbers bars with delta/volume/cumulative delta
5. **3-min chart** — Two sets of TPO levels (period-scoped), IB, Cumulative Delta

---

## Phase 1: Existing Export Inventory

| Export File | Status | Freshness | Data Quality |
|-------------|--------|-----------|--------------|
| `5min.json` | LIVE | 2s | OHLCV valid. `poc_vol`/`vah`/`val` are zero placeholders |
| `tpo.json` | LIVE | ~2s | New `session` / `ib` / `prior_day` contract exists; not yet backend-integrated |
| `woodies_5min.json` | LIVE | ~2s | New live 5m Woodies export exists |
| `woodies_30min.json` | LIVE | 2s | Full CCI/TCCI/ZLR/HFE data, matches 30m view |
| `cumulative_delta.json` | LIVE | 2s | Sampled points with delta/cum/price |
| `tick_reversal_15.json` | LIVE | 2s | OHLCV + delta + bid/ask volume per bar |
| `volume_profile.json` | LIVE | 2s | Per-bar POC/VAH/VAL from footprint data |
| `footprint.json` | LIVE | 2s | Full footprint with levels/absorption |

## Phase 2: Gaps vs Sierra Screenshots

| Visual Element | Sierra Shows | Current Export | Gap |
|----------------|-------------|----------------|-----|
| Session POC | 7409.50 (magenta) | `mes_ai_data.json` market_profile.poc | Exists but not in dedicated file |
| Session VAH | 7420.25 / 7464.25 (magenta dashed) | Same | Same |
| Session VAL | 7382.75 / 7436.25 (magenta dashed) | Same | Same |
| IB High | 7448.00 (cyan) | Not exported | **NEW: added to tpo.json** |
| IB Mid | 7416.63 (cyan) | Not exported | **NEW: added to tpo.json** |
| IB Low | 7395.00 (cyan) | Not exported | **NEW: added to tpo.json** |
| Prior-day High/Low/Close | White levels | `time_levels` in mes_ai_data.json | **NEW: also in tpo.json** |
| Woodies CCI 5m | Full panel with CCI/TCCI/ZLR | `woodies_5min.json` stale | **FIX: write call added** |
| Cumulative Delta Bars | OHLC-style delta bars | Points format in cumulative_delta.json | Adequate for now |

## Phase 3: Code Changes

### New export function: `v9_tpo_to_json()`

Added to `MES_AI_DataExport_merged.cpp`. Outputs:

```json
{
  "type": "tpo",
  "version": "v9.4.0-p30.9",
  "export_ts": 1779090000,
  "session": {
    "poc": 7409.50,
    "vah": 7420.25,
    "val": 7382.75,
    "session_high": 7464.25,
    "session_low": 7363.25,
    "total_volume": 125000.00
  },
  "ib": {
    "found": true,
    "high": 7448.00,
    "mid": 7416.63,
    "low": 7395.00
  },
  "prior_day": {
    "found": true,
    "high": 7474.00,
    "low": 7471.75,
    "close": 7473.50
  }
}
```

### Woodies 5-min write call added

`v9_write_json(v9dir, "woodies_5min.json", w5_json)` — the function `v9_woodies_5min_to_json()` already existed but the write call was missing.

### All Y:\ paths

All 5 file paths use `Y:\` (CrossOver mapping to `/Users/michael`), not `C:\`.

### Version bump

`v9.4.0-p30.9` — look for this in Sierra study name after rebuild.

### Files changed

| File | Change |
|------|--------|
| `sc_study/MES_AI_DataExport_merged.cpp` | Added `v9_tpo_to_json()`, added woodies_5min + tpo write calls, version bump |
| `SierraChart/ACS_Source/MES_AI_DataExport.cpp` | Copied from repo (Sierra build source) |

## Phase 4: Sierra Rebuild Verification

Sierra is now generating the new files with `version=v9.4.0-p30.9`:

```text
tpo.json
age: ~2s
version: v9.4.0-p30.9
session: { poc, vah, val, session_high, session_low, total_volume }
ib: { found, high, mid, low }
prior_day: { found, high, low, close }

woodies_5min.json
age: ~2s
version: v9.4.0-p30.9
history_len: 50
current_bar: { ohlc, cci_14, cci_6_tcci, lsma_value, swi_value,
               czi_value, ema_34, trend_state, zlr/hfe fields }
```

Targeted tests after verification:

```text
pytest tests/v9/db/test_api.py tests/v9/bridge/test_streams.py -q
35 passed, 5 warnings
```

## Remaining Integration Blockers

- `bridge/v9_streams/tpo_stream.py` still documents and pushes the old TPO
  `bars: [{letter, price, level, period_id}]` contract.
- `backend/v9/api/v9/bars.py::post_tpo()` still expects the old `bars` list and
  would ignore the new `session` / `ib` / `prior_day` fields.
- `/api/v9/tpo/current` now prefers fresh Sierra `tpo.json` and returns
  `source=sierra_tpo_json` with `poc`, `vah`, `val`, `ib_high`, `ib_mid`,
  `ib_low`, and `prior_day`.
- The new `tpo.json` still does not include period-scoped 30-minute POC steps in
  the export file itself. **Interim:** `/api/v9/tpo/current` now attaches
  `periods[]` from `v9_tpo_sessions` (DB) for stepped overlay until Sierra
  exports `periods[]` directly.
- Modular Sierra source is not fully aligned with the generated monolith:
  `sc_study/MES_AI_DataExport_merged.cpp` contains `v9.4.0-p30.9` TPO/Woodies
  exports, while modular headers still show older version/contracts. Do not
  regenerate the monolith again until modular sources are reconciled.

## Naming Clarification

| Field | Meaning |
|-------|---------|
| `poc` (in tpo.json session) | POC price level |
| `poc_vol` (in volume_profile) | Volume at POC price |
| `vah` / `val` | Value Area High / Low prices |

## Frontend Status (2026-05-19)

**ChartV5b overlay wired (needs live UAT with backend + Sierra running):**

- `SierraLevelsOverlay.tsx` — time-scoped SVG overlay on lightweight-charts
- Stepped magenta POC from `periods[]` (DB sessions, last 5 periods)
- Cyan IB high/mid/low (`#06b6d4`, not green price lines)
- White dashed prior-day high/low from `prior_day`
- Removed full-width `createPriceLine` POC/VAH/VAL/IB lines

**Still open for full screen parity:**

- Cumulative Delta pane below price (Sierra `cumulative_delta.json` → GET API)
- VAH/VAL stepped lines (only POC stepped in this pass)
- Live UAT vs screenshot timestamps/prices (four axes)

Backend verification after wiring:

```text
/api/v9/tpo/current
source: sierra_tpo_json
version: v9.4.0-p30.9
poc: 7408.25
vah: 7430.5
val: 7389.0
ib_high: 7454.25
ib_mid: 7434.75
ib_low: 7415.25
prior_day: { high: 7435.25, low: 7375.0, close: 7385.5 }
periods: from v9_tpo_sessions (up to 12 rows)
```

**Woodies 5m:** `Woodies5MinPayload` accepts `current_bar`-only Sierra contract;
bridge `post_woodies_5min` ready when narrow bridge includes `woodies_5min` stream.

## Safety

- No SHADOW/DEMO/LIVE enabled
- No trade_command.json written
- Bridge remains local-only (`CLOUD_URL=http://localhost:8000`)
- Full bridge NOT started — narrow `--bars-5min-only` mode only
