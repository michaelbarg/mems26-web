# CC ROUND‑3 — בדיקה‑עצמית חד‑משמעית + השלמת B/C/D (2026‑06‑10)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. סבב‑3 אחרי אימות‑Cowork לסבב‑2.

## הקשר — מה אומת ע"י Cowork (raw) על סבב‑2
- ✅ **FIX A תקין** — proxy נמחק, `measure_pts` אמיתי מהגאומטריה. אל תיגע בזה.
- 🟡 **FIX B — הטסטים ירוקים אבל לא בודקים כלום (proven):**
  - `detect_ghost(_make_ghost_bars()) → detected=False` → ה‑assert ב‑`test_ghost_measure_pts_in_details` (מאחורי `if result.detected`) **לעולם לא רץ**. ירוק‑ריק.
  - `test_s4_fire_setup_routable` עושה assert **רק** על `ws._bar_buffer` — לא על `fire_setup`. לא מוכיח I‑3, לא red‑on‑revert.
  - VEGAS measure נבדק רק כ‑YAML, לא דרך קוד‑הירי.
- 🔴 **FIX C (formula/build%) ו‑FIX D (דוח) — לא בוצעו, ולא הוצהרו** (הפרת B3 — דילוג שקט).

---

## 🔬 פרוטוקול בדיקה‑עצמית — חד‑משמעי, אסור שיתפרש לשני פנים (THE KEY)
לכל טסט‑התנהגות שתכתוב, **שלושת הכללים האלה הם חובה. טסט שלא עומד בכולם = פסול:**

1. **שער אנטי‑ריק (חובה):** הטסט מתחיל ב‑`assert <trigger> is True` **לפני** כל assert אחר — `assert result.detected is True` (לדיטקטור) או `assert fire_setup is not None` (לנתיב‑הירי). כך אם הקלט לא הפעיל את התבנית → **הטסט נכשל (FAIL), לא מדלג**. אסור `if result.detected:` שעוטף את ה‑assert.
2. **assert על הצרכן האמיתי:** ה‑assert הסופי על הפלט שצורכים בפועל — `fire_setup["t1_price"] == entry ± cap*measure` · `fire_setup.ready_to_route is True` — **לא** על שלב‑ביניים (`bar_buffer`, ספירת‑ברים).
3. **הוכחת RED‑on‑revert (חובה — להדביק):** לכל טסט‑התנהגות, **בצע בפועל**: (א) revert את תיקון‑הייצור (שורה אחת), (ב) הרץ pytest → **הדבק את שורת ה‑FAIL**, (ג) restore, (ד) הרץ שוב → green. בלי הדבקת ה‑FAIL הגולמי — הטסט **לא נחשב**.

> מבחן‑הליטמוס היחיד: *"אם אהפוך את התיקון והטסט עדיין ירוק — הטסט פסול."* הוכח שכל אחד הופך אדום. "ירוק" לבד = נדחה.

---

## FIX B — תקן את הטסטים שיהיו אמיתיים
1. **`test_ghost_measure_…`** — תקן את `_make_ghost_bars` כך שהוא **באמת מפעיל GHOST** (`detect_ghost(bars).detected is True` — בדוק זאת ב‑probe לפני), והוסף `assert result.detected is True` כשורה ראשונה. ואז assert ש‑`measure_pts` = הגאומטריה הצפויה, ושב‑fire‑path `t1 == entry ± 0.5*measure`.
2. **`test_vegas_t1_t2_via_fire_path`** (חדש) — בָּרים שמפעילים VEGAS, `assert detected`, ואז `t1 == entry±0.75*measure`, `t2 == entry±1.0*measure` (מתוך ה‑`fire_setup`, לא YAML).
3. **`test_s4_fire_setup_routable`** — assert אמיתי: `fire_setup is not None` **וגם** `ready_to_route is True` (R:R≥1). הסר את ה‑assert על `_bar_buffer`.
4. שמור את 3 טסטי‑הסולם + `test_no_measure_proxy…` (תקינים).
5. **הדבק לכל אחד** (B-real ו‑I‑3): pytest -v + הוכחת RED‑on‑revert (פרוטוקול §3).

---

## FIX C — Phase 2: רובריקת‑detection (formula needed‑מול‑actual + build%)
ממש לפי `CC_MEGA_S4_TARGETS_DAYOPEN_DASHBOARD_2026-06-10.md §2` (לא בוצע בסבב‑2, grep=0):
- **Backend additive:** `pattern-status` → `patterns[].formula[]` = 3‑5 תנאים מהותיים `{label, needed, actual, met}` מהקוד האמיתי + `build_pct=met/total`.
- **Frontend** (`PatternsTab`/Shadow · §Polling Floors): שורת‑תבנית עם build% + ה‑formula (needed‑מול‑actual). observability בלבד.
- **ראיה:** JSON של תבנית אחת עם `formula[]`+`build_pct`.

---

## FIX D — דוח‑חובה + הצהרה (אסור דילוג שקט)
- כתוב `docs/reports/MEGA_S4_TARGETS_2026-06-10.txt` (Contract §C): טבלת‑phases · "if reverted → RED" + **הדבקת ה‑FAIL בפועל** לכל טסט‑התנהגות · **סעיף NOT‑DONE** (כולל: §1.6 CCI‑monitor נדחה בכוונה · וכל דבר שלא הושלם).
- **ראיית‑ירי חיה:** ירי‑SHADOW אחד ב‑`v9_trades` עם stop+T1(+VEGAS T2). **אם RTH סגור → אמור זאת מפורשות ב‑NOT‑DONE** (לגיטימי לדחות), **אל תגיש replay כ"ראיה".**

---

## ⛔ אסור לגעת
FIX A התקין · T1‑סולם · CCI‑cross=None · Standing Decisions · §Polling Floors · default‑behavior (`STOP_ANCHORS_V2` flag‑gated) · אל תסנתז CCI/OHLC.

## מה Cowork יאמת בחזרה (Rule 5)
1. אריץ בעצמי `detect_ghost(_make_ghost_bars()) → detected` — **חייב True** (אחרת הטסט עדיין ריק).
2. אהפוך בעצמי את תיקון‑הירי ואריץ `test_s4_fire_setup_routable` — **חייב FAIL** (אחרת הוא לא מאמת I‑3).
3. `grep formula|build_pct` — **חייב >0** (FIX C).
4. דוח `MEGA_S4_TARGETS` קיים עם NOT‑DONE + הדבקות‑FAIL.
**אל תכריז "done" בלי שכל 4 עוברים אצלי.** (ענף ahead — Michael ידחוף.)
