# P31 — Cursor session result: Day Type (Issue C) + CVD alignment (Issue A)

**Date:** 2026-05-21 IL · **Cursor session response to** `docs/handoff/P31_NEXT_CHAT_CHART_POC_DAYTYPE.md`
**Outgoing agent:** Cursor · **Owner:** Michael · **Mode:** code + live verification (no commits, no push)

> Copy this report to Claude Code for a second-opinion review of root-cause analysis,
> tests, and live UAT axes before approving git commit / push.

---

## 0. Headline

| Issue | Handoff hypothesis | Real root cause | Status |
|-------|--------------------|-----------------|--------|
| **C — Day Type misclassified → S2 doesn't fire** | TZ bug on `session_opened_ts` | **Schema drift** — `v9_day_type_history.{status,confidence}` are `NOT NULL` in live DB, consumer never set them → silent `IntegrityError` → empty history → V9 endpoint returned `classified:false` → user-facing endpoint demoted to V1 `Trend_Normal` | ✅ Fixed live |
| **C followup** | (not anticipated) | P30 C1 seed jumped to `Stage.B1` without setting `machine.opening` → B1 returned early → machine stuck at `B1/UNKNOWN` forever after restart | ✅ Fixed live |
| **A — CVD pane misaligned with 5-min candles** | (uncommitted refactor blamed) | **Same §9 DLL TZ bug, different field.** `points[].t` (CVD) was NOT covered by `BUGGY_TS_KEYS = ("bars","history","profiles","levels")` in the bridge workaround. Backend CVD endpoint reads the raw file directly so the bridge fix wouldn't have helped anyway | ✅ Fixed live in both bridge AND backend endpoint |
| **B — POC lines missing across continuous session** | TZ on `session_opened_ts` | Inconclusive without user clarification; chart pink today-lines DO appear from RTH open onward — see [§5 below](#5-issue-b--pending-user-clarification) | 🟡 Pending — user pointed to Drive spec `P31_POC_LINES_BEHAVIOR_SPEC.md` for CC to verify against code |

S2 firing was **NOT** gated by day_type per code inspection (`grep -r day_type backend/v9/gateway/` returns nothing). The handoff's S2-blocker hypothesis was incorrect. The user's visible symptom (wrong day_type displayed) is now fixed; whether S2 actually fires today depends on pattern conditions (AMT=0 currently makes reactive LONG impossible by spec).

---

## 1. Files changed (no commits yet)

| File | Lines | Purpose |
|------|-------|---------|
| `backend/v9/systems/day_type/consumer.py` | +54 | Always set `status` + `confidence` so prod NOT NULL schema accepts UPSERT |
| `backend/main.py` | +7 / −1 | Pass `lock_state` through consumer event; debug → warning on consumer failure |
| `backend/v9/api/v9/day_type_seed.py` | +14 | Seed `machine.opening = INDETERMINATE` so B1 can advance after mid-session seed |
| `backend/v9/api/v9/cumulative_delta_routes.py` | +63 | Chicago→UTC fix for `points[].t` mirroring §9 bridge workaround |
| `bridge/v9_streams/cumulative_delta_stream.py` | +28 | Same fix at the bridge layer (defence in depth, used by DB-backed consumers) |
| `backend/v9/tests/test_day_type_consumer.py` | +109 | 5 regression tests (incl. one using prod-schema NOT NULL constraints) |
| `tests/v9/systems/test_day_type/test_mid_session_restart_seed.py` | +71 | 2 regression tests for seed→B1→C3 progression |
| `tests/v9/bridge/test_streams.py` | +124 | 5 regression tests for bridge CVD Chicago→UTC override |
| `tests/v9/api/test_cumulative_delta_routes.py` | +85 / −6 | 2 new regression tests + monkeypatch of `_DISABLE_CHICAGO_TS_FIX` in 2 pre-existing tests |

**Test totals (this session):** **14 new tests added, 0 regressions.**

Full pytest runs:
- `backend/v9/tests/ + tests/v9/systems/test_day_type/` → **619 passed, 3 skipped**
- `tests/v9/bridge/test_streams.py + tests/v9/api/test_cumulative_delta_routes.py` → **42 passed**
- Focused `backend/v9/tests/test_day_type_consumer.py` → **10 passed**

---

## 2. Issue C — Day Type fix (deep dive)

### 2.1 Diagnosis chain

1. Live API state at start of session:
   ```
   /day_type/current → classified:false, source:v1_demoted, day_type:Trend_Normal, ib_h:7501.75
   /day_type/v9/current → classified:false, data:null
   /tpo/current → poc=7430.25, vah=7443.25, val=7415.0, ib_locked:true ✓
   /five_min/current → opening_type:null, mode:FIRST_HOUR_TACTICAL, buffer_size:1416
   ```
2. DB inspection showed **state machine IS running**: `v9_day_type_state` had 3905 rows for today, latest at `stage=B2, day_type=Nontrend, lock_state=PENDING`. Machine had progressed through A1→A2→A3→A4→B1→B2 normally.
3. `v9_day_type_history` table was **empty for today** (last row was `2026-05-16`). So the V9 API endpoint (`/day_type/v9/current`) which queries `WHERE date = today` returned `classified:false`.
4. **Suspicion:** `to_classification()` returns None OR `DayTypeConsumer.consume()` silently fails.
5. Wrote one-shot probe (`python3 - <<PY`) that imported the same modules and called `to_classification()` + `consumer.consume()` against the **live production DB**:
   ```
   to_classification() returned a valid DayTypeClassification object.
   consumer.consume() → sqlite3.IntegrityError:
     NOT NULL constraint failed: v9_day_type_history.status
   ```
6. Confirmed actual DB schema mismatch with SQLAlchemy model:
   ```sql
   -- DB: CREATE TABLE v9_day_type_history (... status VARCHAR(16) NOT NULL,
   --                                          confidence FLOAT NOT NULL, ...)
   -- Model: status = Column(String(16), nullable=True)
   --        confidence = Column(Float, nullable=True)
   ```
7. Migration `014_day_type_v9_columns.sql` explicitly says:
   > `-- SQLite doesn't support ALTER COLUMN, so status stays as-is (already has data)`

   The migration acknowledged the drift but couldn't fix it.
8. The consumer.consume() failure was caught at `_logger.debug` in `main._day_type_on_bar` → silenced for weeks (matches the `mems26-pre-live-protocol.mdc` rule against silent failures).

### 2.2 Code fix — consumer

`backend/v9/systems/day_type/consumer.py` — added two static helpers and called them in BOTH INSERT and UPDATE paths:

```42:61:backend/v9/systems/day_type/consumer.py
        # P31 §C fix: the production v9_day_type_history schema still carries
        # `status NOT NULL` and `confidence NOT NULL` (migration 014 noted that
        # SQLite cannot ALTER COLUMN to drop NOT NULL — see header comment).
        # The SQLAlchemy model marks both as nullable=True, so the in-memory
        # test DB created via Base.metadata.create_all() lets nulls through,
        # but the live SQLite DB rejects them with IntegrityError. The error
        # was being swallowed by `_logger.debug` in main._day_type_on_bar,
        # so v9_day_type_history stayed empty and the V9 day_type API endpoint
        # always returned `classified: false` → V1 demoted. Always populate
        # both legacy columns so the live UPSERT cannot drift again.
        legacy_status = self._map_legacy_status(classification_event)
        legacy_confidence = self._map_legacy_confidence(classification_event)
```

Mapping rules:
- `status` ← `lock_state` from the event if present (`LOCKED` / `LOCKED_LOW_CONF` / `PENDING`), otherwise default `"LOCKED"` (matches the 4 existing historical rows).
- `confidence` ← `probability * 100` (V1 percentage; mirrors the reverse mapping already in `day_type_v9_routes._row_to_v9_dict`).

`backend/main.py` — pass `lock_state` through and surface failures:

```242:264:backend/main.py
                            # P31 §C: pass the state machine's lock_state so the
                            # V1-legacy `status` column reflects PENDING vs LOCKED
                            # instead of being hardcoded to LOCKED.
                            "lock_state": str(state.lock_state),
                        })
                except Exception as consumer_err:
                    # P31 §C: was logger.debug — silent failures hid a schema-drift
                    # IntegrityError (status/confidence NOT NULL) for weeks.
                    _logger.warning(
                        "[DayType] V9 consumer persist failed: %s", consumer_err
                    )
```

### 2.3 Issue C followup — seed bug exposed by the fix

After restart with the consumer fix, the state machine got stuck at `stage=B1, day_type=UNKNOWN` post-restart. Diagnosis:

- `maybe_seed_ib_from_tpo` was added by P30 C1 to handle mid-session restart: when machine is fresh AND `session_min > 60` AND TPO has locked IB, seed `ib_high/ib_low/ib_class`, jump straight to `Stage.B1`.
- But the seed **never set `machine.opening`**. `_stage_b1` has an early return `if self.opening is None or self.ib_class is None: return`. So the machine was stuck at B1 forever, `to_classification()` returned None, consumer was never invoked.
- The original P30 C1 fix worked accidentally when the bridge fed in bars BEFORE the seed condition was met (so A1→A2→A3→A4→B1 ran normally, setting opening from `detect_opening_type(bars[0:3])`). On a mid-session restart it never had that window.

Fix (`backend/v9/api/v9/day_type_seed.py`):

```88:103:backend/v9/api/v9/day_type_seed.py
    # P31 §C followup: B1 returns early when ``machine.opening is None`` so
    # jumping straight to B1 without seeding a synthetic opening leaves the
    # machine permanently stuck at ``stage=B1, day_type=UNKNOWN`` — the next
    # process_bar call would just keep running ``_stage_b1`` and returning.
    # We can't reconstruct the original Opening Type from a restart that
    # missed RTH open, so default to INDETERMINATE which the decision matrix
    # resolves to ``DayType.Normal`` (see ``decision_matrix.py``: that's the
    # explicit "opening not clearly classified" fallback). This lets B1 cast
    # a real vote and B2-B6 progress normally; later behavior (failed
    # extension, trend, compression) can still rescore the verdict.
    if machine.opening is None:
        machine.opening = OpeningDetection(
            opening_type=OpeningType.INDETERMINATE,
            drive_direction="NEUTRAL",
            confidence=0.0,
        )
```

Cross-checked `decision_matrix.py` lines 59-62 — `(INDETERMINATE, NARROW|MEDIUM|WIDE)` all explicitly resolve to `DayType.Normal`, the documented "opening not clearly classified — default to Normal (Prompt 15)" fallback. Safe default.

### 2.4 Issue C — 4 UAT axes (live, after 2nd restart at 19:35 IL)

| Axis | Before | After | Status |
|------|--------|-------|--------|
| **Quality** | `IntegrityError` on every consume; `Trend_Normal` V1 demoted | Zero consumer errors post-restart; `Normal` from V9 source | ✅ |
| **Recency** | `v9_day_type_history.last_updated_at` empty for today | Updates every ~3–4 s; machine processed bars continuously at B2 | ✅ |
| **Cardinality** | 0 rows / session_date for today | 1 row / session_date (UNIQUE enforced) | ✅ |
| **Latency** | n/a | `/api/v9/day_type/current` HTTP 200 in ≤14ms | ✅ |

Live API after fix (visible to user via chart top header as **"NOR 68% L"** — was "Trend_Normal" before):
```json
{ "day_type": "Normal", "confidence": 68, "classified": true,
  "stage": "C3", "opening_type": "INDETERMINATE",
  "ib_width_class": "NARROW