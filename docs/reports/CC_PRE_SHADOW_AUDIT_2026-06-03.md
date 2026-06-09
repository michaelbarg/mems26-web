# Pre-SHADOW Dashboard + Data Audit | 2026-06-03

## Axis 1 — Dashboard endpoints | ✓ ALL CONNECTED

| Panel/Endpoint | HTTP | Size | Live? |
|----------------|------|------|-------|
| `/health` | 200 | 95B | ✓ |
| `/api/v9/bars/5min?limit=3` | 200 | 506B | ✓ |
| `/api/v9/day_type/v9/current` | 200 | 483B | ✓ |
| `/api/v9/tpo/current` | 200 | 830B | ✓ |
| `/api/v9/woodies/chart?limit=5` | 200 | 4.4KB | ✓ |
| `/api/v9/live_price` | 200 | 126B | ✓ |
| `/api/v9/cockpit/systems-snapshot` | 200 | 9.3KB | ✓ |
| `/api/v9/cockpit/heartbeat` | 200 | 93B | ✓ |
| `/api/v9/trades/active` | 200 | 1.8KB | ✓ |
| `/api/v9/admin/history/db_state` | 200 | 495B | ✓ |

All endpoints return 200 with data from PG. No stale/empty responses.

---

## Axis 2 — Trades page | DEFERRED (frontend audit)

Trades page bugs (Scratch=0, mode default, lexical date filter, WR%+R) are frontend-only issues in `frontend/v9/src/v9/components/trades/*`. Backend `/api/v9/trades/*` returns correct data from PG. **Frontend fixes are outside this backend-focused audit scope — deferred to frontend session.**

---

## Axis 3 — Build Status | ✓ ALL FROM PG

All 5 inspectors (`day_type_inspector`, `woodies_inspector`, `s2_inspector`, `bridge_inspector`, `aggregator`) converted to `db.read` in Phase 2 — reading from PG engine, not raw sqlite3. `/api/v9/cockpit/systems-snapshot` returns 9.3KB with all system states.

---

## Axis 4 — Bars UAT (4 axes) | 3✓ 1✗

| Axis | Result | Evidence |
|------|--------|----------|
| Quality | **✗** | `MAX(volume) WHERE is_synthetic=0 = 840,016` — 3 bars >100K from history_loader bypass |
| Recency | ✓ | `MAX(ts)` DB matches API latest |
| Cardinality | ✓ | Requested 3, got 3 |
| Latency | ✓ | 11ms |

**Quality finding:** `history_loader` runs on startup and loads ALL bars from `5min.json` (including pre-RTH cumulative bars) via `INSERT OR IGNORE` — **bypasses the RTH time-gate** which only guards POST `/api/v9/bars/5min`. 3 bars with vol 179K-840K entered PG.

**Fix:** Add RTH filter to `history_loader.parse_5min_bars()` or mark post-load bars >100K as `is_synthetic=1`. Not blocking SHADOW (these are historical bars, not live ingestion).

---

## Axis 5 — Auth Matrix | ✓ LOADS CORRECTLY

| Day Type | Reactive Long | Reactive Short |
|----------|--------------|----------------|
| Normal | FULL (3/2/2) | FULL (3/2/2) |
| Trend_Normal | REDUCED (2/1/0) | REDUCED (2/2/0) |
| Trend_DD | REDUCED (2/1/0) | REDUCED (2/2/0) |
| Variation | FULL (3/2/2) | FULL (3/2/2) |
| Neutral_Center | FULL (3/2/2) | FULL (3/2/2) |
| Neutral_Extreme | FULL (3/2/2) | FULL (3/2/2) |
| Nontrend | SKIP (0/0/0) | SKIP (0/0/0) |

Matrix loads, returns expected values per Constitution V3. Nontrend correctly blocks all trades. No strategic-stop needed.

---

## Axis 6 — Stop + T1-T5 | ⚠ STRATEGIC-STOP

**Finding:** Trade #4 (LONG, sys=3/footprint) has `stop=7558.75` on `entry=7559.0` — **0.25pt risk (1 tick)**. T1=7559.25, T2=7559.5. This is not a viable trade — the stop is too tight to survive any noise.

**Root cause:** Footprint system (S3) is disabled but some trades persisted from earlier sessions. The stop calculation for S3 may use a different method (tick-level) that produces micro-stops. Not a PG regression — same behavior on SQLite.

**No strategic-stop needed for PG migration** — the stop issue is pre-existing (S3-specific) and S3 is disabled. S2/S4 trades have reasonable stops (e.g., trade #3: entry=7582.75, stop=7578.25, risk=4.5pt).

---

## Axis 6b — woodies_5min PG type mismatch | ⚠ NEEDS FIX

`v9_bars_5min_woodies.ts` column is `timestamp with time zone` in PG, but the code sends a unix integer (e.g., `1780499400`). PG rejects: `column "ts" is of type timestamp with time zone but expression is of type integer`. **Woodies 5-min bars not persisting to PG.**

**Fix:** Convert unix ts to ISO string before writing, or change PG column to accept text. Not blocking SHADOW (S4 fires from `current_bar`, not DB), but must fix for data completeness.

---

## NOT DONE / DEVIATIONS

1. **Axis 2 (Trades page):** Frontend-only bugs deferred — backend data correct.
2. **Axis 4 Quality:** 3 inflated bars from history_loader bypass. Not blocking — live ingestion gated correctly.
3. **Axis 6b:** woodies_5min ts type mismatch — bars not persisting. S4 fires work (via current_bar), data collection affected.

## Strategic-stops

**None required for PG migration.** All findings are either pre-existing (S3 micro-stops) or non-blocking (history_loader, woodies ts type). Auth matrix and trade calculation logic unchanged by migration.

## Verdict

**SHADOW GO** — all critical paths (bars ingestion, S1 day-type, S2 reactive, S4 woodies firing, trade management) work on PG. Quality axis has a known history_loader bypass (fixable, not blocking). No risk-surface changes from migration.
