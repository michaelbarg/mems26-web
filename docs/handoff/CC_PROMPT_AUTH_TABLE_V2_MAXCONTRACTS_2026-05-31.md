# CC PROMPT — Auth Table V2 (3-5 sizing) + MAX_CONTRACTS=5 enforcement

**תאריך:** 2026-05-31 · **מקור:** Cowork · **אישור Michael:** ננעל 31/5 (ערכים + סמנטיקה)
**מצב:** SHADOW בלבד · שינוי trading-logic (sizing) → מאחורי אישור Michael שכבר ניתן.
**סוג:** מימוש מבוקר. diagnose-first, smallest correct change, Rule 5 (פלט גולמי לכל אימות).

---

## הקשר

GAP-4 נסגר: `MAX_CONTRACTS` היה dead (=2, אפס אכיפה). Michael נעל **per-trade · max 5**, וביטל את רצפת ה-min-3 (לוקחים את הטבלה כפי שהיא; 0=אל-תירה ב-tier). ה-Auth Table עובר מטווח 0-3 לטווח 0-5. זו **V2** — לא דורסים את V1 בלי לתעד.

**אסור:** לגעת ב-D-094 R:R selection / buffering (thread נפרד, פרומפט אחר). לגעת ב-order/risk gate אחר. להריץ שירותים.

---

## משימה A · Auth Table V2 (10×7 = 70 תאים, טווח 0-5)

### A1. החלף את `_AUTH_TABLE_V1` ב-`backend/v9/systems/five_min/auth_table_v1.py` בערכים הבאים

פורמט: `(verdict, HIGH, MEDIUM, LOW)`. **אלו הערכים הנעולים הסופיים** (Michael 31/5):

| Pattern | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| REACTIVE_LONG | REDUCED 3/2/1 | REDUCED 4/3/0 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| REACTIVE_SHORT | REDUCED 4/3/0 | REDUCED 4/3/0 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| INITIATIVE_LONG | FULL 4/3/2 | FULL 4/3/2 | SKIP 0/0/0 | FULL 4/3/2 | SKIP 0/0/0 | SKIP 0/0/0 | SKIP 0/0/0 |
| INITIATIVE_SHORT | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 | FULL 5/4/3 | SKIP 0/0/0 | SKIP 0/0/0 | SKIP 0/0/0 |
| INVERSE_HNS_LONG | SKIP 0/0/0 | SKIP 0/0/0 | FULL 5/4/3 | REDUCED 3/2/1 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| HNS_TOP_SHORT | SKIP 0/0/0 | SKIP 0/0/0 | FULL 5/4/3 | REDUCED 4/3/2 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| DOUBLE_BOTTOM_EE_LONG | SKIP 0/0/0 | SKIP 0/0/0 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| DOUBLE_TOP_AA_SHORT | SKIP 0/0/0 | SKIP 0/0/0 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | FULL 5/4/3 | SKIP 0/0/0 |
| BULL_FLAG_LONG | FULL 5/4/3 | FULL 5/4/3 | REDUCED 4/4/0 | FULL 4/3/3 | SKIP 0/0/0 | REDUCED 4/4/0 | SKIP 0/0/0 |
| BEAR_FLAG_SHORT | FULL 5/4/3 | FULL 5/4/3 | REDUCED 4/4/0 | FULL 5/4/3 | SKIP 0/0/0 | REDUCED 3/2/1 | SKIP 0/0/0 |

(DayType: TN=Trend_Normal, TDD=Trend_DD, NeuE=Neutral_Extreme, NV=Variation, NeuC=Neutral_Center, Norm=Normal, NT=Nontrend.)

### A2. עדכן את האסרטים (שורות 106-115)
- `assert max(max(v[1],v[2],v[3]) ...) == 3` → **`== 5`**.
- שאר האסרטים נשארים: 70 תאים · SKIP→0/0/0 · Nontrend→SKIP. אמת שכולם עדיין עוברים.
- ⚠️ שים לב: הערכים **אינם** חייבים min-3 — תאים כמו `4/3/0`, `3/2/1`, `4/4/0` תקינים ומכוונים (Michael ביטל את רצפת ה-min-3). אל "תתקן" אותם.

### A3. עדכן ספק-אמת
- צור `docs/spec_authority/S2_AUTH_TABLE_V2.md` (העתק מבנה מ-V1, סטטוס LOCKED 2026-05-31, מקור Michael chat 31/5, "Q6 max contracts → cap 5, no min floor", הטבלה לעיל). עדכן את comment ה-Authority ב-`auth_table_v1.py` להצביע על V2.
- אל תמחק את V1 (ארכיון).

### A4. Golden regression + tests
- שינוי sizing → ה-baseline משתנה. הפק diff **לפני→אחרי** של פלט `get_auth_cell` לכל 70 התאים (טבלה old→new) והדבק בדוח.
- עדכן/הוסף טסטים שמאמתים את 70 התאים החדשים. הרץ `pytest tests/v9 -k "auth or quality or sizing"` והדבק פלט גולמי (0 failed).
- אמת שאין שבירה ב-`quality_tier.py` (consumer של הטבלה).

---

## משימה B · אכיפת MAX_CONTRACTS=5 (per-trade)

### B1. `backend/v9/gateway/risk_checks.py`
- `MAX_CONTRACTS = 2` → **`MAX_CONTRACTS = 5`**.
- הוסף בדיקת אכיפה **per-trade**: ב-`passes_strict_checks` (LIVE), אם `contracts > MAX_CONTRACTS` → block + `logger.warning`. מצא מאיפה מגיע מספר החוזים ב-setup (per GAP-4 audit: `T1Setup.sizing_contracts` → gateway `metadata.sizing`). אם השדה לא נגיש שם — **עצור ודווח** (אל תנחש את שם השדה; diagnose-first).
- שיקול: מאחר ש-Auth Table V2 חוסם ל-5 by-construction, הבדיקה היא הגנתית (תופסת drift). זה רצוי — לא לדלג עליה.

### B2. Regression test
- טסט: setup עם 6 חוזים → blocked; עם 5 → passes; עם 3 → passes. הדבק פלט גולמי.

### B3. אל תיגע ב-SHADOW caps
- SHADOW נשאר unbounded (slots בלתי-מוגבל) — אל תאכוף עליו max-contracts. האכיפה היא DEMO/LIVE per-trade בלבד.

---

## פלט מצופה

1. `docs/reports/AUTH_TABLE_V2_MAXCONTRACTS_2026-05-31.md`: diff old→new של 70 התאים · פלט pytest גולמי · אישור האסרטים (max=5) · diff של risk_checks · פלט טסט האכיפה.
2. commits נפרדים: (A) Auth Table V2, (B) MAX_CONTRACTS enforcement.
3. עדכון `STATUS_BOARD.md` שורת log אחת (finding+fix+evidence, Rule 5).

**שערים:** אם `contracts` לא נגיש ב-`passes_strict_checks` → strategic-stop ודווח לפני שינוי. אל תיגע ב-D-094 (thread נפרד). SHADOW בלבד — אפס DEMO/LIVE/order.
