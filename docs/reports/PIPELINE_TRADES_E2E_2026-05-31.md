# E2E 1/2 — Pipeline Sync Audit + Trades Page Fixes

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Status:** GREEN — ready for E2E 2/2 (S1/S2/S3 classification)

---

## A · Pipeline Sync Audit (read-only)

מיפוי מלא של הצינור מקצה לקצה. **לא נמצאו שברים בסנכרון.**

### שכבת Bridge → Backend

```
bridge/v9_streams/ (14 streams)
  → POST http://localhost:8000/api/v9/bars/{type}
  → Bearer token auth, 15s timeout
  → CLOUD_URL enforced localhost-only (base_stream.py:37-44)
```

| Stream | Endpoint | DB Table |
|--------|----------|----------|
| Bars5MinStream | `/api/v9/bars/5min` | `v9_bars_5min` |
| FootprintStream | `/api/v9/bars/footprint` | `v9_bars_footprint` |
| TickReversal15Stream | `/api/v9/bars/tick_reversal?tick_count=15` | `v9_bars_tick_reversal` |
| TickReversal12Stream | `/api/v9/bars/tick_reversal?tick_count=12` | `v9_bars_tick_reversal` |
| Woodies5MinStream (PRIMARY) | `/api/v9/bars/woodies_5min` | `v9_bars_5min_woodies` |
| Woodies30MinStream | `/api/v9/bars/woodies` | `v9_bars_30min_woodies` |
| CumulativeDeltaStream | `/api/v9/bars/cumulative_delta` | `v9_bars_5min` (enrich) + `v9_bars_cumulative_delta` |
| VolumeProfileStream | `/api/v9/bars/volume_profile` | `v9_bars_5min` (enrich) + `v9_bars_volume_profile` |
| ImbalanceFlagsStream | `/api/v9/bars/imbalance` | `v9_system_signals` + `v9_bars_imbalance` |
| StackedImbalancesStream | `/api/v9/bars/stacked_imbalance` | `v9_system_signals` + `v9_bars_stacked_imbalance` |
| LivePriceStream | `/api/v9/live_price` | Redis only |
| TpoStream | `/api/v9/bars/tpo` | `v9_tpo_bars` (placeholder) |

**חוזה שדות:** Bridge שולח `ts,o,h,l,c,vol` — Backend מקבל אותו סכמה. TZ fix פעיל (ET→UTC) בכל הסטרימים מלבד tick_reversal (כבר UTC).

### שכבת Backend → DB

- `bars.py` — 10 POST endpoints לקליטה, 4 GET endpoints לקריאה
- `bar_ingestion.py` — UPSERT on `(ts, symbol)` עם future-bar guard
- `v9_trades` — 22 עמודות, indexes on `(mode, firing_system, entry_ts)`
- `v9_day_type_history` — V1 legacy + V9 hybrid columns

### שכבת Build Status → API

```
BuildStatusAggregator (aggregator.py)
  ├─ bridge_inspector → 8 stream freshness gates
  ├─ s2_inspector → 10 pattern statuses (firing_system=2)
  ├─ woodies_inspector → 9 pattern statuses (firing_system=4)
  └─ day_type_inspector → 1 classification status
  
→ GET /api/v9/status (10-layer health, 0.9s budget)
→ GET /cockpit/systems-snapshot
```

### שכבת API → Frontend

| Endpoint | Polling | Component |
|----------|---------|-----------|
| `/api/v9/status` | 5000ms | `useSystemStatePolling` (V9Dashboard) |
| `/api/v9/trades/recent` | 30000ms | `TradeHistoryStrip` |
| `/api/v9/live_price` | 5000ms (WS fallback) | `useLivePricePoll` |
| health heartbeat | 15000ms | `TopBar` |

**Polling intervals לא שונו** (per CLAUDE.md Polling Floors).

---

## B · אבחון נתיב הטרייד

מיפוי מלא של זרימת העסקה:

```
Pattern Detection (S2/S3/S4)
  → setup_emitter.py: emit_t1_setup()
    → D-091.Q2 gate (Nontrend)
    → Auth Table lookup (pattern × day_type × quality_tier)
    → SKIP verdict short-circuit
    → Build T1Setup
  → pre_fire_validator.py: validate_fire()
    → 7 checks (stop side, price ordering, R:R ≥ 1.0, confidence, time_stop)
  → gateway.py: route_setup()
    → SHADOW: ShadowExecutor → always creates trade
    → DEMO: slot check → DemoExecutor
    → LIVE: slot check → RiskValidator → LiveExecutor
  → trade_manager.py: accept_setup()
    → V9Trade row → DB (state=PENDING)
    → Event emission
  → on_fill() → state=FILLED → target monitoring → close_trade()
```

**ממצא:** הצינור עצמו תקין. הבעיות היו **בשכבת התצוגה** (C1-C5).

---

## C · תיקוני עמוד הטריידס — MANIFEST

### C1: Scratch תמיד 0 — FIXED

**קובץ:** `frontend/v9/src/v9/components/trades/TradesSummaryStrip.tsx:27`

**שורש:** `withPnl` מסנן `pnl !== 0`, ואז `scratch` מחפש `pnl === 0` בתוך `withPnl` — תנאי סותר.

**תיקון:** scratch מחושב מתוך `closed` (כל הסגורות) במקום `withPnl`:
```diff
- const scratch = withPnl.filter((t) => (t.pnl_usd ?? 0) === 0);
+ const scratch = closed.filter((t) => (t.pnl_usd ?? 0) === 0);
```

### C2: Mode ברירת מחדל SHADOW — FIXED

**קובץ:** `frontend/v9/src/v9/stores/tradeStore.ts:46`

**שורש:** `DEFAULT_FILTERS.mode = 'SHADOW'` — מסתיר LIVE/SIM trades בטעינה.

**תיקון:**
```diff
- mode: 'SHADOW',
+ mode: 'ALL',
```

### C3: השוואת תאריכים לקסיקלית — FIXED

**קובץ:** `frontend/v9/src/v9/stores/tradeStore.ts:98-99`

**שורש:** `entry_ts` (ISO datetime מלא) מושווה כמחרוזת ל-`YYYY-MM-DD` — שביר בגבולות TZ.

**תיקון:** חילוץ תאריך מתוך `entry_ts` לפני השוואה:
```diff
- if (filters.dateFrom && (t.entry_ts ?? '') < filters.dateFrom) return false;
- if (filters.dateTo && (t.entry_ts ?? '') > filters.dateTo) return false;
+ if (filters.dateFrom || filters.dateTo) {
+   const entryDate = t.entry_ts ? t.entry_ts.slice(0, 10) : '';
+   if (filters.dateFrom && entryDate < filters.dateFrom) return false;
+   if (filters.dateTo && entryDate > filters.dateTo) return false;
+ }
```

### C4: אין Win Rate % ואין R aggregate — FIXED

**קובץ:** `frontend/v9/src/v9/components/trades/TradesSummaryStrip.tsx`

**שורש:** stats לא כלל winRate/totalR, UI לא הציג אותם.

**תיקון:** הוספת חישוב `winRate = wins/(wins+losses)*100` ו-`totalR = Σpnl_r`, פלוס שני StatChip חדשים בסטריפ.

### C5: limit=200 חותך עסקאות — FIXED

**קבצים:** `backend/v9/api/v9/trades.py:327` + `frontend/v9/src/v9/lib/api.ts:163`

**שורש:** Backend `le=200`, Frontend default `limit=200`. יותר מ-200 עסקאות — חתוך בשקט.

**תיקון:**
- Backend: cap → `le=1000`, הוספת `total` count ו-`truncated` boolean בתגובה
- Frontend: default → `limit=500`

---

## D · בדיקות

### D3: `tests/v9/e2e/test_trades_visibility_freshness.py`

```
$ BRIDGE_TOKEN=michael-mems26-2026 python3 -m pytest tests/v9/e2e/ -v

test_seeded_trade_returned_by_list_endpoint    PASSED
test_seeded_trade_returned_by_recent_endpoint  PASSED
test_seeded_trade_detail_endpoint              PASSED
test_latest_trade_is_most_recent               PASSED
test_truncation_indicator                      PASSED
test_pnl_consistency_across_endpoints          PASSED
test_scratch_trade_has_zero_pnl                PASSED

======================== 7 passed in 0.40s =========================
```

**כיסוי:**
- Visibility: seeded trade מופיעה ב-list, recent, detail endpoints
- Recency: סדר entry_ts DESC
- Truncation: `total`/`truncated` fields פועלים
- Consistency: pnl/outcome/direction/state זהים בין list ו-detail
- Scratch: trade עם pnl=0 מוחזרת כ-BE/SCRATCH

### רגרסיה

- `test_trades_exit.py` — 4 failures **קיימים מלפני השינויים** (missing `setup_db` fixture ב-api/ scope). אומת עם `git stash` — אותן 4 failures בדיוק.
- TypeScript: אין שגיאות חדשות בקבצים ששונו (שגיאות קיימות ב-ComponentTable, PriceDebugConsole, TradeHistoryStrip — לא קשורות).

---

## קבצים ששונו

| קובץ | סוג שינוי |
|-------|-----------|
| `frontend/v9/src/v9/components/trades/TradesSummaryStrip.tsx` | C1 scratch + C4 WR%/R |
| `frontend/v9/src/v9/stores/tradeStore.ts` | C2 mode default + C3 date filter |
| `frontend/v9/src/v9/lib/api.ts` | C5 limit 200→500 |
| `backend/v9/api/v9/trades.py` | C5 cap 200→1000, total/truncated |
| `tests/v9/e2e/__init__.py` | NEW — e2e test package |
| `tests/v9/e2e/conftest.py` | NEW — DB fixtures for e2e |
| `tests/v9/e2e/test_trades_visibility_freshness.py` | NEW — 7 tests |

---

## שער — E2E 2/2

**E2E 1/2 ירוק.** הצינור מאומת, 5 באגי UI תוקנו, 7 טסטים ירוקים, אפס רגרסיה.

פרומפט 2/2 (סיווג S1/S2/S3 מאחורי flags) יכול להתחיל. סדר מימוש: S2 → S3 → S1-opening → S1-daytype.

**דרוש לפני 2/2:**
- Commit של שינויי 1/2 (Michael approval)
- אישור להתחיל ATR infrastructure + feature flags
