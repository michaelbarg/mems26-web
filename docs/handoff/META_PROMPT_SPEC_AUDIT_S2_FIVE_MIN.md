# META-PROMPT · SPEC AUDIT · S2 Five-Minute System
**Version:** 1.0 · 2026-05-27
**For:** Claude Desktop → send to Claude Code (CC)
**Owner audit:** Cursor (verifies CC report)
**Scope:** System 2 — Five-Minute pattern detection & trade lifecycle

---

## CONTEXT

S2 Five-Minute system was built across Pkgs 0–8. The spec authority is:
- `docs/spec_authority/S2_AUTH_TABLE_V1.md` — pattern × day-type sizing table (LOCKED 2026-05-25)
- `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` — exit rules per pattern
- `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` — trade manager hooks
- `docs/decisions/D-091_S2_LIVE_SCOPE.md` — live scope decisions

The goal is to verify **every S2 filter gate, sizing rule, and exit hook is actually
active in the running code** — not stubbed or bypassed.

---

## YOUR TASK (CC)

Run the following 6 checks. For each: read actual code, run tests, report PASS/FAIL/WARN.

---

### CHECK 1 · NT (Non-Trend) Day Type = Global NO_TRADE

**Spec (D-091, S2_AUTH_TABLE_V1 row NT):** When `current_day_type == NT`,
FiveMinSystem must NOT emit any setup or fire any gateway route.

**Verify:**
```bash
rg "NT\|Nontrend\|NON_TREND\|no_trade\|NO_TRADE" \
    backend/v9/systems/five_min/five_min_system.py -A 3 | head -60
```

Check that there is an explicit `if self.current_day_type == "NT": return` or equivalent
guard BEFORE any pattern detection or gateway routing.

**PASS criteria:** NT check is a hard stop that returns early with no trade emission.

---

### CHECK 2 · Auth Table V1 Sizing — Quality Tier Active

**Spec (S2_AUTH_TABLE_V1):** Sizing (contracts per tier) must come from the
per-pattern × per-day-type table. `quality_tier.py` holds this logic.

**Verify:**
```bash
# Check quality_tier.py exists and has the full 10-pattern table
wc -l backend/v9/systems/five_min/quality_tier.py
rg "REACTIVE_LONG\|INITIATIVE_LONG\|BULL_FLAG\|INVERSE_HNS" \
    backend/v9/systems/five_min/quality_tier.py | head -20
# Check it's called from five_min_system.py before gateway route
rg "quality_tier\|QualityTier\|get_sizing\|compute_size" \
    backend/v9/systems/five_min/five_min_system.py | head -20
```

**PASS criteria:** `quality_tier.py` has all 10 in-scope patterns. It is called
in `five_min_system.py` before any route is sent to gateway.

---

### CHECK 3 · OFA Entry Check — initiative vs reactive classification

**Spec (Pkgs 2a/2bc):** OFA (Order Flow Analysis) classification determines
whether an entry is REACTIVE or INITIATIVE. This affects sizing.

**Verify:**
```bash
rg "REACTIVE\|INITIATIVE\|ofa\|OFA" \
    backend/v9/systems/five_min/five_min_system.py -A 3 | head -40
```

**PASS criteria:** OFA classification is active and feeds into sizing decision.
**WARN:** If OFA is computed but not gating any trade, flag as PENDING.

---

### CHECK 4 · Exit Rules per S2_EXIT_DEFINITION_V6

**Spec:** S2 exit rules (adaptive stop, T1/T2 milestones) must be wired.

**Verify:**
```bash
rg "adaptive_stop\|time_stop_mapper\|t1_milestone\|T1\|exit" \
    backend/v9/systems/five_min/five_min_system.py | head -30
cat backend/v9/systems/five_min/time_stop_mapper.py | head -50
```

**PASS criteria:** At minimum, `time_stop_mapper.py` is imported and called when
a trade fires. Adaptive stop config is loaded from file (not hardcoded).

---

### CHECK 5 · Day Type Consumption

**Spec:** S2 subscribes to `mems26:events:system.day_type.classification`.
When a new day type arrives, `current_day_type` is updated.

**Verify:**
```bash
rg "day_type\|DayType\|current_day_type" \
    backend/v9/systems/five_min/five_min_system.py | head -30
```

Check that `process()` or a dedicated handler receives the day type event and
updates `self.current_day_type`.

**PASS criteria:** Day type event handler exists and updates internal state.

---

### CHECK 6 · Full pytest suite for S2

```bash
cd /Users/michael/Downloads/mems26_web_git
python -m pytest tests/v9/systems/five_min/ -q --tb=short 2>&1 | tail -50
```

Also run:
```bash
python -m pytest tests/v9/ -k "five_min or s2" -q --tb=short 2>&1 | tail -30
```

**PASS criteria:** All tests pass (excluding pre-waiver 21 known failures).
Report exact count: `X passed / Y failed / Z warnings`.

---

## REPORT FORMAT

```
## S2 Five-Minute — Spec Audit Results · [DATE]

| Check | Title | Result | Notes |
|-------|-------|--------|-------|
| 1 | NT Day Type NO_TRADE | ✅ / ⚠️ / ❌ | ... |
| 2 | Auth Table V1 Sizing | ... | ... |
| 3 | OFA Classification | ... | ... |
| 4 | Exit Rules V6 | ... | ... |
| 5 | Day Type Consumption | ... | ... |
| 6 | pytest S2 suite | ... | ... |

## Findings requiring Cursor action:
[FAILs and LIVE-blocking WARNs only]

## Shadow GREEN / RED verdict:
[Safe to run shadow? Y/N + reason]
```

---

## STOP SIGNALS

Stop immediately if:
- NT day type does NOT block trades (Check 1 FAIL) — this is a LIVE blocker
- Auth Table sizing is hardcoded (not from `quality_tier.py`) — spec violation
- Day type is not being consumed from the event bus (Check 5 FAIL)
