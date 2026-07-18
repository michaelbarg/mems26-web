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
| **1** | **ORPHAN_AUTO_STOP_V1** — סטופ-מגן אוטומטי לפוזיציה-יתומה. **בוצע:** גייטינג+טסטים מוכנים, **חסום:** אין DLL PLACE_STOP op. ממתין לבניית DLL op + sim | **cc-macbook** | 🟡 חסום-DLL |
| 2 | `PATTERN_LOSS_BREAKER` 1→0 + להוסיף ל-RULED (דריפט מפסיקת-מייקל 07-16) | cowork-dev | 🔴 פתוח |
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
