# פריט 2 מתוך 8 — הסטופ המבני של כניסה-בדחייה-השנייה סמכותי בשער (רצפות-הסטופ לא מרחיבות אותו), ו-T1 = POC או הקצה-הנגדי
(פריט 1 אומת ותוקן ע"י cowork — `c47eaa62`. הפריט הזה הוא מה שעצר את הגולדן **אחרי** שהוא ירה.)

## הראיה (הרנס 11.09, `CEILING_FLIP_TOUCH2_V1=shadow`)
```
17:30:03 [CeilingFlipTouch2] CEILING_TOUCH2_REJECT → SHORT entry=7674.75 stop=7679.00 anchor=7678.75 T1=7670.50 T2=7663.25
17:30:03 route CEILING_FLIP_TOUCH2 SHORT 7674.75 → rr_entry_gate | T1_dist=3.75 < stop_dist=7.75 × 0.65
```
הסטופ המבני של התבנית הוא **4.25** (7679 = השיאים + טיק). השער הרחיב אותו ל-**7.75** (רצפת-סטופ 35%×IB=7.8 / `STOP_FLOOR_IB_V1` / `StopResolver`), ואז יעד-POC (7670.5, 4.25 נק') נראה קצר מדי ⇒ נחסם. כלומר: הכניסה של דלתון נהרגת ע"י כלל שנועד לתבניות אחרות. פסיקת 09.09 10:20: **הסטופ = העוגן המבני, הגודל נגזר** — לא סטופ מורחב.

## מה לבנות
1. **סמכות-סטופ למבנה:** setup שנושא `metadata.stop_is_structural=True` (המפיקים: `CEILING_FLIP_TOUCH2`, `CEILING_FLIP_*`, ו-DOUBLE_TOP/BOTTOM כשיש anchor) — `StopResolver`/`STOP_FLOOR_IB`/`STEP_SCALED_LADDER`/ATR-floor **לא מזיזים** את הסטופ; הם רשאים רק לרשום `[ECON-DIFF]`. הגודל נגזר מהסטופ המבני (`RISK_BUDGET`): 4.25 נק' ⇒ n=min(5, floor(225/(5×4.25)))=5 ⇒ `min(ruled)=5`. אם n<3 ⇒ אין כניסה (לא מקטינים סטופ).
2. **יעדים לפי הדוקטרינה (11.09 09:50):** T1 = POC; **אם POC בתוך 0.65×stop מהכניסה או בצד הלא-נכון ⇒ T1 = קצה-הערך הנגדי (VAL/VAH), T2 = קצה-ה-IB הנגדי**. שרשרת מונוטונית (T-335 קיים). runner=false.
3. **שער R:R** נשאר — אבל מחושב על הסטופ המבני והיעד הנכון: 17:30 ⇒ stop 4.25, T1 = VAL 7663.25 (11.5) ⇒ R:R 2.7 ⇒ עובר.
4. `mobile_monitor` dalton-block: `stop_source: structural|resolver`.

## golden (שורות גולמיות בדיווח)
- 11.09 `17:30:03 CEILING_FLIP_TOUCH2 SHORT 7674.75 stop 7679.00 T1 7663.25 T2 7659.75 n=5 → ADMIT` (shadow — המפיק ב-shadow; ה-route חייב להראות `blocked_by=None` ו-`shadow_only=True`).
- 10.09 `17:10:03 FLOOR_TOUCH2 LONG 7587.50 stop 7585.25 T1 7602.75 → ADMIT` (shadow).
- 11.09 `18:05:03 FLOOR_TOUCH2 LONG 7664 stop 7654` — נשאר admitted, n נגזר (10 נק' ⇒ 4).
- **אפס שינוי** בכתיבות של 08-03 · 08-04 · 09-09 · 10.09 · 11.09 (`REACTIVE_SHORT 18:55` נשאר היחיד ב-11.09) — הסמכות חלה רק על setups עם `stop_is_structural`.
- הרנס ×5 + `--restart-at 18:29` ירוק, 0 Traceback; `test_structural_stop_authority.py`: מוטציה — setup בלי הדגל ⇒ ה-resolver עדיין מזיז.

## דיווח
קומיט אחד, TASK_LOG+STATUS_BOARD באותו קומיט, LOG חתום עם השורות. **לעצור ולכתוב "סיים פריט 2".** אין ריסטארט (המתוזמן 15:45 מרים HEAD).
