# CC PROMPT — DB Corruption RECURRED (P0) · rebuild + serialize residual ORM writers · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** P0 בטיחות. commit אטומי · לא `git add -A` · פלט גולמי. **אישור Michael 2026-06-03.**

## ⚠️ ה-corruption חזר אחרי שתיקון-השורש "אומת"
**אומת אמיתי (Cowork, ~12:48 ET):** 3 קריאות read-only רצופות → **אותו עמוד מושחת** `Page 76860: btreeInitPage()` → `database disk image is malformed`. עמוד זהה = השחתה על-דיסק, לא mount false-positive. **זו הסיבה ל"אין נרות"** (קריאות נכשלות). קיים כבר `data/mems26_local.db.bad2`.

**למה זה חזר:** ה-root-fix (`9255bfa`) החזיק תחת soak של 21,726 דחיפות — אבל ה-soak בדק רק את נתיב ה-**ingestion** בתדר-גבוה, **לא** את נתיב **עיבוד-הברים החי**. ה-residual ~5 כותבי-ORM שנותרו לא-מסורלים (`woodies_system.py:651` `tm._db.commit()`, `five_min_system.py:957`, `day_type/consumer.py:147`, APIs) רצים בעיבוד-הברים החי = **החשוד המרכזי**. ההערכה הקודמת "low risk, defer" הייתה שגויה.

## פעולות
1. **עצור backend.** `PRAGMA integrity_check` (אוטוריטטיבי) → זהה איזו טבלה/עמוד (76860) שייך לאיזו טבלה. הדבק פלט.
2. **המר את כל כותבי-ה-ORM הנותרים ל-`safe_writer`** (זה היה #6, עכשיו P0 — סגירת ה-root באמת):
   - `woodies_system.py:651` (`tm._db.commit()`) · `five_min_system.py:957` · `day_type/consumer.py:147` · `woodies/api.py:119` · `day_type/api.py:332`.
   - לכל אחד: `db.add/commit` → `safe_execute`/`safe_executemany`. **אל תחזיר lock ל-get_db.** (קריאות נשארות get_db/mode=ro.)
   - grep אימות: 0 `\.commit()` שכותב מחוץ ל-safe_writer ב-`systems/` + `api/`.
3. **rebuild נקי** (recover/DROP+VACUUM). **לא** מ-`.corrupt`/`.bad2`/`.bak` הפגומים.
4. **soak שמפעיל גם עיבוד-ברים** — לא רק POST ingestion: הזרם ברים דרך BarRouter→S2/S4.process_bar (שמפעיל את woodies/day_type commits) במקביל לדחיפות, ≥10 דק'.
5. **עצור backend → `integrity_check` = ok.** הדבק. אם לא → זהה את הכותב שנותר.

## Acceptance
- [ ] integrity backend-כבוי = ok **אחרי soak שכולל עיבוד-ברים**. ✓/✗
- [ ] grep: 0 ORM-write commits מחוץ ל-safe_writer ב-`systems/`+`api/`. ✓/✗
- [ ] טסט: כתיבה מקבילה מ-2+ נתיבי-ORM (woodies+day_type) + ingestion → integrity נשאר ok. ✓/✗
- [ ] regression ירוק · commit · `git log -1`.

## Invariants
get_db לא נועל · safe_writer-only · לא לשחזר מ-corrupt/bad/bak · Sierra=SoT · אל תיגע sc_study/B2/B3/LaunchAgent. **❌ לא לאסוף SHADOW עד integrity backend-כבוי=ok.** אחרי הדוח — Cowork מאמת בלתי-תלוי.

## הערה
זה reopener של "DB root fix verified" — הסטטוס היה PARTIAL בפועל (soak לא כיסה עיבוד-ברים). עדכן STATUS_BOARD/ROADMAP בהתאם (Cowork יעשה).
