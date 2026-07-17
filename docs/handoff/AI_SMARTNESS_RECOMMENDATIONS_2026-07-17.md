# המלצות: הפיכת MEMS26 למערכת-מסחר חכמה עם LLM/AI (2026-07-17)

**מחבר:** cowork-dev (Cowork MacBook) · **סוג:** מסמך-תכנון + המלצות · **סטטוס:** הצעות בלבד — **שום קוד לא שונה, שום דגל לא הודלק.**

> ⚠️ **כל הצעה כאן שנוגעת בהחלטת-מסחר/גודל/סיכון היא שינוי-משטח-סיכון → strategic stop + חתימת-מייקל.**
> כל דגל שמוצע נולד **default-OFF**, **shadow-first**, ונרשם ב-`config/RULED_FLAGS.yaml` בטרם יודלק, כמו כל דגל אחר.
> ה-AI **לעולם** לא מציב פקודה, לא מגדיל גודל מעבר לתקרה-פסוקה, ולא עוקף halt. הוא **מסביר, מסווג, ומציע** — הפסיקה של מייקל היא הביצוע.

---

## 0. למה עכשיו — הכאב של היום (מקורקע, לא מופשט)

היום (07-17) חזר בדיוק אותו דפוס שאוכל את הזמן של מייקל כבר שבוע:

- **התבניות צדקו, הצנרת-החיה חסמה.** ספר-הצל (shadow) היה חיובי (~**+$277**) בעוד ה-live סגר **−$58.75**
  (`docs/reports/OPS_LOG_2026-07-17.md` ריצה-17: `day_pnl −58.75`). לדוגמה: `#397 shadow ניצח +106.25`
  בעוד ה-live המקביל נכשל/נחסם (OPS_LOG שורה 190).
- **ערימת-שערים חסמה מנצחים בשקט.** ה-`missed_trade_watch.py` כבר תופס את זה בזמן-אמת:
  `🔴 MISSED-WINNER ZLR SHORT @7503.25 gate=cont_trend_filter הגיע +6.00 נק' תוך 5דק'` (OPS_LOG שורה 254).
  התפלגות-החסימות של ריצה-16: `entry_not_confirmed×3 / cont_trend_filter×5 / eod_entry_cutoff×3`.
- **מייקל היה ה-loop.** לאורך כל היום מייקל הסתכל על כל חסימה בעיניים, שאל אותי ~30 פעם "למה זה לא ירה",
  ופסק חי (הוסיף `TREND_CCI_DIRECT_V1`, `S2_REACTIVE_EDGE_FIX_V1`, `NORMAL_ROTATION_FIX_V1`, `ZONE_LIMIT_ENTRY_V1`
  — כולם היום). זו עבודה שאפשר להפוך ל**תמצית-בוקר מדורגת** שה-AI מכין.
- **חלק מהחסימות היו צודקות.** אותו וואצ' רשם גם `✅ gate-right ZLR LONG @7534.5 gate=rr_entry_gate היה מפסיד (-6.00 נק')`
  (שורה 186). המטרה **אינה** לפתוח את כל השערים — אלא להבחין אוטומטית בין חסימה-דוקטרינה לבאג-חסימה.

**המטרה האסטרטגית:** פחות כיבוי-שרֵפות ידני, המערכת **מאבחנת את עצמה ומסתגלת** — בגבולות-הבטיחות הקיימים.

**עקרון-העל (לכל 8 הפרקים):** גיאומטריה דטרמיניסטית מחליטה *אם* לירות; AI מסביר, מסווג, מדרג, ומציע-כיול —
ואף פעם לא מבצע. זו בדיוק הדוקטרינה שכבר כתובה ב-`agent_chat.py` (`SYSTEM_PROMPT`: *"אל תמליץ לבצע פעולות
מסחר ואל תשנה שום דבר — אתה עונה ומסביר בלבד"*). אנחנו מרחיבים את השכבה הזו, לא ממציאים חדשה.

---

## 1. מה כבר קיים (חובה — כדי לא לבנות כפילות)

לפני כל הצעה: MEMS26 **כבר** מחזיקה שלד-AI ולולאת-למידה. ההמלצות למטה **מרחיבות** את הקיים.

| רכיב קיים | קובץ | מה הוא עושה היום | מה חסר לו |
|---|---|---|---|
| **צ'אט-סוכן חי** | `backend/v9/api/v9/agent_chat.py` (`POST /api/v9/agent/chat`) | Claude עם `_live_context()` (day_type, עסקאות-פתוחות, P&L, דגלים, `sierra_state.json`, ALERTS) + `KNOWLEDGE_MAP`/RAG-lite על מסמכי-הריפו. מודל דרך `AGENT_CHAT_MODEL` (ברירת-מחדל `claude-sonnet-5`). read-only, key ב-.env בלבד | לא קורא את **decisions feed**; לא מסווג חסימות; לא יזום (רק תגובתי) |
| **וידג'ט-צ'אט צף** | `frontend/v9/src/v9/components/agent/AgentChatWidget.tsx` | חלון-שיחה גריר בדשבורד, מקורקע במצב-החי | – |
| **feed החלטות** | `trading_gateway.py:407` (`self.decisions`, deque 300) + `GET /api/v9/gateway/decisions` | כל `route_setup` → `{ts, pattern, direction, entry, blocked_by, outcome, trade_id}` + `today.by_gate` aggregation | in-memory בלבד; אין שכבת-פרשנות מעליו |
| **וואצ'-פספוסים חי** | `scripts/missed_trade_watch.py` | קורא decisions, עוקב אחר חסימות-איכות מול המחיר, מדרג `MISSED-WINNER` מול `gate-right`, סיכום-שערים EOD | הדירוג מכני (±נק'); אין סיווג-שורש (דוקטרינה/באג/כיול) |
| **אבחון-פספוס דוקטרינרי** | `scripts/audit_pattern_miss.py` | לכל swing: איזה קריטריון נכשל ובכמה + מצב `--relax` שמודד תפיסות-חדשות מול **false-fires** | ריצה ידנית; הפלט לא מסוכם לתמצית-החלטה |
| **מטריצת-הדמיה** | `scripts/sim_matrix.py` (+`sim_matrix_e2e.py`) | מריץ כל תא (day-type × pattern) דרך ה-gateway האמיתי, מוודא שהפלייבוק תואם | – |
| **לולאת-למידה (v3)** | `scripts/nightly_exit_review.py` → `PROPOSED_TARGETS_DIFF_<date>.yaml` → `scripts/apply_targets_diff.py` → `/api/v9/agent/proposed_diffs` + `/apply_targets_diff` | ניתוח-MFE לילי → מייצר הצעת-דיף ל-`targets.yaml` (p50-MFE×0.5) → מייקל רואה ב-`/board` → **קליק = פסיקה** → validate→merge→loader→tests→commit, **כשל-טסט = revert אוטומטי** | מכסה רק T1-targets; לא שערים/ספים; ההצעה מספרית ולא מוסברת |
| **מדרג-איכות עסקאות** | `backend/v9/services/daily_quality_agent/agent.py` (W12) | EOD, מדרג כל עסקה A–F על timing/execution/outcome/context — **אנליטי, לא-שער** | ציון דטרמיניסטי; אין נימוק-שפה |
| **בדיקת-אמת סיירה** | `agent_chat.py` `/sierra_live_check` | read-only: סיירה-חיה, עסקה-פתוחה, סגירות-היום + P&L | – |
| **לוג-תפעול מרכזי** | `scripts/ops_log.py` (N12) → `docs/reports/OPS_LOG_<date>.md` | כל וואצ'/סוכן כותב שורה כרונולוגית אחת | טקסט-גולמי; אין תמצית |
| **משמעת-בטיחות** | `config/RULED_FLAGS.yaml` + `scripts/flag_guard.py` | כל דגל פסוק; flag_guard מאמת `.env` מול הקובץ בכל בוקר + fire-drill (PASS 79/79) | – |

**מסקנה:** אין צורך בפלטפורמה חדשה. ה-AI-smartness = **שכבת-פרשנות דקה** מעל feeds שכבר קיימים
(`decisions`, `OPS_LOG`, `PROPOSED_TARGETS_DIFF`), + הרחבת לולאת-הלמידה מ-targets ל-gates.

---

## 2. פרק 1 — זיהוי-פספוסים אוטונומי ("למה אין מסחר")

**הבעיה היום:** ה-`missed_trade_watch.py` מסמן חסימות אבל **לא מסווג אותן**. מייקל צריך לקרוא כל שורה
ולהחליט: "זו חסימה נכונה (דוקטרינה)?", "זה באג-צנרת?", או "זה סתם כיול הדוק-מדי?". זה מה שאכל את היום.

**מה זה פותר:** ממכן בדיוק את לולאת "למה אין מסחר" שעשינו ידנית — סיווג + דירוג + תמצית-בוקר.

**איך בונים (`scripts/miss_classifier.py` חדש, read-only):**
1. **קלט = feeds קיימים בלבד.** בסוף-סשן קורא את `GET /api/v9/gateway/decisions` (כל החסימות + `by_gate`),
   את `OPS_LOG_<date>.md` (כולל שורות `MISSED-WINNER`/`gate-right` של `missed_trade_watch`), ואת
   `PATTERN_MISS_AUDIT` אם רץ. **אין מקור-דאטה חדש** — Rule-1 (honest failure): מה שאין ב-feed לא מומצא.
2. **סיווג פר-חסימה ע"י LLM** (tier זול, ראה פרק 7): לכל `(pattern, direction, gate, entry, hypothetical-outcome)`
   מתייג אחת מ-3:
   - `CORRECT-doctrine` — השער עשה את עבודתו (למשל `gate-right`: היה מפסיד; או counter-trend ב-`daytype_playbook`).
   - `SUSPECT-bug` — חסימה שסותרת את הדוקטרינה/פסיקה (למשל דהיית-Normal שנחסמה טרם `NORMAL_ROTATION_FIX_V1`).
   - `CALIBRATION` — חסם מנצח-אמיתי בגלל סף (`cont_trend_filter` חסם `MISSED-WINNER +6נק'`).
3. **הנימוק מוזרם דרך RULED_FLAGS + הדוקטרינה.** ה-prompt מקבל את `RULED_FLAGS.yaml` + `daytype_playbook.yaml`
   + מפת-הדוקטרינה מ-`agent_chat.py` (`KNOWLEDGE_MAP`) — כדי שהסיווג יהיה מעוגן, לא דעה.
4. **פלט = תמצית-בוקר מדורגת** (`docs/reports/MISS_BRIEF_<date>.md` + כרטיס ב-`/board`): טבלה
   ממוינת לפי `SUSPECT-bug` תחילה, כל שורה עם עלות-הזדמנות משוערת (מ-`missed_watch`), נימוק חד-שורתי,
   וקישור לקובץ:שורה של השער. זה ה-input לפסיקת-הבוקר של מייקל.

**סיכון + מעקה:** read-only מוחלט; הסיווג הוא **המלצה**, לא פעולה. סכנת-שווא היחידה = תיוג-שגוי →
מרוכך ב-(א) תמיד לצרף את הראיה-הגולמית (Rule-5: "paste the command + raw output"), (ב) שני tier-ים —
זול מסווג, מייקל מאשר. אף תיוג לא נוגע בקוד/דגל.

**shadow-first?** לא רלוונטי — הרכיב לעולם-לא-מבצע. רץ **על מכונת-המסחר** (לא מהסנדבוק — ה-sandbox עיוור
ל-DB/localhost, מ-`MEMORY.md`: `morning_briefing` כתב BRIEF-שקר משם). מריצים דרך scheduler מקומי או ידנית.

---

## 3. פרק 2 — כיול-שערים מונחה-נתונים (data-driven gate tuning)

**הבעיה היום:** הפער shadow (~+$277) מול live (−$58.75) הוא **אות-A/B חינמי** שלא מנוצל. כל שער חוסם עסקאות;
חלקן היו מנצחות (עלות), חלקן היו מפסידות (חיסכון). היום אף אחד לא מודד את המאזן הזה פר-שער לאורך זמן.

**מה זה פותר:** הופך את הפער shadow↔live לתקציב-החלטה כמותי — "השער X עלה $Y השבוע נטו, שקול להרפות אותו בכך-וכך".

**איך בונים (מרחיב את הקיים, לא חדש):**
1. **המדידה כבר חצי-בנויה.** `missed_trade_watch.py` כבר צובר `gate_score[gate] = [won, lost]` (חסם-מנצח מול
   חסם-מפסיד) ומדפיס `סיכום-שערים EOD`. ה-shadow-book (`shadow_executor.py` / `executors/shadow.py`) כבר מריץ
   את אותן עסקאות ללא-חסימה. **צוברים** את שני אלה לכל שער, כל יום, לטבלת-עלות שבועית.
2. **סקירה-AI שבועית** (tier חזק, פרק 7): קוראת את הצבירה + מריצה `audit_pattern_miss.py --relax` (שכבר
   מודד newly-caught מול **added FALSE-fires** לכל הרפיה) ומפיקה, לכל שער, שורה: `עלות-חסימה נטו $X ·
   הרפיה-מוצעת · false-fire צפוי · confidence`.
3. **ההצעה נכנסת ללולאת-הלמידה הקיימת.** בדיוק כמו `nightly_exit_review.py` שמייצר `PROPOSED_TARGETS_DIFF`,
   נוסיף `PROPOSED_GATE_DIFF_<date>.yaml` (סף-שער בלבד, לא לוגיקה) שמוצג ב-`/api/v9/agent/proposed_diffs`.
   **הקליק של מייקל = הפסיקה**, וההחלה עוברת דרך `apply_targets_diff.py`-אח (validate→merge→**tests**→commit,
   כשל-טסט=revert). לעולם לא אוטומטי.

**סיכון + מעקה:** זה הפרק הכי קרוב למשטח-הסיכון. מעקות: (א) **אף פעם auto-apply** — רק הצעה + קליק-מייקל;
(ב) כל שינוי-סף עובר `flag_guard` + טסט-רגרסיה (כמו כל שער היום); (ג) מדידה על **shadow**, לא על כסף-אמת;
(ד) ההצעה מוגבלת לספים-מספריים של שערים שכבר קיימים — **לא** יצירת/ביטול שער, **לא** נגיעה ב-halts/kill-switch.

**shadow-first?** כן, מהותית: המדידה כולה מ-shadow-book; כל סף-חדש מודלק קודם ב-SHADOW ל-A/B לפני live
(בדיוק כמו `S4_EXTREME_TREND_RELABEL` שעלה דרך SHADOW).

---

## 4. פרק 3 — ביטחון-תבנית היברידי (hybrid pattern confidence)

**הבעיה היום:** הגלאים בינאריים — ZLR/GB100/S2 או עוברים את כל הקריטריונים או לא (`audit_pattern_miss.py`
מראה שכל קריטריון מדוד). אבל שתי עסקאות שעברו את אותה גיאומטריה יכולות להיות שונות-מאוד באיכות-הקשר
(מיקום מול VAH/VAL, day-type, CVD, מבנה-אחרון). היום זה לא נלכד עד ה-EOD (W12 `daily_quality_agent`).

**מה זה פותר:** מוסיף ציון-ביטחון-הקשר **בזמן-אמת** שמכייל **גודל**, בלי לגעת בהחלטת-הירי.

**איך בונים — דוקטרינה-בטוחה ("גיאומטריה יורה, AI מגדיל/מקטין"):**
1. **הטריגר נשאר דטרמיניסטי.** הגלאי (`zlr.py`/`gb100.py`/`five_min_system.py`) הוא היחיד שקובע *אם* יש תבנית.
   ה-AI **לא ממציא עסקה** ולעולם לא מפעיל ירי.
2. **ציון-הקשר** (0–1) מ-ML/LLM קל על פיצ'רים שכבר ב-`cross_context` (הנשמר על כל עסקה): day-type,
   מיקום מול VAH/POC/VAL, trend_state, CVD net-delta, מבנה-swing אחרון. אפשר להתחיל **דטרמיניסטי** (הרחבת
   `daily_quality_agent/scoring.py` — `context_quality()` כבר קיים!) ורק אז לשדרג ל-LLM אם צריך ניואנס.
3. **הציון מכייל גודל בלבד, כלפי-מטה בלבד.** נכנס כ**מכפיל-הקטנה** בשרשרת-הגודל הקיימת, לצד
   `SIZE_CAP_CUT_V1` ו-`SIZE_CAP_OVER_FIXED_V1` (שכבר עושים `min(fixed, cut)` — הקטנה בלבד). ציון-נמוך →
   `REDUCED`; ציון-גבוה → הגודל-הפסוק כפי-שהוא. **לעולם לא מעל** `FIXED_CONTRACTS_4`/התקרה-הפסוקה.

**סיכון + מעקה:** הסכנה = ציון-שגוי שמקטין מנצח (עלות-הזדמנות, לא הפסד). מעקות: (א) **מונוטוני-הקטנה בלבד** —
מבנית לא-יכול להגדיל סיכון; (ב) עובר דרך אותם choke-points של `SIZE_CAP_CUT` שכבר פסוקים; (ג) דגל
`AI_CONFIDENCE_SIZING_V1` default-OFF; (ד) בשלב-SHADOW הציון **נרשם בלבד** (ליד ה-shadow-fill) ומושווה
לתוצאה בפועל — אם הוא לא מנבא, לא מדליקים.

**shadow-first?** כן — חובה. שבועות של "ציון מול תוצאת-shadow" לפני שהוא נוגע בגודל-אמת.

---

## 5. פרק 4 — סיווג-יום עוזר (day-type co-pilot)

**הבעיה היום:** מייקל דרס ידנית את סוג-היום כל היום (`DAY_TYPE_MANUAL_OVERRIDE=2026-07-17:Normal` —
מ-`PATTERN_MGMT_AUDIT`). המסווג האוטומטי (S1, 7-סוגים) עדיין לא מספיק-אמין לבד, אז מייקל נאלץ לקרוא את
הפרופיל-המתפתח ולפסוק — כל הזמן. זו הזרקת-אנרגיה-אנושית קבועה.

**מה זה פותר:** נותן למייקל **הצעת-day-type עם נימוק** לאישור-בקליק, במקום שיצטרך לגזור לבד מהתצוגה.

**איך בונים (human-approves, לא human-replaces):**
1. **המסווג הדטרמיניסטי נשאר המקור.** `S1_NEW_CLASSIFIER` + `day_type_machine` ממשיכים לרוץ; ה-AI הוא
   **שכבה-שנייה מייעצת**, לא מחליף.
2. **קורא את הפרופיל-המתפתח** (TPO/Value-migration שכבר ב-DB + `sierra_state`) ומפיק כל ~30דק':
   `day-type מוצע · נימוק דלתוני חד-פסקה · confidence · במה הוא חולק על המכונה`. הנימוק מעוגן ב-
   `docs/spec_authority/DALTON_DOCTRINE.md` (שכבר ב-`KNOWLEDGE_MAP` של `agent_chat.py`).
3. **אופציית-vision** (tier חזק): צילום-מסך של הפרופיל → הצעה ("B-period הרחיב את ה-IB כלפי-מעלה → Variation").
   שימושי, אבל **משני** — ה-DB-path מדויק ומספיק להתחלה (Rule-2: ה-numbers מגיעים מ-bar-math, לא מ-vision).
4. **האישור = override קיים.** קליק-"אשר" של מייקל פשוט כותב את אותו `DAY_TYPE_MANUAL_OVERRIDE` שהוא
   כותב היום ידנית — אין מנגנון-כתיבה חדש, רק הצעה שמזינה אותו. פג-תוקף ב-roll של ET כרגיל.

**סיכון + מעקה:** day-type מזין את הפלייבוק (SKIP/REDUCED) → משפיע-מסחר. לכן: (א) **הצעה בלבד** — לעולם
לא כותב override לבד; (ב) בשלב-SHADOW ההצעה נרשמת ומושווה ל-override הידני של מייקל (כמה פעמים הסכימו?);
(ג) הפער AI↔מכונה תמיד גלוי (Rule-5) כדי שמייקל יראה מתי לא לסמוך.

**shadow-first?** כן — "AI-הציע מול מייקל-פסק" נאסף שבועות עד שההסכמה מוכחת.

---

## 6. פרק 5 — תפעול בשפה-טבעית (natural-language ops)

**הבעיה היום:** מייקל שאל אותי ~30 שאלות היום — "למה X לא ירה", "מה חוסם את S4", "תראה לי את הפספוסים
של היום". כל אחת דרשה ממני לקרוא feeds ידנית. זה **בדיוק** מה ש-`agent_chat.py` כבר בנוי לענות עליו —
רק שהיום הוא לא מחובר ל-decisions feed.

**מה זה פותר:** הופך את השאלות-החוזרות לתשובה-מיידית מקורקעת, בלי שאני/מייקל נחפור בלוגים.

**איך בונים (הרחבת `agent_chat.py` הקיים — לא רכיב חדש):**
1. **חיבור ה-decisions feed ל-`_live_context()`.** היום `_live_context()` מושך day_type/עסקאות/דגלים/סיירה.
   מוסיפים section שמושך את `/api/v9/gateway/decisions` (`today.by_gate` + N החסימות האחרונות) ו-tail של
   `OPS_LOG_<date>.md`. עכשיו "למה S4 לא ירה?" נענה מהנתונים האמיתיים.
2. **RAG כבר קיים.** `_knowledge_context()` כבר טוען מסמכים-רלוונטיים לפי נושא-השאלה (FLAG_INDEX,
   TARGETS_STOPS, DALTON). מרחיבים את `_TOPIC_FILES` ל-decisions/miss-brief.
3. **קיצורי-דרך.** ב-`AgentChatWidget.tsx` מוסיפים כפתורי-שאלה מוכנים ("פספוסי-היום", "מה חוסם עכשיו")
   שממפים לשאילתות מוכנות — מקצר את ה-30-שאלות ל-3-קליקים.

**סיכון + מעקה:** נמוך-מאוד — read-only, ה-`SYSTEM_PROMPT` כבר אוסר המלצות-מסחר ושינויים. הסיכון היחיד =
תשובה-שגויה → מרוכך ב-Rule-1 (המודל מצוּוֶה לומר "אין לי את זה" ולא להמציא) + הצגת-המקור. עלות-טוקנים:
מנוהל ע"י tier + budget שכבר קיימים (`AGENT_CHAT_MAX_TOKENS`, שני-מסמכים-לכל-היותר).

**shadow-first?** לא רלוונטי (read-only). **זה ה-quick-win של Phase-1** — יום-עבודה, אפס-סיכון.

---

## 7. פרק 6 — למידה-מפספוסים לאורך זמן (compounding)

**הבעיה היום:** האבחונים מצוינים אבל **חד-פעמיים** — `PATTERN_MISS_AUDIT` ו-`PATTERN_MGMT_AUDIT` נכתבו היום,
ומחר יתחילו מאפס. אין ליד'גר-פספוסים מצטבר, אז הכיול הוא bug-by-bug במקום שבוע-על-שבוע.

**מה זה פותר:** הופך תובנות-נקודתיות למגמה — "השער `cont_trend_filter` חסם 4 מנצחים ב-3 ימים = דפוס, לא רעש".

**איך בונים (מרחיב את לולאת-הלמידה הקיימת):**
1. **ליד'גר-פספוסים מצטבר** (`docs/reports/MISS_LEDGER.jsonl`, append-only כמו OPS_LOG): כל ערב, פלט
   ה-`miss_classifier` (פרק 1) + `gate_score` (פרק 2) נדחף כשורה מובנית: `date, gate/pattern/day-type,
   classification, opportunity-cost, was-right`. **מקור-אחד, append-only** — אותה משמעת של `ops_log.py`.
2. **הסקירה-השבועית צוברת מעליו.** ה-AI-החזק (פרק 8) קורא את הליד'גר של השבוע ומדרג: אילו שערים/תבניות/
   ימים חוזרים כ-`SUSPECT-bug`/`CALIBRATION`, ומייצר את ה-`PROPOSED_GATE_DIFF` (פרק 2) עם **ראיה מ-N ימים**,
   לא מיום-אחד. זה מ-`nightly_exit_review.py` שכבר עושה בדיוק זה ל-targets (`p50-MFE × 0.5 · n=... · POOR .../...`).
3. **סגירת-הלולאה.** כשמייקל פוסק דיף, הפסיקה נכתבת ל-`RULED_FLAGS.yaml` (כמו כל דגל), והליד'גר מסמן את
   הפריט "resolved" — כך הבאג לא חוזר להצעות. זה בדיוק ה-loop שכבר עובד: `nightly_exit_review → PROPOSED_DIFF
   → קליק → apply_targets_diff → commit`.

**סיכון + מעקה:** הליד'גר עצמו read-only-אנליטי. הסכנה = "AI מסיק דפוס מ-n-קטן" → מרוכך: כל הצעה נושאת `n`
ו-confidence (כמו הדיף הקיים), ומייקל לא פוסק על n<סף. אין החלה אוטומטית לעולם.

**shadow-first?** כן — כל הצעה שנובעת מהליד'גר עולה SHADOW→A/B→live.

---

## 8. פרק 7 — ארכיטקטורה + מעקות-בטיחות

### 8.1 הכללים-הקשיחים (בל-יעבור)
- **AI לעולם לא מבצע.** לא מציב op=PLACE, לא מגדיל מעבר לתקרה-פסוקה (`FIXED_CONTRACTS_4`/`PATTERN_RISK_CAPS`/
  `SIZE_CAP_CUT`), לא עוקף `RISK_HALT_V1`/`kill_switch`/`FEED_WATCHDOG`. כל השפעה-על-גודל היא **הקטנה-בלבד**.
- **shadow-first לכל שינוי שה-AI השפיע עליו.** בלי יוצא-מן-הכלל. אותה משמעת של `S4_EXTREME_TREND_RELABEL`.
- **חתימת-מייקל לכל דבר שנוגע במשטח-הסיכון.** כל דגל-AI נולד default-OFF, נרשם ב-`RULED_FLAGS.yaml` עם
  `ruled_by/date`, ו-`flag_guard.py` יאמת אותו בכל בוקר + fire-drill (בדיוק כמו 79 הדגלים היום).
- **AI-שער-מסחר = טעות-קטגוריה.** ה-LLM אף פעם לא בשרשרת-הירי-הסינכרונית. הוא רץ ליד/אחרי, על feeds, אף פעם
  לא כ-blocking-gate. (מרוכך גם ע"י latency + עלות — LLM ב-hot-path זה גם סיכון-אמינות.)
- **מקור-אמת אחד (Rule-1..5 של CLAUDE.md).** ה-AI צורך את מה שהמערכת כבר מייצרת; לא מסנתז OHLC/day-type/levels.
  "aggregator-ים הם amplifiers" — ציון-AI שגוי לא נכנס ל-min/max של סיכון.

### 8.2 איזה מודל לאיזו עבודה (מודעות-עלות)
| שכבה | תדירות | מודל-מוצע | למה |
|---|---|---|---|
| סיווג-חסימות (פרק 1), NL-ops (פרק 5), ציון-הקשר (פרק 3) | תמידי / פר-סשן | **Haiku-class** (זול, מהיר) דרך `AGENT_CLASSIFY_MODEL` חדש | נפח-גבוה, משימה-מוגדרת-היטב; העלות חייבת להיות זניחה |
| צ'אט-סוכן קיים | תגובתי (מייקל שואל) | **Sonnet-class** (`AGENT_CHAT_MODEL` הקיים) | ניואנס + RAG, נפח-נמוך |
| סקירה-שבועית + כיול-שערים (פרקים 2,6) + day-type-vision (4) | שבועי / EOD | **Sonnet/Opus-class** דרך `AGENT_REVIEW_MODEL` | הכרעות-כבדות, מעט-קריאות → עלות-מוצדקת |

- **תקצוב-טוקנים כבר קיים** (`AGENT_CHAT_MAX_TOKENS`, "שני-מסמכים-לכל-היותר" ב-`_knowledge_context`). מרחיבים
  לכל tier. ה-Haiku-tier רץ על תמציות (`by_gate`, `gate_score`) לא על raw-logs → זול.
- **`window.cowork.askClaude` / inference-בצד-לקוח:** ה-key **נשאר server-side** (`agent_chat.py`, `.env`,
  לא-נלוג-לא-מוחזר). מנגנון-Cowork-בדפדפן יכול להריץ את ה-classification-הזול, אבל ה-inference שמחזיק-מפתח
  נשאר בשרת — זו הדוקטרינה-הקיימת, לא לשבור אותה.

### 8.3 אבחון לפני בנייה (Pre-LIVE Discipline)
לפני שמדליקים כל רכיב-AI: לרוץ `audit_pattern_miss.py` על המכונה + לקרוא את הקוד-החי (לא-מהזיכרון), בדיוק
כפי ש-`PATTERN_MISS_AUDIT` §0/§F2 דורש ("diagnose first, fix second"). ה-AI **לא** תירוץ לדלג על האבחון.

---

## 9. פרק 8 — מפת-דרכים מדורגת

| Phase | מה | מאמץ | סיכון | תשואה-צפויה | תנאי-מעבר |
|---|---|---|---|---|---|
| **1 — קריאה-בלבד (השבוע)** | (א) NL-ops: לחבר decisions+OPS_LOG ל-`agent_chat._live_context` + כפתורי-שאלה (פרק 5). (ב) `miss_classifier.py` → תמצית-בוקר מדורגת (פרק 1). | **נמוך** (~1–2 ימים; מרחיב קבצים קיימים) | **אפס** (read-only, אף פעם-לא-מבצע) | ביטול ה-30-שאלות-ביום + תמצית-בוקר במקום eyeballing | עובד על **מכונת-המסחר** (לא sandbox), נותן תשובה נכונה על ראיה-אמיתית של יום-אחד |
| **2 — SHADOW** | (א) ציון-הקשר נרשם-בלבד ליד shadow-fills (פרק 3). (ב) `gate_score` + shadow-book → טבלת-עלות-שער שבועית + `audit_pattern_miss --relax` (פרק 2). (ג) ליד'גר-פספוסים מצטבר (פרק 6). | **בינוני** (~1–2 שבועות) | **נמוך** (SHADOW בלבד; שום גודל-אמת מושפע) | הוכחה-כמותית האם ציון-AI מנבא, ואיזה שער עולה כסף | הציון-מנבא-תוצאה על ≥שבוע shadow; טבלת-העלות יציבה עם n מספיק |
| **3 — עם-פסיקות** | (א) day-type co-pilot מציע→מייקל-מאשר (פרק 4). (ב) `AI_CONFIDENCE_SIZING_V1` מכייל גודל **כלפי-מטה** (פרק 3). (ג) `PROPOSED_GATE_DIFF` → קליק-מייקל → apply→tests→commit (פרקים 2,6). | **בינוני-גבוה** | **בינוני** (נוגע במשטח-סיכון — לכן פסיקה פר-שינוי) | הקטנת human-in-the-loop: המערכת מציעה-day-type ומכיילת-שערים, מייקל מאשר במקום גוזר | כל שינוי: default-OFF→RULED_FLAGS→flag_guard→SHADOW-A/B→חתימת-מייקל→live, פר-פריט |

**סדר-הנעה:** Phase-1 מיידי (אפס-סיכון, quick-win). Phase-2 רק אחרי ש-Phase-1 מוכיח שה-feeds נקראים-נכון.
Phase-3 פר-פריט, כל אחד עם פסיקה נפרדת — **לא חבילה**. בדיוק כמו שהדגלים עלו השבוע אחד-אחד עם ראיה.

---

## 10. סיכום למייקל

- **לא צריך פלטפורמה חדשה.** MEMS26 כבר מחזיקה: צ'אט-סוכן (`agent_chat.py`), feed-החלטות, וואצ'-פספוסים,
  אבחון-דוקטרינרי, מטריצת-הדמיה, מדרג-איכות, ו**לולאת-למידה מלאה** (`nightly_exit_review → PROPOSED_DIFF →
  קליק → apply → tests → commit`). ה-AI-smartness = שכבת-פרשנות דקה מעליהם.
- **הכאב-של-היום ממופה לפרק:** 30-השאלות→פרק 5 · eyeballing-פספוסים→פרק 1 · shadow↔live gap→פרק 2 ·
  override-ידני-כל-היום→פרק 4 · bug-by-bug→פרק 6.
- **הבטיחות לא נפגעת:** AI לעולם-לא-מבצע · הקטנה-בלבד-בגודל · default-OFF · shadow-first · חתימת-מייקל
  למשטח-סיכון · `flag_guard` אוכף · Rule-1..5.
- **התחלה מומלצת:** Phase-1 השבוע — NL-ops + תמצית-הפספוסים. יום-עבודה, אפס-סיכון, מחזיר מיד את הזמן
  שמייקל שרף היום.

*מקורות שנקראו לביסוס (07-17): `CLAUDE.md`, `config/daytype_playbook.yaml`, `config/RULED_FLAGS.yaml`,
`backend/v9/gateway/trading_gateway.py`, `backend/v9/api/v9/agent_chat.py`, `backend/v9/api/v9/gateway_routes.py`,
`backend/v9/services/daily_quality_agent/agent.py`, `frontend/v9/src/v9/components/agent/AgentChatWidget.tsx`,
`scripts/missed_trade_watch.py`, `scripts/audit_pattern_miss.py`, `scripts/sim_matrix.py`, `scripts/ops_log.py`,
`scripts/nightly_exit_review.py`, `scripts/apply_targets_diff.py`, `docs/handoff/PATTERN_MISS_AUDIT_2026-07-17.md`,
`docs/handoff/PATTERN_MGMT_AUDIT_2026-07-17.md`, `docs/reports/OPS_LOG_2026-07-17.md`.*
