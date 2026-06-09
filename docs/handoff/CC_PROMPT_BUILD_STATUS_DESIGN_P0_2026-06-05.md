# CC — Build Status · עיצוב P0 + B-11 + stale-handling · 2026-06-05

חוזה `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. VERIFY file בסיום. הבסיס
(BuildTreeView, route `/build`) כבר committed — זה השלמה, לא בנייה-מחדש.

**🎨 מקור-עיצוב ויזואלי (חובה — בנֵה לפיו, פיקסל/טוקן):**
`docs/plans/BUILD_STATUS_REDESIGN_MOCKUP_V2_2026-06-04.html` — ה-V2 mockup עם ההפניות
"לתיקון" וטבלאות-האפיון. spec משלים: `BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md`.

## 1. 🔴 B-11 — הלוח משקר (קודם כל)
`bridge_inspector.py:82,204` `ORDER BY rowid DESC` (SQLite-only) → PG זורק → כל 8 הזרמים
`no_data`/Bridge OFFLINE/0-armed **שקרי**, למרות שהגשר משדר (כל שורה מראה `fresh <1s`).
**תקן `rowid`→`{ts_col}`** (2 מקומות) + regression anti-tautological (revert→RED
`column "rowid" does not exist`). **אימות:** הלוח מציג streams חיים + Bridge לא-OFFLINE.

## 2. 🟡 stale-handling — להציג טריות אמיתית
בצילום: `day_type_gate` fresh<1s אבל `pattern_specific/r_t1/stop/targets/ready_to_route`
כולם **`stale 5m`**. צריך: (א) לאבחן **למה** ערכי-Woodies בני-5-דק' (האם woodies_5min לא
מתרענן? snapshot תקוע?) — דווח root; (ב) ב-UI להבדיל ברור **stale** מ-**fresh** כך שלא
מתבלבלים בין "אין נתון" ל"נתון ישן". *(אבחון = read-only; תיקון-מקור-הטריות → דווח לפני.)*

## 3. 🟡 השלמת P0 (לפי `BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md` V2)
רינדור השלבים החסרים פר-מערכת:
- `pre_fire_validator` (7 בדיקות) — לא placeholder.
- `risk_checks` caps (loss/trades/contracts/cutoff 15:00 CT/2-consec) — לא placeholder.
- Day-Type Matrix verdict ל-S4 (✅/⚠️/❌ פר pattern×day_type + entry_hint + t1_ref).
- חיווט S5 (TPO) ו-S6 (Killzone) כ-gates (כרגע לא מחווטים ל-aggregator).
- **A5 כ-advisory** (לא חוסם — כבר תוקן ב-decision_tree; ודא שה-UI מציג בהתאם).

## 4. עיצוב — עץ אחיד פר-מערכת (מתחבר ל-I-10)
כל מערכת (S2/S3/S4) תציג עץ A1–A7-שקול עם מה-מתקיים/מה-חסם/מה-stale. (S2/S3 חסרי-עץ —
תיאום עם `DECISION_TREE_MAP_2026-06-05.md`; בנייה מלאה = משימה נפרדת, כאן רק להציג מה שיש.)

## VERIFY (raw output)
- B-11: `grep "ORDER BY" bridge_inspector.py` = `{ts_col}` ב-2 המקומות + regression RED→GREEN +
  צילום-לוח עם streams חיים.
- stale: root-דיווח למה Woodies stale 5m + צילום שמבדיל stale/fresh.
- P0: צילום שמראה pre_fire/risk_checks/Day-Type-Matrix מרונדרים (לא placeholder).
- NOT-DONE: S5/S6 wiring אם לא הושלם; בניית-עץ S2/S3 (נפרד).

## גבולות
frontend + bridge_inspector בלבד · אל תיגע בלוגיקת-מסחר/risk-VALUES · smallest correct change.
