# SOT_HEALTH — Source of Truth Health Check

> **Purpose:** Pre-LIVE / pre-market data freshness audit. For every MEMS26
> system, lists what it receives from Sierra Chart, what it computes
> internally, where it persists, and the live freshness of each source.
>
> **Refresh:** `python3 scripts/sot_health.py` (rewrites the live block below
> in place; the per-system reference is static).
>
> **Strict mode for launchd / pre-market:**
> `python3 scripts/sot_health.py --strict` exits 1 on any STALE/MISSING.

<!-- LIVE_BLOCK_START -->

**Last run:** 2026-06-25 13:49:22 IL  ·  2026-06-25 06:49:22 ET  ·  market: **OFF-HOURS**  ·  duration: 247ms

**Overall: 🔴 MISSING**

## Live status — per system

| System | Sierra inputs | Computed | DB tables | API | Status |
|--------|---------------|----------|-----------|-----|--------|
| **S0_BARS** — Bars / Price / Flow | `5min.json`, `cumulative_delta.json`, `volume_profile.json`, `footprint.json`, `tick_reversal_12.json`, `tick_reversal_15.json`, `imbalance_flags.json`, `live_price.json` | — | `v9_bars_5min.ts`<br>`v9_bars_cumulative_delta.ts`<br>`v9_bars_volume_profile.ts`<br>`v9_bars_footprint.ts`<br>`v9_bars_tick_reversal.ts`<br>`v9_bars_imbalance.ts` | `/api/v9/chart/bars5min`<br>`/api/v9/health`<br>`/api/v9/footprint/current` | 🔴 MISSING |
| **S5_TPO** — TPO / POC / VAH / VAL / IB | `tpo.json` | • S5 IB-from-Sierra normalization (no fallback synthesis)<br>• session-aware POC/VAH/VAL persistence to v9_tpo_history (B1 snapshotter) | `v9_tpo_history.ts`<br>`v9_tpo_bars.ts` | `/api/v9/tpo/current`<br>`/api/v9/key_levels` | 🔴 MISSING |
| **S1_DAY_TYPE** — Day Type State Machine | `5min.json` | • IB high/low/width over 09:30–10:30 ET (S1 authoritative)<br>• Globex / RTH range from 5min bars<br>• Day type classification (TND_UP, TND_DN, NEU_E, NEU_C, RNG, NT)<br>• Opening type (OD/ORR/OTD/OAOR) | `v9_day_type_history.last_updated_at`<br>`v9_day_type_state.ts` | `/api/v9/day_type/v9/current`<br>`/api/v9/key_levels` | 🔴 MISSING |
| **S2_FIVE_MIN** — Five-Min Patterns (FHB / Reactive / Initiative) | `5min.json` | • FHB (First Hour Break)<br>• Reactive Long / Short (volume + delta confluence)<br>• Initiative Long / Short<br>• Quiet lookback patterns<br>• Confluence stack (S2 + day_type + tpo levels) | `v9_five_min_setups.ts`<br>`v9_five_min_state.last_processed_ts` | `/api/v9/build/pattern-status` | 🔴 MISSING |
| **S4_WOODIES** — Woodies CCI Patterns + W-10 TimeStop | `woodies_5min.json`, `woodies_30min.json`, `woodies_diag.json` | • Pattern detectors (9 patterns × directions)<br>• W-10 TimeStop enforcement (90 min / 18 bars)<br>• Trail / Exit discipline (D-092)<br>• ZLR / HFE / LSMA-above-price flags from DLL | `v9_bars_5min_woodies.ts`<br>`v9_bars_30min_woodies.ts`<br>`v9_woodies_signals.ts`<br>`v9_woodies_patterns.ts` | `/api/v9/woodies/current` | 🔴 MISSING |
| **TRADE_MANAGER** — Trade Manager / Bar-Level Detector | — | • Stop / target hit detection (per bar)<br>• Trade close → close_trade(reason)<br>• P&L compute on close | `v9_trades.entry_ts` | `/api/v9/trades/active` | 🔴 MISSING |
| **KILLZONE** — Killzone / Chop Score | `5min.json` | • Killzone classification (currently active / off)<br>• Chop score (0-100) from ATR / range | `v9_killzone_log.ts`<br>`v9_chop_score.ts` | — | 🔴 MISSING |

## Cross-source consistency (Sierra ↔ DB ↔ API)

| Check | Result | Detail |
|-------|--------|--------|
| Cross-check: IB consistency (Sierra ↔ DB ↔ API) | 🟢 FRESH | agree @ 7472.5 (['sierra', 'api']) |
| Cross-check: day_type API vs DB | ℹ️ INFO | both pre-classification (likely pre-10:30 ET) |
| Cross-check: bridge TZ (no 1h Chicago drift) | 🟢 FRESH | ET-anchored (no future drift) |

## Freshness probes — per system breakdown

### 🔴 S0_BARS — Bars / Price / Flow

_Pure pass-through. Sierra DLL writes JSON → bridge POSTs to API → DB row. **No backend computation.** If the row is stale, the bridge or DLL is the issue, not the system._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: 5min.json | 🟢 FRESH | 2s | 86,638B |
| Sierra: cumulative_delta.json | 🟢 FRESH | 2s | 5,967B |
| Sierra: volume_profile.json | 🟢 FRESH | 2s | 75,146B |
| Sierra: footprint.json | 🟢 FRESH | 2s | 93,084B |
| Sierra: tick_reversal_12.json | 🟢 FRESH | 2s | 17,613B |
| Sierra: tick_reversal_15.json | 🟢 FRESH | 2s | 16,104B |
| Sierra: imbalance_flags.json | 🟢 FRESH | 2s | 161B |
| Sierra: live_price.json | 🟢 FRESH | 0s | 74B |
| DB: v9_bars_5min.ts | 🔴 MISSING | 469h | last=2026-06-05T20:55:00 |
| DB: v9_bars_cumulative_delta.ts | 🔴 MISSING | 1173h | last=2026-05-07 13:19:59 |
| DB: v9_bars_volume_profile.ts | 🔴 MISSING | 430h | last=2026-06-07 11:52:21 |
| DB: v9_bars_footprint.ts | 🔴 MISSING | 430h | last=2026-06-07 11:53:00 |
| DB: v9_bars_tick_reversal.ts | 🔴 MISSING | — | no rows |
| DB: v9_bars_imbalance.ts | 🔴 MISSING | 429h | last=2026-06-07T13:04:24 |
| API: /api/v9/chart/bars5min | 🟢 FRESH | — | 200 OK |
| API: /api/v9/health | 🟢 FRESH | — | 200 OK |
| API: /api/v9/footprint/current | 🟢 FRESH | — | 200 OK |

### 🔴 S5_TPO — TPO / POC / VAH / VAL / IB

_Sierra TPO Studies (ID 1=yesterday, ID 3=today, ID 6=IB). Two consumers: `/tpo/current` reads **tpo.json directly** (sub-30s freshness for chart). `/key_levels` reads **DB** (`v9_tpo_sessions`, `v9_day_type_history`). **IB synthesis from bars is FORBIDDEN** (2026-05-28 evening revocation): if Sierra `ib.found=false`, the API returns `ib_source='missing'`._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: tpo.json | 🟢 FRESH | 2s | 480B |
| DB: v9_tpo_history.ts | 🔴 MISSING | 500h | last=2026-06-04 14:30:00 |
| DB: v9_tpo_bars.ts | 🔴 MISSING | 22884h | last=2023-11-14T22:21:40 |
| API: /api/v9/tpo/current | 🟢 FRESH | — | 200 OK |
| API: /api/v9/key_levels | 🟢 FRESH | — | 200 OK |

### 🔴 S1_DAY_TYPE — Day Type State Machine

_Authoritative IB after 10:30 ET lock. Stages A1→A4. Computes `day_type`, `opening_type`, `ib_width_class`, fade-zones. Pre-RTH: row is DEVELOPING/NULL by spec. **TZ rule:** Sierra Inputs Start=09:30 / End=10:29 are interpreted as ET (not UTC, not Chicago)._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: 5min.json | 🟢 FRESH | 2s | 86,638B |
| DB: v9_day_type_history.last_updated_at | 🔴 MISSING | 499h | last=2026-06-04 14:53:34 |
| DB: v9_day_type_state.ts | 🔴 MISSING | — | no rows |
| API: /api/v9/day_type/v9/current | 🟢 FRESH | — | 200 OK |
| API: /api/v9/key_levels | 🟢 FRESH | — | 200 OK |

### 🔴 S2_FIVE_MIN — Five-Min Patterns (FHB / Reactive / Initiative)

_Pattern detection from 5min bars + day-type context. **Volume key alias** added 2026-05-28 (bridge `vol` → detector `v`). FHB only fires within first hour of RTH. Reactive/Initiative/Quiet patterns gated on day_type auth-table._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: 5min.json | 🟢 FRESH | 2s | 86,638B |
| DB: v9_five_min_setups.ts | 🔴 MISSING | — | no rows |
| DB: v9_five_min_state.last_processed_ts | 🔴 MISSING | — | no rows |
| API: /api/v9/build/pattern-status | 🟢 FRESH | — | 200 OK |

### 🔴 S4_WOODIES — Woodies CCI Patterns + W-10 TimeStop

_Sierra Woodies Studies (Input 18). Patterns: ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE. **W-10 TimeStop** (Registry #11) is the SOLE TIME_STOP authority — 90 min flat-out, fixed 2026-05-28 evening (Bug A: bar-count per closed bar; Fix #5: exit_price set before close_trade)._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: woodies_5min.json | 🟢 FRESH | 2s | 32,245B |
| Sierra: woodies_30min.json | 🟢 FRESH | 2s | 19,917B |
| Sierra: woodies_diag.json (optional) | ℹ️ INFO | 860h | 1,059B (informational) |
| DB: v9_bars_5min_woodies.ts | 🔴 MISSING | 18067h | last=2024-06-02T14:55:00 |
| DB: v9_bars_30min_woodies.ts | 🔴 MISSING | 1173h | last=2026-05-07T13:00:00 |
| DB: v9_woodies_signals.ts | 🟡 STALE | 67h | last=2026-06-22T15:19:14 |
| DB: v9_woodies_patterns.ts | 🔴 MISSING | — | no rows |
| API: /api/v9/woodies/current | 🟢 FRESH | — | 200 OK |

### 🔴 TRADE_MANAGER — Trade Manager / Bar-Level Detector

_Owns trade lifecycle: open, monitor, exit. **Layer 4 TIME_STOP removed 2026-05-28 evening** — W-10 is now the sole TIME_STOP authority. Layer 4 still owns stop-hit / target-hit detection._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| DB: v9_trades.entry_ts | 🔴 MISSING | 522h | last=2026-06-03 15:50:04 |
| API: /api/v9/trades/active | 🟢 FRESH | — | 200 OK |

### 🔴 KILLZONE — Killzone / Chop Score

_Time-of-day kill switch (NY open / lunch / power hour). Chop score from 5min bar volatility. Gates pattern firing per Constitution V3._

| Source | Status | Age | Detail |
|--------|--------|-----|--------|
| Sierra: 5min.json | 🟢 FRESH | 0s | 86,638B |
| DB: v9_killzone_log.ts | 🔴 MISSING | — | no rows |
| DB: v9_chop_score.ts | 🔴 MISSING | — | no rows |

<!-- LIVE_BLOCK_END -->

---

## Reference — Per-system inventory

> The tables below describe the **stable** wiring of each system. They do not
> change between runs. The live block above is the only thing the script
> mutates.


### Sierra Chart Study Inputs

| Input | Name | Default | Purpose |
|-------|------|---------|---------|
| 4 | V9 Export Directory | `~/SierraChart_Data/v9_export/` | All JSON files |
| 13 | TPO Yesterday Study ID | 1 | Prev day POC/VAH/VAL |
| 14 | TPO Today Study ID | 3 | Today POC/VAH/VAL |
| 15 | Initial Balance Study ID | 6 | IB high (subgraph 6) / IB low (subgraph 8) |
| 16 | Projected H/L Study ID | 0 | proj_hi / proj_lo for Woodies |
| 17 | TPO Chart Number | 0 | Chart hosting TPO+IB |
| 18 | Woodies Chart Number | 0 | Chart hosting Woodies studies |

### What each system receives vs computes

#### S0_BARS — Bars / Price / Flow

_Pure pass-through. Sierra DLL writes JSON → bridge POSTs to API → DB row. **No backend computation.** If the row is stale, the bridge or DLL is the issue, not the system._

- **Sierra inputs:** `5min.json`, `cumulative_delta.json`, `volume_profile.json`, `footprint.json`, `tick_reversal_12.json`, `tick_reversal_15.json`, `imbalance_flags.json`, `live_price.json`
- **Backend computes:**
  - _pass-through — no backend computation_
- **DB tables (writes):** `v9_bars_5min.ts`, `v9_bars_cumulative_delta.ts`, `v9_bars_volume_profile.ts`, `v9_bars_footprint.ts`, `v9_bars_tick_reversal.ts`, `v9_bars_imbalance.ts`
- **API endpoints:** `/api/v9/chart/bars5min`, `/api/v9/health`, `/api/v9/footprint/current`

#### S5_TPO — TPO / POC / VAH / VAL / IB

_Sierra TPO Studies (ID 1=yesterday, ID 3=today, ID 6=IB). Two consumers: `/tpo/current` reads **tpo.json directly** (sub-30s freshness for chart). `/key_levels` reads **DB** (`v9_tpo_sessions`, `v9_day_type_history`). **IB synthesis from bars is FORBIDDEN** (2026-05-28 evening revocation): if Sierra `ib.found=false`, the API returns `ib_source='missing'`._

- **Sierra inputs:** `tpo.json`
- **Backend computes:**
  - S5 IB-from-Sierra normalization (no fallback synthesis)
  - session-aware POC/VAH/VAL persistence to v9_tpo_history (B1 snapshotter)
- **DB tables (writes):** `v9_tpo_history.ts`, `v9_tpo_bars.ts`
- **API endpoints:** `/api/v9/tpo/current`, `/api/v9/key_levels`

#### S1_DAY_TYPE — Day Type State Machine

_Authoritative IB after 10:30 ET lock. Stages A1→A4. Computes `day_type`, `opening_type`, `ib_width_class`, fade-zones. Pre-RTH: row is DEVELOPING/NULL by spec. **TZ rule:** Sierra Inputs Start=09:30 / End=10:29 are interpreted as ET (not UTC, not Chicago)._

- **Sierra inputs:** `5min.json`
- **Backend computes:**
  - IB high/low/width over 09:30–10:30 ET (S1 authoritative)
  - Globex / RTH range from 5min bars
  - Day type classification (TND_UP, TND_DN, NEU_E, NEU_C, RNG, NT)
  - Opening type (OD/ORR/OTD/OAOR)
- **DB tables (writes):** `v9_day_type_history.last_updated_at`, `v9_day_type_state.ts`
- **API endpoints:** `/api/v9/day_type/v9/current`, `/api/v9/key_levels`

#### S2_FIVE_MIN — Five-Min Patterns (FHB / Reactive / Initiative)

_Pattern detection from 5min bars + day-type context. **Volume key alias** added 2026-05-28 (bridge `vol` → detector `v`). FHB only fires within first hour of RTH. Reactive/Initiative/Quiet patterns gated on day_type auth-table._

- **Sierra inputs:** `5min.json`
- **Backend computes:**
  - FHB (First Hour Break)
  - Reactive Long / Short (volume + delta confluence)
  - Initiative Long / Short
  - Quiet lookback patterns
  - Confluence stack (S2 + day_type + tpo levels)
- **DB tables (writes):** `v9_five_min_setups.ts`, `v9_five_min_state.last_processed_ts`
- **API endpoints:** `/api/v9/build/pattern-status`

#### S4_WOODIES — Woodies CCI Patterns + W-10 TimeStop

_Sierra Woodies Studies (Input 18). Patterns: ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE. **W-10 TimeStop** (Registry #11) is the SOLE TIME_STOP authority — 90 min flat-out, fixed 2026-05-28 evening (Bug A: bar-count per closed bar; Fix #5: exit_price set before close_trade)._

- **Sierra inputs:** `woodies_5min.json`, `woodies_30min.json`, `woodies_diag.json`
- **Backend computes:**
  - Pattern detectors (9 patterns × directions)
  - W-10 TimeStop enforcement (90 min / 18 bars)
  - Trail / Exit discipline (D-092)
  - ZLR / HFE / LSMA-above-price flags from DLL
- **DB tables (writes):** `v9_bars_5min_woodies.ts`, `v9_bars_30min_woodies.ts`, `v9_woodies_signals.ts`, `v9_woodies_patterns.ts`
- **API endpoints:** `/api/v9/woodies/current`

#### TRADE_MANAGER — Trade Manager / Bar-Level Detector

_Owns trade lifecycle: open, monitor, exit. **Layer 4 TIME_STOP removed 2026-05-28 evening** — W-10 is now the sole TIME_STOP authority. Layer 4 still owns stop-hit / target-hit detection._

- **Sierra inputs:** _none — pure compute_
- **Backend computes:**
  - Stop / target hit detection (per bar)
  - Trade close → close_trade(reason)
  - P&L compute on close
- **DB tables (writes):** `v9_trades.entry_ts`
- **API endpoints:** `/api/v9/trades/active`

#### KILLZONE — Killzone / Chop Score

_Time-of-day kill switch (NY open / lunch / power hour). Chop score from 5min bar volatility. Gates pattern firing per Constitution V3._

- **Sierra inputs:** `5min.json`
- **Backend computes:**
  - Killzone classification (currently active / off)
  - Chop score (0-100) from ATR / range
- **DB tables (writes):** `v9_killzone_log.ts`, `v9_chop_score.ts`
- **API endpoints:** —

### Freshness threshold rules

| Window | Fresh ≤ | Stale ≤ | Missing > |
|--------|---------|---------|-----------|
| RTH (09:30–16:00 ET, Mon–Fri) | 60s | 300s | 300s |
| Off-hours / weekend | 360m | 96h | 96h |

### Source-of-Truth discipline (CLAUDE.md)

- **Rule 1 — Honest failure > synthetic value.** When Sierra is silent, propagate `None` / `"missing"`. Never synthesize from another source and tag it with the canonical source's `found` flag.
- **Rule 2 — Verify before you trust.** Run the equivalent DB/bar-math query before believing any UI screenshot or assertion.
- **Rule 3 — `min`/`max` aggregators are amplifiers.** Audit every downstream `min`/`max` for a synthesis fix.
- **Rule 4 — TZ ambiguity is forbidden.** Every `HH:MM:SS` spec value must carry its TZ in the value, comment, or boundary conversion.
- **Rule 5 — Verification quote, not assertion.** "Should work" claims require pasted command + raw output.
