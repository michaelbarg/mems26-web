# SHADOW Status Board — לוח משימות לשער SHADOW

**נגזר מ:** `docs/plans/STATUS_BOARD.md` (מעודכן 2026-05-28 21:50 IL)
**מעודכן עם:** STATUS_BOARD ראשי `b6ebd08` (EOD שישי 16:22) · 7-bug batch `99671e4` · P31 `8bedb74`→`1375a95` · P31.1 fix-up (101 tests) · DLL frozen-tail `ada6c88`/`cc9bd8f` · Bug E+S2 None `e3b986c`
**עודכן בפועל:** 2026-05-29 16:35 (שישי — SHABBAT CLOSE)

**מקרא חשיבות:** 🔴 חוסם · 🟠 גבוה · 🟡 בינוני · 🟢 נמוך
**מקרא סטטוס:** ✅ הושלם · ⏳ בתהליך · 🟡 ממתין ל-RTH · ⬜ פתוח · ⛔ חוסם פעיל

---

## א. שער SHADOW (P-S0) — קריטריוני הפעלה

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 1 | Phase A — 14 packages built | כל חבילות Pipeline 1 (0–8,6 + Consolidation; 4a/4b deferred) נבנו | 🔴 | S2 / TradeManager | ✅ הושלם 25/5 |
| 2 | pytest tests/v9/ green | waiver ניתן 26/5 (1694 pass). נותרו ~11 כשלים pre-existing מ-day_type/IB | 🟠 | בדיקות / day_type | ⬜ פתוח (waiver) |
| 3 | UAT 4 צירים על `/cockpit/systems-snapshot` | Quality · Recency · Cardinality · Latency — בדיקת ה-snapshot החי | 🔴 | API / כל המערכות | 🟡 ממתין ל-RTH |
| 4 | L4-2 Recency (TPO) | `endpoint.latest_ts == MAX(ts) DB` עבור TPO | 🟠 | TPO | 🟡 ממתין ל-RTH |
| 5 | L4-3 Cardinality (Five-Min bars) | `len(rows) == requested_limit` עבור bars 5-דק | 🟠 | five_min / bars | 🟡 ממתין ל-RTH |
| 6 | L4-4 Latency (כל ה-endpoints) | זמן תגובה מתחת לסף המתועד (<100ms health) | 🟠 | API | 🟡 ממתין ל-RTH |
| 7 | G4 smoke trades | ירי בדיקה לכל חבילה (1,2a,2bc,3a,3b,5a,5b,5c,8,6) ב-RTH | 🔴 | Gateway / כל ה-patterns | 🟡 ממתין ל-RTH |
| 8 | 60 דק' ירוק · zero open warnings | soak רציף אחרי UAT ללא אזהרות פתוחות | 🟠 | כלל המערכת | ⬜ פתוח |
| 9 | Michael sign-off | אישור מפורש להפעלת SHADOW | 🔴 | החלטה | ⬜ פתוח |

---

## ב. חוסמים פתוחים (Open Items Pre-LIVE)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 10 | DLL frozen-tail | תוקן: clamp-detect ב-`mapIdx` (Option A). DLL נבנה מחדש **v9.4.3-p31.1**, Parts 1+2+3 DONE, offline UAT עבר 4 צירים. **נותר: אימות RTH חי — Phase B מתוך `CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK` ביום ראשון 16:30–23:00 IL** (אמת IB lock + CCI לא frozen) | 🔴 | sc_study / Woodies S4 | ✅ קוד+DLL rebuilt · 🟡 ממתין ל-UAT חי (ראשון) |
| 11 | `all_bars` current_bar routing | העדפת `current_bar` החי על פני `history[-1]` הקפוא | 🟠 | woodies / bars | ✅ תוקן 05-29 (7-bug batch) |
| 12 | TZ Chicago→NY ב-bridge | `base_stream.py` עבר ל-`America/New_York` (Sierra=ET) | 🟠 | bridge | ✅ תוקן 05-29 |
| 13 | woodies_chart_routes DST bomb | hardcoded `+5*3600` שאינו מודע ל-DST | 🟠 | woodies_chart_routes | ✅ הוסר 05-29 |
| 14 | S2 `current_day_type=None` skip | נוספה אזהרה rate-limited (1/דק') ב-DAY_TYPE_MODE — ה-skips של Pkg 5a/5b/5c גלויים בלוג. **observability בלבד**; שחזור day_type ב-restart עדיין דרך #40 | 🟠 | five_min S2 | ✅ אזהרה נוספה · 🟡 שחזור עדיין פתוח |
| 15 | Status enum sync | `/api/v9/status.day_type` מדווח PENDING/UNKNOWN בעוד שורת ה-DB מסווגת | 🟠 | day_type / consumer | ⬜ פתוח (verify) |
| 16 | 11 כשלי pytest pre-existing | מ-day_type/IB; חוסמים שער "all green" | 🟠 | בדיקות | ⬜ פתוח |
| 42 | Bug E — entry temporal guard | `BarLevelDetector.on_bar` מדלג על bars שהתחילו לפני `entry_ts` — מונע `fill_ts < entry_ts` (stop/target רטרואקטיבי). 3 בדיקות עברו | 🟠 | trade_manager / detector | ✅ תוקן 05-29 (`e3b986c`) |
| 43 | Bug C — fill price accuracy | stop/target נרשם במחיר פתיחת ה-bar במקום מחיר ה-fill בפועל — השפעת PnL | 🟠 | trade_manager / detector (`bar_level_detector.py`) | ⬜ פתוח (HIGH לפני LIVE) |
| 44 | אימות hydration timing חי | האזהרה ב-#14 קיימת — אך לאמת live ב-Phase B שה-day_type מגיע בזמן ולא מדלג | 🟠 | five_min S2 / logs | 🟡 ממתין ל-RTH (ראשון) |

---

## ג. שער איכות נתוני SHADOW (Shadow Data Quality)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 17 | ניקוי backtests חשודים | 21/5 + 22/5 זוהו כ-SUSPECT BACKTEST (100 trades/hr) | 🟠 | v9_trades / shadow | ✅ נוקה (טבלה=0) |
| 18 | חקירת fire-rate גבוה | 25/5–26/5 (145/74 trades/יום) — אחרי שהתיקונים מאומתים | 🟡 | five_min / dispatcher | ⬜ פתוח |
| 19 | ≥200 trades נקיים אחרי תיקון | מינימום נתוני SHADOW נקיים לפני הערכת איכות LIVE | 🔴 | shadow / כל ה-patterns | ⬜ פתוח |
| 20 | repopulate v9_trades | הטבלה אופסה ל-0; תמלא מחדש כשהתיקונים פרוסים | 🟡 | v9_trades | ⏳ בתהליך |

---

## ד. אימות Pipelines (תנאי להשלמה)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 21 | Pipeline 1 (S2) — G4 UAT | כל החבילות נבנו; smoke trades + soak חסרים (ראה #7) | 🔴 | five_min S2 | 🟡 ממתין ל-RTH |
| 22 | Pipeline 2 (S4 Woodies) | SHADOW APPROVED · W-10 LIVE block cleared. נותר: CC verification batch + סקירת נתוני SHADOW ≥200 | 🟠 | woodies S4 | ⏳ בתהליך |
| 23 | Pipeline 3 (S1 Day Type) verify | דוח אימות מ-Michael | 🟡 | day_type S1 | ⬜ פתוח |
| 24 | Pipeline 4 (S3 Footprint) verify | דוח אימות מ-Michael (כולל O-4 entry/stop spec) | 🟡 | footprint S3 | ⬜ פתוח |

---

## ה. רצף P31 — Daily Reset / Archive (נחת 05-29)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 25 | P31-A consumer write-gate | מסרב UPSERT של `UNKNOWN/PENDING` | 🟠 | day_type / consumer | ✅ committed |
| 26 | P31-B SessionBoundaryManager | reset של state-machine בגבול 18:00 ET | 🟠 | day_type / session | ✅ committed |
| 27 | P31-C et_today() | החלפת 13× `date.today()` + SQLite `date('now')` בעזר ET-aware | 🟠 | כל נתיב התאריך | ✅ committed |
| 28 | P31-D RiskValidator.daily_reset wiring | חיווט reset יומי ל-rollover | 🟡 | risk / gateway | ✅ committed |
| 29 | P31-E TPO session_id via et_today | `session_id` מבוסס ET | 🟡 | TPO | ✅ committed |
| 30 | P31-F five_min hydrate-before-return | hydrate של day_type לפני early-return לילי | 🟡 | five_min | ✅ committed |
| 31 | P31-G logging debug→warning | העלאת לוגי כשל DayType ל-warning | 🟢 | logging | ✅ committed |
| 32 | P31-H reject ROLLED_OVER | endpoints `/current` דוחים שורות ROLLED_OVER | 🟡 | API / day_type | ✅ committed |
| 33 | Migration 019 (archive infra) | 4 טבלאות ארכיון · `v9_session_meta(last_rollover_date)` · 5 עמודות `is_synthetic`. הורץ על `mems26_local.db` החי | 🟡 | DB / migrations | ✅ הוחל (M19) |
| 33a | P31.1 fix-up — 9 gaps | T1–T6: rollover ground-state-safe · migration על DB חי · SBM first-bar fallback+archive+truncate · 2× SQLite `date('now')` · 4 קבצי בדיקה חסרים. **101/101 עברו · Bug B נסגר** | 🟠 | day_type / session / DB | ✅ DONE (`P31_1_FIXUP_FINAL`) |

---

## ו. רצף P32 — Bridge TZ + sot_health cleanup  (prompt כתוב, **טרם נשלח**)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 34 | P32-I tick_reversal future-ts | תיקון root של `+5h` (~540K שורות עתיד) + per-stream `DISABLE_CHICAGO_TS_FIX` | 🟠 | bridge / tick_reversal | ⏳ prompt כתוב, לא נשלח |
| 35 | P32-J repoint sot_health TPO | מ-`v9_tpo_sessions` המת ל-`v9_tpo_history` | 🟡 | build_status / TPO | ⏳ prompt כתוב, לא נשלח |
| 36 | P32-K הוספת S3 ל-sot_health map | footprint + tick_reversal למפת הבריאות | 🟡 | build_status / S3 | ⏳ prompt כתוב, לא נשלח |
| 37 | P32-L ניקוי טבלאות יתומות | הסרת `v9_audit_events` · `v9_trade_management_log` | 🟢 | DB | ⏳ prompt כתוב, לא נשלח |

---

## ז. פריטי MED — לפני LIVE (לא חוסמי SHADOW)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 45 | `min_r_t1_threshold` test | בדיקה פרמטרית 0 / 0.5 / 1.0 לפני מעבר ל-1.0 ב-LIVE | 🟡 | dispatcher / tests | ⬜ פתוח |
| 46 | Day-type matrix A2 advisory | כרגע advisory — לא enforced | 🟡 | day_type | ⬜ פתוח |
| 47 | Lunch skip 12:00–13:30 ET | סינון שעת צהריים (DEMO-2) | 🟡 | filters | ⬜ פתוח |
| 48 | FOMC ±90min skip | חלון הימנעות סביב FOMC (DEMO-2) | 🟡 | filters / news | ⬜ פתוח |
| 49 | sentinel 2099 rows | שורות `ts='2099-…'` ב-`v9_bars_5min_woodies` (inspector מוקשח, אך הזרם עדיין כותב) | 🟡 | bridge / build_status | ⬜ פתוח |

---

## ח. שלבים ממתינים (Daily Reset / Demo / post-SHADOW)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 50 | Phase 3 — Archive endpoints | `/api/v9/archive/...` — prompt טרם נכתב | 🟡 | API / archive | ⬜ פתוח |
| 51 | Phase 4 — DemoReadiness UI | פאנל + test chain — תלוי Phase 3 | 🟡 | frontend / demo | ⬜ פתוח |
| 52 | Phase 5 — UAT end-to-end + sign-off | תלוי Phase 4 | 🟠 | כלל המערכת | ⬜ פתוח |
| 53 | Tiered Fire Status (Plan A++) | design ב-`DAILY_RESET_AND_ARCHIVE_DESIGN.md` §13 — שלב פריסה TBD | 🟢 | UI / fire status | ⬜ פתוח |

---

## ט. Follow-ups בתור (לא התחילו)

| מס״ד | כותרת | פרטים | חשיבות | במה נוגע | סטטוס |
|------|-------|-------|--------|----------|-------|
| 38 | rollover עמודת status ב-consumer | כך ש-`/api/v9/status.day_type` תואם למכונה החיה (קשור #15) | 🟠 | day_type / consumer | ⬜ פתוח |
| 39 | pipe opening_type דרך S1→S2 | תיקון cosmetic NA מול INDETERMINATE ב-payload | 🟢 | day_type → five_min | ⬜ פתוח |
| 40 | 6-bars replay ב-restart אמצע-סשן | `day_type_seed.py` — שחזור OPEN_AUCTION_IN במקום INDETERMINATE | 🟡 | day_type / seed | ⬜ פתוח |
| 41 | W-10 TimeStop — סטטוס סופי | מושבת (Option B) — Constitution V3 Layer 4 הוא ה-authority היחיד; root תוקן ב-05-29 | 🟡 | woodies / trade_manager | ✅ הוכרע |

---

## bring-up ליום ראשון (לפני RTH)

מתוך ה-STATUS_BOARD הראשי:

```
□ 1. screen -r mems26_backend  (verify running)
□ 2. curl http://localhost:8000/health
□ 3. python3 scripts/sot_health.py --strict
□ 4. v9_session_meta.last_rollover_date == היום ET
□ 5. Sierra Chart פתוח, Chart 12 (Woodies) פעיל
□ 6. DLL Input 19 = 12 ב-MES_AI_DataExport study
□ 7. Phase A מ: CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md
□ 8. אחרי 09:30 ET: Phase B — אמת IB lock + CCI לא frozen (#10, #44)
```

---

## סיכום מצב (snapshot · 05-29 16:35 — SHABBAT CLOSE)

- **הושלם היום:** רצף P31 המלא + **P31.1 fix-up (101/101 · Bug B נסגר · Migration 019 הוחל על DB חי)** · **DLL frozen-tail (קוד + DLL rebuilt v9.4.3-p31.1 · offline UAT)** · Bug E entry guard · S2 None observability.
- **החוסם הקריטי שנותר (#10):** אימות RTH חי של תיקון ה-frozen-tail — Phase B ביום ראשון 16:30–23:00 IL. הקוד נבנה ועבר UAT offline; חסר רק אימות בשוק חי.
- **HIGH פתוח לפני LIVE:** Bug C (דיוק fill price · #43) · P32 (כתוב, לא נשלח · #34–37) · אימות hydration חי (#44).
- **ממתין ל-RTH:** UAT 4 צירים · G4 smoke trades · soak 60 דק' (#3–8, 21).
- **חוסם נתונים:** ≥200 trades נקיים (#19) לפני הערכת איכות.
- **לפני sign-off:** סגירת 11 כשלי pytest (#16) + אימות #15.

> מסונכרן מול `docs/plans/STATUS_BOARD.md` `b6ebd08` (EOD שישי 16:22). הערה תפעולית מהבורד הראשי: ה-backend היה למטה מ-28/5 19:59 עד שהופעל מחדש 29/5 13:40 (פער תפעולי, לא רגרסיה).

> הערה: ה-STATUS_BOARD המלא (`docs/plans/STATUS_BOARD.md`) עדיין מעודכן ל-05-28 21:50 ואינו משקף את עבודת 05-29 — מומלץ לעדכן אותו במקביל.
