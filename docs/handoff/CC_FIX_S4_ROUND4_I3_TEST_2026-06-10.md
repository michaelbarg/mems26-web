# CC ROUND‑4 — טסט אחד שבאמת מוכיח I‑3 (2026‑06‑10)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. סבב‑4 **ממוקד בטסט יחיד**. אל תיגע בשום דבר אחר — סבב‑3 אומת ע"י Cowork (A/C/D תקינים, GHOST‑test אמיתי `detected=True · measure=4.4`).

## הבעיה היחידה שנותרה (אומת ע"י Cowork, raw)
`test_s4_fire_setup_routable` **לא בודק את I‑3.** האסרטים בפועל:
```
assert len(ws._active_patterns) > 0
assert zlr[0].stop is not None and zlr[0].stop > 0   # ← זה התיקון הישן (stop=None crash, 06-08)
```
זה בודק **stop≠None** — לא `fire_setup`/R:R≥1. ה‑docstring מבטיח "closes I‑3 · R:R≥1" אבל אף assert לא נוגע ב‑target/R:R. וה‑RED‑on‑revert בדוח הוא של ה‑stop‑fallback, **לא** של לוגיקת‑ה‑T1. ⇒ **אם אהפוך את תיקון‑ה‑T1, הטסט יישאר ירוק** = הוא לא מאמת את ליבת‑העבודה.

## התיקון (חד‑משמעי)
המטרה: הטסט יוכיח ש‑**T1 מהאפיון (סולם/measure) הופך את ה‑setup ל‑routable (R:R≥1)**, וש‑**target מנוון (12T קבוע) חוסם** — בדיוק I‑3.

1. **חשוף את ה‑outcome האמיתי.** `fire_setup` הוא כיום משתנה‑מקומי ב‑`process_bar`. הוסף (additive, לא fire‑path) חשיפה כדי לבדוק: `self._last_fire_setup = fire_setup` (גם כשהוא None), או לכוד דרך gateway‑mock את ה‑setup שנותב. אל תשנה התנהגות — רק חשיפה לבדיקה.
2. **assert על הצרכן האמיתי** (לא stop≠None):
   - `fs = ws._last_fire_setup; assert fs is not None` (gate)
   - `rr = abs(fs["t1_price"] - fs["entry_price"]) / abs(fs["entry_price"] - fs["stop_price"]); assert rr >= 1.0` — R:R מ‑T1 האמיתי.
   - (אם יש דגל/שדה `ready_to_route` בנתיב — assert עליו במקום/בנוסף.)
3. **RED‑on‑revert של ה‑TARGET (לא ה‑stop):** הוכח בפועל — שנה זמנית את חישוב‑ה‑T1 ל‑12T הקבוע הישן (`_s4_t1 = entry + sign*12*0.25`), הרץ → ה‑R:R יוצא ~0.3 (12T=3pt על סטופ ~10pt) → ה‑assert על `rr>=1.0` **נכשל**. הדבק את ה‑FAIL הגולמי, ואז שחזר → green.

> מבחן‑הליטמוס: הפיכת **לוגיקת‑ה‑T1** (לא ה‑stop) חייבת להפוך את הטסט לאדום. אם לא — הטסט עדיין פסול.

## ⛔ אסור לגעת
כל השאר מסבב‑3 (FIX A/B‑GHOST/C/D) תקין — אל תיגע. אל תשנה את לוגיקת‑ה‑T1/target עצמה (רק חשיפה לבדיקה + הטסט). Standing Decisions · §Polling Floors · default‑behavior.

## Acceptance + מה Cowork יאמת בחזרה
- הדבק `pytest tests/v9/regression/test_s4_targets_spec.py::test_s4_fire_setup_routable -v` (PASS) + **הדבקת ה‑FAIL הגולמי** מ‑RED‑on‑revert של ה‑T1.
- **אני (Cowork) אהפוך בעצמי את לוגיקת‑ה‑T1 ל‑12T ואריץ את הטסט — הוא חייב להיכשל.** אם יישאר ירוק → עדיין NO‑GO.
- עדכן `MEGA_S4_TARGETS_2026-06-10.txt` (טסט מתוקן + FAIL גולמי). (ענף ahead — Michael ידחוף.)
