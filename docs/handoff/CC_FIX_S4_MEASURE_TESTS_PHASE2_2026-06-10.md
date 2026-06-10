# CC FIX — S4 measure אמיתי + טסטים אנטי‑תאוטולוגיים + Phase 2 + דוח (2026‑06‑10, סבב‑תיקון)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. זהו **סבב‑תיקון** ל‑`6c58d05` (PHASE1) אחרי אימות‑Cowork. הקוד הקיים נכון בחלקו — **אל תשכתב מה שתקין**, תקן רק את 4 הפריטים.

## מה אומת ע"י Cowork (raw) — ההקשר
על `6c58d05`: T1‑סולם ל‑CONT/FAMIR/HTLB/HFE **תקין** (קורא `SA.t1_price`), CCI‑cross=None **תקין**, שריד‑option‑A הוסר. **אבל 4 בעיות:**

---

## FIX A 🔴 — measure אמיתי ל‑VEGAS/GHOST (הפרת Rule 1)
**שורש (אומת):** הדיטקטורים לא חושפים `measure_pts` ב‑`details` → ב‑`woodies_system.py` ה‑proxy `_measure = _s4_risk * 2` (VEGAS) / `* 1.5` (GHOST) **תמיד פעיל** → ה‑measure מסונתז מהסיכון, לא מגאומטריית‑התבנית. זה בדיוק ה‑synthesize‑instead‑of‑None שאסור (CLAUDE.md §Source‑of‑Truth Rule 1). חומר‑הגלם **קיים** בדיטקטורים.

1. **`ghost.py`** — בכל ענף‑fire (4): חשב והוסף ל‑`details`:
   `measure_pts = abs(head_cci − neckline_cci) / 25.0` — `head` = הפסגה/שקע האמצעי (כבר אצלך, `p2[1]`/`t2[1]`); `neckline` = ערך‑ה‑CCI של השקע/פסגה שבין הכתפיים (כבר נמצא ב‑`_find_extremes` — קח אותו). `÷25` = CCI→נק' MES (Table A).
2. **`vegas.py`** — בכל ענף‑fire: `measure_pts = abs(cup_bottom_cci − cup_rim_cci) / 25.0` — עומק‑הכוס מה‑swings שאתה כבר מוצא (קרקעית ≤−200 מול שפת‑הכוס ≥−100). הוסף ל‑`details`.
3. **`woodies_system.py`** — **מחק את ה‑proxy** (`_s4_risk * 2` / `* 1.5`). קרא `_measure = best.details.get("measure_pts")`. אם `None` → **VEGAS/GHOST T1=None ו‑VEGAS T2=None** (ביושר, Rule 1) — אל תסנתז. (T1‑סולם של שאר התבניות לא מושפע.)

**Acceptance A:** `grep -n "risk \* 2\|risk \* 1.5\|_s4_risk \* " backend/v9/systems/woodies/woodies_system.py` → **0 התאמות**. `measure_pts` קיים ב‑`details` של VEGAS+GHOST (raw).

---

## FIX B 🔴 — טסטים שקוראים לקוד‑הירי (הפרת B1), לא ערכי‑YAML
**שורש (אומת):** `test_vegas_t1_measure_075`/`test_ghost_t1_measure_05`/`test_vegas_has_t2_measure`/`test_cci_cross_targets_are_none` בודקים רק `cfg["anchors"][...]` — עוברים גם עם ה‑measure המזויף. והטסט הנדרש `test_s4_fire_setup_routable` **חסר**.

1. **החלף** את טסטי‑ה‑YAML בטסטים שמריצים את **קוד‑הירי האמיתי**: בנה רצף‑ברים סינתטי שמייצר GHOST/VEGAS עם **measure ידוע** (למשל head=+200, neckline=+50 → measure=150/25=6 נק'), הרץ דרך `WoodiesSystem.process_bar` (או detect→target‑calc), ו‑assert על ה‑`fire_setup` שיצא: VEGAS `t1 == entry±0.75*measure`, `t2 == entry±1.0*measure`; GHOST `t1 == entry±0.5*measure`, `t2/t3 == None`.
   - *if reverted → RED because:* עם ה‑proxy (`risk×k`) ה‑T1 לא ישווה ל‑measure האמיתי.
2. **הוסף `test_s4_fire_setup_routable`** — setup עם R:R≥1 → `fire_setup` נבנה (`ready_to_route=True`). *(revert→RED: target מנוון 1pt חוסם — I‑3.)*
3. **שמור** את 3 טסטי‑הסולם הקיימים (`test_zlr_t1_uses_risk_ladder`, `test_famir_htlb_reversal_mult`, `test_hfe_ladder_shift_floor`) — הם תקינים (קוראים `SA.t1_price`).

**Acceptance B:** הדבק `pytest tests/v9/regression/test_s4_targets_spec.py -v` raw (כל הטסטים עוברים) + **הוכח RED‑on‑revert** על טסט‑ה‑measure ועל `test_s4_fire_setup_routable` (revert → הדבק את ה‑FAIL → restore).

---

## FIX C 🟡 — השלם Phase 2 כפי שהוגדר (formula needed‑מול‑actual + build%)
**שורש (אומת):** `grep formula|build_pct|needed|actual` → **0** ב‑backend וב‑`PatternsTab.tsx`. ה‑DetectionPanel הוחזר (revert), והנוסחה needed‑מול‑actual לא קיימת. מימשת תצוגת‑detection אחרת — **לא** מה שביקש Michael.

ממש לפי **§2 בפרומפט המקורי** (`CC_MEGA_S4_TARGETS_DAYOPEN_DASHBOARD_2026-06-10.md`):
- **Backend (additive):** `GET /api/v9/build/pattern-status` → לכל `patterns[]` הוסף `formula[]` = **3‑5 התנאים המהותיים בלבד**, כל אחד `{label, needed, actual, met}` מהקוד האמיתי של הדיטקטור (לא דאמפ‑פרמטרים), + `build_pct = met/total`. ערך לא‑זמין → `actual=null, met=false`.
- **Frontend (`PatternsTab`/Shadow · §Polling Floors):** פר S1/S2/S4 — שורת‑תבנית: שם · בר‑build% · רשימת‑formula קצרה (needed‑מול‑actual, ✓/✗) — "מה חסר כדי לירות". בלי טבלאות‑פרמטרים.
- **observability בלבד** — לא fire‑path.

**Acceptance C:** הדבק JSON של `pattern-status` עם `formula[]`+`build_pct` לתבנית אחת + צילום/טקסט של הכרטיס.

---

## FIX D 🟡 — דוח‑חובה + ראיה אמיתית
**שורש (אומת):** אין `docs/reports/MEGA_S4_TARGETS_2026-06-10.txt`. `SIMULATION_2026-06-09.txt` הוא replay סינתטי — **לא** ראיית‑ירי חיה.

- כתוב `docs/reports/MEGA_S4_TARGETS_2026-06-10.txt` (CC_HANDOFF_CONTRACT §C): טבלת‑phases (DONE/PARTIAL/NOT‑DONE + evidence) · כל טסט עם "if reverted → RED because ___" · **סעיף NOT‑DONE** (כולל: מוניטור‑חציית‑CCI §1.6 **נדחה בכוונה** · ATR=size‑gate אם לא אומת) · Open.
- **ראיה (Rule 5):** pytest raw + **ירי‑SHADOW חי אחד** ב‑`v9_trades` עם stop+T1 (+VEGAS T2) מהאפיון. **אם RTH סגור → אמור זאת מפורשות** ב‑NOT‑DONE; אל תגיש replay סינתטי כ"ראיה".

---

## ⛔ אסור לגעת (כמו קודם)
Standing Decisions (chop/COT‑AMT) · §Polling Floors · התנהגות default (`STOP_ANCHORS_V2` flag‑gated) · אל תסנתז CCI/study/OHLC · `sc_study/`/bridge ללא §7a. **אל תשכתב את T1‑הסולם התקין ולא את CCI‑cross=None.**

## מה Cowork יאמת בחזרה (Rule 5)
1. FIX A: `grep` ל‑proxy = 0 + `measure_pts` ב‑details (raw).
2. FIX B: pytest raw + **RED‑on‑revert** של טסט‑measure ו‑`test_s4_fire_setup_routable`.
3. FIX C: JSON עם `formula[]`+`build_pct`.
4. FIX D: דוח קיים עם NOT‑DONE + ראיה חיה (או הצהרת RTH‑סגור).
**אל תכריז "done" בלי אלה.** (ענף ahead 56 — Michael ידחוף.)
