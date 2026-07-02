# S1 — ACTIVE CANONICAL day-type engine (read this FIRST)

> **Why this file exists:** MEMS26 has **multiple** day-type engines. Chats/agents keep
> getting confused about which one is live, and that confusion caused a real loss on
> **2026-06-29**. This doc states — unambiguously, for any future chat/agent — which engine
> is ACTIVE, where the trade gate reads it, which sources are DEAD, the escalation-only rule,
> and the exact health check. **Do not re-derive S1's "current engine" from memory or from a
> single endpoint — read this, then verify with the query in §5.**
>
> Audited & verified 2026-06-30 (Cowork). Trading-code unchanged.

---

## 1. The ACTIVE CANONICAL S1 = the NEW 7-type classifier

**Canonical engine:** `classify_session(...)` in
`backend/v9/systems/day_type/classifier_core.py`, exposed for replay/UI via
`GET /api/v9/day_type/classify_replay?date=YYYY-MM-DD`
(`backend/v9/api/v9/daytype_classify_routes.py`).

It emits **7 types**: `Normal`, `Normal_Variation` (→ mapped to `Variation` for the
playbook), `Nontrend`, `Neutral_Extreme`, `Trend_Normal`, `Trend_DD`, plus the non-terminal
`FORMING`/`PROVISIONAL` lifecycle states. IB comes from **Sierra TPO** (`v9_tpo_sessions`
CASH, `ib_source="sierra_tpo"`) — the source of truth — not recomputed when Sierra has it.

It is live in **two** independent places, both gated ON today:

| Where | Flag (state 2026-06-30) | Effect |
|---|---|---|
| **Trade gate** (the label that stamps `day_type_at_entry` + drives the 3 day-type gates) | `S1_NEW_CLASSIFIER=1` ✅ | `extract_g1_entry_context` overrides the old engine with `classify_replay`'s `final.day_type` |
| **Live per-bar engine** (the running `day_type_machine` label, post-IB-lock) | `S1_ENGINE_NEW_CLASSIFIER=1` ✅ | `_day_type_on_bar` promotes `classify_session` and **skips** the legacy ShadowReclassifier |

The **OLD 3-type engine** (`day_type_machine`, the `DECISION_MATRIX` state machine in
`backend/v9/systems/day_type/state_machine.py`) is now only a **pre-IB-lock /
fail-safe fallback**, not the canonical classifier. It outputs only
`Trend_Normal / Variation / Normal`.

---

## 2. Exactly where the trade gate reads S1

`backend/v9/services/trade_context.py` → `extract_g1_entry_context(...)` (~L487–551):

1. Default `day_type` = `day_type_machine` blob at entry (the OLD engine). `UNKNOWN` → `None`.
2. **If `S1_NEW_CLASSIFIER` is on** (it is): call `classify_replay(today_ET)`, take
   `final.day_type`, map `Normal_Variation → Variation`, and **override** the value from step 1.
   - Result cached ~30 s (`_NC_CACHE`) so a fire-burst doesn't re-run the pipeline per trade.
   - **Fail-safe:** any exception / no-bars / `FORMING` → keep the OLD engine's value
     (never blocks a fire).
   - Pre-IB-lock `FORMING` **only** drops to `day_type=None` when `OPENING_FIRE_CVD_V1` is
     ON — and **that flag is OFF** today (see §3).

This returned `day_type_at_entry` is what the day-type gates
(`DAYTYPE_POSITION_GATE`, `NONTREND_DISABLE_ALL`, the playbook) consume and what stamps
`v9_trades.day_type_at_entry`.

---

## 3. The 2026-06-29 bug and its fix — STATUS

**Bug (06-29):** 4× `INITIATIVE_SHORT` fired at the day-low on a +96 pt up-day. Root cause:
pre-IB-lock, the NEW classifier was still `FORMING`, so the gate fell back to the **OLD
3-type engine**, which had prematurely produced a directional **`Variation`** → wrong
pattern family selected.

**Fix:** commit **`f1304b6`** ("Stage 0 — CVD-confirm OPEN_DRIVE + pre-lock no-fallback").
Change 3 makes pre-IB-lock `FORMING` return `day_type=None` (no premature INITIATIVE from
the old engine's directional fallback). The code is **present** in `trade_context.py` (L524–528).

> ⚠️ **IMPORTANT — the fix is gated behind `OPENING_FIRE_CVD_V1`, which is OFF (SHADOW-only,
> awaiting Michael sign-off).** So as of 2026-06-30 the pre-IB-lock fallback to the old
> 3-type engine is **still the live behavior**. The fix exists but is **not active**.
> Enabling `OPENING_FIRE_CVD_V1` is a trading-risk-surface change → Michael sign-off + restart
> (see `docs/handoff/CC_STAGE0_OPENING_FIRE_CVD_2026-06-29.md`). Do **not** assume the 06-29
> failure mode is closed in production until that flag is ON.

---

## 4. DEAD / LEGACY day-type sources — DO NOT USE

| Source | Status | Why |
|---|---|---|
| `GET /api/v9/day_type/current` (V1 wrapper) · `GET /api/v9/day_type/v9/current` (returns None) | 🔴 **DEAD** | Retired from the frontend 2026-06-22. Reads a dead wrapper instance → misleading `UNKNOWN`. |
| `v9_day_type_state` (`stage`/`lock_state`/`classification`) | 🟡 **DO NOT trust the label** | The OLD state-machine's own state table. On 2026-06-30 07:50 ET it showed `day_type=UNKNOWN / A2 / PENDING` — that is the legacy wrapper, **not** the canonical classification. Useful only for stage/lock diagnostics, never for the trade label. |
| `v9_day_type_shadow_transitions` | 🟡 **STALE BY DESIGN since 06-22** | This is the legacy `ShadowReclassifier` escalation log. It stopped writing the moment `S1_ENGINE_NEW_CLASSIFIER` went ON (the live engine now skips the legacy reclass branch — `backend/main.py` L481-482). **Its staleness is expected, not a regression.** |
| OLD `day_type_machine` 3-type label as "the answer" | 🟡 **Fallback only** | Canonical = the 7-type classifier. The old engine is a pre-lock / error fallback (and is the surface behind the 06-29 bug). |
| `v9_bars_5min` for the classifier's CVD when stalled | see `SOURCE_OF_TRUTH.md` | The classifier already falls back to the contiguous `v9_bars_5min_woodies`. |

**Canonical, fresh, per-date day-type to trust:** `v9_day_type_history` (one terminal row
per date, written by the live engine) **and** the live `classify_replay(date)` recomputation.
Pre-market rows in `v9_day_type_history` may be a **carry-over** of yesterday (e.g. 06-30 at
07:00 ET held 06-29's exact IB `7489.75/7409` as `LOCKED_LOW_CONF`) until today's RTH bars
arrive and it reclassifies — verify the row's IB/`updated_at` before trusting it intraday
(Rule 2).

---

## 5. Escalation-only invariant (Normal → Variation → Trend, NEVER reverse)

Within a session the day-type may only **upgrade**, never downgrade. Enforced in
`backend/v9/systems/day_type/shadow_reclass.py` (L85-88) via a monotonic rank:

```
TYPE_ORDER = {"Normal": 0, "Variation": 1, "Neutral_Extreme": 1, "Trend_Normal": 2, "Trend_DD": 3}
# new rank <= current rank  →  hold at the highest reached (never downgrade)
```

A "FORMING → Variation → back to Normal" sequence is a **bug**, not normal behavior.
Verified holding in `v9_day_type_history` (all observed transitions are upgrades:
`Normal→Variation`, `Variation→Trend_Normal`, `Normal→Neutral_Extreme`).

---

## 6. How to verify S1 is healthy (exact checks)

**A. Confirm the canonical engine is the one wired to the trade gate** (must both be `1`):

```bash
grep -E '^S1_NEW_CLASSIFIER=|^S1_ENGINE_NEW_CLASSIFIER=' /Users/michael/Downloads/mems26_web_git/.env
# expect: S1_NEW_CLASSIFIER=1  and  S1_ENGINE_NEW_CLASSIFIER=1
```

(Canonical flag truth = `docs/FLAG_INDEX.md`; never answer flag state from memory.)

**B. Confirm it classifies FRESH data correctly** — live recompute on the most recent
COMPLETE RTH day (`psql` binary at `/Applications/Postgres.app/Contents/Versions/*/bin/psql`,
DB `postgresql://localhost/mems26`, LOCAL only):

```bash
cd /Users/michael/Downloads/mems26_web_git && python3 - <<'PY'
import os; os.environ.setdefault("DATABASE_URL","postgresql://localhost/mems26")
from backend.v9.api.v9.daytype_classify_routes import classify_replay
r = classify_replay("2026-06-29") or {}          # use the last completed trading date
print("n_bars=", r.get("n_bars"), "ib_source=", r.get("ib_source"),
      "FINAL=", (r.get("final") or {}).get("day_type"), (r.get("final") or {}).get("status"))
PY
# HEALTHY: n_bars≈78, ib_source='sierra_tpo', FINAL=<a 7-type>/CLASSIFIED (not FORMING)
```

**C. Confirm the per-date history table is fresh + escalation-clean:**

```sql
SELECT date, day_type, status, ib_width, updated_at
FROM v9_day_type_history ORDER BY date DESC LIMIT 8;
-- HEALTHY: top row = today (or last trading day); no within-session downgrade.
```

**D. Expected-stale (do NOT flag as broken):** `v9_day_type_shadow_transitions`
(`max(session_date)` stuck at 2026-06-22) and `v9_day_type_state` (`UNKNOWN/PENDING`) — both
are legacy surfaces superseded by the NEW engine (§4).

---

## 7. One-line summary for a busy agent

> **Canonical S1 = the 7-type `classify_session` / `classify_replay`.** Trade gate reads it
> via `extract_g1_entry_context` (flag `S1_NEW_CLASSIFIER=1`); live per-bar via
> `S1_ENGINE_NEW_CLASSIFIER=1`. The OLD `day_type_machine` 3-type engine is a pre-lock/error
> **fallback only** (and was the 06-29 bug). `/api/v9/day_type/current`,
> `v9_day_type_state`, and `v9_day_type_shadow_transitions` are **DEAD/legacy** — do not use.
> Day-type only escalates, never reverses. Verify with §6.
