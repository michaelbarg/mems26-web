# CC Follow-up — Extend the live day-type source to the S2 Auth Table (INITIATIVE half of I-44/I-50)

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — paste raw output (Rule 5), anti-tautological, NOT-DONE.
**Flag:** reuse `DAYTYPE_GATE_LIVE_V1` (this **completes** it). Default OFF · SHADOW.
**Depends on / completes:** commit `b5eb3e9` (`DAYTYPE_GATE_LIVE_V1` — live in-memory day_type in `extract_g1_entry_context`).

---

## 0 · Why — `b5eb3e9` fixed only HALF
`b5eb3e9` made the **gateway position gate** read the live in-memory `app.state.day_type_machine.day_type` (fixing the **ZLR** stale-"Normal" block). But the **S2 Auth Table** — the path that emitted on 06-30:
```
[S2] T1Setup skipped: pattern=INITIATIVE_LONG day_type=UNKNOWN tier=HIGH · Auth Table SKIP
```
— sources its day_type **separately**. **Verified 06-30 (Rule 5):** `backend/v9/systems/five_min/` does **NOT** import `extract_g1_entry_context`, so the `b5eb3e9` fix does **not** reach the Auth Table. Therefore INITIATIVE can **still** be `SKIP`-ped on a stale/`UNKNOWN` day_type while the live engine already holds `Trend_Normal` (`INITIATIVE_LONG @ Trend_Normal = ("FULL",3,2,1)` — it would fire 3 contracts). The handoff asked for "gate **+** Auth Table read the same live source" — only the gate is done.

## 1 · Scope — behind `DAYTYPE_GATE_LIVE_V1` (default OFF · SHADOW)
1. **Trace** where the S2 fire/Auth-Table path obtains the `day_type` passed to `auth_table_v1.get_auth_cell` (the value logged as `day_type=UNKNOWN`). Likely in `five_min_system` → `quality_tier`/`setup_emitter`. Paste the source.
2. **Read the SAME live source first.** Mirror `b5eb3e9`: try `app.state.day_type_machine.day_type` (live, instant), use it if a valid 7-type, else fall back to the current source. **Factor the read into ONE shared helper** (e.g. `live_day_type()` used by both `extract_g1_entry_context` and the S2 path) — do **not** duplicate the import/parse logic in two places (single source of truth).
3. **Pre-resolution (genuine UNKNOWN, pre-IB-lock).** When the live engine is *still* `UNKNOWN/FORMING` AND `OPENING_FIRE_CVD_V1` is ON AND `opening_type` is a drive (OPEN_DRIVE/OPEN_TEST_DRIVE): authorize via the **opening-type** (a provisional trend tier) instead of the `Neutral_Center → SKIP` fallback in `get_auth_cell` (L144-147). This is the missing Stage-0 ↔ Auth-Table link. Fail-safe: never size **up** beyond the opening-type's implied tier.

## 2 · Tests (anti-tautological)
1. **06-30 golden (14:00):** `INITIATIVE_LONG` with live engine = `Trend_Normal` → Auth Table returns **FULL** (not SKIP). Without the flag → reproduce the SKIP.
2. **Source equality:** the Auth-Table day_type == `app.state.day_type_machine.day_type` at the same bar.
3. **No regression:** a real balanced day (Normal/Neutral) → INITIATIVE/CONT still **SKIP**.
4. **Pre-lock UNKNOWN + OPEN_DRIVE** → INITIATIVE authorized via opening-type (provisional), not SKIP; **UNKNOWN + no drive** → conservative (SKIP).
5. **Flag OFF** → byte-identical to today.

## 3 · Verification (SHADOW · Rule 5)
With `DAYTYPE_GATE_LIVE_V1=1`, on the next trend day paste the Auth-Table `day_type` + `app.state` value + the resulting verdict (FULL/REDUCED, not SKIP) for a CONT fire.

## 4 · NOT-DONE
- ❌ Do not change the Auth Table **cell values** (the (pattern×day_type)→contracts matrix is locked) — only fix the **day_type input**.
- ❌ Do not enable the flag live — SHADOW + Michael sign-off.
- ❌ Do not touch REACTIVE / balanced-day behavior.
- ❌ Do not duplicate the live-read logic — factor one helper shared with `extract_g1_entry_context`.
