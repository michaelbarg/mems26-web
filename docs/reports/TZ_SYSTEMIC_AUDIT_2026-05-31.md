# TZ Systemic Audit — Naive/Aware Mismatch Map

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** DIAGNOSE ONLY — zero code changes  
**Scope:** All Python datetime comparisons where one side is DB-read (naive) and other is aware

---

## Executive Summary

**1 confirmed bug. 0 additional bugs found.** The rest of the codebase correctly handles the SQLite naive-stripping issue through defensive normalization patterns.

---

## 1 · DateTime Model Columns (all return naive from SQLite)

| Model | Timestamp Columns |
|-------|-------------------|
| V9Trade | `entry_ts`, `t1_hit_ts`, `t2_hit_ts`, `t3_hit_ts`, `stop_hit_ts`, `exit_ts`, `created_at`, `updated_at` |
| V9DayTypeHistory | `locked_at`, `created_at`, `last_updated_at`, `updated_at` |
| V9Bar5Min | `ts`, `created_at` |
| V9BarFootprint | `ts`, `created_at` |
| V9BarTickReversal | `ts`, `created_at` |
| V9BarWoodies | `ts`, `created_at` |
| V9TpoBars | `ts`, `created_at` |
| V9SystemSignal / V9SystemMarker | `ts`, `created_at` |
| V9FiveMinState | `last_processed_ts`, `updated_at` |

**All** come back as naive datetime from SQLite regardless of `DateTime(timezone=True)` declaration.

---

## 2 · Aware Datetime Sources

| Source | Pattern | Used In |
|--------|---------|---------|
| `_market_now_utc()` | Always aware UTC | manager.py (on_fill, on_target_hit, close_trade) |
| `datetime.now(timezone.utc)` | Always aware UTC | trail_engine, row_helpers, daily_quality_agent, configs |
| `datetime.fromisoformat(s)` with `+00:00`/`Z` | Aware when offset present | bar_level_detector, trail_engine, trade_excursion |
| `datetime.fromtimestamp(epoch, tz=timezone.utc)` | Always aware | bar_level_detector, row_helpers |
| Bridge timestamps | Always `+00:00` suffix | All bar streams |

---

## 3 · Comparison Sites — Classification

| File:Line | Comparison | Left (source) | Right (source) | Classification | Reasoning |
|-----------|-----------|---------------|----------------|---------------|-----------|
| `bar_level_detector.py:91` | `bar_ts < trade_entry` | aware (_parse_ts) | naive (DB) | **CONFIRMED-BUG** | Guard at line 89 is no-op; TypeError caught silently |
| `trail_engine.py:290` | `now_utc - entry_ts` | aware (now) | normalized (code checks `tzinfo is None`) | SAFE | Line 286: `if entry_ts.tzinfo is None: entry_ts = entry_ts.replace(tzinfo=timezone.utc)` |
| `journal_compat_routes.py:112` | `end - entry_ts` | aware/normalized | normalized | SAFE | Lines 109-111: both sides get `if x.tzinfo is None: x = x.replace(tzinfo=timezone.utc)` |
| `trade_excursion.py:79` | `start <= ts <= end` | aware (_utc helper) | aware (_utc helper) | SAFE | All pass through `_utc()` normalizer |
| `trade_excursion.py:93` | `end < start` | aware (_utc) | aware (_utc) | SAFE | Both normalized |
| `row_helpers.py:121` | `now - ts` | aware (now) | aware (parse_ts_to_utc) | SAFE | `parse_ts_to_utc()` always returns aware |
| `row_helpers.py:320` | `now - fetched_at` | aware | aware (in-memory) | SAFE | Never goes through DB |
| `killzone/detector.py:180` | `now_utc - event_ts` | aware | normalized | SAFE | Line 179: `if event_ts.tzinfo is None: ...` |
| `clock_routes.py:27-28` | `ib_end_utc - now_utc` | aware | aware | SAFE | Both from market_clock (in-memory) |
| `daily_quality_agent:128` | `entry_ts >= day_start` | SQL filter | SQL filter | SAFE | SQLAlchemy text comparison in SQLite |

---

## 4 · Silent Exception Handlers Near Datetime Ops

| File:Line | Handler | What it catches | Risk |
|-----------|---------|----------------|------|
| `bar_level_detector.py:127` | `except Exception as e: logger.error(...)` | Wraps entire `on_bar` including line 91 comparison | **BUG AMPLIFIER** — swallows TypeError, bar silently skipped |
| `trail_engine.py:166` | `except Exception as exc: logger.error(...)` | Wraps `_process_trade` | Low risk — time_stop code is SAFE |
| `row_helpers.py:172-175` | `except Exception` | Wraps `parse_ts_to_utc` failure | Low risk — returns None, caller handles |

**Only `bar_level_detector.py:127` is actively masking a bug.** The others protect against parse failures on malformed data, not comparison mismatches.

---

## 5 · Why Only 1 Bug Exists

The codebase has **three defensive patterns** that other developers applied:

1. **Pattern A — `if x.tzinfo is None: x = x.replace(tzinfo=timezone.utc)`**  
   Used in: `trail_engine.py:286`, `journal_compat_routes.py:109-111`, `killzone/detector.py:179`

2. **Pattern B — Dedicated normalizer (`_utc()`, `parse_ts_to_utc()`)**  
   Used in: `trade_excursion.py:52-58`, `row_helpers.py:58-112`

3. **Pattern C — SQL-level comparison (text, no Python datetime)**  
   Used in: all SQLAlchemy `.filter()` clauses

`bar_level_detector.py` used **Pattern D — `hasattr(x, "tzinfo")`** which is incorrect because every datetime has that attribute. The author likely confused `hasattr(x, "tzinfo")` with `x.tzinfo is not None`.

---

## 6 · Proposed Systemic Fix (NOT implemented)

### Option 1: Per-site fix (minimal blast radius)

Fix only `bar_level_detector.py:89` — replace `hasattr` with `tzinfo is None` check:
```python
if trade_entry.tzinfo is None:
    trade_entry = trade_entry.replace(tzinfo=timezone.utc)
```

**Blast radius:** 1 file, 1 line. Matches Pattern A used elsewhere.  
**Pro:** Smallest change, proven pattern.  
**Con:** Doesn't prevent future developers from making the same mistake.

### Option 2: TypeDecorator on DateTime columns (boundary fix)

Create a custom SQLAlchemy `TZDateTime` type that adds `tzinfo=UTC` on `process_result_value`:
```python
class TZDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
```

Apply to all DateTime columns in models.

**Blast radius:** All 20+ models, all read paths. Every DB datetime becomes aware on read.  
**Pro:** Eliminates the class of bug systemically. No per-site normalization needed.  
**Con:** Larger change, needs testing that nothing breaks (some code might rely on naive). Also: existing Pattern A normalizations become no-ops (harmless but redundant).

### Option 3: Shared helper (opt-in boundary fix)

```python
def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
```

Add to `backend/v9/shared/` and use at all DB-read boundaries.

**Blast radius:** Moderate — callers must opt-in.  
**Pro:** Explicit, no magic. Gradual adoption.  
**Con:** Doesn't prevent the class of bug (developers must remember to use it).

### Recommendation

**Option 1 now** (fix the one bug) + **Option 2 in P6** (systemic prevention when stable).

Rationale: Option 1 matches the existing codebase convention (Pattern A), is proven safe by trail_engine/journal_compat/killzone, and has zero blast radius. Option 2 is the right long-term answer but touches 20+ models and needs dedicated testing.

---

## 7 · Summary

| Category | Count | Details |
|----------|-------|---------|
| CONFIRMED-BUG | 1 | `bar_level_detector.py:91` — naive vs aware, masked by silent except |
| AT-RISK (defended) | 5 | All have correct Pattern A/B normalization |
| SAFE (SQL-level) | 3 | SQLAlchemy filter clauses — text comparison |
| SAFE (in-memory only) | 3 | No DB round-trip involved |
| Silent except amplifiers | 1 | `bar_level_detector.py:127` |

**The TZ bug is NOT systemic.** It's a single site with a broken guard (`hasattr` instead of `.tzinfo is None`). The rest of the codebase correctly defends against the SQLite naive-stripping behavior.

---

## Decision Required — Michael

1. **Approve Option 1** (per-site fix in bar_level_detector) — smallest correct change, matches existing patterns.
2. **Defer Option 2** (TypeDecorator) to P6 stability milestone.
3. After fix: BarLevelDetector will start detecting targets/stops — confirm this is desired behavior in SHADOW.
