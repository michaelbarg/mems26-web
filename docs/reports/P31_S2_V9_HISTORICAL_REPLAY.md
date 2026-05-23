# P31 — S2 V9 Historical Replay Capability

**Date:** 2026-05-21 · **Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Authority:** V9 (LOCKED 10/5/2026) — pre-10/5 trees ARCHIVED
**Mode:** READ-ONLY · evidence-based · file:line citations
**Companions:** Task 1 [`P31_S2_V9_SPEC_CODE_AUDIT.md`](./P31_S2_V9_SPEC_CODE_AUDIT.md) · Task 2 [`P31_S2_V9_PATTERNS.md`](./P31_S2_V9_PATTERNS.md)

---

## §0 · TL;DR — does it exist today?

**Michael's question:** *"View a past day's bars + see where S2 would have
fired entries/exits."*

**Answer:** **No.** None of the existing replay infrastructure does this
end-to-end. Five distinct components touch "replay" or "history" but each
solves a different problem:

| # | Component | What it actually does | What it doesn't do |
|---|---|---|---|
| 1 | `backend/v9/services/historical_replay.py` | At app startup, reads last N hours of bars from a fixed list of DB tables and pushes them through `BarRouter` in `WARMUP` mode | **Does NOT include `v9_bars_5min`** in `replay_map` (`:99-105`). On-demand replay impossible — runs once at startup only. |
| 2 | `backend/v9/services/eod_archiver.py` + `backend/v9/api/v9/history_routes.py` | At 16:00 ET, copies live `~/SierraChart_Data/v9_export/*.json` to `~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/`. `/api/v9/history/{date}` reads them as a JSON bundle. | **Returns raw archived JSON only.** No replay through systems. No setup detection. No firing simulation. |
| 3 | `backend/v9/services/market_clock.py` REPLAY mode | When `MEMS26_CLOCK_MODE=REPLAY`, the clock reflects the last replayed bar's timestamp instead of wall-clock | **Clock service only.** Does not drive any system. Does not feed bars. |
| 4 | `tests/v9/replay/test_p29_scenario_pack.py` | Validates fire/route contract against 10 hand-curated scenarios in `fixtures/p29/scenarios.json` | **Fixture-driven contract test.** Not a runtime replay through `FiveMinSystem.process_bar`. |
| 5 | `frontend/v9/src/v9/components/chart/TimeframeSelector.tsx` | Renders a **`Replay` button** alongside `Live` (`:13`) | **Wired to nothing.** No date picker, no consumer of `onFilterChange('replay')` was found in the frontend tree. Visual placeholder only. |

**What is missing:** a tool / endpoint / UI that takes a date, loads that
day's 5-min bars (we have them — both archived and in DB), instantiates a
clean `FiveMinSystem`, calls `process_bar` once per bar in chronological
order, captures `T1Setup` emissions, and surfaces them on a chart with
entry/stop/T1/T2 markers.

---

## §1 · Component-by-component evidence

### §1.1 · `historical_replay.py` — startup warmup, S2 not covered

```19:23:backend/v9/services/historical_replay.py
class HistoricalReplay:
    def __init__(self, db_path: str, bar_router):
        self.db_path = db_path
        self.bar_router = bar_router
        self._stats = {"tables_read": 0, "bars_replayed": 0, "failed": 0}
```

```96:111:backend/v9/services/historical_replay.py
    async def warm_all_systems(self, hours: int = 12):
        """Replay all known bar types from DB."""
        replay_map = [
            ("v9_bars_tick_reversal", "tick_reversal_15"),
            ("v9_bars_footprint", "footprint"),
            ("v9_bars_woodies", "woodies"),
            ("v9_bars_volume_profile", "volume_profile"),
            ("v9_bars_cumulative_delta", "cumulative_delta"),
            ("v9_bars_imbalance", "imbalance"),
            ("v9_bars_stacked_imbalance", "stacked_imbalance"),
        ]

        for table, bar_type in replay_map:
            await self.replay_table(table, bar_type, hours)

        logger.info(f"HistoricalReplay COMPLETE: {self._stats}")
```

**Critical gap:** `v9_bars_5min` is **not** in `replay_map`. Adding it
would give S2's `BarRouter` listener "5min" the same warmup the other
systems get — but only **once at startup**, not on demand.

The closest thing S2 already does is `FiveMinSystem.hydrate()`:

```110:139:backend/v9/systems/five_min/five_min_system.py
            # Load bars from DB and replay into _bar_buffer (P-WAVE-D3)
            bars_count = 0
            try:
                db = SessionLocal()
                try:
                    rows = (
                        db.query(V9Bar5Min)
                        .order_by(V9Bar5Min.ts.desc())
                        .limit(60)
                        .all()
                    )
                finally:
                    db.close()
                # Replay oldest-first into buffer (no persist)
                for row in reversed(rows):
                    bar = {
                        "ts": str(row.ts or ""),
                        ...
                    }
                    self._bar_buffer.append(bar)
                bars_count = len(rows)
                if len(self._bar_buffer) > 20:
                    self._bar_buffer = self._bar_buffer[-20:]
                logger.info("[FiveMin] Hydrated %d bars from DB, buffer_size=%d", ...)
```

This appends rows to `_bar_buffer` **without** calling `process_bar` —
buffers warm, but no detection runs, no `T1Setup` is emitted.

### §1.2 · `eod_archiver.py` + `history_routes.py` — file bundle reader, not a replay

`eod_archiver.py:44-55` lists ten archived files per session, **including
`5min.json`**:

```44:55:backend/v9/services/eod_archiver.py
ARCHIVED_FILES = (
    "5min.json",
    "cumulative_delta.json",
    "tpo.json",
    "woodies_5min.json",
    "woodies_30min.json",
    "volume_profile.json",
    "footprint.json",
    "imbalance_flags.json",
    "stacked_imbalances.json",
    "mes_ai_data.json",
)
```

So on every RTH close, a complete copy of the day's `5min.json`,
`footprint.json`, `tpo.json`, etc. lands in
`~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/`. **The historical
bar source exists.**

The matching API:

```24:54:backend/v9/api/v9/history_routes.py
@router.get("/dates")
async def history_dates():
    """List archived trading dates (YYYY-MM-DD), newest first."""
    return {"dates": eod_archiver.list_archived_dates()}


@router.get("/yesterday")
async def history_yesterday():
    ...
    payload = eod_archiver.read_session(prev)
    ...
    return payload


@router.get("/{date}")
async def history_by_date(date: str):
    """Bundle for an explicit YYYY-MM-DD."""
    ...
    payload = eod_archiver.read_session(date)
    ...
    return payload
```

`read_session(date_str)` returns a dict with each archived JSON keyed by
filename stem (`{"5min": [...], "footprint": [...], "tpo": {...}, ...}`).
**It is a passive file reader — no system replay, no fire simulation.**

A frontend consumer of `/api/v9/history/yesterday` could **draw the chart**
but cannot **show where S2 would have fired** because no S2 logic is
exercised.

### §1.3 · `MarketClock` REPLAY mode — clock only

```46:48:backend/v9/services/market_clock.py
class ClockMode(str, Enum):
    REALTIME = "REALTIME"
    REPLAY = "REPLAY"
```

```130:137:backend/v9/services/market_clock.py
    def update_replay_timestamp(self, ts, source: str = "bar") -> ClockSnapshot:
        parsed = parse_market_timestamp(ts)
        if parsed is None:
            return self.current()
        self._replay_ts_utc = parsed
        self._replay_source = source
        self._replay_updated_at_utc = datetime.now(UTC)
        return self.current()
```

When `MEMS26_CLOCK_MODE=REPLAY`, every consumer of `now_et()` /
`now_utc()` gets the last bar's timestamp instead of wall-clock. **This is
a necessary precondition for replay** (so e.g. `q0_dispatcher.py:30-53`
sees PRE_LOCK / POST_LOCK relative to the replayed time, not today's
wall-clock). **But it does not actually feed bars** to any system.

### §1.4 · P28 / P29 / P26 replay artifacts — not bar replay through S2

| Artifact | What it actually verifies | Why it doesn't satisfy Michael's goal |
|---|---|---|
| `tests/v9/replay/test_p29_scenario_pack.py` | 10 hand-curated scenarios from `fixtures/p29/scenarios.json` exercise `DecisionMatrix`, `pre_fire_validator`, `TradingGateway` directly | Bypasses `FiveMinSystem.process_bar` entirely — S2 patterns are not run. Cannot show "where S2 would have fired on 2026-05-19". |
| `docs/reports/PROMPT28_REPLAY_SMOKE_RUN.md` | Endpoint health probes + `tests/v9/` regression suite | Describes itself: *"There is no separate full-session historical replay stage script."* (`:81-90`) |
| `tests/atomic/test_replay_clock_consumers.py` | Verifies `MarketClock` REPLAY mode propagates to consumers | Clock-only, no bar feed |
| `scripts/stages/prompt_26_replay_clock_smoke.sh` + `_27_replay_plan.sh` | Stage harnesses for the clock-mode work | No 5-min bar replay through S2 |

P29's `fixtures/p29/scenarios.json` is **10 frozen scenarios** — useful
for contract testing, useless for replaying any specific historical day.

### §1.5 · Frontend `TimeframeSelector` — Replay button is a placeholder

```12:15:frontend/v9/src/v9/components/chart/TimeframeSelector.tsx
const FILTERS = [
  { label: 'Live', value: 'live', default: true },
  { label: 'Replay', value: 'replay' },
];
```

```56:62:frontend/v9/src/v9/components/chart/TimeframeSelector.tsx
        {FILTERS.map(f => (
          <button key={f.value} style={btnStyle(filter === f.value)}
            onClick={() => { setFilter(f.value); onFilterChange?.(f.value); }}>
            {f.label}
          </button>
        ))}
```

`onFilterChange?.(f.value)` is exposed through the component prop. A search
of `frontend/v9/` for any consumer that handles `'replay'` in
`onFilterChange` returns **no matches** — the prop is wired into UI parents
but the `'replay'` value is not branched on anywhere. So clicking
"Replay" today flips local state, fires the callback into a parent that
ignores the value, and changes nothing observable.

---

## §2 · Underlying data — what's actually available

| Data | Storage | How to read it now |
|---|---|---|
| 5-min bars (today + history) | DB `v9_bars_5min` (SQLite) | `SELECT * FROM v9_bars_5min WHERE ts >= ? AND ts < ? ORDER BY ts ASC` |
| 5-min bars (single archived day) | FS `~/SierraChart_Data/v9_archive/<DATE>/5min.json` | `eod_archiver.read_archive(date, "5min.json")` |
| Footprint / COT / AMT (live S2 dependency) | DB `v9_bar_footprint` + `/api/v9/footprint/current` | DB query or HTTP. **For replay** we'd need historical footprint per-bar, not just current snapshot. |
| TPO POC (used by `_compute_location_vs_poc`) | FS `~/SierraChart_Data/v9_archive/<DATE>/tpo.json` | `_load_sierra_tpo()` reads live TPO; archive equivalent exists but is **end-of-day only** — intra-day evolution is not stored. |
| Day Type, Killzone, Woodies (V3.3 stages, currently un-wired in path A) | DB tables / archived JSON | Available but not consumed by Path A's `process_bar` (Task 1 §1 nodes 9-13) |

**Net data availability:**

- 5-min OHLCV ⇒ **available historically** (DB or archive).
- COT/AMT ⇒ **NOT available historically per-bar** — current code reads
  "current" footprint state. Historical replay would need either
  (a) a historical footprint table queryable by bar timestamp, or
  (b) a recompute of COT/AMT from raw archived `footprint.json`.
- TPO POC ⇒ **available end-of-day only** in archive; intra-day POC drift
  is lost. For a faithful replay of S2's `_compute_location_vs_poc`, we'd
  need to either (a) store TPO snapshots per bar, or (b) accept EOD-only
  approximation.

This is the **single biggest blocker** to a faithful S2 historical replay:
S2 reads live cross-system state (COT/AMT/TPO POC) on every bar, and we
do not currently store the per-bar history of those reads.

---

## §3 · Gap analysis vs Michael's goal

Michael's goal restated as a use-case sequence:

1. Open the cockpit on 2026-05-22.
2. Pick `2026-05-19` from a date dropdown.
3. The chart loads that day's 5-min bars.
4. Setup markers (entry / stop / T1 / T2) appear on the bars where
   S2 would have fired LIVE.
5. Optionally: scrub the timeline to see how each setup developed bar-by-bar.

| Step | What's needed | What we have | Gap |
|---|---|---|---|
| 1 | Cockpit running | ✓ | none |
| 2 | Date dropdown | partial — `/api/v9/history/dates` returns the list, no UI | **need date picker UI** |
| 3 | Bars on chart | partial — `/api/v9/history/{date}` returns `5min.json`, no chart wired to it | **need ChartV5b "history" mode** |
| 4 | Setup markers | **fully missing** — no replay-through-S2 endpoint, no setup persistence per replay run | **need 3 things: replay endpoint, COT/AMT historical source, marker overlay UI** |
| 5 | Scrub timeline | bonus — would require step-by-step replay state | extra |

---

## §4 · Concrete plan — phased, smallest-correct-change

This is a **proposal** for Michael's strategic approval, not a green-light.
Per the protocol it stays read-only until explicitly approved. All steps
are reversible and additive.

### Phase R-0 · Decision (no code)

Per `.cursor/rules/mems26-pre-live-protocol.mdc` § "Audit existing surfaces
before building": classify each existing component:

| Component | Classification | Rationale |
|---|---|---|
| `historical_replay.py` | **ADAPT** | Add `v9_bars_5min` to `replay_map` so a `replay_5min(date)` method can be added later. Don't replace. |
| `eod_archiver.py` | **KEEP** | Already archives `5min.json`. Source of truth for the date selector. |
| `/api/v9/history/{date}` | **KEEP** | Already reads bundles. Will be the chart's data source. |
| `MarketClock` REPLAY mode | **KEEP** | Necessary for `process_bar`'s session classification to work historically. |
| P29 scenario pack | **KEEP** | Different purpose (contract tests). Not in scope. |
| `TimeframeSelector` Replay button | **ADAPT** | Wire it to a date picker + replay state. |

**Open question R-1 (for Michael):** is the goal **faithful replay**
(every cross-system input as it was on the historical bar's timestamp) or
**inspection replay** (run S2 patterns on historical OHLCV using
*current* COT/AMT/TPO state, accept inaccuracy)? The choice drives Phase
R-2 size. **My recommendation: inspection replay first**, because data
faithfulness requires per-bar storage of COT/AMT/TPO that does not exist
today.

### Phase R-1 · Backend replay endpoint (additive)

New module `backend/v9/services/s2_replay.py`:

```python
async def replay_s2_for_date(
    date_str: str,
    *,
    cot_amt_source: Literal["current", "snapshot"] = "current",
    tpo_source: Literal["eod_archive", "current"] = "eod_archive",
) -> dict:
    """
    Load 5-min bars from DB or archive for `date_str`, instantiate a fresh
    FiveMinSystem (no gateway, no DB persist), call process_bar once per
    bar in chronological order, capture every T1Setup that emit_t1_setup
    would route. Return a structured timeline:

    {
      "date": "2026-05-19",
      "bar_count": 78,
      "setups": [
        {
          "ts": "2026-05-19T14:35:00Z",
          "bar_index": 27,
          "pattern": "REACTIVE_LONG",
          "entry": 7430.25,
          "stop": 7424.50,
          "t1": 7436.00,
          "t2": 7441.75,
          "confidence": 0.80,
          "size": "full",
          "validator_passed": true,
        },
        ...
      ],
      "rejected": [...],   # validator-rejected emissions
      "warnings": [...],   # missing COT/AMT/TPO data points
    }
    """
```

Implementation skeleton:

1. Read bars: `SELECT * FROM v9_bars_5min WHERE date(ts) = ? ORDER BY ts ASC` (or fall back to archive `5min.json` if DB row count is 0).
2. Set `MarketClock` to REPLAY mode for the duration of this call.
3. Instantiate `FiveMinSystem()` with `_gateway = None` and a no-op
   `set_footprint_system` injection that proxies a snapshot dict.
4. For each bar:
   a. `update_replay_timestamp(bar.ts)`
   b. Build a fake `event.payload = bar`
   c. `await fms.process_bar(event)`
   d. Intercept `setup_emitter.emit_t1_setup` (monkey-patch in
      replay-only context) to capture T1Setups instead of routing to
      gateway.
5. Reset clock to REALTIME after the loop.
6. Return the captured timeline.

New endpoint `backend/v9/api/v9/history_routes.py`:

```python
@router.get("/{date}/s2_replay")
async def history_s2_replay(date: str):
    if not _DATE_RE.match(date):
        raise HTTPException(...)
    return await s2_replay.replay_s2_for_date(date)
```

**Estimated change:** ~200 LOC service + ~10 LOC route + tests. No
modification to `FiveMinSystem` itself (use the existing public API).

### Phase R-2 · Frontend "Replay" mode wiring

1. Create `frontend/v9/src/v9/components/chart/HistoricalDatePicker.tsx`:
   - Calls `GET /api/v9/history/dates` on mount.
   - Renders a `<select>` of dates.
   - Emits selected date upward.
2. Modify `TimeframeSelector` so clicking "Replay" surfaces the date
   picker. The current placeholder UI gets a real consumer.
3. Modify the chart (`ChartV5b.tsx`):
   - When `filter === 'replay'`, fetch
     `GET /api/v9/history/{date}` for the OHLCV.
   - Concurrently fetch `GET /api/v9/history/{date}/s2_replay` for the
     setup timeline.
   - Render OHLC bars from the bundle, overlay markers at each setup's
     bar with entry / stop / T1 / T2 horizontal lines.
4. Show a side panel: "Setups on 2026-05-19" — table of every captured
   T1Setup with REACTIVE/INITIATIVE × LONG/SHORT badges, validator
   pass/fail, hypothetical PnL if held to T1 / T2 (computable from the
   bars we have).

**Estimated change:** ~3 new components, ~150 LOC each, plus typing in
`frontend/v9/src/v9/types/index.ts`. No backend coupling beyond the
new endpoint.

### Phase R-3 · Faithfulness improvements (deferred)

If Michael answers R-1 = "faithful replay":

1. Add a `v9_footprint_snapshots` table keyed by bar timestamp, written
   on every bar by the existing footprint pipeline.
2. Add a `v9_tpo_snapshots` table keyed by bar timestamp.
3. Modify `s2_replay.py` to read those tables instead of "current" state.
4. Backfill from archived `footprint.json` / `tpo.json` for past dates.

**Estimated change:** ~2 migrations + ~100 LOC writer changes + ~50 LOC
backfill script. **Significantly larger** than Phase R-1+R-2; deserves a
separate strategic decision.

### Phase R-4 · Optional · Pattern transparency

While replaying, surface **why each bar did NOT fire** (not just where it
did). E.g. on bar 18, b1_sellers true / b2_drop FALSE → diagnostic
"Reactive LONG missed: Bar 2 volume drop 88%, needs ≥90%". This turns
replay into a calibration tool.

**Estimated change:** ~50 LOC instrumentation in `_detect_reactive` /
`_detect_initiative`, behind a `replay_diagnose=True` flag so production
performance is unaffected.

---

## §5 · Open questions for Michael

- **R-1** — faithful vs inspection replay (see Phase R-0). My
  recommendation: ship Phase R-1+R-2 as **inspection replay** first
  (1-2 days of work), defer faithfulness (Phase R-3) until Michael has
  used R-1+R-2 for a week and decided whether the inaccuracy bites.
- **R-2** — replay scope: only S2, or all six systems? The §1
  inventory deliberately covers S2; if replay needs to show S3
  Footprint or S4 Woodies fires too, the service skeleton in §4 R-1
  generalizes naturally but each system needs its own helper.
- **R-3** — Path A only, or Path A + Path B for replay? Per Task 2 §7
  P-2, a decision is pending. If Path B is on death row, replay it from
  Path A only. If Path B is being kept, replay should show both — and
  the divergence will be visible to Michael bar-by-bar.
- **R-4** — DB vs archive for the bar source: which wins on conflict?
  Archive is FS-only and EOD-snapshotted; DB is upserted live. For days
  before the eod_archiver was deployed, DB is the only source. Pick a
  precedence rule. **My recommendation: DB if rows exist for the date,
  else archive fallback.**
- **R-5** — `gateway = None` in replay: do we want to **also** simulate
  what the gateway would have done (cluster_guard, cooldown, risk
  blocks)? That doubles the replay value but also means replay logic
  must mirror gateway logic. Inspection replay (R-1 minimal) skips this;
  full replay (R-3+) should include it.

---

## §6 · Risks & non-goals

| Risk | Mitigation |
|---|---|
| Replay fires SHADOW trades or writes to `v9_trades` | Phase R-1 explicitly passes `gateway=None` and intercepts `emit_t1_setup` upstream of `db.add(setup)` at `five_min_system.py:551`. **No persistence**. |
| Replay flips `MarketClock` for live consumers | Phase R-1 must wrap clock changes in a context manager and reset on exit / exception. Add a regression test that asserts clock is REALTIME after a replay call. |
| Replay output diverges from what production fired live (because COT/AMT/TPO are "current" not "historical") | Document the limitation in the replay response (`warnings`). Phase R-3 fixes this; until then it is a known approximation. |
| Two parallel paths (Task 2 §2) cause two different replay outputs | If Path A is canonical (Task 2 P-2), replay only Path A. Decision-gated. |

**Non-goals for this plan:**

- Bar-by-bar timeline scrub UI (Step 5 in §3 use case). Worth doing later.
- Multi-day replay / aggregated stats. Worth doing later.
- Live SHADOW comparison overlay ("here's what S2 fired live vs replay").
  Useful but separate feature.
- Editing replay parameters (e.g. tweak COT/AMT thresholds and re-run).
  This becomes a **calibration tool**, not just replay; out of scope.

---

## §7 · Recommended next concrete steps (read-only audit closes here)

1. **Michael answers R-1 / R-2 / R-3 / R-4 / R-5.**
2. If approved: implement Phase R-1 (backend `s2_replay.py` + `/api/v9/history/{date}/s2_replay` route + tests).
3. UAT axis check on the new endpoint:
   - Quality: every captured setup has the same `validator_passed` decision a live run would have (sample one historical day, cross-check).
   - Recency: endpoint accepts today's date (`history_today` analogous to `history_yesterday`).
   - Cardinality: setup count in response equals count of `[FiveMin] FIRE:` log lines from the original live session that day (for a date where logs exist).
   - Latency: < 5s for a full day (~78 RTH bars). Replay is offline so latency isn't trading-critical, but >30s would frustrate iteration.
4. If R-1 endpoint UAT passes: ship Phase R-2 (frontend wiring).
5. Strategic stop. Re-evaluate Phase R-3 only after R-1+R-2 is in
   Michael's hands for at least a week.

---

## Footer

```
   ─────────────────────────────────────────
   📊 STATUS — P31 Task 3 of 3
   ─────────────────────────────────────────
   Current Phase: P31 — Strategic V9 Audit
   Current Task:  Task 3 — S2 V9 Historical Replay (this report)
   Verdict:       NOT AVAILABLE today end-to-end.
                  Bar source ✓ · clock ✓ · system replay ✗ · UI ✗
   Plan:          Phase R-1 (backend replay endpoint, ~200 LOC)
                  Phase R-2 (frontend wiring, ~450 LOC, 3 components)
                  Phase R-3 (faithful per-bar COT/AMT/TPO snapshots) deferred
   Read-only:     ✓ no code changes
   Next concrete: Michael's call on R-1..R-5 before any implementation
   ─────────────────────────────────────────
```

*End of P31_S2_V9_HISTORICAL_REPLAY.md · 2026-05-21 · Cursor Strategic Partner*
