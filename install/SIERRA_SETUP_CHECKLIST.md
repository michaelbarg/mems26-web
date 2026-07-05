# צ'קליסט התקנת Sierra — החצי הידני (אין מתקין שיכול לעשות אותו)

_זהו החלק שהמתקין `install_mems26.sh` **לא** יכול לבצע: Sierra Chart היא תוכנת צד-שלישי מורשית, ופריסת הסטאדי + הצ'ארט דורשות פעולה ידנית ב-UI שלה. עברו על זה שלב-שלב אחרי שהמתקין סיים. Mac path־ים לדוגמה — התאם למכונה._

---

## 0 · לפני שמתחילים
- [ ] המתקין (`install/install_mems26.sh`) רץ בהצלחה: `curl localhost:8000/api/v9/health` = ok.
- [ ] יש רישיון Sierra תקף למכונה הזו (רישיון **פר-משתמש** — לא מועבר אוטומטית ממכונה אחרת).
- [ ] Sierra מותקנת (על מאק — רצה תחת Wine; ודא שהיא נפתחת ומתחברת לספק-הדאטה).

## 1 · פריסת ה-DLL / הסטאדי
- [ ] במחשב-הפיתוח: `scripts/build_monolithic_cpp.sh --deploy` — ממזג את `sc_study/*` ל-`MES_AI_DataExport.cpp` ומעתיק ל-`~/SierraChart/ACS_Source/`.
      (אם מעבירים ידנית: העתק את הקובץ הממוזג ל-`~/SierraChart/ACS_Source/` במכונת-היעד.)
- [ ] ב-Sierra: **Analysis → Build Custom Studies DLL → Remote Build** (או Build). ודא 0 שגיאות.
- [ ] הוסף את הסטאדי `MES_AI_DataExport` לצ'ארט ה-MES (5-דקות RTH).
- [ ] הוסף גם את סטאדי ה-Woodies/5min/cumulative_delta/tpo לפי הקונפיג הקיים.

## 2 · Study Inputs (נשמרים פר-צ'ארט ב-UI של Sierra)
- [ ] **Input 4 — V9 Export Directory** = הנתיב מהמתקין: `~/SierraChart_Data/v9_export/`
      (חייב להיות זהה ל-`V9_EXPORT_DIR` ב-`.env`).
- [ ] **Input 0** — ExportPath (אם רלוונטי לקונפיג שלך).
- [ ] **Input 7** — V9 Lookback.
- [ ] **Input 11/12/22** — TradeCommandPath / TradeResultPath / TradeFillsPath (לביצוע-עסקאות).
- [ ] **Input 21 — EnableOrderPlacement = 0 (כבוי!)** עד שאתה מוכן ל-DEMO/LIVE בפועל.
- [ ] **Input 18** — Woodies same-chart (לפי הקונפיג).

## 3 · חוזה (Contract)
- [ ] הגדר בכל צ'ארט/סטאדי את **החוזה הנוכחי** (למשל `MESU26` לספטמבר) — לא חוזה ישן שפג.
- [ ] ודא שהצ'ארט מציג דאטה חיה (RTH), לא היסטורי-בלבד.

## 4 · אימות ה-feed (הלולאה המלאה)
- [ ] קבצי JSON מופיעים ומתעדכנים ב-`~/SierraChart_Data/v9_export/`:
      `5min.json`, `cumulative_delta.json`, `woodies*.json` — **טריים ≤2 שניות** בזמן RTH.
- [ ] ה-promoter רץ: `launchctl list | grep export_promoter` (מקדם `.tmp→.json`, פותר את באג-ה-Wine).
- [ ] הברידג' דוחף: `tail /tmp/bridge.err.log` — אמור להראות push-ים ל-`localhost:8000` (ולעולם לא URL-ענן).
- [ ] `scripts/mems26_verify.sh` = ירוק (services · DLL · feed · DB).
- [ ] בדשבורד (`localhost:3000`): הברים, סוג-היום, ומצב-המערכות מתעדכנים.

## 5 · לפני מסחר-DEMO ראשון
- [ ] `docs/runbooks/PRE_TRADE_PROTOCOL.md` — עבור על הצ'קליסט המלא.
- [ ] `.env`: `DEMO_EXECUTION_ENABLED=1`; החלטות-סטנדינג כבויות נשארות כבויות.
- [ ] Input-21 ב-Sierra מופעל **רק** כשאתה באמת רוצה שהמערכת תשלח פקודות.

---

**כלל-הזהב שנשאר גם כאן:** הברידג' דוחף **רק** ל-`localhost:8000`. אם ראית `API push FAILED to https://...` — עצור ובדוק את `.env`/הקונפיג (CLAUDE.md §Bridge Local-Only).
