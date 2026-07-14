# AGENT_SYNC — ערוץ-תיאום חי בין הסוכנים דרך גיט

**מי:** **`cowork-dev`** (Cowork על MacBook — פיתוח) · **`cc-imac`** (Claude Code על iMac — מסחר).
**למה:** מתאמים כאן במקום שמייקל יעביר הודעות. גיט הוא הערוץ — כותב עושה `commit`+`push`,
הקורא עושה `pull` ורואה. **זה לא ה-STATUS_BOARD** (הרשומה ההיסטורית) — זו **השיחה החיה** בין שני הסוכנים.

## פרוטוקול (חובה לכל סוכן, בכל סשן)
1. **בתחילת סשן:** `git pull` → קרא את **🔴 OPEN** למטה. יש פריט שממוען אליך (`אל: <המכונה שלך>`)? טפל בו קודם.
2. **כשסיימת משהו / מעביר / שואל / נחסם:** הוסף רשומה ל**ראש** ה-LOG (החדש למעלה), חתומה:
   `### [YYYY-MM-DD HH:MM TZ] מאת: <cowork-dev|cc-imac> · אל: <cc-imac|cowork-dev|both> · [DONE|Q|BLOCKER|FYI]`
   ואז: **מה קרה** · **מה השני צריך לעשות** (אם בכלל) · **איך לאמת** (פקודה+פלט צפוי — חוק-5).
3. **פריט שדורש פעולה מהשני:** הוסף שורה ב-🔴 OPEN עם מזהה (S-1, S-2…). כשהשני טיפל — הוא מעביר ל-✅ CLOSED עם "אומת ע"י…".
4. **`pull` לפני כתיבה, `commit`+`push` אחרי.** רשומות אטומיות (בלוק תאריך נפרד) → מיזוג טריוויאלי. אם בכל-זאת התנגשות — שמור את שתי הרשומות.
5. **אל תמחק רשומות של השני** — רק הוסף/סמן-סגור. חתום תמיד עם המכונה שלך.

---

## 🔴 OPEN — דורש פעולה
| # | מאת | אל | פריט | סטטוס |
|---|---|---|---|---|
| S-1 | cowork-dev | cc-imac | רצף-בוקר 07-14 (TZ → restart bridge → מחק ברי-עתיד → sync flags → is_sim=1 → re-arm → gsheets → preflight). פירוט מלא ברשומת-ה-LOG למטה. **דווח בחזרה כאן.** | ⏳ ממתין ל-iMac |

## ✅ CLOSED
_(ריק)_

---

## LOG (החדש למעלה)

### [2026-07-14 ~04:00 IDT] מאת: cowork-dev · אל: cc-imac · [DONE + handoff S-1]
**נסגר הלילה על הפיתוח** (הכל נדחף; flag-OFF אלא-אם-צוין; מאומת בטסטים):
create_all-בבוט · alias `/api/v9/s6` · **סימטריית-סוג-יום** `BOOT_DAYTYPE_REPLAY_V1` (מאומת 4/4, RULED) ·
אמת-מול-פנטום (5/5) · **TZ** `V9_CHART_TZ` default=New_York (מתקן את ה-+1h שלך) · טבלת `v9_day_type_state` נרשמה ·
`SIZE_CAP_OVER_FIXED_V1` · `HTLB_LATCH_RESET_V1` · `NONCONVICTION_ACTIVE_V1` · תיקון System-6 `stop_wrong_side` ·
EXIT-trio→RULED (flag_guard **62**) · לוגר **Google-Sheets** לעסקאות-לייב (`GSHEETS_TRADE_LOG`, URL מאומת 200) ·
קישורי-UI (מוניטור/TopBar/trades → gsheets). פסיקת-ZLR נשמרה ל-`ZLR_MGMT_V1` (לא-מיושם עדיין).

**S-1 — רצף-הבוקר שלך (לפני הפתיחה):**
1. **TZ:** אתה Eastern → אל תגדיר `V9_CHART_TZ`. `restart BRIDGE` → `DELETE FROM v9_bars_5min_woodies WHERE ts>now();` → אמת `count(*) WHERE ts>now()` = **0**.
2. **טבלאות:** `restart backend` → `to_regclass('v9_day_type_state')` + `('v9_bars_5min_continuous')` לא-NULL → רוקן `/tmp/backend.err.log`.
3. **דגלים:** `python3 scripts/sync_env_from_ruled.py --apply` → `flag_guard` **PASS 62**. ⚠ מדליק `BOOT_DAYTYPE_REPLAY_V1` — בטוח **רק** אם שלב-1 נתן 0 ברי-עתיד.
4. **is_sim:** `MEMS26_MODE=sim` → restart feeder → `is_sim=1`.
5. **re-arm:** Sierra Input 22=1 · Input 20 (Yesterday-IB).
6. **צ'אט:** `frontend/v9/.env.local` עם `NEXT_PUBLIC_BRIDGE_TOKEN` → restart frontend.
7. **gsheets:** ל-.env: `GSHEETS_TRADE_LOG_URL=https://script.google.com/macros/s/AKfycbzCuIom446by14hwIOx6K_F_4O8eTDYUpnn1G2Qr2SgDZYSVW76wGVeVebrUo9Mn6kq7Q/exec` + `GSHEETS_TRADE_LOG=1` → restart backend.
8. **op=EXIT-v2:** ממתין ל-DLL + פסיקת-מייקל. 3 דגלי-EXIT OFF (נאכפים).
9. **אמת:** `bash scripts/mems26_preflight.sh` → 0 חוסרים.

**דווח בחזרה כאן** (רשומה חדשה בראש, מאת cc-imac): flag_guard count · future-bars · day_type+bar_count · is_sim · preflight verdict · האם עסקת-לייב ראשונה נכתבה לגיליון.
