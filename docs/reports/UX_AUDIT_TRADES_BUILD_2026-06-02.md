# UX Audit — Trades Journal + Build Setup

**Date:** 2026-06-02 · **Reviewer:** UX consult (Cowork) · **Scope:** `/trades` page + Build Status (Build Setup) debug surface
**Method:** Read-only audit per CLAUDE.md (audit-before-build, smallest-correct-change, source-of-truth discipline). No production code changed. Mockup uses only existing `Trade` / `BuildStatusResponse` fields — no invented metrics.

---

## 1. What exists today (audit + KEEP/ADAPT/REPLACE/DEFER)

| Surface | File | Verdict | Note |
|---|---|---|---|
| Page shell / header | `TradesView.tsx` | KEEP | Thin, fine. Add nav to Dashboard/Build. |
| Filters | `TradeFilters.tsx` | ADAPT | Rich (mode/system/outcome/dir/date/pattern/overlap/live-gate/confluence). Powerful but no active-filter summary or "reset". |
| Summary strip | `TradesSummaryStrip.tsx` | ADAPT | Has P&L, W/L, win-rate, total-R, by-system. **Missing the three numbers that decide an edge: profit factor, expectancy, max drawdown** — and no time view. |
| Pattern table | `PatternPerformanceStrip.tsx` | KEEP | Genuinely strong — PF, expectancy, by-direction. Only needs sortable headers + visual win% bars. |
| Trade table | `TradesTable.tsx` | REPLACE row body | 12 columns, 1280px min-width, 9–11px mono. The trade *path* and *excursion* are text strings (`IN…→ST…→T1✓`). High cognitive load; the shape of the trade is invisible. |
| Inline expand | `TradeRowExpand.tsx` | KEEP | Per-system recognition is excellent. |
| Build Status | `build_status/BuildStatusTab.tsx` | ADAPT | Readiness verdict + checks[] exist, but verdict sits below ts/session metadata; the *single gating blocker* isn't isolated; no link from a blocker to the trade it affected. |

---

## 2. Findings (prioritized)

### P1 — No equity curve / drawdown anywhere
The journal answers "what happened in each trade" but not "is the account trending up, and what's the worst pain along the way." For a system heading to LIVE futures, cumulative P&L + max drawdown is the primary risk read. **All fields already exist** (`pnl_usd` per trade, ordered by `entry_ts`); this is pure presentation.

### P2 — The trade row hides the trade's shape
`tradePathLine()` and `excursionLine()` encode a rich story (entry → stop-to-BE → T1✓ T2✓ → trailed exit, MFE 8.7 / MAE 1.7, T1 0.2pt away) as a dense mono string. The trader has to *parse* it. A horizontal price track with markers (stop / entry / T1–T3 hit-state / exit) and a shaded MFE–MAE band makes "how did this trade breathe" readable at a glance — same data, ~0 parse cost. This is the single biggest readability win.

### P3 — Edge KPIs are scattered / partial
Win rate and total-R are in the summary; profit factor and expectancy live only inside the pattern table; max drawdown and streaks are nowhere. Pull the six edge numbers (Net, Win%, PF, Expectancy, Max DD, Best streak, Total R) into one card row at the top so the health read is one glance.

### P4 — Build Setup buries the answer
The whole point is "למה לא נכנס / כן נכנס." Today the `READY/DEGRADED/BLOCKED` verdict renders *after* a row of ts/session/RTH metadata, and all checks render as equal-weight chips. When the verdict is BLOCKED there is exactly one gating `severity:'block'` check that matters — surface it at the top in plain Hebrew ("אין snapshot של S2 בחלון הכניסה"), demote the rest.

### P5 — Journal ↔ Debug are disconnected
A trade in the journal and the build snapshot that explains it are two separate screens. A "why did this fire / why was the neighbour skipped" link between them closes the loop the whole product is built around. (Respects source-of-truth: link existing records, synthesize nothing.)

### P6 — Density / readability
9–11px mono across 12 columns at 1280px min-width is a spreadsheet, not a journal. Progressive disclosure (compact visual row → click to expand recognition) lets the table breathe without losing the power-user detail.

---

## 3. Proposed components (shown in the interactive mockup)

1. **`EquityCurveStrip`** — Chart.js line of cumulative `pnl_usd` with per-trade win/loss point colors + shaded max-drawdown. Sits above the table. *(P1)*
2. **`EdgeKpiRow`** — 7 metric cards: Net, Win%, PF, Expectancy, Max DD, Best streak, Total R — all derived from already-loaded trades. *(P3)*
3. **`TradePathRow`** — replaces the text path/excursion cells with a horizontal price track: stop (red) · entry (white) · T1–T3 (blue, green-filled when hit) · exit (amber) + MFE/MAE band. Click → existing `TradeRowExpand`. *(P2, P6)*
4. **`ReadinessHeader`** — verdict pill first, single gating blocker called out in human language, checks demoted to a chip row, plus "חקור את החוסם" / "חבר ל-trade" actions. *(P4, P5)*

---

## 4. Guardrail compliance

- **Source of truth:** every value in the mockup maps to an existing field (`entry_price`, `stop`, `t1/t2/t3`, `t1_hit…`, `price_high/low`, `mfe_pts`, `mae_pts`, `pnl_usd`, `pnl_r`, `systems_agreement`; build `readiness.verdict`, `checks[]`, `rtb_session`). Nothing synthesized.
- **Smallest correct change:** Pattern table and recognition expand are KEEP; only the row *body* and a new top strip change. Filters/store untouched.
- **No trading-logic / risk-surface change.** Presentation only — a phase-gate "stop and ask Michael" point before any code lands.

---

## 5. Suggested sequencing (if approved)

1. `EquityCurveStrip` + `EdgeKpiRow` — highest value, zero data risk, additive only.
2. `TradePathRow` behind a view toggle (visual ↔ classic text) so the dense view stays available.
3. `ReadinessHeader` rework in `BuildStatusTab`.
4. Journal ↔ Build deep-link last (needs a shared trade↔snapshot key — confirm it exists before building).
