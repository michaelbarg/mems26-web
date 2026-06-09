# CC PROMPT — S2 firing-variant גייט → YAML-tunable (D-RVX) · ברירת-מחדל A_VSA = 0 שינוי-התנהגות · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אישור Michael 2026-06-04 (חשיפת-knob בלבד).
**זו חשיפת בורר-קונפיג — לא שינוי-ערך-trading.** ברירת-המחדל זהה-לחלוטין להתנהגות היום; **בחירת וריאציה אחרת = strategic-stop + אישור Michael לפני live.**

## רקע (ממצא Cowork, code-verified)
ב-`five_min_system.py` שלוש הווריאציות מחושבות **כבר היום בכל בר** (`_vsa_pass`/`_rvol_pass`/`_strict_pass`, `:504-511`) ונרשמות ב-`variants_passed` (מדידה מקבילה — כבר קיים). אבל **השער היורה** קבוע-קוד לוריאציה אחת:
```
:513  if S2_VSA_VOLUME:
:514      b2_drop = _vsa_pass          # ← רק A_VSA יורה. B_RVOL/C_STRICT נמדדות בלבד.
:515  else:
:516      b2_drop = b2_vol <= b1_vol * DROP_THRESHOLD_PCT   # legacy — אל תיגע
```
`b2_drop` מזין את שני תנאי-הירי (LONG `:546`, SHORT `:570`) — מקור-יחיד. pass-rates על 417 חלונות PG: A_VSA 22.1% · B_RVOL 20.9% · C_STRICT 11.0% (`C_STRICT ⊆ A_VSA`).

> **מטרה אחת:** להפוך את בחירת-הווריאציה-היורה ל-YAML, עם 5 ערכים: `A_VSA`(ברירת-מחדל) · `B_RVOL` · `C_STRICT` · `UNION`(OR) · `INTERSECTION`(AND). **ברירת-מחדל A_VSA → `b2_drop` זהה-bit ל-`:514` של היום → 0 שינוי-התנהגות.**

## ⛔ risk surface — מה אסור
- **אל תיגע** בחישוב הווריאציות (`:504-511`), בתנאי-הירי (`:546`/`:570`), ב-legacy else (`:516`), ב-`variants_passed` recording, או בכל ערך-stop/target/risk.
- **רק** את הקצאת `b2_drop` ב-`:513-514` (ענף `S2_VSA_VOLUME`) הופכים לבחירה-מ-קונפיג.
- אל תיגע sc_study/polling/PG-paths.

## Phase 1 — אודיט (diagnose-first, הדבק)
1. הדבק `:499-516` + שני אתרי-השימוש ב-`b2_drop` (`:546`,`:570`). אשר ש-`b2_drop` מקור-יחיד.
2. אתר את `_flag(...)` (נקרא `:632`) ואת תבנית ה-loader ב-`config_loader.py` (`_load_yaml`/`_CONFIG_DIR`/`load_*`) — תשתמש באותה תבנית.
3. אשר ש-`config_loader` ניתן-לייבוא מ-`five_min_system` בלי circular (adaptive_stop כבר מייבא אותו).

## Phase 2 — config + loader
- `config/s2_firing.yaml`:
  ```yaml
  # D-RVX — בורר וריאציית הירי של S2 (Reactive volume gate)
  # ברירת-מחדל A_VSA = ההתנהגות הקיימת. שינוי = strategic-stop + אישור Michael.
  variant: A_VSA   # A_VSA | B_RVOL | C_STRICT | UNION | INTERSECTION
  ```
- `config_loader.load_s2_firing() -> str`: קורא את הקובץ, **schema-validate** שהערך באחד מ-5 המותרים; אחרת → `logger.warning` + fallback `"A_VSA"` (Rule 1, No silent failure). חסר קובץ → `"A_VSA"`.

## Phase 3 — wiring (smallest change)
החלף **רק** את `:513-514` ב-בחירה לפי הקונפיג, מעל אותם 3 דגלים:
```
if S2_VSA_VOLUME:
    _v = load_s2_firing()            # cached; default "A_VSA"
    if   _v == "B_RVOL":        b2_drop = _rvol_pass
    elif _v == "C_STRICT":      b2_drop = _strict_pass
    elif _v == "UNION":         b2_drop = _vsa_pass or _rvol_pass or _strict_pass
    elif _v == "INTERSECTION":  b2_drop = _vsa_pass and _rvol_pass and _strict_pass
    else:                       b2_drop = _vsa_pass      # A_VSA — identical to today
else:
    b2_drop = ...  # legacy — unchanged
```
- שמור `variants_passed` כפי שהוא (כל מי שעבר). את ה-`variant` tag שנרשם בירי — התאם לבורר הפעיל (בורר-יחיד→שמו; UNION/INTERSECTION→הערך), בלי לשבור את ה-recording.
- אם תרצה cache ל-`load_s2_firing` (כמו `_pattern_ticks`) — מותר, עם `reset_cache` לטסט.

## Phase 4 — טסט (anti-tautological, B1)
צור טסט שמייבא את **`FiveMinSystem`** ומריץ את נתיב-הייצור (`_detect_reactive`/`process_bar`) עם בָּרים מתוכננים שבהם `_rvol_pass=True` אך `_vsa_pass=False` (b2 מתחת ל-0.5×avg אך לא מתחת לשני השכנים), כך שהבורר משנה תוצאה:
- `variant=A_VSA` → **לא יורה** (b2_drop=False) · `variant=B_RVOL` או `UNION` → **יורה** · `INTERSECTION` → לא יורה.
- assert על **הפלט האמיתי** (direction/fire מ-`_detect_reactive`), לא על משתנה-ביניים מועתק.
- שורת *"if reverted → RED because ___"*: אם מחזירים `b2_drop=_vsa_pass` קשיח → הבורר מתעלם → המקרה B_RVOL לא יורה → **RED**.
- **טסט 0-שינוי:** עם ברירת-מחדל (אין `s2_firing.yaml` / `variant=A_VSA`), נתיב הירי זהה למצב טרום-השינוי על קלט ש-A_VSA תופס (raw).

## Acceptance (✓/✗ + raw)
- [ ] Phase-1 audit מודבק (`:499-516` + 2 אתרי `b2_drop` + תבנית loader).
- [ ] `config/s2_firing.yaml` + `load_s2_firing()` עם schema-validate (5 ערכים) + fallback `A_VSA` (raw: ערך לא-חוקי → warning + A_VSA).
- [ ] `:513-514` מחווט לבורר; 504-511/546/570/516 לא נגעו (raw: diff).
- [ ] טסט-בורר עובר על נתיב-הייצור + *"if reverted→RED"* + טסט 0-שינוי בברירת-מחדל (raw).
- [ ] regression S2/חמש-דקות ירוק (raw) · `git log -1` · **NOT-DONE/DEVIATIONS** (גם "none").

## Invariants
חשיפת-knob בלבד — **ברירת-מחדל A_VSA = 0 שינוי-התנהגות** · בחירת וריאציה אחרת = trading-logic → **strategic-stop + אישור Michael לפני live** ·
single-source (`b2_drop`) · fallback Rule 1 (לא-חוקי/חסר→A_VSA+warning) · אל תיגע variant-compute/fire-conditions/legacy/sc_study ·
localhost-PG · No silent failures · Cowork מאמת בלתי-תלוי (litmus revert→RED + diff שרק `:513-514` השתנה + 0-שינוי בברירת-מחדל).
