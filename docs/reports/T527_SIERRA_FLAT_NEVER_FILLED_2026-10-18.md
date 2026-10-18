# T-527 · `SIERRA_FLAT` בלי מחיר — השורש: ארבע מתוך 13 הן כניסות שמעולם לא בוצעו, והספרים (ו-`broker_truth`) קוראים להן "עסקה לא-מתומחרת" — BRIEF §3.4 (תיקון-שורש + מבחני-רגרסיה)

**נכתב:** 2026-10-18 10:4x IL · fix-agent (סוכן-הכיול 23:40; הריצה של ליל 17→18.10 נורתה באיחור ב-09:55 — המק לא היה מחובר כל השבוע, ריצת-cowork 307 "נמשכה 7 ימים") · יום ראשון, שוק סגור.
**סטטוס:** נבנה-כבוי (דגל `POSITION_TRUTH_UNFILLED_CANCEL_V1`, ברירת-מחדל זהה-בייט, 6 מבחנים) + תוקן — ממתין לאימות (`scripts/broker_truth.py`: קבוצת-המועמדים + קריסה על יום-ידני-בלבד, 6 מבחנים) · flag_guard PASS (274) · אפס נגיעה: `.env`, RULED_FLAGS, עץ-חי, DB (SELECT בלבד), ריסטארט (pid 2030 לאורך כל הריצה).

## 1 · הממצא (SELECT בלבד, 18.10 10:0x)

`live+CLOSED` לפי `exit_reason` ⇒ **`SIERRA_FLAT 13 / 1 / 5`** (n / יש `pnl_sierra` / יש `pnl_usd`) — היה `10/1/5` ב-02.10 (ריצה 173); שלוש נוספו: `#3140` (06.10 EOD), `#3402` / `#3406` (09.10, נדחו ע״י הברוקר). 13 השורות:

| id | מצב בספרים | `entry_ts` | `sierra_order_id` | מה זה באמת |
|---|---|---|---|---|
| 548 · 708 · 744 · 820 | `pnl_usd 0 · outcome BE · exit_price NULL` | יש | יש | **אפס מסונתז** (לפני T-160 מ-30.08) — הפרת Rule 1 בנתון עצמו |
| **571** | `pnl_usd 0 · BE` | **NULL** | **אין** | נוצר 20:00:12, נסגר `SIERRA_FLAT` 20 שנ׳ אחרי — **מעולם לא בוצע** |
| **955 · 979** | `UNPRICED` | **NULL** | **אין** | SCALE_IN (P3 reinforce +2c) 02.09 — אין שורת-ENTRY ביומן-המילויים של ה-DLL ב-±3 דק׳ (17:15:07 / 18:59:38 סביב 17:30:04; 20:10:05 / 22:05 סביב 21:18:53) ⇒ **לא בוצעו** |
| **1220** | `UNPRICED` | **NULL** | **אין** | OPENING_DRIVE 08.09 16:40:08, נסגר 16:40:29 — ה-ENTRY הבא ביומן 16:55:10 ⇒ **לא בוצע** |
| 939 · 3140 | `UNPRICED` | יש | יש (10810 / 11431) | **בוצעו** (ENTRY ביומן 22:05:07 / 20:35:03) ונסגרו ב-EOD-flatten — **ובזרם-הפעילות של סיירה אין אף POSITION_CHANGE / CLOSED_TRADE_PNL בחלון** (31.08 22:00–23:00 · 06.10 20:30–23:00) ⇒ פער-סורק, אין ממה לתמחר |
| 2913 | `UNPRICED` + `pnl_sierra −23.75` | יש | יש | תומחר ע״י `broker_truth` (ריצה 174) ✓ |
| 3402 · 3406 | `UNPRICED` | יש (=exit_ts, 18:10/18:15) | יש | דחיות-ברוקר 09.10 (מרג׳ין) — פריט-ספרים נפרד (באינבוקס של cowork 18.10) |

**השורש של "955/979/1220 נושרות מקבוצת-המועמדים של `broker_truth`" (הצעד-הבא (א) של ריצה 174):** השאילתה סיננה `entry_ts >= :since`; ל-`entry_ts NULL` ההשוואה שקרית ⇒ השורה **נשמטת בשקט** (ולולאת-ההתאמה הייתה נופלת על `None` אילו נכנסה). לכן "live trades 57 · matched 52" לא כלל אותן — והתמונה "9 היסטוריות לא נסגרו" הייתה חלקית: **ארבע מהן אינן עסקאות כלל.** `POSITION_TRUTH` (fill_poller) סוגר פקודה PENDING בלי submit-ack כשסיירה שטוחה — אותו אות (`quality.sierra_order_id` חסר) שבו K1e מסרב לייחס פוזיציה — אבל רושם אותה כ-`SIERRA_FLAT / UNPRICED`, כאילו הייתה עסקה שבוצעה ויצאה בלי מחיר.

## 2 · מה נבנה / תוקן

**(א) דגל-כבוי — `POSITION_TRUTH_UNFILLED_CANCEL_V1` ב-`backend/v9/services/fill_poller.py::_sync_position_truth` (ענף סיירה-שטוחה):** עסקה `PENDING` **בלי** `quality.sierra_order_id`, אחרי חלון-החסד ⇒ אותה סגירה (`close_trade(id, "SIERRA_FLAT", outcome_override="CANCELLED")`, תקדים P8 ל-ORDER_FAILED) + `quality.never_filled=True` + `never_filled_reason`. `pnl_usd` נשאר NULL (נתיב T-160 — `outcome_override` מכובד שם). **שום מספר לא מומצא.** `FILLED`, או `PENDING` עם ack, או כל מצב כשסיירה מחזיקה פוזיציה — ללא שינוי. **OFF (ברירת-מחדל) = קריאה זהה-בייט `close_trade(id, "SIERRA_FLAT")`** ו-`quality` לא נוגעים.
- מבחנים: `tests/v9/regression/test_t527_unfilled_cancel.py` (6): OFF זהה-בייט (צורת `#1220`) · ON ⇒ CANCELLED+never_filled · ON עם ack ⇒ רגיל · ON על FILLED ⇒ רגיל · ON לא מרחיב (עסקה צעירה שורדת) · ON לא נוגע בענף-הפוזיציה (K1e). + 12 המבחנים הקיימים של `test_position_truth_sync.py` ירוקים.
- רישום: `docs/FLAG_REGISTRY.yaml` (`status: built_off`). לא ב-`.env`, לא ב-RULED_FLAGS — הדלקה = פסיקה + ריסטארט מחוץ ל-RTH.

**(ב) תיקון-באג — `scripts/broker_truth.py`:** (1) קבוצת-המועמדים מעוגנת ב-`coalesce(entry_ts, created_at) >= :since` (וגם ההתאמה ±3/±5 דק׳ מעוגנת כך) ⇒ שורה בלי `entry_ts` **נרשמת** כ-`NEVER-FILLED (entry_ts NULL, T-527)` עם `broker=None` (לא מתומחרת — כישלון כן), לא נשמטת. (2) `day_totals`: יום שיש בו רק round-trips ידניים זרק `KeyError` (ה-`days[u["day"]]` חושב לפני ה-`setdefault`) והפיל את הריצה לפני כתיבת `broker.json` — `--since 2026-08-25` קרס היום בגרסה הישנה (rc=1), עובר בחדשה (rc=0). (3) המבנה: `main()` + פונקציות טהורות (`TRADES_SQL`, `anchor_ts`, `load_events`, `round_trips`, `load_journal`, `match_trades`, `day_totals`) — כדי שיהיה מבחן. `--write` לא השתנה (כותב `pnl_sierra` בלבד, רק matched ולא mixed).
- מבחנים: `tests/v9/regression/test_t527_broker_truth_candidates.py` (6): SQL מעוגן ב-coalesce · `anchor_ts` · שורת-`#1220` נרשמת ולא מתומחרת · הנתיב ההיסטורי (order id) זהה · צורת-`#3046` מותאמת דרך `created_at` · יום-ידני-בלבד לא זורק.
- **אימות על הספרים (dry-run, JSON ל-`/tmp`, אפס כתיבה):** `--since 2026-09-01`: ישן `live trades 69 · matched 58` → חדש `75 · matched 59 · never-filled 6`; **69 השורות המשותפות זהות בייט-בייט ב-JSON** (`harness_out/t587/broker_truth_old_0901.out` מול `broker_truth_new_0901.out`). השש שנוספו: `955 · 979 · 1220` (השלוש של ריצה 174), `1337` (09.09 BRACKET_EXIT_ACTIVITY, `pnl_usd +30` בלי `entry_ts`), `2038` (21.09 `ladder_invalid`), **`3046`** (05.10 19:25 GB100 LONG).

**(ג) ממצא-לוואי שהתיקון חשף — `#3046`:** בספרים `BRACKET_EXIT_ACTIVITY −27.50$` בלי `entry_ts`; ביומן-ה-DLL יש ENTRY LONG 7873.0 (order 11408) וב-זרם-הפעילות round-trip 19:26→20:45 **+53.75$** — שעד היום נרשם כ-"ידני/לא של המערכת". Δ ספרים-מול-ברוקר **+81.25$ על שורה אחת**, בכיוון ההפוך מ-T-256. `broker_truth --write` של תור-הלילה יכתוב עכשיו `pnl_sierra=+53.75` עליה (התאמה לפי order id, לא mixed) — לידיעה, לא פסיקה.

**(ד) מה אי-אפשר לתמחר מהברוקר, ולמה:** `939 · 3140` בוצעו ונסגרו ב-EOD-flatten, אבל בזרם-הפעילות אין אירועים בחלונות שלהן (פער-סורק של `com.mems26.activity_feed`) ⇒ "תמחור מהברוקר בכותב-היציאה" אינו אפשרי מהזרם; המספר היחיד הוא הפרש `acct_daily_pl` (כך נגזר −23.75 ל-`#2913` ביד ב-ריצה 173) — מנגנון נפרד שלא נבנה הלילה (ייחוס הפרש-יומי לעסקה אחת דורש שאין שינוי-פוזיציה אחר בין שתי הדגימות).

## 3 · כלל-הקבלה (BRIEF §3: שורש + מבחן-רגרסיה, לא רישום)
- שורש נמצא בקוד (לא מהזיכרון): `fill_poller.py` סוגר PENDING-בלי-ack כ-`SIERRA_FLAT`; `broker_truth.py` מסנן `entry_ts >= since`. ✓
- תיקון עם מבחן: 12 מבחנים חדשים ירוקים + 12 קיימים; `python3 -m pytest -q tests/v9/regression/test_t527_*.py tests/v9/regression/test_position_truth_sync.py ⇒ 24 passed`. ✓
- אימות בתנאי-המקור: הריצה הישנה/החדשה על הספרים האמיתיים (`--since 2026-09-01`, dry-run) — 69 שורות זהות, 6 נוספו, 0 הוסרו. ✓
- `flag_guard` ⇒ `FLAG-GUARD: PASS — all 274 ruled flags match` (tail, לא grep). ✓
- לא נסגר ✅ (רק cowork/מייקל): הדגל ממתין לפסיקה; תיקון-הסקריפט ממתין לאימות בריצת-הלילה הבאה (`broker_truth --since 2026-09-01 --write`).

## 4 · מה דורש פסיקה (לאינבוקס; סוכן-08:30 שולח)
1. **פסיקה? T-527 — להדליק `POSITION_TRUTH_UNFILLED_CANCEL_V1`** (.env + RULED_FLAGS + ריסטארט מחוץ ל-RTH, T-551): פקודה שלא בוצעה תירשם `CANCELLED` ולא `UNPRICED`; אפס מחיר מומצא; OFF זהה-בייט — כן/לא.
2. **פסיקה? T-527 — תיקון-ספרים חד-פעמי של חמשת האפסים המסונתזים** (`548 571 708 744 820`: `pnl_usd 0 / BE` בלי `exit_price`, לפני T-160) ⇒ NULL/UNPRICED, **בלי לנחש מספר** — מבוצע ע״י cowork/מייקל (DB-write אינו בסמכות fix-agent):
   `UPDATE v9_trades SET pnl_usd = NULL, outcome = 'UNPRICED', quality = coalesce(quality,'{}'::jsonb) || '{"pnl_status":"UNPRICED","pnl_unpriced_reason":"SIERRA_FLAT (pre-T-160 synthesized 0 → NULL, T-527 18.10)"}'::jsonb WHERE id IN (548,571,708,744,820) AND exit_reason='SIERRA_FLAT' AND exit_price IS NULL AND pnl_usd = 0 AND outcome = 'BE';`
   (אם `quality` אינו jsonb — `quality::jsonb`; 5 שורות צפויות.) — כן/לא.
3. לידיעה: `#3046` — ספרים −27.50 מול ברוקר +53.75 (Δ +81.25); `#939`/`#3140` — אין רשומת-ברוקר (פער-סורק), נשארות NULL (כישלון כן).

## 5 · ראיות גולמיות
- `harness_out/t587/broker_truth_old.py` (HEAD, ROOT קבוע) · `broker_truth_old_0901.out` / `broker_truth_new_0901.out` (`--since 2026-09-01`) · `broker_truth_old.out` (קריסה, `--since 2026-08-25`) / `broker_truth_new.out`.
- psql (SELECT): 13 שורות `SIERRA_FLAT` עם `entry_ts / created_at / exit_ts / sierra_order_id` — §1; יומן-ה-DLL וזרם-הפעילות סביב 02.09 / 08.09 / 31.08 / 06.10 — סרוקים בפייתון (stdout בסשן).
- קוד: `backend/v9/services/fill_poller.py` (הענף `SIERRA_FLAT`), `scripts/broker_truth.py`, `docs/FLAG_REGISTRY.yaml`, שני קבצי-המבחן.
- הבקאנד: pid 2030 (`lsof -nP -iTCP:8000 -sTCP:LISTEN`) בתחילת הריצה ובסופה.
