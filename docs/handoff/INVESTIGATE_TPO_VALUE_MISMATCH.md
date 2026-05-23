# Investigation Prompt — TPO VAH/POC/VAL Mismatch (G4)

**For:** new chat or Claude Code subagent — read-only diagnostic.
**Mode:** observation only. No code edits, no service restarts, no git
ops. The fix comes **after** this audit confirms which layer is wrong.
**Reporter:** Michael, 2026-05-19, doc 06 (`~/Downloads/06_CRITICAL_ISSUES_TPO_TABLE_CLEANUP.md`)
**Claim:**

```
Sierra Chart (source of truth):
  TPO VAH = 7428.50
  TPO POC = 7411.25
  TPO VAL = 7390.75

MEMS26 Cockpit / our table:
  TPO VAH = 7385.25   ❌
  TPO POC = 7382.75   ❌
  TPO VAL = 7355.00   ❌
```

The cockpit is consistently ~40 points below Sierra. This is large enough
that "rounding" or "stale by a minute" cannot explain it — there is a
real bug somewhere.

---

## Background

Live status as of 2026-05-19 22:54 ET (see
`docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §9):

- Backend up on `:8000`, frontend up on `:3000`.
- Sierra DLL writes `tpo.json` directly to disk — **no bridge needed**
  for this file.
- `tpo.json` is **stale by ≈ 4 h** (last write at 11:55 ET on 2026-05-19);
  fresh updates have stopped despite RTH still being active until 16:00 ET.
- Backend `_normalize_sierra_tpo()` reads `data.get("session")` and
  exposes `session.poc / vah / val` as-is — no calculation happens in
  the backend.
- Frontend `SierraLevelsOverlay.tsx` reads `tpo.poc / tpo.vah / tpo.val`
  directly from the API.

So three layers could be wrong: (a) the DLL writing the wrong numbers to
`tpo.json`, (b) the backend reading the wrong field, (c) the frontend
displaying the wrong field.

---

## Procedure (in order, do not skip)

### Step 1 — Read the current `tpo.json` payload

```bash
python3 - <<'PY'
import json, os, time
p = '/Users/michael/SierraChart_Data/v9_export/tpo.json'
print('age_s:', round(time.time() - os.path.getmtime(p), 1))
d = json.load(open(p))
print('keys:', list(d.keys()))
print('session:', d.get('session'))
print('prior_day:', d.get('prior_day'))
print('previous_session:', d.get('previous_session'))
print('export_ts:', d.get('export_ts'))
PY
```

Capture:
- the `session.poc / vah / val` values that are physically on disk
- the `age_s` (how stale the file is)
- the `prior_day` block (to check we are not confusing prev day with today)
- whether `previous_session` exists (G2 gap)

### Step 2 — Compare against Sierra Chart at the **same** timestamp

This requires a Sierra screenshot taken at `export_ts` (the timestamp the
DLL stamped into `tpo.json` when it last wrote). Michael needs to:

1. Convert `export_ts` to ET local time.
2. In Sierra Chart, rewind crosshair to that timestamp.
3. Read off the TPO study's VAH / POC / VAL at that point in time.
4. Send screenshot to the investigator chat.

### Step 3 — Compare against the API response

```bash
curl -s --max-time 5 http://localhost:8000/api/v9/tpo/current | jq '.poc, .vah, .val, .session_va_ok, .stale, .age_s'
```

This proves whether the **backend** is reading the file correctly.
- If API values match the disk values from Step 1 → backend is honest.
- If API values differ → backend bug in `tpo_routes.py:_normalize_sierra_tpo`.

### Step 4 — Compare against the frontend display

Michael needs to:

1. Open Cockpit at `http://localhost:3000`.
2. Read off VAH / POC / VAL from the right-axis labels (added today —
   `TPO POC`, `TPO VAH`, `TPO VAL` tags).
3. Compare to Step 3 API response.
- If frontend differs from API → frontend bug in `SierraLevelsOverlay.tsx`.
- If frontend matches API but API differs from Sierra screenshot → DLL bug.

### Step 5 — Verdict

Fill in this table exactly (no narrative, just the truth values):

| Layer | VAH | POC | VAL | Matches next layer up? |
|-------|-----|-----|-----|------------------------|
| Sierra Chart (screenshot) | ? | ? | ? | — (source of truth) |
| `tpo.json` on disk | ? | ? | ? | Yes / No |
| `/api/v9/tpo/current` | ? | ? | ? | Yes / No |
| Cockpit right-axis labels | ? | ? | ? | Yes / No |

The first row where "Matches" turns from **Yes** to **No** is the layer
that owns the bug.

---

## Plausible root causes (do NOT pre-judge; let Step 5 tell you)

1. **`tpo.json` going stale at 11:55 ET** — Sierra DLL stopped writing
   updates mid-session, so the cockpit is displaying the TPO snapshot
   from ≈4 h ago. By definition that snapshot's VAH/POC/VAL are
   different from "now". This is **the most likely culprit** given §9.
   - Fix is for CC to debug why the DLL stopped writing — possibly the
     TPO study was detached from the 5 m chart in Sierra, or the export
     interval was paused, or Sierra Chart crashed and restarted but the
     TPO study did not auto-rebind.
2. **DLL writes Globex TPO, not CASH TPO.** Cockpit complains about TPO
   POC drifting low — if the DLL is exporting the rolling Globex session
   instead of the freshly opened CASH session, the values would be
   lower (because pre-RTH Globex traded lower in some sessions).
3. **DLL writes the wrong session date** — e.g. the previous CASH
   session got written into `session` instead of `previous_session`.
   Check via `prior_day.high/low/close` vs Sierra's previous day OHLC.
4. **Backend parses `tpo.json` from a wrong path** — env var
   `V9_TPO_EXPORT_PATH` might point at a stale copy. Check with:
   ```bash
   python3 -c "from backend.v9.api.v9 import tpo_routes; print(tpo_routes.SIERRA_TPO_PATH)"
   ```
5. **Frontend Cockpit reads from an old WebSocket frame**, not from the
   REST API. Unlikely but worth checking the browser dev-tools network
   tab.

---

## Deliverable format

A single Markdown block, no embellishment:

```
TPO VALUE AUDIT — 2026-05-19

EXPORT_TS captured: <unix int>
EXPORT_TS as ET: <YYYY-MM-DD HH:MM:SS ET>
FILE AGE at capture: <X> s

LAYER COMPARISON:
  Sierra Chart screenshot      | VAH=____ POC=____ VAL=____
  /Users/.../tpo.json on disk  | VAH=____ POC=____ VAL=____
  /api/v9/tpo/current          | VAH=____ POC=____ VAL=____
  Cockpit right-axis labels    | VAH=____ POC=____ VAL=____

FIRST MISMATCH LAYER: <DLL | backend | frontend>

ROOT CAUSE HYPOTHESIS: <a|b|c|d|e from §plausible-root-causes>

RECOMMENDED FIX OWNER: <CC | Cursor | Michael>
RECOMMENDED FIX LOCATION:
  file: <path>
  function: <name>
  one-sentence change: <text>

NO CODE CHANGE APPLIED IN THIS INVESTIGATION.
```

---

## Guardrails

- Read-only file system + DB.
- No service restarts.
- No git commits, no push.
- No `screen`, no `launchctl`, no `kill -9`.
- No editing `sc_study/`, `bridge/`, LaunchAgent, `.cursor/`.
- If the investigator cannot get a Sierra screenshot, **stop and tell
  Michael** — do not invent values to fill the table.

---

## What happens next

When the audit returns:

1. Cursor agent reads the verdict.
2. Updates inbox §3 G4 with the confirmed owner.
3. If owner = CC: extends the §4 mega-prompt's Step 4 with the precise
   DLL fix to make.
4. If owner = Cursor: opens a new gap entry, drafts a minimal fix with
   regression test, and verifies the four UAT axes
   (`.cursor/rules/mems26-pre-live-protocol.mdc`).
5. If owner = Michael (e.g. Sierra study detached): hands back to Michael
   with a runbook step.
