# V9 Naming Standardization — Changes Applied

**Date:** 2026-05-10
**Ref:** /tmp/mems26_qa_reports/naming_audit.md, .claude/SKILL.md (NAMING section)

---

## 1. Frontend types/index.ts — Full Rewrite

All interfaces now match actual backend API response shapes.

### Bar5Min

| Old Field | New Field | Reason |
|-----------|-----------|--------|
| `timestamp` | `ts` | Matches API GET `/api/v9/bars/5min` |
| `open` | `o` | Matches API |
| `high` | `h` | Matches API |
| `low` | `l` | Matches API |
| `close` | `c` | Matches API |
| `volume` | `vol` | Matches API |
| `tick_count` | *(removed)* | Not in API response |
| `vwap` | *(removed)* | Not in API response |
| `delta` | `cumulative_delta` | Matches API |
| `poc_price` | `poc_vol` | Was wrong type (price vs volume count) |
| `vah_price` | `vah` | Matches API |
| `val_price` | `val` | Matches API |

### TickReversalBar

| Old Field | New Field |
|-----------|-----------|
| `timestamp` | `ts` |
| `open/high/low/close` | `o/h/l/c` |
| `volume` | `vol` |
| `tick_count` | `tick_size` |
| `up_ticks` | *(removed)* |
| `down_ticks` | *(removed)* |
| `ask_volume` | `ask_vol` |
| `bid_volume` | `bid_vol` |
| `footprint_json` | `footprint` |
| *(new)* | `cluster` |
| *(new)* | `dir` |

### WoodiesBar

| Old Field | New Field |
|-----------|-----------|
| `timestamp` | `ts` |
| `open/high/low/close` | `o/h/l/c` |
| `cci_6` | *(removed — merged into `cci_6_tcci`)* |
| `tcci` | `cci_6_tcci` |
| `cci_34/50/128/200` | *(removed — not in API)* |
| `lsma_25` | `lsma_value` |
| `ema_34_cci` | `ema_34` |
| `turbo_cci_5/8` | *(removed — not in API)* |
| `zlr_pattern` | `zlr_detected` + `zlr_direction` |
| *(new)* | `swi_value`, `czi_value`, `trend_state`, `predictor_next_cci` |

### TPOBar

| Old Field | New Field |
|-----------|-----------|
| `timestamp` | `ts` |
| `price_level` | `price` |
| `tpo_letter` | `letter` |
| `period_label` | `period_id` (int) |
| `is_poc/is_vah/is_val` | *(removed — not in API)* |
| *(new)* | `level` |

### SystemSignal

| Old Field | New Field |
|-----------|-----------|
| `timestamp` | `ts` |
| `signal_type` | `classification` |
| `confidence` | `confidence` (now nullable) |
| `mode` | *(removed — not in signal response)* |
| `metadata_json` | `payload` |

### SystemMarker

| Old Field | New Field |
|-----------|-----------|
| `timestamp` | `ts` |
| `bar_timestamp` | *(removed — use `ts`)* |
| `marker_type` | `type` |
| *(removed)* | `direction`, `label`, `mode` |
| *(new)* | `color`, `border_style`, `payload` |

### Trade

| Old Field | New Field |
|-----------|-----------|
| `system_id` | `system` |
| `entry_time` | `entry_ts` |
| `exit_time` | `exit_ts` |
| `entry_price` | `entry_price` (nullable) |
| `exit_price` | `exit_price` (nullable) |
| `stop_price` | *(removed — see TradeDetailed.stop_initial)* |
| `target_price` | *(removed — see TradeDetailed.t1_price)* |
| `quantity` | *(removed)* |
| `pnl_ticks` | *(removed)* |
| `pnl_dollars` | `pnl_usd` |
| *(new)* | `pnl_r` |
| `outcome` | `outcome` (nullable) |
| `quality_score` | *(removed — see TradeDetailed.quality_review)* |
| `pattern_name` | *(removed)* |
| `notes` | *(removed)* |
| *(new)* | `exit_reason`, `sierra_bracket_id` |

### SystemConfig

| Old Field | New Field |
|-----------|-----------|
| `params_json` | `params` |
| *(new)* | `locked_at`, `locked_by` |

---

## 2. Component Updates (field name alignment)

All components updated to use new field names:

| Component | Changes |
|-----------|---------|
| `ChartArea.tsx` | `b.timestamp` → `b.ts`, `b.open` → `b.o`, etc. |
| `VegasEMAs.tsx` | `bar.close` → `bar.c`, `bar.timestamp` → `bar.ts` |
| `VolumePanel.tsx` | `b.timestamp` → `b.ts`, `b.volume` → `b.vol`, `b.close/open` → `b.c/o` |
| `TopBar.tsx` | `lastBar.close/open` → `lastBar.c/o` |
| `TradeMarkerOverlay.tsx` | Rewritten as colored bar overlay using `entry_ts/exit_ts/system/pnl_usd` |
| `SystemPanelWrapper.tsx` | `signal_type` → `classification`, null-safe `confidence` |
| `System1Panel.tsx` | `metadata_json` → `payload` |
| `System2Panel.tsx` | `s.timestamp` → `s.ts`, `s.signal_type` → `s.classification` |
| `System3Panel.tsx` | `metadata_json` → `payload` |
| `System4Panel.tsx` | `tcci` → `cci_6_tcci`, `cci_34` → `ema_34`, `zlr_pattern` → `zlr_detected/zlr_direction` |
| `System6Panel.tsx` | `metadata_json` → `payload` |
| `TradesTable.tsx` | `system_id` → `system`, `entry_time` → `entry_ts`, `pnl_ticks/pnl_dollars` → `pnl_usd/pnl_r` |
| `TradeDetailsModal.tsx` | Same as TradesTable + `stop_price/target_price` → `exit_reason` |
| `SettingsDrawer.tsx` | `params_json` → `params`, uses `SYSTEM_BORDER_STYLE` constant |

---

## 3. Store Updates

| Store | Changes |
|-------|---------|
| `systemStore.ts` | `params_json` → `params` in `updateConfig` |
| `tradeStore.ts` | `t.entry_time` → `t.entry_ts`, `t.system_id` → `t.system`, `t.pattern_name` → `t.direction` (search) |

---

## 4. System 3 Display Name

- **UI label:** "Footprint" (SYSTEM_NAMES[3])
- **Internal name:** `tick_reversal` (DB, API, bridge)
- **Spec note:** System 3 handles tick_reversal bars + footprint/imbalance observation. "Footprint" is the UI label per SKILL.md.

---

## 5. Stream Name Standardization

No bridge stream files were renamed. The existing convention is correct per SKILL.md:

| Bridge `name` | DLL filename | Redis key | API route |
|---------------|-------------|-----------|-----------|
| `imbalance_flags` | `imbalance_flags.json` | `mems26:v9:imbalance` | `/api/v9/bars/imbalance` |
| `stacked_imbalances` | `stacked_imbalances.json` | `mems26:v9:stacked_imbalance` | `/api/v9/bars/stacked_imbalance` |

Bridge names match DLL filenames (source of truth). Redis/API use shortened forms. This is documented in SKILL.md as intentional.

---

## 6. Backend Pydantic Standardization

`ImbalancePayload.type` default `"imbalance_flags"` and `StackedImbalancePayload.type` default `"stacked_imbalances"` — left as-is. These defaults match what the DLL actually writes in the JSON export. The API POST response returns `"type": "imbalance"` / `"type": "stacked_imbalance"` (short forms). This boundary translation is intentional.

---

## Build Verification

```
Next.js 16.2.6 (Turbopack)
✓ Compiled successfully in 2.1s
✓ TypeScript check passed
✓ Static pages generated (4/4)
```
