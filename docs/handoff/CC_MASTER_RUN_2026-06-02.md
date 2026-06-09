# CC Master Run — MEMS26 · 2026-06-02 (ביצוע מסודר של כל התיקונים)

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מטרה:** לבצע את כל התיקונים מאבחון 2/6, **לפי הסדר**, עם עצירות חובה, ובסוף **דוח מאוחד** של מה תוקן ומה בוצע.

## חוקים (חובה)
- **thread אחד בכל פעם.** סיים phase + commit + דווח — לפני שעוברים ל-phase הבא.
- כל phase = בצע את קובץ הפרומפט המפורט שלו (הכתובת מופיעה למטה). שם נמצאים הפרטים, ה-Acceptance Criteria והטסטים.
- **אל תמשיך** ל-phase הבא אם הקודם לא ירוק או לא נעשה לו commit.
- 🛑 **strategic-stop** = עצור ושאל את Michael לפני שאתה ממשיך. **אל תחליט לבד** ואל תרחיב בשקט.
- אם phase כבר בוצע (כמו S3MUTE/trend_original) — **אמת בלבד ודלג**, וכתוב זאת בדוח.

## הסדר

| # | Phase | קובץ פרומפט | סיכון |
|---|-------|-------------|-------|
| 1 | **D-S3MUTE** — השתקת S3 שמציף סטטיסטיקות | `docs/handoff/CC_PROMPT_D_S3MUTE_2026-06-02.md` | בטוח |
| 2 | **S4 Woodies** — dispatcher single-source + observability | `docs/handoff/CC_PROMPT_S4_WOODIES_CANFIRE_2026-06-02.md` | בטוח |
| 3 | **Build-Status mega** — global_gates + bridge inventory + D-RDY | `docs/handoff/CC_PROMPT_BUILD_STATUS_MEGA_2026-06-02.md` | observability · 🛑 שער B0 (הצג inventory לאישור לפני מימוש מלא) |
| 4 | 🛑 **S2 / D-RVX** — גייט volume + 3 וריאציות | `docs/handoff/CC_PROMPT_S2_REACTIVE_CANFIRE_2026-06-02.md` | logic · strategic-stop על `cumulative_delta` חי — **עצור ושאל** |
| 5 | 🛑 **S1 Day-Type** — atr-None + day-type | `docs/handoff/CC_PROMPT_S1_PIPELINE_AUDIT_2026-06-02.md` | logic · strategic-stop על מקור daily-ATR — **עצור ושאל** |
| 6 | **Trades UX** — TradeDetailsModal dead-code + שדות + פילטרים | `docs/handoff/CC_PROMPT_TRADES_UX_UPGRADE_2026-06-02.md` | UI · בטוח |

**הערה:** Phases 1-3 + 6 בטוחים — אפשר לרוץ ברצף. Phases 4-5 דורשים עצירה לאישור Michael (logic).

## אחרי כל ה-Phases — דוח מאוחד (חובה)

שמור ב: `docs/reports/CC_MASTER_RUN_REPORT_2026-06-02.md`, וכלול:

1. **טבלת סיכום:** `Phase · Status (DONE/PARTIAL/NOT-DONE/STOPPED) · Commit · Evidence (command + raw output)`.
2. **רשימת כל התיקונים שבוצעו:** לכל אחד — `קובץ:שורה` · מה שונה · הטסט שמוכיח + שורת *"if reverted → RED because ___"*.
3. **סעיף NOT-DONE / נעצר:** מה לא בוצע או נעצר ל-strategic-stop, ולמה, ומה צריך כדי להמשיך.
4. **עדכון מסמכי מעקב:** `docs/plans/STATUS_BOARD.md` + `docs/plans/ROADMAP_TO_LIVE.html` (root→fix→verification).
5. **Open:** מה נשאר פתוח.

**כלל זהב (Rule 5):** לכל "בוצע/עובד/עובר" — הדבק command + פלט גולמי. בלי פלט = לא נחשב בוצע.
