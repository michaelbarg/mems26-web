# N1ב — Day-Type Intraday-Transitions Diagnosis (2026-07-15 / 2026-07-16) — REPORT-ONLY

**Author:** cowork-dev (MacBook) · 2026-07-16 ~21:45 IL (night task N1ב, `NIGHT_PROMPT_2026-07-17`)
**Scope:** why v9_day_type_state missed/garbled the intraday transitions. **No engine code changed.**
Throwaway replay script ran from `/tmp/n1b_replay.py` (read-only, NOT committed, per task).

**תקציר בעברית:** הכללים של המסווג בסדר. הקלט שבור: ה-IB שה-DLL מייצא (tpo.json →
v9_tpo_history/v9_tpo_sessions → המכונה) ננעל **לפני פתיחת ה-RTH** ולא מתעדכן לשעה-הראשונה
האמיתית. ב-15/07 זה נתן IB שגוי (7591.75-7619 במקום 7601.25-7626.25) → צד-UP פנטום →
sides=2 → Neutral במקום Variation-DOWN. ריצה עם ה-IB הנכון, אותו קוד ואותם דגלים, נותנת
בדיוק את התשובה של מפתח-האמת: **Variation-DOWN מ-18:15 IL, בלי Neutral**. בנוסף: מספרי
ה-"16/07" בתדריך הם בפועל סשן ה-15/07, ומסמך מפתח-האמת של 15/07 מוזז בשעה (+1h).

---

## 0. Premise verification first (Rule 2) — three context corrections

### 0a. The "2026-07-16 IB ≈ 7601.25-7626.25 … down to 7571.75 (1.18×IB)" numbers are the **2026-07-15** session

```
$ psql -d mems26 -c "SELECT (ts AT TIME ZONE 'America/New_York')::date d, max(high) ib_h, min(low) ib_l, count(*) n
    FROM v9_bars_5min_woodies WHERE symbol='MES' AND d IN ('2026-07-15','2026-07-16')
    AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' AND < '10:30' GROUP BY 1"   -- (abbrev.)
d          | ib_h    | ib_l    | n
2026-07-15 | 7626.25 | 7601.25 | 12     ← Michael's "07-16" IB is EXACTLY here
2026-07-16 | 7613    | 7575.25 | 12
```
07-15 12:00-13:00 ET hour low = **7571.75** (exact), retrace high 7619.75. 7601.25−7571.75
= 29.5 = **1.18×25** — the exact phrase in the task. The 07-16 session (this DB) is a
different shape: open 7597 → plunge to **7575.25 INSIDE the first hour** (09:45 ET bar) →
recover 7614.75 → grind down to 7573.75. On 07-16 nothing ever extended ≥2pt beyond its
(wide, 38.25pt) IB → there was no Variation/Neutral transition to detect **in this DB's data**.

### 0b. Bar timestamps are TRUE (not shifted) — volume-spike proof, 07-15

```
$ psql -d mems26 -c "SELECT (ts AT TIME ZONE 'America/New_York')::time et, open, close, volume FROM v9_bars_5min_woodies
    WHERE symbol='MES' AND date='2026-07-15' AND time BETWEEN '09:00' AND '09:40' ORDER BY ts"  -- (abbrev.)
09:20 | 7609.5  | 7607.75 | 1440
09:25 | 7608    | 7612.5  | 5034
09:30 | 7612.25 | 7621.75 | 24119   ← RTH-open volume signature exactly at 09:30 ET
09:35 | 7622    | 7618.75 | 22391   (session high 7626.25 printed 09:35)
```

### 0c. `GROUND_TRUTH_TRADES_2026-07-15.md` is +1h-shifted and carries the wrong IB

The doc's "16:35 close 7606.75 vol 15249" is the DB's **10:35 ET** bar = true **17:35 IL**
(the doc used IL=UTC+2 instead of IDT=UTC+3). Its "IB 7591.75-7619" is not the first hour —
it is the frozen Sierra export (below). All 5 answer-key trades are real but their true IL
times are +1h (B=19:00, C=19:15, D=19:45, E=21:35-21:45); day-low 7571.75 @ true 19:40 IL.

---

## 1. ROOT CAUSE #1 (primary, data layer): the exported Sierra "IB" is a pre-open artifact that never re-bases to the CASH first hour

```
$ psql -d mems26 -c "SELECT to_char(ts AT TIME ZONE 'Asia/Jerusalem','HH24:MI') il, ib_high, ib_low FROM v9_tpo_history
    WHERE (ts AT TIME ZONE 'America/New_York')::date='2026-07-15' AND ib_high IS NOT NULL ORDER BY ts"  -- (sampled)
13:30 | 7604.25 | 7575       ← pre-open, carries some ETH window
15:30 | 7619    | 7591.75    ← 08:30 ET — RTH opens only at 16:30 IL!
16:30..19:30 | 7619 | 7591.75 (constant all session — never re-based to 7626.25/7601.25)

-- same class on 07-16:
13:30 | 7619   | 7591.75     ← 07-15's wrong pair carried across the day boundary
15:00 | 7613.5 | 7575.25     ← 08:00 ET, pre-open — yet this is what "IB" stayed at all day
$ psql ... "SELECT trading_date, session_type, ib_high, ib_low, vah_price, val_price FROM v9_tpo_sessions WHERE trading_date IN ('2026-07-15','2026-07-16')"
2026-07-15 | CASH   | 7619   | 7591.75 | 7616.5  | 7615.25   ← wrong IB + degenerate VA (width 1.25!)
2026-07-16 | GLOBEX | 7619   | 7591.75 | 7615.75 | 7615.75   ← stale cross-day carry, degenerate VA
2026-07-16 | CASH   | 7613.5 | 7575.25 | 7584.75 | 7581      ← "correct" only by coincidence (see below)
```

- The value pair is **set before 08:30 ET and never re-computed after the CASH IB locks**.
  On 07-16 it *happened* to coincide with the true first hour (the open plunged straight to
  the overnight-low area, so the pre-open window ≈ first-hour range: 7613.5/7575.25 vs bars
  7613/7575.25). On 07-15 it deviated (ib_high −7.25pt, ib_low −9.5pt) → catastrophic.
- Consumers of this value: live machine `backend/main.py:246-253` (`_load_sierra_tpo` →
  `bar_input.ib_high/ib_low`) → `state_machine.py:_stage_a3` (:567-585) accumulates → A4
  locks it → `main.py:453-467` passes `day_type_machine.ib_high/ib_low` into
  `classify_session`; replay endpoint `daytype_classify_routes.py:103-114` **prefers** the
  same stored row (`ib_source='sierra_tpo'`). The prior-day VA refs used by
  P0-1 acceptance (`classifier_core.py:117-141`) come from the same degenerate rows.
- The code invariant this breaks is written at **`relative_features.py:268-272`**:
  *"Sierra IB is the first-hour extremes — any price beyond it is necessarily
  post-first-hour, so session extremes are valid RE"* (`_mech_hi, _mech_lo = sh, sl`).
  With a false-low ib_high, the **first hour's own high counts as a mechanical up-extension**.

### The mechanism on 07-15, step by step (mech-sides flag ON, noise = max(2, 0.2×27.25) = 5.45pt)
session high 7626.25 (printed 09:35, INSIDE the true IB) − false ib_high 7619 = 7.25 ≥ 5.45
→ phantom **UP side from IB-lock onward**; when the real down-leg passed 7586.30 (~12:05 ET)
→ down side too → **sides=2 → Neutral_Extreme/Center** — exactly the wrong "Neutral" family
the answer-key doc condemns (trade D 19:45 IL blocked by "Neutral_Center שגוי").
With the TRUE IB, up-extension = 7619.75−7626.25 < 0 → **sides stays 1-DOWN, Neutral impossible**.

## 2. Empirical replay (the task's core evidence)

### 2a. API `GET /api/v9/day_type/classify_replay?date=2026-07-15` (live backend, live flags, sierra IB = frozen wrong row)
```
ib: 7591.75 - 7619.0  src: sierra_tpo  n: 78
09:35 Normal_Variation PROVISIONAL :: acceptance-reclass: accepted PDH break UP   ← phantom (bad PDH from partial 07-14 data)
10:25 Normal_Variation PROVISIONAL :: 1-sided extension (the phantom UP side!)
12:05 Neutral_Extreme  CLASSIFIED  :: 2-sided, close at an extreme      ← 19:05 IL: WRONG, day was mid-leg DOWN
12:45→15:55 Neutral_Center (flapping CLASSIFIED↔PROVISIONAL)            ← covers trade-D time (19:45 IL)
```

### 2b. Same day, same code, same flags, TRUE IB (throwaway script, `--ib=true`)
```
# 2026-07-15 ib=7601.25-7626.25 w=25.0 vr=1.295 flags all ON (live set)
17:25IL/10:25ET Normal            CLASSIFIED  sd=0 rib=1.0
*18:15IL/11:15ET Normal_Variation PROVISIONAL sd=1 rib=1.38 1tf=DOWN    ← Variation-DOWN as the extension develops
 19:25IL/12:25ET Normal_Variation sd=1 rib=2.1  1tf=DOWN cp=0.081       ← deep in the leg
 20:25IL/13:25ET Normal_Variation sd=1 rib=2.18 !FB (failed-break tag on the retrace)
 22:55IL/15:55ET Normal_Variation CLASSIFIED (EOD)                      ← NEVER Neutral all day
```
**This satisfies ground-truth criterion (א) exactly** (NV-DOWN through the leg, no Neutral).
→ The decision rules + current flags are NOT the blocker; the **IB input value is**.
(One residual blip: a single-bar `Trend_Normal control-path 4 stair-steps UP` at 21:35 IL on
the retrace — S1_TREND_CONTROL_V1 promoting the retrace leg; the S1_VALUE_MIGRATION_V1 veto
could not act because prior-VA is the degenerate 1.5pt row. Same RC#1 data family.)

### 2c. 07-16 replay (API n=63, session still live at run time; sierra IB ≈ bars IB here)
```
ib: 7575.25 - 7613.5  src: sierra_tpo
10:25→ Normal CLASSIFIED :: 0-sided, contained (rib<=1.3) + normal vol + IB not-narrow  (all day)
script: cf flaps 0.12↔0.25↔0.67↔1.0 while type stays Normal; sd=0, rib 0.99→1.22
```
Matches v9_day_type_state (below). **Given this DB's bars, "Normal" is the mechanically
correct verdict for 07-16** — down-extension beyond IB-low was only 1.5pt < noise 7.65pt.

### 2d. What the live machine actually persisted (v9_day_type_state, MacBook)
```
07-15: 17:00 Trend_Normal 0.35 → 17:30 Trend_Normal 0.62 → 17:45-20:46 Variation (cf 0.67↔0.00 flapping)
       → 20:46 Neutral_Center 1.00 → Neutral_Center/Extreme to close    (wrong Neutral, late)
07-16: 17:00 Normal 0.35 → 17:30-18:05 Variation 0.38/0.00/0.25 → 18:26→21:20 Normal cf 0.12↔0.67↔1.00
```
(07-16 the task's "flapping Normal conf 0.12-1.00" — verified ✓. Odd-second rows 18:26:52,
20:46:43, 21:08:29… are backend restarts re-seeding, which also re-write on-change state.)

## 3. Answers to the four specific questions in the task

1. **Does sides/ext use the LOCKED IB correctly?** Yes — mechanically correct usage
   (`relative_features.py:219-236, 262-278`), but of a **wrong locked value** (RC#1). The
   "Sierra IB = authority, never recompute" rule (Michael 2026-06-20) has no sanity check.
2. **Is level_acceptance too strict?** No. 2 closes + 8% volume triggered on time (down-
   acceptance ~12:00 ET on 07-15); it even fires spuriously early on garbage refs (09:35
   "PDH break UP" from a partial prior day; 07-16 09:35 "prior_VA break DOWN" vs the
   degenerate 1.25pt-wide VA row).
3. **Does LOCKED_LOW_CONF freeze the type?** No. `_stage_c1` sets lock_state as
   *informational only* (`state_machine.py:817-849`), C3 loops back to B2 every bar
   (`:862-875`), and the S1_ENGINE_NEW_CLASSIFIER promotion (`main.py:365-523`) ignores
   lock_state entirely. No freeze-after-lock bug exists.
4. **Do S1_ACCEPTANCE_RECLASS_V1 / S1_VALUE_MIGRATION_V1 / S1_TREND_CONTROL_V1 gate the
   needed rules OFF?** No — all ON, on both days, proven from `~/mems26_snapshots/*/.env`
   (every snapshot 07-13→07-15 has all six =1: S1_ENGINE_NEW_CLASSIFIER,
   DAYTYPE_SIDES_MECHANICAL_V1, S1_ACCEPTANCE_RECLASS_V1, S1_TREND_CONTROL_V1,
   S1_VALUE_MIGRATION_V1, S1_CONFIDENCE_V2) and current `.env` (lines 101-241).

## 4. Secondary root causes (real, but only visible once RC#1 is fixed)

- **RC#2 — rule order: acceptance-reclass shadows Neutral.** `daytype_classifier.py:187-201`
  returns Normal_Variation/Trend on any held accepted break BEFORE the `sides==2` Neutral
  check (`:247-254`). A day extended both sides but still holding one acceptance cannot be
  named Neutral until the acceptance is rejected — this is why the live 07-15 flip to
  Neutral_Center lagged to 20:46 IL instead of ~19:05. Doctrine ruling says "נייטרלי = יום
  מבולגן עם פריצה משני הצדדים" → sides==2 should outrank a held one-side acceptance.
- **RC#3 — confidence flapping 0.12↔0.67↔1.00.** `_confidence()`
  (`daytype_classifier.py:75-126`) switches between the 8-item directional evidence list and
  the 3-item balance list depending on `d` (one_tf / break_dir / close_pos vs 0.15/0.85
  bands) — adjacent bars flip the denominator → the persisted conf jumps 0.12↔0.67↔1.00 with
  no market change. Cosmetic, but it is the exact "flapping" symptom and erodes trust.
- **RC#4 — observability gap.** `v9_day_type_state` has NO direction/reason/sides columns
  (schema verified) — "Variation-DOWN" is not even representable; diagnosis required memory
  + replay. Writer at `main.py:588-604`.

## 5. Minimal-fix proposal (NUMBERED; per house rules every trading-logic change ships flag-OFF)

1. **DLL/export fix (owner: cc-imac, DLL ops runbook):** make the exported `ib_high/ib_low`
   re-base to the CASH-session first hour at 17:30 IL (10:30 ET) lock — today it stays a
   pre-open window. Verify which window the DLL currently locks (proven: value exists from
   ≤08:30 ET). Until deployed, treat every exported IB as UNVERIFIED pre-open data.
   *Verification:* on any day, at 17:35 IL `v9_tpo_sessions CASH ib_*` must equal
   `max(high)/min(low)` of the 09:30-10:29 ET bars (2-tick tolerance). Add this check to
   `scripts/mems26_verify.sh`.
2. **`S1_IB_SANITY_V1` (backend, default OFF):** in the two classify_session callers
   (`main.py` context block ~:442-467; `daytype_classify_routes.py:112-114`), when ≥12 RTH
   bars exist and the Sierra IB is *provably inconsistent* with the first-12-bars extremes
   (bars poke >2 ticks beyond it, or it pokes >2pt beyond the bars), fall back to the
   bars-derived first-hour IB + `ib_source="bars_fallback_sierra_inconsistent"` +
   rate-limited `logger.warning`. This is validation of ingested bars, not synthesis
   (Rule 1-compatible: the bars fallback already exists for the no-Sierra case,
   `relative_features.py:221-225`).
3. **`S1_NEUTRAL_PRECEDENCE_V1` (default OFF):** move the `sides == 2` Neutral branch above
   the acceptance-reclass early-return in `classify()` (reorder `daytype_classifier.py:187-201`
   vs `:247-254`), so a two-sided day cannot be shadowed by a still-held single acceptance.
4. **`S1_CONF_SMOOTH_V1` (default OFF):** stabilize `_confidence` — keep `d` sticky (hysteresis:
   change direction-basis only after 2 consecutive bars agree) or EMA(3) the score. Kills the
   0.12↔1.00 flapping without touching type decisions.
5. **Additive columns** `direction`, `reason`, `sides`, `rib` on `v9_day_type_state` (writer
   `main.py:588-604`; observability only, no gate reads them).
6. **Correct `GROUND_TRUTH_TRADES_2026-07-15.md`:** times +1h (true IL: A=17:35, B=19:00,
   C=19:15, D=19:45, E=21:35-21:45; low 7571.75 @19:40), IB = 7601.25-7626.25 (w=25). The
   answer key must not validate future fixes against a shifted clock and a frozen IB.
7. **cc-imac cross-check (live machine, trading-risk):** run E-queries from §1 on the iMac
   for 07-15/07-16. Michael's screen showing "IB 7601.25-7626.25" on 07-16 is consistent
   with the iMac's 07-16 export STILL carrying 07-15's true-CASH values (the stale-carry
   class proven here on the 07-16 GLOBEX row). If confirmed, the live gate is classifying
   against yesterday's IB **today** — highest-priority instance of RC#1.

## 6. Acceptance tests a fix must pass (the two replay criteria, restated on verified data)

- **T1 (07-15 = the session the task's "07-16" bullet describes):** replay 2026-07-15 with
  fix #2 ON (stored Sierra row untouched) → timeline must show `Normal_Variation`/
  direction=with_extension(DOWN) starting ≤18:30 IL (achieved: 18:15 IL) and **no Neutral_***
  segment while the down-leg is active (12:05-13:30 ET). EOD type: Normal_Variation (+
  failed_breakout tag after the retrace).
- **T2 (07-16):** same replay stays `Normal` all day on this DB's bars (regression guard —
  sides=0, rib≈1.07-1.22); with fix #4 ON, adjacent-bar confidence delta ≤0.35.
- **T3 (Neutral reachability, synthetic):** existing two-sided fixture must still produce
  Neutral_Center with fix #3 ON (it strengthens Neutral precedence, must not weaken it).
- **T4 (sanity guard no-op):** on a day where Sierra IB == bars IB (e.g., 07-16), fix #2
  changes nothing (`ib_source` stays `sierra_tpo`).

---
*Raw commands were run with `/Applications/Postgres.app/Contents/Versions/latest/bin/psql -d mems26`;
outputs abbreviated with `-- (abbrev.)`/sampling noted inline. Full per-bar replay reproducible via
the task's throwaway script pattern (`.venv/bin/python3`, DATABASE_URL=postgresql://localhost/mems26,
classify_session cumulative, is_eod on last bar only).*
