# פריט 4 מתוך 8 — שלב B נשפט לפי **מיקום**, לא לפי שם-תבנית (T-355)

**פריט 3א התקבל** (‏`e37bb2cf`). הדגל `EDGE_FADE_TARGETS_V1` נשאר **כבוי** עד שאפסוק על מספרי-הריפליי
(‏10.09 17:50 היה נעצר בסטופ ב-18:35 — ראה ההודעה בערוץ). פריט אחד, קומיט אחד, בלי שאלות.

## למה
שלב B (‏16:45–17:30, בין נעילת-הפתיחה לנעילת-ה-IB) הוא החלון שבו **סוג-היום עוד לא ידוע**, ולכן
שורת-הפלייבוק נבחרת לפי `opening_type` ומסננת לפי **שם-תבנית** (`entry_kinds`). התוצאה, לפי מפקד על
5 הסשנים בהרנס: כמעט כל מה שנולד בשלב B נחסם ב-`dalton_intent:kind` או `:bias` — כולל כניסות-קצה
קלאסיות בקצה-הסשן. זה אותו שורש בדיוק שתיקנּו לימי Normal (‏T-319b-lite): **שם-התבנית אינו הקריטריון —
המיקום הוא.**

שורות גולמיות מההרנס (‏`/tmp/h1409d`, HEAD `e37bb2cf`):
```
10.09 17:10:03 CEILING_FLIP_TOUCH2 LONG  entry=7587.5  stop=7585.25 t1=7602.0  blk=dalton_intent:kind  phase=B
10.09 17:05:03 CEILING_FLIP_TOUCH2 LONG  entry=7592.0  stop=7585.75 t1=7602.0  blk=dalton_intent:kind  phase=B
10.09 17:15:03 CEILING_FLIP_TOUCH2 LONG  entry=7593.0  stop=7585.25 t1=7602.0  blk=dalton_intent:kind  phase=B
09-09 17:05:03 CEILING_FLIP_TOUCH2 SHORT entry=7658.25 stop=7662.5  t1=7653.75 blk=dalton_intent:kind  phase=B
11.09 17:05:03 CEILING_FLIP_TOUCH2 SHORT entry=7672.0  stop=7682.25 t1=7663.25 blk=dalton_intent:kind  phase=B
08-03 16:45:03 CEILING_FLIP_TOUCH2 SHORT entry=7567.5  stop=7571.25            blk=dalton_intent:bias  phase=B
```

## מה לבנות (בדיוק זה)

**0. דגל `PHASE_B_LOCATION_V1` — ברירת-מחדל OFF בקוד. לא ב-`.env`.** שורה ב-`config/RULED_FLAGS.yaml`
עם `expected: '0'` ו-`measured: UNMEASURED`. אותה תבנית כמו 3א — אני מדליק אחרי המספרים.

**1. בשער, בתוך בלוק-דלתון:** כש-`phase == "B"` **וגם** ה-`blocked_by` שחושב הוא
`dalton_intent:kind` או `dalton_intent:bias` — להעביר את ההחלטה לכלל-מיקום, בדיוק כמו T-319b-lite:
- הקצוות בשלב B (‏ה-VA של היום עוד לא קיים): **`prior_vah`/`prior_val`** מהסשן הקודם
  (‏`tpo["previous_session"]`), ובנוסף **`session_high`/`session_low` המתפתחים** ו-`ib_high`/`ib_low`
  אם כבר קיימים (‏`ib_found`).
- `tol = location_gate._tol(ib_width or (session_high - session_low))`.
- **LONG** מותר רק אם מחיר-השיפוט ≤ `min(prior_val, session_low) + tol` ; **SHORT** רק אם
  ≥ `max(prior_vah, session_high) − tol`. אחרת — החסימה נשארת עם `blocked_by=dalton_intent:location`.
- מחיר-השיפוט: `structural_anchor` אם הוא בתוך `2×tol` מהכניסה (שומר-הרדיפה מ-T-319b), אחרת הכניסה.
- כשעובר: `logger.warning("[Gateway] T-355 PHASE_B location admit: ...")` + `_dp_block=None`.

**2. לא נוגעים בשום שער אחר.** ‏`entry_not_confirmed`, `entry_location_quality`, `rr_entry_gate`,
`stand_down` של שלב A, T-335 — כולם נשארים ונשארים אחרונים. אם משהו מהם חוסם — הוא חוסם.

**3. שלב A (‏16:30–16:45) לא משתנה.** `stand_down` נשאר מוחלט.

## golden (שורות גולמיות בדיווח)
**ד1 · הגולדן הראשי:** 10.09 `17:10:03 CEILING_FLIP_TOUCH2 LONG 7587.5 stop 7585.25` ⇒ עם הדגל דלוק
עובר ל-**ADMIT** (‏`shadow_only=True` — הוא עדיין touch-2 בצל), ‏`blocked_by=None`.
השפל של 10.09 עד אותו רגע הוא 7585.5 ⇒ הכניסה ב-2 נק' מהשפל = קצה אמיתי.

**ד2 · הכיוון הנגדי נחסם:** 11.09 `17:20:03 CEILING_FLIP_TOUCH2 LONG 7675.0` (בקרבת **השיא**, לא
השפל) ⇒ חייב להישאר חסום — עם `blocked_by=dalton_intent:location` (לא `kind`).

**ד3 · אפס שינוי בכתיבות** בכל 5 הסשנים + `--restart-at 18:29`, דגל דלוק **וגם** כבוי:
08-03 `7587.5` · 08-04 `7690.75` · 09-09 `7641.25` · 10.09 **אפס** · 11.09 `7673.25` ·
restart `7671.25`. אם כתיבה כן משתנה — **לעצור ולדווח**, לא לשלוח.

**ד4 · טבלת-מעברים:** כל מסלול ש-`blocked_by` שלו השתנה (‏`kind|bias → None|location`), עם
`il · cls · dir · entry · stop · t1 · phase · אם הוא shadow או live`. אני פוסק מה נכנס ללייב.

**ד5 · דגל כבוי = אפס דלתא** מול `e37bb2cf` (אפס שורות `T-355`, אפס מעבר).

**ד6 · `T-335 LADDER INVALID` = 0** ו-`Traceback` = 0 בכל 6 הריצות.

**ד7 · מבחן:** `backend/v9/tests/test_phase_b_location.py` — LONG בשפל עובר · LONG בשיא נחסם
`location` · שלב C לא נוגע (מוטציה) · דגל כבוי ⇒ החסימה המקורית נשמרת.

## דיווח
קומיט אחד · `TASK_LOG` (T-355) + `STATUS_BOARD` באותו קומיט · LOG חתום עם ד1–ד7 גולמיים ·
ואז **"סיים פריט 4"** ולעצור. **אין ריסטארט** (המתוזמן 15:45), אין `.env`, אין נגיעה בפוזיציות.
