# P30 Woodies CCI Panel — Designer Brief (English)

**Audience:** Designer / frontend implementing Sierra Chart fidelity  
**Hebrew source (authoritative copy):** `P30_WOODIES_DESIGNER_BRIEF_HE.md`  
**Spec:** `docs/design/WOODY_PANEL_DESIGNER_SPEC_v1.md`  
**Baseline mockup:** `v14_data_right_aligned.html` (when available in repo)

---

## Part A: Right data column — field semantics and live updates

This is **not decorative text**. It is Michael's **real-time trading HUD**. Every value must update on market ticks (~1s during RTH).

### 10 fields top to bottom

| # | Field | Example | Meaning | Update rate |
|---|--------|---------|---------|-------------|
| 1 | **CCIDiff H** (green) | `55.19 CCIDiff H` | CCI-14 minus TCCI (CCI-6) at the **current bar's High**. Upward momentum at the high. | Live — every tick |
| 2 | **CCIDiff** (white) | `55.19 CCIDiff` | Current CCI-14 (black line) minus TCCI (yellow line). **Core divergence** value. | Live — every tick |
| 3 | **CCIDiff L** (magenta) | `55.19 CCIDiff L` | Same spread at the bar **Low**. Downward momentum at the low. | Live — every tick |
| 4 | **High Prev/Cur** (green) | `7371.00 7375.00 High Prev/Cur` | **High of previous bar** and **High of current bar**. Instant “did we break the prior high?” | Live — every tick |
| 5 | **Last Price** (black, 22px) | `7374.00 Last Price` | **Traded price now**. Largest, most important field. | Live — **every tick** |
| 6 | **Low Prev/Cur** (black) | `7356.75 7366.75 Low Prev/Cur` | **Low of previous bar** and **Low of current bar**. Mirror of row 4. | Live — every tick |
| 7 | **ProjHigh** (cyan) | `7667.00 ProjHigh` | Projected session high (Initial Balance + range logic). **From Sierra DLL export.** | ~every 5m (per bar) |
| 8 | **ProjLow** (magenta) | `7074.75 ProjLow` | Projected session low. Same source as ProjHigh. | ~every 5m (per bar) |
| 9 | **CCI Pred. H/L** (black) | `18.1  18.1 CCI Pred. H/L` | Predicted CCI-14 range for the **next** bar (theoretical high/low). Used for upcoming cross levels. | Live — every tick |
| 10 | **Low angle** (black) | `-67.7° Low Prev/Cur` | **Geometric angle** of the trend line through the lows of the last two bars. Negative = falling, positive = rising. Steepness gauge. | Live — every tick |

**Note:** Rows 1–3 may show the same number in a quiet bar; they are **three distinct calculations** (at H, at current/CCI point, at L), not one value copy-pasted for decoration.

### Display rules (all rows)

| Rule | Value |
|------|--------|
| Alignment | Right-aligned at **x=447** (spec §5.12) |
| Background | **Fully transparent** over chart — no dark box behind text |
| Font | 11px bold all rows; **Last Price 22px bold** |
| Colors (semantic — do not change) | Green = High / up momentum; Black = Low / neutral; Magenta = ProjLow / down; Cyan = ProjHigh |

---

## Part B: How the column reads the chart

### Link 1: CCIDiff (rows 1–3) ↔ black vs yellow line separation

```
Chart:   black (CCI-14)  ─────╮
                              │  ← visual gap
         yellow (TCCI)  ─────╯

Column:  55.19 CCIDiff
```

- Positive growing CCIDiff → black above yellow → bullish divergence.
- Negative → black below yellow → bearish.
- Near zero → potential **ZLR** cross setup.

### Link 2: CCI Pred. H/L (row 9) ↔ where the white X may go next

- White **X** = current CCI-14 on the building bar.
- Row 9 forecasts next-bar CCI high/low inside ±240 scale.
- Predicted values near **±200** → prepare for extreme / exit logic.

### Link 3: Angle (row 10) ↔ slope of lows

- e.g. `-67.7°` = steep down slope; extremes → fading momentum, reversal watch.

### Link 4: ProjHigh / ProjLow (rows 7–8) ↔ daily context

- Chart shows ~30 bars (~2.5h).
- Proj rows give **expected day high/low** not visible in the bar window.

---

## Part C: Time behavior — two independent layers

### Layer 1: Bottom time strip (Zone 2)

Horizontal drag scrolls **visual time forward/back** together:

**Moves together:** histogram bars, CCI-14 line, TCCI, ZLR markers, white X (if still in view), time labels.

**Stays fixed:** horizontal dashed CCI levels (±200, ±100, 0), Y-axis numbers, **entire data column**, frame separator, title bar.

**Critical rule:** Bar *N* is always above **its** time label — **1:1 lockstep**. Never move time labels independently of bars.

**Live default:** Rightmost bar is **building**; updates every tick; every 5m it locks and a new bar opens; window shifts left.

**Historical mode (spec §6.8):** After scrolling back, chart **freezes**; white X hidden; show **“HISTORICAL — back to NOW”**; **Last Price in the data column stays live** on ticks; bars/lines frozen until return to NOW.

### Layer 2: Right Y-axis (Zone 4)

**Independent** from horizontal time scroll. Vertical drag on Y strip changes CCI scale (default ±240).

---

## Part D: Title bar — what the mockup cut

Sierra title includes study parameters, not only CCI + trends:

```
Woodies CCI Trend [CCI: 47.84]  TrendDown … TrendNeutral … TrendUp …
(6, 5, 14, 100, HLC Avg)  Commodity Channel Index  CCI: …  Line 1: …  Line 2: …
```

Spec §5.2 requires **at least 6 text elements** plus `(6…` study params. Truncating to four fields is a **bug vs Sierra**.

---

## Part E: Executive summary for designer

> The current mockup is a **caricature**, not Sierra. Michael needs **Sierra inside the dashboard** — pixel, color, position, and text match the reference screenshot.
>
> **Only allowed difference:** background `#2D5555` instead of Sierra `#1F4848` for dashboard cohesion.
>
> **Three immediate tasks:**
> 1. Rebuild data column — all 10 rows, right @ x=447, Last Price 22px black, **no dark panel behind text**.
> 2. Fix Y-axis — fixed ±240 scale (13 values, step 40); red ticks only at ±200.
> 3. Work against **`v14_data_right_aligned.html`** — side-by-side review; deviations go back for another pass.
>
> **Acceptance:** If an element is not in the Sierra screenshot (or Sierra has something we omit), it is a **defect**.

---

## Dev backlog triggered by this brief

| Priority | Task |
|----------|------|
| P0 | Export + API fields for CCIDiff H/mid/L, true prev-bar OHLC, DLL ProjHi/Lo, predictor H/L, low-angle |
| P0 | `buildDataTexts` rewrite to match table above |
| P1 | Remove data-column dark overlay; right-align @ 447; Last Price 22px `#000000` |
| P1 | Title bar §5.2 full strings when export provides them |
| P2 | Time strip = scroll + bar/time lockstep (reconcile with any bar-count zoom UX) |
| P2 | Historical mode: frozen chart + live Last Price |
| P3 | WOODY tab, chrome states, `v14` pixel diff |

**Agent handoff index:** `P30_WOODIES_PANEL_AGENT_HANDOFF.md`
