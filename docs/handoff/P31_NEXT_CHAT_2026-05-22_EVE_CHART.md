# P31 — Next chat (2026-05-22 ערב, אחרי chart RTH UAT)

**Created:** 2026-05-22 18:13 IL
**Previous session:** Chart white-line refactor + CVD history backfill (commit pending)
**Next session goal:** S4 audit (Woodies) + RTH soak verification

---

## §0 — State of the world

| Resource | Status | PID / Detail |
|----------|--------|--------------|
| **Backend `:8000`** | 🟢 | uvicorn PID **52505** · Health ~25ms · **needs restart** to pick up `cumulative_delta_routes` history endpoint (already in HEAD via `d9291e4`) |
| **Frontend `:3000`** | 🟢 | next dev PID **26120** · hot-reloaded the chart refactor; user must `Cmd+Shift+R` once to clear orphan WebGL canvases |
| **Bridge** | 🟢 | PID 55100 · all 12 streams · §9 workaround active |
| **Sierra Chart** | 🟢 | RTH live · MES on 5m frame · DLL writing to `~/SierraChart_Data/v9_export/` |
| **DB** | 🟢 | SQLite `data/mems26_local.db` · WAL mode |
| **Branch** | `stabilize/mems26-local-truth-2026-05-16` | 10 commits ahead of origin · **uncommitted chart fixes in working tree** |

---

## §1 — What this session shipped

### Chart white-line refactor (Michael 2026-05-22 RTH UAT)

Six visual bugs in the yesterday-POC/VAH/VAL white horizontal references, all fixed in `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts`:

| # | Bug | Fix |
|---|-----|-----|
| 1 | "Infinite white lines" (createPriceLine spanned full chart) | `LineSeries` bounded to today's RTH window (09:30–16:00 ET) with dense points every 5 min |
| 2 | TZ drift — lines 3h late (placed at 12:30 ET instead of 09:30 ET) | Replaced `new Date(toLocaleString(...))` (local-TZ bug) with `Intl.DateTimeFormat` + EDT/EST probe |
| 3 | Lines extended 8h past the latest bar (fixed end at 16:00 ET) | `close = Math.min(rthClose, nowSec + 300)` — extends bar-by-bar |
| 4 | Orphan lines from previous renders accumulated after HMR | WeakMap moved to `globalThis.__mems26YdayTpoStore` — survives Next.js HMR module replacement |
| 5 | Duplicate axis labels (bold + regular for each level) | `lastValueVisible: false, title: ''` on LineSeries — SierraLevelsOverlay (SVG badge) is now the single source for VAH/POC/VAL pills |
| 6 | CVD pane only showed 14 points (1h) instead of full 5h window | Frontend now calls `/api/v9/cumulative_delta/current?history=1&limit=600` — backend backfills from `v9_bars_cumulative_delta` table |

### Regression tests added

```
tests/v9/frontend/test_tpo_stepped_lines.py — 10 tests PASS
  + test_yesterday_lines_bounded_to_rth_window_not_infinite
  + test_yesterday_rth_window_helper_handles_dst
  + test_yesterday_lines_suppress_native_axis_label
  + test_yesterday_window_close_follows_the_price
  + test_yesterday_store_survives_hmr

tests/v9/frontend/test_tpo_overlay_six_lines.py — 6 tests PASS
  (updated to assert LineSeries instead of createPriceLine)

tests/v9/api/test_cumulative_delta_routes.py — 16 tests PASS
  + test_cvd_history_off_by_default_keeps_legacy_shape
  + test_cvd_history_prepends_older_db_rows
  + test_cvd_history_filters_overlap_with_live_points
  + test_load_db_history_returns_empty_when_db_missing
  + test_load_db_history_returns_empty_for_zero_limit
```

**Total: 32/32 PASS** in the chart/CVD scope. Broader sweep clean except for 2 pre-existing time-relative "rotting tests" in `test_tpo_routes_sierra_contract.py` (time-fixed fixtures aged out of the 48h window).

### Files modified in this session

```
M  frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts   (≈210 lines diff)
M  frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx   (≈68 lines diff)
M  tests/v9/api/test_cumulative_delta_routes.py           (+330 lines)
?? tests/v9/frontend/test_tpo_stepped_lines.py            (new file, 200 lines)
?? tests/v9/frontend/test_tpo_overlay_six_lines.py        (new file, 56 lines)
```

`backend/v9/api/v9/cumulative_delta_routes.py` already in HEAD (`d9291e4`) — no change needed there.

---

## §2 — Outstanding verification (Michael in-the-eye)

After `Cmd+Shift+R` in the browser:

1. **White lines start at RTH open (09:30 ET = 16:30 IL = 13:30 UTC).**
   The leftmost point of each white line should sit on the first RTH bar.
2. **White lines end at `now + 5min` (one bar bucket ahead of the latest candle).**
   As new bars arrive, the lines should visibly extend to the right.
3. **After 16:00 ET (= 23:00 IL = 20:00 UTC), white lines pin to 16:00 ET.**
   They stop extending and stay anchored at RTH close.
4. **VAH/POC/VAL pills on the right axis appear ONCE each (3 total, not 6).**
   The bold SierraLevelsOverlay badge is the only label.
5. **CVD pane fills with ~60 candles, not 14.**
   Requires **backend restart** to pick up the `history=1` query param (already in HEAD).

If any of these fail, look at:
- `tpoLevels.ts::todayRthWindowUnix()` returned values (browser devtools console: `Intl.DateTimeFormat...formatToParts(new Date())`)
- `/api/v9/cumulative_delta/current?history=1` response — check `history_count` field is non-zero
- WeakMap cleanup — `globalThis.__mems26YdayTpoStore` in browser console should have 1 entry per chart

---

## §3 — Open next tasks (priority order)

### Immediate (today / tomorrow morning)

| # | Task | Who | Sierra needed? |
|---|------|-----|----------------|
| 1 | Commit + push chart fixes (this session) | Cursor → Michael approves | No |
| 2 | Backend restart to load `?history=1` endpoint | Michael / CC | No |
| 3 | Verify the 5 chart UAT items in §2 | Michael in-the-eye | Yes (live RTH if before 16:00 ET; otherwise replay) |

### After RTH close (16:00 ET / 23:00 IL)

| # | Task | Who | Sierra needed? |
|---|------|-----|----------------|
| 4 | Confirm white lines stayed pinned at 16:00 ET | Michael in-the-eye | No (post-RTH) |
| 5 | EOD archiver auto-fires at 15:55 ET — verify `~/v9_archive/2026-05-22/` has 14 files | CC / Michael | No |
| 6 | TPOHistorySnapshotter wrote `v9_tpo_history` rows during RTH — verify | CC | No |

### Next agent's main task — S4 audit (Woodies)

**Template:** same as §14 (S2 audit done 12:04 IL). Each system gets:
- Code audit (what it does today)
- Spec (what it should do — `docs/handoff/agents/AGENT_S4_WOODIES_T2_FIRE_SPEC.md`)
- Gap analysis (matrix)
- Fix 1 — settings
- Fix 2 — bugs (with regression test)
- 4-axis UAT (Quality / Recency / Cardinality / Latency)

**S4 known issues to dig into:**
- Woodies dedup (`_last_fired_bar_ts`) is shipped (`fb390aa`) but not yet RTH-verified
- VEGAS 43% RTH vs 61% non-RTH WR (`P31-DEMO-D` — deferred to DEMO phase)
- ZLR 7.1% WR overall (`P31-DEMO-E` — possibly stop-too-tight or pattern-too-loose)

### Deferred (post-LIVE per current strategy)

- P31-DEMO-A..E (session-aware filters, performance audits)
- P31-PERF-D (S1/S2/S5 cross-context publishers — RCA-2)
- DLL canonical TZ fix (§9 Option A — bridge workaround is good enough for now)

---

## §4 — How to commit + push (do not blind-run)

```bash
cd /Users/michael/Downloads/mems26_web_git

git status -- frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts \
              frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx \
              tests/v9/api/test_cumulative_delta_routes.py \
              tests/v9/frontend/test_tpo_stepped_lines.py \
              tests/v9/frontend/test_tpo_overlay_six_lines.py \
              docs/handoff/P31_TASK_BOARD.md \
              docs/handoff/P31_NEXT_CHAT_2026-05-22_EVE_CHART.md

git add (above files)

git commit -m "fix(chart): yesterday POC lines RTH-bounded + follow-the-price + CVD history backfill

White POC/VAH/VAL of yesterday now render as LineSeries strictly bounded
to today's RTH window (09:30 → 16:00 ET, via Intl.DateTimeFormat probing
for EDT/EST). The right edge is now \`min(RTH close, now + 5min)\` so the
line visibly extends bar-by-bar instead of dangling 8h past the latest
candle. Cleanup uses a globalThis-scoped WeakMap that survives Next.js
HMR cycles, eliminating orphan lines on the chart. Native axis labels
are suppressed (\`lastValueVisible: false, title: ''\`) so the
SierraLevelsOverlay badge is the single source of right-axis pills.

CVD pane: \`fetchCvd\` now requests \`?history=1&limit=600\`, which the
backend (already in d9291e4) backfills from \`v9_bars_cumulative_delta\`
(122 rows / 10h vs the rolling 14-point JSON tail). The pane now renders
the full 5h visible window instead of just the latest hour.

Per Michael's RTH UAT instructions 2026-05-22 (16:30–18:11 IL).

Regression coverage:
- 5 new tests in test_tpo_stepped_lines.py
- 5 new tests in test_cumulative_delta_routes.py
- 1 updated test in test_tpo_overlay_six_lines.py
- 32/32 chart+CVD tests PASS

[P31-CHART-UAT]"

# push only after Michael's OK
git push origin stabilize/mems26-local-truth-2026-05-16
```

Note: `git push` may fail with 403 — the previous session left a
"manual push needed" note in the task board. If the push fails, escalate
to Michael (auth / branch protection).

---

## §5 — Reading order for the next agent

1. **This file** (§0–§3 above) — current state + open tasks
2. **`docs/handoff/P31_TASK_BOARD.md` §0 + §15** — what just shipped
3. **`docs/handoff/agents/AGENT_S4_WOODIES_T2_FIRE_SPEC.md`** — S4 spec
4. **`backend/v9/systems/woodies/`** — S4 code
5. **`CLAUDE.md`** + **`.cursor/rules/mems26-pre-live-protocol.mdc`** — guardrails

**Do not skip:** the 4-step verification protocol (Read → Audit → Probe → Bound).

---

## §6 — Known gotchas (avoid these traps)

| Trap | Mitigation |
|------|------------|
| `new Date(new Date().toLocaleString(...))` silently uses local TZ | Use `Intl.DateTimeFormat({ timeZone: 'America/New_York' })` + probe pattern |
| `WeakMap` reset by Next.js HMR loses series refs → orphan lines | Stash on `globalThis.<unique-name>` |
| `lightweight-charts` LineSeries with only 2 points truncates mid-chart when bars don't cover the range | Dense points every 5 min across the window |
| `createPriceLine` is infinite — too wide for "RTH-bounded" intent | Use `LineSeries` with explicit time bounds instead |
| Both LineSeries `title` AND SierraLevelsOverlay show right-axis labels → duplicates | Suppress LineSeries label: `lastValueVisible: false, title: ''` |
| CVD JSON file is a rolling 14-point tail (~1h) — not enough for 5h chart | DB-backed `?history=1` backfill |
| Backend restart unsolicited is forbidden | Ask Michael / CC; restart is operator-only |
| 2 pre-existing test failures in `test_tpo_routes_sierra_contract.py` | Time-relative fixtures aged out; not a regression — see `INVESTIGATE_TPO_VALUE_MISMATCH.md` |

---

## §7 — Out of scope for the next chat (deferred)

- **Price delay** (Michael 17:16 IL — "דיליי על המחיר") — separate backend deadlock task `P31-DT-CURRENT-DEADLOCK`. Workaround in place: polling floors `V9Dashboard 5s, SoundProvider 10s` (`CLAUDE.md`). Deeper fix = wire `app.state.*_system` for S2 + Woodies (already done for S2 via P31-02b) and remove HTTP self-calls in Woodies — non-trivial, post-LIVE.
- **DLL canonical TZ fix** (§9 Option A) — bridge workaround handles it; not blocking.
- **P31-DEMO-A..E** — session-aware filters, performance audits — deferred to DEMO phase per Michael's strategic ruling 2026-05-22 08:30 IL.

---

**End of handoff. Next agent: start with §0 → §3.**
