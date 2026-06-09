# מגה‑פרומפט E2E 1/2 — אימות הצינור + אבחון/תיקון עמוד הטריידס

> פרומפט **מימוש** (משנה קוד) להדבקה בסוכן קוד עם גישה ל‑repo `mems26_web_git`.
> **קרא קודם `CLAUDE.md` ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.**
> **מחליף** את `IMPL_PROMPT_1of2/2of2` הישנים (אלה היו לפני שעלה נושא הסנכרון/הטריידס).
>
> ⚠️ זה הבסיס: חייב להיות ירוק **לפני** פרומפט 2/2 (סיווג). SHADOW בלבד · אסור
> לגעת ב‑order routing / risk / sizing · **diagnose‑first** · רגרסיה לכל תיקון.

---

## 0 · מטרה
לוודא שהצינור מסונכרן מקצה‑לקצה ולתקן את מה ששבור בעמוד הטריידס — לפני שעורמים
שינויי סיווג. שלוש משימות: (A) audit סנכרון, (B) אבחון נתיב הטרייד, (C) תיקון
באגי עמוד הטריידס (מאומתים בקוד 31/5, ראה MANIFEST).

## A · Audit סנכרון e2e (read‑only מיפוי + אימות)
מפה ואמת את החוזה בין השכבות; הדבק פלט גולמי לכל חוליה:

```
bridge (bridge/v9_streams/*) --push localhost:8000-->
backend ingest (api/v9/bars.py, bar_ingestion.py) --> DB
  (v9_bars_5min, v9_bars_footprint, v9_bars_tick_reversal, v9_trades, v9_day_type_history)
--> build_status aggregator (systems/build_status/aggregator.py + inspectors)
--> API (api/v9/status.py, /api/v9/trades, cockpit/systems-snapshot)
--> frontend polling (V9Dashboard.tsx, System1/2/4Panel, TopBar, TradeHistoryStrip)
--> Trades page (/trades → TradesView → tradeStore)
```
לכל חוליה: לאמת **חוזה** (שמות שדות/endpoint תואמים) + **טריות** (latest_ts==MAX(ts))
+ **קרדינליות** + **latency<100ms**. לזהות נתקים (שדה שמשתנה שם, mode/TZ לא תואם).
אסור לשנות intervals של polling (ראה CLAUDE.md "Frontend Polling Floors").

## B · אבחון נתיב הטרייד (diagnose‑first, לא לתקן עד אישור)
סימפטום (Michael 31/5): **יש עסקאות אך משהו בהן שגוי** (חישוב/מסנן/עדכון).
עקוב: `setup_emitter.py` → `pre_fire_validator` → gateway (`main.py:365` /
`services/trading_gateway/`) → executor → DB → `GET /api/v9/trades` → `mapTradeRow`
→ `tradeStore` → UI. מצא היכן הערך/הסטטוס משתבש. הדבק פלט גולמי. **דווח שורש לפני
תיקון** (קשר ל‑חוסמים 1.2 gateway כפול / 1.4 order routing אם רלוונטי).

## C · תיקון באגי עמוד הטריידס (MANIFEST — מאומת בקוד 31/5)

| # | קובץ | באג נוכחי | תיקון |
|---|------|-----------|--------|
| C1 | `TradesSummaryStrip.tsx:23,27` | **Scratch תמיד 0** — `scratch=withPnl.filter(pnl===0)` אבל `withPnl=pnl!=null && pnl!==0` (תנאי סותר) | חשב scratch מתוך כלל ה‑closed (`pnl===0`), לא מתוך withPnl |
| C2 | `tradeStore.ts:46` | ברירת מחדל `mode:'SHADOW'` מסתירה עסקאות במצב אחר → "ריק/שגוי" | לאמת מול ה‑mode בפועל ב‑DB; אם צריך — ברירת מחדל `ALL` או להתאים ל‑mode הפעיל |
| C3 | `tradeStore.ts:98-99` | מסנן תאריך משווה `entry_ts` (זמן/TZ) מול `YYYY-MM-DD` לקסיקלית → השמטות בגבול | נרמל ל‑date אמיתי (parse + compare by day, TZ מפורש) |
| C4 | `TradesSummaryStrip.tsx` | אין **Win Rate %** ואין aggregate **R** (pnl_r) | להוסיף WR% + R aggregate (אם pnl_r ב‑DB) |
| C5 | `lib/api.ts:163` | `limit=200` — truncation אם יש יותר | להבטיח pagination או limit מספק + אינדיקציה |

לפני כל תיקון: ודא אמפירית מול ה‑DB/UI שזה אכן הסימפטום (לא רק קריאת קוד).

## D · סדרת בדיקות — ראיית משתמש בכל מקום + טריות

### D1 · מטריצת נראות (כל מקום שהעסקה/הנתון מופיע למשתמש)
ראשית `grep` לכל הצרכנים של נתוני העסקאות, ואז אמת בכל אחד: הערך מוצג, מרונדר,
לא ריק/שגיאה, ו**זהה** בין כל המקומות (cross‑surface consistency):

| מקום (UI) | רכיב | מה לאמת |
|---|---|---|
| עמוד /trades — סיכום | `TradesSummaryStrip` | Total PnL · Wins/Losses/Scratch/Open · WR% · by‑system |
| עמוד /trades — טבלה | `TradesTable` | כל שורה: entry/exit/pnl/outcome/state/mode |
| עמוד /trades — דפוסים | `PatternPerformanceStrip` | פילוח per‑pattern |
| עמוד /trades — מודאל | `TradeDetailsModal` | רשומה בודדת `/api/v9/trades/{id}` |
| דאשבורד — סטריפ | `TradeHistoryStrip` | עסקאות אחרונות (poll 30s) |
| דאשבורד — צ'ארט | `TradeMarkerOverlay` | סמן העסקה על הגרף |
| TopBar | `TopBar` heartbeat | אינדיקטור בריאות (15s) |
| Sidebar | `PerformanceTab`/`StatsTab`/`TradeTab` | מדדי ביצוע תואמים |

**עקביות:** PnL/outcome של עסקה נתונה חייב להיות **זהה** בכל הרכיבים לעיל ומול ה‑DB.

### D2 · טריות (Recency — אסור stale)
- `GET /api/v9/trades` → `latest trade ts == MAX(ts) FROM v9_trades` (Quality+Recency).
- עסקה חדשה/סגירה מתעדכנת ב‑`TradeHistoryStrip` תוך ≤30s, ב‑`TradeMarkerOverlay`
  על הגרף, ובעמוד /trades אחרי refresh — בכל המקומות.
- `pnl_usd`/`outcome` של עסקה שנסגרה מתעדכן בכל המקומות (לא נשאר open/ישן).
- `StreamHealthPanel` מראה streams טריים (<threshold); `TopBar` health <100ms.
- **אנטי‑frozen‑tail** (CLAUDE.md §7a): על פני ברים/עסקאות **שונים** הערכים
  משתנים — לא ערך קפוא חוזר. אסור לשנות polling intervals (טבלת Polling Floors).
- WS מול poll: אם WS מחובר — עדכון מיידי; אחרת fallback ל‑poll (לאמת ששניהם
  מציגים אותו ערך, אין דריפט).

### D3 · אוטומציה
הוסף `tests/v9/e2e/test_trades_visibility_freshness.py`: (a) seed עסקה ידועה ב‑DB
test → `GET /api/v9/trades` מחזיר אותה עם אותו pnl/outcome; (b) latest_ts==MAX(ts);
(c) בדיקת עקביות החישוב מול חישוב DB ישיר. הדבק פלט גולמי.

## 1 · מנגנון הבקרה
1. **diagnose‑first** — A+B הם מיפוי/אבחון; שינוי קוד רק ב‑C ורק אחרי אימות שורש.
2. **רגרסיה לכל תיקון UI:** snapshot של סיכום הטריידס לפני/אחרי על אותו dataset;
   טסט שמוודא את ההפרש הצפוי בלבד (Scratch מתוקן, שאר המספרים ללא שינוי).
3. **smallest correct change** — בלי refactor; בלי לגעת ב‑order/gateway/risk/sizing
   ובלי intervals של polling.
4. **4 צירי UAT** ל‑`/api/v9/trades` ול‑systems‑snapshot.
5. **commit נפרד** לכל תיקון; דוח `docs/reports/PIPELINE_TRADES_E2E_<date>.md` עם
   מפת הסנכרון, שורש הטרייד, ופלט רגרסיה גולמי.

## 2 · שער
פרומפט 2/2 (סיווג S1/S2/S3) מתחיל **רק** אחרי שהצינור אומת ירוק והטריידס תקין —
על צינור מאומת בלבד עורמים את שינויי הסיווג.

## 3 · אסור
לגעת ב‑order/gateway/risk/sizing · לשנות polling intervals · לתקן לפני אבחון שורש ·
refactor רחב · לשנות לוגיקת מסחר.

> STATUS: בסיס e2e. תיקוני UI עם רגרסיה. אבחון בלבד ל‑A/B. סיווג = פרומפט 2/2.
