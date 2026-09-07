# ריפליי-נגדי אחרי תיקוני 07.09 — 10 ימי-הלייב 24.08→04.09 (חשבון 37138283)

**מאת:** cowork-dev (סוכן-משנה, קריאה-בלבד) · **07.09.2026** · **שאלת-מייקל:** *"במצב הקיים, אם היינו עושים ריפליי — כמה כסף היינו עושים?"*

**מקורות-אמת:** פילויי-ברוקר מ-`~/SierraChart/TradeActivityLogs/TradeActivityLog_<date>_UTC.37138283.data` (פרסר `scripts/sierra_activity_join.py`, join על `InternalOrderID`; P&L לרגל = (פילוי-יציאה − פילוי-כניסה)×qty×$5 — חסין ל-FIFO של החשבון המשותף) · ברים `v9_bars_5min_woodies` · דלתא `v9_bars_cumulative_delta` · מזהי-קבוצות/יעדים-מבניים/סוג-יום מ-`v9_trades.quality` (מזהים בלבד; `pnl_usd` **לא** צוטט — T-160) · היסטוריית-מחירי-פקודות (שדות TLV 110/111) מאותו יומן-ברוקר · `gateway_decisions.<date>.jsonl` (ארכיון + חי). **הצל לא צוטט.** אפס כתיבה ל-DB/קוד/`.env`; הסקריפטים ב-`outputs/` של סשן-ה-Cowork (`replay_lib.py`, `replay_after_fixes.py`, `replay_entry_gates.py`, `probe_s2_dead.py`), הפלט הגולמי בנספחים למטה.

**כללי-שמרנות שהופעלו:** מילוי-יעד רק כשהמחיר עבר **דרך** הרמה (H>T / L<T; נגיעה-מדויקת ≠ מילוי) · בר שנוגע ביעד **וגם** הוא בר-היציאה-בסטופ ⇒ סטופ · יעד שלא נגע ⇒ כמו-בפועל · MFE לא נספר · תיקון שמרע (יעד מבני קרוב יותר, שחזור שמבטל גרירה-שעזרה) **נספר בסימנו**.

---

## A · תיקוני-יציאה — מדיד ביושר (§2 · §3 · §4 · §6)

**מה נבדק:** 38 עסקאות-לייב עם פילויים (108 רגליים/קבוצות-OCO) ב-8 ימי-מסחר; 24-25.08 = אפס עסקאות. לכל רגל: יעד-חדש לפי התיקון ⇒ האם נגע בחלון-העסקה ⇒ P&L חדש ממחירי-ברוקר.

| יום | n | ברוקר-בפועל (מערכת) | אחרי §2-§4 | **אחרי §2-§6** | **Δ** | איזה תיקון תרם (סדרתי §4→§3→§2→§6) |
|---|---|---|---|---|---|---|
| 24.08 | 0 | 0 | 0 | 0 | 0 | אין עסקאות (10 מועמדים-מנותבים נעצרו ב-`pre_send_entry_guard` — פוזיציה זרה; חשבון-כולו −695.00) |
| 25.08 | 0 | 0 | 0 | 0 | 0 | אין עסקאות (0/34 החלטות-שער עברו; חשבון-כולו +426.25) |
| 26.08 | 4 | +118.75 | +77.50 | +77.50 | **−41.25** | §3 −41.25: #812 רגל-T2 → struct_c2 7693.75 ממלא ב-14:45 (+$23.75) במקום פלאטן-EOD @7702 (+$65) |
| 27.08 | 5 | +203.75 | +207.50 | +207.50 | **+3.75** | §4 −27.50: #830 שחזור-יעד מבטל גרירה שעזרה (7729.25→7734.75) · §3 +31.25: אותה רגל → struct_c2 7728.5 |
| 28.08 | 8 | +437.50 | +426.25 | +426.25 | **−11.25** | §4 +45.00: #851 T2 שחזור 7726.75 (נגע 12:15) · §3 −56.25: #851 → struct_c2 7738 (קרוב מדי, ממלא בבר-הכניסה) |
| 31.08 | 7 | −100.00 | −100.00 | −100.00 | **0** | 875/877 (5c) `day_type=None` + אין `spacing_levels` ⇒ §2/§3 לא חלים · 5 ילדי-SCALE_IN · ZLR 936/939 יעדים מבניים לא נגעו |
| 01.09 | 3 | −240.00 | −178.75 | −101.50 | **+138.50** | §4 +61.25: #942 T2 שחזור 7672.75 (נגע 10:35, במקום BE −1.25) · §6 +77.25: #948 ×0.4 |
| 02.09 | 4 | +31.25 | +106.25 | +128.75 | **+97.50** | §4 +6.25 (#953 −37.5 גרירה-שעזרה · #971 +43.75) · §3 +23.75 (#971 T2 → 7687.25, נגע 14:15) · §2 +45.00 (#953 ראנר → c3-מוסט = t2 7686.75, נגע 10:40) · §6 +22.50 (#953 −102 · #963 +82.5 · #968 +42) |
| 03.09 | 2 | −283.75 | −283.75 | −283.75 | **0** | #981 סקראץ' בלי struct · #987 struct_c2 7721 לא נגע (סטופ 13:33) |
| 04.09 | 5 | −116.25 | −32.50 | −49.75 | **+66.50** | §4 +51.25: #1073 T2 שחזור 7715 (נגע 13:40; הנגרר 7708.5 הוחמץ) · §3 −18.75: אותה רגל → struct_c2 7718.75 · §2 +51.25: #1073 ראנר → struct_c3 7715 · §6 −17.25 (#998 +75 · #1073 −92.25) |
| **Σ 10 ימים** | **38** | **+51.25** | **+222.50** | **+305.00** | **+253.75** | §4 **+136.25** · §3 **−61.25** על-גבי §4 (לבדו +51.25) · §2 **+96.25** · §6 **+82.50** |

**ליום:** בפועל **+$5.1/יום** ⇒ אחרי-התיקונים **+$30.5/יום** ⇒ **Δ = +$25.4/יום** (10 ימים). כל ה-Δ יושב ב-**3 ימים** (01/02/04.09) ובעיקר ב-**4 עסקאות**: #942 (+61.25), #971 (+67.50), #1073 (+83.75 יציאות), ו-§6 על 4 מפסידות (+276.75) פחות §6 על 2 מנצחות (−194.25). 5 ימים מתוך 8 = Δ≤0. (החשבון-כולו ב-10 הימים: +152.50 — ההפרש מהמערכת = פעילות-ידנית/אתי, מנופה לפי `InternalOrderID`.)

**מה נגע ומה לא (n):**
- **§2 ראנר-לפי-סוג-יום:** 8 רגלי-ראנר זכאיות (5c, לא-ZLR, סוג-יום ידוע ולא-Trend) ⇒ **2/8 נגעו** (#953 t2-fallback, #1073 struct_c3 7715), **6/8 לא נגעו** (948 7682.5 · 950 **7541.75** · 971 7690.5 · 1008 **7625.5** · 1069 7758.5 · 1141 7752.25). שני struct_c3 של S2 יושבים ~100 נק' מהכניסה — "יעד" שהוא למעשה ראנר-בלי-יעד.
- **§3 יעדים-מבניים (רגלי t2/t3 + הרגל-האחרונה של ZLR):** 15 רגליים זכאיות ⇒ **5 שינו P&L: 3 למעלה (#830 +3.75 · #971 +67.50 · #1073 +32.50) / 2 למטה (#812 −41.25 · #851 −11.25)**. struct_c2 לעיתים **קרוב יותר** מ-t2 (812, 851, 1073) ⇒ מקצר רווח.
- **§4 שחזור-יעד אחרי MODIFY_STOP:** סריקת יומן-הברוקר: **ה-DLL גורר את היעד בכל MODIFY_STOP — 19 אירועים / 14 רגליים / 14 עסקאות ב-10 ימים** (לא "3/3"): 812·830·838·851·859·862·873·877·942·953·971·1008·1069·1073. 6 רגליים שינו P&L: **4 למעלה (#851 +45 · #942 +61.25 · #971 +43.75 · #1073 +51.25) / 2 למטה (#830 −27.50 · #953 −37.50** — שם הגרירה הרחיקה את היעד והמחיר הגיע אליו). #1008 (השלישית בפקודה): היעד המקורי 7706/7707.25 **לא נגע** אחרי ה-BE ⇒ 0 מ-§4.
- **§6 סייז:** 6 העסקאות (948·953·963·968·998·1073; `metadata.sizing_contracts=2`/`sizing=2`) ×0.4 על P&L-אחרי-יציאות: Σ −137.50 ⇒ **−55.00** (Δ +82.50). §6 **לבדו** על הבפועל: −228.75 ⇒ −91.50 (Δ +137.25). קירוב: סולם-2-חוזים אמיתי שונה (אין T0).

**🔴 שני סייגים שמשנים את המספר — ה-Δ מודד את ה-SPEC, לא את הקוד שנחת:**
1. **§2 אינרטי בקוד:** `backend/v9/services/sierra_command.py` — הבלוק של `RUNNER_BY_DAYTYPE_V1` (‏:985) מציב `_c4_target=struct_c3`, ואז הבלוק של `RUNNER_TRAIL_V2` (‏:1031, `.env:98`=1) מציב **`_c4_target=None`** ללא-תנאי ל-`contracts>=4`. **הוכחה מריצה (נספח 3; `write_trade_command` נעטף ללכידה, אפס קובץ ב-`command_queue/`):** `RUNNER_TRAIL_V2=1 → c4=None runner_stop_only=c4` למרות הלוג `§2 … c4=7715.0 (struct_c3)`; `RUNNER_TRAIL_V2=0 → c4=7715.0`. הטסט `test_runner_by_daytype.py` הוא grep-בלבד. ⇒ **+96.25 של §2 = 0 בקוד הנוכחי.**
2. **§4 אינרטי בקוד:** `backend/v9/services/trade_manager/manager.py:386` קורא `quality.c{n}_target_price`; `SELECT count(*) FROM v9_trades WHERE quality ? 'c1_target_price' OR quality ? 'c3_target_price'` ⇒ **0**; `grep -rn "_target_price" backend/v9 --include=*.py` ⇒ הקורא בלבד, **אין כותב**. ⇒ `_expected is None → continue` על כל רגל ⇒ **+136.25 של §4 = 0 בקוד הנוכחי.** ובנוסף "לאמת שהסטופ לא זז" (‏§4 בפקודה) הוא **הערה בקוד, לא קוד**.

**סייגים נוספים (מוצהרים, לא נספרו):**
- **באג-המראה (MODIFY_TARGET של TARGET_REALISM גורר את הסטופ):** 3 מקרים: #1008 T2 סטופ-BE 7716.75→7724.75 ⇒ **−$40** (זה מקור ה-−42.50, לא היעד) · #862 T2 7720.25→7729.75 ⇒ −$26.25 · #820 7695.5→7688.25 ⇒ **+$31.25** (עזר). Σ +35.00, n=3 — אינו ב-§4 כפי שנחת.
- **§3 בקוד מזיז גם T1→struct_c1** (2 מ-5 חוזים בכל 5c, ושתי רגלי-T1 של ZLR): מכני −31.25 (15 רגליים) — אבל זה משנה את טריגר-ה-SMART_BE ⇒ מסלול-הסטופ ⇒ **לא ניתן להכרעה.**
- 1 רגל (#859 g3) "יעד-ישן נעלם ולא נגע" ⇒ כמו-בפועל (±$2.50). כל ימי 26-28.08 היו 2-3 חוזים (לפני פסיקת-5) ⇒ אין T0/ראנר-§2 שם.

---

## B · תיקוני-כניסה (§5 · §7) — לא ניתן להמיר לדולרים

**אוכלוסייה:** 810 שורות-חסימה גולמיות (`entry_location_quality` + `awaiting_release`) ⇒ **149 מועמדים** אחרי דדופ (יום, pattern, direction, bar5, gate). הלוגיקה-החדשה הופעלה מחדש על כל מועמד: **§5** = `leg_base` מהקצה-השבור של ה-IB כש-`accepted_break` (מחושב מחדש עם `level_acceptance()` של הריפו על ברים-סגורים: PDH/PDL · VA-קודם · IB) תואם לכיוון; L<1.0 ⇒ דילוג-מיקום (כמו בקוד `trading_gateway.py` ~:1880-1899) · **§7** = בבר-המועמד: דלתא = מקסימום-חלון-30-הברים בכיוון-השבירה **וגם** ווליום ≥ 0.7×מקסימום-החלון (בדיוק שאילתת-הקוד: `ORDER BY ts DESC LIMIT 30`, כולל טרום-שוק), רק כשיש `accepted_break` תואם. `t1_before_stop`: חלון 60 דק', בר-שנוגע-בשניהם = STOP (`blocked_candidate_audit.judge`).

| יום | ELQ נחסמו | **עוברים §5** | release נחסמו | **עוברים §7** | t1_before_stop (עוברים) |
|---|---|---|---|---|---|
| 24.08 | 0 | 0 | 13 | 0 | — |
| 25.08 | 0 | 0 | 6 | 0 | — |
| 26.08 | 0 | 0 | 5 | 0 | — |
| 27.08 | 0 | 0 | 7 | 0 | — |
| 28.08 | 0 | 0 | 10 | 0 | — |
| 31.08 | 0 | 0 | 20 | 0 | — |
| 01.09 | 0 | 0 | 17 | 0 | — |
| 02.09 | 0 | 0 | 11 | 0 | — |
| 03.09 | 31 | **3** | 15 | 0 | 2 T1 / 1 STOP (n=3 <10) |
| 04.09 | 2 | 0 | 12 | 0 | — |
| **Σ** | **33** | **3 (9%)** | **116** | **0 (0%)** | **2/3 — NOT_JUDGEABLE (n<10)** |

- **ELQ חוסם רק מ-03.09** (‏`ENTRY_LOCATION_QUALITY_V1` shadow→1 ב-03.09 07:30) ⇒ אוכלוסיית-§5 = יומיים בלבד. 3 העוברים (03.09): TREND_STEP 10:00 @7722 (STOP; ⚠️ IB עוד לא נסגר ב-10:00), **GB100 11:00:01 @7718.25 (T1)**, **DDBL LONG 11:02:34 @7722.5 (T1)** — העוגן של הפקודה. למה רק 3/33: 10 נחסמו גם ב-`beyond_value` (‏§5 לא נוגע) · 4 בלי `accepted_break` תואם · 16 עדיין pos>0.66 גם מהקצה-השבור (‏0.82-0.99).
- **§7 — 0/116:** 67 מועמדים = שבירה **נגד** כיוון-המועמד (‏§7 לא מחליט; למשל 111 שורות DDBL-**SHORT** ב-03.09 12:xx בעוד `accepted_break=UP`) · 24 בלי `accepted_break` · 21 נכשלו על דלתא/ווליום · 3 בלי דלתא. **§7 לא נפגש עם חסימת-`awaiting_release` אחת ב-10 ימים.**
- **סריקת-ברים §7 (בר-סגור, accepted_break מברים-סגורים לפניו): 15 ברים ב-10 ימים** (CC: 16). מה היה בהם: 03.09 11:00 ⇒ **47 חסימות ELQ** (אשכול-ה-DDBL + GB100) · 03.09 14:00 ⇒ 1 ELQ · 25.08 15:50 / 28.08 15:55 ⇒ `eod_entry_cutoff` · 01.09 13:25 ⇒ `daytype_playbook`×2 · 10 ברים ⇒ אפס מועמדים. ⚠️ **חולשה שנמצאה:** אין בדיקת-סימן לדלתא — 25.08 09:45 "שחרור-LONG" על דלתא **−479** (מקסימום של חלון בן 3 ברים). ⚠️ אין script-שחזור של CC בריפו (16 = ספירת-ברים, לא מועמדים).

**העוגנים שהפקודה דרשה:**
- **03.09 18:00 IL (11:00 ET):** O 7718.25 H 7730.5 C 7730.25 · vol **22,284** ≥ 0.7×28,007=19,605 ✓ · delta **+4,130** = מקס-חלון ✓ · `accepted_break=UP/PDH` (לפני הבר) ✓ ⇒ **§7 מזהה — ברמת-בר.** אבל **46 מועמדי-DDBL-LONG ב-18:00-18:05 נחסמו ב-`entry_location_quality` (chaser 0.86-0.99), לא ב-`awaiting_release`** ⇒ השער שלהם הוא §5; בשרשור §5→§7 (ברמת-בר) עוברים שניהם: DDBL @7722.5 + GB100 @7718.25, `t1_first=T1` לשניהם — ואז עוד ~17 שערים שלא ניתן לשחזר (T-244).
- **04.09 17:40 IL (10:40 ET):** delta −3,763 = מינימום-חלון ✓ · vol **17,087 < 18,675** ✗ · **וגם `accepted_break=None`** ב-10:40 (IB 7729.5/7751 נשבר באותו בר — אין 2 סגירות) ⇒ §7 לא מזהה, פעמיים. 0 מועמדי-release בבר.

**הקשר (מה השערים סירבו, בלי קשר לתיקונים):** `awaiting_release` 10 ימים (דדופ) `t1_before_stop` **54/88 = 61%** (28 לא-הוכרעו) · `entry_location_quality` **7/14 = 50%** (19 לא-הוכרעו).

**תנאי-ההדלקה של §7** (‏`t1_before_stop≥60%` על `n≥10` + שני העוגנים) ⇒ **לא עומד: n=0, עוגן אחד מזוהה (ברמת-בר), השני לא.** נשאר `shadow`.

---

## C · שורה כנה

**Δ-היציאות = כסף שהיה שם. הכניסות = כיוון, לא סכום. "פגענו במטרה" נמדד בשלישי.**

**מה שהמספרים אומרים:** ‎+$254 ל-10 ימים (‎+$25/יום) על בסיס ‎+$51 — כולו מ-4 עסקאות ב-3 ימים, ו-‎+$232 מתוכו (§2+§4) יושב בשני מנגנונים שכפי שנחתו **אינם רצים** (‏`RUNNER_TRAIL_V2` דורס את §2 · `c{n}_target_price` לא נכתב ⇒ §4 לא משחזר) ⇒ לפני שלישי שני תיקוני-שורה + סים, ולצפות לעשרות דולרים ליום, לא מאות.

---

## נספחים — פלט גולמי (Rule 5)

**שיטת-ההרצה:** כל הפקודות מ-`cd /Users/michael/Downloads/mems26_web_git && export PATH="/Applications/Postgres.app/Contents/Versions/18/bin:$PATH" && python3 <outputs>/<script>.py`. אפס כתיבה.

### נספח 1 · מנוע-היציאות — לכל עסקה/רגל, סריקת-גרירה, באג-המראה, פר-יום (`replay_after_fixes.py`)

```text
=== PER-TRADE / PER-LEG ===

#809 2026-08-26 10:00 S2 LONG INITIATIVE_LONG dt=None c=2 sizing=2 struct=- exit=STOP_FILL final=10:12:25
   actual=-47.50 after_exits=-47.50 (phys -47.50) after_all=-47.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7698.75 tgt0=7703.5 [STOP@7694.0x1(10:12:25)] pnl=-23.75 → after=-23.75
   g2 T2     q=1 e=7698.75 tgt0=7714.5 [STOP@7694.0x1(10:12:25)] pnl=-23.75 → after=-23.75

#812 2026-08-26 13:25 S2 LONG INITIATIVE_LONG dt=Variation c=2 sizing=2 struct={'struct_c1': 7690.5, 'struct_c2': 7693.75, 'struct_c3': 7702.0} exit=phantom_reconcile final=15:50:07
   actual=+96.25 after_exits=+55.00 (phys +55.00) after_all=+55.00 | Δ§2=+0.00 Δ§3=-41.25 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=-23.75
   g1 T1     q=1 e=7689.0 tgt0=7695.25 [TGT@7695.25x1(14:47:01)] pnl=+31.25 → after=+31.25
        [sens §3-T1 tgt=7690.5: nearer→fills at new target → +7.50]
   g2 T2     q=1 e=7689.0 tgt0=7701.5 [FLAT@7702.0x1(15:50:07)] pnl=+65.00 → after=+23.75
        §3 tgt=7693.75: touched 14:45 before exit → fills → +23.75
        §4 tgt=7702.0 drag=7702.0→7709.5 @14:47:08: touched 15:00 before exit → fills → +65.00

#818 2026-08-26 14:47 S2 LONG SCALE_IN dt=None c=2 sizing=None struct=- exit=phantom_reconcile final=15:50:07
   actual=+76.25 after_exits=+76.25 (phys +76.25) after_all=+76.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7695.25 tgt0=7705.5 [TGT@7703.75x1(15:02:28)] pnl=+42.50 → after=+42.50
   g2 RUNNER q=1 e=7695.25 tgt0=None [FLAT@7702.0x1(15:50:07)] pnl=+33.75 → after=+33.75

#820 2026-08-26 15:12 S2 LONG SCALE_IN dt=None c=2 sizing=None struct=- exit=SIERRA_FLAT final=15:50:07
   actual=-6.25 after_exits=-6.25 (phys -6.25) after_all=-6.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7703.0 tgt0=7714.75 [FLAT@7701.75x1(15:50:07)] pnl=-6.25 → after=-6.25

#822 2026-08-27 09:55 S2 LONG OPENING_ORR dt=None c=2 sizing=None struct=- exit=STOP_FILL final=09:56:59
   actual=-95.00 after_exits=-95.00 (phys -95.00) after_all=-95.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7723.0 tgt0=7731.25 [STOP@7713.5x1(09:56:59)] pnl=-47.50 → after=-47.50
   g2 T2     q=1 e=7723.0 tgt0=7740.25 [STOP@7713.5x1(09:56:59)] pnl=-47.50 → after=-47.50

#824 2026-08-27 10:15 S4 LONG ZLR dt=Trend_Normal c=2 sizing=2 struct=- exit=T2_HIT final=10:27:22
   actual=+97.50 after_exits=+97.50 (phys +97.50) after_all=+97.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7719.75 tgt0=7729.25 [TGT@7729.5x1(10:27:22)] pnl=+48.75 → after=+48.75
   g2 T1     q=1 e=7719.75 tgt0=7729.25 [TGT@7729.5x1(10:27:22)] pnl=+48.75 → after=+48.75

#828 2026-08-27 12:02 S4 LONG ZLR dt=Variation c=2 sizing=2 struct={'struct_c1': 7744.5, 'struct_c2': 7745.0, 'struct_c3': 7784.75} exit=T2_HIT final=12:37:00
   actual=+45.00 after_exits=+45.00 (phys +45.00) after_all=+45.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+2.50
   g1 T1     q=1 e=7739.75 tgt0=7744.25 [TGT@7744.25x1(12:36:59)] pnl=+22.50 → after=+22.50
        [sens §3-T1 tgt=7744.5: touched in old-fill bar 12:35 → fills → +23.75]
   g2 T1     q=1 e=7739.75 tgt0=7744.25 [TGT@7744.25x1(12:37:00)] pnl=+22.50 → after=+22.50
        [sens §3-T1 tgt=7744.5: touched in old-fill bar 12:35 → fills → +23.75]

#830 2026-08-27 14:00 S2 SHORT INITIATIVE_SHORT dt=Variation c=2 sizing=2 struct={'struct_c1': 7736.75, 'struct_c2': 7728.5, 'struct_c3': 7714.75} exit=phantom_reconcile final=14:27:00
   actual=+103.75 after_exits=+107.50 (phys +107.50) after_all=+107.50 | Δ§2=+0.00 Δ§3=+3.75 Δ§4=-27.50 Δ§6=+0.00 | T1→struct_c1 sens=+11.25
   g1 T1     q=1 e=7744.5 tgt0=7739.0 [TGT@7739.0x1(14:01:53)] pnl=+27.50 → after=+27.50
        [sens §3-T1 tgt=7736.75: touched in old-fill bar 14:00 → fills → +38.75]
   g2 T2     q=1 e=7744.5 tgt0=7734.75 [TGT@7729.25x1(14:27:00)] pnl=+76.25 → after=+80.00
        §3 tgt=7728.5: touched in old-fill bar 14:25 → fills → +80.00
        §4 tgt=7734.75 drag=7734.75→7729.25 @14:01:59: nearer→fills at new target → +48.75

#831 2026-08-27 14:05 S2 SHORT SCALE_IN dt=None c=1 sizing=None struct=- exit=phantom_reconcile final=14:27:56
   actual=+52.50 after_exits=+52.50 (phys +52.50) after_all=+52.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7736.75 tgt0=7726.25 [TGT@7726.25x1(14:27:56)] pnl=+52.50 → after=+52.50

#838 2026-08-28 10:05 S4 SHORT ZLR dt=Trend_Normal c=3 sizing=3 struct=- exit=phantom_reconcile final=10:11:32
   actual=+107.50 after_exits=+107.50 (phys +107.50) after_all=+107.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7744.0 tgt0=7738.0 [TGT@7738.25x1(10:06:14)] pnl=+28.75 → after=+28.75
   g2 T1     q=1 e=7744.0 tgt0=7738.0 [TGT@7738.25x1(10:06:14)] pnl=+28.75 → after=+28.75
   g3 T2z    q=1 e=7744.0 tgt0=7732.25 [TGT@7734.0x1(10:11:32)] pnl=+50.00 → after=+50.00
        §4 tgt=7734.0 drag=7732.5→7723.75 @10:06:23: nearer→fills at new target → +50.00

#840 2026-08-28 10:10 S4 SHORT SCALE_IN dt=None c=2 sizing=None struct=- exit=phantom_reconcile final=10:17:33
   actual=+56.25 after_exits=+56.25 (phys +56.25) after_all=+56.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7738.25 tgt0=7727.0 [TGT@7726.5x1(10:13:50)] pnl=+58.75 → after=+58.75
   g2 RUNNER q=1 e=7738.25 tgt0=None [STOP@7738.75x1(10:17:33)] pnl=-2.50 → after=-2.50

#841 2026-08-28 10:15 S4 SHORT SCALE_IN dt=None c=2 sizing=None struct=- exit=STOP_FILL final=10:17:33
   actual=-70.00 after_exits=-70.00 (phys -70.00) after_all=-70.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7731.75 tgt0=7719.5 [STOP@7738.75x1(10:17:33)] pnl=-35.00 → after=-35.00
   g2 RUNNER q=1 e=7731.75 tgt0=None [STOP@7738.75x1(10:17:33)] pnl=-35.00 → after=-35.00

#848 2026-08-28 11:20 S4 LONG ZLR dt=Variation c=2 sizing=2 struct={'struct_c1': 7777.5, 'struct_c2': 7779.75, 'struct_c3': 7821.25} exit=MAE_SCRATCH final=11:38:47
   actual=-72.50 after_exits=-72.50 (phys -72.50) after_all=-72.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+87.50
   g1 T1     q=1 e=7776.0 tgt0=7784.75 [FLAT@7768.75x1(11:38:47)] pnl=-36.25 → after=-36.25
        [sens §3-T1 tgt=7777.5: touched 11:20 before exit → fills → +7.50]
   g2 T1     q=1 e=7776.0 tgt0=7784.75 [FLAT@7768.75x1(11:38:47)] pnl=-36.25 → after=-36.25
        [sens §3-T1 tgt=7777.5: touched 11:20 before exit → fills → +7.50]

#851 2026-08-28 11:55 S2 SHORT INITIATIVE_SHORT dt=Variation c=3 sizing=3 struct={'struct_c1': 7743.5, 'struct_c2': 7738.0, 'struct_c3': 7736.0} exit=manual final=12:52:58
   actual=+201.25 after_exits=+190.00 (phys +190.00) after_all=+190.00 | Δ§2=+0.00 Δ§3=-11.25 Δ§4=+45.00 Δ§6=+0.00 | T1→struct_c1 sens=-26.25
   g1 T1     q=1 e=7750.0 tgt0=7738.0 [TGT@7738.25x1(11:57:08)] pnl=+58.75 → after=+58.75
        [sens §3-T1 tgt=7743.5: nearer→fills at new target → +32.50]
   g2 T2     q=1 e=7750.0 tgt0=7726.5 [STOP@7735.75x1(12:52:58)] pnl=+71.25 → after=+60.00
        §3 tgt=7738.0: touched 11:55 before exit → fills → +60.00
        §4 tgt=7726.75 drag=7726.75→7711.75 @11:57:15: touched 12:15 before exit → fills → +116.25
   g3 RUNNER q=1 e=7750.0 tgt0=None [STOP@7735.75x1(12:52:58)] pnl=+71.25 → after=+71.25

#853 2026-08-28 12:01 S2 SHORT SCALE_IN dt=None c=2 sizing=None struct=- exit=STOP_HIT final=12:52:58
   actual=+62.50 after_exits=+62.50 (phys +62.50) after_all=+62.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7736.25 tgt0=7715.25 [TGT@7724.25x1(12:24:05)] pnl=+60.00 → after=+60.00
   g2 RUNNER q=1 e=7736.25 tgt0=None [STOP@7735.75x1(12:52:58)] pnl=+2.50 → after=+2.50

#859 2026-08-28 13:00 S4 SHORT ZLR dt=Variation c=3 sizing=3 struct={'struct_c1': 7724.75, 'struct_c2': 7711.75, 'struct_c3': 7709.5} exit=T3_HIT final=13:10:10
   actual=+143.75 after_exits=+143.75 (phys +143.75) after_all=+143.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=-77.50
   g1 T1     q=1 e=7725.0 tgt0=7717.5 [TGT@7717.0x1(13:01:13)] pnl=+40.00 → after=+40.00
        [sens §3-T1 tgt=7724.75: nearer→fills at new target → +1.25]
   g2 T1     q=1 e=7725.0 tgt0=7717.5 [TGT@7717.0x1(13:01:13)] pnl=+40.00 → after=+40.00
        [sens §3-T1 tgt=7724.75: nearer→fills at new target → +1.25]
   g3 T2z    q=1 e=7725.0 tgt0=7709.25 [TGT@7712.25x1(13:10:10)] pnl=+63.75 → after=+63.75
        §3 tgt=7711.75: not touched; old target gone → literal: as actual / physical: ride to final stop → +63.75
        §4 tgt=7712.25 drag=7708.75→7699.25 @13:01:17: nearer→fills at new target → +63.75

#862 2026-08-28 14:40 S4 SHORT TT dt=Neutral_Extreme c=2 sizing=2 struct={'struct_c1': 7716.75, 'struct_c2': 7709.75, 'struct_c3': 7688.25} exit=phantom_reconcile final=15:50:06
   actual=+8.75 after_exits=+8.75 (phys +8.75) after_all=+8.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=-15.00
   g1 T1     q=1 e=7720.5 tgt0=7713.75 [TGT@7713.75x1(14:50:28)] pnl=+33.75 → after=+33.75
        [sens §3-T1 tgt=7716.75: nearer→fills at new target → +18.75]
   g2 T2     q=1 e=7720.5 tgt0=7707.5 [FLAT@7725.5x1(15:50:06)] pnl=-25.00 → after=-25.00
        §3 tgt=7709.75: not touched→as actual → -25.00
        §4 tgt=7709.0 drag=7707.5→7699.5 @14:50:31: not touched→as actual → -25.00

#873 2026-08-31 09:35 S4 SHORT GB100 dt=None c=2 sizing=2 struct=- exit=STOP_HIT final=09:35:35
   actual=-8.75 after_exits=-8.75 (phys -8.75) after_all=-8.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7686.75 tgt0=7686.75 [TGT@7686.75x1(09:35:10)] pnl=+0.00 → after=+0.00
   g2 T2     q=1 e=7686.75 tgt0=7675.25 [STOP@7688.5x1(09:35:35)] pnl=-8.75 → after=-8.75
        §4 tgt=7675.25 drag=7675.25→7670.5 @09:35:20: not touched→as actual → -8.75

#875 2026-08-31 09:40 S2 SHORT OPENING_DRIVE dt=None c=5 sizing=None struct=- exit=STOP_FILL final=09:40:21
   actual=-100.00 after_exits=-100.00 (phys -100.00) after_all=-100.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7689.5 tgt0=7686.5 [STOP@7693.5x1(09:40:21)] pnl=-20.00 → after=-20.00
   g2 T1     q=2 e=7689.5 tgt0=7682.75 [STOP@7693.5x2(09:40:21)] pnl=-40.00 → after=-40.00
   g3 T2     q=1 e=7689.5 tgt0=7677.5 [STOP@7693.5x1(09:40:21)] pnl=-20.00 → after=-20.00
   g4 RUNNER q=1 e=7689.5 tgt0=None [STOP@7693.5x1(09:40:21)] pnl=-20.00 → after=-20.00

#877 2026-08-31 10:00 S2 SHORT REACTIVE_SHORT dt=None c=5 sizing=5 struct=- exit=phantom_reconcile final=10:11:49
   actual=+116.25 after_exits=+116.25 (phys +116.25) after_all=+116.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7689.5 tgt0=7686.5 [TGT@7686.25x1(10:02:40)] pnl=+16.25 → after=+16.25
   g2 T1     q=2 e=7689.5 tgt0=7683.25 [TGT@7683.0x2(10:06:57)] pnl=+65.00 → after=+65.00
   g3 T2     q=1 e=7689.5 tgt0=7677.25 [STOP@7686.0x1(10:11:49)] pnl=+17.50 → after=+17.50
        §4 tgt=7677.0 drag=7677.0→7669.75 @10:07:00: not touched→as actual → +17.50
   g4 RUNNER q=1 e=7689.5 tgt0=None [STOP@7686.0x1(10:11:49)] pnl=+17.50 → after=+17.50

#881 2026-08-31 10:10 S2 SHORT SCALE_IN dt=None c=2 sizing=None struct=- exit=phantom_reconcile final=10:35:18
   actual=+40.00 after_exits=+40.00 (phys +40.00) after_all=+40.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7682.75 tgt0=7672.25 [TGT@7678.75x1(10:24:51)] pnl=+20.00 → after=+20.00
   g2 RUNNER q=1 e=7682.75 tgt0=None [STOP@7678.75x1(10:35:18)] pnl=+20.00 → after=+20.00

#885 2026-08-31 10:35 S2 SHORT SCALE_IN dt=None c=2 sizing=None struct=- exit=STOP_FILL final=10:36:22
   actual=-57.50 after_exits=-57.50 (phys -57.50) after_all=-57.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7676.75 tgt0=7667.5 [STOP@7682.5x1(10:36:21)] pnl=-28.75 → after=-28.75
   g2 RUNNER q=1 e=7676.75 tgt0=None [STOP@7682.5x1(10:36:22)] pnl=-28.75 → after=-28.75

#936 2026-08-31 14:15 S4 LONG ZLR dt=Normal c=2 sizing=2 struct={'struct_c1': 7704.25, 'struct_c2': 7710.0, 'struct_c3': 7725.0} exit=STOP_FILL final=14:33:55
   actual=-55.00 after_exits=-55.00 (phys -55.00) after_all=-55.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7695.0 tgt0=7699.75 [STOP@7689.5x1(14:33:55)] pnl=-27.50 → after=-27.50
        [sens §3-T1 tgt=7704.25: not touched→as actual → -27.50]
   g2 T1     q=1 e=7695.0 tgt0=7699.75 [STOP@7689.5x1(14:33:55)] pnl=-27.50 → after=-27.50
        [sens §3-T1 tgt=7704.25: not touched→as actual → -27.50]

#939 2026-08-31 15:05 S4 SHORT ZLR dt=Normal c=2 sizing=2 struct={'struct_c1': 7680.5, 'struct_c2': 7674.75, 'struct_c3': 7670.25} exit=SIERRA_FLAT final=15:10:16
   actual=-35.00 after_exits=-35.00 (phys -35.00) after_all=-35.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7685.75 tgt0=7679.5 [FLAT@7689.25x1(15:10:16)] pnl=-17.50 → after=-17.50
        [sens §3-T1 tgt=7680.5: not touched→as actual → -17.50]
   g2 T1     q=1 e=7685.75 tgt0=7679.5 [FLAT@7689.25x1(15:10:16)] pnl=-17.50 → after=-17.50
        [sens §3-T1 tgt=7680.5: not touched→as actual → -17.50]

#942 2026-09-01 10:20 S2 LONG INITIATIVE_LONG dt=Trend_Normal c=4 sizing=5 struct=- exit=STOP_FILL final=10:58:38
   actual=+45.00 after_exits=+106.25 (phys +106.25) after_all=+106.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+61.25 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7660.75 tgt0=7663.25 [TGT@7663.25x1(10:22:22)] pnl=+12.50 → after=+12.50
   g2 T1     q=1 e=7660.75 tgt0=7667.75 [TGT@7667.75x1(10:30:31)] pnl=+35.00 → after=+35.00
   g3 T2     q=1 e=7660.75 tgt0=7672.75 [STOP@7660.5x1(10:58:38)] pnl=-1.25 → after=+60.00
        §4 tgt=7672.75 drag=7672.75→7680.5 @10:30:35: touched 10:35 before exit → fills → +60.00
   g4 RUNNER q=1 e=7660.75 tgt0=None [STOP@7660.5x1(10:58:38)] pnl=-1.25 → after=-1.25

#948 2026-09-01 11:45 S4 LONG GB100 dt=Variation c=5 sizing=2 struct={'struct_c1': 7670.5, 'struct_c2': 7681.5, 'struct_c3': 7682.5} exit=STOP_FILL final=12:15:14
   actual=-128.75 after_exits=-128.75 (phys -128.75) after_all=-51.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+77.25 | T1→struct_c1 sens=+92.50
   g1 T0     q=1 e=7668.5 tgt0=7671.75 [TGT@7671.75x1(11:47:08)] pnl=+16.25 → after=+16.25
   g2 T1     q=2 e=7668.5 tgt0=7675.0 [STOP@7661.25x2(12:15:14)] pnl=-72.50 → after=-72.50
        [sens §3-T1 tgt=7670.5: touched 11:45 before exit → fills → +20.00]
   g3 T2     q=1 e=7668.5 tgt0=7681.25 [STOP@7661.25x1(12:15:14)] pnl=-36.25 → after=-36.25
        §3 tgt=7681.5: not touched→as actual → -36.25
   g4 RUNNER q=1 e=7668.5 tgt0=None [STOP@7661.25x1(12:15:14)] pnl=-36.25 → after=-36.25
        §2 tgt=7682.5 src=struct_c3: not touched→as actual → -36.25

#950 2026-09-01 12:35 S2 SHORT INITIATIVE_SHORT dt=Variation c=5 sizing=5 struct={'struct_c1': 7629.75, 'struct_c2': 7624.0, 'struct_c3': 7541.75} exit=STOP_FILL final=12:41:34
   actual=-156.25 after_exits=-156.25 (phys -156.25) after_all=-156.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7643.75 tgt0=7640.75 [STOP@7650.0x1(12:41:34)] pnl=-31.25 → after=-31.25
   g2 T1     q=2 e=7643.75 tgt0=7638.5 [STOP@7650.0x2(12:41:34)] pnl=-62.50 → after=-62.50
        [sens §3-T1 tgt=7629.75: not touched→as actual → -62.50]
   g3 T2     q=1 e=7643.75 tgt0=7638.0 [STOP@7650.0x1(12:41:34)] pnl=-31.25 → after=-31.25
        §3 tgt=7624.0: not touched→as actual → -31.25
   g4 RUNNER q=1 e=7643.75 tgt0=None [STOP@7650.0x1(12:41:34)] pnl=-31.25 → after=-31.25
        §2 tgt=7541.75 src=struct_c3: not touched→as actual → -31.25

#953 2026-09-02 10:15 S2 LONG INITIATIVE_LONG dt=Normal c=5 sizing=2 struct=- exit=STOP_HIT final=11:48:13
   actual=+162.50 after_exits=+170.00 (phys +170.00) after_all=+68.00 | Δ§2=+45.00 Δ§3=+0.00 Δ§4=-37.50 Δ§6=-102.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7669.75 tgt0=7671.75 [TGT@7671.75x1(10:17:28)] pnl=+10.00 → after=+10.00
   g2 T1     q=2 e=7669.75 tgt0=7672.5 [TGT@7672.5x2(10:18:32)] pnl=+27.50 → after=+27.50
   g3 T2     q=1 e=7669.75 tgt0=7679.25 [TGT@7686.75x1(10:40:27)] pnl=+85.00 → after=+47.50
        §4 tgt=7679.25 drag=7679.25→7685.75 @10:18:37: nearer→fills at new target → +47.50
   g4 RUNNER q=1 e=7669.75 tgt0=None [STOP@7677.75x1(11:48:13)] pnl=+40.00 → after=+85.00
        §2 tgt=7686.75 src=fallback c3(shifted=t2): touched 10:40 before exit → fills → +85.00

#963 2026-09-02 11:59 S4 LONG ZLR dt=Variation c=5 sizing=2 struct={'struct_c1': 7691.25, 'struct_c2': 7699.75, 'struct_c3': 7702.0} exit=MAE_SCRATCH final=12:16:07
   actual=-137.50 after_exits=-137.50 (phys -137.50) after_all=-55.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+82.50 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7686.0 tgt0=7688.75 [FLAT@7680.5x1(12:16:07)] pnl=-27.50 → after=-27.50
   g2 T1     q=2 e=7686.0 tgt0=7692.75 [FLAT@7680.5x2(12:16:07)] pnl=-55.00 → after=-55.00
        [sens §3-T1 tgt=7691.25: not touched→as actual → -55.00]
   g3 T1     q=1 e=7686.0 tgt0=7692.75 [FLAT@7680.5x1(12:16:07)] pnl=-27.50 → after=-27.50
        [sens §3-T1 tgt=7691.25: not touched→as actual → -27.50]
   g4 T2z    q=1 e=7686.0 tgt0=7699.5 [FLAT@7680.5x1(12:16:07)] pnl=-27.50 → after=-27.50
        §3 tgt=7699.75: not touched→as actual → -27.50

#968 2026-09-02 12:40 S4 SHORT ZLR dt=Variation c=5 sizing=2 struct={'struct_c1': 7671.75, 'struct_c2': 7662.25, 'struct_c3': 7648.25} exit=MAE_SCRATCH final=13:04:42
   actual=-70.00 after_exits=-70.00 (phys -70.00) after_all=-28.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+42.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7676.5 tgt0=7673.25 [TGT@7673.5x1(12:44:57)] pnl=+15.00 → after=+15.00
   g2 T1     q=2 e=7676.5 tgt0=7670.75 [FLAT@7680.75x2(13:04:42)] pnl=-42.50 → after=-42.50
        [sens §3-T1 tgt=7671.75: not touched→as actual → -42.50]
   g3 T1     q=1 e=7676.5 tgt0=7670.75 [FLAT@7680.75x1(13:04:42)] pnl=-21.25 → after=-21.25
        [sens §3-T1 tgt=7671.75: not touched→as actual → -21.25]
   g4 T2z    q=1 e=7676.5 tgt0=7665.5 [FLAT@7680.75x1(13:04:42)] pnl=-21.25 → after=-21.25
        §3 tgt=7662.25: not touched→as actual → -21.25

#971 2026-09-02 13:10 S4 LONG GHOST dt=Variation c=5 sizing=5 struct={'struct_c1': 7677.5, 'struct_c2': 7687.25, 'struct_c3': 7690.5} exit=STOP_FILL final=14:41:01
   actual=+76.25 after_exits=+143.75 (phys +143.75) after_all=+143.75 | Δ§2=+0.00 Δ§3=+67.50 Δ§4=+43.75 Δ§6=+0.00 | T1→struct_c1 sens=-20.00
   g1 T0     q=1 e=7673.5 tgt0=7676.25 [TGT@7676.25x1(13:13:45)] pnl=+13.75 → after=+13.75
   g2 T1     q=2 e=7673.5 tgt0=7679.5 [TGT@7679.5x1(13:57:53),TGT@7679.5x1(13:57:53)] pnl=+60.00 → after=+60.00
        [sens §3-T1 tgt=7677.5: nearer→fills at new target → +40.00]
   g3 T2     q=1 e=7673.5 tgt0=7682.5 [STOP@7673.75x1(14:41:01)] pnl=+1.25 → after=+68.75
        §3 tgt=7687.25: touched 14:15 before exit → fills → +68.75
        §4 tgt=7682.5 drag=7682.5→7690.0 @13:57:58: touched 14:15 before exit → fills → +45.00
   g4 RUNNER q=1 e=7673.5 tgt0=None [STOP@7673.75x1(14:41:01)] pnl=+1.25 → after=+1.25
        §2 tgt=7690.5 src=struct_c3: not touched→as actual → +1.25

#981 2026-09-03 10:20 S4 LONG ZLR dt=Normal c=3 sizing=5 struct=- exit=MAE_SCRATCH final=10:34:40
   actual=-127.50 after_exits=-127.50 (phys -127.50) after_all=-127.50 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T1     q=1 e=7714.0 tgt0=7725.25 [FLAT@7705.5x1(10:34:40)] pnl=-42.50 → after=-42.50
   g2 T1     q=1 e=7714.0 tgt0=7725.25 [FLAT@7705.5x1(10:34:40)] pnl=-42.50 → after=-42.50
   g3 T2z    q=1 e=7714.0 tgt0=7736.25 [FLAT@7705.5x1(10:34:40)] pnl=-42.50 → after=-42.50

#987 2026-09-03 13:20 S4 SHORT ZLR dt=Variation c=5 sizing=5 struct={'struct_c1': 7735.0, 'struct_c2': 7721.0, 'struct_c3': 7715.25} exit=STOP_FILL final=13:33:33
   actual=-156.25 after_exits=-156.25 (phys -156.25) after_all=-156.25 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7748.5 tgt0=7746.0 [STOP@7754.75x1(13:33:33)] pnl=-31.25 → after=-31.25
   g2 T1     q=2 e=7748.5 tgt0=7744.0 [STOP@7754.75x2(13:33:33)] pnl=-62.50 → after=-62.50
        [sens §3-T1 tgt=7735.0: not touched→as actual → -62.50]
   g3 T1     q=1 e=7748.5 tgt0=7744.0 [STOP@7754.75x1(13:33:33)] pnl=-31.25 → after=-31.25
        [sens §3-T1 tgt=7735.0: not touched→as actual → -31.25]
   g4 T2z    q=1 e=7748.5 tgt0=7739.25 [STOP@7754.75x1(13:33:33)] pnl=-31.25 → after=-31.25
        §3 tgt=7721.0: not touched→as actual → -31.25

#998 2026-09-04 09:55 S4 LONG ZLR dt=None c=5 sizing=2 struct=- exit=STOP_FILL final=10:02:53
   actual=-125.00 after_exits=-125.00 (phys -125.00) after_all=-50.00 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+75.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7745.25 tgt0=7748.75 [STOP@7740.25x1(10:02:53)] pnl=-25.00 → after=-25.00
   g2 T1     q=2 e=7745.25 tgt0=7751.25 [STOP@7740.25x2(10:02:53)] pnl=-50.00 → after=-50.00
   g3 T1     q=1 e=7745.25 tgt0=7751.25 [STOP@7740.25x1(10:02:53)] pnl=-25.00 → after=-25.00
   g4 T2z    q=1 e=7745.25 tgt0=7755.0 [STOP@7740.25x1(10:02:53)] pnl=-25.00 → after=-25.00

#1008 2026-09-04 11:05 S2 SHORT INITIATIVE_SHORT dt=Variation c=5 sizing=5 struct={'struct_c1': 7713.5, 'struct_c2': 7656.0, 'struct_c3': 7625.5} exit=STOP_FILL final=12:07:59
   actual=+13.75 after_exits=+13.75 (phys +13.75) after_all=+13.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=-20.00
   g1 T0     q=1 e=7716.25 tgt0=7714.0 [TGT@7714.0x1(11:21:42)] pnl=+11.25 → after=+11.25
   g2 T1     q=2 e=7716.25 tgt0=7711.5 [TGT@7711.5x2(11:30:56)] pnl=+47.50 → after=+47.50
        [sens §3-T1 tgt=7713.5: nearer→fills at new target → +27.50]
   g3 T2     q=1 e=7716.25 tgt0=7706.0 [STOP@7724.75x1(12:07:59)] pnl=-42.50 → after=-42.50
        §3 tgt=7656.0: not touched→as actual → -42.50
        §4 tgt=7707.25 drag=7706.0→7699.25 @11:31:01: not touched→as actual → -42.50
   g4 RUNNER q=1 e=7716.25 tgt0=None [STOP@7716.75x1(11:35:42)] pnl=-2.50 → after=-2.50
        §2 tgt=7625.5 src=struct_c3: not touched→as actual → -2.50

#1069 2026-09-04 12:25 S2 LONG INITIATIVE_LONG dt=Variation c=5 sizing=5 struct={'struct_c1': 7734.5, 'struct_c2': 7744.5, 'struct_c3': 7758.5} exit=STOP_FILL final=12:59:38
   actual=+68.75 after_exits=+68.75 (phys +68.75) after_all=+68.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=-5.00
   g1 T0     q=1 e=7730.25 tgt0=7733.5 [TGT@7733.5x1(12:47:54)] pnl=+16.25 → after=+16.25
   g2 T1     q=2 e=7730.25 tgt0=7735.0 [TGT@7735.0x1(12:52:32),TGT@7735.0x1(12:52:33)] pnl=+47.50 → after=+47.50
        [sens §3-T1 tgt=7734.5: nearer→fills at new target → +42.50]
   g3 T2     q=1 e=7730.25 tgt0=7739.25 [STOP@7730.75x1(12:59:38)] pnl=+2.50 → after=+2.50
        §3 tgt=7744.5: not touched→as actual → +2.50
        §4 tgt=7739.25 drag=7739.25→7744.75 @12:52:39: not touched→as actual → +2.50
   g4 RUNNER q=1 e=7730.25 tgt0=None [STOP@7730.75x1(12:59:38)] pnl=+2.50 → after=+2.50
        §2 tgt=7758.5 src=struct_c3: not touched→as actual → +2.50

#1073 2026-09-04 13:10 S4 SHORT GB100 dt=Variation c=5 sizing=2 struct={'struct_c1': 7724.0, 'struct_c2': 7718.75, 'struct_c3': 7715.0} exit=STOP_FILL final=14:57:58
   actual=+70.00 after_exits=+153.75 (phys +153.75) after_all=+61.50 | Δ§2=+51.25 Δ§3=+32.50 Δ§4=+51.25 Δ§6=-92.25 | T1→struct_c1 sens=-37.50
   g1 T0     q=1 e=7725.5 tgt0=7722.5 [TGT@7722.5x1(13:24:58)] pnl=+15.00 → after=+15.00
   g2 T1     q=2 e=7725.5 tgt0=7720.25 [TGT@7720.25x1(13:29:33),TGT@7720.25x1(13:29:33)] pnl=+52.50 → after=+52.50
        [sens §3-T1 tgt=7724.0: nearer→fills at new target → +15.00]
   g3 T2     q=1 e=7725.5 tgt0=7715.0 [STOP@7725.25x1(14:57:58)] pnl=+1.25 → after=+33.75
        §3 tgt=7718.75: touched 13:30 before exit → fills → +33.75
        §4 tgt=7715.0 drag=7715.0→7708.5 @13:29:41: touched 13:40 before exit → fills → +52.50
   g4 RUNNER q=1 e=7725.5 tgt0=None [STOP@7725.25x1(14:57:58)] pnl=+1.25 → after=+52.50
        §2 tgt=7715.0 src=struct_c3: touched 13:40 before exit → fills → +52.50

#1141 2026-09-04 15:00 S2 LONG INITIATIVE_LONG dt=Variation c=5 sizing=5 struct={'struct_c1': 7731.5, 'struct_c2': 7738.25, 'struct_c3': 7752.25} exit=STOP_FILL final=15:04:03
   actual=-143.75 after_exits=-143.75 (phys -143.75) after_all=-143.75 | Δ§2=+0.00 Δ§3=+0.00 Δ§4=+0.00 Δ§6=+0.00 | T1→struct_c1 sens=+0.00
   g1 T0     q=1 e=7725.0 tgt0=7727.25 [STOP@7719.25x1(15:04:03)] pnl=-28.75 → after=-28.75
   g2 T1     q=2 e=7725.0 tgt0=7728.75 [STOP@7719.25x2(15:04:03)] pnl=-57.50 → after=-57.50
        [sens §3-T1 tgt=7731.5: not touched→as actual → -57.50]
   g3 T2     q=1 e=7725.0 tgt0=7733.0 [STOP@7719.25x1(15:04:03)] pnl=-28.75 → after=-28.75
        §3 tgt=7738.25: not touched→as actual → -28.75
   g4 RUNNER q=1 e=7725.0 tgt0=None [STOP@7719.25x1(15:04:03)] pnl=-28.75 → after=-28.75
        §2 tgt=7752.25 src=struct_c3: not touched→as actual → -28.75

=== MIRROR BUG (MODIFY_TARGET drags STOP looser) — diagnostic, NOT counted ===
#820 g1 T1 stop 7695.5→7688.25 @15:15:05 pre-drag stop hit 15:50 → actual -6.25 vs -37.50 Δ=-31.25
#862 g2 T2 stop 7720.25→7729.75 @14:50:34 pre-drag stop hit 15:05 → actual -25.00 vs +1.25 Δ=+26.25
#1008 g3 T2 stop 7716.75→7724.75 @11:31:04 pre-drag stop hit 11:30 → actual -42.50 vs -2.50 Δ=+40.00
Σ mirror = +35.00

=== DRAG EVENTS (§4 scan) ===
2026-08-26 #812 g2 T2 14:47:08 tgt 7702.0→7709.5 stop 7681.5→7689.0 Δ=7.5 MODIFY_STOP→target-drag
2026-08-26 #812 g2 T2 15:50:01 tgt 7709.5→7718.5 stop 7689.0→7698.0 Δ=9.0 MODIFY_STOP→target-drag
2026-08-26 #818 g1 T1 14:50:06 tgt 7705.5→7703.75 stop 7689.0→7687.25 Δ=-1.75 TARGET_REALISM→stop-drag
2026-08-26 #820 g1 T1 15:15:05 tgt 7714.75→7707.5 stop 7695.5→7688.25 Δ=-7.25 TARGET_REALISM→stop-drag
2026-08-27 #830 g2 T2 14:01:59 tgt 7734.75→7729.25 stop 7748.75→7743.25 Δ=-5.5 MODIFY_STOP→target-drag
2026-08-28 #838 g3 T2z 10:06:23 tgt 7732.5→7723.75 stop 7755.25→7746.5 Δ=-8.75 MODIFY_STOP→target-drag
2026-08-28 #838 g3 T2z 10:10:09 tgt 7723.75→7734.0 stop 7746.5→7756.75 Δ=10.25 TARGET_REALISM→stop-drag
2026-08-28 #851 g2 T2 11:57:15 tgt 7726.75→7711.75 stop 7764.75→7749.75 Δ=-15.0 MODIFY_STOP→target-drag
2026-08-28 #851 g2 T2 12:13:19 tgt 7711.75→7707.5 stop 7749.75→7745.5 Δ=-4.25 MODIFY_STOP→target-drag
2026-08-28 #851 g2 T2 12:33:54 tgt 7707.5→7698.0 stop 7745.5→7736.0 Δ=-9.5 MODIFY_STOP→target-drag
2026-08-28 #853 g1 T1 12:05:07 tgt 7715.0→7724.0 stop 7749.75→7758.75 Δ=9.0 TARGET_REALISM→stop-drag
2026-08-28 #859 g3 T2z 13:01:17 tgt 7708.75→7699.25 stop 7735.25→7725.75 Δ=-9.5 MODIFY_STOP→target-drag
2026-08-28 #859 g3 T2z 13:05:07 tgt 7699.25→7712.25 stop 7725.75→7738.75 Δ=13.0 TARGET_REALISM→stop-drag
2026-08-28 #862 g2 T2 14:50:31 tgt 7707.5→7699.5 stop 7728.25→7720.25 Δ=-8.0 MODIFY_STOP→target-drag
2026-08-28 #862 g2 T2 14:50:34 tgt 7699.5→7709.0 stop 7720.25→7729.75 Δ=9.5 TARGET_REALISM→stop-drag
2026-08-31 #873 g2 T2 09:35:20 tgt 7675.25→7670.5 stop 7693.25→7688.5 Δ=-4.75 MODIFY_STOP→target-drag
2026-08-31 #877 g3 T2 10:07:00 tgt 7677.0→7669.75 stop 7696.5→7689.25 Δ=-7.25 MODIFY_STOP→target-drag
2026-08-31 #877 g3 T2 10:10:08 tgt 7669.75→7666.25 stop 7689.25→7685.75 Δ=-3.5 MODIFY_STOP→target-drag
2026-08-31 #881 g1 T1 10:15:05 tgt 7672.25→7678.75 stop 7689.5→7696.0 Δ=6.5 TARGET_REALISM→stop-drag
2026-09-01 #942 g3 T2 10:30:35 tgt 7672.75→7680.5 stop 7652.75→7660.5 Δ=7.75 MODIFY_STOP→target-drag
2026-09-02 #953 g3 T2 10:18:37 tgt 7679.25→7685.75 stop 7662.5→7669.0 Δ=6.5 MODIFY_STOP→target-drag
2026-09-02 #953 g3 T2 10:30:07 tgt 7685.75→7686.75 stop 7669.0→7670.0 Δ=1.0 MODIFY_STOP→target-drag
2026-09-02 #971 g3 T2 13:57:58 tgt 7682.5→7690.0 stop 7666.0→7673.5 Δ=7.5 MODIFY_STOP→target-drag
2026-09-04 #1008 g3 T2 11:31:01 tgt 7706.0→7699.25 stop 7723.5→7716.75 Δ=-6.75 MODIFY_STOP→target-drag
2026-09-04 #1008 g3 T2 11:31:04 tgt 7699.25→7707.25 stop 7716.75→7724.75 Δ=8.0 TARGET_REALISM→stop-drag
2026-09-04 #1069 g3 T2 12:52:39 tgt 7739.25→7744.75 stop 7725.25→7730.75 Δ=5.5 MODIFY_STOP→target-drag
2026-09-04 #1073 g3 T2 13:29:41 tgt 7715.0→7708.5 stop 7731.75→7725.25 Δ=-6.5 MODIFY_STOP→target-drag

=== PER-DAY ===
day          n      acct    actual  after_exits      phys  after_all        Δ      Δ§2      Δ§3      Δ§4      Δ§6   T1sens
2026-08-24   0   -695.00         —
2026-08-25   0    426.25         —
2026-08-26   4   -346.25    118.75        77.50     77.50      77.50   -41.25     0.00   -41.25     0.00     0.00   -23.75
2026-08-27   5    301.25    203.75       207.50    207.50     207.50     3.75     0.00     3.75   -27.50     0.00    13.75
2026-08-28   8    412.50    437.50       426.25    426.25     426.25   -11.25     0.00   -11.25    45.00     0.00   -31.25
2026-08-31   7   -100.00   -100.00      -100.00   -100.00    -100.00     0.00     0.00     0.00     0.00     0.00     0.00
2026-09-01   3   -226.25   -240.00      -178.75   -178.75    -101.50   138.50     0.00     0.00    61.25    77.25    92.50
2026-09-02   4    602.50     31.25       106.25    106.25     128.75    97.50    45.00    67.50     6.25    22.50   -20.00
2026-09-03   2   -106.25   -283.75      -283.75   -283.75    -283.75     0.00     0.00     0.00     0.00     0.00     0.00
2026-09-04   5   -116.25   -116.25       -32.50    -32.50     -49.75    66.50    51.25    32.50    51.25   -17.25   -62.50
Σ                 152.50     51.25       222.50    222.50     305.00   253.75    96.25    51.25   136.25    82.50   -31.25

=== PER-DAY, SEQUENTIAL ATTRIBUTION (§4 → §3 → §2 → §6; columns sum exactly to Δ) ===
day          n    actual  after_all        Δ       §4       §3       §2       §6
2026-08-24   0         —          —     0.00
2026-08-25   0         —          —     0.00
2026-08-26   4    118.75      77.50   -41.25     0.00   -41.25     0.00     0.00
2026-08-27   5    203.75     207.50     3.75   -27.50    31.25     0.00     0.00
2026-08-28   8    437.50     426.25   -11.25    45.00   -56.25     0.00     0.00
2026-08-31   7   -100.00    -100.00     0.00     0.00     0.00     0.00     0.00
2026-09-01   3   -240.00    -101.50   138.50    61.25     0.00     0.00    77.25
2026-09-02   4     31.25     128.75    97.50     6.25    23.75    45.00    22.50
2026-09-03   2   -283.75    -283.75     0.00     0.00     0.00     0.00     0.00
2026-09-04   5   -116.25     -49.75    66.50    51.25   -18.75    51.25   -17.25
Σ                  51.25     305.00   253.75   136.25   -61.25    96.25    82.50

=== UNATTRIBUTED (non-system) fills per day ===
2026-08-24 [('07:48:19', 10563, 7679.75, 6.0, 'Limit', None), ('07:49:16', 10564, 7676.25, 6.0, 'Stop Limit', -105.0), ('07:50:06', 10565, 7678.25, 6.0, 'Limit', None), ('08:11:30', 10566, 7675.5, 6.0, 'Stop Limit', -82.5), ('08:13:56', 10568, 7678.0, 1.0, 'Limit', None), ('08:13:56', 10568, 7678.0, 1.0, 'Limit', None), ('08:13:56', 10568, 7678.0, 1.0, 'Limit', None), ('08:13:56', 10568, 7678.0, 2.0, 'Limit', None), ('08:32:52', 10569, 7674.75, 5.0, 'Stop Limit', -81.25), ('08:35:55', 10572, 7676.5, 5.0, 'Limit', None), ('09:30:12', 10573, 7676.75, 1.0, 'Stop Limit', 1.25), ('09:30:12', 10573, 7676.5, 4.0, 'Stop Limit', None), ('09:31:49', 10574, 7675.25, 5.0, 'Limit', None), ('09:42:43', 10575, 7664.0, 5.0, 'Stop Limit', -281.25), ('09:54:17', 10576, 7666.25, 4.0, 'Limit', None), ('11:20:27', 10577, 7659.0, 4.0, 'Stop Limit', -145.0), ('11:23:36', 10578, 7663.0, 4.0, 'Limit', None), ('12:19:45', 10580, 7685.25, 1.0, 'Limit', None), ('13:25:20', 10579, 7667.75, 4.0, 'Stop Limit', 95.0), ('13:26:14', 10585, 7670.0, 3.0, 'Limit', None), ('13:29:48', 10587, 7668.0, 4.0, 'Stop Limit', -116.25), ('14:01:32', 10588, 7669.25, 4.0, 'Limit', None), ('15:41:57', 10589, 7670.0, 4.0, 'Stop Limit', 15.0), ('15:48:54', 10590, 7671.25, 4.0, 'Limit', None), ('16:46:31', 10598, 7671.5, 1.0, 'Limit', 1.25), ('16:46:32', 10598, 7671.5, 3.0, 'Limit', 3.75)]
2026-08-25 [('01:27:28', 10600, 7679.25, 4.0, 'Limit', None), ('03:04:26', 10602, 7691.75, 1.0, 'Limit', 62.5), ('03:12:03', 10605, 7687.5, 3.0, 'Limit', 123.75), ('04:02:44', 10606, 7682.5, 4.0, 'Limit', None), ('04:21:56', 10607, 7686.25, 4.0, 'Stop Limit', -75.0), ('04:31:23', 10608, 7691.5, 4.0, 'Limit', None), ('05:33:03', 10609, 7701.25, 4.0, 'Stop Limit', -195.0), ('05:44:17', 10611, 7705.75, 3.0, 'Limit', None), ('05:52:10', 10612, 7710.0, 3.0, 'Stop Limit', -63.75), ('06:01:39', 10613, 7707.25, 3.0, 'Limit', None), ('08:18:26', 10614, 7707.5, 3.0, 'Stop Limit', -3.75), ('08:20:52', 10616, 7704.75, 3.0, 'Limit', None), ('10:30:17', 10618, 7679.25, 2.0, 'Limit', 255.0), ('10:42:38', 10619, 7677.25, 2.0, 'Limit', None), ('10:53:52', 10621, 7680.75, 1.0, 'Limit', 120.0), ('10:53:55', 10622, 7680.5, 1.0, 'Limit', -16.25), ('10:54:21', 10624, 7680.75, 4.0, 'Limit', -17.5), ('10:54:27', 10623, 7680.5, 1.0, 'Limit', None), ('11:47:33', 10625, 7681.0, 4.0, 'Stop Limit', 6.25), ('11:51:21', 10626, 7682.0, 4.0, 'Limit', 115.0), ('15:02:55', 10628, 7687.75, 4.0, 'Market', 115.0)]
2026-08-26 [('10:04:25', 10639, 7700.75, 2.0, 'Limit', None), ('10:14:43', 10642, 7694.25, 2.0, 'Limit', None), ('12:39:44', 10645, 7674.25, 4.0, 'Stop Limit', -465.0)]
2026-08-27 [('11:29:55', 10675, 7734.25, 3.0, 'Limit', None), ('11:44:45', 10677, 7728.25, 1.0, 'Limit', 30.0), ('11:45:12', 10678, 7727.0, 1.0, 'Limit', None), ('11:51:54', 10676, 7735.25, 3.0, 'Stop Limit', -51.25), ('12:16:40', 10686, 7739.25, 1.0, 'Limit', None), ('12:21:19', 10687, 7735.5, 1.0, 'Stop Limit', -21.25), ('12:23:15', 10689, 7737.0, 1.0, 'Limit', None), ('12:51:03', 10691, 7749.0, 1.0, 'Limit', 60.0), ('14:02:27', 10698, 7738.25, 2.0, 'Limit', None), ('14:25:30', 10699, 7730.5, 1.0, 'Limit', 70.0), ('14:25:30', 10699, 7730.5, 1.0, 'Limit', 38.75)]
2026-09-01 [('06:13:09', 10838, 7656.0, 5.0, 'Limit', None), ('06:52:08', 10839, 7654.5, 5.0, 'Stop Limit', -37.5), ('07:31:49', 10840, 7659.0, 7.0, 'Limit', None), ('07:56:44', 10841, 7654.0, 7.0, 'Stop Limit', -175.0), ('09:35:23', 10843, 7649.75, 6.0, 'Limit', None), ('10:55:41', 10855, 7662.5, 6.0, 'Limit', 272.5)]
2026-09-02 [('04:54:39', 10878, 7624.0, 2.0, 'Limit', None), ('04:54:41', 10878, 7624.0, 4.0, 'Limit', None), ('06:25:55', 10879, 7627.0, 6.0, 'Stop Limit', -90.0), ('06:26:57', 10880, 7628.25, 6.0, 'Limit', None), ('07:59:43', 10882, 7645.0, 2.0, 'Limit', 167.5), ('07:59:43', 10882, 7645.0, 1.0, 'Limit', 83.75), ('08:20:54', 10884, 7656.0, 2.0, 'Limit', 277.5), ('08:22:15', 10885, 7654.75, 1.0, 'Limit', 132.5)]
2026-09-03 [('03:04:31', 10937, 7678.25, 5.0, 'Limit', None), ('03:25:56', 10938, 7675.75, 5.0, 'Stop Limit', -62.5), ('03:51:07', 10939, 7676.5, 8.0, 'Limit', None), ('06:51:21', 10941, 7670.5, 8.0, 'Market', 240.0)]

```

### נספח 2 · שערי-כניסה §5/§7 — 149 מועמדים, עוגנים, סריקת-ברים (`replay_entry_gates.py`)

```text
raw blocked rows (ELQ+release) = 810; after dedup (day,pattern,dir,bar5,gate) = 149

=== PER DAY ===
day        gate                     blocked would_pass judgeable   t1  stop     t1%
2026-08-24 entry_location_quality         0          0         0    0     0       —
2026-08-24 awaiting_release              13          0         0    0     0       —
2026-08-25 entry_location_quality         0          0         0    0     0       —
2026-08-25 awaiting_release               6          0         0    0     0       —
2026-08-26 entry_location_quality         0          0         0    0     0       —
2026-08-26 awaiting_release               5          0         0    0     0       —
2026-08-27 entry_location_quality         0          0         0    0     0       —
2026-08-27 awaiting_release               7          0         0    0     0       —
2026-08-28 entry_location_quality         0          0         0    0     0       —
2026-08-28 awaiting_release              10          0         0    0     0       —
2026-08-31 entry_location_quality         0          0         0    0     0       —
2026-08-31 awaiting_release              20          0         0    0     0       —
2026-09-01 entry_location_quality         0          0         0    0     0       —
2026-09-01 awaiting_release              17          0         0    0     0       —
2026-09-02 entry_location_quality         0          0         0    0     0       —
2026-09-02 awaiting_release              11          0         0    0     0       —
2026-09-03 entry_location_quality        31          3         3    2     1(67% n<10)
2026-09-03 awaiting_release              15          0         0    0     0       —
2026-09-04 entry_location_quality         2          0         0    0     0       —
2026-09-04 awaiting_release              12          0         0    0     0       —
Σ entry_location_quality      33          3         3    2     1NOT_JUDGEABLE   (unresolved=0 not_judgeable=0)
   still-blocked reasons: [('also beyond_value', 10), ('no matching accepted_break', 4), ('pos 0.96 > 0.66 even from IB edge', 3), ('pos 0.83 > 0.66 even from IB edge', 2), ('pos 0.93 > 0.66 even from IB edge', 2), ('pos 0.82 > 0.66 even from IB edge', 1)]
   context — ALL entry_location_quality blocked (dedup) t1_before_stop: 7/14 = 50%  (unresolved=19, not_judgeable=0)
Σ awaiting_release           116          0         0    0     0NOT_JUDGEABLE   (unresolved=0 not_judgeable=0)
   still-blocked reasons: [('break DOWN against direction', 35), ('break UP against direction', 32), ('no accepted_break → §7 does not decide', 24), ('delta_ok=False vol_ok=False', 19), ('delta unavailable', 3), ('delta_ok=False vol_ok=True', 2)]
   context — ALL awaiting_release blocked (dedup) t1_before_stop: 54/88 = 61%  (unresolved=28, not_judgeable=0)

=== WOULD-PASS DETAIL ===
2026-09-03 10:00:08 entry_locati TREND_STEP             LONG  @7722.0 ab=UP/PDH → leg from broken PDH IB edge 7726.5: L=0.00 < floor 1.0 → position test skipped | t1_first=STOP
2026-09-03 11:00:01 entry_locati GB100                  LONG  @7718.25 ab=UP/PDH → leg from broken PDH IB edge 7726.5: L=0.00 < floor 1.0 → position test skipped | t1_first=T1
2026-09-03 11:02:34 entry_locati S2_DELTA_DBL_LONG      LONG  @7722.5 ab=UP/PDH → leg from broken PDH IB edge 7726.5: L=0.00 < floor 1.0 → position test skipped | t1_first=T1

=== §7 ANCHORS (bar-level facts) ===
2026-09-03 11:00 ET (18:00 IL): O=7718.25 H=7730.5 L=7718.0 C=7730.25 vol=22284 delta=4130.0 | window max_delta=4130 min_delta=-3502 max_vol=28007 0.7×=19605 | IB=7700.5/7726.5 accepted_break(before bar)=('UP', 'PDH') (incl. bar)=('UP', 'PDH')
   awaiting_release candidates in 11:00-11:05: n=0 → 
2026-09-04 10:40 ET (17:40 IL): O=7733.25 H=7733.25 L=7724.0 C=7725.0 vol=17087 delta=-3763.0 | window max_delta=2552 min_delta=-3763 max_vol=26678 0.7×=18675 | IB=7729.5/7751.0 accepted_break(before bar)=(None, None) (incl. bar)=(None, None)
   awaiting_release candidates in 10:40-10:45: n=0 → 

=== §7 BAR-LEVEL SCAN (condition true at bar close, accepted_break from closed bars before it) ===
2026-08-24 09:40 ET  SHORT (break DOWN/PDL) delta=-3783 vol=20723  candidates in bar: —
2026-08-25 09:45 ET  LONG (break UP/PDH) delta=-479 vol=15093  candidates in bar: —
2026-08-25 15:50 ET  LONG (break UP/PDH) delta=897 vol=16237  candidates in bar: {'eod_entry_cutoff': 1}
2026-08-26 15:00 ET  LONG (break UP/prior_VA) delta=1892 vol=13174  candidates in bar: —
2026-08-27 14:30 ET  LONG (break UP/PDH) delta=1381 vol=10499  candidates in bar: —
2026-08-27 15:55 ET  LONG (break UP/PDH) delta=2135 vol=37971  candidates in bar: —
2026-08-28 15:55 ET  SHORT (break DOWN/IB) delta=-1214 vol=33256  candidates in bar: {'eod_entry_cutoff': 2}
2026-08-31 14:35 ET  SHORT (break DOWN/PDL) delta=-1585 vol=12937  candidates in bar: —
2026-09-01 13:25 ET  SHORT (break DOWN/PDL) delta=-2118 vol=16812  candidates in bar: {'daytype_playbook': 2}
2026-09-02 10:15 ET  LONG (break UP/prior_VA) delta=2123 vol=19757  candidates in bar: —
2026-09-02 13:40 ET  LONG (break UP/prior_VA) delta=1807 vol=8605  candidates in bar: —
2026-09-02 14:15 ET  LONG (break UP/PDH) delta=3663 vol=16859  candidates in bar: —
2026-09-03 11:00 ET  LONG (break UP/PDH) delta=4130 vol=22284  candidates in bar: {'entry_location_quality': 47}
2026-09-03 14:00 ET  LONG (break UP/PDH) delta=2093 vol=11409  candidates in bar: {'entry_location_quality': 1}
2026-09-04 15:00 ET  SHORT (break DOWN/IB) delta=-2541 vol=10723  candidates in bar: —
Σ §7 fire-bars = 15 (n bars, 10 days)
```

### נספח 3 · הוכחת §2-אינרטי (`probe_s2_dead.py` — `write_trade_command` נעטף; `command_queue/` לפני/אחרי = 1 קובץ)

```text
[SierraCmd] §2 RUNNER_BY_DAYTYPE_V1: trade probe day_type=Variation → c4=7715.0 (struct_c3)
[SierraCmd] F5 RUNNER_TRAIL_V2: trade probe runner leg c4 placed STOP-ONLY (no fixed target) — exit is the structural swing trail
[SierraCmd] §2 RUNNER_BY_DAYTYPE_V1: trade probe day_type=Variation → c4=7715.0 (struct_c3)
RUNNER_TRAIL_V2=1 → contracts=5 target_price(c1)=7722.5 c2=7720.25 c3=7715.0 c4=None runner_stop_only=c4
RUNNER_TRAIL_V2=0 → contracts=5 target_price(c1)=7722.5 c2=7720.25 c3=7715.0 c4=7715.0 runner_stop_only=None
```

### נספח 4 · הוכחת §4-אינרטי (DB + grep)

```text
$ psql mems26 -c "SELECT count(*) FROM v9_trades WHERE quality ? 'c1_target_price' OR quality ? 'c3_target_price';"
0
$ grep -rn "_target_price" backend/v9 --include=*.py | grep -v tests/
backend/v9/services/trade_manager/manager.py:364:        # expected value in quality.c{n}_target_price. If |Δ| ≥ 1 tick, restore.
backend/v9/services/trade_manager/manager.py:386:                _expected = q.get(f"{_leg}_target_price")

$ sed -n 985,1045p backend/v9/services/sierra_command.py | grep -n "RUNNER_BY_DAYTYPE_V1\|RUNNER_TRAIL_V2\|_c4_target = \|_c4_target ="
1:    if (os.getenv("RUNNER_BY_DAYTYPE_V1", "0").strip().lower() in ("1", "true", "yes")
10:                pass  # runner stays (c4=None is set by RUNNER_TRAIL_V2 below)
14:                    _c4_target = _c3_target
16:                    "[SierraCmd] §2 RUNNER_BY_DAYTYPE_V1: trade %s day_type=%s → "
17:                    "no runner, c4=%s (t3/m×risk)", trade_id, _rbd_dt, _c4_target)
26:                _c4_target = _rbd_struct_c3 if _rbd_struct_c3 else _c3_target
28:                    "[SierraCmd] §2 RUNNER_BY_DAYTYPE_V1: trade %s day_type=%s → "
29:                    "c4=%s (%s)", trade_id, _rbd_dt, _c4_target,
32:    # ── F5 · RUNNER_TRAIL_V2 (Michael 2026-08-20, ORACLE_STUDY §5 R-A) ──
43:    # This is not a new mechanism — C4_RULING6_V1 already leaves _c4_target None on
47:    if (os.getenv("RUNNER_TRAIL_V2", "0").strip().lower() in ("1", "true", "yes")
50:            _min_c = int(os.getenv("RUNNER_TRAIL_V2_MIN_CONTRACTS", "3"))
55:                _runner_leg, _c4_target = "c4", None
```

### נספח 5 · `scripts/sierra_activity_join.py --date` × 8 ימים (עמודת `recon` = אריתמטיקת-הרגליים; `broker_pnl` = רשומות-FIFO של החשבון המשותף)

```text
=== 2026-08-26 ===
# T-256 books vs broker — 2026-08-26 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-08-26_UTC.37138283.data
# 16 executions · 9 Closed-Trade-P/L records · broker day total -346.25
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   809 LONG      7701.50     7698.75   +2.75     -75.00     -47.50     -47.50  OK   -27.50
   812 LONG      7688.75     7689.00   -0.25     +32.50     +31.25     +31.25  OK    +1.25
   818 LONG      7695.50     7695.25   +0.25     +41.25     +73.75     +42.50  !!   -32.50
   820 LONG      7703.25           -       -      +0.00          -          -  !!        -
------------------------------------------------------------------------------------------
 TOTAL                                            -1.25     +57.50                  -58.75
COVERAGE: mapped +57.50 of broker day -346.25 → residual -403.75 (INCOMPLETE — per-trade deltas above are indicative only)
          trades with no broker exit mapped: [820]
entry_price != fill price on 3/4 trades → [(809, 2.75), (812, -0.25), (818, 0.25)]
DRY-RUN — would set pnl_sierra on 2 rows: [(809, -47.5), (812, 31.25)]
=== 2026-08-27 ===
# T-256 books vs broker — 2026-08-27 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-08-27_UTC.37138283.data
# 29 executions · 16 Closed-Trade-P/L records · broker day total +301.25
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   822 LONG      7723.50     7723.00   +0.50    -100.00     -95.00     -95.00  OK    -5.00
   824 LONG      7719.00     7719.75   -0.75    +105.00     +97.50     +97.50  OK    +7.50
   828 LONG      7739.75     7739.75   +0.00     +45.00     +47.50     +45.00  !!    -2.50
   830 SHORT     7743.50     7744.50   -1.00     +22.50     +72.50    +103.75  !!   -50.00
   831 SHORT     7736.50     7736.75   -0.25     +51.25     +52.50     +52.50  OK    -1.25
------------------------------------------------------------------------------------------
 TOTAL                                          +123.75    +175.00                  -51.25
COVERAGE: mapped +175.00 of broker day +301.25 → residual +126.25 (INCOMPLETE — per-trade deltas above are indicative only)
entry_price != fill price on 4/5 trades → [(822, 0.5), (824, -0.75), (830, -1.0), (831, -0.25)]
DRY-RUN — would set pnl_sierra on 3 rows: [(822, -95.0), (824, 97.5), (831, 52.5)]
=== 2026-08-28 ===
# T-256 books vs broker — 2026-08-28 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-08-28_UTC.37138283.data
# 37 executions · 20 Closed-Trade-P/L records · broker day total +412.50
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   838 SHORT     7746.50     7744.00   +2.50     +82.50    +107.50    +107.50  OK   -25.00
   840 SHORT     7738.75     7738.25   +0.50     +61.25     +56.25     +56.25  OK    +5.00
   841 SHORT     7731.00     7731.75   -0.75     -77.50     -70.00     -70.00  OK    -7.50
   848 LONG      7776.25     7776.00   +0.25      +0.00          -          -  !!        -
   851 SHORT     7750.00     7750.00   +0.00     +58.75    +132.50    +201.25  !!   -73.75
   853 SHORT     7736.00     7736.25   -0.25     +60.00    +131.25     +62.50  !!   -71.25
   859 SHORT     7725.75     7725.00   +0.75    +155.00    +143.75    +143.75  OK   +11.25
   862 SHORT     7720.50     7720.50   +0.00      +8.75     +33.75     +33.75  OK   -25.00
------------------------------------------------------------------------------------------
 TOTAL                                          +348.75    +535.00                 -186.25
COVERAGE: mapped +535.00 of broker day +412.50 → residual -122.50 (INCOMPLETE — per-trade deltas above are indicative only)
          trades with no broker exit mapped: [848]
entry_price != fill price on 6/8 trades → [(838, 2.5), (840, 0.5), (841, -0.75), (848, 0.25), (853, -0.25), (859, 0.75)]
DRY-RUN — would set pnl_sierra on 5 rows: [(838, 107.5), (840, 56.25), (841, -70.0), (859, 143.75), (862, 33.75)]
=== 2026-08-31 ===
# T-256 books vs broker — 2026-08-31 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-08-31_UTC.37138283.data
# 35 executions · 17 Closed-Trade-P/L records · broker day total -100.00
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   873 SHORT     7688.75     7686.75   +2.00     +11.25      -8.75      -8.75  OK   +20.00
   875 SHORT     7689.50     7689.50   +0.00    -100.00    -100.00    -100.00  OK    +0.00
   877 SHORT     7689.50     7689.50   +0.00          -    +116.25    +116.25  OK        -
   881 SHORT     7682.50     7682.75   -0.25          -     +40.00     +40.00  OK        -
   885 SHORT     7676.50     7676.75   -0.25     -60.00     -57.50     -57.50  OK    -2.50
   936 LONG      7695.00     7695.00   +0.00     -55.00     -55.00     -55.00  OK    +0.00
   939 SHORT     7685.25     7685.75   -0.50          -          -          -  !!        -
------------------------------------------------------------------------------------------
 TOTAL                                          -203.75     -65.00                 -138.75
COVERAGE: mapped -65.00 of broker day -100.00 → residual -35.00 (INCOMPLETE — per-trade deltas above are indicative only)
          trades with no broker exit mapped: [939]
entry_price != fill price on 4/7 trades → [(873, 2.0), (881, -0.25), (885, -0.25), (939, -0.5)]
DRY-RUN — would set pnl_sierra on 4 rows: [(873, -8.75), (877, 116.25), (881, 40.0), (885, -57.5)]
=== 2026-09-01 ===
# T-256 books vs broker — 2026-09-01 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-01_UTC.37138283.data
# 30 executions · 21 Closed-Trade-P/L records · broker day total -226.25
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   942 LONG      7660.25     7660.75   -0.50     +55.00    +155.00     +45.00  !!  -100.00
   948 LONG      7668.75     7668.50   +0.25    -135.00    -128.75    -128.75  OK    -6.25
   950 SHORT     7643.75     7643.75   +0.00    -156.25    -312.50    -156.25  !!  +156.25
------------------------------------------------------------------------------------------
 TOTAL                                          -236.25    -286.25                  +50.00
COVERAGE: mapped -286.25 of broker day -226.25 → residual +60.00 (INCOMPLETE — per-trade deltas above are indicative only)
entry_price != fill price on 2/3 trades → [(942, -0.5), (948, 0.25)]
DRY-RUN — would set pnl_sierra on 1 rows: [(948, -128.75)]
=== 2026-09-02 ===
# T-256 books vs broker — 2026-09-02 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-02_UTC.37138283.data
# 36 executions · 23 Closed-Trade-P/L records · broker day total +602.50
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   953 LONG      7668.75     7669.75   -1.00    +277.50    +162.50    +162.50  OK  +115.00
   963 LONG      7685.75     7686.00   -0.25          -          -          -  !!        -
   968 SHORT     7676.25     7676.50   -0.25          -     +15.00     +15.00  OK        -
   971 LONG      7673.25     7673.50   -0.25    +145.00     +76.25     +76.25  OK   +68.75
------------------------------------------------------------------------------------------
 TOTAL                                          +422.50    +253.75                 +168.75
COVERAGE: mapped +253.75 of broker day +602.50 → residual +348.75 (INCOMPLETE — per-trade deltas above are indicative only)
          trades with no broker exit mapped: [963]
entry_price != fill price on 4/4 trades → [(953, -1.0), (963, -0.25), (968, -0.25), (971, -0.25)]
DRY-RUN — would set pnl_sierra on 3 rows: [(953, 162.5), (968, 15.0), (971, 76.25)]
=== 2026-09-03 ===
# T-256 books vs broker — 2026-09-03 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-03_UTC.37138283.data
# 16 executions · 9 Closed-Trade-P/L records · broker day total -106.25
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   981 LONG      7714.00     7714.00   +0.00          -          -          -  !!        -
   987 SHORT     7749.00     7748.50   +0.50    -143.75    -156.25    -156.25  OK   +12.50
------------------------------------------------------------------------------------------
 TOTAL                                          -143.75    -156.25                  +12.50
COVERAGE: mapped -156.25 of broker day -106.25 → residual +50.00 (INCOMPLETE — per-trade deltas above are indicative only)
          trades with no broker exit mapped: [981]
entry_price != fill price on 1/2 trades → [(987, 0.5)]
DRY-RUN — would set pnl_sierra on 1 rows: [(987, -156.25)]
=== 2026-09-04 ===
# T-256 books vs broker — 2026-09-04 acct 37138283
# source: /Users/michael/SierraChart/TradeActivityLogs/TradeActivityLog_2026-09-04_UTC.37138283.data
# 42 executions · 22 Closed-Trade-P/L records · broker day total -116.25
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
------------------------------------------------------------------------------------------
   998 LONG      7745.75     7745.25   +0.50    -137.50    -125.00    -125.00  OK   -12.50
  1008 SHORT     7717.00     7716.25   +0.75     +32.50     +13.75     +13.75  OK   +18.75
  1069 LONG      7730.50     7730.25   +0.25     +62.50     +68.75     +68.75  OK    -6.25
  1073 SHORT     7725.50     7725.50   +0.00     +70.00     +70.00     +70.00  OK    +0.00
  1141 LONG      7724.25     7725.00   -0.75    -125.00    -143.75    -143.75  OK   +18.75
------------------------------------------------------------------------------------------
 TOTAL                                           -97.50    -116.25                  +18.75
COVERAGE: mapped -116.25 of broker day -116.25 → residual +0.00 (complete — every dollar the broker moved is attributed)
entry_price != fill price on 4/5 trades → [(998, 0.5), (1008, 0.75), (1069, 0.25), (1141, -0.75)]
DRY-RUN — would set pnl_sierra on 5 rows: [(998, -125.0), (1008, 13.75), (1069, 68.75), (1073, 70.0), (1141, -143.75)]
```

### נספח 6 · עובדות-ברים מאחורי כל הכרעת-"נגע" (`v9_bars_5min_woodies`, ET, H/L)

```text
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:20 7667.25 7660.25
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:25 7667.25 7663.25
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:30 7672.25 7664.5
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:35 7673 7667.75
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:40 7670.5 7665.75
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:45 7670.75 7666.25
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:50 7666.5 7662
#942 LONG tgt 7672.75 (exit STOP 10:58) 10:55 7664 7660.25
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 13:55 7679.5 7673.75
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:00 7680 7673.75
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:05 7680.75 7677.25
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:10 7679.25 7677
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:15 7687.5 7677.75
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:20 7683.75 7680.25
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:25 7681.75 7678.5
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:30 7681.75 7679
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:35 7680.25 7674.25
#971 LONG tgt 7687.25/7682.5 (exit STOP 14:41) 14:40 7675.25 7672.75
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:10 7726.75 7724.75
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:15 7726.75 7724
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:20 7725.75 7722.5
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:25 7724.25 7719.75
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:30 7720.5 7716.5
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:35 7719.5 7717
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:40 7718.75 7714.5
#1073 SHORT tgt 7718.75/7715 (exit STOP 14:57) 13:45 7717 7712.75
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:15 7676.25 7667
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:20 7680 7673.75
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:25 7682.5 7676.75
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:30 7682.5 7675.75
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:35 7685.5 7681.25
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:40 7690 7684.25
#953 LONG runner tgt 7686.75 (exit STOP 11:48) 10:45 7690 7682.75
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 11:55 7750.5 7737.25
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 12:00 7741.5 7733.5
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 12:05 7745.25 7736.5
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 12:10 7745 7738.25
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 12:15 7741.5 7726.25
#851 SHORT tgt 7738/7726.75 (exit STOP 12:52) 12:20 7732.5 7720.25
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 14:40 7690.75 7688.5
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 14:45 7696.5 7690.5
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 14:50 7698 7694
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 14:55 7698.5 7695.5
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 15:00 7705.5 7696.75
#812 LONG tgt 7693.75/7701.5 (exit FLAT 15:50) 15:05 7705 7700.75
#830 SHORT tgt 7728.5 (old fill 14:27) 14:20 7735.75 7731.5
#830 SHORT tgt 7728.5 (old fill 14:27) 14:25 7732.5 7723.5
#859 SHORT tgt 7711.75 (old fill 13:10 @7712.25) 13:05 7719 7713.5
#859 SHORT tgt 7711.75 (old fill 13:10 @7712.25) 13:10 7722.75 7711.75
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:25 7731 7727.75
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:30 7731.25 7727.25
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:35 7731.5 7728.75
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:40 7731.75 7728.75
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:45 7734.25 7730.75
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:50 7735.25 7732.5
#1069 LONG tgt 7744.5/7739.25 (exit STOP 12:59) 12:55 7733.5 7730.5
#862 SHORT tgt 7709.75 / mirror stop 7720.25 (FLAT 15:50) 14:50 7716.75 7712.25
#862 SHORT tgt 7709.75 / mirror stop 7720.25 (FLAT 15:50) 14:55 7717.25 7712.75
#862 SHORT tgt 7709.75 / mirror stop 7720.25 (FLAT 15:50) 15:00 7718.75 7713.75
#862 SHORT tgt 7709.75 / mirror stop 7720.25 (FLAT 15:50) 15:05 7723 7716.25
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 11:45 7673 7668
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 11:50 7673.75 7669.75
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 11:55 7672.75 7668.25
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 12:00 7670.75 7667.5
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 12:05 7670 7665
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 12:10 7668 7661.75
#948 LONG tgt 7681.5/7682.5 (exit STOP 12:15) 12:15 7663 7656.25
#1008 SHORT tgt 7707.25 / mirror stop 7716.75 (exit STOP 12:07) 11:30 7716.75 7710.25
#1008 SHORT tgt 7707.25 / mirror stop 7716.75 (exit STOP 12:07) 11:35 7717.5 7714
#1008 SHORT tgt 7707.25 / mirror stop 7716.75 (exit STOP 12:07) 11:40 7722.5 7716.75
```

### נספח 7 · היסטוריית-מחירי-הפקודות של #1008 קבוצה-3 (יומן-ברוקר, TLV 110=Price1, 111=Price2) — ההוכחה לגרירה ולבאג-המראה

```text
TARGET 10983 (Limit)
  11:05:07.934 ET  PLACE       price1=7706.0
  11:31:01.859 ET  REPLACED    price1=7699.25
  11:31:04.673 ET  REPLACED    price1=7707.25
STOP 10984 (Stop-Limit p1/p2)
  11:05:07.934 ET  PLACE       price1=7723.5
  11:05:08.448 ET  Teton CME Routing (Ord price1=7723.5 price2=7728.5
  11:31:01.859 ET  REPLACED    price1=7716.75 price2=7721.75
  11:31:04.817 ET  REPLACED    price1=7724.75 price2=7729.75
  12:07:59.445 ET  Teton CME Routing (Ord price1=7729.75 price2=7724.75
  12:07:59.445 ET  FILLED      price1=7729.75

קריאה: 11:31:01 SMART_BE → סטופ 7723.50→7716.75 (−6.75) ⇒ ה-DLL גרר את היעד 7706.00→7699.25 (−6.75, גרירה) · 11:31:04 TARGET_REALISM MODIFY_TARGET → יעד 7699.25→7707.25 (+8.00) ⇒ ה-DLL גרר את הסטופ 7716.75→7724.75 (+8.00, באג-המראה) · 12:07:59 הסטופ הנגרר 7724.75 מולא ⇒ −8.5 נק' (−$42.50) במקום BE (−$2.50)
```

_סוף הדוח — cowork-dev סוכן-משנה, 07.09.2026. אפס שינוי בקוד/דגלים/DB; קובץ זה הוא הקובץ היחיד שנכתב._
