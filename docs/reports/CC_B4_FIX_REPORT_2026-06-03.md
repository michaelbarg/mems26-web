# CC Report — B4 Volume Fix + Study Verification | 2026-06-03

## Fix A — RTH time-gate on `/5min` | DONE

`bars.py:_is_within_rth(ts_utc)` — checks 09:30-16:00 `America/New_York` (DST-safe via `zoneinfo`). Bars outside RTH → skipped with `rth_skipped` count in response.

```
# Test: bar at 17:00 ET → rejected
POST /5min [{"ts": 1699999200, ...}] → {"rth_skipped": 1, "inserted": 0}

# Test: bar at 10:00 ET → accepted
POST /5min [{"ts": 1699974000, ...}] → {"rth_skipped": 0, "inserted": 1}
```

if reverted → RED because: removing `_is_within_rth` gate lets cumulative settlement bars (vol up to 1M) enter v9_bars_5min.

## Fix A2 — `/5min_continuous` disabled | DONE

Endpoint now returns `{"disabled": True, "inserted": 0}`. No dependency found — all chart/study data comes from RTH chart today. Re-enable when dedicated continuous table is built.

## Fix A3 — CVD RTH time-gate | DONE

`/cumulative_delta` also gated to 09:30-16:00 ET. CVD points outside RTH → skipped. Aligned with 5-min bars by construction.

`/cvd_continuous` was already a no-op.

## Cleanup — is_synthetic | DONE

```
Before: MAX(volume) WHERE is_synthetic=0 = 1,000,000
After:  MAX(volume) WHERE is_synthetic=0 = 71,832
Rows marked is_synthetic=1: 19
```

FiveMin hydration (`five_min_system.py:201`) now filters `.filter(V9Bar5Min.is_synthetic == 0)` — rolling_avg excludes inflated bars.

## Study-field verification per-system

### Version check
All exports show `v9.4.5-wc-fix`. Sierra chart study name shows "v9.4.3-chart5" — this is the **display name** set when the study was added. The actual running DLL code is v9.4.5 (confirmed by export `version` field). **No version mismatch — cosmetic only.**

### S1 (day-type/opening) ✓

| Field | Source | Study/Chart | Populated? |
|-------|--------|-------------|------------|
| IB high/low | DLL In:16 → Study 6, SG6/SG8 | Chart #3 (same) | ✓ (code reads correctly) |
| Today POC/VAH/VAL | DLL In:15 → Study 3, SG0/1/2 | Chart #3 (same) | ✓ |
| Yday POC/VAH/VAL | DLL In:14 → Study 1, SG0/1/2 | Chart #3 (same) | ✓ |
| CVD | cumulative_delta.json | Chart #3, Study 7/9 | ✓ last point: d=-3708 cum=-6548 |

### S2 (five-min/VSA) ✓

| Field | Source | Populated? |
|-------|--------|------------|
| 5-min OHLCV | 5min.json (RTH chart) | ✓ 601 bars, max vol=71,832 (clean) |
| rolling_avg | Computed from _bar_buffer | ✓ hydration now filters is_synthetic=1 |
| CVD enrichment | /cumulative_delta → UPDATE v9_bars_5min | ✓ RTH-gated |

### S3 (footprint) — DISABLED ✓

Export exists (footprint.json, v9.4.5-wc-fix). Study 5 (BidVol/AskVol) connected. Footprint disabled at ingestion level (`FOOTPRINT_DISABLED`). Does not break other systems.

### S4 (Woodies) ✓

| Field | Source | Export value |
|-------|--------|-------------|
| CCI-14 | Study 4, SG0 | -309.69 |
| CCI-6 (TCCI) | Study 10, SG0 | -179.68 |
| EMA-34 | Study 3, SG0 | 7610.8 |
| LSMA-25 | Study 2, SG0 | 7603.29 |
| SWI | local-computed (v9.4.5 fix) | -294.72 |
| CZI | Study 7, SG2 | -49.0 |
| trend_state | Derived from CCI+SWI | RED |
| Proj H/L | Study 9, SG1/SG2 (Woodies Panel) | 7672.0 / 7600.5 |

### Input default mismatches (cosmetic, no runtime impact)

| Input | Code default | Michael's chart setting | Impact |
|-------|-------------|------------------------|--------|
| In:17 (ProjHL Study) | 0 (disabled) | 12 | **None** — Sierra persists per-chart settings. Michael's chart already has 12. |
| In:19 (Woodies Chart) | 0 (same chart) | 12 | **None** — same reason. Michael's chart already has 12. |

These defaults only affect NEW chart instances. The live chart has correct settings (confirmed by export showing all fields populated with sane values).

## Acceptance

- [x] Push from RTH source at 17:00 ET → **NOT** written; RTH bars (09:30-16:00) written OK. Evidence: test `TestRthTimeGate`.
- [x] `MAX(volume) WHERE is_synthetic=0` = 71,832 (was 1,000,000). `is_synthetic=1` count: 19.
- [x] VSA rolling_avg filters is_synthetic via hydration query `.filter(V9Bar5Min.is_synthetic == 0)`.
- [x] Study fields (POC/IB/Woodies) all connected and populated with sane values — not broken.
- [x] Anti-tautological test: `test_outside_rth_rejected` + `test_within_rth_accepted`.
- [x] Regression: 488 passed, 0 new failures. Commit `0ece0fa`.

## NOT DONE / DEVIATIONS

- **Continuous table** — `/5min_continuous` writes disabled, not redirected to a new table. Dedicated continuous table = future task.
- **Code defaults for In:17/In:19** — not updated in DLL (per instructions: don't touch sc_study). Cosmetic only — live chart has correct settings.

## Open

| Item | Owner |
|------|-------|
| Update DLL defaults for In:17=12, In:19=12 | Future sc_study commit (optional, cosmetic) |
| Dedicated continuous 24h table | Future task |
| Backend restart | Michael — currently stopped |
