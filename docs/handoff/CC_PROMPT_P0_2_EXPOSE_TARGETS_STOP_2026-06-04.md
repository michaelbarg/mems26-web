# CC PROMPT — P0-2: חשיפת TARGETS/STOP → r_t1 (גייט אמיתי ל-build-status + הזנת stop/r_t1) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** אישור Michael 2026-06-04 (הבא בתור). מבוסס על `docs/plans/BUILD_STATUS_COMPONENT_AUDIT.md` (פערי P0).
**זו חשיפה (exposure) בלבד — לא שינוי ערכי-trading.** מציגים מה שהמנוע **כבר מחשב**, באותו חישוב כמו הגייט החי. שינוי ערך stop/target = strategic-stop נפרד.

## הבעיה (מהאודיט + ה-S2 firing)
שלב **TARGETS/STOP חסר מה-Build-Status** ל-S2/S4. כתוצאה, ה-inspector מציג שער בעזרת **פרוקסי `confidence≥0.5`**,
בעוד המנוע החי מחליט לפי **`r_t1 ≥ min_r_t1_threshold`** + `pre_fire_validator` (R:R≥1.0). הפרוקסי עלול לסתור את המציאות (ירוק-שקרי).
חשיפת ה-1R/r_t1 סוגרת 3 דברים: (א) גייט אמיתי בתצוגה · (ב) stop/r_t1 אמיתי זמין לכל הצרכנים · (ג) בסיס ל-stop-anchor.

## שלב 1 — אודיט (diagnose-first)
- היכן המנוע מחשב stop/targets: S2 `five_min/adaptive_stop.py` (`compute_stop` → structural_anchor/ATR-cap/floor) + `targets_table.get_targets`; S4 woodies stop שכבתי (`primary 3 ticks`/ATR-cap×group/floor) + r_t1.
- **שאלה מרכזית:** האם המנוע מחשב stop/r_t1 **prospective** לתבנית **armed-שלא-ירתה**, או רק ב-fire-time? הדבק את הממצא.
  - אם רק ב-fire-time → הוסף **מתודת preview read-only** שמחשבת את אותו stop/r_t1 ע"י **קריאה לאותו `compute_stop`/targets** (לא reimplement, לא synth) עבור תבנית armed במחיר הנוכחי.

## שלב 2 — חשיפה דרך inspector + endpoint
חשוף ל-`s2_inspector`/`woodies_inspector` → `/api/v9/build/pattern-status` שלב **TARGETS/STOP** פר-תבנית armed:
- S2: `stop_price`, `risk_1R`, `t1/t2/t3_price`, `r_t1`, `time_stop`, `sizing` (full/half/reject), VSA `variant_tag`.
- S4: `stop_price` (שכבתי), `atr_14_ticks`, `r_t1`, `t1/t2` (ticks לפי תבנית), `entry_price`, + **Day-Type Matrix verdict** (✅/⚠️/❌ לתבנית×יום).
- **source-of-truth:** רק מה שהמנוע מחשב; אם חסר → "ממתין ל-backend", לא לסנתז.

## שלב 3 — החלפת הפרוקסי בגייט אמיתי
ב-`s2_inspector` (וב-`woodies_inspector` אם רלוונטי): החלף `confidence≥0.5` ב-**`r_t1 ≥ min_r_t1_threshold`** (+ `pre_fire R:R≥1.0`).
היכן שה-r_t1 עדיין לא זמין לתבנית מסוימת → "ממתין", לא פרוקסי.

## Acceptance (✓/✗ + raw)
- [ ] אודיט prospective-vs-fire-time מודבק; אם נוספה preview — היא קוראת ל-`compute_stop` הקיים (0 reimplement/synth).
- [ ] `/api/v9/build/pattern-status` מחזיר stop/1R/t1-t3/r_t1/time_stop/sizing ל-S2+S4 (raw JSON).
- [ ] גייט S2/S4 בתצוגה = `r_t1≥threshold` אמיתי (לא confidence); חסר → "ממתין".
- [ ] **אימות-עקביות:** ל-setup/עסקה שנורתה — ה-stop/r_t1 שמוצג == מה שהמנוע השתמש בו בפועל (raw, אותו ערך).
- [ ] **0 שינוי בערכי stop/target** (חשיפה בלבד). regression ירוק · commit · `git log` · NOT-DONE.

## Invariants
exposure-only — **אל תשנה לוגיקת stop/target/risk** (שינוי-ערך = strategic-stop) · אל תיגע sc_study · source-of-truth (חסר="ממתין") ·
localhost-PG · No silent failures · Cowork מאמת בלתי-תלוי (בדגש: ה-stop המוצג == ה-stop החי; אין reimplement/synth).
