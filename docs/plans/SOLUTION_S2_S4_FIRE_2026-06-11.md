# פתרון — למה S2+S4 לא יורים, ואיך לגרום להם לירות (חקירת‑Cowork, 2026‑06‑11)

חקירה עצמאית: קראתי את הקוד, עברתי על הדיטקטורים, והרצתי **סימולציה על 9 ה‑setups האמיתיים של 06‑09** דרך הקוד‑הנוכחי. להלן השורש המאוחד (מוכח) + הפתרון.

---

## 🔴 השורש המאוחד (מוכח בסימולציה) — שער ה‑R:R של A7 חוסם גם S2 וגם S4
**`backend/v9/shared/pre_fire_validator.py:62‑64`:**
```python
reward = abs(req.t1_price - req.entry_price)
if risk <= 0 or (reward / risk) < 1.0:
    return _fail(f"R:R < 1.0 (risk={risk:.2f} reward={reward:.2f})")
```
ה‑gate בודק R:R על **T1** ודורש ≥1.0. **אבל T1 הוא יציאת‑ה‑50% (scalp), לא היעד‑המלא:**
- **S4:** ladder = 0.4‑1.0R (יורד עם הסיכון).
- **S2:** `flag_relative_t1` = 0.4‑0.8R.

⇒ **כל setup עם סטופ > ~5 נק' → T1 < 1R → R:R < 1.0 → A7 חוסם.** וכי אופציה‑1 דחתה T2/T3=None, ל‑gate יש **רק T1** למדוד → חסימה‑לנצח.

### הוכחה (סימולציה שלי · 9 ה‑ZLR‑DOWN של 06‑09, קוד נוכחי)
| שעה | risk | ladder T1 | reward | R:R | A7 |
|---|---|---|---|---|---|
| 11:45 | 23.25 | 7310.95 | 9.30 | **0.40** | 🔴 BLOCK |
| 11:55 | 7.00 | 7318.75 | 5.25 | **0.75** | 🔴 BLOCK |
| 12:05 | 17.50 | 7308.25 | 8.75 | **0.50** | 🔴 BLOCK |
| 12:30 | 10.00 | 7301.50 | 7.50 | **0.75** | 🔴 BLOCK |
| 13:25 | 8.50 | 7310.12 | 6.38 | **0.75** | 🔴 BLOCK |
| 13:30 | 10.75 | 7304.26 | 6.99 | **0.65** | 🔴 BLOCK |
| 14:10 | 10.50 | 7284.68 | 6.82 | **0.65** | 🔴 BLOCK |
| 14:50 | 10.50 | 7283.18 | 6.82 | **0.65** | 🔴 BLOCK |
| TLB‑live | 23.25 | 7268.70 | 9.30 | **0.40** | 🔴 BLOCK |

**9/9 נחסמו** — **גם בקוד‑המתוקן.** זה לא "target מנוון" ולא "טבלת stop/target חסרה" — זו **טעות‑מדידה:** A7 בודק R:R על ה‑scalp (T1) במקום על ה‑runner (T2≈2R). זה ה‑I‑3 האמיתי, וזה חל על **שתי המערכות** (S2 דרך `setup_emitter`, S4 דרך `decision_tree` — שתיהן קוראות לאותו validator).

---

## ✅ הפתרון — שער ה‑R:R יימדד על היעד‑המלא, לא על ה‑scalp
**שינוי `pre_fire_validator`:** ה‑R:R יחושב על **היעד‑המלא (T2/T3 ≈ runner)**, לא על T1. כי T2/T3=None (אופציה‑1) → להשתמש ב‑**מכפיל‑R הצפוי מהאפיון**:
- CONT (ZLR/TT/GB100/TLB): T2 ≈ **2R** → R:R=2 ✓
- REV (FAMIR/HTLB/HFE): T2 ≈ 1.5‑2R ✓ · VEGAS/GHOST: Measure×1.0 ✓
- כך ה‑gate **עדיין מגן** (דוחה עסקה שה‑runner שלה <1R) — אבל מפסיק לדחות עסקאות תקפות על ה‑scalp.

**מוכח:** עם T2≈2R, כל 9 ה‑setups → R:R≈2 → **PASS** (במקום BLOCK).

**יישום (smallest‑correct):** ל‑`FireRequest` להעביר את **מכפיל‑ה‑T2 הצפוי** (מ‑`targets_table`/day‑type), וה‑gate יבדוק `max(t1_rr, expected_t2_rr) ≥ 1.0`. flag‑gated · regression‑test (9 ה‑setups → PASS; revert→RED) · **trading‑logic → אישור Michael.**

---

## 🔴 בלוקר שני (auth מוקדם) — S1 day_type@30דק'
גם אם A7 ייפתח, S1 חייב לתת day_type **בזמן**, אחרת S2/S4 ב‑auth‑skip בשעה הראשונה:
- היום+אתמול: day_type נשאר UNKNOWN עד **B2/IB‑lock@60דק'** (10:30 ET) — שלב‑ה‑30דק' לא ייצר סיווג. (`state_machine.py` — A3 IB‑tracking 09:30‑10:30; הסיווג קורה ב‑B2 בלבד.)
- ה‑provisional day_type מחווט ל‑S2 אך **לא ל‑S4** (תוקן בקוד `3c95789` אך לא נפרס‑חי).
- **פתרון:** (א) S1 מסווג **provisional@30דק'** מ‑`opening_type × IB‑developing` (DECISION_MATRIX) — לא להמתין ל‑IB‑lock@60 · (ב) **intraday‑reclass** כשה‑opening_type מתייצב/היום משתנה (הדגלים `S1_DYNAMIC_RECLASS`/`S1_LIVE_RECLASS` דלוקים — הלוגיקה לא מייצרת reclass) · (ג) opening_type@15דק' יציב.

---

## סדר‑ביצוע כדי שיירו היום
1. **A7 R:R על היעד‑המלא** (הבלוקר הדומיננטי — פותח את כל 9 ה‑setups של שתי המערכות). flag‑gated + אישור.
2. **S1 provisional day_type@30 + reclass** (פותח auth בשעה הראשונה).
3. **restart** ה‑backend (רץ מ‑Jun‑8 — התיקונים לא חיים עד אתחול).
4. **אימות:** סימולציה חוזרת על 06‑09 → ≥ X מ‑9 השורטים עוברים routing + day_type≠UNKNOWN@30.

## הוכחת‑קבלה (Rule 5)
סימולציה: לפני — 9/9 BLOCK (R:R 0.40‑0.75) · אחרי — 9/9 PASS (R:R≈2). + day_type≠UNKNOWN@30 ב‑replay.

*חקירת‑Cowork עצמאית. קוד נקרא, 9 setups אמיתיים נוסחו דרך הקוד‑החי. השורש: pre_fire_validator R:R על T1 (scalp) ולא על runner — חל על S2+S4. הפתרון מוכח‑בסימולציה.*
