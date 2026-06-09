# CC — סגירת מצב-יחסי (live) + אבחון-שורש I-21 (5-min/study stall) · 2026-06-05 night

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`** (anti-tautological tests · Rule 5: command+raw output · NOT-DONE חובה · smallest-correct-change). וגם `CC_VERIFICATION_PROTOCOL.md`.

**מטרה אחת:** לסגור סופית את הדלקת-המצב-היחסי (`a607d11`) — לאמת שהיא **חיה** (לא רק committed) — ולהפיק `VERIFY_RELATIVE_2026-06-05.md`. בנוסף, phase אבחון-בלבד (read-only) לשורש I-21. **אין שינוי trading-logic בפרומפט הזה** מעבר למה שכבר ב-`a607d11`.

**רקע (אומת ע"י Cowork מול הקוד):** `a607d11` נכון ותואם את הסיכום — flag default=True, `start_all.sh` export, `double_bt` קורא `get_trough_tolerance(atr_5m)`, call-sites ב-`five_min_system.py:881,883` מעבירים `self._current_atr_5m` (אין dead-wiring). **אבל CC דילג על אימות:** (א) שבר טסט קיים, (ב) לא הפיק VERIFY, (ג) השינוי לא חי בלי restart.

**Cowork כבר תיקן בעץ-העבודה (uncommitted) — אל תחזיר אחורה, רק הרץ+commit:**
- `tests/v9/test_atr.py` — `test_flags_default_off` שבר (assert `S2_ATR_RELATIVE is False`) → שונה ל-`test_flag_defaults` (assert `True` ל-S2, השאר `False`).
- `tests/v9/regression/test_double_bt_relative.py` (חדש) — מכסה `get_trough_tolerance`.

---

## Phase 1 · אמת שהמצב-היחסי **חי** בשרת הרץ (לא רק בקוד)
מה שאסור לגעת: `atr.py:86,101`, `start_all.sh:33`, `double_bt.py`, `five_min_system.py:881,883` — הם נכונים ב-`a607d11`. רק לאמת+להפעיל.

**1a.** **Michael אישר restart של ה-SHADOW backend** כדי שה-`default=True`/`export=1` ייכנסו לתוקף (process רץ לא קולט קוד חדש בלי restart). לפני הפעלה — בדוק listeners קיימים על `127.0.0.1:8000`/`:3000` (CLAUDE.md §Service Bring-Up) כדי לא ליצור כפילות.

**1b.** **Acceptance (בינארי) + פקודות אימות:**
- ✓/✗ ה-process הרץ נושא את ה-env: `ps eww <backend_pid> | tr ' ' '\n' | grep S2_ATR_RELATIVE` → `S2_ATR_RELATIVE=1`.
- ✓/✗ ייבוא טרי תחת env של `start_all.sh` מחזיר True:
  `S2_ATR_RELATIVE=1 python3 -c "from backend.v9.shared.atr import S2_ATR_RELATIVE; print(S2_ATR_RELATIVE)"` → `True`.
- ✓/✗ ה-tolerance בפועל **ATR-יחסי, לא 0.50**: הדבק `get_trough_tolerance(<ATR-5m נוכחי>)` מול ATR חי (אם ATR≈3 → ~2.25, לא 0.50). אם אין double-bottom חי כרגע — הדבק את הערך מחישוב ישיר תחת ה-flag, וציין שזה computed-not-fired.

## Phase 2 · הרץ את חבילת-הטסטים → ירוק
- ✓/✗ `pytest tests/v9/test_atr.py tests/v9/regression/test_double_bt_relative.py -q` → **all green**. הדבק raw.
- ✓/✗ אין רגרסיה ב-double_bt הקיים: `pytest tests/v9/systems/test_five_min/test_double_bt.py -q` → green (החתימות `atr_5m=None` backward-compatible).
- לכל טסט חדש/משונה — שורת **"if reverted → RED because ___"** (הליטמוס מ-B1). לדוגמה: אם מחזירים `S2_ATR_RELATIVE` ל-`flag()` בלי default → `test_flag_defaults` אדום; אם מחזירים `tolerance=TICK_SIZE*2` קשיח → `test_flag_on_relative_tolerance` אדום.

## Phase 3 · `VERIFY_RELATIVE_2026-06-05.md` (Rule 5 — raw, לא טענה)
מלא את תבנית-הדוח (חלק C בחוזה): טבלת-phases · raw output לכל acceptance מ-1b+2 · ליטמוס פר-טסט · NOT-DONE.

## Phase 4 · commit + סנכרון בורדים
- commit: שני קבצי-הטסט (Cowork) + `VERIFY_RELATIVE` + עדכוני-בורד. הדבק `git log --oneline -3`.
- `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (כבר uncommitted): רשום ש-`a607d11` **אומת-חי** + flag live, סמן I-17 (double-bottom יחסי) לפי מצב, ורענן את שורת "עודכן"/"אתה כאן". K-ים נשארים OPEN (לא כוילו — soak).

---

## Phase 5 · אבחון-שורש I-21 (5-min/study export stall) — **DIAGNOSE-ONLY, read-only, אפס שינוי-קוד**
זהו השורש מאחורי I-11 (footprint 0 ברים) + I-15 (RED קפוא) — הערוץ 5-דק'/study נתקע ~11:35 CT בעוד tick/price/CVD חי (`PATTERN_DIAG §12:14`). **אל תתקן — אסוף ראיות והצע שורש+תיקון לאישור Michael** (B5/B6 · Rule 4).

**אסוף (הדבק raw לכל אחד):**
1. mtimes + last-line של קבצי-הייצוא ב-`~/SierraChart_Data/v9_export/` — ערוץ 5min/woodies/footprint/day_type מול ערוץ tick/price. האם ה-5דק' קפוא וה-tick חי? (`ls -la --time-style=full-iso` + `tail -1`).
2. `/tmp/bridge.err.log` — חפש `push FAILED` / stall / ערוץ שתק (`tail -100`, grep ל-stream-names).
3. DB: `MAX(ts)` פר-טבלה רלוונטית (`v9_bars_5min`, `v9_woodies`, footprint) מול now — איזה ערוץ פיגר.
4. **I-20/C-6 mask:** ב-`/api/v9/build/pattern-status` הצג את `data_freshness` הגולמי — `last_bar_ts`, `lag_seconds` (האם שלילי ~−3h?), `fresh`, `threshold`. זהו ה-TZ-mix (IL-as-UTC, מפר Rule 4) שמסתיר את ה-stall.

**פלט Phase 5 (דוח, לא קוד):** שורש מוצע ל-I-21 (Sierra-export? bridge? DB?) + תיקון מוצע ל-I-20/C-6 (TZ-normalize `last_bar_ts`→UTC בגבול + אכיפת `|lag|≤threshold` לפני `fresh=true`) — **להמתין לאישור Michael לפני מימוש**.

---

## VERIFY (סיכום מה שחוזר אליי — raw)
- P1: `ps eww` grep · import→True · tolerance ATR-value.
- P2: 2× pytest green (raw) + ליטמוס פר-טסט.
- P3: `VERIFY_RELATIVE_2026-06-05.md` קיים.
- P4: `git log --oneline -3` + בורדים מסונכרנים.
- P5: 4 ראיות גולמיות + שורש-מוצע + תיקון-מוצע (לא ממומש).

## NOT-DONE / DEVIATIONS (חובה — גם אם "none")
צפוי-פתוח: כיול-K (soak) · מימוש תיקון I-21/I-20 (ממתין אישור) · cross-check Sierra SoT (CCI/OHLC) אם אין גישת-export בזמן-הריצה.
