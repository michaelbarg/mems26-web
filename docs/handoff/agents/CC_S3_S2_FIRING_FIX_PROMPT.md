# CC Prompt — S3 SHADOW gate + AMT/COT fixes (P31-STRAT-S3)

**מטרה:** להחיות 2 firing systems שמדומים אבל לא יורים — Footprint (S3) ו-5-Min (S2).

**מקור:** [`PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md`](../../reports/PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md) + חקירה ב-2026-05-22.

**מצב נוכחי ב-DB:** מתוך 3 firing systems רק S4 יורה. 1,229 trades all-S4. S2 + S3 מעולם לא ירו אף trade בDB.

---

## הבאגים (3) — לפי סדר עדיפות

### 🔴 באג #1 — S3 חוסם את ה-fire ב-SHADOW mode (15 דק' + טסט)

**מיקום:** `backend/v9/systems/footprint/footprint_system.py:172-179`

**הקוד הנוכחי:**

```python
            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE":
                self._write_journal(event, bar, cluster, empty, ctx, pattern, signals, confluence, classification)
                if classification != "NO_SETUP":
                    self._write_setup(event, bar, classification, pattern, confluence)
                # T3: Fire if signal detected and size != reject
                if t3_signal:
                    self._fire(t3_signal, bar, event)
```

**הבעיה:** `_fire(...)` נמצא **בתוך** ה-`if mode == "LIVE":` block. זה מונע ירי ב-SHADOW.

**ההשוואה ל-S4 שעובד** (`backend/v9/systems/woodies/woodies_system.py:290-321`): `gateway.route_setup(...)` נקרא ללא תנאי `mode`. ה-gateway עצמו (`backend/v9/gateway/trading_gateway.py`) הוא זה שמחליט SHADOW/LIVE — לא הסיסטם.

**התיקון (smallest-correct-change):** הוצא את `_fire` מה-`if mode == "LIVE":` block. השאר `_write_journal` ו-`_write_setup` בתוך (אלה כן צריכים להיות LIVE-only, כי הם persistence).

**הקוד אחרי התיקון:**

```python
            mode = getattr(event, 'mode', 'LIVE')
            if mode == "LIVE":
                self._write_journal(event, bar, cluster, empty, ctx, pattern, signals, confluence, classification)
                if classification != "NO_SETUP":
                    self._write_setup(event, bar, classification, pattern, confluence)
            # T3 Firing: route via gateway (gateway handles SHADOW vs LIVE).
            # 2026-05-22: removed accidental SHADOW gate that blocked all routes.
            if t3_signal:
                self._fire(t3_signal, bar, event)
```

**Acceptance test (regression):**
- `tests/v9/systems/test_footprint_system.py::test_fire_routes_in_shadow_mode`
- Given: event with `mode="SHADOW"` + valid t3_signal + injected mock gateway
- Expect: `mock_gateway.route_setup` נקרא פעם אחת עם `firing_system=3`

**UAT ביציאה לבחינה מסחר אמיתית (RTH):**
- `grep "Footprint.*FIRE routed to gateway" /tmp/backend.log | wc -l` → > 0 (תוך 30 דק' ב-RTH)
- `sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_trades WHERE mode='shadow' AND firing_system=3"` → > 0

---

### 🟡 באג #2 — AMT אינו 90-min rolling, אלא per-bar instant (30-45 דק' + טסט)

**מיקום:** `backend/v9/systems/footprint/footprint_system.py:249-251`

**הקוד הנוכחי:**

```python
        trade_count = int(bar.get("trade_count") or bar.get("ticks_count") or bar.get("n") or 1)
        total_vol = float(bar.get("v") or bar.get("volume") or 0)
        self._last_amt = total_vol / max(trade_count, 1)
```

**הבעיה:** AMT (Average Money Trade) מחושב מהbar הנוכחי בלבד. ה-spec של S2 (`backend/v9/systems/five_min/five_min_system.py:_detect_reactive`) צריך AMT כסף בנצ'מארק של "ממוצע נורמלי" כדי לבדוק `cot > amt`. כשAMT מחושב per-bar, הוא מקפץ באופן רנדומלי בין 0 ל-200+, ולא משמש בנצ'מארק יציב.

**ראיה:** ב-`/api/v9/footprint/current` הAMT מציג 0.0 ב-2026-05-22 08:30 IL. הסיבה: הbar האחרון תקף עם low trade activity.

**התיקון:** החלף את ה-`_last_amt` למחושב כ-90-min rolling window:

```python
# In __init__:
self._amt_window: List[float] = []  # last N bars' per-bar AMT
self._AMT_WINDOW_BARS = 90 // 5  # 18 bars = 90 minutes of 5min bars
# Note: bar type for S3 is tick_reversal (variable interval), so this is approximate.
# Alternative: use a time-based deque with timestamps.

# In _update_flow (replacing line 251):
trade_count = int(bar.get("trade_count") or bar.get("ticks_count") or bar.get("n") or 1)
total_vol = float(bar.get("v") or bar.get("volume") or 0)
per_bar_amt = total_vol / max(trade_count, 1)
self._amt_window.append(per_bar_amt)
if len(self._amt_window) > self._AMT_WINDOW_BARS:
    self._amt_window = self._amt_window[-self._AMT_WINDOW_BARS:]
self._last_amt = sum(self._amt_window) / len(self._amt_window) if self._amt_window else 0.0
```

**Acceptance test:**
- `tests/v9/systems/test_footprint_system.py::test_amt_rolling_90min`
- Given: 20 bars נשלחים, vol=100, trade_count=10 (per_bar_amt=10)
- After bar 18: `_last_amt == 10.0` ± rounding
- After bar 19: window נופל את הראשון, נשאר 18 entries

**UAT:**
- ב-`/api/v9/footprint/current` הAMT צריך להיות > 0 כשיש activity ב-RTH.
- ב-RTH: AMT should be in the range 50-300 typically for MES (verify with Michael).

---

### 🟡 באג #3 — COT (cumulative_delta) לא reset יומי (30 דק' + טסט)

**מיקום:** `backend/v9/systems/footprint/footprint_system.py:81-114` (`hydrate`) + `_update_flow`

**הקוד הנוכחי:**

```python
    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True

        # P-WAVE-D3: Restore cumulative_delta from last journal entry
        restored_delta = 0.0
        try:
            import sqlite3 as _sql
            conn = _sql.connect(self.db_path)
            row = conn.execute(
                "SELECT cumulative_delta FROM v9_footprint_journal ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                restored_delta = float(row[0])
                self._cumulative_delta = restored_delta
                ...
```

**הבעיה:** `hydrate` משחזר את ה-cumulative_delta מהjournal האחרון, **ללא קשר ליום**. אם הbackend רץ כמה ימים, ה-COT נצבר ל-±100K-200K. הspec V3 בעקרון: COT הוא יומי, reset ב-session open.

**ראיה:** ב-2026-05-22 08:30 IL הCOT הוא −144,527 — לא יכול להיות יומי.

**התיקון:**

```python
    def hydrate(self) -> HydrationResult:
        self.current_state["running"] = True
        self.current_state["hydrated"] = True

        # 2026-05-22: COT (cumulative_delta) is a per-session field.
        # Only restore if the last journal entry is from the current session.
        # Session boundary: 18:00 ET previous day (Globex open).
        from datetime import datetime, timezone, timedelta
        from backend.v9.common.session_classifier import SessionClassifier
        sc = SessionClassifier()
        session_open = sc.current_session_open_utc()  # NEW HELPER; if not exists, compute inline
        # Fallback inline: 22:00 UTC = 18:00 ET previous day if before 22:00 UTC today
        # (verify the correct helper exists or add one)

        restored_delta = 0.0
        try:
            import sqlite3 as _sql
            conn = _sql.connect(self.db_path)
            row = conn.execute(
                "SELECT cumulative_delta, created_at FROM v9_footprint_journal ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                last_ts_str = row[1]
                last_ts = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                if last_ts >= session_open:
                    restored_delta = float(row[0])
                    self._cumulative_delta = restored_delta
                    self.current_state["cumulative_delta"] = restored_delta
                    self.current_state["cot"] = restored_delta
                    logger.info("[Footprint] Hydrated COT from current session: %.1f", restored_delta)
                else:
                    logger.info("[Footprint] Last journal is from previous session — starting COT at 0")
                    self._cumulative_delta = 0.0
        except Exception as e:
            logger.warning("[Footprint] Hydration restore failed: %s", e)
        ...
```

**אם `SessionClassifier.current_session_open_utc()` לא קיים** — להוסיף אותו ל-`backend/v9/common/session_classifier.py` כjmethod helper. אם זה דורש שינוי גדול, השתמש בlogic inline.

**Acceptance test:**
- `tests/v9/systems/test_footprint_system.py::test_cot_resets_at_session_open`
- Given: journal entry מ-`2026-05-21 14:00 UTC = 10:00 ET` + hydrate נקרא ב-`2026-05-22 09:00 UTC = 05:00 ET` (אחרי 22:00 UTC = session open)
- Expected: `_cumulative_delta == 0.0` (reset)

**UAT:**
- בכל בוקר ET (אחרי 18:00 ET = 22:00 UTC = 01:00 IL בבוקר הבא), `/api/v9/footprint/current` צריך להראות `cot` קרוב ל-0 בתחילת היום.

---

## סדר עבודה מוצע

1. **תיקון באג #1 קודם** — סיכון אפס, ערך גבוה (S3 יורה מיד). 15 דק' + 5 דק' regression test.
2. **אימות #1 ב-RTH** או POST סינתטי — לוודא שS3 יורה לפני ממשיכים.
3. **תיקון באג #2** — הוסף 90-min rolling. צריך זהירות עם session boundary (אולי לאפס את ה-window גם ב-reset?).
4. **תיקון באג #3** — הוסף session-aware hydration.
5. **דוח חזרה ב-`docs/reports/PROMPT_P31_S3_S2_FIRING_FIX.md`** עם:
   - diff סופי לכל שלושת השינויים
   - מספרים לפני/אחרי (S3 trades count ב-DB, AMT range, COT range)
   - 4 צירי UAT (Quality / Recency / Cardinality / Latency)
   - איזה issues נשארו (לדוגמה S2 fire conditions עדיין צריך 4-bar pattern — זה לא נפתר ע"י #2+#3)

---

## אזהרות חשובות

- **אל תיגע ב-WoodiesSystem או ב-FiveMinSystem** — הם עובדים כמו שצריך (Woodies יורה, FiveMin מוכן וחוסם ע"י S3).
- **אל תשנה את הGateway** — הוא מטפל ב-SHADOW/LIVE routing נכון.
- **אל תשנה את הspec של 4-bar pattern** ב-FiveMin — זו בעיה נפרדת.
- **TradeManager לא משתנה** — stop/T1/T2/T3 logic נשאר כמו ש-S3 יזריק (הוא מחשב אותם פנימית).
- **אל תרוץ commits אוטומטית** — תפנה אל Michael לpush בעצמו.

---

## הקשר נוסף

- `frontend/v9/src/v9/types/index.ts` כבר עודכן (Cursor 2026-05-22): S1=observer, S3=firing.
- ה-Master Matrix V1.0 (`backend/v9/systems/wrappers.py:8-14`) הוא המקור הרשמי.
- חקירת ה-bug נעשתה ב-`docs/reports/PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md`.

**עדכן את `docs/handoff/P31_TASK_BOARD.md` עם רשומת CC חדשה** ב"עדכון לוח" אחרי שהתיקון נסגר.
