# CC PROMPT — Frozen-Tail Watchdog (detect + alert) — מגן על SHADOW soak + צעד ל"רציף" · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** רכיב **ניטור** — detect + alert בלבד. **אל תיגע ב-`sc_study/` / ב-Sierra study** (משטח anti-regression §7a) ולא ב-risk-logic.
אישור Michael 2026-06-04 (המשך לפי הסדר; task #14).

## הבעיה
frozen-tail ב-Sierra study חוזר למרות v9.4.5 (`816dd1a`): ה-DLL ממשיך לכתוב את `5min.json` (mtime מתקדם) אבל **מערך-הברים תקוע**.
היום התיקון הוא **Reload Study ידני** — בלתי-אפשרי ל-SHADOW soak (≥10 ימי RTH ללא קיטוע) ולמסחר רציף 24/7. צריך **זיהוי אוטומטי + התראה**.

## מה לבנות (detect + alert, read-only על מקורות-הנתונים)
1. **גלאי frozen-tail** — חתימה כפולה (שתיהן יחד = frozen-tail ודאי):
   - `~/SierraChart_Data/v9_export/5min.json`: ה-mtime מתקדם אבל **תֵג-הברים האחרון לא זז** מעל סף (למשל >3 מחזורי-כתיבה / >10 דק' RTH).
   - **ו-** `live_price.json` **חי** (mtime+ערך מתעדכנים) → מפריד "feed מת" מ-"frozen-tail" (ב-frozen-tail הפיד חי אבל הברים תקועים).
   - אימות-צולב מול PG: `MAX(ts) FROM v9_bars_5min` לא מתקדם בחלון RTH בזמן ש-live_price טרי.
2. **התראה** — דרך תשתית ה-Slack הקיימת (`SLACK_WEBHOOK_URL`/`SLACK_UAT_WEBHOOK`; אם לא מוגדר → `logger.warning` rate-limited, **לא** debug, לא silent). הודעה: "frozen-tail זוהה — 5min bars תקועים ב-<ts>, live_price חי, נדרש Reload Study".
3. **rate-limit** — התראה אחת לכל אירוע (לא ספאם כל מחזור).
4. **חשיפה ל-build-status/health** (אופציונלי אם זול) — דגל `feed_frozen` שה-`bridge_inspector` יכול להציג, כך שהדאשבורד מראה "❄️ frozen-tail" במקום להיראות בריא.

## מה לא לעשות עכשיו (scope)
- **לא** auto-reload של ה-study (זו פעולת-UI ב-Sierra; דורשת אינטגרציה נפרדת + נוגעת ב-sc_study). detect+alert קודם; auto-reload = פריט-המשך נפרד אם תרצה.
- **לא** לשנות את ה-DLL/study.

## Acceptance (✓/✗ + raw)
- [ ] גלאי מזהה frozen-tail סינתטי (בדיקה: mtime מתקדם + bars-tip קפוא + live_price טרי → alert נורה).
- [ ] לא-זיהוי שגוי: feed תקין → 0 alerts; feed מת לגמרי (live_price גם קפוא) → מסווג "feed down", לא frozen-tail.
- [ ] alert עובר דרך Slack (או logger.warning אם webhook לא מוגדר) — rate-limited, לא silent.
- [ ] 0 נגיעה ב-sc_study/study/risk-logic. commit + טסט · `git log` · NOT-DONE.

## Invariants
detect+alert בלבד · אל תיגע sc_study/DLL/risk-logic · localhost · No silent failures · Bridge Local-Only נשמר · Cowork מאמת בלתי-תלוי.
זה מגן על ה-SHADOW soak (feed לא-מקוטע) וצעד ראשון ל-unattended/רציף.
