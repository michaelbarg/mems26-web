# OPEN_PARITY 2026-10-18 — T-588 פריט 1, **חצי-הלייב בלבד** (חלקי במוצהר)

**נמדד:** cowork-dev, ריצה 327, 18.10 23:05→23:20 IL (יום ראשון, שוק סגור, אפס עסקאות).
**הזמנה:** `docs/handoff/cc_orders/CC_ORDER_2026-10-18_OPEN_PARITY.md` · **בעלים:** Cursor / fix-agent.
**מצב:** פריט 1 **חצי** — צד-הלייב של הטבלה נמדד במלואו ונסגר; **צד-הריפליי NOT-DONE**, הסיבה
מדודה ולא משוערת (§4). פריטים 3/4/5 לא נפתחו. פריט 2 נסגר כבר ב-10:59 בקומיט `39f7f1c8`.

⚠️ **הקובץ הזה אינו "ההזמנה בוצעה".** מי שמרים את ההזמנה: §4 אומר מה חסר ומה לבדוק לפני.

---

## 1 · צד-הלייב — הפלט הגולמי (Rule 5)

```bash
awk '$1=="2026-10-06" && $2>="16:25:00" && $2<="17:15:00"' /tmp/backend.err.log \
 | grep -E "TREE_V3|\[DayType\]|locked opening|opening_type=|OpeningDetector"
```
```raw
16:30:05 [gateway.trading_gateway] TREE_V3 FAMIR LONG 7863.5 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Trend_Normal)]
16:30:06 [day_type.state_machine] FIX-9 RTH-boundary reset: dropping carried pre-RTH state (day_type=UNKNOWN, bars=66) — fresh session, stages decide
16:40:07 [gateway.trading_gateway] TREE_V3 CEILING_FLIP_TOUCH2 LONG 7865.25 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Variation)]
16:45:07 [gateway.trading_gateway] TREE_V3 OPENING_EXTREME_REJECT LONG 7867.5 → TAKE [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=REVERSAL]
16:50:03 [gateway.trading_gateway] TREE_V3 OPENING_DRIVE LONG 7871.5 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(WITH_DRIVE)/edge=*(none)]
17:00:06 [mems26] [DayType] Classification changed: UNKNOWN -> Trend_Normal (conf=0.35)
17:05:03 [gateway.trading_gateway] TREE_V3 INITIATIVE_LONG LONG 7881.0 → SKIP [hour=*(17)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(BREAK)/edge=*(none)]
```

**זמינות-הראיה (נבדקה, לא הונחה):** `/tmp/backend.err.log` = 90,530,909 בתים, מחזיק
`2026-10-02` והלאה, מהם **67,563 שורות של 06.10** ⇒ חלון-הפתיחה של 06.10 מדיד **מהלוג החי**,
לא מציטוט ההזמנה. 528 שורות `TREE_V3` בלוג כולו.

## 2 · הטבלה — מה שמדיד היום

| פוש | מועמד-העץ | ot-לייב | day_type-לייב | החלטת-לייב | ot-ריפליי | day_type-ריפליי |
|---|---|---|---|---|---|---|
| 16:30:05 | FAMIR LONG | `OPEN_AUCTION_IN` | `Trend_Normal` | SKIP | — NOT-DONE | — NOT-DONE |
| 16:40:07 | CEILING_FLIP_TOUCH2 | `OPEN_AUCTION_IN` | `Variation` | SKIP | `UNKNOWN`\* | `FORMING`\* |
| 16:45:07 | OPENING_EXTREME_REJECT | `OPEN_AUCTION_IN` | `Variation` | **TAKE** | — NOT-DONE | — NOT-DONE |
| 16:50:03 | OPENING_DRIVE LONG | `OPEN_AUCTION_IN` | `Variation` | SKIP | `OPEN_REJECTION_REVERSE`\* | `FORMING`\* |
| 17:05:03 | INITIATIVE_LONG | `OPEN_AUCTION_IN` | `Variation` | SKIP | — NOT-DONE | — NOT-DONE |

\* שתי שורות-הריפליי היחידות שיש — **מצוטטות מההזמנה**, לא נמדדו בריצה הזו. אסור לקרוא
לטבלה "מאומתת דו-צדדית" לפני §4.

## 3 · שני ממצאים שההזמנה לא רשמה

**(א) הלייב לא סירב לכל חלון-הפתיחה — ב-16:45:07 הוא לקח.** `OPENING_EXTREME_REJECT LONG
7867.5 → TAKE [kind=REVERSAL]`. ההזמנה מנסחת "הריפליי לוקח, הלייב מסרב"; זה נכון
ל-`OPENING_DRIVE` ב-16:50, **לא** לחלון כולו. ⇒ `OPEN_AUCTION_IN` + `Variation` אינם
חוסמים-כשלעצמם: אותו צמד-תוויות בדיוק ייצר TAKE אחד ו-SKIP ארבעה, וההבדל הוא ב-`kind`
(`REVERSAL` עבר · `WITH_DRIVE`/`BREAK` + `edge=none` נפלו). מי שמייחס את ההחמצה לתווית-היום
לבדה — מייחס לשדה הלא-נכון.

**(ב) הפער בין שני מקורות-התווית אינו נסגר אחרי שהמכונה מסווגת.** ההזמנה כתבה
"16:40–17:05 Variation בגייטוויי בעוד המכונה UNKNOWN עד 17:00". המדידה מחדדת: ב-`17:00:06`
המכונה עברה ל-`Trend_Normal`, ובכל זאת ב-`17:05:03` — **חמש דקות אחרי** — הגייטוויי עוד
מדווח `day_type=*(Variation)`. כלומר זה **לא** "המכונה עוד לא מוכנה" אלא מקור שונה שאינו
מתכנס גם כשיש למכונה תווית. זה מחזק את פריט 3 ומצמצם אותו (§4).

## 4 · מה חסר, ולמה — NOT-DONE מפורש

**חצי-הריפליי של פריט 1 לא בוצע. הסיבה מדודה:** הפריט דורש (א) הוספת לוג-INFO של
`_cls_result` ל-`s1_on_bar`, שקיים **רק** ב-`scripts/fwd_harness.py:790`, ו-(ב) הרצת
`fwd_harness.py --session 2026-10-06`. שני המשטחים **תפוסים בסשן אחר, בזמן-אמת**:

```raw
23:13:27  49229?  —  ps: 46909 00:19 74.9% fwd_harness.py --session 2023-05-08 --variant hist_k --out harness_out/t466
                      47021 00:13 69.9% fwd_harness.py --session 2023-05-11 --variant hist_k --out harness_out/t466
23:14:56  ps:      49229 00:21 24.0% fwd_harness.py --session 2023-05-08 --variant hist_k --out harness_out/t466
                   49468 00:11 72.6% fwd_harness.py --session 2023-05-11 --variant hist_k --out harness_out/t466
⇒ שני עובדים במקביל, ה-PID מתחלפים כל ~20-30 שנ' ⇒ סריקה רצה, לא ריצה בודדת
git log -1 -- scripts/fwd_harness.py ⇒ 3e1a9b40 10-18 19:52 "T-597: harness crashed on 2026-08-07…"
```

1. **עריכת `fwd_harness.py` הייתה נבלעת בסריקה החיה.** כל עובד חדש נטען מהקובץ שעל הדיסק;
   הוספת לוג באמצע סריקה משנה בשתיקה את הפלט של סוכן אחר על מאות סשנים. הקובץ גם נמצא
   בבעלות-עריכה טרייה של אותו סשן (`19:52` היום).
2. **`harness_out/t466/` הוא גם יעד-הכתיבה של הסריקה** — ובדיוק הספרייה שההזמנה קוראת ממנה
   (`t567ref_2026-10-06.json`). הרצה שלישית לתוכה = התנגשות-פלט.
3. **המכונה בלחץ-זיכרון:** `unused RAM 121M < 400M` · `swap used 2,962M/4,096M` · load
   `6.08 6.57 6.36` על 8 ליבות, בעוד שני העובדים ב-~75% CPU כל אחד.

**זה הכלל-של-תור-הלילה לפי רוחו, לא לפי אותיותיו:** המבחן הפורמלי ("קומיט לא-launchd מ-23:00+
או שורת-claim") החזיר **פנוי** — הקומיט היחיד מ-23:00 הוא `4b40a9ef 23:05:22 eod-handoff`,
שהוא launchd+data-only, ואין שורת-claim. אבל ההתנגשות שהכלל נועד למנוע **נמדדה ישירות
ב-`ps`**. ⇒ לא נלקחה בעלות ולא נפתח סוכן-משנה. ⚠️ **מלכודת 38** נרשמה ב-`COWORK_DAILY_READ`.

**הצעד-הבא לבעלים (Cursor/fix-agent), בסדר הזה:**
1. `ps -eo pid,command | grep fwd_harness` ⇒ **אפס** לפני כל נגיעה בקובץ או ב-`harness_out/t466/`.
2. לוג-INFO ב-`s1_on_bar` (`fwd_harness.py:790`): `opening_type` · `day_type` · `session_date`
   לכל פוש, ואז `--session 2026-10-06` (+ `--restart-at 15:40` לשחזור הציטוט) ⇒ למלא את
   חמש שורות-ה-NOT-DONE בטבלה §2.
3. פריט 3 מצומצם לשאלה אחת: `_dp_dt_raw = _dp_gldt()` ⇒ `get_live_day_type()`
   (`backend/v9/services/trade_context.py:565`) — **מה הוא החזיר ב-16:40 וב-17:05 ב-06.10**,
   כשהמכונה הייתה `UNKNOWN` ואז `Trend_Normal`? ההיסטרזיס `_dp_hyst`
   (`trading_gateway.py` ~1130-1156, "hold Trend") הוא מועמד-מכניזם ל-17:05 אך **לא נמדד**,
   והערך-הגולמי אינו בלוג ⇒ לא מיוחס (כלל 1).

## 5 · ציר-הקוד — אומת ב-HEAD, קריאה-בלבד

```raw
backend/v9/gateway/trading_gateway.py
  210  def _resolve_live_cls()                       ← מקור 1: app.state.last_cls_result
  226      return _cls_session_guard(_r)              ← T-588 פריט 2, קיים ב-HEAD
  231  def _cls_session_guard(result, today_iso)      ← טהור; session_date ≠ היום-ET ⇒ None
  234      os.getenv("CLS_RESULT_SESSION_GUARD_V1","0") not in ("1","true","yes") ⇒ מחזיר כמו-שהוא
 ~1160  _dp_ot = "UNKNOWN"                            ← ברירת-מחדל
 ~1167  if _opening_type_locked: _dp_ot = _opening_locked_val    ← T-314, מקור מועדף
  1177  _dp_cls_ot = _resolve_live_cls()              ← הנפילה-אחורה שאכלה את 06.10
```

**שרשרת-השורש, שלושה משטחים בלתי-תלויים:**

| משטח | מדידה |
|---|---|
| ספירת-נעילה | `grep -c "locked opening"` ⇒ 06.10 = **0** · 08.10 = **1** · 09.10 = **1** |
| לוג-הגייטוויי | `opening_type=OPEN_AUCTION_IN` בכל חמשת הפושים של 06.10 |
| סדר-הקוד | ‏`1160` ברירת-מחדל → `1167` נעילה (לא קרתה) → `1177` `last_cls_result` הישן |

⇒ בלי נעילת-T-314, `_dp_ot` נופל למקור 1, ושם — לפני `39f7f1c8` — שכנה התוצאה של **05.10**
בלי בדיקת `session_date`. הדגל `CLS_RESULT_SESSION_GUARD_V1` **כבוי כברירת-מחדל** (`"0"`)
⇒ ההתנהנות זהה-בייט. **אפס הדלקה בריצה הזו** (פסיקה היא של מייקל).

## 6 · אפס-נגיעה

ריסטארט · דגלים · דגלי-גודל · `.env` · פוזיציות · פקודות · `op=EXIT` · קוד-פרודקשן · DLL ·
סיירה · עץ-ההחלטות · כתיבות-DB · `fwd_harness.py` · `harness_out/` · הטלפון.
`ruled_contracts() = 1` נקרא לדיווח בלבד. 14 הקבצים-המלוכלכים של הסשן האחר לא נוגעו —
הועלו לאינדקס המסמכים שלי בלבד, תוספות בלבד.
