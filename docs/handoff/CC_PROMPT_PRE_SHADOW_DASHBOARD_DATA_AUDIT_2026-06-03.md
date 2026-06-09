# CC PROMPT — Pre-SHADOW Dashboard + Data-Integrity Audit (6 צירים, שער-קדם-SHADOW) · 2026-06-03

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** רץ אחרי ירוק-הטסטים (`CC_PROMPT_PG_GREEN_TESTS`), לפני פתיחת SHADOW.
**אישור Michael 2026-06-03.** מטרה: לוודא שאחרי הגירת Postgres כל משטחי-הדאשבורד והנתונים מחוברים נכון ומדויקים.

## עיקרון-על
**Verification-first.** רוב זה audit read-only. תיקוני-תצוגה/wiring — בצע. **כל אי-דיוק בחישוב trading (stop/T1–T5)
או ב-auth-matrix = שינוי risk-surface → strategic-stop ל-Michael, לא לתקן בשקט.** אסור silent-failure: כל פאנל
שמחזיר ריק/stale חייב להיחשף, לא להיבלע.

## הצירים

### 1 · כל רכיבי הדאשבורד מחוברים נכון
לכל פאנל: מאיזה endpoint הוא מושך, האם ה-endpoint עבר ל-PG (Phase 2), והאם מתקבל נתון חי (לא ריק/stale).
אמת מול תדרי-ה-polling הנעולים ב-CLAUDE.md (אל תשנה אותם). הדבק טבלה: panel → endpoint → live? (✓/✗) → latency.

### 2 · עמוד Trades מסודר מחדש
בנה על `docs/reports/TRADES_PAGE_CHECKLIST_2026-05-31.md` + `CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND_2026-05-31.md`.
משטחים: `frontend/.../components/trades/*` (TradesView/TradesTable/TradeFilters/SelectedTradePanel/…).
תקן את הבאגים המתועדים: Scratch תמיד 0 · mode=SHADOW default · מסנן-תאריך לקסיקלי · חסר WR%+R. אמת קצה-לקצה מול `v9_trades` ב-PG.

### 3 · עמוד Build-Status מסודר
`frontend/.../components/build_status/BuildStatusTab.tsx` + `backend/v9/systems/build_status/*`
(aggregator, s2/woodies/day_type/footprint/bridge inspectors). אמת שכל inspector קורא מ-PG (לא raw sqlite),
שכל מערכת (S1–S4) מציגה armed/blocked/fired אמיתי, ושאין פאנל-מת. הדבק מצב פר-מערכת.

### 4 · טבלת הנרות עובדת
`backend/v9/api/v9/bars_5min_history.py` + `frontend/.../chart/v5b/ChartV5b.tsx`.
אמת **4 צירי UAT**: Quality (אין ברים מנופחים/synthetic דולפים, גייט B4 מחזיק) · Recency (`endpoint.latest_ts == MAX(ts)` ב-PG) ·
Cardinality (`len(rows) == limit`, אין 20 הברים החדשים שנחתכים — תקלת P27.5a) · Latency (<סף). הדבק raw של 4 הצירים.

### 5 · Auth-Matrix
`backend/v9/systems/build_status/auth_table_lookup.py` + `backend/v9/systems/five_min/auth_table_v1.py` +
`CC_PROMPT_AUTH_TABLE_V2_MAXCONTRACTS_2026-05-31.md`. אמת שהמטריצה (day-type × quality-tier → max contracts) נטענת,
מחזירה את הערך הצפוי לכל שילוב, ומוזנת לנתיב ה-sizing. **אם ערך/מיפוי שגוי = risk-surface → strategic-stop, אל תתקן בשקט.**
הדבק טבלת lookup צפוי-מול-בפועל.

### 6 · חישוב stop + T1–T5
`backend/v9/services/trade_manager/rules/day_type_targets.py` + `bar_level_detector.py` + `manager.py` + `gateway/trade_management.py`.
אמת לכל day-type: כיצד נגזרים מחיר ה-stop ו-T1/T2/T3/T4/T5 (מקור הרמות, יחידות, TZ של ה-ts לזיהוי פגיעה).
ודא שבאג ה-TZ של `_parse_ts` (תוקן `457cd1c`) לא חזר ב-PG (DateTime עם tz). **חשב ידנית על עסקה לדוגמה והשווה לערכים שהמערכת מייצרת.**
**כל אי-התאמה = strategic-stop ל-Michael** (לוגיקת-מסחר/סיכון). הדבק חישוב-ידני מול ערכי-מערכת.

## Acceptance (✓/✗ + raw, פר-ציר)
- [ ] 1 טבלת panel→endpoint→live→latency. [ ] 2 trades-page באגים סגורים + E2E מול PG. [ ] 3 build-status פר-מערכת מ-PG.
- [ ] 4 נרות: 4 צירי UAT raw. [ ] 5 auth-matrix lookup צפוי==בפועל. [ ] 6 stop+T1–T5 חישוב-ידני==מערכת.
- [ ] סעיף NOT-DONE + רשימת strategic-stops (כל אי-דיוק trading/risk שנמצא, **לא** תוקן). commit · `git log`.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · אל תשנה polling floors / sc_study / risk-logic בלי Michael · No silent failures · Cowork מאמת בלתי-תלוי. שער: SHADOW נפתח רק אחרי ציר 1–4 ✓ ושאין strategic-stop פתוח על ציר 5/6.
