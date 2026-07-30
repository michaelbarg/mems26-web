# CC Night Report 2026-07-29→30

## E2E Fire Proof Level A — Baseline (step 1)

| Date | Link 1 Feed | Link 2 Integrity | Link 3 Opening | Link 4 DayType | Link 5 Patterns | Link 6-7 Trades | Link 11 PnL |
|---|---|---|---|---|---|---|---|
| 07-27 | PASS 183 bars | PASS 0 seams | AUCTION_IN NEUTRAL | ? (API timeout) | 12 fires | 3 live, 14 shadow | -$90 |
| 07-29 | FAIL 1 gap | PASS 0 seams | ORR UP 0.5 | ? (API timeout) | 12 fires | **0 trades** | $0 |

**Key finding:** 07-29 had 12 pattern fires but **0 trades**. The fire chain died between detection (Link 5) and the gateway (Link 7). Root cause: the opening anchor TZ bug (cowork fixed the parse, but bars still arrive 5h-shifted → bars land on wrong timestamps → opening window detection fails).

## P0 — 5h ts-skew Investigation

**Root cause confirmed (Rule-5 raw output):**
```
export_ts: 1785354947 (19:55:47 UTC) ← time(nullptr), correct
newest bar ts: 1785336900 (14:55:00 UTC) ← v9_sc_datetime_to_unix(), 5h behind
offset: 18047s = 5.0h
```

**Diagnosis:** The DLL's `v9_sc_datetime_to_unix()` converts Sierra SCDateTime using Excel serial formula. SCDateTime is in the chart's timezone. The chart timezone is **America/Chicago (Central Time, UTC-5)** — NOT America/New_York as documented in CLAUDE.md.

**Proof:** bar_ts 14:55 reinterpreted as CT → 19:55 UTC (matches real time exactly). Reinterpreted as ET → 18:55 UTC (1h short).

**Current correction chain:**
1. Bridge: `_chicago_to_utc()` with `V9_CHART_TZ=America/Chicago` → correct UTC (**working**)
2. Backend: `TS_WHOLE_HOUR_NORMALIZE_V1=1` adds another +1h → **over-corrects by 1h**

**Recommendation:** Set `TS_WHOLE_HOUR_NORMALIZE_V1=0` in `.env`. The bridge fix is sufficient and correct. The normalize was a workaround from when the bridge used the wrong TZ (America/New_York instead of Chicago). With `V9_CHART_TZ=America/Chicago` already set, the double correction adds a spurious +1h.

**Also:** Update CLAUDE.md: "MES chart = New York EST/EDT" → "MES chart = **Chicago CT** (America/Chicago)" — this is the documented truth that was wrong.

## P0 — Seam Guard v2 (three flaws fixed)

1. **Neighbor by ts-proximity from DB** (not batch order — stale bars in batch gave wrong comparator)
2. **Rate-limit**: max 1 log per bar-ts per 5 min (150K lines → manageable)
3. **Quarantine logging** for investigation (so rejected bars can be recovered)

## P2 — Anti-phantom Global

Signal emission blocked when:
- Bar age > 10 min from real time (replay/hydration bars)
- |entry − last_close| > 2% (garbage prices from replay at old levels)

Fail-open: unknown age → allow.

## P1 — DD Classification (partial)

`DD_BIMODAL_RELAX_V1` (OFF): `detected_relaxed = bool(narrow and bimodal)` without the `held` (close-at-extreme) gate. 07-28 had bimodal=True, second_ratio=0.932, but close returned mid-range → the strict `held` gate blocked detection.

**NOT-DONE:** Neutral reclass rule (expansion returns >70% to value = Neutral, not Normal_Variation). The `sides` variable in the classifier needs a new path.

## P4 — Flag Hygiene

`RELEASE_TREND_BYPASS_PTS` (15) + `DAYTYPE_PLAYBOOK_MIN_CONF` (0.4) registered in FLAG_REGISTRY.

## NOT-DONE

- **P0 ts-skew fix in code** — the fix is a config change (`TS_WHOLE_HOUR_NORMALIZE_V1=0`), not code. Cowork/Michael sets it.
- **P1 Neutral reclass** — the classifier's `sides` variable needs a new feature for V-reversal detection
- **P3 lsma_flat calibration** — data study not yet run
- **E2E Level D** — `rebuild_bar_truth.py` from .scid files + FIRE_MATRIX
- **System 0 Phase A3** — shadow direction authority
