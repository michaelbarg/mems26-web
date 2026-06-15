# Marker Tool — Parity Checklist (standalone → dashboard)

Going through **one by one together**. Source of truth = the standalone tool
`docs/reports/TRADE_PLACEMENT_MARKER_2026-06-12.html`. Status of the new in-dashboard
version (`frontend/.../trades/TradeMarkChart.tsx` + `TradeReviewPanel.tsx`):
**✅ done · ⚠️ partial · ❌ missing · ➕ dashboard-only extra**.

Tell me a number to start on, or say "in order" and we go top to bottom.

---

## A. Header / "upper part" (explanations + calculations)
1. ❌ Collapsible **"system state today"** panel (live flags: PATTERN_RISK_CAPS, GIANT_BAR_STOP, RUNNER_TARGETS_V1, S2_VOL_ADAPTIVE…)
2. ❌ **"How we got here"** narrative timeline (10-11.06 → now)
3. ❌ **Documents list** (INSIGHTS_UNIFIED, S2_WHY_NOT_FIRED_REPLAY, PLAYBOOK…)
4. ⚠️ Instruction hint ("pick a level → click the chart") — short version present

## B. Controls bar
5. ⚠️ **◀ Prev / Next ▶** nav — replaced by the list (decide: add arrows?)
6. ✅ Trade **selector** (standalone dropdown → dashboard selectable list)
7. ❌ **"marked X/Y" progress** counter (dashboard shows filter count instead)
8. ⚠️ **Day-levels toggle** checkbox — dashboard always-on, and missing pivots/PD (see 22–23)
9. ❌ **Export** button (download marks JSON)
10. ✅ **Level buttons** — entry / stop1 / stop2 / stop3 / T1 / T2 / T3
11. ✅ **"Would not enter"** toggle
12. ✅ **Note** textarea
13. ✅ **Meta line** — #id · pattern · direction · date · day-type (in detail)
14. ⚠️ **Live calc readout** — dashboard shows risk + R→T1/T2/T3 summary; standalone shows **per-level** (stop → risk pts; target → +pts + R) inline

## C. Price panel — layers
15. ✅ Candles
16. ⚠️ **Dual price axes** (left + right) — dashboard has right only
17. ✅ Price grid
18. ➕ **Volume** bars — dashboard-only (standalone has none; you asked for it ✓)
19. ✅ **POC**
20. ✅ **VAH / VAL**
21. ✅ **IB high / IB low**
22. ❌ **Pivots** — PP, R1/R2/R3, S1/S2/S3  *(needs replay endpoint to compute from prior day)*
23. ❌ **Previous-day PDH / PDL**  *(needs replay endpoint)*
24. ✅ System **Entry** line (+ sticker)
25. ✅ System **Stop** line (+ sticker)
26. ✅ System **T1 / T2** lines (+ stickers)
27. ✅ System **Exit** line (+ sticker)
28. ✅ **Entry ▲/▼** marker on the entry bar
29. ✅ **Exit ⊗** marker on the exit bar
30. ✅ My **marked** lines (entry/stops/targets)
31. ➕ **Labeled price-tag stickers** per line, decluttered (clearer than the standalone's inline labels)
32. ➕ **Entry/exit bar highlight bands** — dashboard-only
33. ➕ **Setup bracket on the entry candle** — dashboard-only

## D. Sub-panels
34. ✅ **CVD** = cumulative-delta **histogram** (green rising / red falling) — just matched
35. ⚠️ **Woodies CCI** line — present; standalone may color by trend_state (decide)
36. ✅ CCI **±100 / 0** guides
37. ✅ **Time axis** (HH:MM ET)
38. ➕ **Precise ENTRY time** on the axis — dashboard-only

## E. Interactions
39. ✅ **Crosshair**
40. ✅ **Hover readout** — price · bar time · OHLC · CCI
41. ✅ **Click-to-mark**
42. ➕ **Zoom** (±window) — dashboard-only
43. ➕ **Drag-to-resize** chart height — dashboard-only

## F. Marking model / persistence / loop
44. ✅ Marks per trade id (localStorage)
45. ⚠️ **Origin issue** — marks split across `localhost` / `127.0.0.1` / `file://`; fix = persist to DB
46. ❌ **Export marks JSON**
47. ❌ **Submit** button → save marks+notes to **DB** (`v9_trades.quality`) → I derive **lessons** *(needs new endpoint + restart)*
48. ❌ **Import** your existing marks (recovered: localhost #33/#80/#81/#84/#87, file:// #28)

## G. Data / trades ("including the trades")
49. ✅ **Trades list** — standalone: 48 frozen (06-11+06-12); dashboard: **live** (65, all dates)
50. ✅ **Win/Loss + PnL + filter** per trade (dashboard adds ✗/✓ + Losses/Wins/No-entry/Marked filters)
51. ✅ **Day type** per trade
52. ✅ **Bars + CCI + CVD + levels** per date — standalone frozen; dashboard **live** via `/api/v9/chart/replay`
53. ❌ **System's entry rationale** ("why the system entered") per trade — neither has it yet; source = `v9_trades.cross_context` + fire insight

---

### Biggest gaps to close (my read)
**22–23** pivots + PDH/PDL · **14** per-level calc · **46–48** export/submit/import · **53** system rationale · **8** levels toggle · **1–3** explanations header.

Trades data fields (standalone): `id, pat, d, ts, entry, stop, t1, t2, dt, xts, xp, xr, pnl`.
Level fields (standalone, per date): `poc, vah, val, ibh, ibl, pdh, pdl, pp, r1-3, s1-3, daytype, opening`.
