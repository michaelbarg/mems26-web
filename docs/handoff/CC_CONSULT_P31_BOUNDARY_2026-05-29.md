# CC Consultation — P31 Boundary Semantics & Split Decision

**Date:** 2026-05-29
**Mode:** 🟢 ADVISORY · CONSULTATION · NO CODE CHANGES · NO COMMITS
**Output:** `docs/reports/CC_CONSULT_P31_2026-05-29.md` (single file, ≤120 lines)
**Reference:**
- `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (whole file)
- `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` (your own audit)
- `docs/reports/sot_health_audit/0[1-5]_*.md` (5 audit reports)
- `docs/reports/FIX_SESSION_DATE_ET_2026-05-29.md` (your own fix `570f10d`)

---

## §0 · Why this consult exists

Cursor reviewed your audit + 4 sot_health audits. Before writing the
implementation prompt, Michael wants your **opinion** on 3 decisions
that have semantic implications neither of us caught alone. **Do not
implement anything.** Just answer 3 questions.

---

## §1 · Question 1 — Boundary semantics

You wrote in §11.1 of the audit:

> "_extract_session_date() must use the **18:00 ET trading-day boundary**
> instead of bare `.date()` — bars between 18:00 ET and 23:59 ET belong
> to the **next** trading day, bars between 00:00 ET and 17:59 ET belong
> to the **current** calendar date."

But your earlier commit `570f10d` (the one already on HEAD) implements:

```python
return ts.astimezone(ZoneInfo("America/New_York")).date()
```

Which is calendar ET date — **not** the 18:00 ET trading-day boundary.

### Your job

Answer in your report:

1. **Did `570f10d` partially-fix Bug A**, or fully-fix? Walk through the
   3 cases yourself (using `et_today_18()` semantics):
   - bar at 14:00 ET on 2026-05-29 → trading day = ?
   - bar at 20:00 ET on 2026-05-28 (= 00:00 UTC 2026-05-29) → trading day = ?
   - bar at 01:00 ET on 2026-05-29 (= 06:00 UTC 2026-05-29) → trading day = ?

2. **What does the user-visible UI consume?** The dashboard shows "Day
   Type: Normal" or "PENDING". Which of these is the field's source —
   `v9_day_type_history.date = ET-calendar-date` or `= ET-trading-day`?
   If a user looks at the dashboard at **20:30 ET on Sunday May 31**
   (Globex just opened → trading day = June 1), what should they see?

3. **Existing v9_day_type_history rows**: 254 rows, schema `date DATE NOT NULL`.
   If we switch to 18:00 ET trading-day going forward, do existing rows
   need migration (re-key from calendar to trading) or stay as-is? What
   semantic does the DB column carry today?

4. **Recommendation**: pick ONE — `et_calendar_date` OR `et_trading_day_18`
   — for going-forward writes, and explain in 3 lines why the other one
   would silently break a downstream consumer. Cite the consumer file.

---

## §2 · Question 2 — Split decision (P31 vs P32)

Cursor proposes:

| P-ID | Items | Why split |
|------|-------|-----------|
| **P31** | Daily reset + archive + demo readiness (items A–H from below) | One domain: date-of-truth + state-of-truth |
| **P32** | Bridge TZ fix + sot_health cleanup (items I–L) | Different domain: bridge/monitoring |

### Item list

**P31 candidates (A–H):**
- A. 18:00 ET boundary fix in `_extract_session_date` (your §11.1)
- B. State machine reset at boundary (your §11.2)
- C. 13× `date.today()` + 2× SQLite `date('now')` → `et_today()` (your §1)
- D. Wire `RiskValidator.daily_reset()` into `SessionBoundaryManager` (your §9.1)
- E. `tpo_system.process_bar()` `session_id` (your §9.4)
- F. `five_min_system.hydrate()` overnight early-return (audit 04)
- G. `logger.debug` → `logger.warning` in `backend/main.py:282,336` (your §9.6+9.7)
- H. UI/`/current` reject `ROLLED_OVER` rows (your §9.8)
- + design's existing scope: archive tables (Migration 019), `is_synthetic` flag, `v9_session_meta`, seed `v9_account_status`, `SessionBoundaryManager`

**P32 candidates (I–L):**
- I. tick_reversal `+5h` future-ts (audit 03 — DLL `time(nullptr)` double-corrected by bridge)
- J. TPO `sot_health` repoint `v9_tpo_sessions` → `v9_tpo_history` (audit 02)
- K. S3 (footprint + tick_reversal) added to `sot_health.py` system map (audit 01)
- L. Remove `v9_audit_events` + `v9_trade_management_log` from `sot_health` (audit 05 — orphaned)

### Your job

Answer:

1. Is the split clean, or do P31 and P32 share a hidden dependency?
   In particular: **does P32-I (tick_reversal TZ) need to land before
   P31** to avoid `is_synthetic`/`et_today()` filters operating over
   broken timestamps?

2. Within P31, what is the **correct task order** (root-cause → symptom)?
   Re-rank A–H if needed.

3. Are any items mis-classified? (e.g. should F really be P31, or is
   it a separate `five_min_system` cleanup?)

---

## §3 · Question 3 — Design doc gaps

Cursor will add to `DAILY_RESET_AND_ARCHIVE_DESIGN.md`:

- **§14** — "Pre-existing fix overlap (`570f10d`)" — what it fixed,
  what it left. Why P31 supersedes (or extends) it.
- **§15** — "Bug 04 — `five_min_system.hydrate()` overnight early-return"
  — the day_type chain second leg.
- **§7 (Risk Register)** — new row: "boundary semantics conflict with
  `570f10d` — a partial revert is needed at the moment of the new
  function activation, otherwise both old and new write paths run
  briefly". Mitigation: feature flag for new boundary, or atomic
  swap inside one commit.

### Your job

What is **missing** from the design that the audit or sot_health
findings expose? E.g. is there a §16 we should add? Be terse —
1-2 lines per gap.

---

## §4 · Hard rules

- **NO code changes**, **NO migrations**, **NO commits**, **NO test runs**.
- **Cite by symbol** (`function_name`, `class_name`) not by line numbers.
  Line numbers drift; symbols are stable.
- Self-summary at the top of your report (3-5 lines).
- Acknowledgement footer: confirm you read this prompt + the 3 reference
  reports + the design doc.

---

## §5 · STOP conditions

If you discover:
- A 5th case (between cases 1-3 in §1.1) where neither calendar nor
  trading-day semantics give the right answer
- A consumer that reads `v9_day_type_history.date` and assumes one
  semantic but treats it as the other (latent bug)
- A code path that would force `570f10d` and the new boundary to coexist
  (race condition during deploy)

→ **Stop and write the discovery as a numbered finding** at the top
  of your report. Do NOT extrapolate fixes — Michael decides.

---

## §6 · Verification loop

After your report:
1. Cursor reads + cross-checks against this prompt
2. Cursor reports findings to Michael
3. If approved → Cursor writes the implementation prompt for P31 (and
   separate P32 if the split is confirmed)
4. CC implements with per-task commits
