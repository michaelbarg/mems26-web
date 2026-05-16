# 04 — Design Brief

**Status:** living document
**Last updated:** 2026-05-16
**Read after:** [`00_README.md`](./00_README.md), [`01_ARCHITECTURE.md`](./01_ARCHITECTURE.md), [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md), [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md)

This is the actual ask. Sections 0–3 are context the designer already saw; this document tells them **what to design, in what order, with what success criteria, and in what file format**.

---

## 1. Project goals (the "why")

| # | Goal | Measured by |
|---|---|---|
| G1 | Operator can run a full RTH session in SHADOW without ambiguity about what the system is doing or why | Zero unexplained banners; every trade has a traceable Reason Tree |
| G2 | LIVE mode is visually unmistakable; the operator never confuses LIVE with SHADOW or DEMO | Color, motion, kill-switch prominence pass squint-test from 10 ft |
| G3 | Kill-switch is reachable in ≤1 click from any screen and produces a confirmed flat position in < 2 s | Stopwatch-tested with Sierra Sim |
| G4 | Per-system context (S1–S6) is glanceable without drilling into side panel | 6 systems' states visible from the primary screen at all times |
| G5 | Trade lifecycle (detected → routed → open → T1 → T2 → T3 → closed) is visually narrated | Per-stage visual treatment defined in §4 |
| G6 | Pre-fire blocks are explainable; the operator understands **which gate** blocked and **why** | Reason-Tree drawer shows gate + threshold + actual value |
| G7 | The design holds up over a 10-day SHADOW soak and a 7-day DEMO soak with daily 4–8 hour sessions | No "I can't tell what's happening" feedback from Michael during soak |

---

## 2. Screens to design

### 2.1 SHADOW dashboard — PRIMARY (P0)

The single most-used surface. The operator sits here for a full RTH session.

**Must contain:**

- **TopBar** (existing baseline): connection status (bridge + backend dots), mode badge (SHADOW yellow), MES symbol, current price, Day Type label, Killzone label + edge class, timeframe selector, daily PnL + trade count, kill-switch entry point, link to Trades view.
- **Live chart** (`ChartV5b`): candles (5-min default) with volume overlay (histogram inside the chart, **not** a separate pane — see [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) §6.1), POC/VAH/VAL lines from S5, IB lines, PD-H/PD-L/PD-C lines, ONH/ONL lines, OPEN line, **trade markers** per `REQ-UI-003`, **active pattern overlay** per `REQ-UI-004`.
- **6-system status surface** — glanceable per `G4`. Today this is the SidePanel Switcher; the design should evaluate whether a richer surface (bottom strip restored, top-bar chips expanded, overlay, or all of the above gated by user preference) better serves the soak operator.
- **Active trade card** (existing `ActiveTradeCard`): live PnL, time-in-trade, targets-hit progress, mode tag.
- **SidePanel Lens**: per-system deep-dive when a system pill is selected.
- **Trade history strip + soak progress strip** below chart (existing).
- **Layer0 chop-score row** above chart (existing).
- **Banner stack** at top: bridge_down, cooldown, loss_cap, system-down (existing) + propose any new banner types.

**Visual mode tag:** subtle yellow (`#facc15`). No pulse. No prominent borders.

**Success criteria for P0:**
- A new operator can identify "what's the current setup if any, which system is active, what's the active trade if any, what's blocking firing if anything" in under 5 seconds from a static screenshot.

### 2.2 DEMO dashboard — visual diff from SHADOW (P0)

Same layout as SHADOW. Visual identity shifts to **cyan** (`#06b6d4`):

- Mode badge cyan.
- Optional: thin cyan accent on chart border, on TopBar bottom border, on SidePanel left border. Designer to decide.
- Per `01_ARCHITECTURE.md` §4: DEMO writes to Sierra Sim. The operator must see **slot indicators** (SHADOW slot + DEMO slot, with the active one highlighted). When a setup fires, both SHADOW and DEMO try to claim — first-wins. The losing one logs "blocked: slot occupied by DEMO" in its Reason Tree. Designer to visualize the "race" or at least the result.

**Success criteria:**
- Operator at a glance can tell which slot owns the current trade (SHADOW-only / DEMO-only / both attempted, DEMO won).

### 2.3 LIVE dashboard — high-alert mode (P0, CRITICAL)

Same layout. Visual identity shifts to **red** (`#dc2626`) and gains motion:

- Mode badge red, pulsing 2 s (CSS animation already exists).
- **Distinct chart accents** (e.g., red border, red TopBar bottom border, possibly a subtle red overlay glow when a LIVE trade is open) — designer to propose.
- Kill-switch button becomes **the most prominent UI element** (large, distinctly placed, always visible without scroll).
- Risk-cap progress (daily $250 cap) shown as a **filling bar** that visibly fills toward red as it approaches; designer to propose treatment.
- News-window warnings (when a high-impact news event is < 5 min away) should escalate to a top-banner with countdown.
- Confirmation modal required for any operator action that could affect a live position (manual close, manual cancel, mode swap to SHADOW outside of kill-switch path).

**Success criteria:**
- The squint test: from across the room, an observer must immediately know whether the screen is in LIVE or not.

### 2.4 Trades view (P1)

Full-page view at `/trades`. Existing components: `TradesView`, `TradesTable`, `TradeFilters`, `TradeDetailsModal`.

**Designer to spec:**
- Table with sort/filter (mode, system, date range, outcome).
- Per-trade row: mode badge, system badge, direction (LONG/SHORT), entry time, entry price, exit time, exit price, PnL ($ + R-multiple), targets hit (T1/T2/T3 with progress dots), Reason-Tree drill-down link.
- Filters: mode (SHADOW/DEMO/LIVE/all), system (S2/S3/S4/all), date range (today / this week / this soak / custom), outcome (win/loss/scratch/all).
- Aggregate row: count, win rate, PnL sum, avg R, max DD.
- Export to CSV.

**Success criteria:**
- A reviewer can answer "what was my S4 win rate last week on Variation days?" in under 10 seconds.

### 2.5 Settings drawer (P1)

Slide-out drawer (existing `SettingsDrawer`). Spec:

- Mode controls (per-system enable toggles; today these are env-flag controlled — propose UI parity).
- Audio cue toggles (entry, partial close, full close, banner, kill-switch).
- Polling cadence override (advanced, default off).
- Replay mode toggle + scrubber (when `MEMS26_CLOCK_MODE=REPLAY`).
- Theme: locked dark (informational; not a toggle).
- Webhook URL for Slack alerts (`REQ-INFRA-020`).
- Debug toggles: PriceDebugConsole visibility, raw JSON viewer on Trades.

### 2.6 Reason-Tree drawer (P0)

A per-fire (or per-block) audit drawer that opens when:
- The operator clicks a trade marker on the chart.
- The operator clicks a trade row in TradesTable.
- The operator clicks a banner about a blocked setup.

**Must show:**
- Setup origin (system, timestamp, pattern, raw confidence).
- Each pre-fire gate evaluated, in order, with PASS/BLOCK + threshold + actual value (e.g., `Daily loss gate: threshold=-$250, actual=-$48 → PASS`).
- The first gate that BLOCKED (if any) is highlighted.
- Per-system context at the moment of fire (S1 day type, S5 TPO POC, S6 killzone — all snapshotted at fire time).
- Routing result (which mode slot owned the trade, why the others didn't).
- Lifecycle outcome (closed reason: T1/T2/T3/stop/time-stop, PnL).
- "Replay this setup" button (links to Replay mode pre-filled).

**Success criteria:**
- Every fire and every block is fully explainable from this drawer alone.

### 2.7 Blocked-Setup drawer (P1)

Variant of the Reason-Tree drawer scoped to blocks only. Listed in a tab inside `DecisionsTab` or as a dedicated sidebar tab.

- One row per blocked setup with: timestamp, system, the blocking gate's name, and "explain" link to a Reason-Tree drawer instance.
- Filter by gate type (time / news / loss / trades / cooldown / margin / manual / slot).
- Counter at top: "today: X blocked / Y validated / Z attempts".

### 2.8 Kill-Switch (P0, CRITICAL)

Three access points (per `REQ-ADMIN` and `01_ARCHITECTURE.md` §4):

1. **Top-bar PANIC button** — visible in every screen.
2. **`POST /api/v9/admin/kill`** — backend endpoint (already specified).
3. **`bash scripts/kill_live.sh`** — CLI fallback.

**Designer scope:** the PANIC button visual + the **confirmation flow**.

- Idle state: red icon, distinct shape (octagon / shield / similar) — not just text.
- Hover state: tooltip "Demote to SHADOW + flatten LIVE position".
- Click → confirm modal: "This will sell to flat and switch to SHADOW. Are you sure? [Confirm] [Cancel]". Modal must have keyboard focus on Cancel (safety).
- During kill execution (< 2 s): full-screen overlay "Flattening position... mode → SHADOW".
- After kill: persistent banner "Kill-switch triggered at HH:MM:SS. Mode is now SHADOW. View audit." linking to the audit log entry.

### 2.9 Stream Health panel (P1)

Existing `StreamHealthPanel`. Spec the table:

| Column | Format |
|---|---|
| Stream name | e.g., `5min`, `tick_reversal_15` |
| Last push age | "ago 2 s" with green/yellow/red threshold (≤5 s / 5–30 s / >30 s) |
| Pushes per minute | numeric |
| Errors (today) | numeric, red if > 0 |
| Latency p50 / p99 | ms |

11 streams listed. Sort by age (most stale first). Mini sparkline per stream optional.

### 2.10 Replay timeline (P2, deferred)

When `MEMS26_CLOCK_MODE=REPLAY`, the operator can scrub through a past trading day. Spec:

- Horizontal time strip across the bottom (separate from TradeHistoryStrip — replay-only).
- Marker per setup, per fire, per close (color-coded by system).
- Scrub handle; click jumps the chart and re-runs all systems from that point.
- Speed control (1× / 4× / 16× / 64×).

Defer to P2 — not required for SHADOW activation.

---

## 3. Open questions (must be answered to start)

These are the architectural-visual decisions the designer must propose answers to. Michael will choose.

### 3.1 Where does the per-system surface live?

The bottom-strip `SystemPanelsBar` (one cell per system) was removed in the 2026-05-16 hardening session. Options:

| Option | Pros | Cons |
|---|---|---|
| A. **Restore at bottom** | Familiar; tall enough to show real content | Eats vertical space; second-class to chart |
| B. **Sidebar tabs** | Already exists (`SystemsTab`); space-efficient | Hidden by default; not glanceable |
| C. **TopBar chips, expanded** | Always visible; small footprint | TopBar already cluttered |
| D. **Chart overlay (transparent panel right of chart)** | Glanceable + non-blocking | Risk of obscuring price action |
| E. **All four, user-togglable** | Maximum flexibility | Implementation complexity + decision fatigue |

Recommended for designer to propose with mockups.

### 3.2 Volume: overlay or separate?

Today, volume is **overlay inside `ChartV5b`** (histogram series). This is non-negotiable (only one chart instance — see [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) §6.1). Designer to specify:

- Overlay opacity / color (currently faint; visible enough?).
- Whether volume gets its own price-scale pane within the same chart.
- Whether footprint per-bar columns (S3 data) can replace or augment the volume bars.

### 3.3 How does the LIVE mode visual differ from SHADOW/DEMO?

Today: only the mode badge color changes (yellow → cyan → red). Per `G2`, LIVE must be unmistakable. Options:

- Chart border color shift.
- TopBar bottom border thickens and changes color.
- Persistent thin red banner across top of viewport.
- Subtle red overlay glow when a LIVE trade is open.
- Sound cue tone shifts (lower pitch for LIVE).

Designer to propose a layered approach.

### 3.4 Accessibility scope?

The system has one user (Michael). No mandated accessibility requirements. **But** the operator does color-grade analysis for 4–8 hours per day; choose colors that survive:

- WCAG AA contrast for body text on dark background.
- Color-blind safety: do not rely on red/green alone for outcome (use shape + color: ▲▼).
- Keyboard navigation for at least Settings, Trades filters, and the kill-switch confirm modal.

### 3.5 Density target?

Reference: `globals.css` sets `font-size: 13px` as base; pills use 8–11 px; TopBar uses 9–11 px. **Very dense.** The current design optimizes for "expert sees everything at once" over "newcomer can understand". Designer to confirm or push back on this density target.

### 3.6 What happens visually when the bridge is down?

Today: `BannerStack` shows "Connection lost — bridge offline". Polling continues and quietly fails. Designer to spec:

- Should non-live data (chart history) remain interactive?
- Should live-data widgets (PriceDisplay, KillzonePill) gray out, freeze, or show a clock icon with age?
- Is there a "reconnect" affordance?

---

## 4. Trade-lifecycle visual matrix

For each combination of `mode × lifecycle stage`, the designer must spec the visual. This matrix is the most important deliverable.

|  | SHADOW (yellow) | DEMO (cyan) | LIVE (red) |
|---|---|---|---|
| Detected (pre-validation) | Faint dotted marker, no sound | Faint dotted marker, no sound | Faint dotted marker, no sound |
| Pre-fire blocked | Subtle banner; reason in Reason-Tree | Subtle banner; reason in Reason-Tree | Subtle banner; reason in Reason-Tree |
| Routed | Marker becomes solid; ActiveTradeCard appears | Marker becomes solid; ActiveTradeCard appears with cyan accent | Marker becomes solid + red glow; ActiveTradeCard appears with red border; confirmation sound |
| Open | ActiveTradeCard live PnL ticking; marker stays | Same + cyan tint | Same + red tint + chart border red |
| T1 hit | Soft chime; T1 dot fills; trail-stop updates | Same | Same + alert sound |
| T2 hit | Same as T1 | Same | Same |
| T3 hit | Closed; full PnL displayed; soak strip increments | Same | Same |
| Stopped | Closed; red marker; ActiveTradeCard fades | Same | Same + strong alert |
| Time-stopped | Closed; yellow marker; ActiveTradeCard fades | Same | Same |
| Closed (any reason) | Fade `justClosedFade=30s` (existing token) | Same | Same |
| Archived | Removed from active; visible only in TradesView | Same | Same |

---

## 5. Requirements traceability (`REQ-UI-001..014`)

Each of these is in `MEMS26_REGISTRY.yaml`. The designer should propose treatment for each; some are already IMPLEMENTED and need only redesign approval.

| ID | Name | Status | Notes / designer scope |
|---|---|---|---|
| `REQ-UI-001` | Left tabs navigation — 9 tabs (Hebrew labels) | SPECIFIED | Confirm 9-tab list; 15 tab files exist today |
| `REQ-UI-002` | Chart volume time-axis alignment with candles | SPECIFIED | Constraint: must align exactly; overlay inside ChartV5b |
| `REQ-UI-003` | Trade markers on candles — mode border + system fill + outcome icon | SPECIFIED | Spec icon set (▲▼ for direction, ✓✗ for outcome) |
| `REQ-UI-004` | Active pattern overlay — visual region for building patterns | SPECIFIED | Translucent rectangle on chart while pattern building |
| `REQ-UI-005` | Predicted vs Actual panel (TAB 9) | SPECIFIED | Per-system predicted PnL vs realized PnL |
| `REQ-UI-006` | Per-system PnL tracker in Trade tab (SHADOW parallel) | SPECIFIED | Always-running SHADOW even when DEMO/LIVE active |
| `REQ-UI-007` | Remove obsolete formula UI (Weights: Vegas 30%...) | SPECIFIED | Delete; do not redesign |
| `REQ-UI-008` | Mock Mode toggle — synthetic data for off-hours dev | SPECIFIED | Dev-only; small toggle in SettingsDrawer |
| `REQ-UI-009` | 100% browser zoom without overflow | SPECIFIED | Test at zoom 100% on 1280×800 minimum |
| `REQ-UI-010` | Bottom system bar — 6 panels with dot/mode/content per system | IMPLEMENTED (currently absent from layout) | Designer to decide: restore, replace, or remove permanently — see §3.1 |
| `REQ-UI-011` | Right-side level badges — POC/VAH/VAL/PDH/PDL/ONH/ONL/OPEN | IMPLEMENTED (`RightSideLabels`) | Redesign approval; confirm collision handling |
| `REQ-UI-012` | Top bar — MES price, day type, session, mode, time | IMPLEMENTED (`TopBar`) | Refresh; resolve density vs clarity |
| `REQ-UI-013` | Color scheme — system colors, mode colors, outcome colors | IMPLEMENTED (`tokens.ts`) | Resolve token conflict — see [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) §7 |
| `REQ-UI-014` | Chart interactions — click candle popup, drag zoom, resize | SPECIFIED | Click → small popup with OHLC + per-system context at that bar |

---

## 6. Success criteria (acceptance)

A delivered design package is accepted when:

- [ ] All 10 screens in §2 are mocked (P0+P1; P2 deferred).
- [ ] The trade-lifecycle matrix in §4 is fully populated (visuals for every cell).
- [ ] The 8 open questions in §3 each have a recommendation with rationale.
- [ ] The 14 `REQ-UI-XXX` items in §5 each have a treatment (or explicit "no change" with reason).
- [ ] All system colors come from **one** palette (resolving the `tokens.ts` vs `globals.css` conflict — see [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) §7).
- [ ] All background colors come from one palette (same conflict).
- [ ] Mode-state matrix is fully designed: SHADOW vs DEMO vs LIVE × idle / setup-detected / pre-fire-blocked / routed / open / closed.
- [ ] Kill-switch flow is end-to-end (idle → click → confirm → executing → confirmed → audit) with every state mocked.
- [ ] Accessibility checks per §3.4 are satisfied.
- [ ] Density target per §3.5 is explicitly confirmed or rejected with replacement target.

---

## 7. Deliverable format

| Artifact | Format | Notes |
|---|---|---|
| Figma file | shared link (read access for Michael; comment access for dev team) | One file containing all screens, components, and states |
| Component states | Figma variants per component | One variant per state (e.g., `Pill / S2 / inactive / FIRING`) |
| Design tokens | `tokens.json` (one file) | Style Dictionary compatible; consumed into `frontend/v9/src/v9/design/tokens.ts` via codegen later |
| Color matrix table | inside Figma + exported PNG | Mode × system × state grid |
| Mode-difference plate | inside Figma | Side-by-side SHADOW / DEMO / LIVE of the same screen state |
| Designer notes | Markdown commit to `docs/architecture/for_designer/05_DESIGNER_NOTES.md` (NEW file by designer) | Decisions made, alternatives rejected, open dev questions |

The designer's Figma link goes in this section once delivered:

```
Figma: <PASTE LINK HERE>
Tokens JSON: docs/architecture/for_designer/assets/tokens.json (NEW)
Designer notes: docs/architecture/for_designer/05_DESIGNER_NOTES.md (NEW)
Delivery date: YYYY-MM-DD
Reviewed by Michael: ☐
```

---

## 8. Files the designer must NOT touch

- Any `.tsx`, `.ts`, `.py` source file.
- `data/mems26_local.db`.
- Any `scripts/*.sh`.
- `frontend/v9/next.config.ts`, `frontend/v9/package.json`.
- The 4 handoff documents under `docs/reports/handoff/`.
- Anything under `bridge/`, `backend/`, `tests/`.

These are dev surfaces. The designer proposes; the dev team implements.

---

## 9. Iteration cadence

| Round | What | Designer turnaround |
|---|---|---|
| Round 1 | Discovery — read the package, propose answers to §3 open questions | 3 days |
| Round 2 | First draft Figma — primary SHADOW dashboard only | 5 days |
| Round 3 | Mode variants (DEMO, LIVE) + lifecycle matrix | 5 days |
| Round 4 | Supporting screens (Trades, Settings, Reason-Tree, Blocked-Setup, Kill-Switch, Stream Health) | 5 days |
| Round 5 | Tokens consolidation + designer notes | 2 days |
| Round 6 | Michael UAT + revisions | as needed |

Each round ends with a 30-minute review call (Michael + designer + dev lead).

---

## 10. After the designer delivers

The dev team will:
1. Codegen tokens from `tokens.json` into `frontend/v9/src/v9/design/tokens.ts`.
2. Reconcile the conflicts called out in [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) §7.
3. Implement screens P0 first (SHADOW + DEMO + LIVE + Reason-Tree + Kill-Switch).
4. Schedule P1 (Trades view + Settings + Blocked-Setup + Stream Health) before SHADOW soak begins.
5. Defer P2 (Replay timeline) until P29.5 (data collection package) is wired.
6. Re-run the squint-test from §1 G2 after implementing LIVE.

---

## 11. Designer focus list — 2026-05-16 addendum

This section is the explicit "what to draw next" delta on top of §1–§10. Where it conflicts with earlier sections, **§11 wins**. The design infrastructure (tokens, components, layout shell) already exists; this round is about closing the visual gaps and adding the three net-new requirements in §11.2–§11.4.

### 11.1 Per-system feature matrix — inputs · current UI surfaces · the gap to close

For each system, the table names: (a) the **inputs** it consumes (full detail in [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md) §S1–§S6), (b) **where** its outputs currently surface in the UI, and (c) the **specific visual gap** to close in this round.

#### S1 — Day Type (OBSERVING) · indigo `#6366f1`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| 5-min bars · TPO IB (from S5) · PD H/L/C | `TopBar` label (3-letter abbrev `TRD`/`VAR`/`NOR`…), `DayTypePill` in Switcher, `DayTypeLensContent` in Lens (5 tabs), `DayTypePlan` card, `System1Panel` (cube, currently unrendered) | (a) A1..A7 stage progression is **shown nowhere** — propose a 7-dot mini-ring on `DayTypePill`. (b) `lock_state=DEGRADED` looks identical to `LOCKED` — propose a degraded badge with explicit reason on hover. (c) `directional_certainty` is reduced to one letter (`B`/`N`/—) — propose a directional glyph that survives the squint test. |

#### S2 — Five-Min T1 (FIRING) · cyan `#06b6d4`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| 5-min OHLCV · `tick_reversal_15` · S1 tier · S5 tier · S6 gate | `FiveMinPill`, `FiveMinLensContent`, `FiveMinPlan`, `System2Panel`, `TradeMarkerOverlay` on chart | (a) "Pattern building" state (e.g., 2 of 3 conditions met) is **invisible** — implement `REQ-UI-004` translucent rectangle on chart. (b) Inside-bar vs Initiative bar glyphs do not exist — propose a per-pattern glyph set. (c) `confluence` is a bare number — propose a bar/ring/gauge treatment. |

#### S3 — Footprint / Tick Reversal T3 (FIRING) · purple `#a855f7`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| `tick_reversal_15` + `tick_reversal_12` + footprint · cumulative delta | `FootprintPill`, `FootprintLensContent`, `FootprintPlan`, `System3Panel` | (a) Per-bar bid/ask footprint column on the chart is the **most-requested artifact** and is absent — propose inside `ChartV5b`, separate hover panel, or both. (b) The 4 detectors (`ABSORPTION`/`STACKED_IMBALANCE`/`SWEEP_RETURN`/`EXHAUSTION`) share one generic icon — propose unified iconography. (c) `evidence` is raw numbers — surface the story ("absorption at VAL: 1,240 contracts bid into, price unmoved"). |

#### S4 — Woodies T2 (FIRING) · orange `#f97316`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| `woodies_5min` bars (OHLCV + CCI_14 + CCI_6_tcci + LSMA + SWI + CZI + EMA_34 + trend_state + predictor + ZLR) · S1 · S5 · S6 | `WoodiesPill`, `WoodiesLensContent`, `WoodiesPlan`, `System4Panel`, `VegasEMAs` overlay | (a) A1..A7 decision tree is **seven bits of state shown as one** ("fired/not") — propose 7 stage-dots on the pill, each PASS/BLOCK. (b) 9 patterns × 2 directions = 18 distinct `classification` states — propose iconography or a short-name convention that fits in a pill. (c) 5 indicators (CCI / LSMA / SWI / CZI / EMA_34) compete for chart space — decide: chart overlay, sparkline, or reveal only when S4 selected. |

#### S5 — TPO (OBSERVING) · yellow `#eab308`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| 5-min bars (volume per price) · TPO letter assignments per period | `TPOPill`, `TPOLensContent`, `TpoPlan`, `TPOLines` (POC/VAH/VAL horizontal lines), `RightSideLabels`, `System5Panel` | (a) The **profile silhouette** (lateral letter histogram per price) — the iconic TPO graphic — is **not drawn anywhere** in the app. Propose left- or right-anchored silhouette, opacity, intersection with candles. (b) `poc_migration` is a text label — propose an animated arrow indicator. (c) HVN/LVN zones are invisible — propose zone-rectangle treatment on the chart. |

#### S6 — Killzone (OBSERVING + GATE) · teal `#14b8a6`

| Inputs | Surfaces today | Gap to close |
|---|---|---|
| Wall clock (ET) · session flags (holiday half-day · trade-in-lunch · block-first-15min) | `TopBar` label, `KillzonePill`, `KillzoneLensContent`, `KillzonePlan`, `System6Panel`, `BannerStack` (when gate blocked) | (a) "Gate BLOCKED" is a **small label color** — propose a dominant treatment (top-of-viewport band, full-killzone tint, etc.) when blocked. (b) The day's killzone timeline (Gantt-style strip showing all 11 zones across the day) does not exist — propose placement above chart or below `Layer0Strip`. (c) `quality_modifier` and `edge_class` say the same thing twice — consolidate. (d) Holiday half-day and news blackout have backend signals but no UI surface — propose a surfacing pattern. |

---

### 11.2 NEW REQUIREMENT — Trade-on-chart visual layer (TradingView-parity)

> **This is the highest-priority net-new ask in this round.**

When a trade is routed (SHADOW / DEMO / LIVE), the chart must gain a TradingView-style overlay that visually narrates the trade on the candles themselves — entry, stop, targets, in-trade tint, exit. This layer amplifies `REQ-UI-003` (trade markers) and `REQ-UI-004` (active pattern overlay) but goes further: the **candle tint between entry and close** and the **target/stop horizontal line set** are net-new.

**Required elements** (designer to mock each):

| Element | Visual treatment | Source field |
|---|---|---|
| Entry marker | Filled triangle on the entry bar — ▲ for LONG, ▼ for SHORT — colored by system | `payload.entry`, `direction` |
| Entry price line | Horizontal solid line at entry price, spanning entry → close | `payload.entry` |
| Stop line | Horizontal **red dashed** line across the in-trade region | `payload.stop` |
| Target lines | Horizontal dashed lines for T1 / T2 / T3, color = system color, right-axis labels `T1` `T2` `T3` | `payload.t1` / `t2` / `t3` |
| In-trade candle tint | All candles between entry and close tinted with the **mode** color at low alpha (SHADOW yellow ~12%, DEMO cyan ~12%, LIVE red ~12%) so the trade window is visible at a scroll-glance | `entry_ts → close_ts` from `/api/v9/trades` |
| Targets-hit ticks | Small tick fills on each target line as it is hit (T1 fills, then T2, then T3) | trade lifecycle events |
| Exit marker | Filled circle at exit bar, color = outcome (green = win / red = loss / yellow = scratch) | `close_reason`, `pnl_usd` |
| R-multiple label | Inline small label at the exit marker: `+1.4R` / `-1.0R` / `+0.0R` | computed from entry/stop/exit |

**Behavior:**
- Layer is **on by default** in all modes; toggleable per-mode via Settings.
- Persists for 30 s after close (use existing `justClosedFade` token), then collapses to a static historical marker.
- Stacking rule: an open trade's overlay is drawn **above** any historical overlay it intersects.
- Designer to propose treatment for **overlapping concurrent trades** (e.g., S2 SHADOW + S4 DEMO open simultaneously) — likely thinner lines, dual tint, or chooser.

**Success criterion:** a screenshot of the chart during an open trade tells a new viewer, without text: "this was a LONG entered here, stop is here, T1/T2/T3 are here, candles in the trade window are tinted by mode, and the exit (when it happens) will be marked here."

---

### 11.3 NEW REQUIREMENT — SidePanel composition: Woody slot, Plan-tab focus, and the 6-cube width rule

The SidePanel (right column in source, visually on the **left** for the Hebrew/RTL operator — 248 px wide) is the at-a-glance surface. The new composition, top → bottom:

```
┌───────────── SidePanel (248 px) ─────────────┐
│ 1. ActiveTradeCard          (existing)       │
│ 2. WoodySlot                (NEW — §11.3.1)  │
│ 3. Switcher (S1..S6 pills)  (existing)       │
│ 4. Lens (5 tabs, focus = "Plan" — §11.3.2)   │
│ 5. SystemCubes (S1..S6)     (new width rule) │
└──────────────────────────────────────────────┘
```

#### 11.3.1 WoodySlot — new reserved rectangle for the mascot

- A reserved rectangle in the SidePanel for "Woody" — a mascot character. **Image assets are supplied by Michael** (not yet in the repo; designer to reserve the space and stub with a placeholder).
- Position: directly under `ActiveTradeCard`, above the Switcher.
- Suggested size: ~96–128 px tall × full SidePanel width (248 px). Designer to confirm.
- Stateful: Woody's pose / expression changes per the **currently selected system in the Switcher**, paired with that system's **Plan tab** content (see §11.3.2). Michael will walk the designer through each system's intended Woody pose one-by-one.
- Idle (no system selected): Woody in a neutral pose.
- Empty / loading: Woody-only with a small "…" indicator (no skeleton block — keep the character visible).

#### 11.3.2 Plan tab (the "second tab" of each Lens) — designer focus

The Lens (`frontend/v9/src/v9/components/molecules/Lens.tsx`) has 5 tabs: `Now / Plan / Shadow / Hist / Chart`. The **Plan tab is the second tab** and is currently a static text card per system (see `frontend/v9/src/v9/components/sidepanel/lens/plan/*Plan.tsx`). Each system's Plan tab must express something **different**:

| System | What "Plan" must convey |
|---|---|
| S1 Day Type | Today's expected behavior given the locked or pending day-type classification; what the operator should anticipate from each firing system on this kind of day |
| S2 Five-Min | The pattern currently building (if any) + which conditions are met / unmet; what would cause it to fire |
| S3 Footprint | The current order-flow story (who's in control, where absorption is forming) + which detector is closest to firing |
| S4 Woodies | A1..A7 decision tree as a vertical stepper; which stage we are on, which is blocked, why |
| S5 TPO | The day's profile geometry (shape, POC migration vector, where value is rotating); not a tradeable plan — a context plan |
| S6 Killzone | The next gate transition (e.g., "LUNCH closes in 18 min → NY_PM opens (B-edge)"); a day timeline mini-strip |

Designer to deliver **6 distinct Plan-tab layouts**. Michael will review each one alongside the Woody pose for that system (§11.3.1) — the Plan tab and Woody read together as one composition.

#### 11.3.3 SystemCubes (6 cubes) — full-width vs half-width rule

This supersedes §3.1. The 6 `System1Panel..System6Panel` files **already exist** (`frontend/v9/src/v9/components/panels/`); only the container was removed. The new layout rule places them at the bottom of the SidePanel with a stateful width:

| Cube state | Width | Trigger |
|---|---|---|
| **Full width** (one column, full 248 px row) | default | system is `ACTIVE` / `FIRING` / `LOCKED` / has an `activeSignal` |
| **Half width** (two columns, ~115 px each) | compact | system state is `PENDING` (Hebrew: ממתין) — waiting for inputs, plan-only, no signal yet |

**Rejected** (do not propose): the previous mock that placed 3 cubes on the left half of the panel and 3 on the right half by default. Cubes occupy **full panel width by default**; only `PENDING` cubes shrink to half-width and pair up.

The panel "breathes" as systems light up — full-width cubes climb up, half-width pairs sink down. Designer must mock the **four states**:

1. All 6 full-width (rare; everything firing or has an active signal).
2. All 6 half-width (early pre-market; every system is `PENDING`).
3. Mixed (e.g., S2 + S4 + S6 full-width; S1 + S3 + S5 paired half-width below).
4. Single full-width (e.g., S2 only firing) + the other 5 cubes as a 2-column grid of half-width pairs (one of them solo-half).

**Sort order within the stack:** full-width cubes first (in S-number order: S1→S6), then half-width pairs (S-number order, two per row).

---

### 11.4 Tab-by-tab focus list — designer working order for Round 2

Per the iteration cadence in §9, **Round 2** should deliver, in this priority order:

1. **SHADOW dashboard mocked with the new trade-on-chart visual layer** (§11.2) — at least one open-trade frame, one closed-win frame, one closed-loss frame.
2. **SidePanel redesign**: WoodySlot placeholder + new SystemCubes width behavior in all 4 states (§11.3.1, §11.3.3).
3. **6 Plan-tab variants** (§11.3.2), each paired with the system's intended Woody pose.
4. **Per-system gap closures** (§11.1):
   - S1 + S4: A1..A7 stage ring on pill.
   - S2: active-pattern rectangle on chart.
   - S3: per-bar footprint column.
   - S5: profile silhouette overlay.
   - S6: killzone Gantt strip.

Sections §2.2–§2.10 (DEMO/LIVE variants, Trades view, Settings, Reason Tree, Blocked-Setup, Kill-Switch, Stream Health, Replay) follow in Rounds 3+ as scheduled.

---

*End of designer package. For project status and roadmap: [`../../reports/handoff/GANTT_TO_LIVE.md`](../../reports/handoff/GANTT_TO_LIVE.md). For active prompts: [`../../reports/handoff/PROMPT_LIST_TO_LIVE.md`](../../reports/handoff/PROMPT_LIST_TO_LIVE.md).*
