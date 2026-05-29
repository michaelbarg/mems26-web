# MEGA PROMPT — Claude Code Audit + Consult + Conditional Implementation
## IB Ground-Truth Divergence & W-10 TimeStop Restoration · 2026-05-28
## REVISED 2026-05-28 EVENING (post-Michael decision)

**Author of handoff:** Cursor agent (Claude Opus 4.7)
**Owner (CC):** Claude Code
**Mode:** **Phase 1 = AUDIT (read-only) → Phase 2 = CONSULT (push back / agree) → Phase 3 = IMPLEMENT (only after Michael green-lights based on your consultation)**
**Severity:** 🔴 LIVE blocker family — IB data integrity + trade-lifecycle correctness
**Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc` applies in full. Diagnose first, fix second. Smallest correct change. No silent failures.

---

## §0a · MICHAEL DECISIONS — 2026-05-28 EVENING (AUTHORITATIVE — supersedes anything below)

These three decisions OVERRIDE every contradicting paragraph in this prompt
and in `CC_MEGA_PROMPT_7_FIXES_2026-05-28.md`. CC MUST follow them.

1. **IB source = Sierra Initial Balance Study ONLY.** Bars-derived synthesis
   is forbidden. Delete `_ib_from_bars()` (`backend/v9/api/v9/tpo_routes.py`,
   verify by symbol — line drift expected; range was `:322-356` at prompt
   author time). When Sierra reports `ib.found=false`, propagate
   `ib_high=None, ib_low=None, ib_source="missing"` downstream. Michael's
   earlier same-day approval at `tpo_routes.py:325-330` (commit comment
   *"Restored with Michael's explicit approval (2026-05-28 18:31 IDT)"*)
   is **REVOKED 2026-05-28 EVENING**. Record the revocation in
   `docs/reports/AMENDMENTS_LOG.md` with timestamp + reason before deleting
   the function. Do not delete silently.

2. **W-10 TimeStopEnforcer is the SOLE TIME_STOP authority — fixed in code,
   NOT disabled via YAML.** This REVERSES the morning Option B decision
   (subagent `d954ada6`) that disabled W-10 via `time_stop_minutes: null`.
   The new authoritative path:
   - Re-enable YAML: `time_stop_minutes: 90` (Registry #11 — 90min flat,
     same limit for ALL patterns — TREND_DD/Variation/Normal/Neutral/etc).
   - Fix Bug A in code: `_bar_count` MUST count closed 5-min bars only,
     not bridge pushes (verify `woodies_system.py` by symbol — was `:201`
     at prompt author time, current actual line `:204`).
   - Add Fix #5: set `exit_price = self._closes[-1]` BEFORE
     `tm.close_trade(int(trade_id), "TIME_STOP")` in
     `woodies_system._check_time_stops()` (verify by symbol — was `:556`
     at prompt author time, current actual line `:573`).
   - **REMOVE Layer 4 completely**: delete `TIME_STOP_BY_DAY_TYPE` table
     AND the time-based exit block AND `_check_time_stop` method from
     `backend/v9/services/trade_manager/bar_level_detector.py`. Stop/Target
     hit logic in the same file (lines `~86-114` actual) STAYS. Only the
     TIME_STOP plumbing is removed.

3. **Cite-by-symbol discipline.** Every line number in this prompt was
   accurate at author time but has drifted (verified Cursor 2026-05-28
   evening: most cites are off by 1–17 lines). Locate every target by
   `rg -n "<symbol>" <file>` BEFORE editing. If the symbol is missing,
   STOP — the fix may already be landed or the file moved.

The §0 TL;DR below was authored before these decisions. Read it for
historical context but defer to §0a on every conflict.

---

## §0b · TL;DR for CC (HISTORICAL — superseded where it contradicts §0a)

Two subagents ran today AFTER the S4 first-fire and the 5 trade-lifecycle bugs surfaced:

1. **TIME_STOP — IMPLEMENTED** (subagent `d954ada6`): Michael chose Option B → Woodies-side W-10 `TimeStopEnforcer` disabled via YAML kill switch (`time_stop_minutes: null`). Constitution V3 Layer 4 (`bar_level_detector._check_time_stop` + `TIME_STOP_BY_DAY_TYPE`) is the sole TIME_STOP authority. **Bugs A and D from `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` are now moot.** Code, tests, and reports all updated. **Awaits backend restart to activate.**

   **§0a OVERRIDE: Option B is REVERSED. W-10 is sole authority. Layer 4 is removed. Bugs A and D are NOT moot — they must be fixed in code.**

2. **IB GROUND TRUTH — DIAGNOSED ONLY** (subagent `ece40e5e`): 4 independent bugs identified that explain why three separate stores in our system show three different wrong IB values, none of which match Sierra UI (7574 / 7525.5). Report: `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md`. **No code patched. 5 ranked fixes proposed.**

   **§0a OVERRIDE: Bug #2 fix is "delete `_ib_from_bars()`" — no env-var gating, no fallback path.**

**Your job, CC:** Audit both subagents' work independently. Push back on anything you disagree with. Only AFTER Michael green-lights based on your consultation, implement the agreed fixes. Do NOT silently adopt the proposed diffs.

---

## §1 · Required reading (before any audit step)

### Pre-LIVE discipline
1. `.cursor/rules/mems26-pre-live-protocol.mdc` — 4-step verification + Mistakes Log.
2. `CLAUDE.md` — source-of-truth rules + LaunchAgent stability.

### Today's primary artifacts
3. `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` — full IB diagnosis (§0–§8). **This is your main audit target for IB.**
4. `docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — your own earlier diagnosis of the 5 trade-lifecycle bugs (A–E).
5. `docs/reports/AMENDMENTS_LOG.md` § `2026-05-28 · W-10 TimeStopEnforcer disabled (Option B)` — the W-10 change description.
6. `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — rows #14–#18 (post-S4 trade lifecycle), row #14 and #17 marked ✅ RESOLVED.
7. `docs/plans/STATUS_BOARD.md` — today's 1-line top entries.

### Code under audit
8. `backend/v9/systems/woodies/config/dispatcher_config.yaml` — YAML state after W-10 flip.
9. `backend/v9/systems/woodies/time_stop.py` — kill switch at line 71.
10. `backend/v9/systems/woodies/woodies_system.py` — comments at ~line 96 and ~line 533. `_bar_count++` at line 201 (latent Bug A).
11. `backend/v9/services/trade_manager/bar_level_detector.py` — the surviving TIME_STOP authority. Layer 4 path at lines 117–124.
12. `backend/v9/api/v9/tpo_routes.py:359-396` — the `_normalize_sierra_tpo` function with `_ib_from_bars()` synthesis (Bug #2).
13. `backend/v9/systems/day_type/state_machine.py:413-427` — `_stage_a3` cumulative min/max (Bug #3).
14. `backend/v9/api/v9/day_type_seed.py:36-130` — `maybe_seed_ib_from_tpo` (Bug #4).
15. `backend/v9/systems/tpo/tpo_system.py:363-455` — `_update_ib` + `_persist_ib_to_session`.
16. `sc_study/MES_AI_DataExport.cpp:717-730` — DLL IB read (Bug #1).
17. `backend/main.py:181-306` — `_day_type_on_bar` (IB flow into state machine).

### New regression tests added by the W-10 subagent (audit these too)
18. `tests/v9/systems/woodies/test_w10_time_stop_disabled.py` (4 tests, NEW).
19. `tests/v9/services/trade_manager/test_layer4_time_stop_authority.py` (2 tests, NEW).
20. `tests/v9/systems/test_time_stop.py` — 6 tests now `@pytest.mark.skip`.
21. `tests/v9/systems/test_woodies_rth_gate.py` — 1 test now `@pytest.mark.skip`.

---

## §2 · Phase 1 — AUDIT (read-only, do NOT patch)

For each audit subject, your output (Phase 2 consultation) must contain:

- **(a) Confirmed?** — code + DB + log evidence the subagent's claim is correct, OR falsified.
- **(b) Pushback** — anything you disagree with, with specific file:line + reasoning.
- **(c) Missed something?** — gaps the subagent did not address.
- **(d) Spec authority verification** — does this match Constitution V3 / Registry / D-094 / CLAUDE.md?
- **(e) Risk classification** — re-rank if you disagree with the subagent's HIGH/MED/LOW assessment.

### Audit 2.1 — W-10 TimeStopEnforcer RESTORATION (per §0a decision #2)

**This audit subject CHANGED 2026-05-28 evening.** Michael REVERSED the
morning Option B (W-10 disable). New target state:
- W-10 YAML re-enabled to `time_stop_minutes: 90`.
- Bug A fixed (`_bar_count` per closed bar, not per push).
- Fix #5 added (`exit_price = self._closes[-1]` before close).
- Layer 4 fully removed.

Phase 1 audit verifies these CLAIMS about the CURRENT (Option B) state of
the repo SO that Phase 3 implementation can correctly un-do it:

| # | Claim about CURRENT (pre-restoration) state | How to verify |
|---|---|---|
| 1 | `dispatcher_config.yaml` currently has `time_stop_minutes: null` (Option B kill switch). Phase 3 will flip this back to `90`. | Read the YAML directly. |
| 2 | `load_time_stop_config()` correctly coerces `None`/falsy to `None`. After Phase 3 flip, with `time_stop_minutes: 90`, the function must return `90`. | Read `time_stop.py` `load_time_stop_config()` body — locate by symbol, line drift expected (was `:71` and `:134-135` at author time). |
| 3 | `woodies_system.py` has the kill-switch comment block at `_check_time_stops()`. The comment must be REMOVED in Phase 3 and replaced with a reference to AMENDMENTS_LOG entry for the reversal. | `git log -p backend/v9/systems/woodies/woodies_system.py` — find the most recent change to the docstring; Phase 3 reverts that docstring update. |
| 4 | The 6 new tests (`test_w10_time_stop_disabled.py` + `test_layer4_time_stop_authority.py`) currently pass under Option B. Phase 3 will INVERT or DELETE them: `test_w10_time_stop_disabled.py` becomes `test_w10_time_stop_enabled.py` asserting YAML=90 and `enforcer.fired=True at bars_open >= 18`. `test_layer4_time_stop_authority.py` is DELETED (Layer 4 is removed). | `pytest tests/v9/systems/woodies/test_w10_time_stop_disabled.py tests/v9/services/trade_manager/test_layer4_time_stop_authority.py -v` |
| 5 | The 7 currently-skipped tests under `tests/v9/systems/test_time_stop.py` and `tests/v9/systems/test_woodies_rth_gate.py` will be UN-SKIPPED in Phase 3. Verify the skip reasons all cite "2026-05-28 Option B" so the reversal is traceable. | Read each `@pytest.mark.skip` reason text. |
| 6 | Bug A (`_bar_count++` per push) IS still in the code (the morning fix only disabled the consequence, not the bug). After Phase 3 it MUST count closed-bar-ts changes only. | Read `woodies_system.py` near `process_bar()` start — locate by `rg -n "_bar_count \+= 1" backend/v9/systems/woodies/woodies_system.py`. Cited as `:201`/`:204`; trust the rg output, not the cite. |
| 7 | Bug D (TIME_STOP without `exit_price`) IS still in the code at `_check_time_stops()`. The current call is `tm.close_trade(int(trade_id), "TIME_STOP")` with no exit_price set. Phase 3 must add `exit_price = self._closes[-1]` BEFORE that call. | Locate by `rg -n 'close_trade\(int\(trade_id\), "TIME_STOP"\)' backend/v9/systems/woodies/woodies_system.py`. Cited as `:556`/`:573`. |
| 8 | Layer 4 `bar_level_detector.py` has `TIME_STOP_BY_DAY_TYPE` table at `~:21-29`, the time-based exit block in `on_bar` at `~:117-124`, and `_check_time_stop` method at `~:131-165`. Phase 3 DELETES all three regions but KEEPS lines `~:86-114` (stop/target hit logic). | Read `bar_level_detector.py` end-to-end. Locate by symbol: `rg -n "TIME_STOP_BY_DAY_TYPE\|_check_time_stop\|on_stop_hit" backend/v9/services/trade_manager/bar_level_detector.py`. |
| 9 | Spec authority for "W-10 90min flat" is Registry #11. Locate the row in `docs/spec_authority/...` registry file (search for "Registry #11" / "time stop" / "W-10"). | `rg -n "Registry.*11\|W-10\|time.*stop.*90" docs/spec_authority/`. Paste the EXACT cited text into consultation doc — do not paraphrase. |
| 10 | Constitution V3 (`docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt`) Layer 4 description IS the source of `TIME_STOP_BY_DAY_TYPE`. With Layer 4 removed, that paragraph must either be marked superseded or amended. | Read V3, search "Layer 4". Phase 3 either updates V3 spec OR adds a constitution amendment doc citing the Registry #11 → V3 reconciliation. STOP and ask Michael which path he wants. |
| 11 | The currently-active YAML kill switch comment at `dispatcher_config.yaml:32-41` cites the Option B decision. Phase 3 replaces this comment block with a "REVERSED 2026-05-28 EVENING — see AMENDMENTS_LOG" note. | Read the YAML comment block. |

Pushback opportunities — examples to consider:

- After removing Layer 4, is there any OTHER caller of `bar_level_detector._check_time_stop`? (`rg -n "_check_time_stop" backend/`). If yes — STOP, removal is not isolated.
- After re-enabling W-10, is there any code path where `_check_time_stops()` runs WITHOUT `_gateway` wired? (`rg -n "set_gateway\|_gateway" backend/v9/systems/woodies/`). The Fix #5 patch must null-guard this.
- If `_closes` list is empty when Fix #5 fires (defensive question), what should `exit_price` be? Recommend: skip the close (do not pass NULL → pnl=0 regression) and log WARNING. Phase 3 must include this guard.
- Spec contradiction: V3 Layer 4 (per-Day-Type minutes) and Registry #11 (90min flat) are incompatible. Michael chose Registry #11. Document the V3 deviation in `docs/reports/AMENDMENTS_LOG.md` AND in a constitution amendment doc — do not edit V3 directly without his sign-off.
- When W-10 is re-enabled, will `_check_time_stops()` see `entry_bar_count` populated correctly in `_open_fire_records`? Verify the entry-side path that adds to that dict was not broken by the morning Option B work.

### Audit 2.2 — IB ground-truth diagnosis (4 root causes)

Re-verify EACH of the 4 root causes the subagent identified. Do NOT trust the diagnosis text alone — query the live system.

#### Bug #1 — DLL silent IB
**Subagent claim:** `sc_study/MES_AI_DataExport.cpp:717-730` reads ACSIL idx 6 / 8 at `sc.Index` only; this returns 0 post-lock; `ib_found=false` flows downstream. Likely root cause: wrong subgraph indices OR "Extend Lines Forward = No" in the Sierra IB Study.

**Verify:**
- Read the cited lines verbatim.
- `python3 -c "import json,os; print(json.dumps(json.load(open(os.path.expanduser('~/SierraChart_Data/v9_export/tpo.json')))['ib'], indent=2))"` — confirm `ib.found=false, high=0, low=0`.
- Check `docs/forensics/SIERRA_UI_EVIDENCE_2026-05-25.md` (or whatever the file is named) — does the prior forensic mapping cite SG7=High and SG9=Low (which would be ACSIL idx 6 and 8)? Or do those refer to something else?
- Cross-check: what did `tpo.json` show during 09:30-10:30 ET today (the conversation summary says `ib_high=7543.75, ib_low=7522.00`)? Neither matches Sierra UI's 7574/7525.5 nor IB Mid `(7574+7525.5)/2 = 7549.75`. If those numbers truly came out of the DLL during RTH, what subgraph could produce 7543.75? Check Sierra IB Study documentation for SG indices and try mapping. Note this is FORENSIC — do not change the DLL yet.

**Pushback / consult:** is the "wrong subgraphs" hypothesis stronger than "Extend Lines Forward disabled"? Both produce the same observable symptom. The discriminator is what `tpo.json` shows during the IB window itself (when the study is actively building).

#### Bug #2 — Backend bars-synthesis with `ib_found=true` lie
**Subagent claim:** `backend/v9/api/v9/tpo_routes.py:380-396` (`_normalize_sierra_tpo`) synthesises IB from `MAX(high)/MIN(low)` over 09:30-10:30 ET bars when DLL is silent, and **flags `ib_found=ib_locked=True`** so every downstream consumer trusts it. Produces 7583.5 / 7575.0.

**Verify (cite by symbol — line drift expected):**
- `rg -n "def _normalize_sierra_tpo\|def _ib_from_bars" backend/v9/api/v9/tpo_routes.py` to find current line numbers.
- Read both bodies verbatim. Author-time cites: `_normalize_sierra_tpo` at `:359`, `_ib_from_bars` at `:322-356`. Cursor-verified 2026-05-28 evening: still accurate.
- Read the comment block at `_ib_from_bars` docstring — note the `"Restored with Michael's explicit approval (2026-05-28 18:31 IDT)"` text. **§0a decision #1 REVOKES this approval.** That comment must be removed in Phase 3 along with the function body.
- `curl -s http://localhost:8000/api/v9/tpo/current | jq '{ib_high,ib_low,ib_source,ib_locked}'` — confirm the response currently shows synthetic value and `ib_source="v9_bars_5min_09_30_10_30_ET"`.
- Verify the violation against `CLAUDE.md`'s explicit rule: *"Forbidden without explicit approval: inventing proj_*, synthetic time grids, or rolling-window price levels when the DLL omits them."* — this synthesis falls under "rolling-window price levels".

**Decision (per §0a #1) — NO push-back accepted on this point:**
- DELETE `_ib_from_bars()` body and signature entirely.
- DELETE the call site in `_normalize_sierra_tpo` `else:` branch — replace with:
    ```python
    ib_high = ib_low = ib_mid = None
    ib_source = "missing"
    ```
- `ib_found` STAYS `False` (no synthesis can flip it to True).
- DELETE the `ib_source` enum value `"v9_bars_5min_09_30_10_30_ET"` from any
  consumer that switches on it (e.g. `key_levels_routes.py`).
- BEFORE the deletion commit, add an entry to `docs/reports/AMENDMENTS_LOG.md`:
    ```
    2026-05-28 EVENING · IB bars-synthesis revocation
    Reverses the 18:31 IDT same-day approval at tpo_routes.py:325-330.
    Reason: source-of-truth discipline (CLAUDE.md). When Sierra Study
    is silent we propagate "missing" to consumers, not a synthetic value.
    Affected paths: /api/v9/tpo/current, /api/v9/key_levels, day_type seed,
    state_machine A3.
    ```

**Pushback you MAY raise:** the consumer-side fail-mode chain. Verify each
of these handles `ib_high=None` cleanly BEFORE the delete commit lands:
1. `/api/v9/tpo/current` response — UI strip behaviour with `ib_found=False`.
2. `/api/v9/key_levels.previous_day.ib_*` and `today.ib_*` — strip renders "—" cleanly.
3. `day_type_seed.maybe_seed_ib_from_tpo` — `:73` already returns False on `None`. Re-confirm.
4. `state_machine._stage_a3` lines `~:424-427` — already guards on `bar.ib_high is not None`. Re-confirm.
5. `main.py:_day_type_on_bar` lines `~:200-204` — already guards on `_sierra_tpo.get("ib_found")`. Re-confirm.

If any consumer crashes on `None`, the delete commit MUST also include a
guard for that consumer in the same commit. Do not split.

#### Bug #3 — State machine cumulative min/max
**Subagent claim:** `state_machine.py:413-427` (`_stage_a3`) does `self.ib_high = max(self.ib_high, bar.ib_high)` and `self.ib_low = min(self.ib_low, bar.ib_low)` cumulatively across every A3 bar, latching the lowest synthetic `ib_low` ever observed.

**Verify:**
- Read `_stage_a3` body verbatim. Confirm the `max`/`min` lines exist as cited.
- Mentally simulate: bar 1 carries (h=7583.5, l=7575.0); bar 2 carries (h=7583.5, l=7553.25 — from a wider synthetic window). After bar 2: `self.ib_low = min(7575, 7553.25) = 7553.25`. Matches DB.
- Cross-check `_stage_a4`/`_stage_b*` to confirm IB is **NOT** re-read post-A3 (so the latched bad value sticks).

**Pushback / consult:** The subagent's proposed Fix #3 is `self.ib_high = bar.ib_high` / `self.ib_low = bar.ib_low` (verbatim adopt, no min/max). Is this correct per Constitution V3, OR should we keep min/max for the A3 evolving window and only adopt verbatim AT lock (A4)? The cleaner semantic is "Sierra's IB study is the aggregator; we never aggregate", which supports verbatim. Agree?

#### Bug #4 — Seed accepts synthesised IB
**Subagent claim:** `day_type_seed.py:70` guards on `tpo_ib_locked` boolean. Bug #2 sets `ib_locked=True` on synthesis → seed adopts synthetic IB on restart → originally-correct (7574 / 7525.5) destroyed.

**Verify:**
- Read `maybe_seed_ib_from_tpo` body.
- Check `v9_day_type_state` table for the MEDIUM→WIDE transition timestamp the subagent cites (between 14:30 and 17:00 UTC). `sqlite3 data/mems26_local.db "SELECT timestamp, ib_width_class FROM v9_day_type_state WHERE date(timestamp)='2026-05-28' AND ib_width_class IS NOT NULL ORDER BY timestamp" | uniq -f1 | head -20`.
- If the transition is real, confirm a backend restart happened between those timestamps (check `/tmp/backend.log` or process start time).

**Pushback / consult:** Fix #4 plumbing requires `tpo_ib_source` to flow through `main.py:_day_type_on_bar` into the seed function. Subagent's diff suggests reading `_sierra_tpo.get("ib_source")` and passing as parameter. Is this the cleanest path, or should the source field be carried on the `BarInput` model itself?

#### Bug #5 — `_persist_ib_to_session` no COALESCE (latent)
**Subagent claim:** Once Bug #2 is fixed, a transient Sierra silence will fall through with `self.ib_high/low = None`. Currently guarded by `if not sierra.get("ib_found"): return` at line 387, but defense-in-depth COALESCE would help.

**Verify:**
- Read `_persist_ib_to_session` body.
- Check `_update_ib` line 387 guard.

**Pushback / consult:** Subagent ranks this LOW priority (defer 24h). Agree, or should it ship in the same batch as Fix #2 to avoid a follow-up window?

---

## §3 · Phase 2 — CONSULT with Michael (after audit complete)

For each finding above, deliver a CONSULTATION DOC at:
`docs/reports/CC_AUDIT_IB_TIMESTOP_CONSULTATION_2026-05-28.md`

Structure:

```
§0 · Audit summary table
| Subject | Subagent claim | CC verdict | Confidence |
|---|---|---|---|
| W-10 disable (claim 1-11) | … | CONFIRMED / FALSIFIED / PARTIAL | HIGH/MED/LOW |
| IB Bug #1 (DLL) | … | … | … |
| IB Bug #2 (synthesis) | … | … | … |
| IB Bug #3 (min/max) | … | … | … |
| IB Bug #4 (seed) | … | … | … |
| IB Bug #5 (COALESCE) | … | … | … |

§1 · Pushback / disagreement
- One bullet per area where you disagree with the subagent.
- Include alternative root cause hypotheses or alternative fix sketches.

§2 · Missed concerns
- Anything the subagent did not address. Examples:
  - "What about `previous_session_ib` in `tpo.json`? Does it use the same broken DLL path?"
  - "Does the synthesis bug also affect /api/v9/key_levels.previous_day.ib_*?"
  - "If we remove Path A synthesis, what is the UI graceful-degradation path?"

§3 · Spec authority cross-check
- Confirm or falsify Constitution V3 Layer 4 is the canonical TIME_STOP authority.
- Confirm or falsify Sierra's IB Study is the canonical IB source per CLAUDE.md.

§4 · Recommended fix order (your version)
- Re-rank the 5 IB fixes if you disagree with the subagent.
- Include risk vs. blast radius.

§5 · Open questions for Michael
- Specifically anything that requires his Sierra UI interaction (e.g. Subgraphs screenshot).
- Anything that requires a Sierra DLL rebuild + Remote Build deploy.
- Anything that requires backend restart timing.
```

**Then STOP and report.** Do not patch anything until Michael responds to your consultation doc.

---

## §4 · Phase 3 — IMPLEMENT (only after Michael green-lights based on §3)

Phase 3 is now organised in TWO backend packages plus the deferred DLL
package. Implement IN ORDER A1 → A2 → B (B is gated on Sierra UI access).

### Package A1 — IB cleanup (delete bars-synthesis)

Per §0a decision #1. This package lands FIRST so Sierra-Study-silence
propagates honestly through every consumer before W-10 is restored.

1. **Fix #2 (revised)** — Remove `_ib_from_bars()` synthesis from `_normalize_sierra_tpo`.
   - File: `backend/v9/api/v9/tpo_routes.py:380-396`.
   - Diff sketch (subject to your consultation):
     ```python
     ib_found = bool(ib.get("found"))
     if ib_found:
         ib_high, ib_low, ib_mid = ib.get("high"), ib.get("low"), ib.get("mid")
         ib_source = "sierra_live"
     else:
         ib_high = ib_low = ib_mid = None
         ib_source = "missing"
     ```
   - Delete `_ib_from_bars()` function and its caller path.
   - Update `key_levels_routes.py` `sources.ib` string accordingly.
   - **Regression test:** `tests/v9/api/test_tpo_routes_no_ib_synthesis.py` — patch `_load_sierra_tpo` to `ib.found=false`, assert response shows `ib_high=None, ib_low=None, ib_found=False, ib_source="missing"`.

2. **Fix #4** — `maybe_seed_ib_from_tpo` rejects non-`sierra_live` source.
   - File: `backend/v9/api/v9/day_type_seed.py:70` + parameter plumbing in `main.py:_day_type_on_bar`.
   - **Regression test:** `tests/v9/api/test_day_type_seed_rejects_synthetic.py`.

3. **Fix #3** — State machine adopts Sierra IB verbatim.
   - File: `backend/v9/systems/day_type/state_machine.py:413-427`.
   - **Regression test:** `tests/v9/systems/test_day_type_ib_no_accumulate.py`.

4. **Fix #5 (optional, defer-eligible)** — COALESCE on `_persist_ib_to_session`.
   - File: `backend/v9/systems/tpo/tpo_system.py:444-451`.

5. **One-shot manual UPDATE** (after Fix #2 lands and backend restarts):
   ```sql
   UPDATE v9_day_type_history
   SET ib_high = NULL, ib_low = NULL, ib_width = NULL, ib_width_class = NULL
   WHERE date = '2026-05-28';
   ```
   This clears the stuck synthetic IB. Engine won't naturally revisit IB until tomorrow's session. Document this in the AMENDMENTS_LOG entry. **Confirm the exact SQL with Michael before running.**

### Package A2 — W-10 restoration (per §0a decision #2)

This package REVERSES the morning Option B kill switch. Implement only AFTER
Package A1 is green and `/api/v9/tpo/current` shows `ib_source="missing"`
when Sierra is silent (so we know the upstream is honest before W-10 starts
firing TIME_STOP closes).

6. **AMENDMENTS_LOG entry FIRST** — record the Option B reversal:
   ```
   2026-05-28 EVENING · W-10 Option B REVERSED
   This morning's "Layer 4 sole authority" decision is reversed.
   Authority: Registry #11 (90min flat for all 9 patterns).
   Layer 4 (TIME_STOP_BY_DAY_TYPE + _check_time_stop in
   bar_level_detector.py) is REMOVED. The Bug A (per-push counter)
   and Bug D (exit_price=NULL) latent bugs are fixed in code rather
   than worked-around via YAML kill switch.
   Constitution V3 deviation: V3 §"Layer 4" describes per-Day-Type
   limits. This deviation is documented here pending V3 amendment
   doc (separate item — see consultation §3 spec authority section).
   ```

7. **W-10 Bug A fix** — `_bar_count` per closed bar, not per push.
   - File: `backend/v9/systems/woodies/woodies_system.py`.
   - Locate by symbol: `rg -n "_bar_count \+= 1" backend/v9/systems/woodies/woodies_system.py`. Author cites `:201`/`:204`.
   - Diff sketch:
     ```python
     # In __init__ near self._bar_count = 0:
     self._last_bar_ts_for_count: Optional[float] = None

     # In process_bar(), replace:
     self._bar_count += 1

     # With:
     _bar_ts = bar.get("ts")
     if _bar_ts is not None and _bar_ts != self._last_bar_ts_for_count:
         self._bar_count += 1
         self._last_bar_ts_for_count = _bar_ts
     ```
   - **Regression test:** `tests/v9/systems/woodies/test_w10_bar_count_per_close.py`
     — push the SAME bar 5× (same `ts`); assert `_bar_count` increments by 1.
     Then push a NEW `ts`; assert `_bar_count` increments by 1 more.

8. **W-10 Fix #5** — `exit_price` set before `close_trade("TIME_STOP")`.
   - File: same `woodies_system.py` `_check_time_stops()` method.
   - Locate by `rg -n 'close_trade\(int\(trade_id\), "TIME_STOP"\)' backend/v9/systems/woodies/woodies_system.py`. Author cites `:556`/`:573`.
   - Diff sketch:
     ```python
     # BEFORE close_trade call, add (with null guards):
     if tm is not None and self._closes:
         try:
             trade_obj = tm._get_trade(int(trade_id))
             if trade_obj is not None:
                 trade_obj.exit_price = float(self._closes[-1])
         except Exception as exc:
             logger.warning(
                 "[woodies] TIME_STOP exit_price set failed for trade %s: %s",
                 trade_id, exc,
             )
     # If self._closes is empty, SKIP close (do not pass NULL exit_price)
     # and log WARNING — this is the defensive guard required by audit
     # subject 2.1 pushback.
     ```
   - **Regression test:** `tests/v9/systems/woodies/test_w10_time_stop_sets_exit_price.py`
     — wire a fake gateway/TM, populate `_closes=[100.5]`, force
     `bars_open >= limit_bars`; assert `exit_price=100.5` BEFORE
     `close_trade` is called. Add a second test: `_closes=[]` →
     `close_trade` is NOT called and a WARNING is logged.

9. **YAML re-enable** — `dispatcher_config.yaml`.
   - Replace `time_stop_minutes: null` with `time_stop_minutes: 90`.
   - Replace the kill-switch comment block (currently lines `~32-41`) with:
     ```yaml
     # W-10 Time Stop — Registry #11 LIVE blocker
     # Sole TIME_STOP authority. 90min flat across all 9 Woodies patterns.
     # 2026-05-28 EVENING (M.B.): RESTORED post Option B reversal. Layer 4
     # (TIME_STOP_BY_DAY_TYPE) was removed in the same commit. Bug A
     # (per-push counter) and Bug D (exit_price=NULL) are fixed in code,
     # not band-aided. See AMENDMENTS_LOG entry "W-10 Option B REVERSED".
     ```

10. **Layer 4 removal** — `backend/v9/services/trade_manager/bar_level_detector.py`.
    - DELETE `TIME_STOP_BY_DAY_TYPE` constant (currently `:21-29`).
    - DELETE the time-based exit block in `on_bar` (currently `:116-124`).
    - DELETE `_check_time_stop` method (currently `:131-165`).
    - KEEP everything else (subscribe, parse_ts, stop/target hit logic).
    - **Regression test:** `tests/v9/services/trade_manager/test_bar_level_detector_no_time_stop.py`
      — instantiate, push a bar at 10:00 ET with an open trade entered at
      08:00 ET, assert `close_trade` is NEVER called (TIME_STOP authority
      moved to Woodies side). Existing stop/target tests must still pass.

11. **Test cleanup** — un-skip and invert.
    - `tests/v9/systems/woodies/test_w10_time_stop_disabled.py` →
      RENAME to `test_w10_time_stop_enabled.py`. Invert assertions:
      YAML `time_stop_minutes == 90`; enforcer fires at `bars_open >= 18`.
    - `tests/v9/services/trade_manager/test_layer4_time_stop_authority.py` →
      DELETE (Layer 4 is removed). The `test_day_type_time_stop_table_is_complete`
      test is moot.
    - `tests/v9/systems/test_time_stop.py` → un-skip the 6 currently-skipped
      tests. Verify each still passes against the restored 90min YAML.
    - `tests/v9/systems/test_woodies_rth_gate.py` → un-skip the 1 currently-skipped test.

### Package B — DLL (blocked on Sierra UI interaction)

6. **Fix #1** — DLL: confirm correct subgraph indices + `_v9_last_nonzero` persistent lookup.
   - File: `sc_study/MES_AI_DataExport.cpp:717-730`.
   - **Prerequisite (Michael):** Sierra UI screenshot of "Initial Balance Study → Subgraphs" tab showing which numbered SG currently displays 7574.00 and which 7525.50. Plus the Sierra Chart time zone (CT vs ET — needed to interpret the 09:30-10:29 window correctly).
   - **Build & deploy:** `./scripts/build_monolithic_cpp.sh --deploy` per `docs/runbooks/SIERRA_DLL_OPS.md`. Sierra UI Remote Build + study reload.
   - **Regression test:** `tests/v9/sierra/test_tpo_export_ib.py` — load a recorded post-lock `tpo.json` fixture and assert `ib.found=True, ib.high=7574.0, ib.low=7525.5`.

### Per-fix UAT (4 axes, mandatory per pre-LIVE protocol)

After EACH fix lands and backend restarts:

- **Axis 1 Quality:** the specific bug condition is gone (e.g. `bad_count=0`, `ib_source != "v9_bars_5min_…"`).
- **Axis 2 Recency:** the endpoint's `latest_ts` equals `MAX(ts)` in DB.
- **Axis 3 Cardinality:** `len(rows) == requested_limit` — no silent truncation (P27.5a regression class).
- **Axis 4 Latency:** response time under documented threshold.

### Backend restart

When Package A is fully landed:
- Coordinate with Michael for restart timing (do NOT restart from CC if Michael is mid-trade).
- After restart, run the live UAT for `/api/v9/tpo/current`, `/api/v9/key_levels`, `/api/v9/day_type/v9/current`.
- Update `docs/plans/STATUS_BOARD.md` with results.

---

## §5 · Test results from today (subagent claims to verify)

The W-10 subagent reported these numbers. Re-run yourself and confirm:

| Scope | Reported | Verify with |
|---|---|---|
| `test_w10_time_stop_disabled.py` + `test_layer4_time_stop_authority.py` | 6 passed / 0 failed | `pytest <both paths> -v` |
| Full woodies-adjacent (woodies/, test_time_stop, test_woodies_rth_gate, test_atr_stop, test_pattern_dispatcher, test_anti_patterns, test_zlr_stage1_completeness, test_a1_strategic_gate, test_r_t1_emission, test_hfe, trade_manager/) | 293 passed / 7 skipped / 0 failed | `pytest <scope> -q` |
| Consolidated TIME_STOP-relevant scope | 51 passed / 7 skipped | `pytest tests/v9/systems/test_time_stop.py tests/v9/systems/woodies/test_w10_time_stop_disabled.py tests/v9/services/trade_manager/test_layer4_time_stop_authority.py tests/v9/systems/test_woodies_rth_gate.py -v` |
| Pre-existing failures (unrelated, ALREADY tracked as OPEN_ITEMS #5) | 3 failed: `TestAcceptSetup::test_invalid_firing_system`, `TestDBPersistence::test_get_active_trades`, `TestDBPersistence::test_get_active_trades_by_mode` | `pytest tests/v9/services/test_trade_manager.py -q` |

If your numbers differ, **report the discrepancy in §0 of your consultation doc** before proceeding.

---

## §6 · Trade-lifecycle bugs status (post §0a Option B REVERSAL)

| # | Bug | Status (revised 2026-05-28 evening) | Owner |
|---|---|---|---|
| A | TIME_STOP fires after 52s (push-count counter) | 🔴 OPEN — Package A2 step 7 fixes in code (`_bar_count` per-closed-bar). Was marked MOOT this morning; reversed. | CC |
| B | Demo stop "inverted" on LONG (#156) | 🟡 OPEN — CC classified as Smart BE+1T working as designed; verify post-restart with clean LONG fire | CC |
| C | `t1_hit_ts == stop_hit_ts` on wide-range bar | 🟢 OPEN — needs priority tightening at `bar_level_detector.py` stop/target block (`~:88-114`). NOTE: this block STAYS after Layer 4 removal — the fix still applies. | CC |
| D | `pnl=0.0` / `exit_price=NULL` on TIME_STOP | 🔴 OPEN — Package A2 step 8 fixes in code (`exit_price = self._closes[-1]` before close). Was marked MOOT this morning; reversed. | CC |
| E | `stop_hit_ts = 09:30:00` (before entry) | 🟡 OPEN — Chicago→UTC conversion missing in `BarLevelDetector._parse_ts`. NOTE: this still applies because `_parse_ts` and the stop/target path STAY after Layer 4 removal. | CC |

Include in your consultation doc whether you agree with B/C/E remaining open and their severity tags. Bugs A and D are back to OPEN per §0a #2.

---

## §7 · Hard constraints

- **Phase 1 (Audit) is READ-ONLY.** No `git add` / `git commit` / `git restore` / file edits.
- **Phase 2 (Consult) writes only `docs/reports/CC_AUDIT_IB_TIMESTOP_CONSULTATION_2026-05-28.md`** — no code touched.
- **Phase 3 (Implement) requires Michael's explicit go-ahead** based on §3.
- **No `except Exception: pass`.** No silent error handling between now and LIVE (per CLAUDE.md).
- **No `while I'm here` refactors.** Smallest correct change.
- **Strategic stop** at any of:
  - Audit reveals a subagent claim is materially wrong (not a minor detail) — STOP and tell Michael.
  - Implementation reveals a 6th bug — STOP and write up.
  - Constitution V3 Layer 4 turns out NOT to be the TIME_STOP authority — STOP.
  - DLL audit reveals a hardware/Sierra-config issue Michael needs to resolve first — STOP.
- **Do not run** `bash scripts/start_all.sh` or any service-spawning command unless Michael explicitly asks.
- **Do not restart the backend** without coordinating with Michael (he may be mid-trade).
- **Do not touch** `~/Library/LaunchAgents/com.mems26.bridge.plist` or `CLOUD_URL` configuration.
- **Pre-LIVE Mistakes Log applies in full:**
  1. Don't slice-bug like P27.5a (`result[:limit]` instead of `result[-limit:]`).
  2. Don't propose a fix already in the code (verify with Read first).
  3. Don't trust a CC report at face value — re-verify against raw evidence.
  4. Don't promote a hypothesized fix to code before confirming the diagnosis.

---

## §8 · Deliverables

### Phase 1 + 2 (mandatory, no code)
1. `docs/reports/CC_AUDIT_IB_TIMESTOP_CONSULTATION_2026-05-28.md` — your audit + consult document per §3.
2. A one-message summary back to Cursor (this agent) and Michael with:
   - Pass/fail for each of the 11 W-10 claims in §2.1.
   - Confirmed/falsified for each of the 5 IB bugs in §2.2.
   - Your top 3 pushbacks.
   - Your re-ranked fix order.
   - Explicit list of questions for Michael.

### Phase 3 (conditional on Michael green-light)
3. Per-fix commits (or grouped if Michael prefers) with:
   - File:line diff.
   - Regression test added under `tests/v9/`.
   - Targeted pytest result.
   - UAT (4 axes) result.
4. Update `docs/reports/AMENDMENTS_LOG.md` with an `IB Backend Cleanup (Package A)` entry per fix landed.
5. Update `docs/plans/STATUS_BOARD.md` with a 1-line per fix.
6. Update `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — mark IB items as RESOLVED with citations.
7. A final report `docs/reports/IB_PACKAGE_A_LANDED_2026-05-28.md` summarising what landed, what's deferred to Package B (DLL), and what's still open.

---

## §9 · Open items for Michael (already known, do not re-litigate)

These are tracked in `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md`:

- 🔴 #1 — DLL frozen-tail bug (Woodies). Separate from this IB work.
- 🟠 #2 — `woodies_chart_routes.py:43` hardcoded `+5h` (winter bomb).
- 🟠 #3 — S2 `current_day_type=None` silent skip.
- 🟠 #4 — `/api/v9/status.day_type` reports `PENDING` while DB row is classified.
- 🟠 #5 — 11 pre-existing pytest failures.

Reference if relevant but **do not expand scope** into these in this prompt.

---

## §10 · Process discipline

Per `.cursor/rules/mems26-pre-live-protocol.mdc`:

- **One thread at a time.** Finish audit + consult before opening implementation.
- **Update reports the moment state changes.** Do not let the consultation doc go stale while implementing.
- **Strategic stops mandatory** at phase gate transitions, plan contradictions, or any change affecting trading logic.

The Cursor agent (me) keeps:
- Code reading + strategic stop/go gating.
- Verification of CC's audit against the four UAT axes.
- Routing to Michael for DLL / Sierra UI interaction.

CC (you) keeps:
- Audit execution, consultation doc, conditional implementation, regression tests, UAT, reports.

---

## Acknowledgement template (paste at top of your reply when you start)

```
Acknowledged MEGA_PROMPT_CC_AUDIT_IB_TIMESTOP_2026-05-28.md.
Phase 1 starting now (read-only audit).
ETA Phase 1+2: 45-60 min. Phase 3: gated on Michael green-light.
Pre-LIVE protocol: confirmed reading .cursor/rules/mems26-pre-live-protocol.mdc + CLAUDE.md.
```

Go.
