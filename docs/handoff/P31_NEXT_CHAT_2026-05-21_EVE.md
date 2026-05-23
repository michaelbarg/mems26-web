# P31 — Chat handoff: After Issue C (Day Type) + Issue A (CVD alignment) fixes

**Date:** 2026-05-21 19:55 IL · **Outgoing:** Cursor (evening session — Issue C + Issue A done) · **Incoming:** Cursor (fresh chat) · **Owner:** Michael

> **READ FIRST:** `docs/handoff/P31_TASK_BOARD.md` §0 (current status) + this doc.
> **Previous chat handoff:** [`P31_NEXT_CHAT_CHART_POC_DAYTYPE.md`](./P31_NEXT_CHAT_CHART_POC_DAYTYPE.md) — Issue C and Issue A there are now **DONE**, Issue B still open pending user clarification.
> **Don't re-investigate Issue C or Issue A** — both root causes were found, fixed, tested (12 new regression tests), and verified live.

---

## 0. Service state at handoff

| Service | PID | State | Started |
|---------|-----|-------|---------|
| `uvicorn backend.main:app :8000` | **57984** | 🟢 | 19:37:50 IL (Cursor restart #2 — loaded Issue A endpoint fix) |
| `python3 bridge/json_bridge.py` | **55100** | 🟢 | ~19:31 IL (Cursor restart via launchctl — loaded Issue A bridge fix) |
| `next dev :3000` | **90313** | 🟢 | unchanged from prior session |
| Bridge LaunchAgent | `com.mems26.bridge` | running | KeepAlive=conditional, do **not** touch |

**Backend restarts this session:** old PID 12464 → 43761 → 45728/57984 (twice). Day Type state machine reset each time; mid-session seed (P30 C1) fires correctly now that it also sets `machine.opening = OpeningType.INDETERMINATE` (fix in `backend/v9/api/v9/day_type_seed.py`).

**Bridge restart this session:** old PID 60596 → 55100 (once). Released the Chicago→UTC fix for CVD `points[].t`.

**Local commits ahead of origin:** unchanged from prior handoff (3 commits) **plus** all the new Issue C / Issue A work is in the working tree, NOT committed yet — Michael needs to review + commit + push.

**Working tree dirty (changed by this session) — `git status --porcelain` markers shown verbatim so `git diff <file>` works correctly:**

```
 M backend/main.py                                       (Issue C — pass lock_state + warning instead of debug)
 M backend/v9/systems/day_type/consumer.py               (Issue C — set status + confidence)
 M backend/v9/tests/test_day_type_consumer.py            (+5 regression tests)
 M bridge/v9_streams/cumulative_delta_stream.py          (Issue A — fix points[].t in bridge push)
 M backend/v9/api/v9/cumulative_delta_routes.py          (Issue A — fix points[].t in endpoint read)
 M tests/v9/api/test_cumulative_delta_routes.py          (+2 regression tests + 2 existing tests updated)
 M tests/v9/bridge/test_streams.py                       (+5 regression tests)
?? backend/v9/api/v9/day_type_seed.py                    (Issue C followup — NEW file from prior session, edited this session to seed machine.opening)
?? tests/v9/systems/test_day_type/test_mid_session_restart_seed.py  (NEW file from prior session, +2 regression tests added this session)
```

> **Heads-up for git diff:** the two `??` files are **untracked** (created in a prior session, never `git add`-ed). `git diff <file>` will show nothing for them; use `git status -uall` to confirm they exist or just `cat <file>` to read the content. To see all changes including the new files in one place: `git diff` for the `M` files + `cat` the two `??` files.

All other dirty files are from the prior handoff's working tree (see [`P31_NEXT_CHAT_CHART_POC_DAYTYPE.md` §0](./P31_NEXT_CHAT_CHART_POC_DAYTYPE.md)).

---

## 1. What's DONE this session — do NOT re-investigate

### ✅ Issue C — Day Type V9 classification

**Root cause (different from handoff's hypothesis):** schema drift in `v9_day_type_history` — `status NOT NULL` and `confidence NOT NULL` in the live SQLite DB, but the SQLAlchemy model marks both `nullable=True` (migration 014 acknowledged that SQLite can't `ALTER COLUMN` to drop NOT NULL). `DayTypeConsumer.consume()` never set either column → every UPSERT raised `IntegrityError` → swallowed at `_logger.debug` in `main._day_type_on_bar` → `v9_day_type_history` stayed empty all day → V9 endpoint returned `classified: false` → user-facing endpoint fell through to V1 demoted (`Trend_Normal`).

**NOT** the TZ on `session_opened_ts` (handoff's hypothesis) — the V9 classifier never gates on time strings.

**Followup bug exposed:** the P30 C1 mid-session-restart seed (`maybe_seed_ib_from_tpo`) jumped to `Stage.B1` without setting `machine.opening`. B1 returns early when `opening is None` → machine perma-stuck at `B1 / UNKNOWN`. Now seeds `opening = OpeningDetection(opening_type=OpeningType.INDETERMINATE, ...)` so B1 votes via the matrix (INDETERMINATE × any width → `DayType.Normal`).

**Live verification (4 UAT axes):**
- Quality: V9 endpoint returns `{ "day_type": "Normal", "confidence": 68, "classified": true, "source": "v9", "opening_type": "INDETERMINATE" }` (was `source: "v1_demoted"`).
- Recency: `last_updated_at` advances every 2–4 s (was frozen / row didn't exist).
- Cardinality: 1 row per `session_date` (UNIQUE constraint).
- Latency: API < 15 ms warm.

**S2 firing note:** the handoff claimed "S2 can't fire without day_type". Code audit (`rg day_type backend/v9/gateway/`) shows the gateway and S2 do **not** gate on day_type — it's advisory only (`time_stop_minutes` mapping in `setup_emitter.emit_t1_setup`). So fixing C fixed the user's visible display symptom but does **not** automatically make S2 fire. S2's actual non-firing today is pattern conditions (`AMT=0` in footprint, no Reactive/Initiative 4-bar match) — separate from C.

### ✅ Issue A — CVD pane time-axis alignment

**Root cause:** same DLL TZ bug as §9 (`SCDateTime::GetAsDouble()` returns Chicago wall-clock encoded as UTC unix), but for `cumulative_delta.json::points[].t`. The §9 bridge workaround in `BaseV9Stream._fix_chicago_bar_ts` only walks `BUGGY_TS_KEYS = ("bars", "history", "profiles", "levels")` and only rewrites the `ts` field. CVD points use a different array name (`points`) **and** a different field name (`t`), so they slipped through.

**Why frontend's `alignCvdPointTimesToPriceBars` couldn't recover:** frontend bar `tsToUnix` parses DB ts as EDT (`-04:00`) → unix is `real_utc + 4h`. CVD points stayed at `real_utc - 5h` (CDT). Diff = `9h` — doesn't match the heuristic's `EDT_SHIFT (4h)` / `EST_SHIFT (5h)` so no shift was applied. Result: CVD candles rendered ~9 h to the LEFT of price bars, mostly off-screen.

**Two-layer fix:**
1. `bridge/v9_streams/cumulative_delta_stream.py` overrides `_fix_chicago_bar_ts` to also rewrite `points[].t` (so bridge-pushed data is correct; needed for downstream DB readers / Redis caches).
2. `backend/v9/api/v9/cumulative_delta_routes.py` adds `_fix_chicago_points()` and calls it from `cumulative_delta_current()` — this endpoint reads `cumulative_delta.json` **directly** (not via the bridge), so the bridge fix doesn't help it. Both layers honour `V9_DISABLE_CHICAGO_TS_FIX=1` for clean cutover when §9 Option A (DLL canonical fix) ships.

**Live verification (4 UAT axes):**
- Quality: latest `points[-1].t` decodes to a UTC time within ~3 min of "now" (was ~5 h off).
- Recency: `age_s < 5 s` consistently (was already fine — the data was being polled; only the timestamps were buggy).
- Cardinality: 140 points returned (matches `point_count`).
- Latency: < 100 ms.

### Tests added — 12 new regression tests, 651/651 backend tests pass

| File | New tests | What they pin |
|------|-----------|---------------|
| `backend/v9/tests/test_day_type_consumer.py` | 5 | Consumer sets `status` + `confidence`; maps `lock_state`; succeeds against prod-schema NOT NULL constraints; handles missing probability; UPSERT under prod constraints |
| `tests/v9/systems/test_day_type/test_mid_session_restart_seed.py` | 2 | Seed populates `machine.opening`; full pipeline (seed → process_bar → to_classification) returns a non-None classification |
| `tests/v9/bridge/test_streams.py` | 5 | CVD bridge rewrites `points[].t`; preserves other fields; honours `V9_DISABLE_CHICAGO_TS_FIX`; tolerates missing/malformed `points`; still rewrites `bars[].ts` via super() |
| `tests/v9/api/test_cumulative_delta_routes.py` | 2 new + 2 updated | Endpoint Chicago→UTC fix is active by default; respects kill-switch; pre-existing tests updated to opt-out of the workaround when asserting other behavior |

Run: `python3 -m pytest backend/v9/tests/ tests/v9/systems/test_day_type/ tests/v9/bridge/test_streams.py tests/v9/api/test_cumulative_delta_routes.py -q --ignore=backend/v9/tests/e2e` — all green.

---

## 2. What's STILL open — Issue B (POC display)

### Symptom (user-reported, original Hebrew)
> "POC והקווים שלו לא מופיעים כראוי, צריכים להופיע בכל הזמן של מסחר רציף."
> ("POC and its lines do not appear properly, they should appear during all the continuous trading time.")

### What we found in this session (diagnosis only — no fix applied)

**Backend data is fine:** `/api/v9/tpo/current` returns `poc=7430.25, vah=7443.25, val=7415.0, ib_locked=true, session_high/low populated`. No "missing" data.

**Frontend rendering:** four overlapping TPO line systems run on the chart pane:
1. `syncTpoPriceLines()` in `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts` — today (pink) horizontal LineSeries, t0 = local `rthOpen` (09:30 ET attempt), t1 = now+5min.
2. `syncYesterdayTpoLines()` — yesterday (white) horizontal LineSeries, t0 = Globex open (18:00 ET), t1 = now+5min.
3. `TpoContinuityOverlay` (separate component, `paneIndex=0`) — stepped continuity lines built from `tpo.periods[]`.
4. `SierraLevelsOverlay` — SVG axis badges only (just the right-edge price labels, no lines).

**What I saw in the browser screenshot (Chrome via browser MCP):**
- Pink **today** POC/VAH/VAL lines visible **from ~17:30 IL onwards** (correctly maps to RTH open 09:30 ET = 14:30 UTC = 17:30 IL today).
- White **yesterday** POC/VAH/VAL lines visible on the **pre-RTH portion** (left of the 17:30 IL boundary).
- There is a clear visual transition at the boundary where white stops and pink starts.

**Hypothesis-grade observation (not confirmed as the actual bug):** the `rthOpen` calc in `tpoLevels.ts::syncTpoPriceLines` is structurally buggy — `new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }))` is parsed as **local TZ** in the browser, so `setHours(0,0,0,0)` lands on local midnight (IL), not ET midnight. Result: `rthOpenUTCISO = 2026-05-21T06:30:00.000Z` instead of correct `14:30:00.000Z` — 8 h early. Same bug in `TpoContinuityOverlay::isRth()`. Today this **accidentally works for Michael's IL TZ** because the resulting "local 09:30" maps approximately to the visible RTH portion of the chart. Will break for users in other TZs and across DST transitions.

**Open question for Michael (in Hebrew so he can reply naturally):**

> Issue B — מה בדיוק חסר/לא נכון בקווי ה-POC? לפי הצילום שראיתי, הקווים הוורודים של ה-POC/VAH/VAL של היום מופיעים מ-17:30 IL והלאה (זה אכן זמן פתיחת RTH), והקווים הלבנים של אתמול מופיעים בחלק שלפני. האם הכוונה ש:
>
> 1. ה-POC הוורוד של היום צריך להתחיל מוקדם יותר (לפני RTH)?
> 2. יש פערים/שבירות בקווים בתוך תקופת ה-RTH עצמה?
> 3. הקווים מופיעים בגובה מחיר שגוי?
> 4. ה-POC הלבן של אתמול חסר מהחלק לפני RTH?
> 5. הקווים צריכים להמשיך 24 שעות ביממה (כולל גלובקס + RTH של היום)?
> 6. משהו אחר?

Once Michael answers, the fix is mechanical (most likely in `tpoLevels.ts` or `TpoContinuityOverlay.tsx`). Until then, **do not guess** — the chart has multiple overlapping line systems and the wrong fix will create new visual inconsistencies.

### Files to read first when picking up Issue B
1. `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts` — `syncTpoPriceLines` (today/pink lines), `syncYesterdayTpoLines` (yesterday/white), `buildTpoPlan`, `isRthNow`, `isGlobexOpen`.
2. `frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx` — stepped continuity lines (separate code path, separate isRth check, separate period parsing with hardcoded `-04:00` EDT — see `periodToUnix`).
3. `frontend/v9/src/v9/components/chart/v5b/SierraLevelsOverlay.tsx` — SVG axis badges (read-only labels; not the issue).
4. `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` lines 914–925 — where the overlays are rendered.

### UAT for Issue B once a hypothesis is fixed
- Open `localhost:3000`, take a screenshot at any time during RTH.
- Pink today POC/VAH/VAL must be visible at the correct price levels for the period the user describes.
- White yesterday POC/VAH/VAL must be visible for the period the user describes.
- No gaps/breaks in the continuous trading area (whatever the user defines as that).
- Cross-verify the data via `curl -s /api/v9/tpo/current` — UI levels must match API levels.

---

## 3. Known structural issues uncovered but NOT fixed (low priority follow-ups)

These were noticed during diagnosis but are **not blockers**; they're filed as follow-ups so we don't lose them.

| ID | File | Symptom | Why deferred |
|----|------|---------|--------------|
| **P31-DT-CURRENT-DEADLOCK** ⚠️ | `backend/v9/systems/day_type/api.py::get_current` | `/api/v9/day_type/current` makes 3 synchronous `requests.get` self-calls (lines 235 to V9 endpoint, 132 to killzone, 143 to tpo) with `timeout=2`. Under heavy frontend polling the FastAPI loop deadlocks — endpoint returns HTTP 000 or falls through to V1 with TPO timeout → `{day_type: UNKNOWN, classified: false, source: null}` (NOT V1 demoted; the TPO call failed). **Same root pattern as §6 FiveMin SLOW (HTTP self-calls).** Issue C fix is intact (state machine + `v9_day_type_history` UPSERT keep working under the deadlock); only the aggregator endpoint stalls. `/api/v9/day_type/v9/current` (direct DB read) keeps working. | Pre-existing pattern; same setter-injection fix as P31-02b will apply (inject `tpo_system` + `killzone_system` into the api.py module). Out of scope for Issue C — but please pick this up next session and ask Michael before adding more HTTP self-call surface area. |
| **P31-FE-TZ-1** | `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts::syncTpoPriceLines` | `rthOpen` computation parses NY-formatted string as local TZ → off by `(local_tz - ET)` hours. Accidentally works for IL (UTC+3, so "12:13 PM" string parses as IL 12:13 = ET 05:13 in this combination). Will break in EST winter or for users in other TZs. | No live symptom for Michael; would change visible chart for everyone — needs deliberate plan. |
| **P31-FE-TZ-2** | `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx::tsToUnix` + `cvdMapping.ts::tsToUnix` | Hardcoded `-04:00` (EDT). Post-§9 the DB ts is already UTC, so this adds a spurious +4 h on the chart time axis (chart shows 20:05 IL labels for actual 16:05 UTC bars). The CVD alignment heuristic was written around this same shift, so removing it requires updating both sides at once. | Frontend visible time labels look "right enough" to the user; the real fix is to stop parsing as EDT and respect UTC suffix. Out of scope for Issue A/C. |
| **P31-FE-TPO-1** | `frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx::periodToUnix` | Appends `-04:00` to strings that may already have `+00:00` suffix (e.g. periods array first element is `"2026-05-20 15:55:00+00:00"`). Result: `'2026-05-20T15:55:00+00:00-04:00'` → `Date.parse` returns `NaN` → that period is silently filtered out. | Step-continuity lines may be missing one period. User hasn't reported the symptom specifically. |
| **P31-DLL-CDT-A** | `sc_study/v9_exports.h::v9_sc_datetime_to_unix` | Original DLL TZ bug. §9 bridge + Issue A fixes are workarounds — **CC owns the canonical fix** (see §9 Option A in `P31_TASK_BOARD.md`). | Not urgent (workarounds active); requires Sierra Chart build + reload. |
| **P31-S2-AMT-ZERO** | `backend/v9/systems/five_min/five_min_system.py::_detect_reactive` | `_get_amt_from_footprint()` returns 0.0 today → `cot_above_amt` check (`cot > amt`) with `cot = -169672` is False → reactive LONG can never fire on a falling tape. Mirror SHORT is fine. | Affects S2 fire rate, NOT a code bug per se — the footprint AMT calculation upstream may be the real issue. |

> **Re: P31-DT-CURRENT-DEADLOCK** — verified 19:58 IL: state machine has fresh `B2 / Normal` row in `v9_day_type_state` (id=7399 at 16:58:12 UTC); consumer wrote `Normal / PENDING / 68 / INDETERMINATE / 16:58:14 UTC` to `v9_day_type_history`. So Issue C fix is **functionally healthy in the engine + DB**, only the aggregator HTTP endpoint stalls intermittently. The cockpit (which polls `/current`) will see "UNKNOWN" flicker during heavy load. The fix is symmetric to §6/P31-02b but needs Michael's go-ahead before opening that thread.

---

## 4. Useful commands for the next agent

```bash
# Current backend / bridge state
lsof -i :8000 -sTCP:LISTEN | head -3
pgrep -fl json_bridge
ps -o pid,lstart,command -p $(lsof -i :8000 -sTCP:LISTEN -t)

# Day Type sanity (Issue C verification)
curl -s http://127.0.0.1:8000/api/v9/day_type/current | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v9/day_type/v9/current | python3 -m json.tool
sqlite3 data/mems26_local.db "SELECT date, day_type, status, confidence, opening_type, last_updated_at FROM v9_day_type_history WHERE date = date('now')"

# CVD sanity (Issue A verification)
curl -s http://127.0.0.1:8000/api/v9/cumulative_delta/current | python3 -c "
import sys, json, datetime as dt
d = json.load(sys.stdin); pts = d.get('points', [])
if pts:
    diff = int(dt.datetime.utcnow().timestamp()) - pts[-1]['t']
    print(f'last point.t={pts[-1][\"t\"]} = {dt.datetime.utcfromtimestamp(pts[-1][\"t\"])} UTC, diff={diff}s ({diff/60:.1f}min)')
    print('ACTIVE' if abs(diff)<600 else 'INACTIVE')"

# All tests for this session's surface
python3 -m pytest \
  backend/v9/tests/test_day_type_consumer.py \
  tests/v9/systems/test_day_type/test_mid_session_restart_seed.py \
  tests/v9/bridge/test_streams.py \
  tests/v9/api/test_cumulative_delta_routes.py \
  -q

# Backend restart (correct pattern — kill the PYTHON process, not the wrapper)
kill $(lsof -i :8000 -sTCP:LISTEN -t)
sleep 3
cd /Users/michael/Downloads/mems26_web_git && set -a && . ./.env && set +a && \
  export DATABASE_URL=sqlite:///./data/mems26_local.db && \
  nohup env BRIDGE_TOKEN="$BRIDGE_TOKEN" DATABASE_URL="$DATABASE_URL" \
    UPSTASH_REDIS_REST_URL="$UPSTASH_REDIS_REST_URL" \
    UPSTASH_REDIS_REST_TOKEN="$UPSTASH_REDIS_REST_TOKEN" \
    CLOUD_URL="$CLOUD_URL" \
    python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 >> /tmp/backend.log 2>&1 &
disown
sleep 6
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/api/v9/health

# Bridge restart (via LaunchAgent)
launchctl kickstart -k gui/$(id -u)/com.mems26.bridge
sleep 3
pgrep -fl json_bridge
```

**Gotcha for backend restart:** `pgrep -f "uvicorn backend.main" | head -1` returns the **bash wrapper** first, not the python process. Use `lsof -i :8000 -sTCP:LISTEN -t` to get the actual python PID.

---

## 5. Suggested working order for the next chat

1. **Wait for Michael's answer to the Issue B clarification question** (in §2 above). Do not guess; multiple overlapping line systems make wrong fixes easy.
2. **Verify Issue C + Issue A are still live** (the two `curl` commands in §4).
3. **Update `P31_TASK_BOARD.md` §0** — outgoing chat didn't update it; the board still says "Day Type → S2 fire — pre-LIVE blocker" but C is now done. Ask Claude Code to draft the update (per the always-applied workspace rule: "At the end of every prompt, fix, UAT, or phase gate, ask Claude Code to prepare or update the report before moving on").
4. **Fix Issue B** once Michael answers.
5. **Then** revisit S2 firing: is the only remaining blocker `AMT=0` (P31-S2-AMT-ZERO above), or is there something else?
6. Strategic stop, then plan P-S0 (SHADOW activation) — that's the next pre-LIVE gate per the road map.

---

## 6. Pre-LIVE position when this handoff was written

| Phase | Status | Note |
|-------|--------|------|
| P27.5 / P28 / P29 / P30 Waves | ✅ | Done (prior sessions) |
| §6 FiveMin SLOW | ✅ | 75× speedup (prior session) |
| §9 Bridge Chicago→UTC for `bars[].ts` | ✅ | Active (prior session) |
| §10 SQLAlchemy JSON serializer | ✅ | Active (prior session) |
| §11 chop_score cache | ✅ | Active (prior session) |
| P31-02c bar_router thread leak | ✅ | Done (prior session) |
| **Issue C — Day Type V9 classification** | ✅ | **THIS SESSION** |
| **Issue C followup — seed populates `machine.opening`** | ✅ | **THIS SESSION** |
| **Issue A — CVD `points[].t` Chicago→UTC** | ✅ | **THIS SESSION (bridge + endpoint, two layers)** |
| Issue B — POC display | 🟡 | Pending Michael's clarification |
| P-S0 SHADOW activation | ⬜ | Still gated on (a) Issue B, (b) S2 actually firing on a few RTH bars |
| SHADOW soak | ⬜ | After P-S0 |

---

## 7. End-of-session checklist for the incoming chat

- [ ] Read this doc top-to-bottom and `docs/handoff/P31_TASK_BOARD.md` §0.
- [ ] Run the §4 sanity curls before doing anything — confirm Issue C + Issue A are still active in your environment.
- [ ] Ask Michael for the Issue B clarification (paste the Hebrew question from §2 verbatim).
- [ ] Do NOT touch `sc_study/`, `bridge/json_bridge.py`, `~/Library/LaunchAgents/com.mems26.bridge.plist`, or any `CLOUD_URL` setting (workspace rules).
- [ ] Do NOT commit / push without Michael's explicit ask. Working tree has 9 modified files from this session; Michael will commit when ready.
- [ ] If you restart the backend: use `lsof -i :8000 -sTCP:LISTEN -t` to get the python PID — do **not** trust `pgrep -f uvicorn` (returns the bash wrapper first).
- [ ] If you restart the bridge: use `launchctl kickstart -k gui/$(id -u)/com.mems26.bridge` — do **not** spawn it manually (the LaunchAgent sets the env correctly).
- [ ] After any meaningful fix or UAT pass, ask Claude Code to update `docs/reports/PROMPT_P31_*.md` and `P31_TASK_BOARD.md` §0 before moving on.
