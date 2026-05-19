# P30.9 — Claude Code Mega Prompt (copy everything below the line)

---

You are closing **P30.9 Sierra Screen Parity** and refreshing MEMS26 work documents so Michael knows exactly how to proceed toward LIVE. This is **documentation + live UAT only** unless you find a trivial doc fix; do **not** change trading logic, risk surface, bridge CLOUD_URL, or LaunchAgent plist.

**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Recent commits (already pushed):**
- `98724ab` — feat(P30.9): Sierra TPO API, stepped chart overlay, 5min hardening
- `4b2c263` — chore(P30.8): modular Sierra version labels v9.3.1-p30.8

**Repo:** `/Users/michael/Downloads/mems26_web_git`

---

## 1. Goal

Produce **accurate, post-UAT work documents** so the team can answer:

1. Is P30.9 **GREEN**, **PARTIAL**, or **BLOCKED**?
2. What is proven live vs only in code?
3. What is the **single next thread** (P30.9b CVD? P30.10 Woodies panel? Sierra `periods[]` export?)?
4. What must Michael do manually (Sierra rebuild, bridge mode, visual compare)?

---

## 2. Safety (non-negotiable)

- Bridge **only** `CLOUD_URL=http://localhost:8000`. If `/tmp/bridge.err.log` shows push to `https://...`, **STOP** and report config drift.
- Do **not** start full 12-stream bridge without explicit Michael approval. Narrow mode OK: `--bars-5min-only` + `V9_SKIP_HISTORY=1`.
- Do **not** run `npm run dev`, `next dev`, or `scripts/start_all.sh` unless Michael asked.
- Before starting services: check listeners on `127.0.0.1:3000` and `127.0.0.1:8000`.
- Do **not** enable SHADOW/DEMO/LIVE or write `trade_command.json`.
- Do **not** regenerate `MES_AI_DataExport_merged.cpp` from modular sources (modular still v9.3.1-p30.8; monolith v9.4.0-p30.9).

---

## 3. What was implemented (verify in code, do not assume)

### Backend
| Item | Location |
|------|----------|
| Sierra `tpo.json` → `/api/v9/tpo/current` | `backend/v9/api/v9/tpo_routes.py` — `source=sierra_tpo_json`, max age 30s |
| `periods[]` from DB interim | `_load_tpo_periods()` from `v9_tpo_sessions` |
| Woodies 5m `current_bar` POST | `backend/v9/api/v9/bars.py` — `Woodies5MinPayload` |
| 5min POST: no erroneous cumulative_delta dispatch; BarRouter only on insert | `bars.py` `post_bars_5min` |

### Frontend
| Item | Location |
|------|----------|
| Stepped POC, cyan IB, white prior-day overlay | `frontend/v9/src/v9/components/chart/v5b/SierraLevelsOverlay.tsx` |
| ChartV5b integration (no full-width TPO price lines) | `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` |

### Sierra exports (Michael's machine)
| File | Role |
|------|------|
| `/Users/michael/SierraChart_Data/v9_export/tpo.json` | Session POC/VAH/VAL, IB, prior_day — **source of truth for levels** |
| `5min.json` | OHLCV only; `poc_vol`/`vah`/`val` zeros are **not** TPO truth |
| `woodies_5min.json` | Woodies 5m panel data |
| `cumulative_delta.json` | CVD points (`i`, `d`, `cum`, `p`) — **no GET API yet for UI pane** |

### Tests (run and paste output)
```bash
cd /Users/michael/Downloads/mems26_web_git
pytest tests/v9/api/test_tpo_routes_sierra_contract.py \
       tests/v9/api/test_woodies_5min_payload.py \
       tests/v9/db/test_api.py \
       tests/v9/bridge/test_streams.py -q
```

---

## 4. Mandatory live UAT (four axes — all required for GREEN)

Run only if Michael has approved service bring-up. Record **raw command output** and timestamps in the report.

### 4.1 Services
```bash
# Listeners (must not duplicate)
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN

# Sierra export freshness
ls -la /Users/michael/SierraChart_Data/v9_export/tpo.json \
       /Users/michael/SierraChart_Data/v9_export/5min.json \
       /Users/michael/SierraChart_Data/v9_export/cumulative_delta.json
python3 -c "
import json, time, os
for f in ['tpo','5min','cumulative_delta']:
  p=f'/Users/michael/SierraChart_Data/v9_export/{f}.json'
  d=json.load(open(p)); age=time.time()-os.path.getmtime(p)
  print(f, 'age_s=', round(age,1), 'version=', d.get('version'), 'type=', d.get('type'))
"
```

### 4.2 API — TPO current
```bash
curl -s -w "\nlatency_ms=%{time_total}\n" http://127.0.0.1:8000/api/v9/tpo/current | python3 -m json.tool | head -50
```

| Axis | Check |
|------|--------|
| **Quality** | `source=sierra_tpo_json`, `poc`/`ib_*`/`prior_day` non-null and plausible vs Sierra screenshot or `tpo.json` file |
| **Recency** | `tpo.json` mtime &lt; 30s; API `age_s` &lt; 30 if present |
| **Cardinality** | `len(periods) >= 1` if DB has sessions; document if empty |
| **Latency** | `/api/v9/tpo/current` &lt; 500ms (record actual) |

### 4.3 API — 5m bars (regression)
```bash
curl -s -w "\nlatency_ms=%{time_total}\n" "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=600" | python3 -c "
import sys,json
raw=sys.stdin.read().split('latency_ms=')
rows=json.loads(raw[0])
print('count', len(rows))
print('latest', rows[-1] if rows else None)
print('latency_ms', raw[1].strip() if len(raw)>1 else '?')
"
```

| Axis | Check |
|------|--------|
| **Quality** | OHLCV valid; no duplicate ts groups |
| **Recency** | `latest.ts` == `MAX(ts)` in DB (query SQLite if needed) |
| **Cardinality** | `len(rows)==600` when limit=600 |
| **Latency** | &lt; 2s documented threshold |

### 4.4 Visual — ChartV5b (browser)
Michael's contract from screenshots:
- **Magenta POC** steps ~every 30m (not full-width static lines)
- **Cyan IB** (not green `#4ade80`)
- **White** prior-day levels
- **Cumulative delta pane below price** — **NOT YET IMPLEMENTED**; mark as open gap

Capture: screenshot or short note “overlay visible Y/N”, “POC steps Y/N”, “IB cyan Y/N”.

Compare levels to Sierra at same bar time (±0.25 tick tolerance).

---

## 5. Documents you MUST update

Update **in place** with dated evidence sections (`## UAT 2026-05-19` or today’s date). Do not leave stale “UI blocked” language if overlay is shipped.

### Primary
| File | Action |
|------|--------|
| `docs/reports/PROMPT30_9_SIERRA_SCREEN_PARITY.md` | Set top **Status** line; add UAT table (4 axes × endpoint); list **Done / Partial / Blocked** per screen; **Next thread** section |

### Cross-reference (short addendum only if facts changed)
| File | Action |
|------|--------|
| `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md` | Confirm still GREEN for 5m pipeline; note bars-only bridge mode if verified |
| `docs/reports/PROMPT30_7_CHART_HISTORY_RENDERING.md` | Note ChartV5b overlay does not regress scroll-back (if tested) |

### Optional index (create if missing)
| File | Action |
|------|--------|
| `docs/reports/P30_ROADMAP.md` | **Create** one-page table: P30.0–P30.9 status, next P30.9b/CVD, blockers, owner |

---

## 6. Status rubric (use exactly)

| Status | Meaning |
|--------|---------|
| **GREEN** | All four UAT axes pass for touched surfaces; regression tests pass |
| **PARTIAL** | Code shipped; live UAT incomplete OR CVD/VAH stepped gaps remain |
| **BLOCKED** | Sierra export missing/stale, API wrong source, or bridge drift |

**P30.9 cannot be GREEN** until ChartV5b visual is checked AND `/api/v9/tpo/current` passes four axes. CVD pane absence keeps at most **PARTIAL** unless Michael explicitly defers CVD to P30.9b.

---

## 7. Known gaps (classify KEEP / ADAPT / DEFER in report)

| Gap | Recommendation |
|-----|----------------|
| `tpo.json` lacks native `periods[]` | **DEFER** Sierra DLL; **KEEP** DB interim in API |
| `bridge/v9_streams/tpo_stream.py` old contract | **ADAPT** or **DEFER** until full bridge approved |
| `post_tpo()` old `bars[]` schema | **ADAPT** when bridge ingests new tpo.json |
| Cumulative Delta pane in ChartV5b | **Next:** P30.9b — GET from Sierra file or enrich 5m bars |
| VAH/VAL stepped overlay | **DEFER** after POC UAT passes |
| Woodies 5m live in UI | Needs bridge stream `woodies_5min` + panel component |
| Full 12-stream bridge overload | **DEFER** — stay bars-only |

---

## 8. Recommended “how to proceed” block (put at end of P30.9 report)

Write a section **## How Michael Proceeds** with numbered steps, e.g.:

1. Rebuild Sierra study showing **`MES AI Data Export v9.4.0-p30.9`** on chart.
2. Confirm `tpo.json` + `5min.json` fresh under `SierraChart_Data/v9_export/`.
3. Backend + frontend up; bridge **`--bars-5min-only`** only.
4. Open Cockpit ChartV5b — verify overlay vs screenshot.
5. If GREEN on data axes but CVD missing → open **P30.9b** (CVD pane + GET API) as single thread.
6. Do **not** advance to LIVE trading until P30 phase gate says so.

---

## 9. Deliverables checklist (your reply to Michael)

- [ ] Updated `PROMPT30_9_SIERRA_SCREEN_PARITY.md` with final status + UAT evidence
- [ ] Optional `P30_ROADMAP.md` created/updated
- [ ] Pytest output pasted or summarized (pass count)
- [ ] Raw curl/Sierra freshness output pasted
- [ ] Explicit **Next single thread** ID (e.g. P30.9b CVD)
- [ ] List of anything **BLOCKED** requiring Michael decision

**Do not** claim `streams=12/12` without heartbeat raw proof. **Do not** mark GREEN on quality axis only (P27.5a lesson).

---

## 10. Reference — Michael’s visual contract (screenshots)

1. 5m chart: TPO VAH/VAL dashed magenta, POC solid magenta **stepped in time**, IB cyan, CVD bars below  
2. TPO profile screen (letters) — separate P-ID later  
3. Woodies CCI 5m — separate P-ID  
4. Tick Reversal 15 — separate P-ID  
5. 3m dual TPO periods — may share overlay logic later  

P30.9 scope for this gate: **#1 data + ChartV5b overlay only**.

---

*End of mega prompt — paste from section 1 through section 9 into Claude Code.*
