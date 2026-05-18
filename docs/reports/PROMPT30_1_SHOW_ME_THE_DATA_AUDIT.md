# P30.1 — Show Me The Data Audit

**Date:** 2026-05-18  
**Status:** STATIC AUDIT COMPLETE — visual proof still pending  
**No SHADOW/DEMO/LIVE enabled. No services started. No frontend dev server started. No trade command writes.**

---

## Summary

P30.1 answers Michael's question: "When will I see all data and historical bars on screen?"

Current answer:

- The frontend already has a real cockpit base.
- `ChartV5b` already requests 240 historical bars, live price updates, TPO lines, volume overlay, timeframe switching, and scroll-back loading.
- S1-S6 state polling exists through `systemStateStore`.
- The UI has a right-side cockpit (`SidePanel`) with `ActiveTradeCard`, `Switcher`, and Lens tabs.
- This has **not yet been visually proven** in a running browser during this prompt.

The next safe step is browser/UI verification with explicit Michael approval to use the existing running frontend/backend or start them if absent.

---

## Existing Screen Data Paths

| Area | Existing frontend file | Data source | Static status | Visual proof |
|---|---|---|---|---|
| Main 5m chart history | `ChartV5b.tsx` | `/api/v9/chart/bars5min?limit=240` | EXISTS | PENDING |
| Historical scroll-back | `ChartV5b.tsx` | `/api/v9/chart/<tf>?limit=240&before=...` | EXISTS up to 2000 cap | PENDING |
| Volume overlay | `ChartV5b.tsx` | chart bar `volume` | EXISTS | PENDING |
| Live forming bar | `ChartV5b.tsx` | `/api/v9/live_price` | EXISTS | PENDING |
| TPO lines | `ChartV5b.tsx` | `/api/v9/tpo/current` | EXISTS | PENDING |
| Killzone chart label | `ChartV5b.tsx` | `/api/v9/killzone/current` | EXISTS, label only | PENDING |
| Mode / health / day type | `TopBar.tsx` | `/api/v9/status`, `/api/v9/day_type/v9/current` | EXISTS | PENDING |
| S1-S6 state polling | `systemStateStore.ts` | `/api/v9/<system>/current` | EXISTS | PENDING |
| Active trade card | `ActiveTradeCard.tsx` | `/api/v9/trades/active` | EXISTS, contains POST buttons | PENDING |
| Trade history strip | `TradeHistoryStrip.tsx` | `/api/v9/trades/recent` | EXISTS in UI, endpoint needs verification | PENDING |
| Shadow soak strip | `ShadowSoakStrip.tsx` | `/api/v9/status`, `/api/v9/shadow/soak_progress` | EXISTS in UI, endpoint shape needs verification | PENDING |

---

## S1-S6 Visibility Audit

| System | Role | Current UI/data path | Static status | Gap before "shown working" |
|---|---|---|---|---|
| S1 Day Type | Observer | `TopBar`, `DayTypeLensContent`, `systemStateStore` | EXISTS | Need visual proof of current state, freshness, degraded handling |
| S2 Five-Min | Firing | `FiveMinLensContent`, `systemStateStore` | EXISTS | Need visual proof of setup/fire/block state and stale/degraded display |
| S3 Footprint | Firing | `FootprintLensContent`, `systemStateStore` | EXISTS | Need visual proof that S3 state shows as firing system, not observer |
| S4 Woodies | Firing | `WoodiesLensContent`, `systemStateStore` | EXISTS | Needs endpoint payload audit before Sierra 1:1 panel |
| S5 TPO | Observer | `TPOLensContent`, TPO chart lines, `systemStateStore` | EXISTS | Need visual proof that POC/VAH/VAL/IB are accurate and fresh |
| S6 Killzone | Observer/context | `TopBar`, `KillzoneLensContent`, `systemStateStore` | EXISTS | UI must avoid implying zone label is a D-061 hard block |

---

## Chart History Requirements

Before Michael can trust the chart visually, browser verification must prove all four axes:

| Axis | Required proof |
|---|---|
| Quality | No invalid/outlier bars rendered; backend bad-bar filter remains defense-in-depth |
| Recency | Latest rendered finalized bar equals DB latest bar for the selected timeframe |
| Cardinality | Initial request renders requested count, normally 240 bars |
| Latency | Chart fetch and UI render stay within operational threshold |

Additional visual checks:

- Scroll left loads older bars without duplicates.
- Cap at 2000 bars is respected.
- Volume overlay aligns with candles.
- Live forming bar does not hide finalized DB truth.
- TPO levels are visible and not stale.
- Killzone label is contextual, not a false trade blocker.

---

## Data Contract Drift Found

| Item | Finding | Action |
|---|---|---|
| `api.ts` | Does not centralize all active UI endpoints; many components fetch directly | ADAPT later, do not block visual audit |
| `UI_DATA_CONTRACT.md` | Some endpoint names are older or inconsistent with current frontend (`shadow/soak_progress` vs documented `shadow/soak/progress`) | Update after endpoint verification |
| `ActiveTradeCard` | Existing Exit / Move Stop POST buttons are present | Do not expand command-writing UI in P30; consider disabling/hiding before DEMO/LIVE |
| Killzone UI | Current labels can read as OPEN/CLOSED gate | Relabel as context/tag unless true calendar/risk/mode block |
| Woodies panel | Designer wants Sierra 1:1 rendering, but current endpoint payload must be proven first | Run P30.2 Woody payload audit before building panel |

---

## Recommended Next Slice

### P30.2 — Browser Visual Data Proof

Only after Michael explicitly authorizes browser/frontend verification:

1. Check existing listeners on `127.0.0.1:3000` and `127.0.0.1:8000`.
2. If services are already running, do not start duplicates.
3. If services are not running, ask Michael before starting anything.
4. Open the cockpit in browser.
5. Capture proof for:
   - Chart renders 240 bars.
   - Scroll-back works.
   - Volume overlay works.
   - Latest rendered bar matches backend/DB.
   - S1-S6 states are visible and understandable.
   - Degraded/stale states are visible.
6. Produce screenshot-backed report:
   `docs/reports/PROMPT30_2_BROWSER_VISUAL_DATA_PROOF.md`

---

## Stop Conditions

Stop and ask Michael if:

- frontend/backend are not already running and service start is needed;
- any POST/mode-changing UI path becomes part of P30 work;
- any path might write `trade_command.json`;
- SHADOW/DEMO/LIVE activation appears necessary;
- visual proof contradicts backend reports;
- a component hides degraded/stale data.

---

## Result

P30.1 static audit is complete.

It proves the codebase has a real screen/data foundation, but it does **not** prove Michael can see the data correctly yet. That requires P30.2 browser visual verification.
