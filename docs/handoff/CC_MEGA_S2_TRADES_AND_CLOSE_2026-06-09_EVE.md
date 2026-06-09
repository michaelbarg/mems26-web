# CC — מגה ערב: S2→trades · B2 · E2 · טסט #3 אמיתי · סגירה (Rule 5, self-verify) · 2026-06-09

**הוכן ע"י Cowork (verifier) אחרי הצלבת המגה של היום.** מצב מאומת חי (16:52 IDT, RTH פתוח):
- ✅ **S4 יורה ונכתב ל-`v9_trades` חי** — `created_at=2026-06-09 16:50:05 IDT, firing_system=4, pattern_id='HTLB'`. החוסם בן-השבוע (#1) סגור ומוכח.
- ✅ backend health=200@7ms · `v9_bars_5min` היום=7 (max 16:50) · git tip `17f80d6` (ahead 29) · אין דגל default-off שהודלק · S3 לא נגעו.
- 🟡 **S2 setup לא הגיע ל-trades:** `v9_five_min_setups` היום=1 (`ts=16:45, INITIATIVE_LONG, LONG`) אבל אין `firing_system=2` היום ב-`v9_trades`.
- 🔴 **טסט #3 (B1) עדיין מזויף** — Cowork הוכיח אמפירית RED-on-revert מזויף: החזרת תיקון שורה 936 ב-worktree מבודד → הטסט **עדיין 2 passed**. הוא קורא ל-`_detect_reactive` אבל ה-assertions בודקים רק ערכי-fixture, לא את פלט-הפרודקשן ולא את שורה 936.

**קרא קודם דרך ה-index:** `CLAUDE.md` (§Pre-LIVE · §Standing Decisions · §Index) · `SYSTEM_INDEX.md` · `CC_HANDOFF_CONTRACT.md`.

**איך לעבוד:** כל פריט **אבחן→בצע→אמת-את-עצמך (פקודה+פלט גולמי)→done**. אל תכריז "עובד" בלי raw.

**מעקות קבועים (אסור לחרוג):** אל תדליק אף דגל default-off (`S2_CHOPPINESS_GATE`·`LAYER0_CHOP_GATE`·`S2_REQUIRE_COT_AMT`). S3/footprint — לא נוגעים עד post-LIVE. כל trading-logic = STRATEGIC-STOP מתועד.

═══════════════════════════════════════════════════════════
## 🔴 P1 · S2→trades — למה הסטאפ של 16:45 לא נהיה trade? (אבחון-קודם, אל תניח)
═══════════════════════════════════════════════════════════
זהו אבחון, לא תיקון-עיוור. הדבק raw לכל חוליה:

1. **השורה עצמה:** `SELECT * FROM v9_five_min_setups WHERE ts::date=CURRENT_DATE;` — מה ה-direction/pattern/confidence/status המלאים?
2. **לוג `setup_emitter→gateway`** סביב 16:45: האם הסטאפ **emitted**? **approved** או **vetoed**? אם vetoed — **מה הסיבה המדויקת** (איזה gate)? (זכור: chop gates + COT/AMT אמורים להיות OFF default — אם veto נובע מהם, זו רגרסיה → STRATEGIC-STOP.)
3. **אם approved אך אין שורה ב-`v9_trades`:** עקוב gateway→trade_manager→persist. איפה זה נופל? (השווה לנתיב S4 שכן עבד 16:50.)
4. **הכרעה:** veto לגיטימי (→ תעד, זה לא באג) **או** חוליה שבורה ב-S2 ספציפית (→ תקן smallest-change + regression).

תוצר: `docs/reports/S2_TO_TRADES_DIAG_2026-06-09.txt` (raw לכל 4 החוליות + הכרעה).

═══════════════════════════════════════════════════════════
## 🔴 P2 · טסט #3 (B1) — כתוב מחדש כך שיהיה RED-on-revert אמיתי
═══════════════════════════════════════════════════════════
**הבעיה (אומת ע"י Cowork):** `tests/v9/regression/test_s2_detect_on_completed_bar.py` קורא ל-`_detect_reactive` ישירות עם buffers משלו ובודק רק ערכי-fixture (`trimmed[-1]["c"]==7399`, `b4_trimmed_bearish != b4_full_bearish`). הוא **לא נוגע בשורה 936** (הנתיב שתוקן), לכן החזרת התיקון לא מפילה אותו.

**החוזה לטסט הנכון (load-bearing):** הטסט חייב **להריץ את `process_bar`** (השיטה שמכילה את שורה 936), לא את `_detect_reactive` ישירות.
- בנה `self._bar_buffer` של ≥8 ברים שלמים שמרכיבים זיהוי תקף (Reactive/Initiative) על הבר השלם b4, ואז הוסף **בר חלקי אחרון** ש"הופך" את b4 (למשל close הפוך) — בדיוק כמו ה-bridge (push ראשון של ts חדש = OHLC חלקי).
- הרץ `await fs.process_bar(event)` עם `is_new_bar`. **לכוד את ה-setup הנפלט** (monkeypatch על נקודת-ה-persist/gateway — אתה מכיר אותה).
- **Assertion על פלט-הפרודקשן** (לא fixture): `emitted.entry_price == completed_bar["c"]` (שורה ~1007: `entry_price` מגיע מ-`_det_buf[-1]`) **וגם** `emitted.direction` תואם את הבר השלם.
- **הוכחת RED-on-revert (חובה, הדבק שתי הרצות):**
  1. fix present (שורה 936 = `self._bar_buffer[:-1]...`) → **GREEN**.
  2. שנה שורה 936 ל-`_det_buf = self._bar_buffer` (ללא trim) → הבר החלקי נהיה b4 → `entry_price`/`direction` משתנים → **RED**.
  עשה זאת ב-worktree מבודד (`git worktree add --detach /tmp/redcheck 17f80d6`) — **אל תיגע בעץ החי בזמן RTH**.

**אל תסמן ✅ בלי שתי ההרצות (GREEN→RED) מודבקות.** אם אינך מצליח לגרום ל-RED — הטסט עדיין לא load-bearing; דווח NOT-DONE.

═══════════════════════════════════════════════════════════
## 🟡 P3 · B2 — `pnl_r` מנופח ×~50 (I-22) [נתוני-דיווח, לא fire-path]
═══════════════════════════════════════════════════════════
אבחן-קודם **איפה** ה-×50 נכנס (נקודות↔טיקים? `$/point`? scaling כפול בין entry/stop ל-pnl?). הדבק חישוב ידני מול הערך השמור על trade קיים. תקן + regression test שנכשל-על-החזרה. תוצר: עדכון `STATUS_BOARD.md` (finding→fix→verification).

═══════════════════════════════════════════════════════════
## 🟡 P4 · E2 — Dashboard (frontend; §Polling Floors; `useBuildStatus`)
═══════════════════════════════════════════════════════════
(א) פאנל **detection** per-pattern S2/S4 = המשטח הבולט בראש · (ד) סקשן **TARGETS/STOP** → **accordion מקופל כברירת-מחדל** · (ב) day_type freshness = observer (לא סף-360s) · (ג) זרמים-מושתקים לא אדומים. אל תשנה polling intervals (§Frontend Polling Floors). צלם מסך אחרי.

═══════════════════════════════════════════════════════════
## 🟢 P5 · אמת תצוגת Trades (frontend)
═══════════════════════════════════════════════════════════
ודא שהשורה החיה (16:50, `firing_system=4`, HTLB) **מוצגת בעמוד Trades** ב-frontend — לא רק ב-DB. אם נכתבה ב-DB אך לא מוצגת → באג-frontend בעמוד Trades → תקן (`TRADES_PAGE_REDESIGN_2026-06-03.md`). הדבק צילום/`get_page_text`.

═══════════════════════════════════════════════════════════
## ✅ Completion gate (אל תסיים בלי כל אלה)
═══════════════════════════════════════════════════════════
1. **טסטים:** הרץ regression מלא **אחרי סגירת RTH** (לא בזמן מסחר חי — מונע זיהום `v9_trades`/ערעור המערכת). הדבק את המספר (CC טען 208). כל טסט-שכתבת מוכח RED-on-revert.
2. **דגלים:** 7 ON · 3 default-off OFF · S3 לא נגעו. הדבק `ps eww`/runtime.
3. **מערכת חיה:** health · streams S2+S4 · S4 ירי מוצג. S2→trades מוכרע (P1).
4. **עדכן בורדים:** `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` (finding→fix→verification לכל פריט) — §Roadmap auto-update.
5. **דוח-סיום:** `docs/reports/MEGA_RUN_2026-06-09.txt` — raw לכל P + סעיף NOT-DONE.
6. **commit** הכל (הענף 26 ahead 29 מ-origin — Michael ידחוף).

**סדר:** P1 (S2 אבחון) → P2 (טסט אמיתי, worktree) → P5 (תצוגת Trades) → P3 (B2) → P4 (E2) → Completion אחרי סגירת RTH. עצור-אסטרטגית אם P1 מגלה ש-veto נובע מדגל-chop/COT (רגרסיה) או לפני כל שינוי fire-path.

**מה ש-Cowork יבדוק כשתחזיר:** raw של P1 (4 חוליות), שתי-ההרצות GREEN→RED של P2, חישוב-ידני של B2, וצילום תצוגת-Trades. אל תכריז "done" בלי אלה.
