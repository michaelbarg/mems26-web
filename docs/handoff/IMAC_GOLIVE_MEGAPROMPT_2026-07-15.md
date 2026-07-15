# מגה-פרומפט ל-Claude ב-iMac — cutover למסחר-אמת מהמכונה המרוחקת · 2026-07-15

**אתה cc-imac.** מייקל פסק: **מהיום המסחר-על-כסף-אמת רץ מה-iMac** (המכונה שלך), לא ממק-הפיתוח.
זה ה-cutover המתוכנן (`SECOND_MAC_SETUP.md §10`). בצע את השלבים **בסדר המדויק** — כל שלב הוא שער:
אם שלב נכשל, **עצור ודווח**, אל תמשיך לשלב הבא. כל דיווח = פקודה גולמית + פלט (Rule 5) + NOT-DONE.

---

## ⚠ חוק-הברזל: מכונה אחת סוחרת בכל רגע
‏Teton = **חיבור-מסחר יחיד**. אם שתי מכונות מחוברות-אמת בו-זמנית → הוראה-כפולה / ניתוק-באמצע-סשן.
לכן ה-cutover הוא **רצף מסירה**: מק-הפיתוח **משתיק ומתנתק לגמרי** לפני שאתה מתחבר-אמת.

---

## PHASE 0 — מק-הפיתוח מושתק (מייקל מבצע; אתה מוודא מהראיות)
לפני שאתה נוגע בחשבון-אמת, ודא שמק-הפיתוח **שקט לחלוטין**:
1. מק-הפיתוח: ‏Input 22 → 0 (לא-חמוש) · ‏backend עם `LIVE_EXECUTION_V1=0` · ‏FLATTEN → `qty=0` · **‏File→Disconnect בסיירה שם**.
2. הוכחה שאתה יכול לבדוק: אין `trade_command.json` טרי נכתב ממק-הפיתוח, וה-`sierra_state.json` שלו קפוא/מנותק.
**אל תמשיך אם מק-הפיתוח עדיין מחובר-אמת או חמוש.** (מייקל מאשר בכתב שהמק-הפיתוח מנותק.)

---

## PHASE 1 — עדכון קוד + דגלים (בטוח, לא-נוגע-במסחר)
```
git pull --ff-only origin stabilize/mems26-local-truth-2026-05-16     # → behind=0
python3 scripts/sync_env_from_ruled.py --apply                         # מיישר .env לפסיקות (70 דגלים)
python3 scripts/flag_guard.py                                          # חובה PASS 70/70
```
- אם `flag_guard` נכשל → **עצור ודווח** (דגל לא-מוכר/קונפליקט). אל תתקן דגלים לבד.
- מיגרציית-DB (אם טרם): בדוק `SELECT column_name FROM information_schema.columns WHERE table_name='v9_trades' AND column_name IN ('t4','t4_hit_ts')`. אם חסר: `python3 backend/v9/db/migrations/versions/021_t4_contract_columns.py`.
- ריסטארט-בקאנד → `scripts/mems26_verify.sh` = **OK** (DLL==ריפו, פיד טרי, DB עדכני).
**שער:** `flag_guard PASS` + `verify OK` לפני PHASE 2.

## PHASE 2 — בילד DLL (כאן "מתי אפשר בילד": עכשיו, אחרי PHASE 0+1)
```
./scripts/build_monolithic_cpp.sh --deploy          # מפיץ את מקור-4-החוזים (t4) ל-ACS_Source שלך
```
בסיירה שלך:
1. ‏Analysis → Build Custom Studies DLL → **Remote Build** → המתן ל-"Build succeeded".
2. **reload לסטאדי** (Remove+Re-Add אם צריך).
3. **חובה אחרי הבילד — לחמש: ‏Input 22 ("Enable Order Placement") → 1** (היום כן! ה-iMac סוחר).
4. **בדוק ‏Input 4 ("V9 Export Directory")** = `/Users/michael/SierraChart_Data/v9_export/` — מתאפס ב-Remote-Add.
**שער:** אחרי reload — `sierra_state.json` מתעדכן ≤2ש', `order_placement_armed=true`, בינארי-DLL טרי מהמקור.

## PHASE 3 — 🔴 שפיות-הפיד (החסם האמיתי מהיום — קריטי!)
היום נראו במק-הפיתוח דחיות-CME עם מחירים אבסורדיים ("‏Bid 996150 violates High Limit 811925").
זה **הזנת-מחיר פגומה** — עם פיד כזה **כל הוראת-אמת תידחה או תתמלא במחיר-שגוי**. חובה לוודא שאצלך נקי:
```
python3 -c "import json,os,time; lp=json.loads(open(os.path.expanduser('~/SierraChart_Data/v9_export/live_price.json')).read()); \
print('bid=%s ask=%s age=%.0fs'%(lp['bid'],lp['ask'],time.time()-os.path.getmtime(os.path.expanduser('~/SierraChart_Data/v9_export/live_price.json'))))"
```
- ‏bid/ask **חייבים** להיות בטווח שפוי ל-MES (~7500-7700), **לא** 996150/525000. גיל ≤2ש'.
- אם המחיר לא-שפוי: בסיירה ‏File→Disconnect→Connect (רענון-פיד). עדיין לא-שפוי אחרי רענון → **עצור, אל תסחר-אמת**, דווח (זו תקלת-נתונים בצד-סיירה/הזנה, לא בקוד שלנו).
**שער:** מחיר-חי שפוי + טרי לפני PHASE 4.

## PHASE 4 — הוכחת-סים 4-חוזים (חובה לפני אמת!)
בסיירה: ‏Trade → **Trade Simulation Mode → ON** (זמנית). ודא `is_sim=1` בעין. ואז:
- ‏BUY 4 → **8 הוראות** (4 זוגות: ‏C1 יעד=כניסה+3.5=T0 · ‏C2/C3/C4=T1/T2/T3) → ‏MODIFY_STOP (כל 4 הסטופים זזים) → ‏FLATTEN → `qty=0`.
- `python3 scripts/fire_drill.py` = **🟢 GO**, `effective_contracts==4`.
- (הראיה ממק-הפיתוח: הוכחה זו עברה שם 14:50 — 4 יעדים + 4 סטופים; העתק את המבנה.)
**שער:** הוכחת-סים ירוקה + drill GO לפני חימוש-אמת. אם נכשל → **עצור, אל תעבור לאמת.**

## PHASE 5 — חימוש למסחר-אמת (רק אחרי כל השערים ירוקים)
1. בסיירה: ‏Trade → **Trade Simulation Mode → OFF** (חשבון-אמת).
2. **ודא בעין:** `is_sim=0` **וגם** המחיר עדיין שפוי (PHASE 3) **וגם** `qty=0` (flat).
3. שרשרת-החימוש לאמת (שלושתן נדרשות):
   - סיירה: ‏Input 22 = 1 (DLL חמוש) ✓ (מ-PHASE 2)
   - ‏.env: `LIVE_EXECUTION_V1=1` (נתיב-הביצוע-החי בבקאנד) — בדוק שדלוק; אם לא, הוסף + ריסטארט.
   - שער-הבטיחות-החדש (`trade_commands.py`, נבנה היום): פקודות-אמת נחסמות אלא אם `LIVE_TRADING_ARMED=1`.
     לחימוש מכוון: הוסף `LIVE_TRADING_ARMED=1` ל-.env. **זהו שער-הבטיחות — אל תדליק אותו לפני שכל השאר ירוק.**
4. ‏`flag_guard` PASS + ‏`fire_drill` GO אחרי כל שינוי-env (ריסטארט).
**שער:** `is_sim=0` + מחיר-שפוי + 3 החימושים דלוקים + drill GO = מוכן ל-RTH על אמת.

## PHASE 6 — פיקוח-חי בזמן המסחר
- `sierra_state.json` ≤2ש' לאורך כל הסשן; אזעקת-NAKED_STOP/DIVERGENCE → דווח מיד.
- העסקה הראשונה: ודא **4 זוגות** נבנים, ‏T0 יוצא ראשון, שער-המיקום חוסם מיקום-שגוי (לוג `blocked_by=location_gate`).
- עצירת ‏−$400 בתוקף. עסקה-פתוחה בגבול-RTH → FLATTEN.

---

## מלכודות ידועות (חסוך לעצמך)
- **אחרי כל בילד/reload — ‏Input 22 מתאפס ל-0 בשקט.** זה בדיוק מה שגרם היום לכך שהוראה הלכה לחשבון-אמת בטעות (הסים התאפס). בדוק אותו **אחרי** כל reload.
- `sot_health` מציג DB-🔴 כוזב (קורא SQLite מת) — האמת ב-`postgresql://localhost/mems26`.
- הריפו אצלך ב-`~/mems26/mems26_web_git` (לא Downloads); קיצורי-הדסקטופ יודעים.
- הפידר רץ עם `--account auto` (פותר MEMS26_MODE לבד; ל-live יאזין לחשבון-האמת).
- `launchd` חסום-TCC מ-.env בכמה הקשרים — הפידר עוקף עם auto; אם משהו לא-קורא-env, הרץ ידנית.

## ידוע-למחר (לא היום): פער-נתונים S1/S2
מייקל זיהה: ‏S1/S2 עובדות על ברי-5-דקות שמתחילים רק ב-RTH (16:30), בעוד ווּדיס מקבל רציף.
**למחר:** לחבר את S1/S2 לטבלת-הברים-הרציפה הקיימת. לא לגעת בזה היום.

---
## דיווח סופי
‏append ל-`docs/handoff/AGENT_SYNC.md` (LOG + סגירת שורת-OPEN) + סעיף "מוכנות-iMac-לאמת" ב-EXECUTION_REPORT:
לכל PHASE — עבר/נכשל + ראיה גולמית + מצב-החימוש הסופי (is_sim, Input22, LIVE_EXECUTION_V1, LIVE_TRADING_ARMED).
‏commit+push. **אל תסחר-אמת לפני שכל 6 השערים ירוקים ומייקל אישר GO.**
