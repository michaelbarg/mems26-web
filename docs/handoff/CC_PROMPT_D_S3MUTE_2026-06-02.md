# CC Prompt — D-S3MUTE · השתקת S3 Footprint עד ייצוב 1/2/4

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**תווית החלטה:** D-S3MUTE (✅ APPROVED 2026-06-02, Michael) — ראה `docs/plans/DECISION_LEDGER.md`.
כל קוד שתיגע בו נושא הערה `# D-S3MUTE`.

## מטרה (אחת)
להוסיף מנגנון דגל שמשתיק את **S3 Footprint** (עוצר ירי + איסוף signals/trades) כדי
ש-S3 (היחיד שמפיק מלא, 142+ עסקאות) לא יציף את הסטטיסטיקות בזמן שמייצבים את S1/S2/S4.
**לא** למחוק/לשנות את לוגיקת S3 — רק לעקוף אותה מאחורי דגל, הפיך מיידית.

## רקע מאומת (verify-before-trust)
- `grep -rn "S3_MUTE" backend/` כרגע = **ריק** → המנגנון לא קיים בקוד. (אומת ע"י Cowork 2026-06-02.)
- שאר דגלי הריצה נקראים ב-`backend/v9/shared/atr.py` מ-env (כמו `S4_EXTREME_TREND_RELABEL`),
  וה-LaunchAgent קורא מ-`plist EnvironmentVariables` (לא מ-`.env`).

## Phase 1 · הוספת הדגל
- ב-`backend/v9/shared/atr.py`: הוסף `S3_MUTE = os.getenv("S3_MUTE", "0") == "1"` (default OFF =
  S3 פעיל; השתקה רק כש-`S3_MUTE=1`). הערת `# D-S3MUTE`.
- **AC1:** `python3 -c "import os; os.environ['S3_MUTE']='1'; import backend.v9.shared.atr as a; print(a.S3_MUTE)"` → `True`; בלי ה-env → `False`.
  (אם import נכשל על תלות — הוכח דרך קריאת הקובץ + טסט בודד.)

## Phase 2 · שער ההשתקה בנתיב הירי של S3
- אתר את נקודת הירי של S3: `backend/v9/systems/footprint/footprint_system.py` —
  פונקציית ה-`_fire`/ה-dedup gate (`:39`, `:426-436` לפי STATUS_BOARD). **קרא את הקוד הנוכחי**
  לפני שינוי; אם המסלול שונה — דווח ועצור (B6).
- הוסף בתחילת מסלול הירי: `if S3_MUTE: <log debug rate-limited "S3 muted"> ; return` —
  כך ש-S3 לא יוצר signals/trades כשהדגל ON. אל תיגע בחישוב ה-footprint עצמו (תצוגה/observability
  של S3 ב-Build Status נשארת — רק הירי מושתק). אם אתה מזהה נתיב כתיבה שני (signals/state) —
  השתק גם אותו, אחרת זו wiring חלקית.
- **AC2:** טסט אנטי-טאוטולוגי שמייבא וקורא לקוד הייצור (`FootprintSystem.<entry>`/`process_bar`)
  עם בר שב-`S3_MUTE=0` מפיק fire, ומוודא: `S3_MUTE=1` → **0 fires** · `S3_MUTE=0` → fire כרגיל.
  ה-assert על הצרכן האמיתי (signal שנרשם / trade שנותב), לא על משתנה ביניים.
  שורת ליטמוס חובה: *"if reverted → RED because בלי השער, S3_MUTE=1 עדיין יורה"*.

## אסור לגעת (risk surface)
- חישוב ה-footprint/CVD, ה-export מ-`sc_study`, נתיבי S1/S2/S4. רק נתיב הירי של S3.
- אל תשנה את ה-plist בעצמך — הפעלת ההשתקה (`S3_MUTE=1`) היא פעולת ops של Michael.

## Verify (Rule 5 — הדבק command+output)
- `grep -n "S3_MUTE" backend/v9/shared/atr.py backend/v9/systems/footprint/footprint_system.py`
- פלט הטסט (flag ON=0 fires / OFF=fire) — raw.

## דוח חובה (חלק C) + NOT-DONE + עדכון `STATUS_BOARD.md`+`ROADMAP_TO_LIVE.html`.
**un-mute** עתידי: כש-S1(D-S1DYN)+S2(D-RVX)+S4(D-WDIAG) מאומתים יציבים ב-RTH (`S3_MUTE=0`+reload).
