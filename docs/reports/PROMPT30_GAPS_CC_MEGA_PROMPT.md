# P30 Gaps Closure — Claude Code Mega Prompt (copy from §1 below)

**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Repo:** `/Users/michael/Downloads/mems26_web_git`  
**Context docs:** `P30_ROADMAP.md`, `PROMPT30_9_SIERRA_SCREEN_PARITY.md`, `PROMPT30_8_5MIN_JSON_EXPORT.md`

---

## §1 — Mission

Close **documented gaps** between Sierra screenshots and MEMS26 Cockpit so Michael has a clear **GREEN path** before LIVE. Work in **one thread at a time**. Default order: **P30.9 RTH sign-off → P30.9b CVD → doc commit → optional P30.9c VAH/VAL**.

You may **implement code** only where specified below. Otherwise: UAT, docs, and evidence.

---

## §2 — Safety (non-negotiable)

- Bridge: `CLOUD_URL=http://localhost:8000` only. Never cloud URL.
- No full 12-stream bridge without explicit Michael approval. OK: `--bars-5min-only`, `V9_SKIP_HISTORY=1`.
- Do not change LaunchAgent plist / `KeepAlive=true`.
- No SHADOW/DEMO/LIVE, no `trade_command.json`.
- Do not regenerate `MES_AI_DataExport_merged.cpp` from modular sources.
- Check `127.0.0.1:3000` and `127.0.0.1:8000` before starting duplicate services.

---

## §3 — Gap inventory (what is missing)

### A. P30.9 — still PARTIAL (not GREEN)

| # | Gap | Owner | Type |
|---|-----|-------|------|
| A1 | **RTH visual UAT** — ChartV5b overlay vs Sierra screenshot (stepped POC, cyan IB, white prior-day) | Michael + CC evidence | UAT only |
| A2 | **`periods[]` empty pre-RTH** — stepped POC needs DB sessions or Sierra `periods[]` | CC verify at RTH; Sierra DLL later | Data |
| A3 | **VAH/VAL stepped lines** — only POC stepped in `SierraLevelsOverlay.tsx` | Code P30.9c | Frontend |
| A4 | **CC report files not in git** — `P30_ROADMAP.md`, updated `PROMPT30_9_*` may be local only | CC commit | Docs |

### B. P30.9b — NEXT code thread (highest priority implementation)

| # | Gap | Current state | Target |
|---|-----|---------------|--------|
| B1 | **No GET for cumulative delta** | Only `POST /api/v9/bars/cumulative_delta` (bridge) | `GET /api/v9/chart/cumulative_delta` or `/api/v9/cumulative_delta/current` reading Sierra file (mirror `price_routes.py` + `tpo_routes.py`) |
| B2 | **No CVD pane in ChartV5b** | ChartV5a has proxy strip from bar volume sign | Second pane or bottom strip: Sierra `cumulative_delta.json` points `{i, d, cum, p}` |
| B3 | **Sierra file contract** | `/Users/michael/SierraChart_Data/v9_export/cumulative_delta.json` — type `cumulative_delta`, version `v9.4.0-p30.9` | Document mapping `i` → bar index / time alignment with `bars5min` |

**Reference implementation patterns:**
- `backend/v9/api/v9/price_routes.py` — read JSON from export dir, max age check
- `backend/v9/api/v9/tpo_routes.py` — Sierra file + normalize + `source` field
- `frontend/.../ChartV5a.tsx` lines ~542–567 — cumDelta strip (upgrade to real API data)

### C. Bridge / ingestion (DEFER unless Michael approves narrow stream add)

| # | Gap | File |
|---|-----|------|
| C1 | `TpoStream` still documents old `bars: [{letter, price, level}]` | `bridge/v9_streams/tpo_stream.py` |
| C2 | `post_tpo()` ignores new `session` / `ib` / `prior_day` | `backend/v9/api/v9/bars.py` |
| C3 | `woodies_5min` not in bars-only bridge | `bridge/json_bridge.py` — add stream only if Michael approves |
| C4 | Full 12-stream bridge overload | P30.11 — do not start |

### D. Later screens (separate P-IDs)

| P-ID | Gap |
|------|-----|
| P30.10 | Woodies 5m panel (CCI/TCCI/ZLR) — `woodies_5min.json` live; UI = `WoodiesLensContent` not 1:1 chart panel |
| P30.11 | Footprint/TPO profile letters screen |
| P30.12 | Tick Reversal 15 numbers bars panel |
| — | Sierra native `periods[]` in `tpo.json` (replace DB interim) |

### E. Tech debt (note only, do not block P30.9b)

- Flaky: `test_publish_threadsafe_warns_when_unbound` (P27.5) — 1 fail in full suite
- `5min.json` `poc_vol`/`vah`/`val` zeros — **not** TPO truth; never use for overlay

---

## §4 — Execution order

### Phase 0 — Docs hygiene (15 min)
1. Commit if missing: `docs/reports/P30_ROADMAP.md`, `docs/reports/PROMPT30_9_SIERRA_SCREEN_PARITY.md` (CC UAT section).
2. Ensure `P30_ROADMAP.md` matches reality after your work.

### Phase 1 — P30.9b CVD (implementation)

**Backend**
1. Add `backend/v9/api/v9/cumulative_delta_routes.py` (or extend `chart` routes):
   - Read `V9_CUMDELTA_EXPORT_PATH` default `.../v9_export/cumulative_delta.json`
   - Max age env `V9_CUMDELTA_MAX_AGE_S` default 30
   - Return: `{ source: "sierra_cumulative_delta_json", points: [...], session_delta, current_delta, age_s, version }`
   - `logger.warning` if stale/missing (not debug)
2. Register router in FastAPI app (find pattern from `tpo_routes`).
3. Test: `tests/v9/api/test_cumulative_delta_routes.py` — mock file, stale rejection, normalize.

**Frontend**
1. `CumulativeDeltaPane.tsx` under `chart/v5b/` — fetch GET every 5s (or WebSocket later).
2. Integrate in `ChartV5b.tsx`: layout = price chart (flex 1) + CVD pane (fixed height ~80–120px).
3. Map points to bar times: align `point.i` with bar index in `allBarsRef` / `barsForOverlay`; fallback to time from `bars5min` if needed.
4. Style: green/red bars or OHLC-style delta bars per Sierra screenshot (Michael's #1 screen).

**UAT (four axes)**
```bash
curl -s -w "\nlatency=%{time_total}\n" http://127.0.0.1:8000/api/v9/chart/cumulative_delta
# or whatever path you choose — document in report
```
- Quality: points non-empty, `cum` monotonic-ish, matches Sierra file
- Recency: file age < 30s
- Cardinality: point count documented vs Sierra `len(points)`
- Latency: < 500ms

### Phase 2 — P30.9 RTH sign-off (if market open)

When `ib.found=true` in `tpo.json` / API:
```bash
curl -s http://127.0.0.1:8000/api/v9/tpo/current | python3 -m json.tool
```
- Compare poc/vah/val/ib_* to Sierra TPO screen ±0.25
- Screenshot ChartV5b overlay vs Sierra
- If API + visual pass: set P30.9 → **GREEN (data contract)** in `PROMPT30_9` (CVD still tracked under P30.9b)

### Phase 3 — P30.9c VAH/VAL stepped (optional, same PR or follow-up)

- Extend `SierraLevelsOverlay.tsx` using `renderSteppedVAH` / `renderSteppedVAL` logic from `ChartV5a.tsx` (lines 87–115).
- Only after POC steps verified in RTH.

### Phase 4 — Bridge TPO adapt (only if Michael says yes)

- Update `tpo_stream.py` docstring + payload mapper for new `tpo.json` shape.
- Update `post_tpo()` to upsert session levels — **do not** break old bridge payloads if still in flight.

---

## §5 — Acceptance criteria

### P30.9b GREEN when:
- [ ] GET endpoint live with `source=sierra_cumulative_delta_json`
- [ ] ChartV5b shows CVD pane below price (not volume-proxy)
- [ ] Four-axis UAT recorded in new `docs/reports/PROMPT30_9b_CVD_PANE.md`
- [ ] `pytest tests/v9/api/test_cumulative_delta_routes.py -q` passes
- [ ] `P30_ROADMAP.md` row P30.9b → GREEN

### P30.9 full GREEN when:
- [ ] A1 RTH visual signed off
- [ ] P30.9b GREEN (CVD was part of screenshot contract #1)
- [ ] Optional: A3 VAH/VAL stepped

---

## §6 — Files to create/update

| Action | Path |
|--------|------|
| CREATE | `backend/v9/api/v9/cumulative_delta_routes.py` |
| CREATE | `tests/v9/api/test_cumulative_delta_routes.py` |
| CREATE | `frontend/v9/src/v9/components/chart/v5b/CumulativeDeltaPane.tsx` |
| CREATE | `docs/reports/PROMPT30_9b_CVD_PANE.md` |
| MODIFY | `ChartV5b.tsx`, FastAPI router registration |
| UPDATE | `P30_ROADMAP.md`, `PROMPT30_9_SIERRA_SCREEN_PARITY.md` |

---

## §7 — Deliverables for Michael

Reply with:
1. Table: gap ID → DONE / DEFER / BLOCKED
2. New endpoint path + sample JSON
3. Screenshot or note: CVD pane visible Y/N
4. Updated roadmap snippet
5. **Single next thread** after P30.9b (P30.10 Woodies vs P30.9c VAH/VAL)

---

## §8 — Do NOT do in this prompt

- Start full 12-stream bridge
- Enable LIVE trading
- Use `5min.json` poc_vol/vah/val for TPO overlay
- Claim GREEN without four-axis evidence per endpoint
- Regenerate Sierra monolith from modular sources

---

*End mega prompt — paste §1–§7 into Claude Code.*
