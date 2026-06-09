# CC PROMPT — אימות code↔doc parity לצינור המלא (READ-ONLY)

**תאריך:** 2026-05-31 · **מקור:** Cowork (Michael ביקש מסמך As-built + פערים, ו-CC מאמת מולו)
**מצב:** SHADOW בלבד · אפס שינויי קוד · diagnose/verify-first
**המסמך לאימות:** `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md`

---

## מטרה

המסמך הנ"ל מתאר את כל הצינור מ-**זיהוי סוג-היום (S1)** ועד **ניהול עסקה וסגירה** ב-30 שלבים (Phase 0–6), מסומן ✅ (קוד=אפיון) ו-⚠️ GAP (פער פתוח). הוא נגזר מ-`FULL_PATH_MEGA_TABLE_2026-05-31.md` + קריאת `backend/v9/gateway/`. **המשימה שלך: לאמת שכל שורה עדיין נכונה מול הקוד החי**, ולתפוס drift אם נוצר.

---

## חוקי-על (חובה)

1. **READ-ONLY.** אפס שינויי קוד. אם מצאת drift — רשום finding, אל תתקן.
2. **Rule 5 — Verification quote, not assertion.** לכל שורה שאתה מאשר/מפריך, הדבק **פקודה + פלט גולמי** (grep/קוד/pytest). "אומת ✓" בלי פלט = לא קביל.
3. **No edits from memory.** קרא את הקובץ בפועל בכל מיקום קוד שצוין במסמך.

---

## מה לעשות — אימות לפי Phase

לכל אחד מ-30 השלבים במסמך, פתח את מיקום הקוד המצוין (עמודת "קוד") ואשר:
(א) שהפונקציה/השורות עדיין קיימות שם; (ב) שהלוגיקה המתוארת תואמת לקוד; (ג) שהמספרים/הספים שצוטטו (סף, multiplier, אחוז split, threshold) זהים לקוד.

**מקד את האימות בנקודות הסיכון הבאות (high-value):**

- **Phase 1 (S1):** סף נעילה C1 (`state_machine.py:680-746`) — אשר את שלושת תנאי הנעילה (conf≥0.70 / consecutive≥2 / session_min≥210) ואת ה-`ConfidenceThreshold.__eq__` (GAP-5). אשר ספי gap ו-IB width (flag-OFF מול flag-ON).
- **Phase 3 (sizing/stop):** Auth Table 70 תאים max=3 (`auth_table_v1.py`); adaptive-stop multipliers (Reactive 1.0×/OFA 1.5×/Double-H&S 2.0×); contract split (25/50/25 · 33/33/34 · 50/50/0); time-stop per day_type.
- **Phase 4 (gateway):** 5 שערי הסיכון בסדר הנכון (`trading_gateway.py:86-141`); first-wins (`:124-139`); **GAP-4** — אשר ש-`MAX_CONTRACTS=2` לא נאכף באף `if` (`risk_checks.py`).
- **Phase 5 (trade mgmt):** stop-first priority ב-`bar_level_detector.py:43-128`; Smart BE+1T; כללי C.2/C.4/C.6/C.7 (`trade_management.py:17-124`); S4 W-10 time-stop (18 ברים).

**לכל ⚠️ GAP במסמך — אשר שהניסוח מדויק:**
- GAP-3 (first-wins): grep שאין R:R/ranking/buffering ב-`trading_gateway.py`.
- GAP-4 (MAX_CONTRACTS): grep שימושים → אשר dead.
- GAP-6 (ZLR): אשר RESOLVED — הרץ `pytest tests/v9/systems/woodies/ -v -rsxX` והדבק שורת הסיכום (0 failed, 0 skipped על ZLR). זה גם re-verify של דוח CC הקודם (Rule 5).
- GAP-1/2/5/7/8/11 + Bug C: אשר שעדיין נכונים או שהשתנו.

---

## פלט מצופה

`docs/reports/PIPELINE_DOC_PARITY_VERIFY_2026-05-31.md` הכולל:
1. טבלה: שלב # → MATCH ✅ / DRIFT ⚠️ / לא-נמצא ❌, עם **ראיה גולמית** לכל שורה שנבדקה (לפחות כל נקודות ה-high-value + כל ה-GAPs).
2. רשימת drifts שנמצאו (אם יש) — מיקום, מה המסמך אומר, מה הקוד אומר.
3. verdict כללי: האם המסמך As-built נאמן למצב הקוד נכון ל-31/5.

**אם נמצא drift מהותי בלוגיקת-מסחר → strategic-stop + דווח ל-Michael, אל תתקן.**
בסיום: עדכן `STATUS_BOARD.md` בשורת log אחת (finding+evidence, Rule 5).
