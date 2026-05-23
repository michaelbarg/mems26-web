# P31 — Chat handoff: Chart sync · POC overlay · Day Type / S2 fire

**Date:** 2026-05-21 17:35 IL · **Outgoing:** Cursor (afternoon session — §6/§9/§10/§11/02c done) · **Incoming:** Cursor (fresh chat) · **Owner:** Michael

> **READ FIRST:** `docs/handoff/P31_TASK_BOARD.md` §0 (current status) + §6/§9/§10 (today's fixes).
> **Don't repeat work that was done today.** This handoff lists only what's *still* broken.

---

## 0. Service state at handoff

| Service | PID | State |
|---------|-----|-------|
| `uvicorn backend.main:app :8000` | **12464** | 🟢 (Cursor restart 17:14, §11 cache loaded) |
| `python3 bridge/json_bridge.py` | **60596** | 🟢 (Cursor restart 14:55, §9 workaround active) |
| `next dev :3000` | **31297** | 🟢 |
| Backend log monitor | 10538 | 🟢 (regex `took 1[0-9]{4,}ms|JSON serializable|PendingRollback`) |

**Local commits ahead of origin (not pushed):** 3 — `2b4a4f8 §9`, `24e3573 board`, `c4e9218 §11`. Michael needs to `git push` from Terminal.app when ready (osxkeychain has the PAT).

**Working tree dirty:** ~60 files from prior sessions + frontend chart refactor (`CvdChartPane.tsx` 421 lines, `cvdMapping.ts` new). These were NOT committed by today's chats — they're WIP from the chart-sync work that the user reports is now broken.

---

## 1. Three issues to fix (user-reported 2026-05-21 17:32 IL)

### Issue A — CVD pane misaligned with 5-min candles

**Symptom (user):** *"הקולמטיב לא נמצא מתחת לזמן של ה-5 דקות במיקום הנכון, הוא יותר מדי שמאלה. כל נר של קולמטיב צריך להיות 5 דקות וגם למעלה הם צריכים להיות באותו זמן."*

**What changed recently:** uncommitted refactor of `CvdChartPane.tsx` (+421/−276) + new `cvdMapping.ts` (+171). These belong to the chart-sync work that was supposed to keep CVD aligned with the price chart.

**Files to read first:**
1. `frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx` — the pane itself
2. `frontend/v9/src/v9/components/chart/v5b/cvdMapping.ts` — new mapping logic (uncommitted)
3. `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` (~line 470 `loadBars`, ~line 547 `fetchCvd`) — main chart that the CVD pane mirrors
4. `frontend/v9/src/v9/stores/chartSyncStore.ts` — cross-pane time sync store

**What's already verified today (do NOT re-investigate):**
- DB `v9_bars_5min`: 120 rows today, 0 duplicates, all `.000000` microsec format (today's chat cleaned this).
- Backend `/api/v9/chart/bars5min` returns 200 unique bars, ASC by time, all UTC-correct (post §9 fix).
- Today's chart was crashing with `Assertion failed: data must be asc ordered by time` at `ChartV5b.tsx:531` — caused by `'14:25:00'` vs `'14:25:00.000000'` being different Map keys but same unix sec. Cleaned via SQL `DELETE + UPDATE`.

**Hypothesis to test:** CVD pane uses its own time-axis derivation (`cvdMapping.ts`) that may not match the price chart's `time` field. Compare the `time` value passed to `cvdSeries.setData()` vs `candleRef.current.setData()`. They must use the **same Unix-second granularity** AND **same per-bar bucket boundary** (5min buckets starting at :00/:05/:10/:15…).

**UAT for issue A:** open `localhost:3000`, look at any visible 5-min candle (e.g., the most recent one). The CVD bar **directly below it** must share the same X-axis tick (its center should align with the candle's center). If the CVD bar is to the LEFT of where it should be, the unix-sec offset between CVD-bucket-start and candle-bucket-start is wrong.

---

### Issue B — POC lines missing across continuous trading session

**Symptom (user):** *"POC והקווים שלו לא מופיעים כראוי, צריכים להופיע בכל הזמן של מסחר רציף."*

**Backend evidence (`/api/v9/tpo/current` at 17:35 IL):**
```json
{
  "running": true,
  "hydrated": true,
  "source": "sierra_tpo_json",
  "poc": 7432.75,
  "vah": 7444.25,
  "val": 7415.5,
  "session_opened_ts": "2026-05-21 09:30:00",
  "session_high": 7470.0,
  "session_low": 7410.0,
  "ib_high": 7480.5,
  "ib_locked": true,
  "stale": false,
  "age_s": 1.36
}
```

POC + VAH + VAL data **exists in the API**, fresh (1.36s age). So the issue is **frontend display**, not data.

**Note about `session_opened_ts`:** `"2026-05-21 09:30:00"` — interpreted as UTC = 12:30 IL = 06:30 ET. Real RTH open is 09:30 ET = 14:30 UTC = 17:30 IL. So this value is suspicious — may be encoded in Chicago wall-clock (same §9 DLL bug). Verify before assuming POC lines should start at this time.

**Files to read first:**
1. `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` — `applyTpoToChart` (referenced in deps at line 566)
2. Grep `frontend/v9/src/v9/components/chart/` for `poc`, `vah`, `val`, `priceLine`, `addLineSeries` to find where the lines are drawn
3. `backend/v9/api/v9/tpo_routes.py` — verify `_load_sierra_tpo()` returns the data structure the frontend expects

**Hypothesis to test:** POC line is drawn as a `priceLine` (horizontal price line spanning chart width) but its `time` range may be bounded by `session_opened_ts` which is buggy (Chicago wall-clock). Either:
1. Frontend draws line from `session_opened_ts` to "now" — if start is buggy (5h behind real session start), line might be off-screen or partial.
2. Frontend only draws POC line when current time is within session — current Day Type misclassification (Issue C) may suppress it.

**UAT for issue B:** in browser DevTools, find the POC chart series and inspect its data points. Should be a horizontal line at `y=7432.75` spanning the visible session.

---

### Issue C — Day Type misclassified → S2 doesn't fire

**Symptom (user):** *"סוג היום — האבחנה לא נכונה, בגלל זה 5 דקות בטח לא יורה."*

**Backend evidence (`/api/v9/day_type/current` at 17:35 IL):**
```json
{
  "day_type": "Trend_Normal",
  "confidence": 65,
  "ib_h": 7480.5,
  "ib_l": 7472.25,
  "ib_range": 8.25,
  "extension_ratio": 7.545,
  "classified": false,
  "source": "v1_demoted",
  "reason": "V9 has not classified today; V1 result available but not canonical"
}
```

🔴 **`classified: false`** + **`source: "v1_demoted"`** + reason: *"V9 has not classified today; V1 result available but not canonical"*.

V9 day_type classifier never ran for today. V1 (legacy) classified it as `Trend_Normal` but the system marks this as not canonical, so downstream gates ignore it.

**Five-min state (`/api/v9/five_min/current`):**
```json
{
  "running": true,
  "hydrated": true,
  "mode": "FIRST_HOUR_TACTICAL",
  "buffer_size": 716,
  "opening_type": null,
  "last_pattern": null,
  "last_confluence": 0
}
```

`opening_type: null` — FiveMin doesn't know what day type to operate as. `buffer_size: 716` is huge (likely from accumulated bars including older sessions). `last_pattern: null` — no patterns fired.

**Files to read first:**
1. `backend/v9/systems/day_type/` — entire folder. Esp. `state_machine.py`, `api.py`, `prev_day.py` (committed earlier today as `5b75101`).
2. Search for "classified" / `classify_day` to find what gates the V9 classification:
   ```bash
   rg "classified.*True|set_classified|day_type.*classify" backend/v9/systems/day_type/
   ```
3. `backend/v9/systems/five_min/five_min_system.py` — `self.opening_type` is set from `hydrate()` based on day_type. If day_type never classifies, opening_type stays None.

**Hypothesis to test:** The V9 day_type classifier requires the IB to lock + extension_ratio to reach a threshold, AND probably requires `session_opened_ts` to be UTC-correct. Since `session_opened_ts` is `09:30 UTC` (suspicious — should be `14:30 UTC` = 09:30 ET), the classifier may think we're still pre-market and refuse to classify. Cross-reference with §9 DLL TZ bug.

**Pre-LIVE blocker:** Without correct day_type, **S2 can't fire** (per spec section 8 — gateway requires day_type for confluence). The user is right that fixing this is mandatory.

**UAT for issue C:**
1. Set day_type manually via API (if available) — does S2 start firing?
2. Check `session_opened_ts` actual value vs real RTH (09:30 ET = 14:30 UTC = 17:30 IL today)
3. If S2 patterns fire after correct classification → bug confirmed in classifier's time-based gates

---

## 2. Suggested working order

1. **Issue C first** — Day Type / S2 firing is the **pre-LIVE blocker**. Without it, the whole SHADOW soak gate is meaningless.
2. **Issue B next** — POC display. Likely related to the same `session_opened_ts` TZ bug that's blocking C.
3. **Issue A last** — CVD alignment is a UI bug, doesn't affect trading logic.

**Why this order:** A and B may both resolve themselves if C's root cause (TZ on session_opened_ts) is found and fixed. Don't waste time on UI fixes first.

---

## 3. Don't touch — what's already working

- `§6` FiveMin process_bar SLOW — fixed (commits `12b376f` + `0f5960d`, verified 75× faster).
- `§9` bridge Chicago→UTC workaround — active. Bridge PID 60596.
- `§10` SQLAlchemy JSON serializer — fixed (commit `9ba7d62`, in DB session).
- `§11` chop_score cache+timeout — active (commit `c4e9218`, TTL=60s).
- `P31-02c` bar_router thread-leak — cherry-picked (commit `3ed6a84`).
- `MES_AI_DataExport.cpp` DLL — **don't touch** (CC's domain — see `docs/runbooks/SIERRA_DLL_OPS.md`).
- `bridge/json_bridge.py` LaunchAgent — **don't touch** (`~/Library/LaunchAgents/com.mems26.bridge.plist`).

---

## 4. Useful commands for the next agent

```bash
# Current backend / bridge state
pgrep -fl "uvicorn|json_bridge"
curl -s http://127.0.0.1:8000/api/v9/day_type/current | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v9/tpo/current | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v9/five_min/current | python3 -m json.tool

# Today's bars sanity
sqlite3 data/mems26_local.db "SELECT COUNT(*), MIN(ts), MAX(ts) FROM v9_bars_5min WHERE date(ts)=date('now','localtime');"

# Backend log monitor (already running PID 10538) — check at any time:
tail -F /tmp/backend.log | grep --line-buffered -E "SLOW handler|day_type|FiveMin.*FIRE|Pattern.*fired"

# Sierra TPO file
ls -la /Users/michael/SierraChart_Data/v9_export/tpo.json
python3 -c "import json,datetime as dt;d=json.load(open('/Users/michael/SierraChart_Data/v9_export/tpo.json'));print('export_ts:',dt.datetime.utcfromtimestamp(d['export_ts']));print(json.dumps(d,indent=2)[:500])"
```

---

## 5. Pre-LIVE position when this handoff was written

- Phase 0 (P27.5), Phase 1-2 (P28/P29), P30 Waves — done.
- §6 / §9 / §10 / §11 / P31-02c — done today.
- **Pre-LIVE gate (P-S0 SHADOW activation):** **BLOCKED on Issue C** (day_type → S2 fire).
- Once C resolves and S2 fires successfully on a few RTH 5-min bars → SHADOW soak can begin.

---

## 6. End-of-session checklist for the incoming chat

- [ ] Read `docs/handoff/P31_TASK_BOARD.md §0` (current state) before doing anything.
- [ ] Check backend / bridge PIDs are still alive.
- [ ] Tail `/tmp/backend.log` for any `[day_type]` / `FIRE` messages while you work.
- [ ] Fix Issue C → verify S2 fires → fix B → fix A.
- [ ] Update `P31_TASK_BOARD.md §0` after each fix.
- [ ] Don't push commits without Michael's explicit `git push` from Terminal.app.
