# פרומפט CC — סגירת pytest (החלטות Michael) + הפיכת CVD לחי (#4)

> להדבקה ב-Claude Code. **קרא קודם `CLAUDE.md` + `.cursor/rules/...mdc`.**
> SHADOW בלבד · אפס נגיעה ב-order/DEMO/LIVE/risk/sizing/polling · רגרסיה לכל שינוי ·
> דוח אוטומטי לכל שלב (פורמט קבוע, פלט גולמי).
>
> **k נעולים על ה-priors הנוכחיים** (Michael 31/5) — אל תכייל ערכים, השתמש כפי שהם.

---

## חלק A · סגירת 22 כשלי ה-pytest (לפי החלטות Michael 31/5)

מקור: `docs/reports/PYTEST_37_ROOT_FIX_2026-05-31.md`.

1. **cross_context / snapshot (8 טסטים)** — Michael אישר: **עדכן את הטסטים** ל-output
   הנוכחי של `accept_setup` (`trigger="system_2"` לא `"entry"`). קודם `rg` לוודא
   ששום קוד production לא מצפה ל-`"entry"` בשדה הזה (זה audit/journal). דווח.

2. **`get_active_trades` — PENDING=active (2 טסטים)** — Michael החליט: **PENDING נחשב
   active**. תקן את `get_active_trades()` לכלול `PENDING` (יחד עם FILLED/PARTIAL).
   ⚠️ זה משנה סמנטיקת lifecycle/slot — ודא ש**ניהול ה-slot** מונע ירי הזמנה שנייה
   בזמן ש-PENDING תלוי (מניעת פוזיציה כפולה). הוסף רגרסיה. דווח.

3. **NT skip counter (2 טסטים)** — קודם **אבחן**: 3 הקריאות ל-`process_bar()` הן
   **3 ברים שונים או אותו בר 3 פעמים?** הדבק ראיה.
   - אם אותו בר → ה-dedup תקין, **הטסט שגוי** → עדכן טסט.
   - אם ברים שונים → באג בקוד → תקן שהמונה יצטבר + רגרסיה.

4. **8 ordering + 2 mixed** — `pollution` של state משותף. הוסף **DB isolation
   fixtures** (session-scoped / autouse cleanup) — infra בלבד, אפס לוגיקת מסחר.
   ל-2 ה-mixed: אחרי ה-isolation, אם נשאר חלק לוגיקת-מסחר → **STOP ודווח** (לא לתקן לוגיקה).

**יעד:** `pytest -q` נקי, או תיעוד מדויק של כל נותר + סיבה.

---

## חלק B · #4 — `S1_CVD_OPENING` חי (מחליף את סיווג הפתיחה)

**החלטת Michael 31/5:** ה-CVD יחליף את סיווג הפתיחה **החי**, מקצה-לקצה (לא רק shadow).

**מצב נוכחי:** `detect_opening_type_cvd()` מייצר label של CVD **לצד** התוצאה המקורית;
המקורי (מבוסס-מחיר) הוא תמיד הנתיב החי.

**שינוי נדרש:**
- כש-`S1_CVD_OPENING=True` **ו**-CVD/footprint זמין → ה-label של ה-CVD הופך
  ל-**opening_type החי** ומזין `DECISION_MATRIX` → `day_type` → playbook.
- כש-הדגל OFF **או** CVD/footprint חסר (אין `v9_bars_footprint.delta` לחלון) →
  **fallback** למסווג המחיר המקורי (`detect_opening_type`). מקור-אמת: אם אין CVD,
  לא לסנתז — ליפול חזרה.
- **golden regression:** flag OFF ⇒ זהה לחלוטין למקורי. flag ON + CVD זמין ⇒ ה-label
  של CVD בשימוש. flag ON + CVD חסר ⇒ fallback למחיר. הדבק פלט גולמי.

⚠️ זה **משנה התנהגות ב-SHADOW** (CVD עכשיו באמת משפיע על day_type) — לאסוף baseline
לפני/אחרי של התפלגות opening_type/day_type וקצב ירי, ולדווח. אפס נתיב ל-order.

---

## תוצרים
- חלק A: `docs/reports/PYTEST_CLOSE_2026-05-31.md` — לכל אשכול: פעולה + raw before/after
  + `pytest -q` סופי + כל (C) שנשאר עם הצעה.
- חלק B: `docs/reports/S1_CVD_LIVE_2026-05-31.md` — manifest השינוי, golden regression
  גולמי (OFF=identical / ON-with-CVD / ON-no-CVD fallback), baseline SHADOW לפני/אחרי.

## אסור
לשנות לוגיקת מסחר כדי לעבור טסט (מעבר ל-#2 שאושר) · לסנתז CVD · לנתב ל-order/DEMO/LIVE ·
לכייל k · לגעת ב-polling/sc_study.
