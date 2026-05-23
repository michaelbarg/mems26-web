UNIFIED HISTORY ARCHITECTURE — 2026-05-22 10:45 ET

=== Sub-question decisions ===

1. Historical depth source: B (EOD archiver, extended)
   Reasoning: The EOD archiver already exists (eod_archiver.py, 10/14 files),
   preserves full-fidelity Sierra JSON snapshots, and requires zero DLL work.
   Sierra's rolling-tail exports (50–600 bars per stream) provide sufficient
   intra-day coverage for startup gap-fill without needing .scid replay or DLL
   extensions. Path A (DLL) violates Michael's constraint ("if it works don't
   break it") and Path C (.scid replay) carries high drift risk and effort.
   The one gap — the archiver has NEVER run (archive dir doesn't exist) — is
   trivially fixed by wiring an auto-trigger. Four missing files
   (live_price.json, tick_reversal_12.json, tick_reversal_15.json,
   reversal_cluster.json) should be added to ARCHIVED_FILES for completeness.

2. Startup gap-fill detection: alpha (per-table MAX(ts) vs rolling-tail export)
   Reasoning: On startup, each stream's current Sierra export contains a
   rolling tail of recent bars. The simplest correct gap-fill is: read the
   current export, compare each bar's ts against MAX(ts) in the target DB
   table, and INSERT any bars newer than that. This handles short gaps (minutes
   to hours) automatically with no archive dependency. For longer gaps
   (days+), fall back to reading archived JSONs for dates between MAX(ts) and
   today. Per-table MAX(ts) is a single indexed query — trivial, fast, and
   correct. Sub-daily granularity (path beta) isn't needed because the rolling
   exports already provide that resolution. Full replay (path gamma) risks
   processing gigabytes of duplicates on a fresh DB.

3. EOD trigger: ii (FastAPI lifecycle hook + market_clock scheduler)
   Reasoning: The backend already runs the TPO snapshotter as an asyncio
   background task wired through FastAPI lifespan events, using market_clock
   for RTH-aware scheduling. The pattern is proven and self-contained —
   survives launchctl restarts, honours holidays/half-days, and needs no
   OS-level cron. The trigger should fire at 15:55 ET (5 min before RTH
   close, matching the crontab example already in history_routes.py:75) so
   the archive captures the final session state. The bridge (path iii) has
   no scheduler infrastructure and shouldn't gain one.

4. Manual replay surface:
   `POST /api/v9/history/replay?from=YYYY-MM-DD&to=YYYY-MM-DD`
   Reasoning: Reads archived JSONs for each date in the range, parses the
   bars[]/points[]/history[] arrays, and ingests into the corresponding DB
   tables using INSERT OR IGNORE (deduplicate on bar_id UNIQUE). Returns a
   per-table summary: {table: rows_inserted, rows_skipped}. This satisfies
   Michael's "fill from date X to Y" ask. Single-date shorthand:
   `POST /api/v9/history/replay/2026-05-20` (no from/to needed). The
   endpoint reuses the existing eod_archiver.read_archive() for file I/O
   and the existing POST handler INSERT logic (or a shared _ingest_bars
   helper) for DB writes.


=== Wiring bug analysis (4 zero-row dedicated tables) ===

These are NOT data-loss bugs — all 4 streams store data elsewhere:

| Stream | Bridge POSTs to | Handler action | Where data lands | Dedicated table |
|--------|----------------|----------------|------------------|-----------------|
| CVD | /api/v9/bars/cumulative_delta | UPDATE v9_bars_5min.cumulative_delta | v9_bars_5min (1900/1900 enriched) | v9_bars_cumulative_delta: 0 rows |
| Volume Profile | /api/v9/bars/volume_profile | UPDATE v9_bars_5min.poc_vol/vah/val | v9_bars_5min (1599 enriched BUT values=0.0) | v9_bars_volume_profile: 0 rows |
| Imbalance | /api/v9/bars/imbalance | INSERT v9_system_signals (class=IMBALANCE) | v9_system_signals (41,352 rows) | v9_bars_imbalance: 0 rows |
| Stacked Imb | /api/v9/bars/stacked_imbalance | INSERT v9_system_signals (class=STACKED_IMBALANCE) | v9_system_signals (0 rows — genuinely sparse data) | v9_bars_stacked_imbalance: 0 rows |

Critical sub-finding: VP enrichment writes zeros (poc_vol > 0: 0 rows). The
handler reads bar.get("poc_vol") but the volume_profile.json export likely uses
different keys (e.g., "poc", "total_vol"). This is a real field-name mismatch
bug in the VP enrichment path — data arrives but gets written as 0.

Decision needed: should the dedicated tables be populated alongside the
current enrichment/signal paths, or are they vestigial? The HistoricalReplay
service (historical_replay.py:96-106) tries to replay from them — if
HistoricalReplay is to work, the dedicated tables need writers. Recommendation:
add INSERT into dedicated tables as a secondary write in each POST handler
(~15 LOC each), keeping the existing enrichment/signal path unchanged.


=== Per-stream plan ===

| Stream | Current state | Gap | Fix needed | LOC | Risk | Effort |
|--------|---------------|-----|------------|-----|------|--------|
| 5min bars | 1900 rows, live, from 2026-04-19 | startup gap-fill | Gap-fill ingester reads 5min.json bars[] on boot | ~40 | LOW | 2h |
| CVD bars | 0 dedicated rows, enrichment works (1900 in 5min) | dedicated table empty + no gap-fill | Add INSERT into v9_bars_cumulative_delta in POST handler + gap-fill from export | ~50 | LOW | 2h |
| Volume profile bars | 0 dedicated rows, enrichment broken (zeros) | field-name mismatch + dedicated table empty | Fix VP field mapping in POST handler + add INSERT into dedicated table + gap-fill | ~60 | LOW | 3h |
| Footprint bars | 2457 rows, live, from 2026-05-12 | only 10 days history | Gap-fill from archive (if archives populated) + rolling-tail on startup | ~40 | LOW | 2h |
| Footprint journal | 132k rows, plenty | none | — | — | — | — |
| Imbalance bars | 0 dedicated rows, 41k signals in v9_system_signals | dedicated table empty | Add INSERT into v9_bars_imbalance in POST handler + gap-fill from export | ~40 | LOW | 2h |
| Stacked-imb bars | 0 dedicated rows, 0 signals (genuinely sparse) | dedicated table empty | Add INSERT into v9_bars_stacked_imbalance in POST handler | ~30 | LOW | 1h |
| Woodies 5min bars | 1.88M rows, live | none | — | — | — | — |
| Woodies 30min bars | 3.20M rows, live | none | — | — | — | — |
| Tick reversal bars | 8.14M rows, live | none | — | — | — | — |
| TPO sessions | 18 rows, daily | deeper history (nice-to-have) | Archiver captures tpo.json; replay can backfill | ~20 | LOW | 1h |
| TPO history (B1) | 0 -> growing today | DONE | Cursor shipped 2026-05-22 AM | DONE | DONE | DONE |
| TPO journal | 13k rows, letter restart-dup bug (CC #2 noted) | dup letters on restart | Not blocking; fix is in _open_session letter-idx recovery | ~15 | LOW | 1h |
| Day-type state | 13k rows, plenty | none | — | — | — | — |
| Day-type history | 6 rows, UPSERT | none | — | — | — | — |
| Trades | 1299 rows, live | none | — | — | — | — |
| EOD archiver | exists, 10 files, NEVER RUN | no archive dir, no auto-trigger | Wire lifecycle auto-trigger + first manual run + add 4 missing files | ~60 | LOW | 2h |


=== Recommended phasing ===

PHASE 1 (~6h, blocks: NONE):
  - Wire EOD archiver auto-trigger via FastAPI lifespan + market_clock (fire at 15:55 ET)
  - Add 4 missing files to ARCHIVED_FILES: live_price.json, tick_reversal_12.json, tick_reversal_15.json, reversal_cluster.json
  - Run first manual archive: POST /api/v9/history/archive_now (populate today)
  - Fix VP field-name mismatch in POST /api/v9/bars/volume_profile handler
  - Add secondary INSERT into dedicated tables for CVD, VP, imbalance, stacked-imbalance POST handlers
  - Regression tests for all 4 POST handlers (INSERT path) + archiver auto-trigger
  Acceptance: archive dir exists with today's date + 14 files; all 4 dedicated tables gain rows on next bridge push; archiver fires autonomously at 15:55 ET

PHASE 2 (~5h, blocks: PHASE 1):
  - Build startup gap-fill service: on backend boot, for each stream:
    1. Query MAX(ts) from target DB table
    2. Read current Sierra export JSON
    3. Parse bars[]/points[]/history[] array
    4. INSERT OR IGNORE rows newer than MAX(ts)
  - Wire into FastAPI lifespan (after HistoricalReplay warm-up, before accepting requests)
  - Cover: 5min, footprint, CVD, VP, imbalance, stacked-imb, woodies (if gap detected), tick-reversal (if gap detected)
  - Regression test: simulate 1h gap by deleting recent rows, restart, verify gap filled
  Acceptance: backend restart after 1h downtime fills the gap automatically; MAX(ts) matches Sierra export latest ts within 5 min

PHASE 3 (~4h, blocks: PHASE 1 archive data):
  - Build POST /api/v9/history/replay endpoint (from/to date range)
  - For each date in range: read archived JSON via eod_archiver.read_archive(), parse bars, INSERT OR IGNORE into DB
  - Per-stream ingestion mapping: {archive_filename -> target_table -> parse_function}
  - Return summary: {date: {table: {inserted: N, skipped: M}}}
  - Regression test: archive 2 dates, wipe DB, replay, verify row counts
  Acceptance: POST /api/v9/history/replay?from=2026-05-20&to=2026-05-21 ingests archived data into all stream tables; no duplicates on re-run


=== Open questions for Michael ===

- VP enrichment writes zeros to v9_bars_5min.poc_vol/vah/val — is the intent for VP to enrich 5-min bars, or should the full volume profile (per-price-level detail) be persisted separately? The current v9_bars_volume_profile schema has a TEXT `profile` column for the full JSON — populating it means ~25KB per bar.
- Should the 4 dedicated tables (CVD/VP/imbalance/stacked-imb) be populated going forward, or are they vestigial? HistoricalReplay depends on them, but the current enrichment+signals paths work for live trading. Recommendation: populate them (small cost, enables replay).
- How many days of archive history does Michael want to maintain? Disk cost is ~200KB/day (14 JSON files). Suggest: keep 90 days, auto-prune older.
- Stacked imbalance has 0 signals and 0 bars in the export today. Is this expected (genuinely rare during GLOBEX), or is the DLL not exporting stacks? Verify during next RTH session.

NO CODE CHANGE APPLIED IN THIS INVESTIGATION.
NO DLL CHANGE APPLIED.
NO COMMITS / PUSHES.
