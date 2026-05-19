# P30.9c — Chart Sierra Alignment (CC Mega Prompt)

**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Cursor fix landed in repo (verify + UAT + gaps below)**

---

## §1 Mission

Finish **Sierra 5m chart parity**: CVD on chart time axis (not separate pane), TPO today + yesterday visible, stepped POC, cyan IB when Sierra exports it.

---

## §2 What Cursor just changed (verify in diff)

| Area | Change |
|------|--------|
| **CVD** | Volume pane → `cvd` scale on same lightweight-charts instance; `mapCvdToBarTimes()` aligns tail of Sierra points to tail of loaded bars |
| **TPO overlay** | `z-index: 10`; session `poc/vah/val` (magenta); `previous_day` API for yesterday POC/VAH/VAL (silver dashed); prior-day high/low (white); IB only if `ib_locked` and price > 0 |
| **Backend** | `ib_*` null when `ib.found=false`; `periods[]` filtered to last 48h in DB |
| **Removed** | Separate `CumulativeDeltaPane` below chart (was not time-aligned) |

**Files:** `ChartV5b.tsx`, `SierraLevelsOverlay.tsx`, `cvdMapping.ts`, `tpo_routes.py`

---

## §3 Known gaps (CC / Sierra / Michael)

| ID | Gap | Owner | Action |
|----|-----|-------|--------|
| G1 | **IB lines missing** | Sierra DLL | `tpo.json` shows `ib.found: false` until IB window — verify after 10:30 ET RTH; if still false during RTH, fix ACSIL IB export |
| G2 | **CVD index `i`** | Sierra + mapping | Points use Sierra bar index `i`, not DB ts — tail-align is interim; ideal: export `ts` per CVD point in DLL |
| G3 | **Stepped POC** | DB `v9_tpo_sessions` | Needs clean 30m rows with valid `closed_ts`; consider Sierra `periods[]` in `tpo.json` |
| G4 | **DISCONNECTED** top bar | WebSocket | `usePriceStream` / Redis — separate from chart; do not confuse with TPO |
| G5 | **RTH visual UAT** | CC | Browser checklist §6 in `PROMPT30_AUTONOMOUS_PARITY_CC_MEGA_PROMPT.md`; screenshot only on FAIL |

---

## §4 Mandatory UAT

```bash
# Backend restarted after pull
curl -s http://127.0.0.1:8000/api/v9/tpo/current | python3 -m json.tool | head -35
curl -s http://127.0.0.1:8000/api/v9/tpo/previous_day | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v9/cumulative_delta/current | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('points',[])),d.get('source'))"
```

**Browser:** `http://127.0.0.1:3000` → hard refresh `Cmd+Shift+R`

Checklist:
- [ ] CVD bars **inside** chart bottom (no second pane below drag handle)
- [ ] CVD scrolls/pans with candles
- [ ] Magenta POC stepped segments visible
- [ ] Magenta dashed today VAH/VAL
- [ ] Silver dashed yesterday POC/VAH/VAL (`/tpo/previous_day`)
- [ ] White prior-day high/low
- [ ] Cyan IB only when `ib.found=true` in `tpo.json`

```bash
pytest tests/v9/api/test_tpo_routes_sierra_contract.py \
       tests/v9/api/test_cumulative_delta_routes.py -q
```

---

## §5 If IB still missing during RTH

Investigate `v9_tpo_to_json()` in `MES_AI_DataExport_merged.cpp` — IB block must set `found: true` and real prices after IB formation. Do **not** fake IB in backend.

---

## §6 Deliverables

1. Update `PROMPT30_9_SIERRA_SCREEN_PARITY.md` — P30.9c section + UAT evidence
2. Update `P30_ROADMAP.md` — P30.9b superseded by in-chart CVD; P30.9c status
3. Report: G1–G5 table with DONE/BLOCKED
4. Optional: add `ts` to `cumulative_delta.json` export (Sierra)

---

## §7 Safety

- Bridge local-only; bars-only unless Michael approves
- No LIVE / trade_command
- No monolith regen from modular sources

*End mega prompt.*
