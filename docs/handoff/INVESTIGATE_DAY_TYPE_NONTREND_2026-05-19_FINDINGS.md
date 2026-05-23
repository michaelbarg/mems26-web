# Day Type Investigation Findings — 2026-05-19

**Mode:** read-only diagnostic (no code edits, no service restarts, no DB writes, no git ops).
**Source prompt:** `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md`
**Repo:** `~/Downloads/mems26_web_git`
**Backend process:** uvicorn PID 15095 started 2026-05-19 19:55:43 ET (latest of ≥3 today)
**Investigator:** Cursor agent · **Status:** awaiting Michael's decision per §6 of source prompt

---

## 1. Final classification (from `v9_day_type_state` DB)

| Field | Value |
|-------|-------|
| `day_type` | **Nontrend** |
| `confidence` | 0.38 |
| `lock_state` | **LOCKED_LOW_CONF** |
| `locked_at_ts` | 2026-05-19T17:10:13Z (13:10 ET) |
| `locked_at_session_min` | ≈220 (forced lock at 210 threshold) |
| `final_stage` | C3 |
| `ib_width_class` (engine) | NARROW |
| `opening_type` (DB column) | "NA" (TPO default, not engine output) |
| `behavior` | DEVELOPING |

> **Important:** `GET /api/v9/day_type/state` currently returns
> `stage=A1, day_type=UNKNOWN, session_min=0`. That endpoint reads a
> module-level `_engine` in `backend/v9/systems/day_type/api.py:21` which
> is **never fed bars**. The real machine lives in
> `app.state.day_type_machine` (created in `backend/main.py:209`); its
> trail is in the `v9_day_type_state` table. Everything below comes from
> that DB plus the live bars/TPO endpoints.

---

## 2. Top 3 votes (reconstructed from DB trail)

| # | DayType | weight | stage | reason |
|---|---------|--------|-------|--------|
| 1 | **Nontrend** | 0.38 | B6→C1→C3 | `DECISION_MATRIX[(UNKNOWN, NARROW)]` not found → defaulted to Normal, `_rescore_from_behavior` kept the prior vote, base 0.10 + range_aligned 0.20 + stability 0.08 = 0.38. C1 forced-lock at session_min ≥ 210. |
| 2 | Normal | 0.68 | B2 (14:32:07 UTC) | First IB lock right after 10:30 ET — `(UNKNOWN, WIDE) → Normal default`, behavior_agrees + range_aligned = 0.68. Stable for 60 min, then **wiped by reset #1** before reaching C1. |
| 3 | Normal | 0.68 | B2 (16:35 + 16:45 UTC) | Identical default-Normal path on transient MEDIUM IB seed; also wiped by reset #3. |

---

## 3. Inputs that drove the verdict — engine vs ground truth

| Input | Engine at lock | TPO API (truth) | Bars-5min API (truth) |
|-------|----------------|------------------|------------------------|
| IB high | (re-derived from 1 bar) | **7402.00** | 7414.75 (first 12 RTH bars) |
| IB low | (re-derived from 1 bar) | **7356.25** | 7394.25 |
| IB width | ~5 pt → **NARROW** | 45.75 pt → **WIDE** | 20.50 pt → MEDIUM |
| opening_type | OpeningType.UNKNOWN (no 3-bar opening assembled post-restart) | "NA" (TPO default) | n/a |
| drive_direction | NEUTRAL | n/a | net-down |
| extensions_up | 0 | n/a | 0 (post-IB high 7402.25 ≤ IB high) |
| extensions_down | 0 | n/a | **29.25 pt** (post-IB low 7365.00) |
| range_category | NORMAL (default, never compared to ATR) | n/a | 49.75 / 20.50 = **2.43 → EXTREME** |
| failed_extension | NONE | n/a | NONE (price did not return to range) |
| session_high / session_low | n/a | **7433.00 / 7353.75** (79.25 pt) | 7414.75 / 7365.00 within available bars |

> Engine inputs (DB row at lock): `ib_width_class=NARROW`, `behavior=DEVELOPING`,
> `opening_type="NA"` (column populated from TPO, not the detector).
> TPO is stale (`age_s≈14397`, last export 18:54 ET) but its IB still
> reflects the 09:30-10:30 ET window correctly.

---

## 4. Ground truth from Sierra (what actually happened)

### 4.1 IB window 09:30-10:30 ET (12 RTH bars from `/api/v9/chart/bars5min`)

| ts (UTC) | o | h | l | c |
|----------|---|---|---|---|
| 13:30 | 7408.75 | 7414.75 | 7406.50 | 7406.50 |
| 13:35 | 7406.75 | 7411.50 | 7406.00 | 7410.25 |
| 13:40 | 7411.50 | 7413.50 | 7408.75 | 7410.25 |
| 13:45 | 7410.25 | 7410.50 | 7402.00 | 7407.25 |
| 13:50 | 7406.50 | 7406.75 | 7399.00 | 7402.75 |
| 13:55 | 7403.75 | 7407.00 | 7401.75 | 7406.25 |
| 14:00 | 7406.75 | 7409.25 | 7404.75 | 7407.50 |
| 14:05 | 7408.00 | 7410.50 | 7405.25 | 7409.75 |
| 14:10 | 7410.00 | 7411.75 | 7408.50 | 7410.00 |
| 14:20 | 7406.75 | 7407.25 | 7397.25 | 7401.50 |
| 14:25 | 7401.50 | 7406.25 | 7396.75 | 7397.50 |
| 14:30 | 7397.50 | 7401.50 | 7394.25 | 7399.25 |

→ IB high = 7414.75, IB low = 7394.25, **IB width = 20.50 pt (MEDIUM)**

### 4.2 Last 6 RTH bars (drifting lower)

| ts (UTC) | o | h | l | c |
|----------|---|---|---|---|
| 15:30 | 7386.50 | 7389.25 | 7381.50 | 7381.75 |
| 15:35 | 7382.00 | 7383.75 | 7378.25 | 7380.50 |
| 15:40 | 7380.50 | 7381.00 | 7376.25 | 7377.00 |
| 15:45 | 7377.50 | 7379.75 | 7375.00 | 7377.25 |
| 15:50 | 7377.25 | 7377.75 | 7366.75 | 7368.00 |
| 15:55 | 7368.00 | 7371.25 | 7365.00 | 7368.50 |

### 4.3 Post-IB behavior

- Broke IB high? **NO** (max post-IB high = 7402.25 < 7414.75)
- Broke IB low? **YES** (min post-IB low = 7365.00; extension = 29.25 pt)
- Range / IB ratio = 49.75 / 20.50 = **2.43 → EXTREME**

### 4.4 TPO snapshot (4 h stale, last export 18:54 ET)

```
session_high = 7433.00   session_low = 7353.75   total range = 79.25 pt
ib_high      = 7402.00   ib_low      = 7356.25   ib_width   = 45.75 pt (WIDE)
poc          = 7370.50   vah         = 7391.25   val        = 7358.75   va_ok = True
profile_shape = "NA"     opening_type = "NA"     total_volume = 954633
prev_session  poc = 7408.25   vah = 7412.25   val = 7383.75
```

### 4.5 Visible behavior

One-sided downside trend. No upside extension at all; full breach of IB
low by ~30 pt; closing the visible window near session lows; profile
drifting through POC (7370.50) and below VAL (7358.75).

This is textbook **Trend_Normal-down** (possibly Trend_DD if a late
second distribution formed after 11:55 ET).
**It is NOT a Nontrend day.** Michael's reading of the chart is correct.

---

## 5. Engine timeline — the smoking gun

From `v9_day_type_state` for 2026-05-19, focused on the IB-lock window
and the three resets:

| ts (UTC) | stage | day_type | conf | lock_state | ib_width | note |
|----------|-------|----------|------|------------|----------|------|
| 14:32:07 | B2 | **Normal** | **0.68** | PENDING | **WIDE** | ← first correct IB lock |
| 14:35-15:35 | B2 | Normal | 0.68 | PENDING | WIDE | (13 stable rows, 60 min) |
| **15:40:05** | **A2** | **UNKNOWN** | **0.00** | PENDING | UNKNOWN | ← **RESET #1** |
| 15:45:05 | A2 | UNKNOWN | 0.00 | PENDING | UNKNOWN | (only 2 opening bars) |
| 15:50:07 | A2 | UNKNOWN | 0.00 | PENDING | UNKNOWN | |
| 15:55:05 | B2 | **Nontrend** | **0.38** | PENDING | **NARROW** | ← IB re-seeded from 1 bar |
| **16:00:05** | **A2** | **UNKNOWN** | 0.00 | PENDING | UNKNOWN | ← **RESET #2** |
| 16:05:04 | B2 | Nontrend | 0.38 | PENDING | NARROW | |
| 16:10-16:30 | B2 | Nontrend | 0.38 | PENDING | NARROW | (5 stable rows) |
| 16:35:04 | B2 | Normal | 0.68 | PENDING | MEDIUM | ← different IB seed |
| 16:40:04 | B2 | Nontrend | 0.38 | PENDING | NARROW | |
| 16:45:08 | B2 | Normal | 0.68 | PENDING | MEDIUM | |
| **16:50:32** | **A2** | **UNKNOWN** | 0.00 | PENDING | UNKNOWN | ← **RESET #3** |
| 16:55-17:05 | A2 | UNKNOWN | 0.00 | PENDING | UNKNOWN | (3 rows) |
| **17:10:13** | **C3** | **Nontrend** | **0.38** | **LOCKED_LOW_CONF** | **NARROW** | ← **FORCED LOCK** at session_min≈220 |
| 17:15-19:50 | C3 | Nontrend | 0.38 | LOCKED_LOW_CONF | NARROW | (32 stable rows) |

`backend.log` confirms ≥3 distinct uvicorn worker PIDs today
(`9393 → 9654 → 15095`). Each restart instantiates a fresh
`DayTypeStateMachine()` (`backend/main.py:209`) with empty
`opening_bars=[]`, `ib_high=0`, `ib_low=inf`, `vote_history=[]`.

---

## 6. Root cause

**Primary: (e) Hydration replayed stale state from DB after restart,
plus (b) inputs misfed.**

Every reset point in §5 is past 10:30 ET (`session_min ≥ 60`). On the
first bar after a fresh machine, `_stage_a3`
(`backend/v9/systems/day_type/state_machine.py:378-393`) immediately
advances to A4 because `session_min ≥ ib_period_min=60`, and locks IB
from THAT single bar's range (≈5 pt → NARROW). The TPO-truth IB
(`ib_high=7402, ib_low=7356.25`, WIDE) is read by `main.py:226-234` and
passed to the engine via `BarInput.ib_high / ib_low` — but only if
`tpo_sys.ib_high` and `ib_low` are not None at that moment. The fact
that the engine still saw NARROW after every reset shows TPO returned
`ib_high=None` for the first post-restart bar (TPO hadn't finished
re-hydrating its own session state when the day_type bar fired).

The Nontrend label then falls out cleanly:

1. `DECISION_MATRIX[(UNKNOWN, NARROW)]` is not a key → falls through
   to the `DayType.Normal` default in
   `state_machine.py:_stage_b1:424` (`DECISION_MATRIX.get(key, DayType.Normal)`).
2. `_stage_b6._rescore_from_behavior` (`state_machine.py:525-542`) sees
   `behavior=DEVELOPING`, `range_category=NORMAL` (default, never
   compared to ATR because the engine doesn't carry an ATR), and
   returns `self.day_type` unchanged.
3. Confidence pins at 0.38: base 0.10 + range_aligned 0.20 + stability
   0.08 (only ~3 consecutive votes after each reset).
4. C1 forced-lock fires at session_min ≥ 210
   (`state_machine.py:601-608`): confidence 0.38 < threshold 0.85, so
   `lock_state = _LOCK_LOW_CONF`.

### Hypotheses ruled out

- (a) "Nontrend rule too aggressive": false. The rule fired correctly
  given corrupted NARROW + DEVELOPING inputs.
- (c) "Voting weights skewed Nontrend over Trend_Normal": false. The
  matrix never even reached Trend_Normal — Trend_Normal lives in the
  `(OPEN_DRIVE, *)` and `(OPEN_AUCTION_OUT, WIDE)` cells, and the
  engine's `opening_type` was UNKNOWN after every reset.
- (d) "Lock fired too early": false. Lock fired right at the
  configured `min_session_min_for_lock=210` threshold.

---

## 7. Secondary observations (not the root cause, but worth recording)

1. **Two state machine instances exist.** `app.state.day_type_machine`
   (live, fed by BarRouter) vs `backend/v9/systems/day_type/api.py:21`
   `_engine` (never fed). The GET `/state` endpoint reads the second
   one, so the live API misleads any observer. The DB tables are the
   only honest source today.

2. **`opening_type` column in the DB is misleading.** `main.py:234`
   writes `tpo_state.get("opening_type", "NA")` into the
   `v9_day_type_state.opening_type` column instead of
   `state.opening_type.value`. So the column reflects TPO's
   classification (or its "NA" default), not the day-type engine's
   own `detect_opening_type()` result.

3. **TPO/bars IB disagreement.** TPO says IB=7402.00-7356.25 (45.75 pt).
   The bars5min endpoint's first 12 RTH bars say IB=7414.75-7394.25
   (20.50 pt). That's a separate bug (P30 territory) but it adds
   ambiguity to "what IB even is" today.

4. **Bars endpoint is ~4 h stale** (last bar 11:55 ET on a 2026-05-19
   query at 22:54 ET / 18:54 ET-equivalent). Acceptable for forensic
   analysis but explains the missing late-session bars.

---

## 8. Recommended fix locations (do NOT apply)

### Primary — restart tolerance

```
file:     backend/main.py
function: _day_type_on_bar  (defined around line 221)
line:     ~252  (just before `state = day_type_machine.process_bar(bar_input)`)
change:   if day_type_machine.bar_count == 0 and tpo_sys is not None
          and tpo_sys.ib_locked and tpo_sys.ib_high is not None
          and tpo_sys.ib_low is not None:
            day_type_machine.ib_high  = tpo_sys.ib_high
            day_type_machine.ib_low   = tpo_sys.ib_low
            day_type_machine.ib_class = IBClassification(
                ib_high=tpo_sys.ib_high,
                ib_low =tpo_sys.ib_low,
                ib_range=tpo_sys.ib_high - tpo_sys.ib_low,
                ib_width=classify_ib_width(
                    tpo_sys.ib_high - tpo_sys.ib_low,
                    narrow_max=day_type_machine.config.ib_narrow_max_pt,
                    medium_max=day_type_machine.config.ib_medium_max_pt))
            day_type_machine.ib_locked = True
            day_type_machine.stage     = Stage.B1
```
Makes the engine restart-tolerant during RTH. Requires no schema
change. Add a regression test under `tests/v9/systems/day_type/` that
spawns a fresh engine at session_min=130 with TPO IB seeded and
asserts `state.ib_width == WIDE`.

### Secondary — observability

```
file:     backend/v9/systems/day_type/api.py
function: get_state
line:     42
change:   replace `_get_engine()` with `request.app.state.day_type_machine`
          (and accept `request: Request` parameter) so /state reflects
          the live engine.
```

### Tertiary — upstream cause

Investigate why uvicorn restarted ≥3× during 2026-05-19 RTH
(`PIDs 9393 → 9654 → 15095`). This is the prime cause of every
misclassification today; no engine-side fix matters if restarts keep
happening. Likely candidates: LaunchAgent / supervisor policy
unrelated to the bridge, an unhandled exception in another
subsystem, or manual restarts during the day's parity work.

---

## 9. UAT axes (per `.cursor/rules/mems26-pre-live-protocol.mdc`)

| Axis | Status today | After primary fix (expected) |
|------|--------------|------------------------------|
| Quality | FAIL — engine produced Nontrend on a clear Trend day | PASS — engine sees WIDE IB from TPO seed |
| Recency | n/a (the verdict is "fresh" but on stale state) | n/a |
| Cardinality | n/a (single classification per session) | n/a |
| Latency | OK (`/state` 9.4 s on cold call, mostly TPO; this is a separate concern) | OK |

---

## 10. Decision needed from Michael (per source prompt §6)

Pick one:

1. **Adjust a threshold in `DayTypeConfig`** — not appropriate here.
   The diagnosis is corrupted INPUTS, not threshold drift. (No threshold
   change would make today's NARROW-from-1-bar story correct.)
2. **File a P-ID for a code fix** in `backend/main.py` (`_day_type_on_bar`
   restart-tolerance seed) and optionally
   `backend/v9/systems/day_type/api.py` (live `/state` endpoint).
   **Recommended.** Cursor agent implements with a regression test,
   verified against the four UAT axes.
3. **Accept the verdict** — only if Michael decides today's
   "Nontrend / LOCKED_LOW_CONF" is acceptable for journaling and that
   restart-tolerance is deferred to a later P-ID.
4. **Defer to Claude Code** if Michael prefers the report-and-fix split
   per `CLAUDE.md` reporting workflow (Cursor's protocol still
   implements; CC writes the post-fix report).

> Per `.cursor/rules/mems26-pre-live-protocol.mdc` "one thread at a time"
> rule, this is a strategic stop. Awaiting Michael before any code edit.

---

## 11. Provenance / evidence files

- API live: `/api/v9/day_type/state`, `/api/v9/day_type/history?limit=100`,
  `/api/v9/tpo/current`, `/api/v9/killzone/current`,
  `/api/v9/chart/bars5min?limit=80`
- DB: `data/mems26_local.db` → `v9_day_type_state` (114 rows for
  2026-05-19), `v9_day_type_history` (no row for 2026-05-19 yet)
- Sierra exports: `/Users/michael/SierraChart_Data/v9_export/tpo.json`
  (stale 4 h), `woodies_5min.json`, `cumulative_delta.json`
- Logs: `/tmp/backend.log` (≥3 `Started server process` markers today)
- Source files read (read-only): `schemas.py`, `state_machine.py`,
  `decision_matrix.py`, `detector.py`, `hydration.py`,
  `day_type_v9_routes.py`, `api.py` (day_type), `main.py` (excerpt)
