# P30.10 — Woodies 5m CCI Panel

**Date:** 2026-05-19 (evening UAT pass)  
**Status:** **GREEN** — live HUD + Sierra label parity + building-bar merge  
**Architecture:** [`docs/architecture/Woody_CCI_System_Architecture.docx`](../architecture/Woody_CCI_System_Architecture.docx) (auto-FIRE pipeline; no manual Fire on panel)

---

## Summary

Sierra-faithful **Woodies CCI Trend** floating panel on Cockpit **5m** (S4). Data: Sierra `woodies_5min.json` → `GET /api/v9/woodies/chart` → `WoodiesCciPanel.tsx` (2s poll).

**Critical fix (2026-05-19):** When `current_bar` shares `ts_unix` with history tail (building 5m bar), API + frontend now **replace** the tail with live `current_bar` so price, CCI, histogram, and all 10 HUD rows tick in LIVE mode.

---

## Delivered

| Layer | Item |
|-------|------|
| API | `GET /api/v9/woodies/chart?limit=1..120` — merge building bar; `study_caption` |
| DLL / export | `ccidiff_h/l`, `predictor_cci_high/low`, `prev_ohlc`, `low_prev_angle` |
| Frontend | HUD Sierra strings; historical freeze + live HUD; WOODY tab; ZLR border |
| Tests | 29 pytest (API + `buildDataTexts` + merge + frozen chart) |
| UAT script | `scripts/uat_woodies_live_tick.sh` |

---

## Sierra vs MEMS26 — data column (live reference)

| Row | Sierra label (example) | JSON fields | MEMS26 `buildDataTexts` |
|-----|------------------------|-------------|-------------------------|
| 1 | `47.01 CCIDiff H` | `ccidiff_h` | `formatCciDiffRow(..., 'H')` |
| 2 | `47.01 CCIDiff` | `cci_14 − cci_6_tcci` | white mid row |
| 3 | `47.01 CCIDiff L` | `ccidiff_l` | `formatCciDiffRow(..., 'L')` |
| 4 | `7380.00 7385.75 Hig` | `prev_high`, `high` | `hi` |
| 5 | **`7383.50 Last`** | `close` | `last` (22px black @ CCI 0) |
| 6 | `7372.50 7379.75 Low` | `prev_low`, `low` | `lo` |
| 7 | `7680.00 ProjHigh` | `proj_hi` (enrich if DLL omits) | `phi` |
| 8 | `7085.50 ProjLow` | `proj_lo` | `plo` |
| 9 | `162.3 162.3 CCI Pre` | `predictor_cci_high/low` | `cci` |
| 10 | `69.7° Low Prev/Cur` | `low_prev_angle` (DLL) | `angle` |

**Designer:** further pixel tweaks (fonts, exact Y) → `docs/design/WOODY_PANEL_DESIGNER_SPEC_v1.md` §5.12.

---

## UAT — four axes (`/api/v9/woodies/chart?limit=50`)

| Axis | Result | Evidence |
|------|--------|----------|
| **Quality** | PASS | `bad_count=0` (no bar without `cci_14`) |
| **Recency** | PASS | `bars[-1].ts_unix == latest_ts_unix` |
| **Cardinality** | PASS | `len(bars)==50` for `limit=50` |
| **Latency** | PASS | ~30ms local read |

---

## UAT — live building-bar tick

```bash
# After backend restart (see below)
bash scripts/uat_woodies_live_tick.sh 5 4
```

**Expect:** `tail_eq_cur_close: true`; between polls either CCI/close changes (same ts) or new bar ts.

**2026-05-19 run:** backend restarted (`uptime` &lt; 5s); `study_caption` = `(6, 5, 14, 100, HLC Avg) · 5m`.

---

## UAT — Cockpit visual

1. Open Cockpit → **5m** → **WOODY** tab.  
2. **LIVE** (no “HISTORICAL” banner): Last row shows `XXXX.XX Last` updating ~every 2s.  
3. Scroll back → chart frozen, HUD still live; **back to NOW** restores chart tick.  
4. Compare side-by-side with Sierra screenshot (Michael).

---

## Backend restart (required after route changes)

```bash
# Free port 8000, then:
cd /Users/michael/Downloads/mems26_web_git
[ -f .env ] && set -a && source .env && set +a
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 >> /tmp/backend.log 2>&1 &
```

Verify: `curl -s http://127.0.0.1:8000/api/v9/woodies/chart?limit=2 | jq .study_caption,.current_bar.close`

---

## Tests

```bash
pytest tests/v9/api/test_woodies_chart_routes.py tests/v9/frontend/test_woodies_build_data_texts.py -q
# 29 passed
```

---

## Deferred

| Item | Notes |
|------|--------|
| `proj_hi`/`proj_lo` from Sierra subgraphs | API enrich `max(high)±2` until DLL exports on `current_bar` |
| Time strip 1:1 scroll vs bar-count zoom | Michael chose bar-count zoom on time drag |
| Loading skeleton §6.1 | P3 |
| Auto-FIRE / pre-fire | `Woody_CCI_System_Architecture.docx` — not P30.10 UI |
| Pixel diff vs `v14_data_right_aligned.html` | When mockup in repo |

---

## Files touched (2026-05-19)

- `backend/v9/api/v9/woodies_chart_routes.py` — tail merge, `study_caption`
- `frontend/.../woodiesDesignerSpec.ts` — Sierra HUD strings, Last 22px
- `frontend/.../WoodiesCciPanel.tsx` — client merge `current_bar`, parse fix
- `scripts/uat_woodies_live_tick.sh`
- `docs/architecture/Woody_CCI_System_Architecture.docx`
- `docs/architecture/README.md`

---

## Bridge (cockpit-minimal)

```bash
cd bridge && CLOUD_URL=http://localhost:8000 V9_SKIP_HISTORY=1 V9_DISABLE_WATCHDOG=1 \
  python3 json_bridge.py --cockpit-minimal
```

Export path: `/Users/michael/SierraChart_Data/v9_export/woodies_5min.json` (`V9_WOODIES_5MIN_MAX_AGE_S=30`).
