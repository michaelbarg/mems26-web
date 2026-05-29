# MEGA-PROMPT · Independent Critical Review of MEMS26 S2/S4 Forensic Audit · 2026-05-28

> **How to use:** Paste the entire block below the `--- BEGIN PROMPT ---` line into Claude Desktop (claude.ai) and attach the file list under §B as upload attachments. Claude Desktop has no live access to my system — your job is to stress-test our findings using only the attached source code, spec, and the forensic report.

---

--- BEGIN PROMPT ---

You are a senior systems auditor performing an **independent critical review** of a pre-LIVE forensic audit of an algorithmic futures trading system (MEMS26). The system is days from going LIVE on MES futures. Mistakes from here cost real money. Your job is to **confirm or refute the audit's findings using nothing but the attached files**. Do not propose fixes. Do not suggest implementations. Confirm what is solid, refute what is weak, and surface gaps the auditor missed.

## §A — Background

Earlier today (Thu 2026-05-28, ~12:00 ET, RTH active), the trading system's S2 (5-Min) and S4 (Woodies CCI) firing systems produced **zero trades**. An initial diagnostic report (`DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md`) concluded: *"No bug. Gates open. Patterns simply didn't match today's price action."*

The system owner pushed back on three grounds:

1. The Woodies CCI values in the frontend UI **do not match** the Woodies CCI study he can see in his Sierra Chart UI right now.
2. Today's price action actually had multiple high-quality Woodies setups (per his eye on the chart).
3. He suspects the data reaching the backend is wrong, not the trading logic.

A second auditor performed a forensic re-audit and produced the report attached as `AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md`. The forensic report concludes the prior diagnosis was wrong: **patterns WERE detected (the database has 12+ S4 signal hits today)**, but they were blocked at the A5/sizing stage because the Sierra study values (SWI, TCCI, CCI-14, LSMA, EMA-34, CZI, trend_state) for the most recent ~13 bars of every session in the DLL export are **frozen / identical across all 13 bars** — a data-integrity bug, not a logic bug.

## §B — Files to attach (minimum sufficient set)

Upload these 12 files. Each one is annotated with what to look for.

| # | Path | What it is | What to inspect |
|---|------|-----------|-----------------|
| 1 | `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` | The forensic report you are reviewing | The conclusions, especially §3 parity table, §5 replay, §6 ranked hypotheses |
| 2 | `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` | The PRIOR diagnosis being challenged | Compare its claims to the new evidence; was the prior author wrong, partially wrong, or wrongly summarized? |
| 3 | `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | Master spec | Find the Woodies / S4 / S2 sections; check if the impl deltas D-1..D-6 in §2 of the audit are correctly classified |
| 4 | `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` | 9-pattern entry/stop/exit spec (canonical) | Confirm the 9 pattern IDs in the impl match. Confirm RTH/lunch/FOMC/trend-state filters per pattern |
| 5 | `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv` | Day-type advisory matrix | Note this is "advisory" per Pipeline 2 scope |
| 6 | `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` | Strategy caveats / failure modes | Check if frozen-data failure modes are documented |
| 7 | `sc_study/v9_woodies_export.h` | **The C++ DLL function that builds `woodies_5min.json`**. Look hard at lines 421-572 (function `v9_woodies_5min_to_json`). | The frozen-tail hypothesis lives or dies here. Audit `GetStudyArrayFromChartUsingID` + `GetContainingIndexForDateTimeIndex` + the `S_VAL` macro fallback to `v9_calc_cci`. Does the local-fallback at non-zero stale values protect the export? |
| 8 | `sc_study/v9_exports.h` | Helper macros incl. `v9_sc_datetime_to_unix` (lines 147-152) | Confirm the timestamp encoding produces Chicago-wall-clock-as-UNIX as the bridge assumes — OR is it actually chart-local? |
| 9 | `sc_study/MES_AI_DataExport.cpp` | The main DLL entry. Look at the `WoodiesSierraStudies sierra` block (lines 569-628) | This is the per-bar Sierra-study read for the current bar. It uses `arr[idx]` (NO `GetContainingIndexForDateTimeIndex` mapping) — that's why `current_bar.cci_14` is live (47.21) while `history[-1].cci_14` is frozen (49.70). Confirm. |
| 10 | `bridge/v9_streams/base_stream.py` | The bridge — applies the "Chicago TS" fix at lines 58-87, 283-322 | Look at `_chicago_to_utc` and `BUGGY_TS_KEYS`. Is the fix DST-aware? If chart is in ET not CT, what is the actual error? |
| 11 | `bridge/v9_streams/woodies_5min_stream.py` | The trivial Woodies-5min stream subclass | Confirms which file it watches |
| 12 | `backend/v9/api/v9/bars.py` | The FastAPI ingestion endpoint. Look at lines 786-853 (POST /api/v9/bars/woodies_5min) | Audit the routing decision: `payload.all_bars` prefers `history` over `current_bar`. Result: S4 is fed the FROZEN history tail, not the LIVE current_bar. Is this intentional or a bug? |
| 13 | `backend/v9/api/v9/woodies_chart_routes.py` | The frontend Woodies chart endpoint (GET /api/v9/woodies/chart) | This is what `WoodiesCciPanel.tsx` queries every 15s. Audit the `+5h` Chicago fix on line 43 and the `_parse_sierra_payload` merge of `current_bar` onto `history[-1]` |
| 14 | `backend/v9/systems/woodies/woodies_system.py` | The S4 firing system. Lines 198-470 (`process_bar`) + 581-628 (`calculate_size`) | Confirm: (a) S4 consumes `bar.cci_14` etc. directly from the routed bar (the frozen one); (b) `calculate_size` consumes `self.current_state` (also frozen); (c) A5 = sizing reject is the gate fired for all 12+ detected patterns today |
| 15 | `backend/v9/systems/woodies/pattern_engine.py` + the 9 detectors in `backend/v9/systems/woodies/patterns/*.py` | The pattern detection layer | Confirm the 9 IDs match the spec (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE) and that each blocks on `AntiPattern.blocked` |
| 16 | `backend/v9/systems/woodies/anti_patterns.py` | AP1-AP9 enforcement | Confirm `blocked=True` → `detected=False` chain |
| 17 | `backend/v9/systems/woodies/pattern_dispatcher.py` | W-8 dispatcher (select_winner) | Confirm tie-breaker logic; check if `r_t1_missing_fallback=true` matches `dispatcher_config.yaml` |
| 18 | `backend/v9/systems/woodies/decision_tree.py` | A1–A7 + B1–B14 stages | Confirm the A1–A7 ordering and that A5 = "sizing" is correctly labeled in the audit |
| 19 | `backend/v9/systems/five_min/five_min_system.py` | S2 firing system | Lines 680-790. Audit the gate ordering: mode → NT skip → Reactive → Initiative → H&S → DblBT → Flag → FHB gate. Is anything unsafe with the +1h timestamp drift on `bar.ts`? |
| 20 | `frontend/v9/src/v9/components/chart/woodies/WoodiesCciPanel.tsx` | The Woodies CCI panel Michael looks at | Line 1043: `fetch(${API}/api/v9/woodies/chart?limit=…)`. 15s polling. Look at how `current` overlays the chart line — does it visually hide the frozen tail or expose it? |
| 21 | `frontend/v9/src/v9/components/systems/WoodiesLensContent.tsx` | The Woodies lens content used by the dashboard | Audit what fields it shows from `systems[4]` state |

> Total: ~21 files. Skip any one you can't open; just say which.

## §C — Forensic report's headline claims (your job: stress-test each)

**Claim 1 — DLL frozen-tail bug.** The last ~13 5-min bars in every session block of `woodies_5min.json` share IDENTICAL Sierra-sourced studies (CCI-14, TCCI, LSMA, EMA-34, SWI, CZI, trend_state). Cause hypothesis: `sc.GetContainingIndexForDateTimeIndex(woodies_chart, dll_bar_idx)` maps the 13 most recent DLL bars to the same Woodies-chart index because the Woodies chart's study array hasn't been recomputed past a boundary for "in-progress" bars; the `S_VAL` macro returns a non-zero stale value, so the local-fallback (`v9_calc_cci`) is bypassed.

- Read `sc_study/v9_woodies_export.h` lines 460-475 and 489-528.
- Is the hypothesis plausible? What other Sierra-side cause could produce this pattern?
- The bug is ONLY in the per-bar history loop. The single-bar `WoodiesSierraStudies sierra` read in `MES_AI_DataExport.cpp:582-621` does NOT use `GetContainingIndexForDateTimeIndex` — it does `arr[idx]` at known-good `idx`. Confirm the asymmetry.

**Claim 2 — Backend ignores `current_bar`.**
`Woodies5MinPayload.all_bars` (in `backend/v9/api/v9/bars.py:223-231`) returns `history` if non-empty, else `current_bar`. So when both are present (always in practice), the routing path passes `history[-1]` (frozen) to S4.

- Confirm by reading the function.
- Is this intentional (e.g., to avoid re-routing the live tick multiple times per bar)? Look for a comment.

**Claim 3 — A5/sizing reject is the actual fire-blocker.**
For the 11:10 ET ZLR LONG with conf 0.83 detected today, with FROZEN `swi_value=-78.17` and FROZEN `tcci=-21.09`, the audit computed `aux_count = 0+1+0 = 1`, which causes `calculate_size()` to return `"reject"` for any tier above `low`. With LIVE Sierra values (Sierra UI shows positive SWI and rising TCCI alongside the +131 CCI), the math would likely have flipped to `aux_count ≥ 2` and produced `half` or `full`.

- Walk through `calculate_size()` lines 581-628 yourself. Recompute aux_count for ZLR/LONG with the frozen values vs a plausible live snapshot (SWI ~+20, TCCI ~+150, CZI ~60). Does the audit's math hold?

**Claim 4 — Chicago TS over-correction.**
`bridge/v9_streams/base_stream.py` adds 5h to bar ts (Chicago CDT → UTC); `backend/v9/api/v9/woodies_chart_routes.py:43` does the same. If Sierra chart is actually in ET (EDT), this over-corrects by 1h. The audit's evidence: DB row `v9_bars_5min.ts = 2026-05-28 17:10:00` (= 13:10 ET) at wall-clock time 12:10 ET.

- Read both fix sites.
- Is `v9_sc_datetime_to_unix` (in `sc_study/v9_exports.h:147-152`) actually emitting CDT-wall-clock or chart-local-as-UNIX? Both bridge and backend assume CDT.

**Claim 5 — Frontend shows 13 identical bars then a "live tick" jump.**
Live response from `/api/v9/woodies/chart?limit=20` at 12:20 ET wall-clock:
```
ts=16:15 UTC  cci=145.45 ...  (1 bar OK)
ts=16:20 UTC  cci=155.98 ...  (start of frozen block)
ts=16:25 UTC  cci=155.98 ...
... 11 more identical ...
ts=17:15 UTC  cci=155.98
ts=17:20 UTC  cci=-134.45 ...  (current_bar overlay; +1h timestamp drift visible)
```

- Read `_parse_sierra_payload` in `woodies_chart_routes.py:149-225`.
- Why does the function leave the 13 frozen bars in the response untouched but overlay current_bar onto the tail? Is the merge correct? Should the function detect the frozen tail and warn/repair, or is that out of scope?

**Claim 6 — `v9_woodies_patterns` table is defined but never written; signals table IS the truth.**
The audit ran `rg "V9WoodiesPattern\(" backend/` → 0 hits. So the prior diagnosis's mental model ("if no rows in patterns table, no patterns detected") was structurally wrong.

- Confirm by ripgrep over the backend.

**Claim 7 — Bridge / push freshness is healthy.**
`bar_router.received = 9,383` today; `v9_bars_5min_woodies` has 3,193 rows (one per push); Sierra file mtime <3s. Spec requires bar-level cadence (no tick-level requirement for the 9 patterns).

- Confirm spec doesn't demand tick-level in Tables A/C.

## §D — Critical-review questions you MUST answer

Answer each as **CONFIRMED / REFUTED / NEW GAP** with file:line citations.

1. Is the DLL frozen-tail subgraph-mapping hypothesis (Claim 1) consistent with the C++ code? If not, what's a better explanation given the field-by-field freeze across 7 different Sierra study outputs simultaneously?
2. Does the impl of the 9 Woodies patterns (`backend/v9/systems/woodies/patterns/*.py`) match the entry/stop/T1/T2 spec in `S4_WOODIES_TABLE_A_Pattern_Setup.csv`, or is there silent drift in any of the 9 detectors?
3. Is `calculate_size` (lines 581-628) reading from `self.current_state` (which lags by one bar) or from `studies` (the current bar's values)? Does that matter for the A5-reject conclusion?
4. Is the +5h timestamp fix in `backend/v9/api/v9/woodies_chart_routes.py:43` and `bridge/v9_streams/base_stream.py:_chicago_to_utc` DST-aware? Is there any code path that probes the actual Sierra chart TZ?
5. Is `Woodies5MinPayload.all_bars` deliberately preferring `history` over `current_bar`, or is that an unintended fallback? Read the docstring/comments and judge.
6. Are there OTHER frozen-tail symptoms elsewhere in the codebase (e.g. footprint/5min/TPO routes that also use `GetContainingIndexForDateTimeIndex`)? Surface any you find.
7. Did the prior diagnosis (`DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md`) make any defensible claims the new audit dismissed too quickly? Specifically: was the day-type-event opening_type missing-field really cosmetic, or does it affect S2 detector gating?
8. The audit's spec-vs-impl deltas D-1 (lunch skip) and D-2 (FOMC) are listed as LOW severity. For a pre-LIVE futures system, do you agree?
9. Look at `backend/v9/systems/woodies/pattern_dispatcher.py` `min_r_t1_threshold = 0.0`. Does running shadow with 0.0 and going LIVE with ≥1.0 require any test surface that's currently missing?
10. **The single most important question:** if you had to bet, is the headline root-cause hypothesis in §6 of the audit (DLL frozen-tail → backend uses frozen → sizing rejects) **the right primary cause**, or is there a more parsimonious explanation that fits all the evidence (12+ signals, frozen 7-field tail, +1h ts drift, 0 fires)?

## §E — What NOT to do

- **Do not propose fixes.** No diffs, no patches, no recommended code changes. Confirm or refute only.
- **Do not assume the audit's tables are correct.** Re-derive aux_count yourself, re-read the DLL macro yourself, re-check the spec yourself.
- **Do not opine on operational/process questions** ("CC should…"). Stick to code+spec evidence.
- **Do not add new pattern designs or new study definitions.** The 9 patterns and 11 studies are LOCKED.

## §F — Output format

Produce a single Markdown document with these sections:

1. **Headline verdict** (one paragraph): does the new audit's headline ("data-integrity bug, not logic bug, primary cause = DLL frozen-tail") hold up?
2. **Per-claim verdicts** (Claim 1 through Claim 7 from §C, each: CONFIRMED / REFUTED / PARTIAL, with file:line citations)
3. **Per-question answers** (§D 1-10)
4. **New gaps the audit missed** (anything not surfaced in either prior report)
5. **Pre-LIVE blockers** (your independent ranking, top 3)
6. **What you couldn't verify** without live system access (be honest)

Keep the total under ~3,000 words. Cite file:line for every claim. If the attached files don't contain enough to answer a question, say "INSUFFICIENT EVIDENCE — would need X" rather than guessing.

--- END PROMPT ---
