## רשימת-הסגירה 11.09 (מייקל 16:10) — לבצע **במלואה** אחרי 23:00 (אין ריסטארט; הפתיחה הבאה שני 16:30, ריסטארט-קדם-פתיחה 15:45). שער-הקבלה = `fwd_harness.py` על 08-03 · 08-04 · 09-09 · 10.09 · **11.09** (היום — הגולדנים מהטייפ של היום נכנסים לרשימה). כל פריט = קומיט משלו + TASK_LOG + STATUS_BOARD **באותו קומיט** + LOG חתום עם פלט גולמי (Rule 5). אפס `.env` בלי snapshot, אפס דגל-env חדש בלי שורת RULED_FLAGS עם `measured:`.

### T-320 · הפרונט — "העסקה שצריכה לירות" על הברים (מייקל 16:10) — **P0 של הלילה**
מייקל: "להוסיף על גבי הברים בפרונט עסקה שצריכה לירות — שאדע, כשזה מגיע לשם, אם נורה או לא. לא ממולא. אחד של מערכת 2 בצבע שלה ואחד של מערכת 4 בצבע שלה, ואם משהו עצר אותה אני רוצה לדעת מה."
- **KEEP/ADAPT:** `frontend/v9/src/v9/components/chart/TradeMarkerOverlay.tsx` (lightweight-charts, `SYSTEM_COLORS` מ-`types`), `v5b/LiveTradeOverlay.tsx` — אותו מנגנון-overlay, שכבה חדשה `PendingSetupOverlay.tsx`. לא לגעת ב-polling floors (CLAUDE.md).
- **Backend:** `GET /api/v9/setups/pending` (חדש, קריאה בלבד): לכל מערכת (2, 4) התבניות במצב `armed` מה-inspector/probe הקיימים (`s2_pattern_probe` — `Awaiting: <key>` + **רמת-הטריגר** במחיר: neckline / רמת-b3 / קו-ה-ZLR), עם `since_ts`, `direction`, `trigger_price`, `condition_text`; ולכל תבנית — ההחלטה האחרונה של השער מה-JSONL (`gateway_decisions.jsonl` / `/api/v9/gateway/decisions`): `outcome ∈ {live, shadow, blocked}`, `blocked_by`, `reason`, `ts`. Rule 1: אין רמת-טריגר ⇒ `trigger_price=null` (מציגים על הבר בלי מחיר), לא ממציאים.
- **Frontend:** לכל תבנית armed — סמן **חלול** (משולש/חץ בכיוון העסקה) על רמת-הטריגר בבר הנוכחי, בצבע המערכת (S2 בצבע שלה, S4 בצבע שלה). כשהמחיר מגיע והתבנית יורה ⇒ הסמן **מתמלא**; אם השער חסם ⇒ הסמן נשאר חלול עם ✕ ו-tooltip: `pattern · direction · blocked_by · reason` (למשל `dalton_intent:location zone=mid_value poc=7604.75`). היסטוריה: 3 השעות האחרונות — סמן קטן על הבר שבו הייתה החלטה (מלא=לייב, חלול=צל, ✕=חסום), hover מציג את הסיבה. `starved_by` (T-315) מוצג כ-✕ עם "starved by <pattern>".
- **golden ידני על 10.09** (טייפ-ריפליי מהליגר): 17:20 CEILING_FLIP_LONG ✕ kind · 17:30 INITIATIVE_LONG מלא (לייב) · 20:30 DOUBLE_TOP ✕ location · ZLR LONG 18:04–18:29 ✕ location. צילום-מסך ל-LOG.

### T-319b · יום Normal — יעדים וסטופ (אחרי שמייקל רואה את המספר)
- להציג למייקל את המדידה-מחדש (39e96599/1494ff8b) **בשורה אחת עם יחידות**: n ימי-Normal מתויגים (3), n כניסות-קצה, Σ$ בפועל (ברוקר) מול Σ$ סים-עם-סטופים ($5/נק' × חוזים), ומה נחסם/עבר תחת T-319b-lite היום. לא "+794".
- בנייה (רק אחרי "כן" של מייקל): T1=POC · T2=קצה-הערך הנגדי · T3=קצה-ה-IB הנגדי · runner=false · סטופ `BEYOND_IB_EDGE` — סמכותי לשורת-Normal בלבד דרך `trade_economics.resolve_targets("POC")` (`TRADE_ECONOMICS_AUTHORITY_V1` ערך חדש `normal`; לא `=1` גלובלי — T-298 של המשמרת). golden 10.09: CEILING_FLIP_LONG 17:20 ⇒ T1=7602.75; DOUBLE_TOP 20:35 ⇒ T1=7604.75, T2=7598.5.

### T-322 · שלב B (16:45–17:30) על פתיחות-מכרז — לפי מיקום, עם קצוות של דלתון
- ב-AUCTION_IN/OUT הערך של היום דק; הקצוות לשלב B = **VAH/VAL של אתמול + קצוות ה-IB-המתפתח** (טווח-הפתיחה). אותו כלל: LONG רק בקצה-התחתון, SHORT רק בקצה-העליון, אמצע חסום.
- מדידה קודם על 09-09 (AUCTION_IN) ו-10.09 (ORR→AUCTION) — כמה סטאפי-שלב-B היו עוברים/נחסמים ומה עשו. golden: 10.09 17:20 CEILING_FLIP_LONG (עוגן 7585.5 = IB-low) ⇒ admitted.

### T-323 · מפיקי-shadow — מספר לכל אחד, ואז פסיקה
`CEILING_FLIP` · `VA_FADE` · `FAILED_BREAK_VA` · `RE_ACCEPTANCE` — לכל אחד: ריפליי מאז 28.08 (מספר-ירי, Σ סימנים, Σ$-סים-עם-סטופים $5/נק', מיקום-הכניסה לפי `zone_of`), שורה אחת לכל מפיק. מייקל פוסק מפיק-מפיק. אין הדלקה בלי פסיקה.

### T-316 · kind לפי מיקום-העוגן — לכל השורות (המדידה-מחדש 1494ff8b)
להציג את הטבלה (admitted/blocked לפי תבנית×סוג-יום, Σ$ ברוקר ללייב, סימן לתאומים, המכנה). אם המספר מחזיק — לבנות כהרחבה של T-319b-lite לשורות Trend/Variation (לא רק Normal/Neutral).

### T-312 · אינדקס-החיווט — להשלים
`gen_wiring_index.py --check` (קורא-בלי-כותב = כשל; כותב-בלי-קורא = dead) · `GET /api/v9/wiring` (`populated/len/age_s`) · `wiring_guard.py` בתוך `fire_drill.py` ובשער-הבוקר · הרנס דרך main.py לשאר הרג'יסטרי (לא רק נעילת-הפתיחה). `docs/WIRING_INDEX.md` מחולל, מקושר מ-`SYSTEM_INDEX.md`.

### T-324 · EOD 11.09 — מה ירה, מה נחסם, ולמה (דוח, לא קוד)
`docs/reports/EOD_2026-09-11.md`: כל route של היום (לייב/צל/חסום, blocked_by, zone), P&L ברוקר בלבד (`sierra_activity_join.py --date 2026-09-11 --write` ואז `live_pnl.py`), נעילת-הפתיחה (locked_at/negated_at), מסירת-התווית ב-17:30 (S1 מול פורסם), והאם כלל-המיקום חסם משהו שהיה מרוויח / העביר משהו שהפסיד — עם מחירים. זה ה-`measured:` הראשון של T-319b-lite.

### T-325 · שרידים
`config_consumer_guard` — 13 שדות-YAML בלי צרכן: למחוק או לחווט, rc=0 · T-317 נשאר כבוי · T-304 (System6 target_divergence — להשתיק במקור) · T-308/T-310 — לוודא שנסגרו עם שורת-לוח.

### סדר-ביצוע
T-324 (הדוח, 20 דק') → T-320 (הפרונט) → T-319b-הצגת-המספר → T-323 → T-322 → T-316 → T-312 → T-325. ריסטארט **לא** הלילה — שני 15:45 (מתוזמן) על HEAD שההרנס ×5 אישר.
