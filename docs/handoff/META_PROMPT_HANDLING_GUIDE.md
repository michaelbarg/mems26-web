# מדריך ניהול מגה-פרומפטים — MEMS26
**Version:** 1.0 · 2026-05-27
**משתמש:** מייקל
**עדכון:** לפי הצורך

---

## מה זה מגה-פרומפט?

מגה-פרומפט הוא מסמך הנחיות מפורט שנשלח ל-Agent (Claude Desktop או CC).
הוא מגדיר:
- **מה לבדוק / לבנות** — בצורה מדויקת, עם פקודות ספציפיות
- **אמות מידה להצלחה** — PASS / FAIL / WARN
- **פורמט דוח** — מה לדווח חזרה
- **סימני עצירה** — מתי לעצור ולשאול את מייקל

---

## זרימת עבודה סטנדרטית

```
Cursor כותב מגה-פרומפט
        ↓
מייקל שולח ל-Desktop  ← [כאן אתה]
        ↓
Desktop שולח ל-CC (Claude Code)
        ↓
CC מריץ בדיקות / בונה קוד / מדווח
        ↓
מייקל מדביק את דוח CC ל-Desktop
        ↓
Desktop מסכם ומגיש ל-מייקל
        ↓
מייקל מביא ל-Cursor לאישור G3
        ↓
Cursor מבצע G3 ✅ / ❌
```

---

## איך לשלוח מגה-פרומפט ל-Desktop

### שלב 1: פתח את הקובץ
```
docs/handoff/META_PROMPT_<שם>.md
```

### שלב 2: העתק את **כל** תוכן הקובץ

### שלב 3: פתח Claude Desktop → צ'אט חדש

### שלב 4: הדבק את הטקסט ושלח

### שלב 5: Desktop יפיק "CC MEGA PROMPT" — שלח אותו ל-CC

### שלב 6: CC מסיים → הדבק את הדוח ב-Desktop שוב

### שלב 7: הבא את הדוח ל-Cursor לבדיקת G3

---

## סדר עדיפויות לשאר היום (2026-05-27)

### עכשיו — אם Services כבויים (לפני RTH)

| # | קובץ מגה-פרומפט | זמן משוער CC | עדיפות |
|---|---|---|---|
| 1 | `META_PROMPT_SPEC_AUDIT_S4_WOODIES.md` | ~30 דק' | 🔴 CRITICAL |
| 2 | `META_PROMPT_SPEC_AUDIT_S2_FIVE_MIN.md` | ~20 דק' | 🔴 CRITICAL |
| 3 | `META_PROMPT_SPEC_AUDIT_S1_DAY_TYPE.md` | ~15 דק' | 🟡 HIGH |
| 4 | `META_PROMPT_SPEC_AUDIT_BRIDGE.md` | ~20 דק' | 🟡 HIGH |

**ניתן לשלוח 1+2 במקביל** לשני sessions שונים של CC.

### לאחר קבלת דוחות
1. הבא דוחות ל-Cursor
2. Cursor עורך G3 על כל דוח
3. פותרים FAILs לפי עדיפות
4. מניעים לשדואו

---

## מה לעשות כשCC מחזיר שגיאה

| שגיאה | פעולה |
|---|---|
| `ModuleNotFoundError` | CC צריך `cd /Users/michael/Downloads/mems26_web_git` ראשון |
| `ImportError` | בדוק את הנתיב — אולי שינוי שם מודול |
| Service לא רץ | לא חשוב לבדיקת קוד — ממשיכים |
| `pytest: no tests ran` | בדוק שהנתיב נכון |

---

## תיוק מגה-פרומפטים

| תיקייה | תוכן |
|---|---|
| `docs/handoff/META_PROMPT_*.md` | פרומפטים **לDesktop** (כותב CC mega-prompts) |
| `docs/handoff/CC_MEGA_PROMPT_*.md` | פרומפטים **לCC** (מגיעים מDesktop) |
| `docs/handoff/NEXT_CHAT_*.md` | המשך שיחה בצ'אט הבא |
| `docs/reports/` | דוחות G3 וסיכומי UAT |

---

## חוקים

1. **אל תשנה קוד** לפני שדוח CC מגיע ל-Cursor לאישור
2. **אל תשלח פרומפט חדש לCC** לפני שהקודם סיים
3. **כל דוח CC** עובר G3 ב-Cursor לפני שמקדמים
4. **Strategic stop** — אם CC מוצא FAIL חמור, עוצרים ושואלים מייקל
5. **לא מתקדמים ל-LIVE** עד שכל ה-CRITICAL checks ירוקים
