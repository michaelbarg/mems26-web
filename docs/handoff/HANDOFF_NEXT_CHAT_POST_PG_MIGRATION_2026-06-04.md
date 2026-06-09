# Cowork Handoff — Next Chat: Post-Postgres-Migration, gating SHADOW | 2026-06-04

**אתה (Cowork chat הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC (Claude Code, על ה-Mac) מבצע; אתה כותב פרומפטים,
מצליב (Rule 5: **דרוש פקודה + פלט גולמי**, לא "confirmed"), מעדכן בורדים. **לא** שולט ב-backend/launchctl/Sierra מה-sandbox.
**לא** מגיע ל-Postgres של ה-Mac מה-sandbox → ספירות-PG חיות נשענות על raw של CC; אתה מאמת קוד/git/constraints ב-repo הממונט.

## 0 · הנחיות-על
`CLAUDE.md` (**§DB — local Postgres** עודכן; §Bridge Local-Only; §Pre-LIVE; §Source-of-Truth) · `CC_HANDOFF_CONTRACT.md` ·
זיכרון: roadmap auto-update · **אין present_files לקבצי-מעקב** · work-by-system-needs · [[project-postgres-migration]].
מקור-אמת: `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`.

## 1 · 🟢 השינוי הגדול: ה-stack המקומי הוגר ל-Postgres מקומי (root fix ל-corruption)
ה-corruption החוזר (SQLite, `v9_bars_footprint`, page 76860) נסגר **מהשורש** ע"י הגירה ל-`postgresql://localhost/mems26`.
השורש שאומת: `POST /api/v9/bars/footprint` (`bars.py:415`) כתיבת-ORM לא-מסורלת + `FOOTPRINT_DISABLED` שלא מיוצא בכלל.
Postgres MVCC מבטל את כל מחלקת ה-corruption. נתוני-עבר היו מתכלים → התחלה נקייה.
**אומת GO (Cowork בלתי-תלוי):** 6 phases `3fbb71f`→`28dda30` + constraint fix `2742e4c`; soak 21,807 דחיפות/0 שגיאות/0 deadlocks;
כל יעדי ON CONFLICT עם UNIQUE תואם; green tests `f6fabac` (0 שינויי-פרודקשן, אומת ב-git).

## 2a · ✅ split-brain נסגר ואומת → מחלקת ה-DB סגורה (DB-side GO)
split-brain (כתיבות `db_path` → SQLite) נסגר (CC `69744bb`) ואומת בלתי-תלוי (Cowork, code+git): 0 `db_path=self.db_path` בפרודקשן;
`_get_engine` מתעלם מ-db_path על PG + warning; CC raw פר-מערכת COUNT עולה ב-PG (TPO/day_type_state/reversal/tpo_history), SQLite mtime לא זז.
**כל מחלקת ה-DB סגורה ומאומתת:** reads+writes על PG, constraints, tests (488, 3 pre-existing woodies), axis4/6b, split-brain.
**הצעד הבא אינו-DB:** תנאים לפתיחת SHADOW משמעותי — (a) שירותים על PG ב-RTH + feed (frozen-tail watch) · (b) flags ON · (c) S2 firing (D-RVX variant=Michael) · (d) S1 day-type inputs (bar.atr=None). S3=MUTE✓ S4✓.

## 2b · ✅ ציר 4 + 6b — נסגרו ואומתו (Cowork)
`d635b1c` axis4 (history_loader RTH gate → `MAX(vol) WHERE is_synthetic=0 = 83,033`) · `20f9df7` axis6b (woodies ts unix→ISO + הסרת db_path → נשמר ל-PG). היו חוסמי-SHADOW; **נסגרו**. (המקור שלהם הוביל לגילוי 2a.)

## 2 · (היסטוריה) תיקוני-האיכות שזוהו ב-audit
פרומפט מוכן: `docs/handoff/CC_PROMPT_FIX_AXIS4_AXIS6B_PRE_SHADOW_2026-06-03.md`.
- **ציר 4:** `history_loader.py:336` עושה `INSERT OR IGNORE INTO v9_bars_5min` **בלי גייט-RTH** → ברים מנופחים (vol 840K) עם
  `is_synthetic=0` מזהמים VSA/כיול (אותה מחלקת באג כמו B4). תיקון: החל `_is_within_rth` (קיים ב-bars.py) גם ב-loader.
- **ציר 6b:** `v9_bars_5min_woodies.ts` = `DateTime(timezone=True)`, אבל `woodies_system.py:548` שולח `bar_ts` כ-unix-int → PG דוחה
  → **ברי S4-woodies לא נשמרים**. (חשף ש-"woodies writes work" מ-`2742e4c` נבדק עם ts לא-מייצג.) תיקון: המר ל-timestamp (TZ מפורש).
- **❌ SHADOW חסום** עד ששני אלה מתוקנים + הצלבת-Cowork (raw: `MAX(volume) WHERE is_synthetic=0` שפוי; woodies COUNT עולה).

## 3 · פרומפטים מוכנים נוספים (לפי תיעדוף Michael)
- **עמוד Trades — עיצוב-מחדש:** `docs/handoff/AGENT_PROMPT_TRADES_PAGE_REDESIGN_2026-06-03.md` — סוכן read-only, **לא מממש**;
  חוקר מודל-עסקאות + UI + checklist, מעצב להסקת-מסקנות (פר-מערכת/pattern/day-type, התפלגות T1–T3, MAE/MFE, equity, drill-down);
  תוצר: `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md` + mockup + gap-list. (CC דחה את ציר 2 ב-audit — זה מחליף.)
- **Config externalization (Option A · YAML):** `docs/handoff/CC_PROMPT_CONFIG_YAML_AUTH_TARGETS_2026-06-03.md` — מהלך **מכני**
  (auth_table + targets → YAML, **ערכים זהים**, round-trip equality, fallback, תקרות). רץ **אחרי** התיקונים/audit. נותן כיול בלי redeploy.
- **Build-Status — לדיון עם Michael:** כבר קיים `BuildTreeView` (route `/build`) + `BUILD_STATUS_REDESIGN_MOCKUP.html`.
  השאלה: להמשיך לפתח את הקיים או עיצוב טרי. **לא להתחיל בלי הכרעת Michael.**
- **Stop-anchor design (פתוח, ממתין ל-go של Michael):** Michael רוצה לעגן stop ל-VAH/POC/daily-H-L/swing-low-של-N-ברים.
  ממצא: `adaptive_stop.py` (D-091) **כבר** עם שכבת structural-anchor (A); כל הרמות זמינות (`/api/v9/key_levels`). הרחבה = לוגיקת-מסחר
  → **strategic-stop**, משתלב עם ה-config. אם Michael מאשר — להכין `docs/plans/` design proposal ל-"stop anchor modes".

## 4 · אחרי ש-SHADOW נפתח (מתוך ROADMAP, שלב 5+)
SHADOW soak ≥10 ימי RTH + ≥20 עסקאות. **תנאי-מקדים לדאטה משמעותי (החלטות Michael פתוחות):** S2 לא יורה (ווריאציית D-RVX) ·
S1 day-type inputs מתים (`bar.atr`=None). S3=MUTE ✓, S4=יורה ✓. אז Pipeline 5 (חוסם-LIVE, executors=stubs) → DEMO → LIVE (P-L0..L1).

## 5 · Invariants קשיחים
**local Postgres בלבד (localhost) · ❌ לעולם לא Render/Upstash/prod-PG** · Bridge Local-Only (push רק ל-localhost:8000) ·
get_db בלי lock · No silent failures · אל תיגע sc_study/polling-floors/risk-logic בלי Michael · CLAUDE.md §DB עכשיו Postgres-era ·
Rule 5 (raw, לא rubber-stamp; ההגירה לימדה שוב: בדיקה לא-מייצגת = over-claim) · אין present_files לקבצי-מעקב.

## 6 · הצעד הראשון בצ'אט הבא
1. כש-CC מחזיר תיקון ציר 4+6b → **הצלב raw** (vol שפוי WHERE is_synthetic=0; woodies COUNT עולה אחרי בר RTH). אם נקי → SHADOW=GO מצד ה-DB.
2. סקור תוצר סוכן-עיצוב-Trades (כשיחזור). 3. דון עם Michael על Build-Status + stop-anchor. 4. הרץ config-YAML אחרי התיקונים.
עדכן STATUS_BOARD/ROADMAP פר-שער (finding+fix+verification, Rule 5).
