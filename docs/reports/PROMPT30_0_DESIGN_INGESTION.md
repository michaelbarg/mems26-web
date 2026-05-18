# P30.0 — Design Spec Ingestion + Implementation Map

**Date:** 2026-05-18
**Status:** READY FOR MICHAEL DECISIONS — spec ingested, existing UI audited, no implementation started
**No SHADOW/DEMO/LIVE enabled. No code changes. No frontend dev server started.**

---

## 1. Authority Conflict Resolution

The designer spec (v1.1) raised 2 system classification conflicts. Both are now resolved:

| Conflict | Designer Spec says | Resolved by | Answer |
|----------|-------------------|-------------|--------|
| §7.1 S3 Firing vs Observer | "S3 FIRING per Designer Brief, OBSERVER per V3 spec" | P29 gateway fix + Master Index V2 | **S3 is FIRING.** `FIRING_SYSTEMS = {2,3,4}` committed. |
| §7.1 S1 Firing vs Observer | "Similar conflict for Day Type" | Master Index V2 + P29 gateway fix | **S1 is OBSERVING.** S1 rejected from gateway in test. |

Additional authority alignment:
- **D-074:** S4 Woodies uses `woodies_5min` timeframe — no change needed.
- **D-061:** Killzone zones are context/tag only — existing `system_colors.ts` already has S6 as OBSERVING.
- **Frontend `system_colors.ts`:** Already correct: `FIRING_SYSTEMS = [2,3,4]`, `OBSERVING_SYSTEMS = [1,5,6]`.

---

## 2. Component Implementation Map

### 2.1 Existing Components — Disposition

| Existing Component | Spec Section | Disposition | Notes |
|---|---|---|---|
| `V9Dashboard.tsx` (113 lines) | §4.1 Layout | **ADAPT** | Spec adds Left Zone (Woody+BigTrades) — current layout has no left zone. Needs 3-column layout (left/center/right) instead of current 2-column (center/right). |
| `TopBar.tsx` (261 lines) | §5.5 Mode Badge + S6 display | **ADAPT** | Mode badge exists but is simpler than spec. Spec adds: pulse ring for LIVE and topbar tint `#1A0808`. **Do not wire Pause LIVE** in P30 because it is a mode-changing action. Killzone currently reads like OPEN/CLOSED; per D-061 it must be shown as context/tag unless a calendar/risk/mode blocker is active. |
| `SidePanel.tsx` (117 lines) | §4.1 Right Zone | **KEEP** | Width 248px vs spec's 280px — minor CSS. ActiveTradeCard + Switcher + Lens structure matches spec. |
| `Switcher.tsx` (45 lines) | §4.1 Right Zone | **KEEP** | Already splits Firing [2,3,4] / Observing [1,5,6]. Matches spec. |
| `ActiveTradeCard.tsx` (173 lines) | §5.1 Active Trade Card | **ADAPT** | Current: basic direction/price/contracts/PnL/buttons. Spec adds: system circle + pattern icon, TRIGGER row, PLANNED R:R section, chip styling (ST/EN/T1/T2/T3), state variants. |
| `ChartV5b.tsx` (311 lines) | §4.1 Main Chart | **ADAPT** | Needs: toggle tabs on left edge (§5.6), Big Trades toggle on bottom edge (§5.7). Chart itself is solid. |
| `SystemPanelsBar.tsx` (28 lines) | Not in spec | **DEFER** | Spec replaces this with toggle-tab overlays on chart. Don't remove yet — defer decision. |
| `tokens.ts` (93 lines) | §3.1 Color Tokens | **ADAPT** | Missing: `--bg-woody`, `--bg-toolbar-dim`, `--border-faint`, mode-specific vars, Woody-specific colors. Add tokens, don't replace. |
| `system_colors.ts` (33 lines) | §3.1 System Colors | **ADAPT** | System roles are correct (`FIRING=[2,3,4]`, `OBSERVING=[1,5,6]`). Color values are close but not exact: S4 uses `#f97316` while designer spec calls for Sierra orange `#fb950b`. |
| `api.ts` (83 lines) | Data sources | **ADAPT** | Some existing components fetch directly instead of through this layer (`/api/v9/status`, `/api/v9/woodies/current`, `/api/v9/shadow/today_wr`). P30 should not assume this API layer already covers every needed source. |

### 2.2 New Components from Spec

| Spec Component | Section | Status | Data Source | Can Build Without SHADOW? |
|---|---|---|---|---|
| **Woody CCI Panel** | §5.3 | NEEDS_DATA_VERIFY | `/api/v9/woodies/current` + `/api/v9/chart/woodies` or equivalent bars | Possibly — read-only only, but must first prove the endpoint payload contains enough CCI history, ZLR markers, projected values, and 30-bar series data for Sierra 1:1 rendering |
| **Big Trades Panel** | §5.4 | NEEDS_DATA_SOURCE | No confirmed existing endpoint | No — needs endpoint/stream design before implementation |
| **Mode Badge (3 states)** | §5.5 | READY | `/api/v9/status` → mode field | Yes — read-only, already polled |
| **Toggle Tabs** | §5.6 | NEEDS_DECISION | N/A (UI-only) | Yes — pure layout |
| **Big Trades Toggle** | §5.7 | DEFER | Depends on Big Trades Panel | No |
| **Plan Tab Redesign** | §5.8 | READY | System `/current` endpoints | Yes — read-only GETs |
| **Pattern Icon Library** | §5.2 | READY | Static SVG paths | Yes — no API needed |
| **S3 Footprint Panel** | §5.9 | DEFER (PREP) | `/api/v9/footprint/current` | Yes but spec says "not for immediate implementation" |
| **S5 TPO Panel** | §5.10 | DEFER (PREP) | `/api/v9/tpo/current` | Yes but spec says "not for immediate implementation" |
| **Trade Detail Drawer** | §5.11 | DEFER | P29.5 schemas (now defined) | Partially — schemas exist but no runtime wiring |
| **Recent Trades Strip** | §5.12 | DEFER | P29.5 schemas | Same as above |
| **SHADOW Panel** | §5.13 | DEFER | P29.5 schemas + runtime | No — requires SHADOW soak data |

### 2.3 Stores — Changes Needed

| Store | Change | Notes |
|-------|--------|-------|
| `layoutStore.ts` | **ADAPT** | Add: `leftZoneWidth`, `leftZoneCollapsed`, `woodiesPanelOpen`, `bigTradesPanelOpen`, overlay states |
| `systemStore.ts` | **KEEP** | Already handles signals/markers/configs per system |
| `marketStore.ts` | **ADAPT/VERIFY** | Has Woodies bars and TPO level fields, but P30 must verify the fields are populated by current data hooks before relying on them for UI. |
| `tradeStore.ts` | **ADAPT/VERIFY** | Stores trade lists/account state, but `ActiveTradeCard` currently polls `/api/v9/trades/active` directly. Do not assume active-trade state is centralized. |
| `priceStore.ts` | **KEEP/VERIFY** | Existing price store/hooks support live price display; verify before using it for chart-side chips. |

---

## 3. Decisions Needed from Michael

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| 1 | **Toggle behavior: radio vs stacked?** (§5.6, §7.2) | A: One overlay at a time B: Multiple simultaneously | Layout complexity, z-index management |
| 2 | **Plan tab for observers S1/S5/S6** (§5.8, §7.2) | A: Same 4-section (STATE/BUILDING/TO_FIRE/DATA_HEALTH) adapted for "context readiness" B: Different structure (no BUILDING/TO_FIRE since they don't fire) | Affects 3 lens tab implementations |
| 3 | **Active Trade Card missing states** (§7.3) | IDLE, EXIT, SHORT, BLOCKED, DEGRADED — need visual design for each | Blocks full ActiveTradeCard implementation |
| 4 | **Implementation start point** | A: Mode Badge (smallest, highest safety value) B: Active Trade Card enhancements C: Woody CCI panel D: Layout shell (3-column) | Determines P30.1 scope |
| 5 | **Big Trades Panel data source** | Needs a new endpoint or bridge stream — does not exist today | Blocks Big Trades Panel entirely |
| 6 | **Left Zone vs overlay-only** | Spec shows Left Zone as persistent column. Alternative: overlays only (no left column until content exists) | Layout decision affects V9Dashboard rewrite scope |

---

## 4. Recommended Implementation Order

Based on safety (no SHADOW activation needed), data readiness (existing endpoints), and risk:

| Priority | Component | Why first |
|----------|-----------|-----------|
| **P30.1** | Mode Badge (3 states) | Smallest scope. Highest safety value — LIVE mode visibility is critical. Existing TopBar, existing `/api/v9/status` endpoint. No new data needed. |
| **P30.2** | Design tokens update | Add missing Woody/mode tokens to `tokens.ts`. Foundation for all subsequent work. |
| **P30.3** | Pattern Icon Library | Static SVG constants file. No API dependency. Unblocks ActiveTradeCard pattern display. |
| **P30.4** | Plan Tab Redesign | Uses existing system `/current` endpoints. 4-section structure for firing systems. Improves supervisability before SHADOW. |
| **P30.5** | ActiveTradeCard enhancements | After Michael decides missing states. Uses existing `/api/v9/trades/active`. |
| **P30.6** | Woody CCI data verification | Before building the panel, prove current endpoints expose the exact fields needed for Sierra 1:1 rendering (CCI history, TCCI, trend bars, ZLR markers, projected hi/lo, timestamps). |
| **DEFER** | Toggle tabs, Left Zone, Big Trades implementation, S3/S5 panels, Trade Detail Drawer, Recent Trades Strip, SHADOW Panel | Blocked by decisions, missing data sources, runtime wiring, or SHADOW activation |

---

## 5. Safety Notes

- **No POST/mode-changing routes** are wired in P30. All components read from GET endpoints.
- **ActiveTradeCard Exit/Move Stop buttons** already exist — P30.0 does NOT expand command-writing UI.
- **Pause LIVE button** (§5.5) is a mode-changing action — DEFER to Phase 9+ kill-switch / LIVE pre-flight work, not P30 display work.
- **Mode Badge** is read-only display — safe to implement now.
- **Do not run `npm run dev` / `next dev`** unless Michael explicitly authorizes browser/UI verification.
- **P30.0 did not prove visual correctness.** It only maps design against existing code and data readiness.

---

## 6. P29.5 Schema → Spec Mapping

The P29.5 data collection schemas (committed) directly unblock several spec components:

| Spec Component | P29.5 Schema | Status |
|---|---|---|
| Trade Detail Drawer (§5.11) | `SystemStateSnapshot`, `ReasonTree`, `PreFireDecision` | Schemas READY, runtime wiring DEFERRED |
| Recent Trades Strip (§5.12) | `LifecycleEvent`, `GatewayDecision` | Schemas READY, runtime wiring DEFERRED |
| SHADOW Panel (§5.13) | All 6 schema categories | Schemas READY, requires SHADOW soak data |
| Active Trade Card (§5.1) cross-system view | `SystemStateSnapshot` | Schemas READY, existing `cross_context` JSON column |

---

## Files Changed

| File | Type | Notes |
|------|------|-------|
| `docs/design/MEMS26_COCKPIT_V5_DESIGN_SPEC.md` | New | Designer spec copied into repo |
| `docs/reports/PROMPT30_0_DESIGN_INGESTION.md` | New | This report |

No code changes. No tests needed.

## 7. P30.0 Result

P30.0 is a documentation/audit gate, not an implementation gate.

Before P30.1 code work, Michael must decide:

1. Whether P30.1 starts with the read-only Mode Badge visual hardening.
2. Whether Killzone UI should be relabeled from OPEN/CLOSED to context/tag language.
3. Whether overlay behavior is radio or stacked.
4. Whether observer Plan tabs use the same 4-section structure or an observer-specific variant.
5. Whether to run a separate Woody endpoint payload audit before attempting Sierra 1:1 panel rendering.
