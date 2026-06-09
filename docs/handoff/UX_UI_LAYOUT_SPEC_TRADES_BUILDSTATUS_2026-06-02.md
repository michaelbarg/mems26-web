# UX/UI Layout Spec — Trades Page + Build Status Panel (2026-06-02)

**Scope:** placement-only design spec for CC. Read-only authored. No code changed.
**Companion prompts (logic + acceptance):**
`docs/handoff/CC_PROMPT_TRADES_UX_UPGRADE_2026-06-02.md`,
`docs/handoff/CC_PROMPT_BUILD_STATUS_MEGA_2026-06-02.md`.

This spec tells you **exactly where every element goes**. It does **not** change
the trading-logic or data contracts those prompts already define. Every element
cites the real field/component it maps to. **No invented data** — when a field is
`null`/missing, render `—`/`missing` (CLAUDE.md Rule 1).

> ⚠️ **Two distinct token systems exist in this app — do not mix them.**
> - **Trades page** (`components/trades/*`) uses **CSS variables** from
>   `frontend/v9/src/app/globals.css` + Tailwind utility classes.
> - **Build Status panel** (`components/build_status/*`) uses the **`COLORS`
>   object** from `frontend/v9/src/v9/design/tokens.ts` via inline `style={{}}`.
> Stay native: a new Trades element uses CSS vars; a new Build Status element
> uses `COLORS`. Never introduce a third palette or hard-coded hex.

---

## A. Design tokens to reuse

### A.1 Trades page tokens — CSS vars (`globals.css:3-19`)

| Token | Value | Semantic use on Trades |
|-------|-------|------------------------|
| `--bg-primary` | `#0d1117` | page bg, row-expand bg, input bg |
| `--bg-secondary` | `#161b22` | top bar, filter bar, summary strip, sticky `thead` |
| `--bg-tertiary` | `#21262d` | (available for hover/elevated chips) |
| `--border` | `#30363d` | all dividers, row borders, input borders |
| `--text-primary` | `#e6edf3` | primary cell text |
| `--text-secondary` | `#8b949e` | sub-labels, "When" cell |
| `--text-muted` | `#484f58` | captions, `—` empties, IDs, disabled |
| `--green` | `#56d364` | WIN, positive P&L, LONG, hit ✓ |
| `--red` | `#f85149` | LOSS, negative P&L, SHORT, error banner |
| `--sys1`..`--sys6` | see `globals.css:11-16` | per-system color (via `SYSTEM_COLORS`, `types/index.ts:205`) |

**Reuse, don't reinvent — existing Trades conventions:**
- **System token:** `SYSTEM_COLORS[id]` + `S{id} {SYSTEM_NAMES[id]}` (`TradesTable.tsx:100-103`).
- **TEST badge** (synthetic): amber inline chip, `rgba(234,179,8,0.2)` bg / `#d97706`
  fg / `rgba(234,179,8,0.3)` border, `fontSize:8`, `fontWeight:700`
  (`TradesTable.tsx:69-86`). **Reuse this exact chip for the Synthetic filter's
  "TEST only" state and any synthetic indicator.**
- **Amber warning accent** `#eab308` for `T1_NO_BE`, partial-P&L sub
  (`TradesTable.tsx:171,196`). Reuse for the truncation notice.
- **State→color map** (`TradesTable.tsx:188-191`): WIN→`--green`, LOSS→`--red`,
  OPEN/FILLED/PARTIAL→`#3b82f6` (blue), else `--text-secondary`.
- **Pattern pill** (active vs idle): `TradesTable.tsx:133-138` — active uses
  `rgba(59,130,246,0.18)` bg + `--sys1` fg + border; idle `rgba(255,255,255,0.06)`.
  **Reuse this pill shape for all clickable filter chips** (Direction, Synthetic, sort indicators).
- **Filter control:** `FilterSelect` (`TradeFilters.tsx:115-135`) — `10px` muted
  label + `text-xs` bordered `<select>`. **All new filters reuse `FilterSelect`.**
- **Modal frame:** `TradeDetailsModal.tsx:95-99` — `fixed inset-0` scrim
  `rgba(0,0,0,0.6)`, centered card `w-[640px] max-h-[92vh] overflow-y-auto
  rounded-lg`, `bg-secondary`, `border: 2px {SYSTEM_BORDER_STYLE[mode]} {systemColor}`.
- **Section header inside modal:** `text-[10px] uppercase tracking-wide` muted
  (`TradeDetailsModal.tsx:133`). **Reuse for every modal section title.**
- **`Mini` label/value pair** (`TradeDetailsModal.tsx:336-343`) for metric grids.

### A.2 Build Status tokens — `COLORS` (`design/tokens.ts:3-45`)

| Token | Value | Semantic use on Build Status |
|-------|-------|------------------------------|
| `bgBase` | `#0a0a0a` | tab bg |
| `bgSurface1/2/3` | `#0d0d0d`/`#0f0f0f`/`#101010` | system card / sticky thead / card header |
| `bgSurface5` | `#1a1a1a` | refresh button |
| `borderFaint`/`borderTertiary` | `#1a1a1a`/`#262626` | card borders, header rule |
| `textPrimary/Secondary/Tertiary` | `#e5e5e5`/`#a3a3a3`/`#737373` | text tiers |
| `bull` | `#16a34a` | **FRESH / READY / present ✓ / fired** |
| `warning` | `#f59e0b` | **STALE / DEGRADED / vetoed** |
| `caution` | `#facc15` | **armed** (also `modeShadow`) |
| `bear` | `#dc2626` | **DEAD / ERROR / BLOCKED / absent ✕** |
| `bearLight` | `#fca5a5` | error-banner text |

**Reuse, don't reinvent — existing Build Status conventions:**
- **`FreshnessPill`** (`ComponentTable.tsx:11-53`): `fresh <60s`→`bull`/`#0e3a1f`,
  `stale`→`bear`/`#3a1a1a`, `lag ?`→`warning`/`#3a280a`, with `title` tooltip
  `source=… · ts=…`. **This is the canonical freshness chip. Extract/export it and
  reuse for every `global_gate` row and every bridge field row.** Its thresholds
  (`STALE_LAG_S=60`) match the bridge_inspector FRESH<60s boundary.
- **`StatusPill`** (`StatusPill.tsx:10-17`): the existing 6-state map
  (fired/armed/blocked/vetoed/n-a/unknown) with bg+fg+icon. **Reuse its style
  vocabulary for the per-system READY/DEGRADED/BLOCKED badge** (A4) and the big
  readiness banner (map READY→`fired` greens, DEGRADED→`vetoed`/`armed` ambers,
  BLOCKED→`blocked` reds).
- **`StatusDot`** (`SystemSection.tsx:32-39`): `● label` ok/bad dot — reuse for
  run/hyd indicators (already present).
- **Live-input chip row** (`SystemSection.tsx:167-195`): `field=value` wrap-flex
  with `textTertiary` key / `textPrimary` value. **This is the established pattern
  for "field → value"; Bridge Field Inventory rows extend it with a freshness pill.**
- **`ComponentTable`** columns (`ComponentTable.tsx:88-96`):
  `Stage · Key · Spec · Live · Required · Present · Value`. **The global_gates
  table reuses this exact column grammar** (gate has the identical additive shape,
  `types.ts:59-68`).

---

## B. Trades page

### B.1 Full-page ASCII wireframe

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MEMS26   / Trades                                          (h-40 top bar)      │  ← TradesView:22-32 (KEEP)
├──────────────────────────────────────────────────────────────────────────────┤
│ FILTER BAR (bg-secondary, flex-wrap, px-4 py-2)                                │  ← TradeFilters (ADAPT)
│ Row 1:  Mode▾  System▾  Outcome▾  Direction▾  Synthetic▾                       │     primary cuts
│ Row 2:  From[date] To[date]  [Search pattern…]  Overlap▾ LIVE-elig▾ Confluence▾│     time + advanced
│ Row 3:  [✕ Clear all filters]            "3 filters active"                     │     reset + counter (NEW B3)
├──────────────────────────────────────────────────────────────────────────────┤
│ SUMMARY STRIP (bg-secondary, px-4 py-3)                                        │  ← TradesSummaryStrip (ADAPT)
│  Total P&L (filtered)      Wins Losses BE Open  WinRate  TotalR                │     +BE chip (A2)
│  +$1,234.00                 …                                                  │
│  384 trades · 356 closed · 12 partial   ░ Showing 384 of 900 (truncated) ░     │  ← truncation notice (NEW A4)
│  By system:  [S3 …]  [S4 …]                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ PatternPerformanceStrip (KEEP, unchanged)                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ TABLE  (flex-1 overflow-auto; inner div overflow-x-auto; min-w-[1280px])       │  ← TradesTable (ADAPT)
│ ┌──┬──┬─────────┬─────┬────┬──────────────┬───────────┬──────────┬───┬──────┬─────────┬──┐
│ │▶ │# │When↕    │Sys↕ │Dir │ Path (IN/ST/T/OUT) │Range/T1 │Sys S1-6 │C1-3│Pattern│P&L↕    │St↕│
│ ├──┼──┼─────────┼─────┼────┼──────────────┼───────────┼──────────┼───┼──────┼─────────┼──┤
│ │▶ │12│06-02 …  │S4   │SHORT│ IN…→ST…→T1…  │ Hi.. Lo.. │ S3* S4✓  │…  │ ZLR  │ +$120   │WIN│ ← click row → MODAL
│ └──┴──┴─────────┴─────┴────┴──────────────┴───────────┴──────────┴───┴──────┴─────────┴──┘
│  (loading → spinner row;  fetch error → red banner ABOVE table;  empty → muted)│
└──────────────────────────────────────────────────────────────────────────────┘
```

### B.2 Filter bar — layout, filters & order (`TradeFilters.tsx`)

Keep the existing `flex items-center gap-3 px-4 py-2 border-b flex-wrap` shell and
`FilterSelect`. Reorganize into **3 logical rows** using `<div className="basis-full">`
breaks (the file already uses one at line 77). Order left→right, top→bottom:

**Row 1 — primary categorical cuts (highest-frequency):**
1. **Mode** ▾ — `KEEP` (`TradeFilters.tsx:14-24`).
2. **System** ▾ — `ADAPT` (A3): derive options from loaded `trades` (systems with
   `count>0`), prefixed by "All Systems". Today's data → `All · S3 · S4` only.
   Keep `SYSTEM_NAMES`/`SYSTEM_COLORS` for the label.
3. **Outcome** ▾ — `ADAPT` (A2): options `All · Win · Loss · Breakeven · Scratch ·
   Open`. Insert **Breakeven** (value `BE`) between Loss and Scratch.
4. **Direction** ▾ — `NEW` (B1): `All · Long · Short`. Place immediately after
   Outcome (direction is a top-of-mind cut). Long label tinted `--green`, Short `--red`.
5. **Synthetic** ▾ — `NEW` (B2): `All · Real only · TEST only`. Place last on Row 1.
   When "TEST only" active, show the amber TEST chip (A.1) next to the select label.

**Row 2 — time + free-text + advanced (lower-frequency):**
6. From / To date inputs — `KEEP` (`TradeFilters.tsx:49-68`).
7. Pattern search box — `KEEP` (`TradeFilters.tsx:69-76`).
8. Overlap ▾ · LIVE-eligible ▾ · Confluence ▾ — `KEEP` (`TradeFilters.tsx:78-110`),
   the more analytical filters, grouped at the right of Row 2.

**Row 3 — controls (NEW B3):**
9. **[✕ Clear all filters]** button — left aligned. Reuse the idle pattern-pill
   style (`rgba(255,255,255,0.06)` bg). On click → reset store to `DEFAULT_FILTERS`
   (`tradeStore.ts:45-55`).
10. **"N filters active"** label — `text-[10px]` `--text-muted`, right of the
    button. N = count of filters differing from `DEFAULT_FILTERS`. Hide ("0 filters
    active" → render nothing) when none active.

### B.3 Summary strip (`TradesSummaryStrip.tsx`) — ADAPT

- **Add a "BE" StatChip** between **Scratch** and **Open** (line 92), color
  `--text-secondary`. Per A2, BE counts as scratch for win-rate but gets its own
  visible count. Source: `real.filter(t => t.outcome === 'BE')`.
- **Truncation notice (NEW A4):** place as a third line in the left block, directly
  under the existing `"384 trades · 356 closed"` line (`TradesSummaryStrip.tsx:84-87`).
  Render **only when `truncated === true`** (new store field from `fetchTrades`):
  `Showing {trades.length} of {total} — raise limit to see all`. Style:
  `text-[10px]`, color `#eab308` (amber), with a small left amber dot. When not
  truncated → render nothing (no layout shift baseline).

### B.4 Table (`TradesTable.tsx`) — column order + sortable columns

**Keep the existing 12-column order** (`TradesTable.tsx:27-41`) — it is already
information-dense and tested:

`▶ · # · When · Sys · Dir · Path · Range/T1 · Systems S1–S6 · C1-C3 · Pattern · P&L (realized) · St`

**Sortable columns (NEW C1)** — add a clickable affordance to **4 headers only**:
**When · Sys · P&L · St(Outcome)**. The rest stay static (Path/Systems/Pattern are
composite strings, not meaningfully sortable).
- Indicator: append `↕` (idle, `--text-muted`) / `↑`/`↓` (active, `--text-primary`)
  to the `<th>` label. Reuse the existing uppercase `10px` thead styling
  (`TradesTable.tsx:23-26`) — do not restyle the header.
- Click toggles asc→desc→(back to default entry_ts desc). Client-side sort over
  the **filtered** array; never re-fetch. Null P&L / null outcome sort to the
  bottom regardless of direction.
- Only one active sort column at a time; clicking a new column resets the others to `↕`.

**Path column density (C3):** keep `min-w-[1280px]` table inside the existing
`overflow-x-auto` wrapper (`TradesTable.tsx:20`) so horizontal scroll is contained,
not page-breaking. For the Path cell (`tradeRowFormat.ts:73-91`): keep the single
`IN→ST→T1→T2→T3→OUT` string but wrap it in a `max-w-[360px]` cell with the full
path as a `title` tooltip; segments may wrap to 2 lines rather than forcing the
table wider. **No data change** — render-only. Confirm no clipping at 1024px
viewport (contained scroll + sticky `thead` preserved).

### B.5 Row interaction — wire the rich modal (A1 — choose option (a))

**Decision: option (a). Make a row click open `TradeDetailsModal` (the rich, dead
component) and retire the thin `TradeRowExpand`.** Rationale: the timeline,
confidence, day_type, per-contract P&L, and excursion grid already exist and are
fully styled in `TradeDetailsModal.tsx`; rebuilding them into the inline expand
(option b) would duplicate ~150 lines and risk the two drifting (CLAUDE.md
"smallest correct change" + no dual implementations).

Wiring:
- Row `onClick` → `setSelectedTradeId(t.id)` (store already has it, `tradeStore.ts:88`)
  instead of `toggleExpandedTradeId` (`TradesTable.tsx:62`).
- Render `<TradeDetailsModal />` once in `TradesView` (after `<TradesTable />`,
  `TradesView.tsx:37`). Modal self-renders null when `selectedTradeId == null`
  (`TradeDetailsModal.tsx:86`).
- Remove the inline-expand branch (`TradesTable.tsx:205-211`) and the `▶/▼` caret
  semantics shift to "opens detail" (keep the caret column as a click affordance).
- Delete the now-unused `TradeRowExpand.tsx` so there is a single implementation.

**Modal section order (top→bottom)** — keep `TradeDetailsModal.tsx`'s existing
order; it is already correct for an operator reading a trade post-mortem:
1. **Header** — system dot + color, `Trade #id`, P&L (`:100-126`).
2. **What fired** — headline + Trigger/Pattern/Class/Confidence/Day type/Blocked
   grid (`:131-150`).
3. **Recognition at entry** — per-system agree/against cards (`:152-189`).
4. **Timeline / lifecycle** — ordered event list (`:191-209`).
5. **P&L per contract (C1/C2/C3)** — 3-col grid (`:211-238`).
6. **Price range (5m bars)** — Hi/Lo/MFE/MAE/T1 grid (`:240-274`).
7. **Execution** — path line + contract hits (`:276-288`).
8. **Trade Timeline** — `management_log`-driven ENTRY→STOP_MOVE/SMART_BE→
   T1/T2/T3_HIT→STOP_HIT→EXIT (`:290-329`). This is the 804-row DB timeline that
   is invisible today.

Keep the modal frame, scrim, system-colored border, and section-header styling
exactly as written (A.1). No restyle — just make it reachable.

### B.6 States — loading / error / empty (C2)

Add `loading` + `error` to the trade store. Placement and visual:
- **Loading (initial fetch):** spinner row spanning all columns inside `<tbody>`
  (replace the static empty row when `loading && trades.length === 0`), `--text-muted`
  text "Loading trades…". Do **not** show "No trades found" during load.
- **Fetch error:** a **red banner placed ABOVE the table**, inside `TradesView`
  between `PatternPerformanceStrip` and the table div (`TradesView.tsx:35-36`).
  Style mirrors the Build Status error banner concept but in Trades tokens:
  `--red` text, `border-color:--red`, `bg: rgba(248,81,73,0.08)`, message
  "Failed to load trades — is the backend on :8000? [Retry]". This is the
  CLAUDE.md "no silent failures" surface; it must be visually distinct from empty.
- **Empty-after-filter:** keep the existing muted "No trades found matching filters."
  row (`TradesTable.tsx:215-220`) — only shown when `!loading && !error && trades.length === 0`.

### B.7 Responsive / narrow rules

- Table: contained horizontal scroll (B.4); sticky `thead` retained
  (`TradesTable.tsx:24`).
- Filter bar already `flex-wrap`; the 3-row grouping (B.2) degrades gracefully —
  selects wrap within their logical row.
- Modal: `w-[640px]` is fixed; on viewports < 680px it should fall back to
  `w-[92vw]` (add a `max-w-[640px] w-[92vw]` so it never overflows). `max-h-[92vh]`
  + internal scroll already handle vertical (`TradeDetailsModal.tsx:97`).

---

## C. Build Status panel

### C.1 Full-panel ASCII wireframe

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Build Status · Live Debug            ☐ Show only blockers   last refresh …  ⟳  │ ← BuildStatusTab:22-93 (KEEP header)
├──────────────────────────────────────────────────────────────────────────────┤
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━ READINESS BANNER (NEW A2/C3) ━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ ● BLOCKED   reason: bridge stream cvd_continuous DEAD (RTH)               ┃ │ ← data.readiness (types.py:135-139)
│ ┃   ✕ bridge_streams_fresh  ✕ s4_trend_not_stuck_gray  ✓ s1_day_type … ⓘ RTH ┃ │   verdict color = bull/warning/bear
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│  ts: …   session: …   RTH: open · -123m            build: v1   (KEEP meta row)  │ ← BuildStatusTab:161-195
├──────────────────────────────────────────────────────────────────────────────┤
│ ▼ Bridge · Live Data Feed   ●run ●hyd  lag 3s  0 fires      [DEGRADED] LIVE    │ ← SystemSection header (ADAPT: per-sys badge A4)
│   ┌── GLOBAL GATES (NEW A1) — 8 stream freshness rows ──────────────────────┐  │
│   │ Stream            Live   Required  Present  Freshness                    │  │  ← reuse ComponentTable grammar
│   │ woodies_5min      3s     < 90s     ✓        ⬤ fresh 3s                    │  │     gate = GlobalGate (types.ts:59-68)
│   │ footprint         5s     < 90s     ✓        ⬤ fresh 5s                    │  │     FreshnessPill (ComponentTable:11)
│   │ cumulative_delta  410s   < 360s    ✕        ⬤ stale 6m                    │  │
│   │ …                                                                        │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│   ┌── BRIDGE FIELD INVENTORY (NEW Phase B) — collapsible ▶ ─────────────────┐  │
│   │ Field            Value     Freshness   Source        Consumer  Pattern   │  │
│   │ trend_state      GRAY 🚩    fresh 3s    woodies_5min  S4-A1     all 9     │  │
│   │ cci_14           102.3      fresh 3s    woodies_5min  S4/S2     ZLR,TLB…  │  │
│   │ POC              5012.50    fresh 8s    volume_profile S1/S5    SR        │  │
│   │ …  (≥20 rows; null → "missing")                                          │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│   (no patterns table for bridge — global_gates replace the empty table)          │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▼ Five-Min (S2)   ●run ●hyd  lag …  ✓2× fired       [READY] SHADOW             │ ← per-system READY badge (A4)
│   Live Inputs: opening_type=OPEN_DRIVE  day_type=…   Interpretation: …          │ ← KEEP (SystemSection:167-195)
│   ┌ Pattern │ Status │ Reason │ Fired ┐  (KEEP patterns table)                   │
│ ▼ Woodies (S4) …                                                                │
│ ▼ Day Type (S1) …                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### C.2 Readiness verdict banner (A2 + C3) — placement & color

- **Location:** in `BuildStatusTab.tsx`, **directly above the meta row** (insert
  before line 161, after the scrollable container opens) so it is the first thing
  the operator sees inside the data region. Full-width card, `borderRadius:6`,
  `marginBottom:12` (matches the meta row spacing).
- **Source:** `data.readiness` (`BuildStatusResponse.readiness`, backend
  `types.py:142-149`; add `readiness?: Readiness` to frontend `types.ts` per C3).
- **Verdict color (reuse `COLORS` + StatusPill vocabulary):**
  - `READY` → `bull` fg on `#0e3a1f` bg (same green as `StatusPill.fired`).
  - `DEGRADED` → `warning` fg on `#3a280a` bg (same as `vetoed`).
  - `BLOCKED` → `bear` fg on `#3a1a1a` bg (same as `blocked`).
- **Contents (in order):**
  1. Big verdict label + colored `●` (left).
  2. `reason` line (`readiness.reason`) — `textSecondary`, one line.
  3. A horizontal wrap of **failed checks** — each `readiness.checks` item with
     `passed=false` rendered as `✕ {key}` in the severity color (block→`bear`,
     degrade→`warning`); passed/info checks shown smaller as `✓ {key}` /
     `ⓘ {key}` in `textTertiary`. Tooltip = `check.detail`.
- **Backward-compat:** if `data.readiness` is absent/empty (`verdict` default
  `"BLOCKED"` but no checks), render a neutral "readiness: n/a" pill in
  `textTertiary` — do **not** crash or imply a real block.

### C.3 Bridge `global_gates` panel (A1 — the central bug fix)

- **Location:** inside `SystemSection`, **below the header, above the patterns
  table** (insert at `SystemSection.tsx:166`, before the live-inputs block). Render
  only when `system.global_gates.length > 0` (so non-bridge systems are unaffected —
  no regression).
- **Render as a table reusing the `ComponentTable` column grammar** (gate shares
  the additive shape, `types.ts:59-68`). Columns, left→right:
  `Stream(key) · Live · Required · Present · Freshness`. Map:
  - `key` → stream label (`bridge_inspector.py:138`).
  - `live` → e.g. `3s` / `no_data` (`bridge_inspector.py:142`).
  - `required` → `< 90s` (`:143`).
  - `present` → ✓ (`bull`) / ✕ (`bear`), same as `ComponentTable:115-120`.
  - **Freshness** → **`FreshnessPill`** (extract/export from
    `ComponentTable.tsx:11`), fed `gate.freshness` (`:144`). Its FRESH<60s/STALE
    coloring already aligns with the bridge_inspector `[FRESH]/[STALE]/[DEAD]`
    status embedded in `value`.
- **Color semantics per gate** (drive from `present` + freshness, matching
  `bridge_inspector` thresholds): FRESH→`bull`, STALE→`warning`, DEAD/ERROR→`bear`.
- The bridge section's patterns table is empty (`bridge_inspector.py:191
  patterns=[]`); with gates rendered above it, suppress the empty "No patterns
  reported." row for `id="bridge"` (or let global_gates stand in for it).

### C.4 Bridge Field Inventory (Phase B) — placement without clutter

- **Location:** a **collapsible sub-section inside the bridge `SystemSection`**,
  directly **below the global_gates table**. Default **collapsed** (`▶`), labeled
  `Bridge Field Inventory (N fields)`. This keeps the at-a-glance gate view clean
  while making the ≥20 per-field rows available on demand.
- **Render** as a table extending the live-input "field → value" grammar
  (`SystemSection.tsx:167-195`) plus a freshness pill. Columns:
  `Field · Value · Freshness · Source · Consumer · Pattern(s)` — exactly the
  inventory table in `CC_PROMPT_BUILD_STATUS_MEGA_2026-06-02.md` §B1.
- **Per-field color/state:** value `textPrimary`; `null`/missing → `missing` in
  `textTertiary` (Rule 1, no synthesis). Freshness via the shared `FreshnessPill`.
  **`trend_state` row gets a 🚩 + amber `warning` highlight when value is `GRAY`**,
  with interpretation text "trend_state=GRAY → A1 blocks all 9 Woodies patterns"
  (already half-present in `woodies_inspector.py`). This is the single most
  operationally important field — give it the only colored emphasis in the table.
- Source of each row's data is the backend Phase B work; this spec only fixes
  **where** it lives and **how** a field/missing/stale renders.

### C.5 Per-system card layout (KEEP + A4 badge)

Keep `SystemSection` header as-is (`SystemSection.tsx:115-164`): caret · name ·
`●run` · `●hyd` · freshness · fire-summary · counts · mode pill. **Add one element
(A4):** a per-system **READY/DEGRADED/BLOCKED badge** immediately left of the mode
pill (`SystemSection.tsx:152`), so the operator sees which system blocks without
expanding. Reuse `StatusPill` styling (greens/ambers/reds from C.2). Derive the
per-system verdict from that system's gates + its readiness checks (backend-provided
or rolled up frontend per the mega prompt). Body order unchanged:
1. (bridge only) global_gates table — C.3.
2. (bridge only) Bridge Field Inventory — C.4.
3. Live Inputs + Interpretation row — KEEP (`:167-195`).
4. Patterns table — KEEP (`:198-249`).

### C.6 States — loading / error / empty (KEEP)

`BuildStatusTab` already handles error (`:108-123`), no-data (`:125-137`), loading
(`:139-151`) with the correct tokens. **Do not change them.** New banner (C.2) and
gates (C.3) render only inside the `data &&` branch, so these states are unaffected.
Manual-refresh-only is preserved (`useBuildStatus.ts:15-19`); **no auto-poll**.

---

## D. Per-element placement tables

### D.1 Trades page

| Element | Location | Source field / component | State / color rules |
|---------|----------|--------------------------|---------------------|
| System filter | Filter Row 1, pos 2 | derived from `trades[].system` count>0; `SYSTEM_NAMES`/`SYSTEM_COLORS` | options = All + present systems only (A3) |
| Outcome filter | Filter Row 1, pos 3 | `filters.outcome`; add `'BE'` to `TradeOutcome` | `Breakeven` between Loss & Scratch (A2) |
| Direction filter | Filter Row 1, pos 4 | `t.direction` | All/Long/Short; Long `--green`, Short `--red` (B1) |
| Synthetic filter | Filter Row 1, pos 5 | `t.is_synthetic` | All/Real only/TEST only; TEST→amber chip (B2) |
| Clear-all + counter | Filter Row 3 | `DEFAULT_FILTERS` (`tradeStore.ts:45`) | idle pill style; counter `text-[10px]` muted (B3) |
| BE StatChip | Summary, between Scratch & Open | `t.outcome === 'BE'` | `--text-secondary` (A2) |
| Truncation notice | Summary, under trade-count line | new `truncated`/`total` from `fetchTrades` | amber `#eab308`, only if `truncated` (A4) |
| Sort affordance | thead: When, Sys, P&L, St | client sort on filtered array | `↕` muted idle / `↑↓` `--text-primary` active; nulls last (C1) |
| Path cell | Path column | `tradePathLine(t)` (`tradeRowFormat.ts:73`) | `max-w-[360px]`, wrap+`title`; contained scroll (C3) |
| Row click → modal | each `<tr>` | `setSelectedTradeId(t.id)` | opens `TradeDetailsModal`; retire inline expand (A1/a) |
| Detail modal | rendered in `TradesView` | `TradeDetailsModal.tsx` + `fetchTradeById` | system-colored border; 8 sections per B.5 |
| Mgmt-log timeline | modal section 8 | `management_log` (804 rows) | ENTRY green / STOP_MOVE amber / *_HIT green / STOP_HIT red (`TradeDetailsModal:304-307`) |
| Loading spinner | tbody, all-col row | store `loading` | muted "Loading trades…"; hides empty msg (C2) |
| Fetch-error banner | above table in `TradesView` | store `error` | `--red` text + `rgba(248,81,73,0.08)` bg + Retry (C2) |
| Empty-after-filter | tbody, all-col row | `trades.length===0 && !loading && !error` | muted "No trades found matching filters." (KEEP) |

### D.2 Build Status panel

| Element | Location | Source field / component | State / color rules |
|---------|----------|--------------------------|---------------------|
| Readiness banner | top of data region, above meta row | `data.readiness` (`types.py:135-149`) | READY→`bull`, DEGRADED→`warning`, BLOCKED→`bear` (C.2) |
| Failed-check chips | inside banner | `readiness.checks[].passed=false` | block→`bear`, degrade→`warning`, info→`textTertiary` (C.2) |
| readiness n/a | inside banner (fallback) | missing/empty `readiness` | `textTertiary` neutral pill (C.2) |
| Global gates table | bridge card, below header / above patterns | `system.global_gates` (`types.ts:97`) | per-gate FRESH `bull` / STALE `warning` / DEAD `bear` (C.3 / A1) |
| Freshness pill (shared) | each gate + field row | `FreshnessPill` (`ComponentTable.tsx:11`) | fresh<60s `bull`, stale `bear`, `lag?` `warning` |
| Bridge Field Inventory | bridge card, collapsible below gates | Phase B backend rows | value `textPrimary`; null→`missing` `textTertiary` (C.4) |
| trend_state row | inside field inventory | `trend_state` | GRAY → 🚩 + `warning` + A1-block note (C.4) |
| Per-system verdict badge | each system header, left of mode pill | per-system roll-up | READY/DEGRADED/BLOCKED via `StatusPill` style (A4) |
| Live Inputs / Interpretation | each system, below header | `live_inputs`/`interpretations` | KEEP (`SystemSection:167-195`) |
| Patterns table | each non-bridge system | `system.patterns` | KEEP; `StatusPill` per row (`PatternRow`) |

---

## E. Implementation guardrails for CC

- Trades elements use **CSS vars + Tailwind**; Build Status elements use **`COLORS`
  + inline style**. Do not cross the streams.
- Extract `FreshnessPill` from `ComponentTable.tsx` into a shared module (smallest
  change) so gates + field inventory reuse one implementation — do not fork it.
- A1: choose modal option (a); delete `TradeRowExpand.tsx` after wiring so there is
  a single trade-detail implementation (no drift).
- No new palettes, no restyle of KEEP components, no auto-poll on Build Status, no
  change to polling floors. Missing data renders `—`/`missing`, never synthesized.
```
