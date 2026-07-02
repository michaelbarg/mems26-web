# MEMS26 — דוח-ניקוי: מה מת, מה מבלבל, ומה מקור-האמת (2026-07-02, Cowork)
_בסיס: האינדקס רוענן היום (739 קבצים, 48 חשודי-יתום — `SYSTEM_TREE.html` בדשבורד) + כל ממצאי-הסשן. כלל-ברזל: **לפני-LIVE מסמנים ומקפיאים, לא מוחקים** (מחיקה = אחרי שבוע-המדידה, בקומיט-ניקוי ייעודי אחד)._

## א · מקורות-האמת (כולל סוג-היום) — הטבלה הקובעת
| אות | מקור-האמת | מה מתחזה/מת (לא לגעת) |
|---|---|---|
| **סוג-יום** | `classify_replay` / `classifier_core` (7-סוגים) → stamps דרך `extract_g1_entry_context`; חי per-bar (`S1_ENGINE_NEW_CLASSIFIER=1`); UI: הבאדג' החדש קורא מהמקור הזה | 🔴 מנוע-3-הסוגים הישן עוד בקוד (למחיקה אחרי-אימות-part-b) · endpoints מתים: `/day_type/current`, `/day_type/v9/current` |
| ברים-5דק' | `v9_bars_5min_woodies` (רציף, קנוני) | 🔴 `v9_bars_5min_continuous` — close-זבל, אסור לחווט · `v9_bars_5min` = דלתא-פר-בר בלבד (יכול להיתקע) |
| CVD לזיהוי-S2 | `v9_bars_cumulative_delta` (טרי ✓ אומת היום) | ⚠️ עמודת-ts שלה TEXT (מחלת-I-53) — לתקן טיפוס |
| הרשאת תבנית×יום | `config/daytype_playbook.yaml` (הוכרז קנוני D-1; הלילה מיושר) | 🟡 auth-verdicts (יישור-מוכרז) · TableB=מסמך · PATTERN_AWARE=רדום |
| גודל-פוזיציה | `FIXED_CONTRACTS_3` בשלוש נקודות-חנק (+VOL_REGIME הלילה) | 🔴 **שתי מערכות-sizing חיות במקביל:** `calculate_size` הישן עדיין רץ בנתיב-הניתוב (A5 "reject" בזמן ש-V2 אמר 3! — ראיית 18:50) — לאחד ל-V2 בלבד (נוסף לפריט-11) |
| מצב-סלוט/עסקאות | gateway in-memory + `v9_trades` (self-heal מגשר ✓) | — |
| דגלים | `docs/FLAG_INDEX.md` (מג'ונרט) | רשימות-דגלים בפרוזה = היסטוריה |

## ב · מה מבלבל את המערכת (רעש חי — לתקן, לא למחוק)
1. **"unknown stream: cvd_continuous / bars_5min_continuous"** — ספאם כל-היום ב-StreamHealth (אלפי שורות!): הברידג' דוחף זרמים ש-StreamHealth לא מכיר → לרשום אותם או להפסיק לדחוף. מציף את הלוג ומסתיר אזהרות אמיתיות.
2. **כפל-שכבות ירי ב-S4:** `PatternDispatcher` (winner-selection) + dispatch פנימי ב-woodies + D-094 rr-selection (כבוי) — שלוש שכבות-בחירה; לתעד מי חי ולמחוק את הכבויה אחרי-LIVE.
3. **טסטים-נכשלים-ידועים (21)** — הוכח היום שהם קדם-קיימים (fixture-era); חלקם ייסגרו עם פריט-2 — לירוק את השאר או לסמן xfail עם סיבה, כדי שכשל-אמיתי חדש לא יטבע ברעש.
4. **ts-כ-TEXT** בשתי טבלאות (cumulative_delta, tpo trading_date) — כל שאילתא שנייה נופלת על casting.
5. **כפל-מפות-צבע-DT ב-UI** (round-2 איחד ל-lib אחד; המפות הישנות לניקוי).

## ג · מת-או-חשוד — רשימת המחיקה-לאחר-LIVE (מהאינדקס + היום)
- **48 חשודי-יתום** ב-SYSTEM_TREE (סינון "רק יתומים") — המובהקים: `gateway/{demo,live,shadow}_executor.py` (סטאבים שהוחלפו ב-services/trading_gateway/executors) · `trade_management.py` הישן · UI: `TradeReviewPanel/TradeDetailsModal` (החדש החליף) + 4 ה-pills שה-strip החליף · סקריפטי-outputs חד-פעמיים.
- **גייטים-ישנים בקוד** (reactive_location/trend_direction — כבויים מהיום; הקוד נשאר לעת-עתה בכוונה).
- **שאריות-SQLite** (4 אתרים — inventory-check, tpo_snapshotter-writer, HistoricalReplay-path, sot_health) — הארכיון ב-PG נצבר ✓ (705 שורות), אז מחיקה בטוחה אחרי אימות-אחרון.
- **HFE** — מושבת-לצמיתות; הקוד נשאר (סטנדינג — לא מוחקים בלי מיכאל).

## ד · איך בוחנים בעצמך
`localhost:3000/patterns-visual.html` = התבניות · **SYSTEM_TREE.html** (קישור בדשבורד) = כל קובץ 🟢בשימוש/🔴יתום עם חיפוש · `docs/SOURCE_OF_TRUTH.md` (יעודכן עם טבלה-א' הזו) · `docs/FLAG_INDEX.md` = כל דגל. **קומיט-הניקוי:** אחרי שבוע-המדידה, PR ייעודי אחד עם gen_index לפני/אחרי.
