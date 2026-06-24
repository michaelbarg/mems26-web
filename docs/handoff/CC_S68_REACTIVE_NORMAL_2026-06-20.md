# CC Handoff — #68: ניהול מסחר לפי סוג-יום (S2/S4) · שלב-1: REACTIVE ביום-Normal · 2026-06-20

> ⚠️ **הוחלף** ע"י `CC_S68_DAYTYPE_LOCATION_PLAN_2026-06-21.md` (תוכנית מלאה: כל 7 הסוגים + מיקום+כיוון מסוג-יום ולא CCI). שמור לרפרנס-audit בלבד.

**מחבר:** Cowork (תכנון + audit, ללא קוד). **סמכות-ניהול:** `docs/spec_authority/S1_TRADE_MANAGEMENT_3CONTRACTS.md` (Michael, 2026-06-20).
**מצב:** ספציפיקציה לאישור-Michael. **לא בוצע commit. לא שונה קוד.**

---

## 0. מטרה (במילים של Michael)
מערכת-1 מזהה נכון את סוג-היום. עכשיו **S2/S4 צריכים לציית לכיוון שהיא קובעת**: להיכנס בצד הנכון של ה-IB לפי סוג-היום, ולנהל את העסקה לפי טבלת 3-החוזים.

**דוגמה (יום Normal):** המחיר עולה ל-IBH → מחפשים **שורט** (lower-high/דחייה + CVD divergence), **לא לונג**. ניהול: **C1=IB-center · C2=VAL · C3=IBL (trail)** · BE אחרי C1 · trail אחרי C2 · אל תרדוף אם IBH נשבר.

---

## 1. ממצאי-AUDIT (נקרא בקוד החי — לא מהזיכרון)

### מה כבר בנוי ומחווט (KEEP — לא לבנות מחדש)
| משטח | קובץ | מה הוא עושה |
|---|---|---|
| verdict פר תבנית×יום | `daytype_playbook.decide()` ← `trading_gateway.py:150` (`DAYTYPE_PLAYBOOK=1`) | FULL/REDUCED/SKIP + `require_with_trend`. REACTIVE/Normal = **FULL**. |
| **שער-מיקום REACTIVE** | `reactive_location_gate.decide()` ← `trading_gateway.py:185` (`REACTIVE_LOCATION_GATE`) | חוסם REACTIVE_LONG אם `entry>POC`, SHORT אם `entry<POC`. **זה כבר כלל-ה"שורט-בקצה-עליון" של Michael** (POC≈VAH/VAL). |
| יעדים פר-יום | `targets_table._TARGETS` + `day_type_targets.compute_targets_for_day_type` ← woodies:724 / five_min:1413 | C1/C2/C3 פר-סוג-יום — אבל **R-based**. |
| ניהול runner | `manager` (`resolve_trail_config` + `RUNNER_TRAIL_V1`) | BE אחרי T1 + trail. |
| רמות-מבנה בגייטוויי | `cross_context.tpo_system` → `poc/vah/val/ib_high/ib_low` | הרמות המבניות **כבר זמינות** בנקודת-ההחלטה. |

### מה מת / חסר (הפער האמיתי)
- **`daytype_style` ב-`daytype_playbook.yaml`** (`fade_edges`, `t1_anchor`, `t2_anchor`, ההערה "SHORT only ≥ POC / LONG only ≤ POC") — **0 קוראים בקוד**. config מת.
- **היעדים-המבניים לא מחושבים למחיר.** ב-`targets_table`, Normal `t2="POC"` עם `t2_r=None`; `compute_targets_for_day_type` פותר **רק R-multiples** → מחזיר `t2_price=None` לכל יעד מבני. כלומר POC/VAL/IB-center/extreme הם **תוויות-stub**, לא מחיר.

### 🔴 שני קונפליקטים שדורשים את החלטתך
1. **Normal: 1 חוזה מול 3.** הקוד הקיים (`targets_table.Normal`): **1 חוזה** (HALF, T1=1R, T2=POC, אין T3, time-stop 30דק'). **הטבלה שלך:** **3 חוזים** (C1=IB-center, C2=VAL, C3=IBL trail). הטבלה שלך = הסמכות החדשה ⇒ לאמץ. **זה משנה את Normal מסקאלפ-חוזה-אחד ל-3-חוזים — מאשר?**
2. **R-based מול מבני.** הקוד R-based; הטבלה שלך מבנית. השלב הזה בונה resolver-מבני (להלן §2).

---

## 2. שלב-1 build-ready — REACTIVE ביום-Normal

### מה כבר מכוסה (לא לבנות):
- **צד/כיוון** ("שורט בקצה-עליון בלבד") — `reactive_location_gate` כבר עושה זאת. נדרש רק: (א) שהדגל ON, (ב) שה-`day_type=Normal` מגיע נכון (§3).
- **verdict** (REACTIVE/Normal=FULL) — `daytype_playbook` כבר.

### מה לבנות — resolver-יעדים מבני (הפער):
מודול חדש (sibling לשערים), `DAYTYPE_TARGETS_STRUCTURAL` (default-OFF), שכאשר `daytype_style[day_type].target == location`/`fade_edges`, מחשב C1/C2/C3 מ-`cross_context.tpo_system` במקום מ-R:

| כניסה | C1 | C2 | C3 (runner) |
|---|---|---|---|
| SHORT מ-IBH (Normal) | IB-center = (ibh+ibl)/2 | VAL | IBL (trail) |
| LONG מ-IBL (Normal) | IB-center | VAH | IBH (trail) |

ניהול: BE אחרי C1 · trail-5min אחרי C2 (משתמש ב-`RUNNER_TRAIL_V1` הקיים) · `time_stop` כמו היום · **3 חוזים** (אחרי אישור קונפליקט-1).

**חיווט:** להרחיב את `compute_targets_for_day_type` (או wrapper) כך שתקבל `tpo_ctx` ותחזיר מחירים מבניים כש-`daytype_style` מבקש location; אחרת ליפול ל-R-based הקיים (fail-safe). זה **מחיה את `daytype_style` המת** במקום להוסיף config מקביל.

---

## 3. #68a — תשתית-ערך (prerequisite לקוהרנטיות מלאה)
היום `current_day_type` (S2) + `v9_day_type_state` (S4) עדיין מהמנוע-**הישן** (`state_machine`/DECISION_MATRIX, ≤5 סוגים, ללא Neutral). נקודה-אחת: `main.py:_day_type_on_bar` — לעקוף את **ערך-ה-day_type בלבד** (באירוע שמתפרסם + בערך שנשמר ל-DB) למסווג-החדש, ממופה `Normal_Variation→Variation`, **fail-safe** (שגיאה/אין-ברים/FORMING → נשאר הישן).

- **דגל נפרד `S1_NEW_CLASSIFIER_S2S4` (default-OFF)** — *לא* להרחיב את `S1_NEW_CLASSIFIER` הדלוק (זה ידליק שינוי-מסחר בלי אישור-נפרד).
- **DRY:** helper משותף `_resolve_new_day_type(today)` עם מטמון-30ש' (היום משוכפל ב-`trade_context.py:511-523`) — גם השער וגם ה-per-bar יקראו אותו.
- **מלכודת-חיווט (קריטי):** allow-lists של chart-patterns (`five_min:56-57`) משתמשים ב-`"Variation"`, לא `"Normal_Variation"` → **חובה למפות לפני ההצבה**, אחרת chart-patterns יושתקו בשקט בימי-Variation.
- **הערה ל-REACTIVE:** ה-side+verdict כבר על המסווג-החדש בגייטוויי (דרך `extract_g1_entry_context`), אז #68a קריטי בעיקר ל-chart-patterns / Nontrend-skip / S4-sizing ולקוהרנטיות-מלאה — לא חוסם את שלב-1 של REACTIVE.

---

## 4. אימות — SHADOW חי (offline backtest לא-ישים · ראה §4א)
- **טסטים אנטי-טאוטולוגיים (RED-on-revert):** REACTIVE-SHORT@Normal → C1/C2/C3 = IB-center/VAL/IBL (מחירים מבניים, לא R); LONG@IBL מראה-מראה. היפוך-cfg/היפוך-כיוון משנה תוצאה (לא טאוטולוגי).
- **אימות-חי ב-SHADOW (המאמת העיקרי):** הדלק flag ב-SHADOW בלבד. לכל REACTIVE ביום-Normal לוג: (א) `entry` מול IB-center/POC/קצוות (האם בקצה?), (ב) would-block ע"י המיקום/כיוון, (ג) C1/C2/C3 המבניים שהיו נקבעים + תוצאתם מול הניהול בפועל. לצבור **≥N ימי-Normal** (להגדיר עם Michael) לפני כל מעבר DEMO/LIVE.
- **4 צירי-UAT** לכל endpoint שנוגעים בו (Quality/Recency/Cardinality/Latency).

## 4א. למה לא offline backtest (ממצא-נתונים, Cowork 2026-06-20)
המדגם של REACTIVE-על-Normal = **8 עסקאות ביום-אחד** (06-18); בימי-Neutral (06-08/09/11) ירו **0 REACTIVE** → הרחבה לא עוזרת. בנוסף, ה-8 נכנסו **באמצע ה-IB** (סביב POC ~7560, IB 7535.5–7581.8) — כלומר הפרו את כלל-המיקום עצמו (net −$295; סינון-POC היה משאיר 1 מ-8) ⇒ ניהול-עליהם לא בר-בדיקה. גם רמות-TPO ל-06-18 מגיעות ב-2 שורות (VAL 7489 מול 7564). **מסקנה (Rule 2): אין מדגם offline בר-בדיקה → המאמת הוא SHADOW חי.**

## 5. NOT-DONE (מה השלב הזה לא עושה)
- לא נוגע ב-INITIATIVE/HFE/ZLR/TLB/HNS (התבניות הבאות, אחת-אחת).
- לא מחליף `decision_matrix.py` / `state_machine.py` (נשארים עד שכל #68 חי ויציב).
- לא משנה `opening_type` (נשאר ישן — מחוץ ל-scope).
- `daytype_style`: **לחווט** (§2) ולא להשאיר dead config; אם לא מחווט בשלב זה — לתעד מפורשות.

## 6. בטיחות + סדר
- כל דגל **default-OFF**, **flag-gated**, fail-open/fail-safe. SHADOW לפני DEMO/LIVE.
- **שינוי-trading-surface** → אישור-Michael **פר-דגל ופר-תבנית** לפני הדלקה.
- **ללא commit/push עד הוראת-Michael.** Standing-OFF flags (chop/COT) ללא שינוי.
- **סדר מומלץ:** (1) אישור 2 הקונפליקטים §1 → (2) resolver-מבני ל-REACTIVE/Normal §2, **flag default-OFF** → (3) הדלקה ב-SHADOW + אימות-חי §4 (אין offline) → (4) #68a value-wiring §3 → (5) תבנית הבאה.
