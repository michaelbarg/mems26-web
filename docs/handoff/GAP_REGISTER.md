# 🧭 GAP REGISTER — פנקס-פערים משותף (S1 · S2 · S4)

**פסיקת-מייקל 2026-07-19:** *"צריך מקום שכל הסוכנים יכולים להוסיף פערים ולבדוק אותם לפני
שהם נקבעים כבעיה."*

**זה המקום.** קובץ אחד, git-tracked. כל סוכן (cowork-dev · cc-macbook · cc-imac · cursor)
**מוסיף** פער חשוד כאן, ו**אף פער לא הופך ל"בעיה" עד שהוא אומת בקוד/דאטה (חוק-5).**
נבנה כי שלושה "פערים" כבר התבררו כ**פנטום** אחרי אימות (ה"פספוסים" של entry_not_confirmed =
מחיר-מעופש · "CVD לא מיוצא" = מפתח-JSON שגוי) — הפנקס הזה מונע לרדוף פנטומים.

## מחזור-החיים של פער (חובה)
```
🔵 SUSPECTED  → מישהו חושד. שורה עם system + תיאור + מצביע-ראיה + מי-מצא + תאריך.
🟡 VERIFYING  → מישהו בודק בקוד/דאטה עכשיו.
🟢 CONFIRMED  → אומת אמיתי. חייב שורת-ראיה (פקודה+פלט או file:line). רק אז הופך לפריט-עבודה.
⚪ PHANTOM    → נבדק ואינו בעיה. חייב שורת-ראיה שמפריכה. נשאר בפנקס (כדי לא לחזור אליו).
🔧 FIXED      → תוקן. שורת-ראיה = קומיט + אימות.
```

## 3 חוקי-הברזל
1. **אסור לקפוץ ל-🟢 CONFIRMED בלי שורת-ראיה** (פקודה+פלט גולמי, או `file:line` שמוכיח). הצהרה ≠ ראיה.
2. **פנטום נשאר בפנקס** עם ההפרכה — לא נמחק (אחרת מישהו יוסיף אותו שוב).
3. **חשד = בסדר גמור.** עדיף לרשום 10 חשדות ש-3 מהם פנטום, מאשר לפספס אחד אמיתי. אבל אל תטפל
   בחשד עד שאומת.

## איך מוסיפים פער (העתק שורה)
`| G-NN | S? | <תיאור בשורה> | 🔵 | <file:line או מסמך> | <מי-מצא> | 2026-07-NN |`

---

## 📋 הפנקס החי

| # | מע' | פער | סטטוס | ראיה / הפרכה | בעלים | תאריך |
|---|---|---|---|---|---|---|
| G-01 | S4 | Paint-lag: `current_bar` מנותב ל-S4 עם `trend_state` גולמי (בלי `_trend_from_cci`) → TT/GB100/ZLR-v2 עיוורים לצבע בראלי | 🔧 **FIXED** | **G1 בוצע (cowork, הוראת-מייקל):** `bars.py:1167` מחיל `_trend_from_cci` על `last_flat` של current_bar (כמו `:1087`), מגויט ב-TREND_CCI_DIRECT_V1 (OFF=byte-identical). 6 טסטים, flag_guard 91/91, restart health=200. commit 8dcb4a79. **הערה:** מנתב ל-S4 בלבד — לא ל-DB/UI (זה G-16) | cowork → ✅ | 07-19 |
| G-02 | S2 | S2 יורה מאוחר: 7 ברים מינ' (B1-B4+3 רקע) + FHB + avg20-נפח מורעל בגלובקס-דק | 🟢 **CONFIRMED** | אומת ע"י cowork (B2): `MIN_BARS_REQUIRED=7` (`five_min_system.py:34`); avg20 (`:658-659`) + `S2_VSA_VOLUME=1` **חי** → נתיב-מורעל פעיל | ממתין-גישה (מייקל) | 07-19 |
| G-03 | S4/S2 | `FIXED_CONTRACTS_4=1` מתעלם מפסק REDUCED של הפלייבוק | 🔧 **RESOLVED (פסיקת-מייקל 07-19: להשאיר 4 תמיד)** | `trading_gateway.py:633` — FIXED_4 כופה 4; REDUCED משפיע רק על allow, לא על גודל. **מייקל פסק: 4 תמיד, לא באג.** אין שינוי-קוד | מייקל ✅ | 07-19 |
| G-04 | S2 | A5 `OFA_Initiative ≠ INITIATIVE_LONG` → INITIATIVE over-fire על Normal | 🔧 **FIXED** | פסיקה-4: `S2_AUTH_MATRIX_SINGLE_SOURCE_V1=1`, auth_matrix בוטל, 14 טסטים, אפס-שינוי-התנהגות. commit 504d948d | — | 07-19 |
| G-05 | S2 | day-type מעופש על **שער-הזיהוי** של chart-patterns (`self.current_day_type`) בעוד נתיב-הפליטה מודע-override | 🟢 **CONFIRMED** | cowork אימת (07-19): `self.current_day_type` נכתב **רק** מ-`v9_day_type_state` (`:280`, המת) או event-bus (`:426`) — **אף פעם לא מ-`get_live_day_type`**. שער-הזיהוי קורא אותו ישירות: NT-skip (`:1139`) + `chart_patterns_allowed` (`:1180,:1192`). override מגיע ל-emit/sizing (`:1375,:1434`) אבל **לא** לזיהוי → override של מייקל ל-Neutral לא פותח reversal chart-patterns (בדיוק תלונת 07-17). אותה מחלקה כמו G-14 (S124 G3) | מייקל→cc · **S124 G2** | 07-19 |
| G-06 | S4 | A6 S4 day-type בלי override → T2/runner שגוי | 🔧 **FIXED** | פסיקה-5: `S4_OVERRIDE_AWARE_V1=1`, S4 קורא `get_live_day_type` ראשון, 5 טסטים. commit 634983c1 | — | 07-19 |
| G-07 | S4 | entry_not_confirmed "פספס" GHOST/FAMIR 07-17 | ⚪ **PHANTOM** | ה"פספוסים" = מחיר-מעופש (GHOST @7534.5 = מחיר מלפני שעה) מזיהום `v9_bars_5min`. תוצאה אמיתית: חסימה-1, gate-right. השער **נשאר** (פסיקה-2). הזיהום עצמו CONFIRMED+FIXED (ראה G-09) | — | 07-19 |
| G-08 | S2 | CONFLUENCE FULL בפלייבוק אבל flag OFF → תא-ירוק בלי ירי-חי | ⚪ **STALE** | `CONFLUENCE_RI_ZLR_LIVE=1` **חי ב-.env** → CONFLUENCE יורה חי. הפער התייחס למצב-ישן | — | 07-19 |
| G-09 | data | `v9_bars_5min` מזוהם בברי-מחיר-מעופש → ATR/סיווג-יום מנופחים | 🔧 **FIXED** | 2 שכבות: שומר-קליטה חוצה-מקורות (>15נק' מ-woodies→דחייה) + הידוק-TS-HOUR. אומת על 07-17: תפס 2/2 רפאים. commit ac8bb9a7 | — | 07-18 |
| G-10 | S1 | Sierra Study ID:1 bar-persistence Input — האם באמת 6? לא בריפו | 🔵 **SUSPECTED** | לא-מוכרע מהקוד (Bible U1). דורש צילום-Inputs מסיירה / מדידה-חיה | **מייקל** (צילום) | 07-19 |
| G-11 | S1/S2/S4 | מספרי against-Dalton 15/16/17 | 🟢 **CONFIRMED (partial) + אימות-cowork** | T1 via `/chart/replay`: 21 trades w/VA · "10 against" **אך cowork אימת: over-count** — 2 הימים היו Normal_**Variation** (CONT=with-expansion ב-D0); הווׁשורטים-below-value שניצחו (07-17 כל 5, +$225) הם **תואמי-D0** לא נגד. **against אמיתי ~3** (ZLR-longs near-VAH 07-15 שהפסידו). **הנתונים מאמתים D0: with-expansion ניצח, against הפסיד.** מספר-מדויק דורש audit_pattern_miss (PG trust-restart). Doc `PATTERN_INTEL_NUMBERS_2026-07-19.md` | cursor→cowork ✅ | 07-19 |
| G-12 | S2 | BE/runner wiring מ-`daytype_style.stop_be_early` — לא עוקב עד trade_manager בכל נתיב | 🔵 **SUSPECTED** | לא-מוכרע (Bible U4). דורש מעקב-קוד מ-YAML→manager | ממתין-בעלים | 07-19 |
| G-13 | S1 | האם YELLOW בכלל מגיע מ-DLL החי? | 🟢 **CONFIRMED (absent on 15–17)** | T4: `chart/replay.trend` counts YELLOW=**0** על 15/16/17 (BLUE/RED/GRAY בלבד). Doc `PATTERN_INTEL_S1_T4_T5_2026-07-19.md`. נעילת-YELLOW כנראה inert בחלון זה | cursor→cowork | 07-19 |
| G-14 | S2 | Flag T2 fork קורא `self.current_day_type` (`five_min_system.py:1551`) בעוד emit כבר `get_live_day_type` → יעדי T2 לא תואמים override/live | 🟢 **CONFIRMED** | `file:line` אומת cursor-agent 07-19; אותו מחלקת-פער כמו G-05 | מייקל→cc · **S124 G3** | 07-19 |
| G-15 | S1 | `DAYTYPE_HONEST_PRELOCK_V1` default OFF → תווית ישנה פרה-IB יכולה לעבור ב-`get_live_day_type` | 🟢 **CONFIRMED** | `trade_context.py:559-573`; דגל קיים, לא הודלק | מייקל(הדלקה) · **S124 G4** | 07-19 |
| G-16 | S1/UI | TopBar/DayTypeLens קוראים `classify_replay` בלי override/antiflap → תצוגה ≠ שערי-מסחר. **מורחב 07-19:** גם טרנד-חי UI (`/woodies/chart` Sierra raw) ≠ G1 `_trend_from_cci` על current_bar; DirectionStrip.`dir` ✅ אבל `dir_sustained` לא מוצג | 🟢 **CONFIRMED** | ביקורת `UI_CONSISTENCY_AUDIT_2026-07-19.md` (cursor): `useLiveDayType.ts:46` · `systemStateStore.ts:57-69` · `WoodiesCciPanel.tsx:81,1069` + `woodies_chart_routes.py:85-86` · `bars.py:1161-1168` (G1 לא ל-DB/UI). P0=paint+day-type | מייקל→cc · **S124 G5** (+paint נפרד) | 07-19 |
| G-17 | S4 | אחרי כשל `get_live_day_type`, נסיגה ל-`v9_day_type_state` ואז `"Normal"` (סינתזה) | 🟢 **CONFIRMED** | `woodies_system.py:672-688`; SoT מסמן טבלה לא-למסחר; A6 תיקן רק עדיפות ראשונה | מייקל→cc · **S124 G6** | 07-19 |
| G-18 | S1 | Neutral=sides==2; escalation = **Acceptance דו-כיווני (A)** | 🟢 **SIGNED A (מייקל 2026-07-20)** | `G8_NEUTRAL_ESCALATION_DOCTRINE_2026-07-19.md` · classifier · shadow לוג-בלבד | מייקל · **S124 G8** | 07-20 |

**תור-סגירה מסודר (cursor):** `LIVE_CHANNEL` §🔴 S124 GAPS · ביקורת `S1_SOURCE_AND_DAYTYPE_AUDIT_2026-07-19.md` · CC `CC_PROMPT_S124_GAPS_2026-07-19.md`. מיפוי: S124 G1↔G-01 · G2↔G-05 · G3↔G-14 · G4↔G-15 · G5↔G-16 · G6↔G-17 · G7↔G-03 · G8↔G-18. (G-02 S2-late = מחוץ לתור S124 — גישה נפרדת.)

**נסגרו/הופרכו מיידית (07-19, אימות-cowork):** ה-SPEC-flags **כולם דלוקים** (`ZLR_SPEC_V2=1 ·
VEGAS_SPEC_V2=1 · S2_VSA_VOLUME=1 · DIRECTION_CONTEXT=1 · DAYTYPE_LOCATION_GATE=1`) → Bible-U3
מוכרע, ו-`audit_pattern_miss` (שמניח ON) תואם-מציאות.

## סיכום-מצב (07-19, אחרי S124)
- **🟢 CONFIRMED פתוחים:** G-01 (paint), G-02 (S2-late), G-03 (REDUCED), G-05 (stale detect),
  G-14 (Flag T2), G-15 (honest prelock), G-16 (UI SoT), G-17 (S4 fallback), G-18 (דוקטרינה).
- **🔧 FIXED:** G-04, G-06, G-09.
- **⚪ PHANTOM/STALE:** G-07, G-08.
- **🔵 SUSPECTED:** G-10..G-13.
- **תור-עבודה למייקל:** אשר סדר ב-LIVE_CHANNEL S124 G0, ואז `לתקן`/`לדחות` לכל פער — אל תתחיל מקצה בלי פסיקה.
