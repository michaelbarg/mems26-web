# CC — מגה: הכנה+הרצה למסחר היום + סגירת כל הפתוחים (Rule 5, self-verify) · 2026-06-09

**קרא קודם דרך ה-index:** `CLAUDE.md` (§Pre-LIVE · §Standing Decisions · §Index · §Frontend Polling Floors) ·
`SYSTEM_INDEX.md` · `docs/reports/OPEN_ISSUES_REGISTER_2026-06-09.md` (הרשימה המלאה) ·
`CC_FIX_FAKE_TESTS_AND_REPLAY_2026-06-09.md` · `CC_HANDOFF_CONTRACT.md`.

**איך לעבוד:** כל פריט בתבנית **אבחן→בצע→אמת-את-עצמך (פקודה+פלט גולמי)→done**. אל תכריז
"עובד" בלי raw. אתר קבצים דרך ה-index, לא grep עיוור.

**מעקות קבועים (אסור לחרוג):**
- אל תדליק/תשחזר אף דגל default-off: `S2_CHOPPINESS_GATE`·`LAYER0_CHOP_GATE`·`S2_REQUIRE_COT_AMT`.
- **S3/footprint — לא נוגעים ולא משתמשים עד post-LIVE** (Michael 2026-06-09). I-11 לא חוסם. scope = S2+S4.
- כל trading-logic = STRATEGIC-STOP מתועד. **A2 ו-B3 כבר אושרו ע"י Michael** (פרטים למטה).

═══════════════════════════════════════════════════════════
## 🟢 שער קדם-פתיחה (≤20 דק' · חובה לעבור כדי לסחור היום · SHADOW)
═══════════════════════════════════════════════════════════
**זה הקו-האדום למסחר. בצע קודם. אל תעשה שינויי-fire-path מסוכנים בשלב הזה — רק אימות+תיקון-באג-ההצגה.**

**G1 · שירותים חיים** — בדוק listeners קיימים על `127.0.0.1:3000`/`:8000` (אל תכפיל). הפעל/אתחל
לפי `scripts/start_all.sh`. אמת: backend health 200 · bridge push ל-localhost · frontend :3000 200.
הדבק raw.

**G2 · 7 הדגלים שהוגדרו אתמול = ON ב-runtime** — אמת בתהליך-הרץ (לא רק `.env`):
`S2_ATR_RELATIVE`·`S3_RELATIVE`·`S1_CVD_OPENING`·`S1_IB_WIDTH_ATR`·`S1_DAYTYPE_STAGING`·`S2_VSA_VOLUME`·`S3_MUTE`.
הדבק את ערכי-ה-runtime. (אם דגל חסר — תקן ב-plist/הפעלה, לא ב-cloud.)

**G3 · זרמי S2+S4 חיים + verdict לא-BLOCKED** — `build/pattern-status`: ודא `bars_5min`/`woodies_5min`
FRESH ו-verdict לא נחסם מהם. tick_reversal/tpo non-critical (`a8cb1fb`). footprint = S3 → התעלם.

**G4 · A1+E1 — ירי→`v9_trades`→תצוגת Trades עובד (הבאג שפתח הכל)**
אבחון-שרשרת (אל תניח את הסיבה): זיהוי → persist `v9_five_min_setups` (#2/#4, `23163d9`) →
gateway/trade_manager → `v9_trades` → **עמוד Trades בפרונט**. הרץ `scripts/replay_day.py` (06-08) או
חכה לירי-חי, והדבק לכל חוליה:
- `SELECT count(*),max(ts) FROM v9_five_min_setups WHERE ts::date=CURRENT_DATE;`
- לוג setup_emitter→gateway: emitted/approved/vetoed (+סיבה).
- `SELECT count(*),firing_system,max(ts) FROM v9_trades WHERE ts::date=CURRENT_DATE GROUP BY firing_system;`
- **עמוד Trades:** האם השורות מוצגות? אם נכתבו ב-DB אך לא מוצגות → **באג-frontend בעמוד Trades** → תקן.
מצא את החוליה השבורה, תקן, ואמת ב-DB **וגם** בתצוגה. תוצר ביניים: `docs/reports/A1_FIRE_TO_TRADES_VERIFY_2026-06-09.txt`.

**G5 · A3 — סטופים מהטבלה** — ודא ש-`compute_stop`/`compute_stop_v2` קוראים את הטבלה
(`config/*.yaml`, per-pattern×day-type) לכל תבנית. בדוק שה-t1 הקשיח (4 ticks) שתיקון #1 הוסיף
ל-DLL-fallback תואם את הטבלה ולא דורס. אם דורס → STRATEGIC-STOP.

> **בתום השער:** אם G1-G5 ירוקים → המערכת מוכנה ל-SHADOW. דווח GO/NO-GO ל-Michael **לפני** שתמשיך.

═══════════════════════════════════════════════════════════
## 🟡 סשן (במהלך/אחרי הפתיחה · כל פריט עם verify-gate · STRATEGIC-STOP על trading-logic)
═══════════════════════════════════════════════════════════
**A2 · Double-Top dedup — ✅ אושר (אופציה 1).** הוסף `last_fire_pattern_id+ts` ל-FiveMinSystem;
דלג על אותה תבנית+כיוון תוך N ברים (N=lookback: Double/H&S 30, Flag 20). הגלאים נשארים stateless.
טסט RED-on-revert אמיתי (קורא לנתיב). בחי זה מונע ירי-רפאים (43→distinct).

**B3 · CCI מ-Sierra export — ✅ אושר.** השתמש ב-`cci_14`/`cci_6_tcci` שמגיעים ב-export (source-of-truth)
במקום חישוב-פייתון. fallback רק אם בר חסר, ואז `source="derived"` ביושר (Rule 1) — לא להעמיד פנים
שזה Sierra. מבטל את פער-ה-CCI ומייתר את ה-DLL-fallback. אבחן-קודם (הדבק את הפער על אותו חלון).

**B1 · טסט #3 — שכתב שיקרא לקוד אמיתי.** (Cowork אימת אמפירית: הגרסה הנוכחית עדיין מזויפת —
החזרת `_det_buf[:-1]` לא הפילה אותה.) פרטים: `CC_FIX_FAKE_TESTS_AND_REPLAY`. הוכח RED-on-revert
עם `git stash` (הדבק אדום→ירוק).

**B2 · `pnl_r` מנופח ×~50 (I-22)** — אבחן-קודם איפה ה-×50 (נקודות↔טיקים? $/point? scaling כפול?),
תקן + regression. נתוני-דיווח, לא fire-path.

**E2 · Dashboard — תיקון-באג + ארגון-מחדש** (frontend; §Polling Floors; `useBuildStatus`):
(א) פאנל **detection** per-pattern S2/S4 = המשטח הבולט בראש · (ד) סקשן **TARGETS/STOP** →
**accordion מקופל כברירת-מחדל** (לא בולט) · (ב) day_type freshness (observer, לא סף-360s) ·
(ג) זרמים-מושתקים לא אדומים.

**E1 · עמוד Trades** — אם G4 גילה שדרוש מעבר ל-redesign מלא: `TRADES_PAGE_REDESIGN_2026-06-03.md`.

═══════════════════════════════════════════════════════════
## ✅ Completion gate (אל תסיים בלי כל אלה)
═══════════════════════════════════════════════════════════
1. **צ'קליסט פתוחים:** עבור על `OPEN_ISSUES_REGISTER_2026-06-09.md` — כל פריט DONE (עם raw) או NOT-DONE מנומק.
2. **דגלים:** 7 ON · 3 default-off OFF · S3 לא נגענו. הדבק.
3. **מערכת חיה ויורה:** health · streams S2+S4 · ירי נכתב ל-`v9_trades` ומוצג.
4. **טסטים:** הרץ regression מלא, הדבק את המספר. כל טסט-שכתבת מוכח RED-on-revert.
5. **עדכן בורדים:** `ROADMAP_TO_LIVE.html` (סמן done · רענן "אתה כאן"+"עודכן") + `STATUS_BOARD.md`
   (שורת-לוג finding→fix→verification לכל פריט) — לפי §Roadmap auto-update.
6. **דוח-סיום:** `docs/reports/MEGA_RUN_2026-06-09.txt` — פלט גולמי לכל G ולכל פריט-סשן + סעיף NOT-DONE.
7. **commit** הכל (זכור: הענף 26 לפני origin — Michael ידחוף).

**סדר:** שער-קדם-פתיחה (G1-G5) → דווח GO → סשן (A2→B3→B1→B2→E2/E1) → Completion. עצור-אסטרטגית לפני A2/B3.
