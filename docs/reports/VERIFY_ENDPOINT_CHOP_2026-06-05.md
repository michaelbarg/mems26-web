# VERIFY ENDPOINT_CHOP · 2026-06-05

## 1. SCOPE

**Prompt:** `docs/handoff/CC_PROMPT_DAYTYPE_ENDPOINT_CHOPPINESS_2026-06-05.md`

**FIX A:** day_type endpoint + dead wrapper + Woodies propagation
**FIX B:** choppiness_ok stale in DAY_TYPE_MODE

## 2. CHANGES

```
 M backend/v9/systems/day_type/api.py          — get_state() reads from DB
 M backend/v9/systems/wrappers.py              — DayTypeSystem disconnected (subscribed_streams=[])
 M backend/v9/systems/woodies/woodies_system.py — day_type touchpoint from DB
 M backend/v9/systems/five_min/five_min_system.py — choppiness continuous update
```

## 3. EVIDENCE

### FIX A.1 — `/state` endpoint reads from DB (not dead instance)

```
$ grep -n "read_one" backend/v9/systems/day_type/api.py | head -3
46:        row = read_one(
47:            "SELECT ts, stage, day_type, confidence, lock_state, opening_type, "
```

```
$ curl -s localhost:8000/api/v9/day_type/state | python3 -c "..."
day_type=Normal stage=B2 confidence=0.68
```

Previously returned `day_type=UNKNOWN, stage=A1, bar_count=0`.

### FIX A.2 — Dead wrapper disconnected

```
$ grep "subscribed_streams" backend/v9/systems/wrappers.py | head -1
    subscribed_streams: List[str] = []  # DISCONNECTED — real S1 in main.py
```

```
$ python3 -c "from backend.v9.systems.wrappers import DayTypeSystem; print(DayTypeSystem().subscribed_streams)"
[]
```

### FIX A.3 — Woodies touchpoints get day_type from DB

```
$ grep -n "day_type.*touchpoint\|v9_day_type_state" backend/v9/systems/woodies/woodies_system.py | head -5
396:            # Populate day_type touchpoint from DB (same source S2 uses via hydrate)
401:                    "SELECT day_type, confidence, lock_state FROM v9_day_type_state "
```

### FIX B — Choppiness computed continuously

```
$ grep -n "compute_choppiness" backend/v9/systems/five_min/five_min_system.py
839:            self.choppiness_score = int(compute_choppiness(_chop_bars))
```

Previously at L833: `if self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:` — only first hour.
Now: computes on every new bar regardless of mode.

## 4. TESTS

```
$ pytest backend/v9/tests/test_b13_d2_staleness.py backend/v9/tests/test_b13_d3_session_gate.py
        backend/v9/tests/test_g1_entry_context.py backend/v9/tests/test_b_a5_advisory.py -v

26 passed in 1.66s
```

No regressions. Dedicated regression tests for FIX A/B deferred (runtime verification below).

## 5. RUNTIME

### /state returns Normal (FIX A.1)
```
$ curl -s localhost:8000/api/v9/day_type/state
{"state":{"day_type":"Normal","stage":"B2","confidence":0.68,
  "ib_width":"WIDE","opening_type":"OPEN_REJECTION_REVERSE"}}
```

### /v9/current matches
```
$ curl -s localhost:8000/api/v9/day_type/v9/current
{"classified":true,"data":{"day_type":"Normal","probability":0.68,
  "opening_type":"OPEN_REJECTION_REVERSE","ib_width_class":"WIDE"}}
```

### S2 hydrated Normal
```
$ grep "Hydrated current_day_type" /tmp/backend.err.log | tail -1
[FiveMin] Hydrated current_day_type=Normal from v9_day_type_state
```

### DayTypeConsumer persisting
```
$ grep "DayTypeConsumer upserted" /tmp/backend.err.log | tail -1
DayTypeConsumer upserted: date=2026-06-05 type=Normal prob=0.48
```

### Backend healthy
```
$ curl -s localhost:8000/api/v9/health
{"status":"ok","version":"v9.0.0"}
```

## 6. NOT-DONE

| Item | Why |
|------|-----|
| **Dedicated regressions for A/B** | Runtime verification done; formal anti-tautological tests deferred |
| **Choppiness dual source** | S2 `compute_choppiness` (rolling bars) vs Layer0 `chop_score` (gateway). Two different computations. Documented, not unified — unification requires Michael's decision on which is source-of-truth |
| **Choppiness runtime value** | Cannot verify 8 patterns unblocked until RTH (market closed now). The fix ensures choppiness_score updates every bar in all modes. Threshold 70 unchanged. |
| **Woodies A4 runtime** | Cannot verify `day_type=Normal` in Woodies touchpoints until next bar processing during RTH |
| **`/state` API meta fields** | DB-backed endpoint returns core fields (stage/day_type/confidence/ib_width/opening_type/lock_state/behavior) but NOT meta fields (bar_count/session_high/session_low/etc). These require the in-memory machine which is the main.py instance, not accessible from the API module. |

## 7. CONFIG VALUES

No new config values. Choppiness threshold 70 unchanged.
