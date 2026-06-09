# Cowork Handoff — Next Chat (2026-06-05) — post live-debug, S2 phantom-trade open

**אתה (Cowork chat הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC מבצע (על ה-Mac); אתה כותב פרומפטים, מצליב (**Rule 5: פקודה+פלט גולמי**, לא "confirmed"), מעדכן בורדים. **לא** שולט ב-backend/launchctl/Sierra מה-sandbox — אבל **כן** יכול לקרוא קוד/git ב-repo הממונט, ולשלוף דאטה-חיה דרך **Chrome→`http://localhost:8000`** (ה-API של ה-backend) ✅. מצטבר חשוב: CC נטה ל-over-claim → **תמיד הצלב** (תפסנו בסשן: `ingest_bar` no-op מת, "don't fix" שגוי, litmus שבודק helper לא detector).

## 0 · מקור-אמת והנחיות-על
`CLAUDE.md` (§DB=Postgres · §Bridge Local-Only · §Pre-LIVE · §Source-of-Truth · §Sierra). **Sierra=מקור-אמת.** `CC_HANDOFF_CONTRACT.md`. בורדים: `docs/plans/STATUS_BOARD.md` (source-of-record) + `ROADMAP_TO_LIVE.html`. **בּאג-לוג הסשן: `docs/reports/BUG_LOG_2026-06-04_05.md`.** זיכרון: [[project-postgres-migration]] · [[project-stop-target-placement-table]] · [[project-config-tunable-stop-exits-contracts]] · אין present_files לקבצי-מעקב.

## 1 · 🔴 הצעד המיידי — B-13: תקרית S2 (trading-safety, החמור)
S2 ירה 2 עסקאות (shadow) `DOUBLE_TOP_AA_SHORT` על **מחיר פנטומי 7341/7365** (לא קיים בשוק; טווח אמיתי 7548–7630), יעדים אבסורדיים, ב-17:18–17:20 ET (אחרי סגירה). שורש: בר פגום ל-pattern-engine + 3 שכבות שכשלו (אין price-sanity · אין RTH-gate בירי [`risk_checks:38` SHADOW עוקף] · entry_ts שעון-שרת +03:00 לא ET). **ממתין להכרעת Michael** ל-3 guardrails (RTH-gate-כל-mode · price-sanity-band · TZ-fix) + חקירת מקור-הבר הפגום (bridge/S2 log מאותו רגע / האם שורות-DB ישנות). **trading-logic → strategic-stop.** שליפת-עדות: Chrome→`/api/v9/trades/recent` (sys=2).

## 2 · 🔴 B-11 — bridge_inspector שובר על PG (פרומפט מוכן)
`bridge_inspector.py:82,204` `ORDER BY rowid DESC` (SQLite-only) → PG זורק → כל הזרמים `no_data`/Bridge "OFFLINE" **שקרי** (המערכת עובדת, הדאשבורד משקר). **תיקון: `ORDER BY rowid DESC` → `ORDER BY {ts_col} DESC`** (2 מקומות) + regression. שלח ל-CC.

## 3 · 🟡 סריקת SQLite-isms לפני LIVE (מחלקת-על)
3 באגים נפרדים השבוע מאותה מחלקה (datetime↔str · `rowid` · `str(ts)`-dedup). **המלצה: סריקה ייעודית** של נתיבי-קריאה ל-PG: `rowid`, הנחת-string על ts, `PRAGMA`, `datetime('now')`, `INSERT OR REPLACE` shim.

## 4 · פרומפטים כתובים שטרם בוצעו (ב-`docs/handoff/`)
`CC_PROMPT_BUILD_STATUS_CULL_2026-06-04` (cull=אופציה A מאושר) · `CC_PROMPT_S1_POC_REEVAL_2026-06-04` (flag OFF) · `CC_PROMPT_CONTINUOUS_5MIN_CHART` (בוצע ב-`1896a97`; נותר **תצוגה**: RTH פר-סשן כמו Sierra chart#5, לא overnight צף) · `CC_PROMPT_FIX_5MIN_CVD_DUPLICATION` (בוצע ב-`355a54b`). **לפני שליחה — הצלב שלא בוצע כבר (CC עשה כמה מהם).**

## 5 · החלטות פתוחות של Michael (תלויות-soak/דחויות)
D-RVX (וריאציית S2 מ-soak; ברירת-מחדל A_VSA) · הגדרת-סטופים (טבלה מוכנה, [[project-stop-target-placement-table]]; לבנות `stop_anchors.yaml`+2 עוגנים+loader) · S1-POC enable+ספים (אחרי שCC יבנה) · #6 residuals + #5 post-soak = לפני LIVE.

## 6 · מצב חי (2026-06-05 בוקר)
גשר רץ ודוחף (`/tmp/bridge.err.log` push#50/errors≈0 — **לא** bridge.log שריק). day_type מסווג (PG-fix `3820f3b` עבד). S2 `run on`/10-armed. RTH closed עד 09:30 ET.

## 7 · Invariants
local Postgres בלבד · Bridge Local-Only · Sierra=source-of-truth (לא לסנתז) · אל תיגע sc_study/DLL/risk-VALUES בלי Michael · Rule 5 · הצלב כל טענת-CC מול קוד/git/DB · אין present_files לקבצי-מעקב.

## 8 · הצעד הראשון בצ'אט הבא
1. **B-13** — סכם ל-Michael את 3 ה-guardrails להכרעה; כשמאשר → פרומפט CC (diagnose-first: מקור-הבר הפגום קודם). 
2. **B-11** — שלח את פרומפט ה-rowid fix.
3. כש-CC מחזיר — הצלב (Chrome→API + קוד+git). עדכן בורדים פר-שלב (Rule 5).
