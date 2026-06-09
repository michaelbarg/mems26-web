# CC PROMPT — Independent Verification of Cowork's Work (Adversarial QA) · 2026-06-02

**מאת:** Michael → **אל:** Claude Code
**מטרה:** בקרה **בלתי-תלויה ועוינת** על כל מה ש-Cowork (סוכן ה-Cowork) ייצר וטען ב-2026-06-01. **אל תסמוך על הדוחות/הפרומפטים של Cowork** — אמת כל טענה מחדש מול קוד/DB/git. המטרה: לתפוס טעויות לפני Day 2 כדי שלא יהיו תקלות.

> **חוקי הבקרה (חובה):**
> - **Read-only.** אל תתקן כלום בפרומפט הזה — רק אמת ודווח. תיקונים = פרומפט נפרד אחרי שמיכאל רואה את הממצאים.
> - **Rule 5:** לכל טענה — הדבק `command + raw output`. אסור "נראה נכון".
> - לכל טענה תן verdict: **MATCH** (אומת) · **MISMATCH** (שגוי — פרט) · **CANNOT-VERIFY** (חסר נתון/דורש RTH חי).
> - **עדיפות:** אם אתה מוצא MISMATCH אחד שמשנה את תוכנית Day 2 — עצור והבלט אותו בראש הדוח.

## הקבצים שנוצרו ע"י Cowork (מושאי הבדיקה)
- `docs/reports/AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md`
- `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`
- `docs/reports/DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`
- `docs/reports/DECISION_BRIEF_WOODIES_ZLR_HFE_TREND_2026-06-01.md`
- `docs/handoff/CC_MEGA_PROMPT_REACTIVE_CHECK_FIX_DISPLAY_2026-06-01.md`
- `docs/handoff/CC_MEGA_PROMPT_S1_DAYTYPE_DYNAMIC_2026-06-01.md`
- `docs/handoff/CC_MEGA_PROMPT_BUILD_STATUS_OBSERVABILITY_2026-06-01.md`
- `docs/handoff/CC_PROMPT_FIRE_AUDIT_DIAGNOSIS_AND_READINESS_GATE_2026-06-01.md`
- `docs/plans/DECISION_LEDGER.md` · עריכות ב-`STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`

---

## A · הטענה הקריטית ביותר — partial-wiring של תיקון D-WDIAG (`1c0397a`)
Cowork טען: ה-override (`woodies_system.py` ~358) משנה את `_ts` ואת `current_state["trend_state"]`, אבל ה-`decision_tree._a1_trend_gate` (`decision_tree.py:176`) קורא `ctx.studies.get("trend_state")` — הערך הגלמי שלא שונה → trend_state לא עקבי בין נתיבים.
**אמת בלתי-תלוי:**
1. `git show 1c0397a` — מה בדיוק שונה? האם נכתב ל-`studies["trend_state"]` או רק ל-`_ts`/`current_state`?
2. ב-`process_bar`: ה-`WoodiesDecisionContext` נבנה עם `studies=studies` — האם `studies["trend_state"]` הוא הערך הגלמי (מ-`bar.get("trend_state")`) או המעודכן? (קרא ~251-294).
3. `decision_tree.py:176` `_a1_trend_gate` — קורא `ctx.studies` או `ctx.current_state`?
4. **מסקנה:** האם ה-override מגיע ל-gate שקובע `ready_to_route`, או נעצר ב-dispatcher בלבד? verdict: האם טענת ה-partial-wiring של Cowork נכונה?
5. בדוק גם: האם השינוי **מאחורי דגל**? יש מתג revert? יש טסט שמכסה את ה-override?

## B · D-RVX לא בוצע
Cowork טען: אין commit ואין דוח ל-Reactive. אמת: `git log --all | grep -iE 'RVX|reactive.var'` · `find . -name '*reactive_variant*'` · `ls docs/reports | grep -i RVX`. verdict: בוצע / לא בוצע.

## C · D-OBS read-only?
Cowork טען `691c99b` הוא observability בלבד, אפס לוגיקת-מסחר. אמת: `git show 691c99b --stat` — האם נגע **רק** ב-build_status/frontend, או גם בקבצי firing/risk/detector? verdict.

## D · D-S1DYN shadow-only?
אמת: (1) `S1_DYNAMIC_RECLASS` default OFF? (2) כשהדגל OFF — ה-day_type החי **זהה-בייט**? (3) `shadow_reclass.py` כותב רק ל-`v9_day_type_shadow_transitions` ולא נוגע ב-day_type שמוזן ל-Auth Table? (4) commits `caeb984`/`df16d03`/`9d8ff30` קיימים? verdict לכל.

## E · עיגון הקוד ב-Decision Briefs — האם המספרים/שורות נכונים?
דגום ואמת (MATCH/MISMATCH) מול הקוד:
- Reactive brief: `DROP_THRESHOLD_PCT=0.10` (`five_min_system.py:30`?) · `LOOKBACK_MAX_VOL_RATIO=0.6` · גייט בר2 ב-`_detect_reactive`.
- S1 brief: `_check_reeval` `move_30=None` (~783) · אין עמודת `atr` ב-`v9_bars_5min` (`PRAGMA table_info`) · `_rescore_from_behavior` (~660) · B6 conf-gate `>0.15` (~643).
- Woodies brief: `zlr.py` דורש `current>prev` (Impl B) · `hfe.py` ±200/hook≥50/AP5[2,12] · HFE לא ב-`PATTERN_TIER` → default 'low'.
- Fire-audit: IB width 20.5 (7596.5−7576.0) · E_up=1.77 · R=2.77 — חשב מחדש ואמת.

## F · אין נתיבי-קבצים מומצאים
סרוק את כל ה-prompts/briefs של Cowork אחר הפניות לקבצים/שורות — האם כל קובץ/פונקציה שמוזכרים **קיימים** בפועל? רשום כל הפניה שבורה.

## G · עקביות מסמכי המעקב
`DECISION_LEDGER.md` מול `STATUS_BOARD.md` מול `ROADMAP_TO_LIVE.html`: האם הסטטוסים (D-RVX/D-S1DYN/D-WDIAG/D-RDY/D-OBS) **עקביים** ביניהם ותואמים למצב git בפועל? רשום כל סתירה.

## H · בדיקת over-claim בדוח ה-fire-audit
Cowork תיקן את עצמו (D-WDIAG: 73/73 DLL ZLR עם bounce → ה-"8 ZLR שפוספסו" לא היו pullback לא-תקפים). אמת את ה-73/73 מ-DB (`v9_bars_5min_woodies`/signals). verdict: האם ה-self-correction נכון?

---

## פלט נדרש
טבלה: `סעיף · טענת Cowork · verdict (MATCH/MISMATCH/CANNOT-VERIFY) · raw evidence`. ואז: **רשימת MISMATCH ממוינת לפי השפעה על Day 2**. בלי תיקונים — רק ממצאים. אם A מאשר partial-wiring → זה הפריט מספר 1.
