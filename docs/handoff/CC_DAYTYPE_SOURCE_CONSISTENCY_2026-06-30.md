# CC Handoff — Day-Type Source Consistency at Gate/Auth (blocks CONT on trend days) · I-44 / I-50 live repro

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — anti-tautological, **paste command + raw output (Rule 5)**, mandatory NOT-DONE.
**Flag:** default-OFF / SHADOW. Enabling = trading-risk-surface change → Michael sign-off.
**Read first:** `docs/SOURCE_OF_TRUTH.md`, the dead-wrapper warning in `CLAUDE.md` (§Codebase Index Protocol), I-44/I-50 in `docs/reports/MEMS26_ISSUES_REGISTER.md` + `STATUS_BOARD.md`; code: `backend/v9/systems/daytype_position_gate.py`, `services/trade_context.py::extract_g1_entry_context`, `systems/five_min/auth_table_v1.py`, the Woodies V2Sizing path.

---

## 0 · Why — today's live smoking gun (06-30, a Trend_Normal / OPEN_DRIVE day → **0 trades**)
Both **continuation** patterns (the *correct* family for a trend day) were blocked, for one root: **the gate/auth did not read the live 7-type day-type.** Raw evidence:

**day_type timeline** (`v9_day_type_state`, UTC): `UNKNOWN` until **14:00:00**, then **`Trend_Normal`** 14:00→ ; `opening_type=OPEN_DRIVE` from **13:35**.

**(a) INITIATIVE_LONG** (setup id 262) fired 14:00:00 UTC:
```
[FiveMin] FIRE: INITIATIVE LONG (conf=0.80, size=half)
[S2] T1Setup skipped: pattern=INITIATIVE_LONG day_type=UNKNOWN tier=HIGH · Auth Table SKIP
```
Root: `auth_table_v1.get_auth_cell` maps any unknown day_type → **`Neutral_Center` fallback** (L144-147), and `INITIATIVE_LONG @ Neutral_Center = SKIP` (L52). At 14:00:00 the auth read `UNKNOWN` (the value just before the resolution tick). Note `INITIATIVE_LONG @ Trend_Normal = ("FULL",3,2,1)` — it would have fired 3 contracts.

**(b) ZLR_LONG** fired 14:25:04 UTC — **25 min AFTER** day_type was already `Trend_Normal` — yet at the **same instant** two paths disagreed:
```
[V2Sizing] no auth cell for (ZLR, Trend_Normal) — using max     ← Woodies sizing read Trend_Normal (LIVE, correct)
[Gateway] BLOCKED by day-type position gate:
          balanced day (Normal) — continuation (ZLR) blocked    ← the gate read "Normal" (STALE/wrong)
```
The `daytype_position_gate` was fed `day_type="Normal"` while the live classifier **and** the sibling Woodies sizing path both had `Trend_Normal`. It blocked a CONT pattern as "balanced" **on a trend day**. This is **I-44 (day_type-source split) / I-50 (trend-source reconcile) reproduced live** — now shown to actively suppress correct trend fires.

**Conclusion:** our Stage-1 pattern-aware gate *logic* is correct (block CONT on balanced); it is being fed a **stale/wrong day_type** ("Normal") → so it blocks the right patterns on a trend day. **Do NOT revert Stage 1 — fix the day_type SOURCE.**

---

## 1 · Scope — diagnose, then fix (behind a flag, SHADOW)
**Diagnose (Rule 5 — paste the value each path returns at the same bar):**
- What `day_type` does `daytype_position_gate.decide` receive — trace `trade_context.extract_g1_entry_context` (logged "Normal"). Confirm whether it fell back to the **OLD 3-type `day_type_machine`** (→"Normal") instead of the live **7-type `classify_replay` / `app.state.day_type_machine`** (→"Trend_Normal"). Is `classify_replay` returning FORMING in that call while `v9_day_type_state` already shows Trend_Normal (two-instance / dead-wrapper split)?
- What `day_type` does the Woodies V2Sizing read (logged "Trend_Normal")? Why does it see the live value when the gate doesn't?

**Fix:**
1. **Single live source.** Make the **position gate** AND the **S2 Auth Table** read the **same canonical live 7-type** day-type used by the sizing path / `v9_day_type_state` (`app.state.day_type_machine` / `classify_replay`) — never a stale snapshot or the old 3-type engine. (SOURCE_OF_TRUTH + the dead-wrapper rule.)
2. **Pre-resolution (UNKNOWN) window.** When the 7-type is *genuinely* still FORMING/UNKNOWN pre-IB-lock **and** `OPENING_FIRE_CVD_V1` is on **and** `opening_type` is a drive (OPEN_DRIVE / OPEN_TEST_DRIVE): authorize via the **opening-type** (a provisional trend tier) instead of the `Neutral_Center → SKIP` fallback — so the Stage-0 opening fire can actually size + trade. This is the missing link between Stage 0 and the Auth Table. Fail-safe: never SIZE-UP beyond the opening-type's implied tier on uncertainty.

## 2 · Tests (anti-tautological)
1. **06-30 golden fixture (14:00–14:30):** with the fix, on the live `Trend_Normal` the position gate **ALLOWS** ZLR/INITIATIVE (CONT) and the Auth Table returns FULL/REDUCED (not SKIP). Without the fix → reproduce the block.
2. **Source equality:** assert the gate's `day_type` == `v9_day_type_state` (live) at the same bar.
3. **No Stage-1 regression:** a *real* balanced day (Normal/Neutral) still **BLOCKS** CONT.
4. **Pre-lock UNKNOWN + OPEN_DRIVE** → INITIATIVE authorized via opening-type (provisional), not SKIP; **UNKNOWN + no drive** → still conservative (no fire).
5. **Flag OFF** → byte-identical to today.

## 3 · Verification (SHADOW · Rule 5)
Enable in SHADOW; on the next trend day paste the gate + auth + `v9_day_type_state` values **at the same instant** showing agreement, and a CONT fire passing the gate. Paste raw log lines.

## 4 · NOT-DONE (explicit)
- ❌ Do NOT revert Stage 1 (`DAYTYPE_PATTERN_AWARE_V1`) — the logic is correct; only its day_type input is stale.
- ❌ Do NOT change REACTIVE / balanced-day behavior.
- ❌ Do NOT enable live — SHADOW + Michael sign-off (trading-risk-surface).
- ❌ Do NOT re-enable S3/footprint.
- ❌ Do NOT "fix" by widening the Auth Table to authorize INITIATIVE on Neutral_Center — that would break balanced-day safety. The fix is the SOURCE, not the table.
