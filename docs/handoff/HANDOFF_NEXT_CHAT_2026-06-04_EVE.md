# Cowork Handoff — Next Chat (2026-06-04 eve) — post-firing-fixes, 2 designs awaiting cross-check

**אתה (Cowork chat הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC (Claude Code, על ה-Mac) מבצע; אתה כותב פרומפטים,
מצליב (**Rule 5: פקודה + פלט גולמי**, לא "confirmed"), מעדכן בורדים. **לא** שולט ב-backend/launchctl/Sierra/RTH מה-sandbox.
**לא** מגיע ל-Postgres של ה-Mac → ספירות-PG חיות נשענות על raw של CC; אתה מאמת **קוד/git/constraints** ב-repo הממונט.
מצטבר חשוב מהסשן: CC נטה ל-over-claim → **תמיד הצלב** (תפסנו: woodies upsert, split-brain, אבחון-על-DB-שגוי, grep שגוי). 3 המסירות האחרונות עברו נקי.

## 0 · הנחיות-על
`CLAUDE.md` (**§DB עכשיו Postgres**; §Bridge Local-Only; §Pre-LIVE; §Source-of-Truth) · `CC_HANDOFF_CONTRACT.md` ·
זיכרון: [[project-postgres-migration]] · [[project-config-tunable-stop-exits-contracts]] · roadmap auto-update · **אין present_files לקבצי-מעקב**.
מקור-אמת: `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (סודר: "מה לבצע" P1–P5 ב-banner; לוג 1/1b/1c מקופל).

## 1 · 🟢 הצעד המיידי: הצלבת תוצרי 2 המעצבים (סיימו, ממתינים)
שני סוכני-עיצוב (read-only, **לא מימוש**) סיימו וממתינים להצלבת-Cowork מול source-of-truth:
- **Trades redesign** — prompt: `AGENT_PROMPT_TRADES_PAGE_REDESIGN_2026-06-03.md`. תוצר צפוי: `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md` + mockup + gap-list.
- **Build-Status redesign** — prompt: `DESIGNER_PROMPT_BUILD_STATUS_REDESIGN_2026-06-04.md`. תוצר צפוי: `docs/plans/BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md` + mockup + gap-list.
**הצלב:** (a) לא סינתזו שדות שה-backend לא פולט (source-of-truth Rule 1 — חסר="ממתין ל-backend"); (b) ה-gap-list מתיישר עם `CC_PROMPT_P0_2_EXPOSE_TARGETS_STOP` (אותם שדות stop/r_t1/targets); (c) המלצת-cull ל-Build-Status תואמת מה שבאמת בשימוש (זהירות: ה-JS ב-ROADMAP ממספר לפי מיקום-סעיף).

## 2 · ✅ מה נסגר ואומת בסשן (DB + firing — הכל אומת Cowork)
- **DB מלא על Postgres:** migration 6 phases (`3fbb71f`→`28dda30`) + constraints (`2742e4c`) + tests (`f6fabac`) + axis4/6b (`d635b1c`/`20f9df7`) + **split-brain** (`69744bb`, db_path→SQLite תוקן). כל מחלקת ה-corruption חוסלה.
- **S1/S2 firing:** S1 atr-fallback (`9cac12f`), D-090/D-096 observer (`d785b2c`), S2 VSA enable (`5343755`) + D-096 doc (`48f9bdd`). אומת.
- **frozen-tail watchdog** (`11e82e9`, detect+alert, לא נוגע sc_study). **P0-2** חשיפת stop/r_t1 ל-build-status (`8eb5747`, exposure-only).

## 3 · 🟡 in-flight / ממתין
- **config-YAML מורחב** (`CC_PROMPT_CONFIG_YAML_AUTH_TARGETS` — הורחב 4/6 ל-stop+exits+contracts + `min_r_t1_threshold`) — **נשלח ל-CC** (לאמת round-trip equality + 0 שינוי-ערכים כשיחזור).
- **P1 bring-up ב-RTH** (Mac-side) — צ'ק-ליסט `docs/runbooks/RTH_BRINGUP_SHADOW_CHECKLIST_2026-06-04.md`. מבחן-אמת: ירי S2 חי + consistency של P0-2 (stop מוצג == stop חי). **השער לפתיחת SHADOW soak.**

## 4 · ⏳ החלטות פתוחות של Michael (חוסמות המשך)
- **Build-Status cull:** איפה Build חי (/build בלבד מול דאשבורד) + ReadinessHeader keep/drop (תוצר המעצב יעזור).
- **stop-anchor:** go + אילו anchors (VAH/POC/daily/swing) + כללים → design proposal (נשען על P0-2).
- **build-status drift:** S3 firing מול observer · Killzone 8 מול 11 אזורים.
- **post-soak (תלוי-דאטה):** נעילת k · כיבוי תבניות חלשות (GB100/ZLR/VEGAS).

## 5 · residuals פתוחים (לא-חוסמי-SHADOW, לפני LIVE)
P0-2: #2 תבניות-chart S2 (preview R-based ≠ pattern-measure של המנוע) · #3 `min_r_t1_threshold=0.0` (נכלל ב-config-YAML) · frontend טרם מרנדר stage `targets_stop`.
S1: re-eval trigger#1 (extreme move) חלקי — `move_30=None` (`state_machine.py:783`, צריך deque(maxlen=6)). ניקוי PG: shim · main.py SQLite fallback · 3 טסטי woodies HFE/B3 (pre-existing).

## 6 · Invariants קשיחים
**local Postgres בלבד (localhost) · ❌ לעולם לא Render/Upstash/prod-PG** · Bridge Local-Only · get_db בלי lock · No silent failures ·
אל תיגע sc_study/DLL/risk-VALUES/polling-floors בלי Michael (חשיפה≠שינוי-ערך) · SHADOW=paper · Rule 5 · אין present_files לקבצי-מעקב.

## 7 · הצעד הראשון בצ'אט הבא
1. **הצלב את 2 תוצרי המעצבים** (§1) → דווח ל-Michael + עדכן ROADMAP/STATUS_BOARD.
2. כש-CC מחזיר config-YAML → הצלב round-trip equality (0 שינוי-ערכים).
3. כשיש RTH → P1 bring-up + אימות S2/consistency (§3).
4. סגירת החלטות §4 לפי Michael. עדכן בורדים פר-שלב (Rule 5).
