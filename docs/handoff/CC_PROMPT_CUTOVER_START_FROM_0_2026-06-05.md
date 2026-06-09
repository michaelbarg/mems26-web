# CC — START HERE · Cutover "start SHADOW from 0 today" (B-13 + G1) · 2026-06-05

פסקת-פתיחה ל-CC (העתק-הדבק). Michael אישר את ה-scope. כל "DONE" = paste פקודה +
raw output (Rule 5) + סעיף NOT-DONE.

---

אתה מבצע חיתוך מתואם: תיקוני-שורש ל-B-13 + עמודות G1, ואז reset ל-0 והתחלת
ריצת-shadow טרייה. **קרא קודם:** `CLAUDE.md` · `docs/handoff/CC_HANDOFF_CONTRACT.md` ·
`docs/handoff/CC_PROMPT_B13_REMEDIATION_FULL_2026-06-05.md` ·
`docs/handoff/G1_WORK_PLAN_2026-06-05.md` + `docs/handoff/CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md` ·
עדות-האבחון: `docs/handoff/CC_PROMPT_B13_DIAGNOSE_ONLY_2026-06-05.md` + `docs/reports/BUG_LOG_2026-06-04_05.md`.

**מאומת ע"י Cowork (אל תסרוק מחדש — בנֵה על זה, אמת בריצה):**
- B-13 שורש: בכניסה (`bars.py`) יש שומר-עתיד (`ts>now+2m`, L308) אבל **אין שומר-staleness**;
  `_route_bar` (L345) שולח `last_valid_bar`; בר-6/5 ישן (exact-tick 7341/7365.75) עבר ל-S2.
  ב-`five_min_system.process_bar` אין מעבר DAY_TYPE→OVERNIGHT (L760-779), אז S2 נשאר חמוש אחרי הסגירה.
- G1 §0 (כל 7 העסקאות, דרך API): `has_killzone=has_daytype=has_woodies=7/7`;
  `cross_context`=מערך באורך-1; הנתיב `cross_context[0].systems.{killzone_system,day_type_machine,woodies_system}`.
  ⇒ promote-able. **backfill מבוטל** (מוחקים את העסקאות, מתחילים מ-0).

## רצף החיתוך — בסדר הזה בדיוק

**שלב 1 · כל הקוד נוחת (לפני reset):**
1. **B-13 D2** — שומר-staleness ב-`bars.py` POST `/5min` (ואודיט שאר ה-POST שמריצים `_route_bar`):
   דחיית בר עם `ts` ישן מהאחרון-שנקלט ביותר מ-interval אחד, ו/או מחיר רחוק מהשוק-החי מעבר ל-`STALE_PRICE_BAND`.
   נדחה = לא נכתב ולא מנותב. regression: בר-6/5 ישן → נדחה; הסרת-השומר → RED.
2. **B-13 D3** — session קנוני **America/Chicago 08:30–15:00** (Rule 4, מקור-אמת יחיד):
   ירי חסום מחוץ-לחלון **בכל המערכות ובכל mode כולל SHADOW**; הוסף מעבר DAY_TYPE→OVERNIGHT ב-15:00 CT
   ב-S2 **ואמת S3/S4 ושאר המערכות** לאותו קצה; `entry_ts` ב-UTC (תצוגה CT). regression: setup ב-15:01 CT → אין ירי בשום mode.
   (הערה: `bars.py:33` מאריך ingest ל-17:00 ET=16:00 CT — buffer-דאטה מותר, אבל **ירי אסור** אחרי 15:00 CT.)
3. **G1** — `day_type_at_entry`/`pattern_id_at_entry`/`session_at_entry` (String, nullable, index) ב-`V9Trade`;
   migration אלמביק (downgrade מסיר); אכלוס-בכניסה ב-`trading_gateway` בין `_capture_cross_context`
   ל-`_persist_trade`, **מאותו** `cross_context` דרך helpers של `trade_context.py` (ערך זהה ל-`extract_trade_display`),
   מקור שותק→NULL, אפס סינתזה; טסט-litmus: אין killzone→NULL (RED על fallback). **בלי backfill.**

**שלב 2 · בסדר:**
4. `alembic upgrade head` → paste + `\d v9_trades` (3 עמודות nullable+indexed).
5. **כל ה-regressions ירוקים** (B-13 + G1) — paste raw pytest, הוכחת RED→GREEN.
6. **⛔ STRATEGIC-STOP → דווח ל-Michael.** אל תמשיך ל-reset/restart בלי אישורו. paste את כל ה-raw output.

**שלב 3 (רק אחרי אישור Michael):**
7. **reset ל-0** — truncate `v9_trades` + `v9_bars_5min`/`_continuous`/`_woodies` + `v9_five_min_state`.
8. **restart backend עם `export S3_MUTE=1`** (ב-`scripts/start_all.sh`, **בלי לגעת** ב-CLOUD_URL/KeepAlive) + ingestion טרי מ-Sierra.
9. **אימות נקי (Rule 5, paste):** soak מקבילי ≥10ד' 0 errors/0 deadlocks · `[Footprint] S3_MUTE active` ואין `firing_system=3` ·
   אין ירי מחוץ 08:30–15:00 CT · עסקה חדשה עם 3 עמודות-G1 מאוכלסות · `SELECT COUNT(*),MIN(ts),MAX(ts)` נקי לכל טבלת-בארים · S2 mode=OVERNIGHT אחרי 15:00 CT.
10. עדכן `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (finding+fix+verification, מתוארך). דווח ל-Michael לפני שהריצה "מאומתת".

## ערכים שדורשים אישור Michael (אל תמציא risk numbers)
`STALE_PRICE_BAND` + סבילות-ה-staleness (כמה intervals). הצע ברירות-מחדל בדוח, Michael מאשר לפני שזה חי.

## גבולות קשיחים
smallest correct change · regression לכל תיקון · אל תיגע CLOUD_URL/KeepAlive/risk-VALUES מעבר ל-session-gate ·
localhost-PG בלבד · **אל תבנה G2–G7 / D4 price-sanity (נדחה) / frontend** · אל תאגד B-11/B-14/Frontend-Phase1 (threads נפרדים).
Cowork יצליב כל פלט גולמי מול קוד/git/API.

---
