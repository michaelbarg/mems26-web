# פרומפט CC — תיקון 11 כשלי test-ordering (DB isolation) → pytest נקי

> להדבקה ב-Claude Code. **קרא קודם `CLAUDE.md`.**
> **test-infra בלבד** — אסור לגעת בקוד production / לוגיקת מסחר / order / sc_study.
> דוח אוטומטי בסוף (פורמט קבוע, פלט גולמי).

---

## מצב
מקור: `docs/reports/PYTEST_CLOSE_2026-05-31.md`. 11 כשלים נותרים — **כולם עוברים
בבידוד** (`pytest <file> -v` = PASS) ו**נכשלים בסוויטה המלאה** → זיהום state משותף
(DB חי / singletons ברמת מודול). אפס קשר ללוגיקת מסחר.

| אשכול | כמות | שורש |
|-------|------|------|
| `test_bar_level_detector_entry_guard` | 3 | זיהום state מטסטים שכותבים ל-DB חי |
| `test_blocker_sweep_regressions` | 3 | singleton ברמת מודול לא מאופס בין טסטים |
| `test_trail_engine::TestIntegration` | 2 | session state מטסטי manager קודמים |
| `test_cross_system_integration` | 1 | DB חי נעול ע"י כתיבות מקבילות |
| `test_replay_clock_consumers` | 1 | כנ"ל |
| `test_snapshot_compliance::t1_hit` | 1 | אינטראקציית mock בתוך class |

## משימה
לתקן כך שכל 11 **יעברו בסוויטה המלאה** — דרך **בידוד אמיתי**, לא הסתרה.

1. **DB isolation:** temp/in-memory DB per test (או per module), באותו דפוס כמו
   `tests/v9/gateway/conftest.py` (autouse → temp DB, override `DATABASE_URL`). יישם
   ל-scopes שכותבים ל-DB החי (bar_level_detector, cross_system, replay_clock).
2. **Singleton/module reset:** fixture autouse שמאפס state ברמת מודול בין טסטים
   (blocker_sweep, trail_engine session state).
3. **Mock reset:** ב-snapshot_compliance — אפס mock בין מתודות (setup/teardown).

## כללי ברזל
- **קוד טסטים/conftest בלבד** — אפס שינוי production.
- **אסור** `skip`/`xfail`/מחיקת assertions כדי "לעבור" — חייבים לעבור בזכות בידוד אמיתי.
- אם מתברר ששורש אחד הוא **באג production אמיתי** (לא זיהום) → **STOP ודווח**, אל תתקן לוגיקה.
- אסור לגעת ב-live DB path / order / sc_study / polling.

## אימות
רוץ פעמיים: (a) `pytest <each file> -v` = PASS (כמו קודם), (b) **`pytest tests/ -q`
מלא** = **0 failed**. הדבק את שתי הריצות (raw). זה הקריטריון — ירוק בסוויטה, לא רק בבידוד.

## תוצר
`docs/reports/PYTEST_GREEN_FINAL_2026-05-31.md`: לכל אשכול — fixture שנוסף + raw
before/after, ופלט `pytest -q` סופי (0 failed). אם נשאר משהו — סיבה מדויקת.
