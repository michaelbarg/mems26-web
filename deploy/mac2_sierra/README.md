# חבילת-סיירה למק-2 — נארזה ממק-1 ב-2026-08-19 (snapshot חי של המכונה הסוחרת)

**למי:** cc-imac. **מה:** כל צד-סיירה הדרוש לשכפול, דרך git (הערוץ היחיד למק-2).
ה-runbook המלא: `docs/runbooks/MAC2_CLONE_24_7.md` (כולל שלב-1א). סדר-ביצוע במק-2:

1. **סיירה סגורה** לפני הכל.
2. צ'ארטבוקים: `cp deploy/mac2_sierra/Data/*.Cht ~/SierraChart/Data/`
   (הראשי: `AAMichael_lap25.Cht`).
3. `cp -R deploy/mac2_sierra/SymbolSettings ~/SierraChart/` (מיזוג/דריסה).
4. `cp deploy/mac2_sierra/Sierra4.config deploy/mac2_sierra/Accounts4.config ~/SierraChart/`
   ⚠️ אחרי הפתיחה לעבור ב-Global Settings על נתיבים מקומיים (Data Files Folder,
   ACS_Source). אם סיירה תבקש סיסמת-Ironbeam בחיבור הראשון — מייקל מקליד פעם אחת
   (grep אישר שאין סיסמה גלויה בקבצים; ייתכן שהיא לא נארזת).
5. **סטאדי:** `./scripts/build_monolithic_cpp.sh --deploy` → פתיחת סיירה →
   Remote Build → reload study → Input-4 = `/Users/<user>/SierraChart_Data/v9_export/`.
6. **גשר:** `mkdir -p ~/SierraChart_Data/v9_export` → התקנת LaunchAgents מהריפו
   (backend · bridge · export-promoter · mobile_relay · startup_check).
7. **שער-אימות (בלי-ירוק-אין-מסחר):** `mems26_verify.sh` → `mems26_arming_gate.py` →
   `fire_drill.py` 🟢 → `sim_drill_5_contracts.py` על סים.
8. דיווח חתום ב-`docs/handoff/LIVE_CHANNEL.md` + שורת-STATUS_BOARD עם ראיות (חוק-5).

**לא לחמש לייב** לפני הכרעות-מייקל בשלב-3 של ה-runbook (תפקידים · סשן-Ironbeam-כפול).
החבילה הזו היא snapshot חד-פעמי — אם הצ'ארטבוק ישתנה במק-1, לארוז מחדש (לא מקור-אמת חי).
