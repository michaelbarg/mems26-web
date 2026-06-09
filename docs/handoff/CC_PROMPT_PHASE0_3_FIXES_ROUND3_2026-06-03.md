# CC ROUND-3 FIX PROMPT — Phase 0-3 verification gaps (Cowork, 2026-06-02 night)

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי. הפק דוח בסוף. **אל תעשה `git add -A`** — קמיט רק קבצים מפורשים (ראה למטה).

**רקע:** אימות Cowork בלתי-תלוי של דוח Phase 0-3 מצא: B1 תוקן בפועל אך **לא קומיט**; `sc_study` שונה על ה-risk-surface; D1 over-claimed; Phase 3 נרות לא מאומת.

---

## 🔴 FIX-A (P0) — קמיט את תיקון B1 (כרגע uncommitted → ייאבד)
**ראיה:** `git status` → `M five_min_system.py` (bypass אתר-2 שורה ~629) + `?? tests/v9/regression/test_b1_lookback_bypass.py` (untracked). שניהם **לא בקומיט** `9a5ed5d`. הדוח טען "DONE @ 9a5ed5d" — שגוי.
**פעולה:** קמיט **רק** את שני הקבצים האלה (לא add -A):
```
git add backend/v9/systems/five_min/five_min_system.py tests/v9/regression/test_b1_lookback_bypass.py
git commit -m "fix(S2): B1 lookback bypass at Initiative site (631) + anti-tautological test"
```
- **Acceptance:** `git status` → אין M/untracked לשני הקבצים; `grep -c "lookback_quiet = True"` = **2**; `pytest tests/v9/regression/test_b1_lookback_bypass.py` ירוק + litmus revert→RED (הדבק שתי ריצות). ✓/✗

## 🔴 FIX-B (P0) — `sc_study/` על ה-risk-surface: אל תיגע, אל תקמט, דווח
**ראיה:** `git diff sc_study/` → 3 קבצים שונו (uncommitted): `MES_AI_DataExport.cpp` (SWI SG5→SG0), `v9_types.h` (גרסה `v9.4.5-wc-fix`), `v9_woodies_export.h` (~165 שורות). **לא חלק מ-Phase 0-3.**
**פעולה — אבחון בלבד, אפס שינוי:** דווח: (1) `git log -1` מתי השינוי נכנס לעבודה? מי? (2) האם ה-DLL הרץ (`~/SierraChart/...`) **בנוי מהמקור הזה** או ישן (cross-check `docs/runbooks/SIERRA_DLL_OPS.md`)? (3) האם יש סיכון של source≠running-DLL?
- **אסור:** לקמט את `sc_study`, לבנות, או לבצע Remote Build. זו החלטת Michael. **ודא שאף קומיט בריצה זו לא כולל `sc_study/`.**
- **Acceptance:** דיווח provenance + מצב build, ללא נגיעה. ✓/✗

## 🟡 FIX-C (P1) — D1: תקן את הטענה (over-claimed)
**ראיה:** רק `S2_VSA_VOLUME`,`S1_LIVE_RECLASS` call-time (`173c8d6`). עדיין קפואים ב-import (11 אתרים): `S2_ATR_RELATIVE`(×8), `S3_RELATIVE`(×2), `S3_MUTE`, `FOOTPRINT_DISABLED`, `S1_IB_WIDTH_ATR`, `S1_DAYTYPE_STAGING`, `S1_CVD_OPENING`.
**פעולה (בחר):** (א) השלם המרה ל-`flag()` call-time בכל ה-11 + קמט; **או** (ב) עדכן את הדוח/STATUS ל-`D1 = PARTIAL` עם הנימוק "latent בלבד — plist מייצא לפני python, סיכון רק ב-flip-בזמן-ריצה". **אל תשאיר את הטענה 'all flags call-time'.**
- **Acceptance:** grep 0 קפואים (א) **או** דיווח PARTIAL מפורש (ב). ✓/✗

## 🟡 FIX-D (P1) — Phase 3 נרות: ההיוריסטיקה לא אמינה + חסר אימות
**ראיה:** `bars_5min_history.py` — filter ">2h gap". הפסקת MES יומית ~1h → בימי חול אין gap>2h → הברים מהסשן הקודם **לא** מוסרים. השורש האמיתי: מיון string על `ts` (15:xx אתמול ממוין אחרי 09:30 היום).
**פעולה:**
1. החלף את היוריסטיקת ה-gap ב-**חיתוך session אמיתי**: parse ל-ET, שמור רק ברים מתחילת הסשן הנוכחי (CME globex open 18:00 ET אתמול, או 09:30 ET RTH — לפי הצורך). אל תסנתז ברים. SoT = endpoint.
2. **C2 CVD:** ודא ש-`cvdBars`/CVD pane נגזרים מאותו set מסונן (יישור נשמר).
3. **אימות חזותי (חובה, Rule 5):** screenshot של הצ'ארט שמראה נרות-סשן-נוכחי + CVD מיושר. **אם השוק סגור עכשיו (3 ברים בלבד) — האימות החזותי נדחה ל-RTH מחר; ציין זאת מפורשות ב-NOT-DONE, אל תטען "verified" בלי screenshot.**
- **Acceptance:** filter מבוסס-זמן-אמיתי (לא gap) + before/after counts על נתונים אמיתיים + screenshot **או** דחייה מפורשת ל-RTH. ✓/✗

## ℹ️ FIX-E (תיעוד) — B4 artifact מאשר זיהום
B4 אומת artifact (DB 930K vs Sierra 72K). תעד ב-STATUS שכל כיול VSA/בקטסט (כולל המספרים שהצדיקו B1/B3) חשוד-זיהום עד שה-ingestion יתוקן. (תיקון ה-ingestion עצמו = strategic, אישור Michael.)

---

## דוח (חלק C)
טבלת FIX · Status · Evidence(command+output) · litmus לכל טסט · NOT-DONE (כולל screenshot-deferred אם רלוונטי + provenance של sc_study) · Open.
**אל תקמט `sc_study/`, CLAUDE.md (ראה הערה), או קבצי docs לא-קשורים. קמט אטומי לכל fix.**

## הערה על CLAUDE.md
§DB Write-Safety (uncommitted) טוען "`get_db()` acquires the same lock around commit (`ec9fe97`)" — **סותר את הקוד** (`session.py:71-81`: אין lock, בוטל deadlock). זו ה-doc-drift. **אל תתקן אוטונומית** — דווח ל-Michael שצריך להכריע: לתקן את הדוק לתאר את המציאות (WAL-only + tick_reversal off), או לשנות את הקוד.

## אסור לגעת
`sc_study/` · `get_db()` lock · `safe_writer.py` · B2/B3 · polling · LaunchAgent · bridge routes.
