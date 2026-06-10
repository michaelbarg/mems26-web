# CC MEGA — מימוש יעדי‑S4 + פתיחת‑יום + רובריקת‑Detection ב‑Shadow (2026‑06‑10)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` (A: איך נכתב · B: מה חובה · C: תבנית‑דוח · D: אימות‑Cowork).

**מטרה אחת:** להפוך את אפיון‑היעדים של S4 שננעל היום (06‑10) לקוד חי (flag‑gated SHADOW), להכין את היום, ולתת ל‑Michael תצוגת‑detection פר‑תבנית. מחולק ל‑4 phases אטומיים.

---

## מקורות‑אמת (קרא לפני שאתה נוגע בקוד)
- **אפיון נעול 06‑10:** `docs/plans/MEMS26_S4_REVIEW_TABLE_2026-06-10.xlsx` (9 תבניות · כניסה/סטופ/T1/T2/T3) — **קנוני**.
- `config/stop_anchors.yaml` (V2, flag‑gated `STOP_ANCHORS_V2`) · `config/stop_params.yaml` (s4_patterns, ערכי‑היום).
- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` + `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` (Table A) + `STOP_ANCHOR_DECISIONS_DRAFT_2026-06-07.md`.
- `docs/runbooks/PRE_TRADE_PROTOCOL.md` (פתיחת‑יום).
- **CLAUDE.md:** §Standing Decisions · §Chop Gates (DISABLED) · §Frontend Polling Floors · §Service Bring-Up · §Source-of-Truth Discipline · §Roadmap auto-update.

## עקרונות מחייבים (CLAUDE.md + Contract)
- **Diagnose‑first / read‑current‑code / audit‑before‑build.** אל תתקן מהזיכרון.
- **Smallest‑correct‑change.** טסט‑רגרסיה לכל תיקון (B1: anti‑tautological, RED‑on‑revert).
- **שינוי trading‑logic = flag‑gated + single‑source‑of‑truth + strategic‑stop + אישור Michael לפני LIVE.** ה‑FIX כאן נשאר תחת `STOP_ANCHORS_V2` (SHADOW); אל תדליק ב‑LIVE.
- **No silent failures / no silent skips** (B3: סעיף NOT‑DONE חובה) · **Rule 5:** command+raw‑output, לא "✅".

---

## ⛔ אסור לגעת (risk surface)
- אל תֿדליק מחדש את שערי‑ה‑chop (`S2_CHOPPINESS_GATE`/`LAYER0_CHOP_GATE`) ולא את `S2_REQUIRE_COT_AMT` — Standing Decisions, default‑OFF, אישור‑Michael בכתב.
- אל תגדיל אינטרוולי‑polling (§Polling Floors).
- אל תשנה התנהגות default (דגל כבוי = בדיוק כמו היום). `STOP_ANCHORS_V2` נשאר flag‑gated.
- אל תסנתז ערכי‑CCI/study/OHLC — source‑of‑truth (Sierra → גשר → DB).
- אל תיגע ב‑`sc_study/`, bridge, market‑data routes בלי §7a.

---

## PHASE 0 — פתיחת‑יום (T‑30 → T‑0) · diagnose‑only עד שמאשרים feed
**מטרה:** לוודא שהמערכת חיה+מסונכרנת לפני שסומכים על SHADOW. רוץ `docs/runbooks/PRE_TRADE_PROTOCOL.md` Phases 0‑4 והדבק PASS/FAIL גולמי (Rule 5).

חובה לפני התחלת שירותים (CLAUDE.md §Service Bring-Up): בדוק listeners קיימים על `127.0.0.1:3000` ו‑`127.0.0.1:8000` כדי לא להריץ כפול.

**Acceptance (הדבק raw לכל אחד):**
- [ ] `curl -s localhost:8000/health` → `alive:true, mode:shadow` · uvicorn יחיד.
- [ ] `python3 scripts/sot_health.py --strict` → אין 🔴.
- [ ] קבצי‑export ב‑`~/SierraChart_Data/v9_export/` FRESH (<5s): `5min`, `woodies_5min`, footprint, `tpo`, `5min_continuous`, `live_price`.
- [ ] גשר: `streams=N/N`, **0 push errors**, **local‑only** (אין `push FAILED to https://...` — אחרת עצור ושאל את Michael, §Bridge Local-Only).
- [ ] DB: `opening_type ≠ NA` ו‑`day_type ≠ UNKNOWN` בחלון (FIX‑1 כבר committed; ודא restart קלט אותו). שאילתה: `SELECT opening_type, day_type, COUNT(*) FROM v9_day_type_state WHERE date(ts)=CURRENT_DATE GROUP BY 1,2;`
- [ ] S2/S4 יכולים לירות (לא תקועים GRAY/auth‑skip מבאג).

**🚩 STRATEGIC STOP:** אם feed/classification שבור (export stale · day_type=UNKNOWN · bar_count לא עולה) → **אבחן, דווח, ואל תמשיך ל‑fire‑path**. זו הסיבה ש‑Phase 0 ראשון.

---

## PHASE 1 — THE FIX: יעדי‑S4 הנעולים → קוד (trading‑logic · flag‑gated SHADOW)
**מטרה:** להחליף את ה‑placeholder של S4 (T1/T2 בטיקים‑קבועים, בלי T3, day‑type‑blind) באפיון‑06‑10. **סוגר I‑3** (ZLR ב‑A7: target מנוון 1pt → אין `fire_setup`).

> **🔑 היקף Phase 1 (אופציה 1 · אישור Michael 06‑10):** ממש **רק יעדים שניתן לחשב בכניסה** — **T1 לכל 9** (סולם/Measure) + **VEGAS T2** (Measure×1.0). כל יעד שהוא **חציית‑CCI דינמית** (CONT T2/T3 · GHOST T2/T3 · FAMIR/HTLB/HFE T2/T3) → **`None` ביושר** (Rule 1). מוניטור‑חציית‑ה‑CCI = **משימה‑2 נפרדת** (§1.6), **לא** בפרומפט הזה. T1+סטופ נכונים מספיקים כדי לפתוח את A7 ולסגור I‑3.

### 1.0 Diagnose (read‑current‑code, הדבק ממצא)
- אשר את המצב הקיים: כל 9 הדיטקטורים (`backend/v9/systems/woodies/patterns/*.py`) פולטים `targets=[entry±T1_TICKS·tick, entry±T2_TICKS·tick]` (קבוע), בלי T3. רק `htlb.py`+`famir.py` מתייחסים ל‑`t1_ladder_continuation`.
- אשר את נתיב‑היעדים ל‑`fire_setup`/`execution_bridge` (`WoodiesIntent.t2_price/t3_price` קיימים אך הדיטקטור מספק 2 בלבד).

### 1.1 עדכן `config/stop_anchors.yaml` לערכי‑06‑10 (single‑source‑of‑truth)
- `t1_ladder_continuation` (0‑25, R לפי **מרחק כניסה−סטופ**): נשאר 1.0/0.75/0.65/0.5/0.4 · `t1_reversal_multiplier: 0.80` · `t1_floor_points: 3`.
- VEGAS/GHOST `t1_measure_cap`: **VEGAS → 0.75** (היה 0.5) · GHOST → 0.5.
- HFE `t1_ladder_shift: -1` (קיים).
- הוסף ל‑schema/loader שדות‑יעד פר‑תבנית (ראה 1.3) אם נדרש, או החזק אותם בקוד‑הדיטקטור עם מקור‑יחיד.

### 1.2 חווט `t1_ladder_continuation` ל‑**כל 9** (כיום רק HTLB/FAMIR)
- T1 = `ladder(risk)` כאשר `risk = |entry − stop|` בנקודות · REV ×0.8 · HFE מדרגה −1 · רצפה 3 נק' (גוברת על תוצאה קטנה יותר).
- ZLR/TLB/TT/GB100 (CONT) — בלי ×0.8. VEGAS/GHOST — **לא** סולם, אלא Measure (1.3).

### 1.3 T1/T2/T3 פר‑תבנית (האפיון הנעול — מהטבלה)

| תבנית | T1 | T2 | T3 |
|---|---|---|---|
| ZLR (CONT) | סולם 0‑25 | חציית +200 | חציית +100 / trail |
| TLB (CONT) | סולם 0‑25 | סווינג‑CCI הבא (≈±200) | חציית ZL |
| TT (CONT) | סולם 0‑25 | חציית +200 | חציית ZL |
| GB100 (CONT) | סולם 0‑25 | חציית +200 | חציית ZL |
| VEGAS (REV) | **Measure×0.75** | **Measure×1.0** | trail לקיצון‑נגדי |
| GHOST (REV) | Measure×0.5 | חציית ±100 קרוב | חציית ±100 רחוק *(long: −100→+100 · short: +100→−100)* |
| FAMIR (REV) | סולם×0.8 | חציית −100 (צד‑נגדי) | −200 / חציית ZL |
| HTLB (REV) | סולם×0.8 | **חציית ZL** | **חציית +100** |
| HFE (REV) | סולם −1 ×0.8 | חציית −100 | חציית ZL |

- **בטבלה כל "חציית ___" = יעד‑CCI דינמי → ב‑Phase 1 הוא `None`** (אופציה 1). נכתבים רק: **T1 לכל 9** + **VEGAS T2** (Measure×1.0). אל תסנתז מחיר ל‑CCI‑cross.
- VEGAS/GHOST Measure = גובה‑הכוס/ראש‑צוואר ב‑CCI ÷ 25 ≈ נק' MES (Table A). **GHOST: רק T1** (Measure×0.5) נכתב; T2/T3 (חציות ±100) = None.

### 1.4 סטופ (אשר מול `stop_anchors.yaml` + `atr_stop.py`)
- **3 טיק מעבר לקצה‑הבר** (לא עליו): CONT = שפל/גבוה נר‑העוגן · REV = קיצון‑הסווינג/כתף/בר‑כושל/קונסולידציה/בר‑קיצון. ATR = **שער‑גודל** (סטופ מבני תמיד גובר; ATR לא מזיז לתוך הנר). רצפה 4T.

### 1.5 הזרם stop+T1 (+VEGAS T2) ל‑`fire_setup` (סוגר I‑3)
- ודא ש‑`fire_setup` נבנה כאשר R:R≥1 (לפי T1) ו‑tier≥MEDIUM (לא נחסם ב‑A7 מ‑target מנוון). T2/T3=None לא חוסם ירי.

### 1.6 (משימה‑2 · נדחית — **לא בפרומפט הזה**) מוניטור‑חציית‑CCI ליציאות T2/T3
- **אל תממש כאן.** תוספת מוכלת בנתיב‑Woodies הפר‑בר: `b11_t2_milestone`/`b12_t3_milestone` מקבלים `cci`+`threshold` ובודקים "האם CCI חצה +200/±100/ZL בבר הזה" → יציאה במחיר‑הבר. Woodies כבר רואה CCI פר‑בר → **לא** rebuild של ה‑trade‑manager הגנרי (שמשווה מחיר בלבד — אומת ב‑`b11/b12`). כשייבנה, יחליף את ה‑None‑ים של Phase 1.
- רשום ב‑NOT‑DONE שזה **נדחה בכוונה** (אופציה 1).

### Acceptance + טסטים (B1 · RED‑on‑revert · ציין "if reverted → RED because ___")
- `test_zlr_t1_uses_risk_ladder` — ZLR T1 = ladder(risk), **לא** 12T קבוע. *(revert→RED: חוזר ל‑12T)*
- `test_vegas_t1_measure_075_t2_10` — VEGAS T1=Measure×0.75, T2=Measure×1.0.
- `test_ghost_t1_measure_05` — GHOST T1=Measure×0.5; **T2/T3=None** (אופציה 1).
- `test_hfe_ladder_shift_floor` (רצפת‑3 גוברת).
- `test_cci_cross_targets_are_none` — ZLR/TT/GB100/FAMIR/HTLB/HFE: **T2/T3=None** (יעדי‑CCI נדחו ל‑§1.6). *(revert→RED: אם מישהו מסנתז מחיר ל‑CCI‑cross)*
- `test_s4_fire_setup_routable` — מקרה R:R≥1 → `fire_setup.ready_to_route=True` (סוגר I‑3). *(revert→RED: target מנוון חוסם)*
- כל הטסטים **מייבאים וקוראים לקוד‑הייצור** (`<pattern>.detect` / `WoodiesSystem.process_bar` / fire path) — לא משכפלים לוגיקה.
- **Rule 5:** הדבק pytest output + **ירי‑SHADOW אחד** ב‑`v9_trades` עם **stop+T1 מהאפיון** (לא טיקים‑קבועים; VEGAS גם T2; שאר T2/T3=None לפי אופציה 1). SQL: `SELECT pattern_name, entry, stop_price, t1, t2, t3 FROM v9_trades ORDER BY ts DESC LIMIT 1;`

---

## PHASE 2 — רובריקת‑Detection ב‑Shadow (S1/S2/S4 · אחוזי‑בנייה) · additive, observability‑only
**מטרה (בקשת‑Michael · מחודד 06‑10):** בטאב **Shadow**, פר S1·S2·S4, להציג לכל תבנית את **הנוסחה שלה** — מה היא **מחפשת** (הצורך) מול **מה קורה בפועל עכשיו** — בצורה **ברורה, הגיונית וקלה‑להבנה**: רואים מיד "מה עוד צריך לקרות כדי שתירה". **לא דאמפ של כל הפרמטרים — רק 3‑5 התנאים המהותיים** שמגדירים את התבנית. אחוז‑הבנייה נגזר מ‑needed‑מול‑actual. **זה הדגש המרכזי.**

> ⚠️ observability בלבד — **לא fire‑path** ולא trading‑logic. Rule 1: הצג את התנאים האמיתיים מהקוד, אל תמציא.

### 2.1 Backend (additive)
- הרחב `GET /api/v9/build/pattern-status` → לכל `systems[].patterns[]` הוסף **`formula[]`** — **רק התנאים המהותיים** (3‑5, לא כל פרמטר), כל אחד מנוסח **needed‑מול‑actual** וקריא‑לאדם:
  - `{ label, needed, actual, met }` — `label`=מה מחפשים במילים פשוטות · `needed`=הסף/התנאי · `actual`=הערך‑החי עכשיו · `met`=bool.
  - המקור = הקוד האמיתי של הדיטקטור (S4 `patterns/*.py` · S2 `five_min.detect` · S1 `state_machine`). ערך לא‑זמין → `actual=null, met=false` (ביושר).
  - `build_pct` = `met/total` מהתנאים המהותיים בלבד.
  - `tier` (FIX 6) מ‑Auth Table פר `pattern × day_type`; `UNKNOWN` → `tier="—"`.
- **דוגמה ZLR** (אשר מול הקוד · 4 תנאים מהותיים, **לא** כל הפרמטרים):

  | label | needed | actual | met |
  |---|---|---|---|
  | מגמת Stage‑1 | trend ∈ BLUE/RED | BLUE | ✓ |
  | פולבק מתחת +100 | CCI < +100 | +40 | ✓ |
  | לא חצה −100 | CCI > −100 | +20 | ✓ |
  | נר דחיית קו‑אפס | CCI מתהפך מעלה | עוד לא | ✗ |

  → **build_pct = 75%** · "חסר רק נר‑הדחייה כדי לירות".

### 2.2 Frontend (`useBuildStatus` · §Polling Floors — אל תגדיל אינטרוולים)
- כרטיס פר **S1·S2·S4** → שורת‑תבנית: שם · **בר‑אחוז‑בנייה** · ומתחת **רשימת‑formula קצרה** (needed‑מול‑actual, ✓/✗) — מיידי וברור "מה חסר כדי לירות". **בלי טבלאות‑פרמטרים ארוכות.** tier ליד. סגנון עקבי עם הרצועה (FIRING/OBSERVING).

### 2.3 Acceptance
- Michael רואה פר S1/S2/S4 כל תבנית עם **build %** + **רק הנוסחה המהותית** (needed‑מול‑actual) — ברור "מה עוד צריך לקרות", בלי דאמפ‑פרמטרים. מתעדכן חי.
- `day_type=UNKNOWN` → pending ביושר (אין % מזויף).
- **Rule 5:** הדבק JSON של `pattern-status` (תבנית אחת עם `formula[]`+`build_pct`) + צילום/טקסט של הכרטיס החי.

---

## PHASE 3 — עדכון הדאשבורד/רוד‑מאפ (חובה · CLAUDE.md §Roadmap auto-update)
**אחרי כל phase, ולפני "done", עדכן את שני הקבצים — אחרת הם משקרים מול המציאות:**

1. **`docs/plans/ROADMAP_TO_LIVE.html`** — (א) סמן פריטים שהושלמו עם `data-done="1"`. (ב) הוסף פריטים שצצו לסקשן הנכון (blockers / SHADOW / Pipeline). (ג) רענן את מרקר **"📍 אתה כאן"** + את שורת **"עודכן <b>YYYY‑MM‑DD</b>"** בכותרת.
2. **`docs/plans/STATUS_BOARD.md`** — הוסף רשומה מתוארכת בראש, בתבנית **finding → fix → verification** (לא רק "done"). שורה לדוגמה: `[2026‑06‑10] S4 targets: root=placeholder fixed‑ticks (I‑3) → fixed (ladder 0‑25 + CCI‑cross + measure, flag‑gated) → verified: pytest X/X + SHADOW fire עם stop/T1/T2/T3 מהטבלה`. פריטים שנדחו נשארים OPEN עם הפתרון‑המוצע.

> זהו "עדכון הדאשבורד" שעליו דיברנו — שני הקבצים יחד: ה‑HTML הוא תצוגת‑העל, STATUS_BOARD הוא מקור‑הרשומה.

---

## דוח חובה (CC_HANDOFF_CONTRACT §C)
קובץ: `docs/reports/MEGA_S4_TARGETS_2026-06-10.txt`.
1. **טבלת phases:** `Phase · Status (DONE/PARTIAL/NOT-DONE) · Evidence (command+output) · Deviation/why`.
2. לכל טסט: שורת *"if reverted → RED because ___"*.
3. סעיף **NOT DONE / DEVIATIONS** (גם אם ריק — "none").
4. **Open / מה נשאר.**
- **Commit** (ענף `stabilize/mems26-local-truth-2026-05-16` ahead — **Michael ידחוף**, Cowork חסום מ‑push).

## מה Cowork יאמת בחזרה (Rule 5)
- Phase 0: raw של health+sot_health+freshness+`day_type≠UNKNOWN`.
- Phase 1: **RED‑on‑revert** של `test_zlr_t1_uses_risk_ladder` + `test_s4_fire_setup_routable`; ו‑SHADOW‑fire אחד עם stop/T1/T2/T3 **מהטבלה** ב‑`v9_trades`.
- Phase 2: JSON של `pattern-status` עם `formula[]` (needed‑מול‑actual, רק תנאים מהותיים) + `build_pct` לתבנית אחת.
- אל תכריז "done" בלי אלה.
