# Cowork Handoff — Next Chat: DB Corruption Root + Postgres Long-Term | 2026-06-03

**אתה (Cowork chat הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC (Claude Code, על ה-Mac) מבצע; אתה כותב פרומפטים, מצליב (חלק D של החוזה), מעדכן בורדים. **לא** שולט ב-backend/launchctl/Sierra של ה-Mac מה-sandbox. אין `sqlite3` CLI — `python3`. DB ב-`data/mems26_local.db`.

## 0 · הנחיות-על
`CLAUDE.md` (§DB Write-Safety, §Pre-LIVE, §Source-of-Truth, **§Bridge Local-Only**) · `docs/handoff/CC_HANDOFF_CONTRACT.md` · זיכרון: roadmap auto-update · אין present_files לקבצי-מעקב · work-by-system-needs · **don't re-add get_db lock** (deadlock) · integrity רק backend-כבוי · Sierra=SoT.

## 1 · 🔴 הבעיה המרכזית: DB corruption חזר (אחרי ש"אומת")
**אומת אמיתי (Cowork ~12:48 ET):** 3 קריאות → אותו עמוד `Page 76860 btreeInitPage` → `malformed`. **זו הסיבה ל"אין נרות"** (קריאות נכשלות).
**השורש האמיתי (CC אישר):** סריאליזציה **opt-in** + **~20 כותבי-ORM לא-מסורלים** עדיין כותבים דרך `get_db()`+`db.commit()` בלי lock: `trades.py`, `trade_manager/manager.py` (`db.flush`×6 — קריטי-לסיכון!), `trading_gateway.py`, `woodies/api.py`, `day_type/api.py`, `five_min_system.py:957`, `woodies_system.py:651`. **Phase 1 כיסה רק `bars.py`.** כל סבב סוגר חלק → corruption חוזר מהבא. זו תבנית.

## 2 · פתרון מיידי (P0) — לקבל DB נקי, בלי band-aid עיוור
פרומפט קיים: `docs/handoff/CC_PROMPT_DB_CORRUPTION_RECURRED_2026-06-03.md`. **diagnose-first (read-only ~20 דק'):**
- האם **כל** חיבור (ORM engine + כל raw) באמת WAL + busy_timeout? יש חיבור **משותף בין threads** (`check_same_thread=False`, `footprint_system:80`)?
  - אם WAL לא-אחיד / חיבור-משותף → המנגנון, תיקון **קטן** (WAL+busy_timeout אחיד, לבטל shared conn). כותבי-ORM תחת WAL אחיד **בטוחים** → לא צריך להמיר 20.
  - אם הכל WAL וזה עדיין משחית → מקביליות אמיתית → **Single-Writer-Queue** (תהליכון-כתיבה אחד, חיבור אחד, enqueue אסינכרוני — אין deadlock; מכסה את כל ה-20 בלי לשכתב כל אחד).
- **+ lint-guard לאכיפה** (אוסר `sqlite3.connect`-כותב / `db.commit` מחוץ ל-writer) → כותב #21 לא יכול להשתחל.
- recovery: rebuild נקי (**לא** מ-`.corrupt`/`.bad2`/`.bak`) → backend-down integrity=ok.
- **❌ לא לאסוף SHADOW עד שהאכיפה המבנית בפנים** — אחרת בונים DB מחדש כל יום.

## 3 · 🎯 הפתרון לטווח-ארוך: הגירת ה-stack המקומי ל-Postgres מקומי
**הקוד כבר תומך (D-069):** `session.py` — "local=SQLite, production=DATABASE_URL", מטפל ב-`postgres://`→`postgresql://`. ה-ORM (כולל 20 הכותבים) **"פשוט יעבוד"** מול Postgres — Postgres מטפל במקביליות → **כל מחלקת ה-corruption נעלמת**, ואפשר **למחוק safe_writer + הכותבים הגולמיים**.
- צעדים: להריץ **Postgres מקומי** (`localhost`), `DATABASE_URL=postgresql://localhost/mems26`, הגירת schema (SQLAlchemy/Alembic) + נתונים, להחליף raw `sqlite3.connect` בכתיבות-ORM.
- ⚠️ Postgres קפדן בטיפוסים → עלול לחשוף באגים סמויים (טוב). צריך אימות LIVE-readiness (latency/יציבות).

## 4 · ⚠️ פרודקשן/ענן — גרסה אחרת, לא לגעת/לשבור!
**Render** (`mems26-web.onrender.com`) + **Postgres** (DATABASE_URL בענן) + **Upstash** (Redis בענן: live_price ticks, pub/sub, history-resume, audit). **זו פריסה נפרדת/ישנה.** כללים:
- ה-**stack המקומי** (המסחר החי, SQLite) הוא מה שמתקנים — **נשאר מקומי** (Bridge Local-Only: הגשר דוחף **רק** ל-localhost, **לעולם לא** ל-onrender).
- Postgres-מקומי (אם נלך) = instance **מקומי נפרד**, **לעולם לא** ה-Postgres של Render.
- **אל תיגע** ב-Render/Upstash/prod-Postgres.
- ⚠️ ממצא: הגשר דוחף `live_price` ל-**Upstash (ענן)** — תלות-ענן ב-stack המקומי + latency; רלוונטי ל-Fix 3 (trade-mgmt-on-live-price). לשקול local redis ל-real-time.

## 5 · threads פתוחים נוספים
- **Fix 3+4 (חוסם-LIVE, #12):** ניהול-עסקה על live_price=primary (active default-ON, call-time flag) + bad-tick guard + live_price-staleness guard; Fix 4 stale-bar guard 10min RTH-scoped. פרומפט: `CC_PROMPT_TRADE_MGMT_LIVEPRICE_FIX3_FIX4_2026-06-03.md`. (אישור Michael: active-from-start.)
- **✅ נסגר:** B4 (RTH-only `0ece0fa`) · sc_study v9.4.5 (`816dd1a`) · feed (Reload Study; frozen-tail חזר→מעקב-רגרסיה).
- **ניקוי:** Phase 3 journals · D1 דגלים · woodies ts=2025-01-01 · טבלה רציפה 24h.

## 6 · Task list (#1-#13)
DONE: #1 B4 · #2 SHADOW-prompt-V2 · #10 feed. P0: **#13 corruption חזר** (+#6 כותבי-ORM = חלק ממנו). חוסם-LIVE: #12 trade-mgmt. ניקוי: #7/#8/#9/#11.

## 7 · פרומפטים שנוצרו + מקורות
`CC_PROMPT_DB_CORRUPTION_RECURRED` · `CC_PROMPT_TRADE_MGMT_LIVEPRICE_FIX3_FIX4` · `CC_PROMPT_SHADOW_DAY_OPS_V2` · `CC_PROMPT_B4_FIX` · `CONSULT_TRADE_MGMT_LIVEPRICE` · `HANDOFF_CONTINUATION_2026-06-03_COWORK`. מקור-אמת: `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`.

## 8 · הצעד הראשון בצ'אט הבא
1. backend-down → integrity אוטוריטטיבי (לאשר corruption + לזהות טבלה).
2. CC: אינוונטרי כל ה-writers + אבחון WAL/threading (read-only).
3. לפי האבחון: WAL-fix קטן **או** Single-Writer-Queue + lint-guard. recovery.
4. החלטת Michael: האם להגר ה-stack המקומי ל-Postgres מקומי כיעד (D-069 כבר תומך) — מסיים את הסאגה. **בלי לגעת בענן.**
