# CC Investigation — Unified history architecture across all Sierra streams

**Issued:** 2026-05-22 10:25 IL (07:25 UTC) · **For:** Claude Code · **Mode:** read-only investigation + architecture spec. No code changes, no service restarts, no git commits.
**Predecessor:** Issue B clarification (Michael, 2026-05-22 AM) → CC #2 recommended **B1** (TPO snapshot to `v9_tpo_history`). Cursor implemented B1 this morning (see §"Already shipped" below). Michael then expanded the ask: *"if we're already touching, I want everything to be uniform — take history for ALL the data over the same time range. If the system was closed for an hour, no need for full reload — load only the missing part and continue."*

The deliverable for this investigation is the **architecture spec** that satisfies Michael's expanded vision, broken into phases so Cursor (or CC) can implement one stream at a time without architectural rework later.

---

## What Michael wants (in his words, translated)

1. **Uniform historical backfill across ALL Sierra-derived data** — same time window (e.g., 30 days) for bars, TPO, CVD, footprint, Woodies, IB, etc. Not just TPO POC.
2. **Gap-fill on startup** — if backend was down for 1 h / 1 day / 1 week, the boot path detects what's missing and ingests **only** the gap. No full reload, no manual catch-up.
3. **Manual completion** — an operator-facing way to say *"fill from date X to Y"* if something was missed in the wild.
4. **Sierra is the source of truth** (per `CLAUDE.md`): we're parasites of Sierra anyway. If Sierra has the data — and it does, in `.scid` files + native study computations — our system should be able to **re-sync to Sierra at boot**, not just from the moment we started running.

The architecture must therefore turn MEMS26 from *"live-only"* into *"live + crash-resilient + Sierra-grade history"*. Single guiding principle: **the DB after a boot should be observationally identical to the DB after running 24/7 from session-start.**

---

## Already discovered this morning (do NOT re-investigate)

### Sierra JSON exports (14 files in `~/SierraChart_Data/v9_export/`)

| File | bytes | Live keys | Has history array? | Notes |
|------|-------|-----------|--------------------|-------|
| `5min.json` | 86 KB | bars[] (601 rows) | **YES** | `ts, o, h, l, c, vol, poc_vol, vah, val, cumulative_delta` per bar |
| `cumulative_delta.json` | 1.7 KB | points[] (23 rows) | **YES** | `i, t, d, cum, p` per point; `output_interval=300` |
| `footprint.json` | 32 KB | bars[] (31) | YES | `idx, o, h, l, c, vol, delta, poc_price, …levels` per bar |
| `imbalance_flags.json` | 161 B | bars[] (0 today) | YES but empty | rolling, may be populated mid-RTH |
| `live_price.json` | 73 B | flat | NO | transient — skip from history work |
| `mes_ai_data.json` | 1.4 KB | flat snapshot | NO | derived summary — skip |
| `reversal_cluster.json` | 177 B | flat | NO | latest cluster only — skip |
| `stacked_imbalances.json` | 127 B | stacks[] (0 today) | YES but empty | rolling |
| `tick_reversal_12.json` | 12 KB | bars[] (82) | YES | tick reversal bars |
| `tick_reversal_15.json` | 11 KB | bars[] (70) | YES | tick reversal bars |
| `tpo.json` | 434 B | **session, ib, prior_day, previous_session** (no periods!) | **NO** | single live value — this is what Issue B B1 patches around |
| `volume_profile.json` | 25 KB | profiles[] (31) | YES | per-bar `poc, vah, val, total_vol, levels[]` |
| `woodies_30min.json` | 20 KB | history[] (50) + current_bar | **YES** | the only export that explicitly carries history natively |
| `woodies_5min.json` | 30 KB | history[] (50) + current_bar | **YES** | same |

> Critical observation: most exports already include a `bars[]`/`points[]`/`history[]` array. The bridge ingests these into DB tables. But **the exports are snapshots of the rolling tail** (60 bars, 50 bars, …) — they do **not** carry full session history. That gap is what makes startup gap-fill non-trivial.

### DB tables (30 v9_* tables, row counts at 09:30 IL today)

| Stream | Table | Rows live | Status vs Sierra |
|--------|-------|-----------|------------------|
| 5-min bars | `v9_bars_5min` | 1,894 | Live ✓ |
| Woodies 5-min bars | `v9_bars_5min_woodies` | **1,864,446** | Plenty of history ✓ |
| Woodies 30-min bars | `v9_bars_30min_woodies` | **3,179,877** | Plenty ✓ |
| Tick reversal bars | `v9_bars_tick_reversal` | **8,074,150** | Plenty ✓ |
| Footprint bars | `v9_bars_footprint` | 2,457 | Some history |
| Footprint journal | `v9_footprint_journal` | 132,148 | Plenty |
| **CVD bars** | `v9_bars_cumulative_delta` | **0** | ❌ ingestion not wired |
| **Volume-profile bars** | `v9_bars_volume_profile` | **0** | ❌ not wired |
| **Imbalance bars** | `v9_bars_imbalance` | **0** | ❌ |
| **Stacked-imbalance bars** | `v9_bars_stacked_imbalance` | **0** | ❌ |
| Old Woodies bars | `v9_bars_woodies` | 0 | unused / legacy |
| TPO sessions (daily) | `v9_tpo_sessions` | 18 | Daily aggregate only |
| TPO history (per-letter) | `v9_tpo_history` | **0 → growing** | NEW today (Issue B B1) |
| TPO journal | `v9_tpo_journal` | 13,403 | Letter bar ranges, not POC |
| Day-type state | `v9_day_type_state` | 13,373 | Live ✓ |
| Day-type history | `v9_day_type_history` | 6 | UPSERT once per session — fine |
| Woodies signals | `v9_woodies_signals` | 30,638 | Live ✓ |
| System signals | `v9_system_signals` | 41,316 | Live ✓ |
| Trades | `v9_trades` | 1,299 | Live ✓ |
| Chop score | `v9_chop_score` | **0** | ❌ probably never persisted |
| Killzone log | `v9_killzone_log` | 0 | ❌ |
| Reversal enrichment | `v9_reversal_enrichment` | 0 | ❌ |
| (other empty operational tables) | — | 0 | by design |

> The **four-priority-gap** streams (CVD, VP, imbalance, stacked-imbalance) all have **live JSON data** AND **schema-ready DB tables** AND **zero rows**. That's a wiring bug — the bridge POSTs them to the API, but something between API and DB drops them on the floor. **Worth confirming in the investigation** so any unified-history plan also closes the live ingestion gap.

### Existing P30 infrastructure (DO NOT rebuild — extend)

- **`backend/v9/services/eod_archiver.py`** (P30 G6, Michael 2026-05-19) — copies 10 of the 14 JSON exports to `~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/`. Idempotent. **Filesystem-only, no DB ingestion.** Triggered manually via `POST /api/v9/history/archive_now`. **No cron / lifecycle hook yet.**
- **`backend/v9/api/v9/history_routes.py`** — `/api/v9/history/{dates, yesterday, {date}, archive_now}`. Reads filesystem archives, returns bundle JSON. Cockpit "Hist" tab uses `/yesterday`.
- **`backend/v9/services/market_clock.py`** — DST-correct, holiday-aware (2026 NYSE), half-day-aware. Centralized time service. **Use this for any new RTH gating.**
- **`backend/v9/services/tpo_history_snapshotter.py`** (Cursor 2026-05-22 AM — Issue B B1) — first concrete instance of an intra-RTH snapshotter writing per-30-min rows to a per-stream history table. **Use this as the template** for other streams that need denser-than-daily snapshots.
- **Bridge streams** (`bridge/v9_streams/*.py`, 12 streams) — `live_price_stream`, `bars_5min_stream`, `woodies_*`, `cumulative_delta_stream`, `footprint_stream`, `tick_reversal_*`, `volume_profile_stream`, `imbalance_flags_stream`, `stacked_imbalances_stream`, `tpo_stream`. No `historical/backfill/gap-fill` keywords anywhere in bridge code today — pure live forwarders.

---

## The architectural question CC must answer

> *Given Sierra has the full history in `.scid` files, the DLL exposes only rolling-tail JSON, and the backend already has an EOD archiver but no DB ingestion + no startup gap-fill — what's the minimum architecture that gives us: (a) **uniform** history across all relevant streams, (b) **automatic** EOD persistence, (c) **gap-fill on startup**, (d) **manual replay** endpoint, while preserving the source-of-truth-is-Sierra invariant?*

Specifically, the spec must pick a path for each of the four sub-questions:

### 1. Where does historical depth come from?

| Path | Pros | Cons |
|------|------|------|
| **A — DLL extension** writes N days of historical per-stream JSON at study reload | Sierra-perfect fidelity; rebuild once, gain forever | Requires CC DLL work; Michael wary of touching DLL ("if it works don't break it") |
| **B — EOD archiver** is sufficient (already 10 streams) + add the 4 missing (CVD/VP/imbalance/stacked-imbalance) to `ARCHIVED_FILES` | Reuses existing P30 work; zero DLL touch | Only captures EOD snapshot — intra-day granularity is lost (TPO B1 pattern needed per-stream where intra-day matters) |
| **C — Sierra .scid replay** in backend — open Sierra's binary data files and recompute | Full fidelity, no DLL touch, no Sierra-running requirement | Risk: drift from Sierra's internal calculations; high effort; .scid format reverse-engineering |

### 2. How does startup gap-fill detect "what's missing"?

| Path | Pros | Cons |
|------|------|------|
| **α — Per-table `MAX(ts)` vs `list_archived_dates()`** | Trivial logic; uses existing archiver | Granularity = daily; doesn't catch intra-day gaps |
| **β — Per-stream timestamp + per-archive timestamp** | Sub-daily granularity | More complex; needs an index of archive contents |
| **γ — Replay all archives older than `MAX(ts)` and deduplicate at insert** | Brutal but correct | Slow on a fresh DB (potentially Gigabytes); may double-process bars |

### 3. Who triggers EOD archiving?

| Path | Pros | Cons |
|------|------|------|
| **i — System cron at 16:05 ET → curl `archive_now`** | Simplest; documented in the existing `archive_now` docstring | OS-level — easy to forget on a fresh machine |
| **ii — FastAPI lifecycle hook + market_clock-aware scheduler** | Self-contained — survives `launchctl` restarts | More moving parts; one more background task |
| **iii — Bridge-side scheduler** | Bridge is the runtime that knows when Sierra closes | Bridge currently has no scheduler infra |

### 4. Manual replay surface

`POST /api/v9/history/replay/{date}` → reads `<archive>/<date>/`, ingests into DB, returns count per table. Or — broader — `POST /api/v9/history/replay?from=YYYY-MM-DD&to=YYYY-MM-DD`. Skim the existing route file and propose the minimum signature that satisfies Michael's "השלמה ידנית אם נגיד" ask.

---

## Investigation steps (CC executes these, returns the deliverable below)

### Step 1 — Confirm the gap inventory

```bash
# Per-stream MAX(ts) where the column exists, oldest table first
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db "
  SELECT 'v9_bars_5min' AS t, COUNT(*) AS rows, MAX(ts) AS max_ts FROM v9_bars_5min
  UNION ALL SELECT 'v9_bars_cumulative_delta', COUNT(*), MAX(ts) FROM v9_bars_cumulative_delta
  UNION ALL SELECT 'v9_bars_footprint', COUNT(*), MAX(ts) FROM v9_bars_footprint
  UNION ALL SELECT 'v9_bars_volume_profile', COUNT(*), MAX(ts) FROM v9_bars_volume_profile
  UNION ALL SELECT 'v9_bars_imbalance', COUNT(*), MAX(ts) FROM v9_bars_imbalance
  UNION ALL SELECT 'v9_bars_stacked_imbalance', COUNT(*), MAX(ts) FROM v9_bars_stacked_imbalance
  UNION ALL SELECT 'v9_bars_5min_woodies', COUNT(*), MAX(ts) FROM v9_bars_5min_woodies
  UNION ALL SELECT 'v9_bars_30min_woodies', COUNT(*), MAX(ts) FROM v9_bars_30min_woodies
  UNION ALL SELECT 'v9_bars_tick_reversal', COUNT(*), MAX(ts) FROM v9_bars_tick_reversal
  UNION ALL SELECT 'v9_tpo_history', COUNT(*), MAX(ts) FROM v9_tpo_history
  ;
"
```

### Step 2 — Trace the live ingestion path for each 0-row stream

For `v9_bars_cumulative_delta`, `v9_bars_volume_profile`, `v9_bars_imbalance`, `v9_bars_stacked_imbalance`:

```bash
# Which bridge stream writes the JSON? Which API endpoint receives it?
# Which DB table does the API endpoint insert into?
rg "v9_bars_cumulative_delta" backend/ bridge/ --type py
rg "/api/v9/bars/cumulative_delta" backend/ bridge/ --type py
```

Note **per stream**: (a) bridge stream class, (b) API endpoint handler, (c) DB INSERT site. If any step is missing, that's the wiring bug.

### Step 3 — Confirm the EOD archiver coverage

```bash
ls /Users/michael/SierraChart_Data/v9_archive/ 2>/dev/null
# Are there any archived dates at all? When was the last archive_now run?
```

If empty, the archiver has never run automatically — confirms Path (i)/(ii)/(iii) is unavoidable.

### Step 4 — Read these files (do not edit)

| File | Why |
|------|-----|
| `backend/v9/services/eod_archiver.py` | Existing archive engine; what does it cover? what to extend? |
| `backend/v9/api/v9/history_routes.py` | Existing replay endpoints; what to add for ingestion? |
| `backend/v9/services/tpo_history_snapshotter.py` | Template for per-stream snapshotter — pattern is *valid* for streams that need intra-day granularity |
| `backend/v9/services/market_clock.py` | Use this for any scheduler — DO NOT hardcode times |
| `backend/v9/api/v9/bars.py` (and `bars_5min_history.py`) | How the bridge POST → DB INSERT path looks for the working streams |
| `bridge/v9_streams/cumulative_delta_stream.py` | Sample empty-DB stream to trace the wiring break |
| `docs/runbooks/SIERRA_DLL_OPS.md` | If Path A is chosen, this is the DLL build/reload runbook CC will follow |

### Step 5 — Make recommendations

Choose **one** path per sub-question (1, 2, 3) above. Justify in one paragraph each.

For **each stream that needs work**, fill the per-stream table below.

---

## Deliverable format

A single Markdown block, no embellishment. File the deliverable as `docs/handoff/CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md` (so Cursor can pick it up directly):

```
UNIFIED HISTORY ARCHITECTURE — 2026-05-22 <HH:MM> ET

=== Sub-question decisions ===
1. Historical depth source: <A | B | C>
   Reasoning: <1 paragraph>

2. Startup gap-fill detection: <α | β | γ>
   Reasoning: <1 paragraph>

3. EOD trigger: <i | ii | iii>
   Reasoning: <1 paragraph>

4. Manual replay surface: <signature>
   Reasoning: <1 paragraph>

=== Per-stream plan ===
| Stream | Current state | Gap | Path needed | LOC | Risk | Effort |
|--------|---------------|-----|-------------|-----|------|--------|
| 5min bars            | rows=1894, live ✓        | history pre-today | … | … | … | … |
| CVD bars             | rows=0, live empty      | ingestion broken + history | … | … | … | … |
| Volume profile bars  | rows=0, live empty      | ingestion broken + history | … | … | … | … |
| Footprint bars       | rows=2457, partial      | history depth | … | … | … | … |
| Footprint journal    | rows=132k, plenty      | none / nice-to-have | … | … | … | … |
| Imbalance bars       | rows=0, live empty      | ingestion broken | … | … | … | … |
| Stacked-imb bars     | rows=0, live empty      | ingestion broken | … | … | … | … |
| Woodies 5min bars    | rows=1.86M, plenty      | none | … | … | … | … |
| Woodies 30min bars   | rows=3.18M, plenty      | none | … | … | … | … |
| Tick reversal bars   | rows=8.07M, plenty      | none | … | … | … | … |
| TPO sessions (daily) | rows=18, recent only    | deeper history | … | … | … | … |
| TPO history (B1)     | rows=0 → growing today  | working — Cursor 2026-05-22 ✓ | DONE | DONE | DONE |
| TPO journal          | rows=13k, plenty        | per-letter restart-dup bug noted by CC #2 | … | … | … | … |
| Day-type state       | rows=13k, plenty        | none | — | — | — |
| Day-type history     | rows=6, UPSERT          | none | — | — | — |
| Trades               | rows=1299, live ✓        | none | — | — | — |

=== Recommended phasing ===
PHASE 1 (~__ h, blocks: NONE):
  - <bullet of concrete steps>
  - Acceptance: <one line>

PHASE 2 (~__ h, blocks: PHASE 1):
  - <bullet>
  - Acceptance: <one line>

PHASE 3 (~__ h, blocks: PHASE 2):
  - <bullet>

=== Open questions for Michael ===
- <bullet, if any> (do not block on these; flag them and continue)

NO CODE CHANGE APPLIED IN THIS INVESTIGATION.
NO DLL CHANGE APPLIED.
NO COMMITS / PUSHES.
```

---

## Guardrails

- **Read-only.** No edits to any source file. No DB writes. No service restarts. No `launchctl`, `screen`, `kill -9`.
- **No commits, no pushes.** Working tree must stay clean of CC's hand for Michael to review.
- **Do not edit `sc_study/`, `bridge/`, the LaunchAgent, or anything under `.cursor/`.** The DLL is owned by CC for *implementation*; this is the *investigation* step and the DLL stays untouched.
- Bridge must continue pushing only to `http://localhost:8000`. Do not touch any `CLOUD_URL` env.
- If a hypothesis cannot be confirmed by data within ~15 min, **stop and tell Michael**. Don't fill the deliverable with guesses.
- Honour the always-applied workspace rule: "At the end of every prompt, fix, UAT, or phase gate, ask Claude Code to prepare or update the report before moving on" — this **is** that report; it's your output.

---

## What happens after CC returns

1. Michael reads the deliverable.
2. He approves PHASE 1 (or asks for modifications).
3. Cursor (or another CC session, Michael's call) implements PHASE 1 with regression tests, four-axis UAT, and an update to `P31_TASK_BOARD.md`.
4. Repeat for PHASE 2 and PHASE 3.
5. At the end, the system is **uniform-history-complete**: a fresh boot brings the DB up to Sierra parity automatically, and no operator intervention is needed after downtime.
