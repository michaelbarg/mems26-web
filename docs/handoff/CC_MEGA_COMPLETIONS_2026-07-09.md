# CC — מגה-פרומפט השלמות (2026-07-09 ערב, אחרי ביקורת ה-fixpack)

**חוזה:** `docs/handoff/CC_HANDOFF_CONTRACT.md` מחייב. **שער-על: אין ריסטארט backend, אין
נגיעה ב-.env/דגלים-פסוקים, ואין reload לסיירה — בלי אישור מייקל מפורש.** עסקה 333 חיה
(2 חוזים LONG @7576.75). ‏snapshot לפני כל משטח-out-of-git. ‏Rule 5 בכל דיווח. עבודה
בסדר הפאזות — לא לקפוץ קדימה. אחרי כל פריט: שורת STATUS_BOARD (ממצא+תיקון+ראיה).

## תוצאת הביקורת שלי (Cowork) על d7c3a52 + 3572aec — נקודת הפתיחה שלך

- ‏16/17 טסטים עוברים אצלי (`BRIDGE_TOKEN=x pytest backend/v9/tests/test_incident_333_fixpack.py tests/v9/services/test_daytype_antiflap.py`).
- 🔴 **רגרסיה-בין-קומיטים:** `test_cert_flag_exists_in_direction_context` נכשל —
  ‏3572aec כתב מחדש את `direction_context_live.py` ומחק את FIX-5
  ‏(CONT_TREND_STATE_CERT_V1) שנוסף ב-d7c3a52. הדגל לא קיים בקובץ הנוכחי.
- 🔴 **FIX-6 לא מחווט:** `sierra_position_reconciler.py` מיובא רק ע"י הטסט. אין
  ‏startup/loop → קוד מת (הפרת "wire the full decision pipeline").
- 🟡 `gen_flag_index.py --check` נכשל: ‏DAYTYPE_ANTIFLAP_V1, ‏DAYTYPE_ONE_SOURCE_V1
  חסרים ב-FLAG_REGISTRY.yaml.
- 🟡 אף דגל חדש לא נוסף ל-`config/RULED_FLAGS.yaml` (35 הישנים PASS).

## PHASE A — סגירת פערי-הביקורת (עכשיו, קוד בלבד, בלי ריסטארט)

**A1 — שחזור FIX-5.** להחזיר את ההסמכה ל-`direction_context_live.py` (מיזוג עם ה-anti-flap
של 3572aec, לא דריסה): ‏dir_sustained="UP" גם כאשר K הברים האחרונים trend_state=='BLUE'
וגם lsma_slope>0 (סימטרי DOWN/RED), תחת CONT_TREND_STATE_CERT_V1 (default OFF).
‏DoD: **כל 17** הטסטים עוברים בריצה אחת. לקח מחייב: קומיטים עוקבים על אותו קובץ —
מריצים את איחוד הטסטים של שניהם.

**A2 — חיווט ה-reconciler.** ‏main.py: משימת רקע (או שילוב בלולאת fill_poller — בדוק מה
קיים לפני שאתה בונה, KEEP/ADAPT) שרצה כל ≤30 שנ' כשיש עסקה demo/live פתוחה:
‏qty-אמת מ-trade_activity_events.jsonl (‏POSITION_CHANGE אחרון) מול TM. סטייה →
‏WARNING רועש + banner (‏BannerStack — בדוק איך banners קיימים נדחפים) + הקפאת
auto-mgmt לאותה עסקה. דגל SIERRA_RECONCILER_V1 (default OFF — מייקל ידליק בריסטארט).
‏DoD: טסט חיווט (מזויף-ריצה: TM=1 פתוח, events=2 → WARNING) + הוכחה שהלולאה נרשמת בבוט.

**A3 — משמעת דגלים.** ‏FLAG_REGISTRY.yaml: להוסיף DAYTYPE_ANTIFLAP_V1,
‏DAYTYPE_ANTIFLAP_HOLD_S (param), ‏DAYTYPE_ONE_SOURCE_V1, ‏CONT_TREND_STATE_CERT_V1,
‏SIERRA_RECONCILER_V1 → `python3 scripts/gen_flag_index.py` ירוק ב---check.
‏config/RULED_FLAGS.yaml: כולם `unset_or_0` (standing-OFF עד פסיקת מייקל) →
`python3 scripts/flag_guard.py` PASS.

**A4 — אינדקס.** `python3 scripts/gen_index.py` (קובץ שירות חדש) + קומיט.

## PHASE B — פריסה ואימות (רק אחרי: 333 סגורה + אישור מייקל; מועדף אחרי 23:00)

1. `scripts/mems26_snapshot.sh "fixpack-0709-deploy"`.
2. `launchctl kickstart -k gui/$UID/com.mems26.backend` → לאמת boot-line env_loader.
3. `flag_guard` PASS · `fire_drill` 🟢 · `mems26_verify.sh`.
4. אימות פר-FIX חי (ציטוט פקודה+פלט):
   - ‏FIX-1: ‏debug-fire סינתטי עם t1 בצד הלא-נכון → `blocked_by=t1_wrong_side`.
   - ‏FIX-2/4: בבוקר, לפני 60 דק' מהפתיחה — לוג "ib_forming_no_clamp" / structural-skip.
   - ‏FIX-3: אין CRITICAL על עסקה בריאה; טסט גיאומטריה הפוכה ב-pytest בלבד (לא חי).
   - ‏FIX-6: שורת heartbeat של ה-reconciler בלוג (אם מייקל הדליק) או OFF-שקט.
   - ‏anti-flap/one-source/cert: כבויים = התנהגות זהה-בייט (להראות שאין שורות הדגלים בבוט).
5. **יישור רשומת 333 (חוב פתוח):** אחרי סגירתה — P&L אמיתי מ-trade_fills_journal.jsonl +
   ‏CLOSED_TRADE_PNL מה-activity feed → לתקן v9_trades: ‏exit אמיתי, ‏pnl פר-רגל,
   ‏contracts=2, רגל-3 VOID (לא-מולאה), תיוג MANUAL-MANAGED. דוח S6 של 23:05 חייב לשפוט
   את 333 מול המספרים האמיתיים — לוודא לפני שהוא רץ, או להריץ מחדש אחרי היישור.
6. עדכון ROADMAP_TO_LIVE.html + STATUS_BOARD (חובת הפרוטוקול).

## PHASE C — ניירות-פסיקה למייקל (להכין; לא להדליק כלום)

עמוד אחד לכל דגל: מה משתנה מחר, סיכון, ערך מומלץ, ראיית-היום:
- ‏CONT_TREND_STATE_CERT_V1 — ראיה: 13 חסימות CONT כולל לונגים-עם-המגמה ביום +50.
- ‏DAYTYPE_ANTIFLAP_V1 + HOLD_S ‏(300 או 600) — ראיה: ‏Nontrend↔Normal↔Variation בשעה.
- ‏DAYTYPE_ONE_SOURCE_V1 — ‏DAY-3 (מנוע=UI=שערים).
- ‏SIERRA_RECONCILER_V1 — תקרית 333 הייתה מתגלה ב-≤30 שנ'.
- החייאת-הכותב (persist בעת promotion, ‏main.py:475) — קדנצת-כתיבה = פסיקה.

## PHASE D — התור העומד (אחרי B, לפי סדר; פריט אחד בכל פעם)

- **D1 — DLL (רק flat + מייקל מודע; ‏build_monolithic_cpp.sh --deploy עם auto-snapshot):**
  ‏(א) ‏EXIT op שבור — error=-1 גם עם פוזיציה פתוחה (שוחזר פעמיים 07-09 בוקר); ‏(ב) קיפאון
  שדה last-trade price ב-live_price (העוקף bid/ask כבר ב-debug endpoint — לתקן במקור).
  הוכחת EXIT על סים אחרי reload.
- **D2 — שגיאות `UPDATE v9_trades SET state='CLOSED'`** שהופיעו בלוג סביב 18:45 —
  לאבחן (varchar overflow? נתיב סגירת-צל?) + טסט רגרסיה + חוב טסט-הגארד ל-varchar.
- **D3 — ‏TP-audit 30 יום** דרך psql ישיר (ההרנס scripts/tp_audit.py קיים; דגימת v1 חזרה
  ריקה — חלון הברים מה-API קצר מדי; לעבור ל-psql). מזין את מחקר-המימושים.
- **D4 — ציד הבר-הישן 2026-06-09** (חשוד: סטרים בברידג').
- **D5 — item-4 חיווט (מימון-סטופים) + item-20/System6 ללולאת ה-poll** — קודם audit האם
  כבר חווטו (לא לבנות כפול).
- נשאר DEFER (פסיקות קיימות): ‏items 12/13/16/17 עד בייסליין רווחי; ‏S3 לא נוגעים.

## דיווח
בסוף כל פאזה: מה בוצע (עם ראיות), מה לא (NOT-DONE מפורש), שאלות למייקל (מרוכזות,
לא חוסמות את הפאזה הבאה אלא אם שער). אני (Cowork) מבקר אחרי כל פאזה.

---
## עדכון 20:2x — פסיקת מייקל: "הכל מאושר"
כל 5 הדגלים נפסקו ON (antiflap hold=600 · one-source · cert · reconciler) + **החייאת-הכותב
מאושרת** (persist-on-promotion, main.py:475 — בצע בפאזה הבאה). .env+RULED עודכנו (aba9bf8,
flag_guard PASS 39). פאזה A שלך אומתה ע"י Cowork (17/17, FIX-5 חזר, reconciler מחווט).
פריסה: מתוזמנת ל-22:30 ע"י Cowork (משימת-לילה) — אל תבצע ריסטארט בעצמך. המשך: פאזה C
(מיותרת ברובה — הפסיקות כבר ניתנו; נותר רק נייר-כיול ל-hold אם תרצה) → פאזה D (D1-D5).

## עדכון 21:5x — FIX-7 (נכנס לראש פאזה D)
**FIX-7 — עיוורון-פולבק בשער-הכיוון הראשי.** ‏21:45: ‏FAMIR LONG ‏conf 0.71 נחסם
‏"direction-context: setup UP vs DOWN (LSMA DOWN + CVD-slope +0 → DOWN)" בעוד ‏trend_state=BLUE,
יום Variation-עולה, מחיר ליד שיא-יום. אותה מחלה כמו FIX-5 אבל ב-`_dc_dir` הראשי
(‏direction_context.compute_direction) — צד-LSMA קורא DOWN בהתבססות מתחת ל-LSMA שעלה.
תקן באותו עיקרון: הסמכת trend_state×K + ‏lsma_slope>0 ⇒ ‏dir=UP (סימטרי), תחת אותו דגל
‏CONT_TREND_STATE_CERT_V1 (כבר פסוק ON) או תת-דגל אם תרצה הפרדה. טסט אנטי-טאוט: הפיקסטורה
של 21:45 (closes מתחת ל-LSMA עולה + BLUE + slope>0 + setup UP) — ישן=blocked, חדש=pass.
זהירות: לא להחליש את הגנת-הצ'ופ (מצבים מעורבים/שיפוע-שטוח → נשאר DOWN/NEUTRAL).

## עדכון 22:2x — hotfix של Cowork על ה-CERT + חוב-טסט אליך
‏0dd5792: תנאי ההסמכה היה `dir_sustained == "NEUTRAL"` — אבל תרחיש-התקרית האמיתי הוא
**DOWN** (כל K הברים מתחת ל-LSMA עולה; ראיה: 5 חסימות ZLR ‏21:00-21:15 עם BLUE×3 + ‏slope ‏+0.36
— תנאי-ההסמכה התקיימו והיא לא פעלה). הטסט שלך עבר כי הפיקסטורה יצרה NEUTRAL, לא DOWN —
אנטי-טאוטולוגי באות אך לא ברוח. **חוב:** טסט עם הפיקסטורה האמיתית של 21:00 (שלושה closes
מתחת ל-LSMA עולה, BLUE×3, ‏slope>0 → ‏sustained צד-גולמי DOWN → ‏cert חייב להרים ל-UP;
ישן=DOWN, חדש=UP) + אותו תרחיש ל-RED. לקח לפרוטוקול: פיקסטורת-תקרית = הנתונים האמיתיים
מה-DB של רגע-התקרית, לא קירוב.
