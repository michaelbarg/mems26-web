# CC PROMPT — אבחון firing של S1 + S2 על ה-PG (read-only, מגדיר מה לתקן לפני SHADOW) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** **read-only / diagnostic — אל תתקן עדיין.** אישור Michael 2026-06-04.
מטרה: לדעת **בוודאות מהנתונים** (לא מאבחון 2/6 הישן) אם S1/S2 יורים על ה-PG, כדי שנחליט מה לתקן לפני SHADOW.
מצב-DB: כל מחלקת ה-DB סגורה ומאומתת (PG, split-brain נסגר).

## הקשר מהקוד (אימת Cowork, static)
- **S1:** `day_type/state_machine.py` **כן** משתמש ב-`bar.atr` (gap ratio :427, range :589/617, **re-eval :784** `atr = bar.atr`).
  כלומר נתיב ה-re-eval קיים — השאלה היחידה: **האם `bar.atr` מוזן** כשהבר מגיע ל-state-machine, או None (כפי שדווח 2/6 → re-eval מת, hard-lock דה-פקטו).
- **S2:** `five_min_system.py:_detect_reactive` כבר מכיל **גייט 3-וריאציות** (`S2_VSA_VOLUME` flag): ON→VSA (Variant A: `b2<b1 & b2<b0 & b2≤0.7·rolling_avg`),
  RVOL (`b2≤0.5·rolling_avg`), אחרת legacy (`b2 ≤ b1·DROP_THRESHOLD_PCT` — הגייט ה"בלתי-אפשרי" 0/1085). כלומר "S2 לא יורה" **לא בהכרח נכון** אם הדגל ON.

## אבחון נדרש (raw, על PG; אם RTH סגור — replay על ברי `v9_bars_5min`)
### S1 day-type
1. האם `bar.atr` מוזן ב-boundary של ה-state-machine? אתר היכן `BarInput` נבנה לפני `day_type` ובדוק אם `atr` מוצב (לא None). הדבק את הערך לכמה ברים אמיתיים.
2. האם re-eval **יורה אי-פעם**? שאילתת PG: התפלגות `lock_state` ב-`v9_day_type_state` (PENDING/LOCKED/…), והאם `current_day_type` מתקדם אחרי lock או תקוע.
3. מסקנה: S1 חי או תקוע, ואם תקוע — **השורש המדויק** (bar.atr=None? trigger? hard-lock?).

### S2 reactive
4. מה מצב הדגל `S2_VSA_VOLUME` בפועל (env בזמן ריצה)?
5. הרץ את 3 הווריאציות על ברי-RTH אמיתיים אחרונים (או replay) → לכל וריאציה: **כמה ברים עוברים** את הגייט (מתוך N). זה מחליף את "0/1085".
6. ספירות בפועל: `v9_five_min_setups` count · `v9_trades WHERE firing_system=2` · האם S2 **יכול** לירות היום ובאיזו וריאציה.

## תוצר (raw, ל-Cowork להצלבה)
- טבלה: S1 — bar.atr מוזן? (✓/✗ + ערכים) · re-eval יורה? · שורש אם תקוע.
- טבלה: S2 — דגל · pass-rate פר-וריאציה · setups/fires count · "יכול לירות?".
- **המלצה:** מה התיקון ל-S1 (אם bar.atr לא מוזן — היכן לחווט) ואיזו וריאציה ל-S2 (קלט להחלטת D-RVX של Michael). **אל תתקן** — רק אבחן + המלץ.

## Invariants
read-only · localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · אל תיגע risk-logic/sc_study · No silent failures · Cowork מאמת בלתי-תלוי. החלטת D-RVX + תיקון S1 = שלב נפרד אחרי האבחון.
