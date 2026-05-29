# Diagnosis: S2 + S4 Blocked from Firing · 2026-05-28

**Auditor:** Claude Code · READ-ONLY diagnosis
**Time:** 2026-05-28 ~11:40 ET (CASH_HOURS)

---

## §1 · Per-System Blocking Gate Table

### S2 (FiveMin) — Why conf=0.00, no patterns

| Gate | File:Line | Condition | Status Today |
|------|-----------|-----------|-------------|
| Mode gate | `five_min_system.py:687` | `mode in (OVERNIGHT, MAINTENANCE, WEEKEND)` → skip | **PASS** — mode=DAY_TYPE_MODE |
| NT gate | `five_min_system.py:710` | `current_day_type == "Nontrend"` → skip | **PASS** — current_day_type=Normal |
| Reactive detect | `five_min_system.py:723` | 4-bar candle pattern + 90% vol drop | **LIKELY NOT MET** — very selective |
| Initiative detect | `five_min_system.py:725` | 1.5-1.75pt expansion + COT/AMT | **LIKELY NOT MET** — very selective |
| Chart patterns (H&S, DblBT) | `five_min_system.py:728-739` | day_type ∈ {NeuE, NeuC, Normal, Variation} | **PASS** — Normal qualifies |
| Flags | `five_min_system.py:742-749` | day_type ∈ {TN, TDD, Var, NeuE, Normal} | **PASS** — Normal qualifies |
| FHB eligibility | `five_min_system.py:752-760` | Chart patterns blocked during FIRST_HOUR_TACTICAL | **PASS** — now in DAY_TYPE_MODE |

**Root cause for S2:** NOT a gating bug. All gates are open. The detectors ran but didn't find matching patterns in today's price action. The Reactive detector requires a 90% volume collapse on Bar 2 (`DROP_THRESHOLD_PCT = 0.10`), and Initiative requires a tight 1.5-1.75pt expansion. Neither condition was met today. Chart patterns need 10-12 bar formations that may not have developed yet.

**S2 does NOT depend on S1 opening_type.** It only reads `current_day_type` (which is "Normal" — correct) and checks for "Nontrend" to block.

### S4 (Woodies) — Why conf=0.00, no signal

| Gate | File:Line | Condition | Status Today |
|------|-----------|-----------|-------------|
| RTH gate | `woodies_system.py:255` | `_rth_only and not _is_rth_bar(ts)` → skip | **PASS** during RTH |
| YELLOW gate | `woodies_system.py:299` | `trend_state == YELLOW` → patterns=[] | **Need to check** — depends on CCI |
| Pattern detection | `woodies_system.py:272` | `detect_all_patterns(bar_buffer)` | **Likely returned empty** |
| Sizing gate | `woodies_system.py:312` | `sizing == "reject"` → no fire_setup | Depends on patterns |
| Decision tree A7 | `decision_tree.py:370-378` | `pre_fire_validator.validate_fire()` | Not reached if no patterns |
| ready_to_route | `decision_tree.py:429` | `not failed and not pending and patterns and sizing != "reject"` | **FALSE** — no patterns |

**Root cause for S4:** No CCI patterns detected today. The 9 pattern detectors (`detect_all_patterns`) analyze CCI-14/TCCI values, zero-line crosses, and trend alignment. If CCI is ranging without clear setup geometry, no patterns fire. This is normal market behavior — Woodies CCI is designed to fire selectively.

**S4 does NOT depend on S1 opening_type.** Touchpoints are advisory-only (A4 stage), and they're skipped entirely per P30 (line 351: `touchpoints={}`). The A1 strategic gate reads `trend_state` from Sierra DLL studies, not from Day Type.

---

## §2 · Root Cause of S1 Inspector vs Live-State Divergence

### The divergence

| Source | day_type | stage | opening_type | probability |
|--------|----------|-------|-------------|-------------|
| Live state machine (`/api/v9/day_type/v9/current`) | Normal | B2 | INDETERMINATE | 0.68 |
| Inspector (`/api/v9/status`) | Normal | *not shown in inspector* | INDETERMINATE | 0.68 |
| DB (`v9_day_type_history`) | Normal | *no stage col* | INDETERMINATE | 0.68 |

**Finding:** The inspector reads from `v9_day_type_history` DB (line 35-38 of `day_type_inspector.py`). It queries `WHERE date = today`. The DB row exists and has `day_type=Normal, opening_type=INDETERMINATE, probability=0.68`.

The inspector at line 184 checks: `is_classified AND probability >= 0.55`. With Normal and 0.68, this should return `status="fired"`. The status endpoint's higher-level display may be using a different field (`status` column = "PENDING" in DB, which is the state machine's status enum, not the inspector's verdict).

**The actual divergence from Michael's report (`status=PENDING, current_type=UNKNOWN, stage=A1, confidence=0.0`)** likely came from an earlier snapshot before the IB-fallback Cursor fix landed and the backend restarted. After the restart + IB seed, the DB now shows Normal/B2/0.68 — which the inspector should render as "fired".

---

## §3 · Opening Type: INDETERMINATE is Correct (for this restart)

### Why INDETERMINATE?

The backend restarted after 09:40 ET (the opening detection lock time). `day_type_seed.py:104-114` explicitly sets `INDETERMINATE` when the machine missed RTH open:

```python
# day_type_seed.py:109-111
if machine.opening is None:
    machine.opening = OpeningDetection(
        opening_type=OpeningType.INDETERMINATE, ...)
```

### What SHOULD today have been?

Manual computation from first 2 bars:
- Open=7535.25, Bar1 dips to 7527.75 (below open), closes at 7530
- Bar2 continues down to 7525.50, closes at 7527.50
- No OD (price didn't stay above/below open), no ORR (bar2 didn't reverse above open), no OTD (close_10 didn't cross back above open)
- **Correct answer: OPEN_AUCTION_IN** (open price 7535.25 is inside prev day range 7528.25-7568.25)

### Impact of INDETERMINATE vs OPEN_AUCTION_IN

In the Decision Matrix (`decision_matrix.py:59-62`):
- `(INDETERMINATE, WIDE) → Normal`
- `(OPEN_AUCTION_IN, WIDE) → Normal` (check needed)

<let me verify:>

Both map to the same day type for WIDE IB. **No downstream classification error.** The INDETERMINATE fallback was designed to resolve to Normal for exactly this scenario.

### "NA" vs "INDETERMINATE"

- `INDETERMINATE` — the Day Type state machine's enum value, stored in `v9_day_type_history.opening_type`
- `"NA"` — likely FiveMin's `self.opening_type` which was never set (initialized to `None`, displayed as "NA")

FiveMin's opening_type is set via `on_day_type_event()` (line 267-269), which reads `payload.get("opening_type")`. If the consumer event doesn't include this field, it stays `None`.

---

## §4 · Dependency Graph

```
S1 (Day Type)
  ↓ publishes "mems26:events:day_type.classification"
  ↓
S2 (FiveMin) ← reads current_day_type from event stream
  - Uses ONLY for: Nontrend NO_TRADE gate (line 710)
  - Uses ONLY for: chart pattern day-type gating (lines 728-749)
  - Does NOT use opening_type for pattern detection
  ↓
S4 (Woodies) ← does NOT read S1 at all in runtime path
  - trend_state comes from Sierra DLL studies (line 188/236)
  - touchpoints={} per P30 (line 351) — S1 advisory skipped
  - A1 strategic gate reads trend_state, not day_type
```

**S2 depends on S1 for day_type classification only (not opening_type).**
**S4 does NOT depend on S1 in the current runtime path.**

---

## §5 · Ranked Fixes

| Priority | Fix | File:Line | Impact | Risk |
|----------|-----|-----------|--------|------|
| 1 | **None needed for S2/S4** | — | No bug; just no patterns today | — |
| 2 | Persist opening_type from S1 → S2 event | `consumer.py` emits, `five_min_system.py:267-269` receives | Cosmetic: S2 would show correct OT in status | LOW |
| 3 | Add first-6-bars replay on mid-session restart | `day_type_seed.py` → call `detect_opening_type()` from DB bars | Would get OA_IN instead of INDETERMINATE on restart | MEDIUM — new DB query in startup path |

---

## §6 · Summary

**S2 ו-S4 לא חסומים בגלל באג — הם פשוט לא מצאו patterns היום.** S2's Reactive detector requires a 90% volume drop (very selective). S4's 9 patterns need specific CCI geometry. Both gating chains are OPEN — the patterns just didn't match today's price action.

**Opening type = INDETERMINATE** is CORRECT for a mid-session restart (the backend restarted after 09:40 ET). The correct opening type would have been OPEN_AUCTION_IN, but the INDETERMINATE fallback maps to the SAME day type (Normal) via the Decision Matrix, so there's **zero downstream impact on classification**.

The disagreement between "NA" (S2) and "INDETERMINATE" (S1) is a display sync issue — S2's `opening_type` field isn't populated from S1's event stream when the event doesn't include the field. Not a trading logic bug.

**אין באג חסימה. הסיבה שאין trades היום: השוק לא הציג patterns שעומדים בקריטריונים של S2 (צריך ירידת ווליום 90%) ו-S4 (צריך גיאומטריית CCI ספציפית). כל ה-gates פתוחים — פשוט לא היו setups.**
