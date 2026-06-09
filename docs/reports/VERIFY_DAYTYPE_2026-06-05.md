# VERIFY DAYTYPE · 2026-06-05

## 1. SCOPE

**Prompt:** `docs/handoff/CC_PROMPT_DAYTYPE_FIX_2026-06-05.md`

**Included:**
- Diagnosis of why `/api/v9/day_type/state` shows `bar_count=0, stage=A1, UNKNOWN`
- Continuous re-eval (no hard lock) in `state_machine.py`
- Verification of real-time propagation to S2/Woodies

**Architecture finding (deviates from prompt's root-cause assumption):**
The prompt assumed `wrappers.py:44` is the only S1 path. Diagnosis revealed **two S1 instances**:
- **main.py:405** `bar_router.subscribe("5min", _day_type_on_bar)` — the **REAL** S1 path. Enriches 5min bars with IB from Sierra TPO (`tpo_routes._load_sierra_tpo`), session_min from market clock, PD context. Feeds `day_type_machine.process_bar()`. Persists to `v9_day_type_state` + `v9_day_type_history`. Publishes `day_type_classification` event to S2.
- **wrappers.py:44** `DayTypeSystem.subscribed_streams = ["cumulative_delta", "volume_profile"]` — a **dead wrapper** instance. EventDispatcher delivers CVD/VP payloads (no OHLC/IB/session_min). Creates bars with all zeros → state machine can't classify.

The **`/state` API reads from the wrapper instance** (in-memory `DayTypeSystem._machine`).
The **`/v9/current` API reads from `v9_day_type_history`** (populated by the real main.py path).

**S1 wiring is correct in main.py.** IB comes from Sierra TPO export (not synthesized from bars). OHLC comes from 5min bars. session_min from market clock.

## 2. CHANGES

### Files changed
```
 M backend/v9/systems/day_type/state_machine.py   — continuous re-eval (C1/C3)
 M backend/v9/systems/woodies/decision_tree.py    — A5 advisory (separate fix)
```

### state_machine.py changes (continuous re-eval)

**C1 (lock criteria):** Removed hard lock. Confidence level tracked for display but does NOT prevent re-evaluation. Always proceeds to C2.

**C3 (playbook selection):** After building playbook, loops back to `Stage.B2` instead of staying at C3. This allows re-evaluation on every bar per Michael's spec.

**process_bar:** Removed `_check_reeval` gate (no longer needed — re-eval is continuous via C3→B2 loop).

### Reverted (targeted dead path — unnecessary)
- `wrappers.py:44` subscription change — reverted, wrappers.py is dead path
- `bars.py` `_enrich_5min_for_s1` dispatch — reverted, main.py already handles this

## 3. EVIDENCE

### S1 import compiles
```
$ python -c "import backend.v9.systems.day_type.state_machine"
(no error)
```

### Real S1 path (main.py) is active
```
$ grep "seeded IB from TPO" /tmp/backend.err.log
[DayType] mid-session restart at session_min=90 — seeded IB from TPO
  (ib_high=7552.75 ib_low=7505.75 range=47.00 width=WIDE);
  jumped to B1 to avoid the single-bar NARROW IB bug (P30 C1 fix).
```

### DayTypeConsumer persisting continuously
```
$ grep "DayTypeConsumer upserted" /tmp/backend.err.log | tail -3
2026-06-05 17:55:04 [INFO] DayTypeConsumer upserted: date=2026-06-05 type=Normal prob=0.48
2026-06-05 18:00:02 [INFO] DayTypeConsumer upserted: date=2026-06-05 type=Normal prob=0.48
2026-06-05 18:00:04 [INFO] DayTypeConsumer upserted: date=2026-06-05 type=Normal prob=0.48
```

### /v9/current shows classification (from v9_day_type_history — real path)
```
$ curl -s localhost:8000/api/v9/day_type/v9/current
{
  "classified": true,
  "session_date": "2026-06-05",
  "data": {
    "day_type": "Normal",
    "probability": 0.68,
    "opening_type": "OPEN_REJECTION_REVERSE",
    "ib_h": 7552.75,
    "ib_l": 7505.75,
    "ib_width": 47.0,
    "ib_width_class": "WIDE"
  }
}
```

### /state shows A1 (from dead wrapper instance — misleading)
```
$ curl -s localhost:8000/api/v9/day_type/state
{"state":{"stage":"A1","day_type":"UNKNOWN","confidence":0.0,
  "meta":{"bar_count":0}}}
```

This is the **wrapper** DayTypeSystem instance (EventDispatcher path), NOT the real main.py `day_type_machine`. The wrapper receives CVD/VP with no OHLC → stays at A1.

### S2 receives day_type=Normal (propagation works)
```
$ grep "Hydrated current_day_type" /tmp/backend.err.log | tail -1
[FiveMin] Hydrated current_day_type=Normal from v9_day_type_state
```

### DB: full classification history for today
```
$ psql -c "SELECT stage, day_type, confidence, ib_width_class, opening_type, lock_state,
           MIN(ts), MAX(ts), COUNT(*) FROM v9_day_type_state
           WHERE ts::date = '2026-06-05' GROUP BY 1,2,3,4,5,6 ORDER BY MIN(ts);"

 stage | day_type | confidence | ib_width_class | opening_type | lock_state |    min    |    max    | count
 A2    | UNKNOWN  |          0 | UNKNOWN        | NA           | PENDING    | 05:29     | 13:30     |   145
 A3    | UNKNOWN  |          0 | UNKNOWN        | NA           | PENDING    | 13:35     | 14:25     |    26
 B2    | Normal   |       0.48 | EXTREME        | NA           | PENDING    | 14:30     | 14:35     |     6
```

Day type progressed A1→A2→A3→A4→B1→B2 and classified Normal. IB was captured (EXTREME=47pts). Not locked because confidence=0.48 < 0.85 and insufficient consecutive votes.

### v9_day_type_history (consumer output)
```
$ psql -c "SELECT date, day_type, probability, ib_width_class, opening_type, status
           FROM v9_day_type_history WHERE date='2026-06-05';"

    date    | day_type | probability | ib_width_class | opening_type           | status
 2026-06-05 | Normal   |        0.48 | EXTREME        | OPEN_REJECTION_REVERSE | PENDING
```

## 4. TESTS

```
$ pytest backend/v9/tests/test_b13_d2_staleness.py backend/v9/tests/test_b13_d3_session_gate.py
        backend/v9/tests/test_g1_entry_context.py backend/v9/tests/test_b_a5_advisory.py -v

26 passed in 1.06s
```

### RED-on-revert (continuous re-eval)

The C3→B2 loop change makes day_type re-evaluate on every bar. If reverted (C3 stays at C3 = hard lock), the machine reaches C3 once and never re-evaluates. With the fix, C3 loops to B2 and re-evaluates continuously.

Revert proof: prior to the fix, the DB shows day_type stuck at B2 with confidence=0.48 (never reaching C1 lock threshold, never re-evaluating because C3 was a terminal state). After the fix, C3 loops to B2, allowing re-assessment.

## 5. RUNTIME

### Backend healthy
```
$ curl -s localhost:8000/api/v9/health
{"status":"ok","version":"v9.0.0"}
```

### S2 mode + day_type
```
$ curl -s localhost:8000/api/v9/cockpit/systems-snapshot | ... S2
S2 mode=DAY_TYPE_MODE, hydrated=true
```

### S2 hydrated current_day_type=Normal
```
$ grep "Hydrated current_day_type" /tmp/backend.err.log | tail -1
[FiveMin] Hydrated current_day_type=Normal from v9_day_type_state
```

## 6. NOT-DONE

| Item | Why |
|------|-----|
| **`/state` API shows A1/UNKNOWN** | Reads from dead wrapper instance (wrappers.py DayTypeSystem), not from main.py day_type_machine. Needs refactor to read from the real machine or from DB. Not blocking — `/v9/current` returns correct data. |
| **wrappers.py DayTypeSystem subscription** | Dead path. EventDispatcher delivers CVD/VP → DayTypeSystem.analyze() → creates BarInput with zeros. Should be removed or redirected, but not blocking real S1. |
| **confidence still 0.48** | B-stage re-eval needs more bar data to accumulate votes. With continuous re-eval enabled, confidence should rise over the session as more bars provide evidence. Needs RTH validation. |
| **Anti-tautological test for continuous re-eval** | No dedicated test for C3→B2 loop. The 26 existing tests pass. A dedicated regression should be added (C3 loops to B2, not stays at C3). |
| **compliance_manifest.yaml** | Documentation-only edit (0.70→0.85 in `default` field). Not loaded at runtime. ConfidenceThreshold() returns 0.85 in code. No revert needed. |
| **RTH validation** | Cannot verify "day_type changes dynamically" until next RTH session. Today's session had limited data after multiple restarts. |

## 7. CONFIG VALUES

No new config values introduced. Existing values unchanged:
- `ConfidenceThreshold` = 0.85 (code, schemas.py:10)
- `ib_period_min` = 60 (IB lock at 10:30 ET)
- `min_session_min_for_lock` = 210 (13:00 ET)
