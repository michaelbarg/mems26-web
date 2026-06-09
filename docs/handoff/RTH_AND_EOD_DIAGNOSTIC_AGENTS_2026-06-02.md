# MEMS26 — 2 סוכני אבחון (RTH כל 30 דק' + סוף-יום) · brief לצ'אט חדש

מסמך זה מברִיף צ'אט Cowork חדש להפעיל **2 סוכנים read-only**. שניהם **לא משנים שום קוד/DB/שירות** — תצפית בלבד, ומדווחים. אם מוצאים בעיה — **מדווחים, לא מתקנים**.

## רקע (לקריאה ראשונה)
- MEMS26 = מסחר אוטונומי, מצב **SHADOW** (אין הזמנות אמיתיות). 4 מערכות: **S1** סוג-יום · **S2** Five-Min/Reactive · **S3** Footprint (**מושתק זמנית**, `FOOTPRINT_DISABLED`) · **S4** Woodies.
- DB: `data/mems26_local.db` (השתמש ב-python3/sqlite3, read-only). RTH = 16:30–23:00 IL.
- ה-9 תבניות של Woodies (S4): ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE.
- S2 וריאציות: A_VSA / B_RVOL / C_STRICT.
- מקור ה"למה לא ירה": Build Status מחזיר per-pattern `blocked_reason` (endpoint `build/pattern-status`); + הטבלאות ב-DB.
- **verify-before-trust:** הצלב מול DB, אל תאמין להנחות.

---

## סוכן A · בדיקה כל 30 דק' ב-RTH (recurring)
**מתי:** כל 30 דק', 16:30–23:00 IL, ימים א–ה. (scheduled task; אפשר להשתמש ב-`mems26-rth-monitor` הקיים או ליצור חדש.)
**מה לדווח (קצר, בעיות בראש):**
1. **בריאות DB:** `PRAGMA quick_check` = ok? (אם לא → 🔴 ALERT corruption.)
2. **לכל מערכת (S1/S2/S4):** רצה? מקבלת נתונים טריים? **ירתה היום?** אם לא ירתה — **למה?** (הגייט החוסם מ-`blocked_reason`).
3. **לכל תבנית (9 של Woodies + 3 וריאציות S2):** סטטוס armed/blocked/fired + הסיבה החוסמת.
4. **day_type:** מסווג? עבר Normal→Variation→Trend? (IB ננעל?)
5. **טריות streams:** bars_5min, woodies_5min, cumulative_delta, imbalance — סמן stale (>10 דק' ב-RTH).
6. **חריגות.**
פלט קצר וסרוק. אם RTH סגור → שורה אחת "RTH סגור".

---

## סוכן B · ניתוח סוף-יום (פעם אחת, ~23:05 IL)
**מתי:** פעם ביום אחרי סגירת RTH (~23:05 IL).
**מטרה:** לכל מערכת ולכל תבנית — **למה לא ירתה היום**, מגובה בנתונים, + **המלצה**.
**מבנה הדוח (שמור ל-`docs/reports/EOD_FIRE_ANALYSIS_<date>.md`):**
1. **סיכום ירי היום:** טבלה — מערכת · #fires (per mode) · #setups · #blocked. (מ-`v9_trades`, `v9_five_min_setups`, `v9_woodies_signals`, `v9_system_signals`.)
2. **לכל תבנית (9 Woodies + 3 וריאציות S2):** כמה פעמים נדרכה (armed), כמה ירתה, וה-**סיבה החוסמת הדומיננטית** (ספירת `blocked_reason` לאורך היום). זה הלב — "למה כל תבנית לא ירתה".
3. **day_type timeline:** מתי סווג, אילו מעברים (live + shadow), האם תאם למה שהיה צריך.
4. **streams/data quality:** מה היה טרי, מה היה תקוע (imbalance?), פערים.
5. **המלצה (data-grounded):** לכל מערכת/תבנית שלא ירתה — מה כדאי לשקול (סף יחסי? wiring? gate?), עם המספרים שתומכים. **המלצה בלבד — לא מימוש.** סמן strategic-stops (S1 Auth Table, S2 וריאציה) לאישור Michael.

---

## כללי שני הסוכנים
- read-only מוחלט. אל תיגע בקוד/DB/שירות/דגלים.
- כל טענה מגובה בשאילתת DB / `blocked_reason` גולמי (Rule 5).
- אם DB corrupt או backend למטה → דווח מיד, אל תנסה לתקן.
- הקשר מלא של היום (DB root fix, footprint מושבת, החלטות S1/S2): `docs/handoff/HANDOFF_CONTINUATION_2026-06-02_PM.md`.
