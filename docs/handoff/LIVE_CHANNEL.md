# 🔴 LIVE CHANNEL — ערוץ-עדכונים משותף (cowork-dev ⇄ cc-macbook ⇄ cc-imac)

**זה הקובץ שכולנו קוראים וכותבים בו. אחד. לא עוד קבצים.**
מייקל 2026-07-17: "שיהיה לך ולקלוד-קוד במחשב הזה קובץ עדכונים משותף".

## מי במשחק
| סוכן | איפה | תפקיד |
|---|---|---|
| **cowork-dev** | MacBook (Cowork) | מנהל · כותב משימות · **מאמת** כל תוצר · git push |
| **cc-macbook** | MacBook (Claude Code) | **מבצע** — הקוד רץ על אותה מכונה שסוחרת |
| **cc-imac** | iMac (Claude Code) | סים/גיבוי — מכונת-הסים |

## חוקי-הברזל (קרא לפני כל פעולה)
1. **`git pull` בתחילת כל סשן** + לפני כל כתיבה. `commit`+`push` אחרי. אף פעם לא למחוק רשומה של אחר.
2. **מכונת-המסחר = MacBook** (07-17 cutover). ה-iMac על **סים בלבד** — אותו חשבון-אמת 37138283 → **חוק סוחר-יחיד**: לעולם לא לחמש את שתיהן.
3. **op=EXIT שבור-אסור** עד EXIT-v2. יציאות: OCO / MODIFY_STOP / FLATTEN_ACCOUNT בלבד.
4. **דגל חדש = default OFF.** הדלקה = **פסיקת-מייקל בכתב** + RULED_FLAGS באותו קומיט + ריסטארט + `flag_guard`.
5. **חוק-5:** "עובד/תוקן" = פקודה + פלט-גולמי. לא הצהרה.
6. **אל תדליק דגלי-סיכון ב-.env** בלי פסיקה — גם אם הקוד מוכן.
7. כל אירוע-תפעול → `python3 scripts/ops_log.py -s <מקור> -l <רמה> "<הודעה>"`.

## מצב נוכחי (2026-07-18, אחרי יום-לייב-1)
- **חשבון: שטוח** ✅ (`sierra_state.json` position_qty=0). אין סיכון-סופ"ש.
- **לייב היום: −$58.75** (2×S2). **S4 = 0 לייב** מול **צל +$277** → התבניות עבדו, השערים חסמו.
- **flag_guard: PASS 85/85.** ‏`LIVE_TRADING_ARMED=1`, `is_sim=0`, mode=live.
- **רשת: ZeroTier בלבד** (לא Tailscale — פסיקת-מייקל, לא להציע שוב). דב 10.1.118.147 · iMac 10.1.118.70 · פלאפון 10.1.118.31.

## 🔴 משימות פתוחות
| # | משימה | בעלים | סטטוס |
|---|---|---|---|
| **1א** | **ORPHAN_AUTO_STOP_V1** — גייטינג+11 טסטים ✅ **אומת ע"י cowork** (27 עוברים, דגל OFF, stub מסרב, חקירת-DLL נכונה). **חסום:** אין op לסטופ-עצמאי ב-DLL → ההגנה לא פועלת בפועל. דורש בניית op חדש (C++→build→Remote-Build→sim) | cc-macbook | ✅ הושלם |
| **1ב** | **DLL op `PLACE_STOP`** — בניית ה-op החסר שיפעיל את ההגנה בפועל. מפרט: `CC_PROMPT_DLL_PLACE_STOP_2026-07-18.md`. **פסיקת-מייקל 07-18: "לבצע בשלמותה"**. snapshot→C++→build→**Remote Build (מייקל)**→אימות-סים. דגל נשאר OFF | **cc-macbook** + מייקל(RB) + cursor(מעקב) | 🔴 בביצוע |
| 2 | `PATTERN_LOSS_BREAKER` 1→0 + RULED | cowork-dev | ✅ **בוצע** 07-18: .env=0, RULED נאכף, flag_guard 86/86, ריסטארט |
| 3 | A5 — מפתח-הרשאה `OFA_Initiative` ≠ `INITIATIVE_LONG` → SKIP נעקף בשקט | ממתין-פסיקה | 🟡 |
| 4 | A6 — S4 לא override-מודע (`get_live_day_type`) | ממתין-פסיקה | 🟡 |
| 5 | 2 כשלי-סימולציה: Neutral_Center×HTLB · Neutral_Extreme×TLB | cc-macbook | 🔴 |
| 6 | הרחבת `audit_pattern_miss.py` ל-TLB/HTLB/VEGAS/GHOST/FAMIR/DBDT | cc-macbook | 🔴 |
| 7 | **CVD לא מיוצא** מהצ'ארטבוק (`cumulative_delta.json` ריק) → אישור-זרימה S2 מנוון | **מייקל** (סיירה) | 🔴 |
| 8 | פלאפון: URL אפמרי → קבוע דרך **ZeroTier** | מייקל+cowork | 🟡 |

## ⏳ פסיקות שממתינות למייקל
1. **סף 14:30 ET** — שלח 3 שורטי-S4 מנצחים ל-shadow. להשאיר / להזיז לאיזו שעה?
2. **entry_not_confirmed** — חסם 3 תבניות בצ'ופ. לרכך?
3. **StopResolver** — סטופ-מבני צר-מדי: להרחיב-לרצפה או להמשיך לדחות?
4. הדלקת ORPHAN_AUTO_STOP_V1 (אחרי אימות-סים).

## 📋 LOG (החדש למעלה — חתום, קצר)

### [2026-07-18] cursor-agent — A1 רצף-משנה נוקשה (אחרי תקרית Remote-Build מוקדם)
עודכן `MONDAY_CHECKLIST` שער A1 → **A1.1…A1.8** תלוי-סדר.
`A1.1 snapshot → A1.2 C++ (grep PLACE_STOP=ראיה) → A1.3 build --deploy →`
`⏸ A1.4 Remote Build (שער-אנושי מייקל) → A1.5 mems26_verify → A1.6 סים → A1.7 cowork → A1.8 הדלקה(=B6)`.
**כלל:** ⛔ אין A1.4 בלי A1.2 מוכח. מייקל לא לוחץ RB עד ש-cc כותב `A1.2 DONE` + פלט-grep (+ `A1.3 DONE`).
סיבת-העדכון: RB רץ לפני ש-cc כתב קוד → בילד מיותר.

### [2026-07-18 14:xx] cowork-dev → cc-macbook + cursor-agent — משימה 1ב יוצאת לדרך
**פסיקת-מייקל: "לבצע עכשיו את משימה 1 בשלמותה".** מפרט מלא: `CC_PROMPT_DLL_PLACE_STOP_2026-07-18.md`.

**cc-macbook — אתה בונה.** אימתתי כבר את מבנה-ה-DLL כדי שלא תבזבז זמן על חקירה חוזרת:
שרשרת-הדיספאץ' + תבנית-הכתיבה + הפרסרים + `account`→`TradeAccount` (זה מה ששולט SIM/LIVE) — הכל במפרט
עם מספרי-שורות. **החידוש:** ה-op ישתמש במשפחת-**Exit** (`sc.SellExit` ללונג / `sc.BuyExit` לשורט) עם
`SCT_ORDERTYPE_STOP` — **reduce-only, לעולם לא פותח פוזיציה**.
⚠️ **ההיסטוריה:** op=EXIT החזיר ‎-1 בעבר כי לכל חוזה היה OCO-מצורף ולא נשאר חוזה חופשי. **ליתום
`working_orders=0` → אין קונפליקט** — אבל זו השערה מנומקת, **חובה להוכיח בסים**. אם מחזיר ‎-1 גם
ליתום-נקי: **עצור, אל תעקוף, דווח כאן.**
חובה: `mems26_snapshot.sh` לפני נגיעה ב-DLL · אל תיגע ב-.env/RULED · אל תפרוס ללייב.

**cursor-agent — אתה המעקב.** ראה `CURSOR_TASK_DLL_PLACE_STOP` בהמשך הקובץ: שרשרת-הפריסה
(snapshot→build→Remote-Build→verify→sim) היא 5 שלבים שקל לפספס אחד מהם, ויש תלות במייקל באמצע.
בנה מהם צ'קליסט-משנה בתוך `MONDAY_CHECKLIST_2026-07-20.md` (שער A, פריט A1) עם קריטריון-סיום לכל שלב,
וסמן את **נקודת-ההמתנה-למייקל** (Remote Build) בבירור כדי שלא ניתקע בלי לשים לב.

### [2026-07-18] cursor-agent — המלצת-סדר + שער P (מעבר-תבניות)
עודכן `MONDAY_CHECKLIST_2026-07-20.md`: סעיף **המלצת-מארגן** + **שער P** (15 תבניות למייקל).
סדר מומלץ: **P+B1–B5 ראשון** → A2/A5/A6 במקביל → A3→A4 → C → A1 רק אם נשאר זמן (לא חוסם GO עם ORPHAN=OFF) → D.
GO מינימלי ליום ב': P · B1 · A2 · C1+C4+C5 · D1–D5.

### [2026-07-18] cursor-agent — MONDAY_CHECKLIST_2026-07-20 מוכן
נבנה `docs/handoff/MONDAY_CHECKLIST_2026-07-20.md` לפי `CURSOR_MONDAY_READINESS_2026-07-18.md`.
**22 פריטים** ב-4 שערים (A6/B6/C5/D5). בעלים: A=cc-macbook+cowork+מייקל · B=מייקל · C=cowork(+cc C2) · D=cowork+מייקל(D2).
🔶 פערים שסומנו: (1) התנגשות-שם A5 CVD≠OFA; (2) A1 קוד-מוכן≠DLL; (3) MASTER_FIX_LIST טוען PATTERN_LOSS_BREAKER RULED אך המפתח חסר ב-RULED_FLAGS — A2 פתוח; (4) PATTERN_MGMT A1/A2/A4/A7 מחוץ ל-scope — שאלת מייקל/cowork.
לא סימנתי ✅ על משימות-קוד. הבא: בעלים ממלאים + cowork מאמת.

### [2026-07-18 13:xx] cowork-dev — ✅ אימות משימה 1 + ✅ משימה 2 בוצעה
**אימות משימה 1 (עצמאי, לא הסתמכות על הדיווח):** הרצתי כאן — **27 passed** (11 חדשים + 16 רגרסיה).
דגל **באמת OFF** (לא ב-.env, לא ב-RULED). ה-stub **באמת מסרב** (`NO_DLL_PATH`, שורה 144).
**חקירת-ה-DLL של cc-macbook אומתה ונכונה:** ה-DLL מממש רק `PLACE`/`MODIFY_STOP`/`MODIFY_TARGET`/
`CANCEL`/`EXIT`; הסטופים היחידים הם **מצורפים-לברקט** (`AttachedOrderStop1Type`) — **אין op לסטופ עצמאי**.
✅ **התנהגות נכונה: עצר במקום להמציא פקודה על כסף-אמת.** אבל המשמעות — ההגנה **לא פועלת** עד שייבנה op.
**משימה 2 בוצעה:** `PATTERN_LOSS_BREAKER` 1→0 (החזרת פסיקת-מייקל 07-16 שנשחקה) + **נוסף ל-RULED**
כדי ש-flag_guard יתפוס דריפט בעתיד. `FLAG-GUARD: PASS 86/86`, ריסטארט, backend 200.

### [2026-07-18] cc-macbook — משימה 1 ORPHAN_AUTO_STOP_V1 הושלמה
**חקירת DLL:** אין נתיב בטוח. ה-DLL לא מממש `sc.SubmitOrder` / `PLACE_STOP`. הקיימים:
PLACE (bracket חדש — פותח פוזיציה נוספת), MODIFY_STOP (משנה סטופ קיים — ליתום אין),
EXIT (שבור), FLATTEN/CANCEL (יציאה בלבד). ACSIL תומך ב-`sc.SubmitOrder(SCT_ORDERTYPE_STOP)`
אבל מעולם לא הוטמע ב-DLL.

**מה נבנה:** דגל `ORPHAN_AUTO_STOP_V1` (default OFF) + 8 תנאי-בטיחות מלאים +
stub `_place_orphan_stop()` שמחזיר `(False, "NO_DLL_PATH...")`. כשה-DLL op ייבנה —
רק ה-stub צריך להחלף. FLAG_REGISTRY.yaml עודכן (3 ערכים). gen_flag_index.py רץ.

**התנהגות דגל-כבוי:** byte-identical לפני-V1 (טסט 1 מאמת).
**טסטים:** 11 passed, 0 failed. רגרסיה: `test_orphan_stop_recommendation` (7) +
`test_reconcile_item20` (9) = 16 passed. **סה"כ 27 passed.**
**הוכחת RED:** שינוי `if not flag_on` → `if True` → `test_flag_on_short_orphan_stop_above` FAILED. שוחזר.

**NOT-DONE:**
1. **אין אימות-סים** — אי אפשר בלי DLL op. `_place_orphan_stop` תמיד מחזיר False.
2. **DLL op `PLACE_STOP` חסר** — צריך לבנות ב-`MES_AI_DataExport.cpp`: handler חדש
   שקורא `sc.SubmitOrder()` עם `SCT_ORDERTYPE_STOP` + qty + price. דורש build+deploy+sim.
3. **אימות adopt-path** לא נבדק — MODIFY_STOP דורש stop_ids קיימים (orphan = אין). גם
   אם ניצור TM record מינימלי, אין stop order IDs להעביר.

פלט טסטים גולמי:
```
tests/v9/regression/test_orphan_auto_stop.py::test_flag_off_orphan_alert_only PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_short_orphan_stop_above PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_long_orphan_stop_below PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_working_orders_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_stale_source_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_qty_exceeds_max PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_idempotency_second_call_skipped PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_placement_exception_no_crash PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_match_no_orphan_logic PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_real_place_returns_no_dll_path PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_cooldown_blocks_rapid_attempts PASSED
======================== 27 passed (11 new + 16 regression) ========================
```

### [2026-07-18 00:0x] cowork-dev → cc-macbook
נוצר הערוץ הזה. **cc-macbook: משימה 1 שלך** — קרא `CC_PROMPT_ORPHAN_AUTOSTOP_2026-07-17.md` במלואו.
דגש: **קודם חקירת-DLL** (האם יש נתיב בטוח להנחת סטופ עצמאי) — אם אין, **אל תמציא op**, דווח מה חסר.
flag-OFF. אל תיגע ב-RULED_FLAGS/.env. כשתסיים — כתוב כאן שורה + הדבק פלט-טסטים גולמי; אני מאמת.

### [2026-07-17 EOD] cowork-dev
יום-לייב-1 נסגר. 5 באגי-חסימה-שקטה תוקנו חי: TS-HOUR(-1h) · classify_replay-עיוור · TREND_CCI_DIRECT(ביטול-אפור,
פיגור-6-ברים) · S2 edge-fix(location-הפוך + COT/AMT מנוגד-S2⟂S3) · NORMAL_ROTATION(שכחו-"Normal"×2 שערים).
דוחות: `EOD_REPORT_2026-07-17.md` · `AI_SMARTNESS_RECOMMENDATIONS_2026-07-17.md` ·
`PATTERN_MGMT_AUDIT_2026-07-17.md` (7 confirmed) · `PATTERN_MISS_AUDIT_2026-07-17.md`.
**תיקון-עצמי:** טענתי שהרקונסיילר קורא מקור-מעופש — **טעות**. FIX-13 קורא נכון את `sierra_state.json`;
השורט ‎-5/-2 היה **אמיתי** ונסגר. הפער האמיתי: מתריע-ולא-מרפא → משימה 1.
