# CC PROMPT — תיקון רגרסיית PG: datetime↔str ב-DataFreshness (day_type_inspector קורס → day_type=None) · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** באג חי שנתפס ב-Build-Status (RTH 2026-06-04). **bugfix read-path בלבד — אפס שינוי trading/risk.**

## הבאג (אומת ע"י Cowork, code-level)
ב-RTH ה-Build-Status הראה `warnings: day_type_inspector failed: 1 validation error for DataFreshness last_bar_ts Input should be a valid string [input_value=datetime.datetime(2026,6,...tzinfo=...)]` → `day_type=None`.
שורש: `day_type_inspector.py:102` `last_updated = r.get("last_updated_at")`. תחת **Postgres** עמודת timestamp חוזרת כ-`datetime` (תחת SQLite חזרה כ-`str`). מועבר ל-`DataFreshness(last_bar_ts=last_updated)` (`:326`), ו-`DataFreshness.last_bar_ts` מוגדר **`Optional[str]`** (`types.py:48`) → pydantic נכשל → ה-inspector קורס → `day_type=None` → **S1 לא מסווג → שער-יום של S2/S4 נופל.** זו רגרסיה מהמעבר SQLite→PG (`project-postgres-migration`).

## ⛔ risk surface
read-path/display בלבד. אל תיגע בלוגיקת-classification/risk/stop/target/sc_study. שמור localhost-PG.

## Phase 1 — אודיט שורש + **סריקת-אחים** (diagnose-first; זה העיקר — אל תתקן רק שורה אחת)
1. אשר `types.py:48` `last_bar_ts: Optional[str]` + `day_type_inspector.py:102,326`.
2. **סרוק את כל נתיבי-הקריאה שמזינים שדה-str של pydantic בערך שמקורו ב-DB read** — לא רק DataFreshness. חפש דפוסים: `r.get("...ts")`/`...at"`/`MAX(ts)` שמוזנים ל-מודל עם שדה `str`. בדוק את כל ה-inspectors (`s2/woodies/bridge/footprint/day_type`) + כל מקום שבונה `DataFreshness`/שדות-ts אחרים. **הדבק את הרשימה** (מי כבר עושה `.isoformat()` ומי לא).
3. הכרע: תיקון-נקודתי בכל אתר מול **coercion מרכזי** (מומלץ — Pydantic `field_validator` על `DataFreshness.last_bar_ts` שממיר `datetime→.isoformat()`, או helper `_as_iso(x)` משותף). מרכזי מונע חזרה של הבאג בנתיבים עתידיים.

## Phase 2 — תיקון (smallest correct, single-source)
- מומלץ: `field_validator("last_bar_ts", mode="before")` ב-`DataFreshness` שמחזיר `x.isoformat() if isinstance(x, datetime) else x`. כך כל הצרכנים מוגנים.
- החל את אותו עיקרון על כל שדה-str אחר שהאודיט מצא שמקבל datetime מ-PG.
- **No silent failure:** אם המרה נכשלת — `logger.warning`, לא בליעה.

## Phase 3 — regression test (B1, anti-tautological)
- טסט שמזין ל-`DataFreshness` (או ל-`day_type_inspector` בנתיב-הייצור) `last_updated` כ-**`datetime` timezone-aware** (כמו PG) → מאמת שלא נזרק validation error ושהפלט הוא ISO-string. *"if reverted (coercion מוסר) → RED because pydantic ידחה datetime."*
- assert על הפלט האמיתי (ה-`DataFreshness` שנבנה / תגובת ה-endpoint), לא על העתק.
- (אם בר-ביצוע) טסט שמריץ את `day_type_inspector` עם row שכולל `last_updated_at=datetime(...)` → `day_type` לא None בגלל הקריסה.

## Acceptance (✓/✗ + raw)
- [ ] Phase-1: רשימת כל האתרים datetime→str-field (raw grep) + הכרעת מרכזי/נקודתי.
- [ ] תיקון מוחל; `git diff` מצורף.
- [ ] regression test עם datetime-input עובר + litmus revert→RED (raw).
- [ ] הרצת `/api/v9/build/pattern-status` (או fixture) — `day_type_inspector` לא ב-warnings, `day_type` נפלט (raw). *(אם הגשר/דאטה למטה — לפחות אין יותר validation-error; ציין זאת.)*
- [ ] regression מלא ירוק · `git log -1` · עדכון `STATUS_BOARD.md` (root=PG datetime↔str · fix · verification) · **NOT-DONE/DEVIATIONS**.

## הערה — לא חלק מהבאג הזה
ה-Build-Status OFFLINE כי **הגשר למטה / אין דאטה** (run=off, 8 streams no_data) — נושא נפרד (bring-up שירותים+feed ב-Mac, `/tmp/bridge.err.log`). תיקון זה מתקן את `day_type=None` אך **לא** מעלה את הגשר.

## Invariants
read-path bugfix · single-source coercion · No silent failure · אל תיגע classification/risk/sc_study · localhost-PG ·
Cowork מאמת בלתי-תלוי (litmus revert→RED + סריקת-אחים מלאה, לא תיקון-שורה-בודדת).
