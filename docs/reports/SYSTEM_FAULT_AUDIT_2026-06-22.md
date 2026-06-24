# MEMS26 — Full System Check / Fault List (2026-06-22)

Status legend: ✅ fixed today · 🔧 spec'd to CC (flag-OFF, awaiting build/verify) · 🟡 built flag-OFF, awaiting SHADOW + Michael · 🔴 open (no fix yet).

The through-line of today: the **logic** is mostly right; the **plumbing** (which data source is live, which classifier feeds which screen, when fires are allowed) is fragile. Nothing here is LIVE-money — all SHADOW.

---

## Axis 1 — Day-type classification (סיווג סוג היום)

| # | Fault | Sev | Root cause | Fix / status |
|---|-------|-----|-----------|--------------|
| 1.1 | **Two classifiers disagree** — pills/snapshot = old 3-type engine; Build-Status = new 7-type | High | Old engine still feeds the live per-bar path; new classifier only on classify_replay | Display unified to classify_replay ✅; live-engine swap built+verified flag-OFF (`S1_ENGINE_NEW_CLASSIFIER`) 🟡 |
| 1.2 | **Wide days mis-stamped Nontrend** — today 72pt range = Nontrend (should be Normal) | High | No range floor on Nontrend | `NONTREND_WIDTH_FLOOR` >18pt 🔧 (verified: today→Normal, 06-19→Nontrend) |
| 1.3 | **Display read stale/gapped `v9_bars_5min`** → strip + classify froze on early bars | High | Raw-bars stream gapped (missing 09:00–09:35); consumers picked it | Strip → fresh-with-fallback to woodies ✅ |
| 1.4 | Live engine misclassified Trend_DD when wired (06-16→Variation) | Med | Per-bar call omitted `profile_shape` | CC added IB-lock context cache → Trend_DD ✅ verified (flag-OFF) |
| 1.5 | `classify_replay` docstring stale ("Trend_DD won't fire") | Low | Not updated after refactor | 🔴 cosmetic |

## Axis 2 — Direction per day-type (סיווג כיוון)

| # | Fault | Sev | Root cause | Fix / status |
|---|-------|-----|-----------|--------------|
| 2.1 | **Direction model not wired to the firing gate** — display-only | High | `DIRECTION_CONTEXT` gate flag-OFF, never validated | Gate built flag-OFF 🟡; needs full backtest (#18) before enable |
| 2.2 | **Strip showed "unclear" on a clear down-break** | High | `_fetch_live_bars` picked gapped 5min on a freshness tie; sparse CVD lookback read +1 | Prefer contiguous source on tie ✅ |
| 2.3 | **Balance-branch misfires on trend days** (06-16: reads UP on a down-trend → blocks winners) | Med | `close-vs-POC` overrides breakout-state on trend days | 🔴 open — trend/breakout must override balance |
| 2.4 | Direction degrades to no-CVD when falling back to woodies | Low | woodies has no `cumulative_delta` | Acceptable now; real fix = repair `v9_bars_5min` ingestion gap 🔴 |

## Axis 3 — Pattern firing gates (אפשרות לתבניות לירות)

| # | Fault | Sev | Root cause | Fix / status |
|---|-------|-----|-----------|--------------|
| 3.1 | **Nontrend-no-block gap** — Nontrend allows ALL fires | High | Gate assumed playbook blocks Nontrend; it doesn't | Nontrend width-floor + opening gate 🔧 |
| 3.2 | **No opening-type gate** — fires AGAINST the opening drive | High | `opening_type` computed but never gates fires | `OPENING_TYPE_GATE` 🔧 (allow with-drive, block counter) |
| 3.3 | **Patterns fire pre-IB-lock** with no day structure | High | No "wait for structure / opening gate" rule | Addressed by 3.2 🔧 |
| 3.4 | **Duplicate double-fire** (ids 199/200, 2s apart) + **no already-positioned check** (4 shorts stacked on the 10:20 bar) | Med | No dedup / no open-position guard | 🔴 open — dedup + position-stack guard |
| 3.5 | Position gate is location-only (short above POC allowed pre-breakout) | Med | Gate doesn't know "fade edge" vs "pre-breakout coil" | Opening gate + direction gate address it 🟡 |

## Axis 4 — Today's fires (למה היום ירו לא נכון)

| # | Finding | Sev | Detail | Fix / status |
|---|---------|-----|--------|--------------|
| 4.1 | **−$280 net** (closed): 4 counter-drive shorts −$555 vs breakdown winners +$275 | — | Shorted an OPEN_DRIVE UP (0.85) before the break | Opening gate would block all 4 🔧 |
| 4.2 | **Profit-realization too tight** — trail cut both winners on the first bounce (195: +1.14R vs 2.44R MFE; 196: ran to POC after exit) | Med | k=1.0 trail too tight on a clean trend leg | 🔴 trailing-runner lever (already on roadmap) |
| 4.3 | `quality.day_type`=None in trade JSON (column OK, nested copy null) | Low | Not threaded into the payload | 🔴 low-risk |
| 4.4 | Entered the breakdown late (09:40) — GRAY-trend no-fire zone 09:15–09:35 | Info | S4 needs a colored trend | By-design; note for direction gate |

## Axis 5 — Codebase index (למה האינדקס לא היה יעיל)

| # | Fault | Sev | Root cause | Fix |
|---|-------|-----|-----------|-----|
| 5.1 | **No source-of-truth / data-flow map** — index is a file/import locator only (0 SoT entries) | High | gen_index maps files+importers+orphans, not *which DB table/endpoint is the canonical LIVE source per signal* | **Add a "Source-of-Truth map"** to `SYSTEM_INDEX.md`: per signal (5min bars · day-type · direction · TPO levels · trades) → the canonical live table/endpoint + the stale/legacy ones to avoid. This is exactly the gap that caused today's stale-table & two-classifier confusion (CLAUDE.md §Source-of-Truth Discipline) |
| 5.2 | `bars_5min_continuous` model flagged orphan, but the **table is written with junk** (close=6274) | Med | Disconnect between model (unused) and a populated-but-garbage table | 🔴 document or retire the table; it must never be a bars source |

**Why the index didn't help today:** every problem today was *"which source is the live truth"* (stale `v9_bars_5min` vs live woodies; old engine vs new classifier; gapped vs contiguous bars). A file-locator index answers *"where is the code"* — which I already knew. The missing layer is the **data-flow / source-of-truth map** (5.1).

---

## Priority order (my recommendation)
1. **Opening-type gate + Nontrend width-floor** (3.1/3.2/4.1) — biggest live-money lever; blocks today's −$555 pattern. 🔧 at CC.
2. **SHADOW-validate the engine-unification** (1.1) — stop the two-classifier split for good. 🟡 your enable.
3. **Source-of-Truth map in the index** (5.1) — prevents the next stale-source bug.
4. **Dedup + already-positioned guard** (3.4) — stop duplicate/stacked fires.
5. **Trailing-runner** (4.2) + **balance-branch trend override** (2.3) — recover left-on-table profit + fix the trend-day direction misread.
6. Backtest `DIRECTION_CONTEXT` before enabling (2.1, #18).
