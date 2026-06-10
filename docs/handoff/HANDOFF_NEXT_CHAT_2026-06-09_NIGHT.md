# HANDOFF — צ'אט Cowork הבא · 2026-06-09 לילה

אתה (Cowork הבא) = **orchestrator + verifier בלתי-תלוי**. CC מבצע על ה-Mac; אתה כותב פרומפטים, מצליב (Rule 5: פקודה+פלט-גולמי), **מאמת בעצמך לפני שמכריז "תוקן"**, ומאשר לפני fire-path. עבוד דרך ה-index.

═══════════════════════════════════════════════
## ⭐⭐ קרא ראשון — איך לא לעבוד לא-נכון (זו הבעיה החוזרת)
═══════════════════════════════════════════════
**הבעיה שחוזרת:** הצ'אט-הקודם נטה להתייחס למערכת כאילו היא שבורה/ריקה — לאבחן מאפס, להניח שחסר משהו, ולשלוח ל-CC פרומפט לתקן דבר **שכבר תוקן ו-committed**. זה גורם עבודה כפולה ורגרסיות. **אל תעשה את זה.**

**המודל הנכון:** CC = מהנדס-בכיר שכבר עשה את העבודה היום, הריץ אותה, ו-committed הכל ל-Mac. אתה = הבודק שמאמת את התוצאה החיה — **לא** מנהל שמקצה מחדש משימות גמורות.

**מה שגוי מול מה שנכון (דוגמאות מהיום):**
- ❌ "S1 לא מסווג, day_type=UNKNOWN — בוא נשלח ל-CC לתקן opening_type."
  ✅ קודם `git log` → רואה `f926237 FIX1` committed; הצ'art החי מראה `Trend Normal · CLASSIFIED · OPEN_DRIVE`. **כבר תוקן.** אל תשלח שוב.
- ❌ "ה-targets לא מהטבלה — בוא נכתוב פרומפט FIX5."
  ✅ `git log` → `3ac3bae FIX5` committed. בדוק חי שזה עובד; אם כן — סמן done.
- ❌ "הצ'art שבור / חסרים ברים — בוא נאבחן feed."
  ✅ פתח את הצ'art החי (Claude-in-Chrome) ובדוק; כנראה כבר תקין (tip `58bdb94`).

**הכלל:** לפני **כל** "בוא נתקן X" — בדוק 3 מקורות: (1) `git log` (כנראה X כבר committed), (2) הצ'art/המערכת החיה, (3) ה-DB. אם X כבר שם → **אמת ותמשיך, אל תשלח פרומפט.**

**מה ש-CC כבר מחזיק (אל תבנה מחדש):** כל הקוד (FIX 1–7 + צ'art, tip `58bdb94`, ahead 46) · השירותים רצים (backend+גשר+frontend חיים, אל תאתחל) · הקונטקסט המלא של היום. **אל תסביר ל-CC מה נעשה ואל תשלח פרומפטים שכבר ביצע.**

**מה כן לעשות:** (א) אמת חי את מה שכבר נעשה (Rule 5), (ב) בחר את הפריט-הפתוח הבא (רשימה למטה), (ג) פרומפט ממוקד **רק** למה שנותר. הסנכרון = דרך ה-repo + המערכת החיה, לא הסבר-מחדש.


═══════════════════════════════════════════════
## 🔴 קודם כל — בטיחות-git (לא לדלג)
═══════════════════════════════════════════════
- הענף `stabilize/mems26-local-truth-2026-05-16` **ahead 46 מ-origin = לא נדחף**. כל התיקונים קיימים **רק על ה-Mac**. **Michael חייב `git push` מה-Mac** (Cowork חסום מ-push). עד שזה נדחף — מעבר-מחשב/clone מאבד הכל.
- לא-מקומט כרגע = **docs בלבד** (ROADMAP/STATUS_BOARD/ISSUES_REGISTER/PATTERN_DIAG + דוחות חדשים). `bars_5min_history.py` מראה modified אבל diff **ריק** (mtime בלבד, 0 שינוי). **שום קוד-fix לא בסיכון** — הכל committed.
- צעד ראשון: ודא `git status` נקי-מקוד + `git push` בוצע מה-Mac.

═══════════════════════════════════════════════
## ✅ מה שהושלם היום (committed, מאומת ע"י Cowork)
═══════════════════════════════════════════════
tip = `58bdb94`. השרשרת:
- **FIX 1** (`f926237`+`95f3ca9`) — opening_type נקרא מה-state-machine (לא מ-TPO שמקודד NA) + provisional day_type מ-`opening_type×IB` (DECISION_MATRIX) ל-auth+targets. **מאומת חי:** הצ'art מראה `Trend Normal · CLASSIFIED · OPEN_DRIVE · IB 7417/7390.75`, day_type≠UNKNOWN.
- **FIX 2** (`3ec2c10`) — `zlr_detected` bool→int ב-woodies INSERT.
- **FIX 5** (`3ac3bae`) — targets צורכים את הטבלה דרך provisional day_type (לא fallback). אומת: `get_targets` מחזיר None ל-UNKNOWN → לכן היה צריך provisional.
- **FIX 7** (`6ad2e6e`+`89f17c6`) — Flag stop = **בר-הפריצה** (לא flag wick) · T1 יחסי **0.4R(25נק')→0.8R(15נק')**, YAML-tunable. **RED-on-revert הוכח ע"י Cowork** (worktree: revert anchor → `test_bear_flag_stop_is_breakout_bar` FAILED).
- **FIX 4** (`766796f`+`3ed9e74`) — קריאת-HTTP-עצמית חוסמת-loop (deadlock 2.2s) הוסרה מ-quality_tier → in-memory. (decision_tree 5 קריאות רצות ב-`to_thread` → לא deadlock, רק latency.)
- **FIX 3/3B** (`873cd1f`→`58bdb94`) — הצ'art: ה-"+" המוקרנים. **שורש אמיתי: ברי-Globex של יום-המחר דלפו ל-feed הרציף ונוצרו לפני סשן-היום.** תוקן (RTH-filter בודק תאריך). **מאומת ויזואלית ע"י Cowork** (טעינה-נקייה+zoom: ה-"+" נעלמו, ציר רציף).

210 regression tests עוברים.

═══════════════════════════════════════════════
## 🟡 פתוח לפני DEMO (לא חוסם הלילה)
═══════════════════════════════════════════════
1. 🔴 **אימות-חי ב-RTH מחר של שרשרת-הירי המלאה** (ה-GO/NO-GO האמיתי): `day_type≠UNKNOWN` בחלון → ירי-S2 עם **targets מהטבלה, R:R≥1, tier≥MEDIUM (חוזים>0)** + **סטופ-פריצה** → שורה ב-`v9_trades` + מוצג בעמוד Trades.
2. 🟡 **S4 Woodies targets עדיין טיקים-קבועים** (כמו עסקה #20) — להמיר לטבלה כמו FIX 5/7.
3. 🟡 **sizing=0** — `REACTIVE×Trend_Normal` ב-LOW=0 חוזים (auth_matrix, בכוונה). החלטת-Michael אם לשנות.
4. 🔵 **decision_tree 5 touchpoints → in-memory** מ-`app.state` (חוסן+latency, לא deadlock).
5. 🔵 **FIX 6 — dashboard** פאנל זיהוי+דירוג פר-מערכת S1/S2/4 (backend מוסיף tier ל-`patterns[]`, frontend בטאב Shadow). `docs/handoff/CC_MASTER_FIX_2026-06-09_EVE.md` §FIX6.
6. 🔵 **פיד היה תקוע** (בר אחרון 17:50, סשן הסתיים) — לוודא מחר שהגשר/Sierra חי ב-RTH (`/tmp/bridge.err.log`).

═══════════════════════════════════════════════
## הפרומפטים שכבר מוכנים
═══════════════════════════════════════════════
`CC_MASTER_FIX_2026-06-09_EVE.md` (FIX 1–6) · `CC_FIX7_FLAG_STOP_AND_RELATIVE_T1_2026-06-09.md` · `CC_FIX3B_CHART_FORWARD_PROJECTION_2026-06-09.md` (הושלם).

═══════════════════════════════════════════════
## לקחי-Cowork מהיום (אל תחזור עליהם)
═══════════════════════════════════════════════
- **אל תכריז "תוקן" בלי לאמת בעצמך** — לבאג ויזואלי דרוש צילום-אחרי (אני בדקתי חי דרך Claude-in-Chrome). היו 2 טעויות: (1) אזעקת-IB-שווא מ-grep שטוח (היה תקין); (2) העברת FIX-3 "✅" של CC בלי לוודא — הצ'art נשאר שבור. ראה `[[feedback_verify_json_structure_before_claiming]]` + `[[feedback_verify_fix_touches_culprit]]`.
- **Rule 5 חל גם על CC**: "paste command+output", לא לקבל "✅".
- **המאונט של Cowork (sandbox bash) יכול להיות מיושן** מול ה-Mac החי — הצלב דרך Desktop Commander על ה-Mac האמיתי.

**הצעד הראשון בצ'אט הבא:** (1) ודא push מה-Mac. (2) אם RTH פתוח — אמת חי את שרשרת-הירי (פריט 1). (3) אחר כך S4-targets / FIX 6 / decision_tree.
