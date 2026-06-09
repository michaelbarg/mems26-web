# CC Prompt — DB Write-Safety ROOT FIX (corruption recurs under load) · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מצב מאומת (Cowork+CC):** `data/mems26_local.db` נשחת מחדש תוך דקות מהעלאת ה-backend.
`integrity_check` עם backend **כבוי** עדיין מראה corruption (`Rowid out of order`, `2nd reference
to page`, tick_reversal עם TEXT ב-ts/NULL ב-close, 30min_woodies חסר שורות באינדקס). זה **נזק
אמיתי וחוזר**, לא קריאה קרועה. **trades לא נפגעו** (טבלה נפרדת, תדירות נמוכה).

**שורש (ראיה):** כתיבות SQLite מקביליות לא-בטוחות — חיבור **משותף** בין threads
(`footprint_system.py:80`, `check_same_thread=False`, כתיבה בתדירות גבוהה) + סחף של
`sqlite3.connect` גולמיים (`woodies_system.py:141/549/573`, `reversal_handler.py:75`, routes)
בלי `WAL`/`busy_timeout` עקביים.

**מטרה:** תיקון-שורש לבטיחות כתיבה **+** לאפשר איסוף היום — **מגודר ב-SOAK-TEST**.
RTH נפתח בעוד ~2 שעות. אם ה-soak לא נקי → **לא אוספים היום** (לדווח; לא לסחור/לכייל על נתונים מושחתים).

**אסור לגעת (risk surface):** לוגיקת ההחלטה/ירי של המערכות. **רק שכבת persistence/DB.**

## Phase 0 · אבחון מדויק (read-only, ~15 דק')
- אַתֵר את כל נתיבי הכתיבה ל-DB הראשי; זהה אילו רצים במקביל/threads שונים. הוכח את החיבור-המשותף
  (`footprint._conn`) ואת הכותבים ללא pragmas.
- אם אפשר — **שחזר את ה-corruption בטסט מבוקר** (שתי כתיבות מקביליות דרך אותו חיבור → integrity נכשל).
  זה ה-baseline שמוכיח שהתיקון עובד.
- **דווח לפני שתתקן** (B6 — אל תרחיב בשקט).

## Phase 1 · תיקון-שורש: writer יחיד מסודר (~45-60 דק')
- כל הכתיבות ל-DB הראשי עוברות דרך **נתיב כתיבה יחיד**: thread כותב יחיד עם תור (queue), או lock
  גלובלי יחיד שעוטף כל `persist`. **אף חיבור לא משותף בין threads.**
- כל חיבור: `open → write → commit → close` קצר, עם `PRAGMA journal_mode=WAL` + `busy_timeout`.
  לבטל את החיבור הקבוע המשותף ב-footprint.
- ודא ש**נתיב רישום ה-trades** עובר דרך אותו writer בטוח — זה הקריטי.

## Phase 2 · בידוד הכותבים הרועשים + FIFO
- `tick_reversal` + `footprint` (תדירות גבוהה) — להוציא מה-DB הראשי ל-store נפרד/זמני,
  **FIFO-capped** (חלון מתגלגל, זורק ישן). מקור-אמת שלהם = Sierra; אין צורך בעומק.
  (footprint כבר מושתק ב-D-S3MUTE — לוודא שגם ה-persist מופנה/מושתק.)

## Phase 3 · כיבוי מסודר
- לתפוס `SIGTERM` → `PRAGMA wal_checkpoint(TRUNCATE)` → close נקי. לתקן את ה-LaunchAgent שישלח
  `SIGTERM` (לא `SIGKILL`) ולא יעשה restart מיידי תוך כדי flush.

## Phase 4 · DB נקי + backfill
- להעלות על ה-DB הנקי (מהשחזור הקודם). `backfill` ההיסטוריה מ-Sierra exports
  (`~/SierraChart_Data/v9_export/`) — **לא** מהגיבוי הפגום `.corrupt.bak`.

## Phase 5 · SOAK-VERIFY — שער GO/NO-GO (~30-40 דק' לפני הפתיחה)
- העלה backend תחת עומס מלא. הרץ `PRAGMA integrity_check` כל ~5 דק' לאורך כל החלון + ספירת trades עולה.
- **GO:** נשאר `ok` כל הזמן → אוספים היום (trades + bars_5min + day_type).
- **NO-GO:** כל סימן corruption → עצור איסוף, דווח, ה-fix ממשיך אחרי הפתיחה.
- הדבק פלט גולמי של **כל** integrity_check (Rule 5).

## דוח חובה (חלק C) + NOT-DONE + עדכון `STATUS_BOARD.md`+`ROADMAP_TO_LIVE.html`
- טסט אנטי-טאוטולוגי: הטסט המבוקר מ-Phase 0 עובר מ-**RED** (לפני) ל-**GREEN** (אחרי ה-writer היחיד);
  שורת *"if reverted → RED because בלי serialization שתי כתיבות מקביליות משחיתות"*.
- לוח זמנים צמוד — אם Phase כלשהו נתקע, **עצור ודווח** במקום לדלג.
