# CC PROMPT — B4 Volume Artifact FIX (RTH-only table, time-gated) · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי, commit אטומי, **לא `git add -A`**, פלט גולמי. **אישור Michael 2026-06-03.**

## רקע (שורש מאומת — דוח B4 diagnose)
RTH chart (`/api/v9/bars/5min`) ו-continuous chart (`/api/v9/bars/5min_continuous`) כותבים לאותה טבלה `v9_bars_5min` ב-INSERT OR REPLACE. **מחוץ ל-RTH** (settlement 16:00–16:40 ET + overnight) ה-RTH chart מייצא נפח-**סשן-מצטבר** (עד 1M) — אלה הברים המנופחים. בתוך RTH הברים תקינים per-bar. אומת: DB vol=1,000,000/OHLC של פתיחת-סשן מול Sierra continuous vol=1,244.

## הכרעת Michael — היום: טבלה אחת בלבד = RTH (מימד הזמן הוא הקובע)
ה-RTH chart **מחובר לכל הסטאדי** (Woodies/TPO/POC/IB) → הוא המקור היחיד היום. הטבלה הרציפה 24h = **משימה נפרדת לעתיד** (לא בונים עכשיו). המסחר נפתח 09:30 ET ואנחנו בוחנים את העבר מתוך נתוני ה-RTH הקיימים.

### Fix A (core, time-gate) — RTH writer כותב רק בשעות RTH
- בנתיב הכתיבה של מקור-ה-RTH ל-`v9_bars_5min` (`/api/v9/bars/5min` ו/או bridge `bars_5min_stream`): כתיבה מתבצעת **רק** ב-RTH **09:30–16:00 ET**. מחוץ ל-RTH → דלג (זה החלון שבו נוצרים הברים המנופחים). הפיך (בדיקת-זמן/דגל).
- ⚠️ TZ מפורש ET, לא "assumed" (Rule 4). שים לב ל-DST.

### Fix A2 — מקור ה-continuous לא כותב ל-v9_bars_5min היום
- ה-`/5min_continuous` לא כותב ל-`v9_bars_5min` (הטבלה הרציפה הייעודית = משימה נפרדת). **לפני שמשביתים — אמת ודווח:** האם תצוגת הצ'ארט/סטאדי כלשהו תלוי כרגע בכתיבות ה-continuous לטבלה הזו? אם כן — דווח ואל תשבור; אם לא — השבת/נתב (הפיך).

### Fix A3 — CVD (cumulative delta) גם מ-RTH היום, מיושר לנרות
- היום ה-cumulative delta מגיע מ**אותו מקור RTH** + **אותו time-gate** (09:30–16:00 ET) כמו הנרות → נרות ו-CVD מיושרים מעצם הבנייה (פותר גם את C2 alignment). מקור-RTH ל-`cumulative_delta` כותב רק ב-RTH; מחוץ ל-RTH → דלג.
- `/cvd_continuous` (CVD רציף) = **לא** משמש היום → חלק ממשימת הטבלה הרציפה העתידית. (אמת/דווח אם משהו תלוי בו לפני שמשביתים.)
- אמת שאין artifact מצטבר ב-CVD בחלון settlement (כמו בנפח).

### Cleanup — סימון הברים המנופחים הקיימים (הפיך, **לא מחיקה**)
- סמן `is_synthetic=1` בשורות `v9_bars_5min` עם `volume > 100000` ו/או מחוץ לחלון RTH שלא תואמות per-bar. דרך `safe_writer`. **אל תמחק.**
- ודא ש-VSA `rolling_avg` **מתעלם** מ-`is_synthetic=1` (זה הפער שמזהם את S2).

## Study-field connection verification (Sierra export study ID:10) — אימות read-only, דווח, **אל תשנה Sierra UI**
ה-study "MES AI Data Export" (ID:10, על Chart #3) מאגד שדות ממספר studies/charts. קלט נוכחי (Michael, screenshots 2026-06-03):
- In:1 Export JSON Path · In:2 interval=3s · In:3 VA%=70 · In:4 Imbalance=3 · In:5 V9 Export Dir · In:6/7 Tick Reversal 15/12=1 · In:8 Lookback=200 · In:9 Woodies 30min hist=50 · In:10/11 Live Price on/200ms · In:12/13 Trade cmd/result paths · **In:14 TPO Yesterday Study=1** · **In:15 TPO Today Study=3** · **In:16 Initial Balance Study=6** · **In:17 Projected High-Low Study=12** · In:18 TPO Chart=0(same) · **In:19 Woodies Chart=12** · In:20 Yesterday IB Study=0(disabled) · **In:21 Continuous 24h Chart=5**.
- studies על הצ'ארט: ID:1/ID:3 TPO Value Area · ID:6 Initial Balance · ID:7/ID:9 Cumulative Delta Bars · ID:5 BidVol vs AskVol · ID:2/ID:8 Volume · ID:10 export.
**אמת ב-`sc_study/MES_AI_DataExport.cpp` (קריאה בלבד):** שכל Input נקרא וממופה לשדה הנכון (TPO yest/today, IB, ProjHiLo, Woodies@chart12, Continuous@chart5, CVD@7/9, BidAsk@5). הצלב מול ה-JSON המיוצא — כל שדה מאוכלס בערך שפוי.
**🔴 פער גרסה לבדוק:** שם ה-study בצ'ארט = "v9.4.3-chart5" אבל `V9_VERSION="v9.4.5-wc-fix"`. סביר שזה רק literal-שם מיושן (ה-export JSON version=v9.4.5 הוא הקובע), אבל **אמת חד-משמעית** איזה build טעון ורץ על צ'ארט המסחר (השווה את שם-ה-study ב-cpp מול `V9_VERSION` + version בייצוא). אם הצ'ארט מריץ v9.4.3 ישן בפועל → S4/SWI/trend עדיין על המיפוי השגוי. דווח.
**דווח mismatches → Michael מתקן ב-Sierra UI** (CC לא משנה Sierra inputs).

### עיקרון: עובדים לפי המערכות והצרכים שלהן — אמת per-system
לכל מערכת, אמת שהשדות שהיא **צורכת** מחוברים למקור הנכון ומאוכלסים:
- **S1 (day-type/opening):** opening_type · IB (In:16 Study 6) · POC/VAH/VAL (TPO In:14/15 Study 1/3) · CVD/PE (CDBV Study 7/9) · gap/ATR.
- **S2 (five-min/VSA):** נרות 5-דק' + **volume נקי per-bar ב-RTH** (זה ה-B4) · COT/AMT (Woodies In:19 Chart 12) · cumulative delta · POC.
- **S3 (footprint):** BidVol/AskVol (Study 5) · footprint deltas — **מושבת**, רק לאמת שלא שובר אחרים.
- **S4 (Woodies):** CCI_14/CCI_6 · trend_state · SWI (local-computed v9.4.5) · EMA34/LSMA25 · ProjHiLo (Woodies In:19 Chart 12 + In:17 Study 12).
לכל מערכת: השדה מגיע מ-Sierra export (SoT, לא מסונתז), מהמקור/Study/Chart הנכון, ומאוכלס בערך שפוי. דווח per-system: ✓/mismatch.

## Acceptance (בינארי + פלט גולמי)
- [ ] push ממקור-RTH ב-17:00 ET → **לא** נכתב; ברי RTH (09:30–16:00) נכתבים תקין per-bar. הדבק בדיקה. ✓/✗
- [ ] `MAX(volume) WHERE is_synthetic=0` חזר לטווח שפוי (לא 1M). count is_synthetic לפני/אחרי. ✓/✗
- [ ] VSA rolling_avg מסנן is_synthetic. ✓/✗
- [ ] הסטאדי (POC/IB/Woodies) עדיין מחוברים/עובדים — לא נשברו. ✓/✗
- [ ] **טסט אנטי-טאוטולוגי:** push ממקור-RTH מחוץ ל-RTH → לא נכתב; *"if reverted → RED because cumulative settlement bar enters v9_bars_5min"*. ✓/✗
- [ ] regression ירוק, commit אטומי (לא sc_study, לא add -A), `git log -1`. ✓/✗

## אסור לגעת
`sc_study/` · חיבור הסטאדי ל-RTH chart · `get_db` lock · `safe_writer.py` core · B2/B3 · LaunchAgent · polling.

## דוח (חלק C)
phases · Evidence(command+output) · litmus · NOT-DONE (כולל אם continuous-disable חשף תלות) · Open. **אחרי הדוח Cowork מאמת בלתי-תלוי.**
