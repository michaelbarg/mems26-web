# P30 Session Summary — 2026-05-20

## Commits

| Hash | Description |
|------|-------------|
| `ac59a6e` | Woodies 10s deadlock, TPO 6-line rendering, DLL G1-G4 |
| `5d46872` | DLL v9.4.2: Sierra native study reads for Woodies + TPO |

---

## What Was Fixed

### 1. Woodies 10s Self-Deadlock (CRITICAL)
- **File:** `backend/v9/systems/woodies/woodies_system.py`
- **Problem:** `process_bar` called 5 sync HTTP requests to localhost:8000 (touchpoints), blocking the event loop for 10-12s per bar
- **Fix:** `touchpoints={}` — skip HTTP, touchpoints are advisory-only
- **Status:** DONE. No more SLOW handler entries in logs.

### 2. TPO 6-Line Rendering
- **Files:** `tpoLevels.ts`, `SierraLevelsOverlay.tsx`, `ChartV5b.tsx`
- **Problems fixed:**
  - Case mismatch (`VAH` vs `vah`) — 0 lines rendered
  - Duplicate lines (price lines + SVG lines)
  - Lines moving on zoom (SVG not locked to price)
  - Badge colors (pink fill today, white fill yesterday, black text)
  - Yesterday lines infinite — now bounded from 18:00 ET (Globex open)
  - Today lines outside RTH — now only 09:30-16:00 ET
- **Status:** DONE. 3 white + 3 pink lines, correct prices from DLL.

### 3. TPO Continuity Overlay
- **File:** `TpoContinuityOverlay.tsx` (NEW)
- **Stepped paths** (LineType.WithSteps) for today's developing TPO
- Yesterday: straight horizontal lines only (static history)
- **Status:** DONE. Renders from periods data.

### 4. Hydration Fix
- **File:** `ChartV5b.tsx`
- **Problem:** `woodiesOpen` read localStorage during SSR
- **Fix:** Default `false`, read in `useEffect` after mount
- **Status:** DONE.

### 5. WoodiesPanelTab CSS
- **File:** `WoodiesPanelTab.tsx`
- **Problem:** `border` + `borderLeft` shorthand conflict
- **Fix:** Explicit `borderTop/Right/Bottom`
- **Status:** DONE.

### 6. DLL v9.4.2-p30.11 — Sierra Native Study Reads
- **Files:** `MES_AI_DataExport.cpp`, `v9_woodies_export.h`, `v9_types.h`
- **New inputs:** `TPOChartNumber`, `WoodiesChartNumber`, `ProjHLStudyID`
- **Sierra study mapping (verified via diagnostic scan):**

| Value | Study ID | Subgraph | Verified |
|-------|----------|----------|----------|
| CCI-14 | 4 | SG0 | YES |
| CCI-6 (TCCI) | 10 | SG0 | YES |
| EMA-34 | 3 | SG0 | YES |
| LSMA | 2 | SG0 | YES |
| Sidewinder | 6 | **SG5** | YES (SG0=ref line) |
| ChopZone | 7 | **SG2** | YES (SG0=ref line) |
| ProjHigh | 9 (Panel) | **SG1** | YES (not Pivot Points!) |
| ProjLow | 9 (Panel) | **SG2** | YES |
| CCIDiff | computed | CCI14-CCI6 | YES |

- **TPO validation:** G2 rejects prices outside 3000-10000 (was -76624)
- **TPO session:** G4 adds `va_ok` + `session_date`
- **Status:** DONE. All values match Sierra display.

---

## Build Protocol (saved to memory)

1. Edit modular files in `sc_study/`
2. Run `bash scripts/build_monolithic_cpp.sh --deploy`
3. Copy to `~/SierraChart2/ACS_Source/` (second install)
4. Sierra UI: Remote Build
5. Sierra uses **Windows** compiler: `localtime_s` not `localtime_r`
6. Headers must be inlined (monolith) — Remote Build only uploads `.cpp`

---

## Sierra Study Configuration

| Input | Value | Purpose |
|-------|-------|---------|
| TPO Yesterday Study ID | 1 | TPO VA Lines, ref=1 |
| TPO Today Study ID | 3 | TPO VA Lines, ref=0 |
| IB Study ID | 6 | Initial Balance |
| Projected H/L Study ID | 0 | Disabled (use Panel SG1/SG2) |
| TPO Chart Number | (set in Sierra) | Chart with TPO studies |
| Woodies Chart Number | 12 | Chart with Woodies studies |

---

## What's Next

1. **Chrome verification** — refresh and confirm all TPO lines + badges
2. **CCIDiff H/L accuracy** — currently H=M=L from Sierra (single bar close). If separate H/L needed, requires reading CCI at H/L anchors from Sierra
3. **CCI Predictor** — Sierra study SGs don't expose predicted values. Computed from Sierra CCI-14 prev bar.
4. **Remove diagnostic code** — `woodies_diag.json` export can be removed after verification complete
5. **Push to remote** — when ready for deployment
