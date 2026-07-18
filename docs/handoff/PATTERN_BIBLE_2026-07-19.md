# ספר-התבניות — PATTERN BIBLE · 2026-07-19

**מבצע:** cursor-agent (ניתוח-קוד בלבד) · **מקור-משימה:** `CURSOR_PATTERN_BIBLE_2026-07-19.md`
**פסיקת-מייקל:** לעבור תבנית-תבנית — גאומטריה, מחסומים, מימוש; למה ווּדיס תקוע; למה S2 מאוחר.
**חוק:** כל עובדה עם `file:line`. לא מוכרע → **"לא-מוכרע מהקוד"** + מה חסר.
**הצלב מול** `frontend/.../planHelp.ts` — לא הסתמכות יחידה (VEGAS כבר הוחלף בעבר).
**ראיות ריצה:** `sim_matrix.py` → `PASS: 112 cells, mismatches=0` (2026-07-19).  
`audit_pattern_miss.py --date 2026-07-17` — **נכשל כאן** (Postgres trust/dialog); מספרי B2 מבוססי-קוד + `PATTERN_MISS_AUDIT_2026-07-17.md`.

**חוזים בפועל:** פלייבוק `max_contracts:3` → REDUCED=`ceil(3/2)=2` (`daytype_playbook.py:142-143`),  
אבל עם `FIXED_CONTRACTS_4=1` החי — רוב הנתיבים כופים **4** (`sierra_command.py:235-278`, `sizing.py:109-111`).  
ה-gateway בודק רק `_pb.allow` — **REDUCED לא מקטין גודל שם** (`trading_gateway.py:633`).  
בטבלאות למטה: פסק הפלייבוק + הערה על חוזים.

---

## חלק ב' — חקירות מייקל (קודם — זה מה שביקש)

### B1 · למה ווּדיס תקוע

**היפותזה (07-17):** צבע-טרנד מפגר אחרי CCI ~6 ברים — CCI ‎-36→+182 ב-16:45–17:05, צבע GRAY עד 17:15.

#### מי קובע `trend_state` — מי מנצח בפועל?

| מנגנון | נוסחה | האם מזין דטקטורים חיים? | Cite |
|---|---|---|---|
| **DLL Sierra Study ID:1** (Woodies CCI Trend) | SG4≠0→BLUE, SG2≠0→RED, SG3≠0→GRAY, else GRAY | **כן — מנצח בנתיב החי** | `sc_study/v9_woodies_export.h` (~560-574, 669-678) |
| **A1 `BARS_PERSISTENCE_REQUIRED=6`** | consecutive≥6 + קיצון ±100 | **לא** — לא wired לדטקטורים; `EntryPhaseEngine` מסומן לא-פעיל | `a1_strategic_gate.py:30,114-142`; `entry_phase.py:7-9` |
| **`TREND_CCI_DIRECT_V1`** | \|cci\|≥`PT`(50) → BLUE/RED else keep | **חלקי בלבד** — ראה למטה | `bars.py:364-388,1022-1023` |

**ממצא מכריע — פיצול-מוח:**

1. בלולאת `history` / כתיבת-DB: `bar["trend_state"] = _trend_from_cci(...)` (`bars.py:1022-1023`) — **override עובד**.
2. אחר-כך, אם יש `payload.current_bar`, נבנה `last_flat` מ-**raw** `_cb.get("trend_state")` **בלי** `_trend_from_cci` (`bars.py:1073-1096`).
3. `woodies_system` מזין דטקטורים מהבר המנותב — כלומר **צבע Sierra הגולמי**, לא ה-CCI-direct.

⇒ `TREND_CCI_DIRECT_V1=1` משפר **DB/UI/היסטוריה**, אבל **TT/GB100 על הבר החי עדיין יכולים לראות GRAY** בזמן ש-|CCI|≥50.

#### כמה ברים עד שהצבע מתהפך?

| מקור | חישוב מהנוסחה |
|---|---|
| Sierra paint (קונבנציית Woodies / מראה A1) | **6 ברים** בצד אחד של האפס → ~**30 דק'** על 5-min. התאמה לראיית 07-17 (~16:45→17:15). |
| `TREND_CCI_DIRECT` (כשמוחל) | **0 ברים** ברגע \|cci\|≥50 |
| DLL SWI-fallback (אין מערכי Sierra) | מינ׳ 1 בר אחרי קרוס + תנאי SWI; יכול להישאר GRAY | `v9_woodies_export.h` / `cci_calc.py:127-133` |

**לא-מוכרע מהקוד:** ערך Input המדויק של Study ID:1 בסיירה של מייקל (האם באמת 6) — לא נקרא מה-Inputs בריפו. דורש אישור מצילום Inputs / מדידה חיה.

#### אילו תבניות נעולות על הצבע (לא על CCI)?

| תבנית | נעול-צבע? | Cite |
|---|---|---|
| **GB100** | **כן** — `trend == BLUE/RED` קשיח | `gb100.py:91,147` |
| **TT** | **כן** — אותו | `tt.py:81,141` |
| **ZLR** | בסיס=CCI בלבד; עם `ZLR_SPEC_V2` דורש ≥6 ברים paint | `zlr.py:75-82,211-217` |
| TLB / HTLB / VEGAS / GHOST / FAMIR / HFE | **לא** קוראים `trend_state` בדטקטור | greps ריקים בקבצי-הדפוס |

**גלובלי אחרי זיהוי:** YELLOW → מנקה **כל** התבניות (`woodies_system.py:619-624`). בנתיב Sierra Study ID:1 כמעט אין YELLOW (רק BLUE/RED/GRAY) — נעילת-YELLOW עלולה להיות כמעט-inert בלייב.

#### האם `TREND_CCI_DIRECT` פתר את הפיגור?

**לא במלואו.** נשארו נתיבים שקוראים צבע ישן:

- `bars.py:1073-1096` — `current_bar` raw
- `woodies_system` studies מהבר המנותב
- GB100/TT קוראים `bars[-1].trend_state`

**תיקון אפשרי (לא בוצע — משטח-סיכון):** לקרוא `_trend_from_cci` גם על `current_bar` לפני `_route_bar`. דורש פסיקת-מייקל.

---

### B2 · למה S2 תמיד יורה מאוחר

**היפותזה:** B1→B4 = 4 ברים + 3 רקע = 7 ברים = 35 דק'; B4 מאשר רק אחרי שהתנועה יצאה.

#### מינימום ברים → דקות (מהקוד)

| תבנית | מינ׳ ברים לדטקציה | דקות (×5) | מתי בתוך התנועה | Cite |
|---|---|---|---|---|
| **REACTIVE** | 4 (B1–B4); buffer≥7 | **20** לסיום-רצף; **35** למילוי-buffer | **מאוחר בדהייה** — ירי על B4 מעבר לקיצון B3 | `five_min_system.py:34,617-725` |
| **INITIATIVE** | 4; buffer≥7 | **20 / 35** | **אמצע–סוף דחף** — מבחן שני (B4) אחרי הרחבה | `:817-909` |
| **HNS** | ≥12 | **≥60** | **מאוחר** — שבירת צוואר אחרי כתף ימין | `head_shoulders.py:26,141-206` |
| **DBDT** | ≥10 | **≥50** | **מאוחר** — שבירת צוואר אחרי תחתית/פסגה 2 | `double_bt.py:30,167-228` |
| **FLAGS** | ≥10 (מוט≥5+דגל≥3+1) | **≥50** | **אמצע המשך** — פריצת דגל אחרי מוט | `flags.py:32-40,141-200` |
| **CONFLUENCE** | יורש הורים + 4 ברי woodies ל-G-fresh | תלוי הורים | אותו בר כמו RI+ZLR | `confluence_ri_zlr.py:84-166` |

#### FHB — מתי S2 משתחרר

| ספירת-ברים RTH | מצב | מותר | Cite |
|---|---|---|---|
| 1–3 | ACCUMULATING | **כלום** | `first_hour_buffer.py:27-28` |
| 4–6 | EARLY | REACTIVE בלבד | `:28` |
| 7–9 | DEVELOPING | REACTIVE + INITIATIVE | `:29` |
| 13+ / אחרי 10:30 | COMPLETE / DAY_TYPE | + chart patterns | `:31`; `five_min_system.py:1169-1195` |

**עלות 07-17:** חלון 16:45–17:05 (ראלי) — REACTIVE נעול עד בר 4 (=20 דק' מ-16:30) במקרה הטוב; INITIATIVE עד בר 7 (=35 דק'). Chart patterns בכלל לא ב-FIRST_HOUR.  
**לא-מוכרע מספרי כאן:** כמה swings בפועל נחסמו ב-FHB ב-07-17 — דורש `audit_pattern_miss` על Postgres חי.

#### `b2_volume_drop` — ממוצע מורעל?

**מאומת מהקוד — כן כש-`S2_VSA_VOLUME=1`:**

```658:659:backend/v9/systems/five_min/five_min_system.py
        _vol_buf = [b.get("v", 0) or 0 for b in bars_5m[:-3] if (b.get("v", 0) or 0) > 0]
        _rolling_avg = sum(_vol_buf[-20:]) / max(len(_vol_buf[-20:]), 1) if _vol_buf else b1_vol
```

- Overnight נכנס ל-`_bar_buffer` (`:1097-1102`) ואז חוזר — הנפחים נשארים.
- avg20 = עד 20 נפחים חיוביים **כולל Globex דק** → `b2 ≤ 0.7×avg` כמעט בלתי-אפשרי בבוקר RTH עמוס.
- בלי VSA: `b2 <= 0.10 * b1` (`DROP_THRESHOLD_PCT`, `:30,:681`) — לא תלוי avg20.

#### השוואת מהירות S4 מול S2 (אותה תנועה)

| | מינ׳ מבני | תלות נוספת |
|---|---|---|
| **GB100/TT** | **3 ברים = 15 דק'** | אבל **צבע BLUE/RED** — בפועל +~30 דק' paint-lag → **~45 דק'** |
| **ZLR בסיס** | 13 ברים חלון; ירי על בר-bounce | CCI בלבד (בסיס) — יכול להיות מוקדם יותר מ-GB100 אם הצבע תקוע |
| **REACTIVE** | 20–35 דק' | + FHB + VSA avg |

⇒ "S2 מאוחר יחסית" נכון מבנית מול GB100/TT **התיאורטיים**; ביום-גאפ עם GRAY, **גם S4 paint-locked תקוע** — ואז S2 (CCI/price) עלול להיות *היחיד* שיכול לירות, אבל רק אחרי B4+FHB.

**מספרי audit על 15/16/17:** לא-מוכרע בסשן הזה (DB down). מקור משני: `PATTERN_MISS_AUDIT` F1/F3/F4 + LOG cc 07-19 (TLB/FAMIR/HTLB swings על 07-17 אחרי הרחבת-כיסוי).

---

## שרשרת-מחסומים משותפת (gateway) — סדר ריצה

מקור: `trading_gateway.py::_route_setup_inner`. רק חוסמים קשיחים (לא mutate של סטופ/יעדים):

| # | שער | תנאי חסימה | Cite | שקט? |
|---|---|---|---|---|
| 1 | kill_switch | engaged | `:486-494` | fail-open except |
| 2 | session_gate | מחוץ 08:30–15:00 CT | `:496-500` | |
| 3 | eod_entry_cutoff | חלון אחרון לפני 15:00 CT | `:502-516` | |
| 4 | feed_watchdog | פיד מעופש | `:518-528` | debug על כשל |
| 5 | cooldown | אחרי 2 סטופים | `:532-535` | |
| 6 | SSV | סבל בצד | `:541-545` | דגל |
| 7 | duplicate_fire | כפילות ≤30ש' | `:551-564` | |
| 8 | chop_searching | LAYER0 SEARCHING | `:577-583` | **OFF standing** |
| 9 | opening_type_gate | נגד-דרייב פרה-IB | `:589-613` | |
| 10 | **daytype_playbook** | SKIP / require_with_trend | `:622-662` | רק `.allow` |
| 11 | trend_direction_gate | CCI (אם POSITION off) | `:668-680` | |
| 12 | reactive_location | REACTIVE צד-POC | `:683-698` | |
| 13 | location_gate | קצה-VA / CONT×Variation | `:703-731` | |
| 14 | daytype_position_gate | מיקום×סוג-יום | `:736-756` | inert אם flag=0 |
| 15 | direction_context + cont_trend_filter | CONT נגד dir; REV פטור ב-Neutral/Variation/**Normal** (`NORMAL_ROTATION_FIX_V1` default ON) | `:774-834` | |
| 16 | lsma_flat | שיפוע שטוח | `:850-870` | |
| 17 | news_blackout | חדשות אדומות | `:877-888` | |
| 18 | day_direction_doctrine | נגד-הרחבה | `:894-947` | debug על כשל |
| 19 | **entry_not_confirmed** | בר לא אישר | `:1345-1370` | |
| 20 | rr_entry_gate | R:R נמוך | `:1375-1470` | |
| 21 | zone_limit_late_entry | drift/גיל | `:1496-1548` | |
| 22 | daily/consec loss | עצירות | `:1557-1589` | |
| 23 | s4_risk_cap / pattern_loss_breaker | מטא-S4 | `:1596-1607` | |
| 24 | cluster_guard | DEMO/LIVE | `:1687-1692` | |

**לפני `route_setup` (לא בפיד-החלטות):**

| שער שקט | מי | Cite |
|---|---|---|
| Nontrend → return | כל S2 | `five_min_system.py:1138-1149` |
| chart_patterns_allowed / None | HNS/DBDT/FLAGS | `:1170-1195` |
| FHB clear direction | RI | `:1210-1219` |
| Detector `(None,…)` | כל דטקטור | לפי קובץ |
| YELLOW clear all | כל S4 | `woodies_system.py:619-624` |
| HTLB_DIRECTION_GATE | S4 נגד latch | `:572-590` |
| Paint BLUE/RED | GB100/TT/(ZLR v2) | `gb100.py` / `tt.py` / `zlr.py` |
| emit Auth SKIP / NO_TRADE | S2 | `setup_emitter.py:55-109` |

---

## חלק א' — כרטיסי תבניות

מקרא טבלת-יום: עמודות = Trend_Normal · Trend_DD · Variation · Normal · Neutral_Center · Neutral_Extreme · Nontrend · Nonconviction.  
מקור פסק: `config/daytype_playbook.yaml:129-152`. חוזים: פלייבוק-סגנון / בפועל≈4 אם FIXED_4.

---

### 1) ZLR · S4 CONT

**1. גאומטריה** (`zlr.py`)  
- LOOKBACK=12, מינ׳ 13 ברים (`:32,:180-181`).  
- קיצון \|CCI\|≥`ZLR_CCI_MIN`(100) בחלון → תיקון באזור ±100 → bounce `current>prev` ו-`0<cci<200` LONG (`:200-209`).  
- `ZLR_SPEC_V2`: ≥6 paint BLUE/RED מהקיצון, SWI, 3×EMA34, ΔCCI≥15, \|entry CCI\|≤120, CZI 3/3 (`:64-129,:211-217`).  
- AP1 pullback≤12 (`anti_patterns.py:44-82`); AP8 flat 3-bar range≥50 (`:197-229`).

**2. טריגר** — `bars[-1]` bounce CCI (`:198,:220`). **מתי:** אמצע–סוף תיקון במגמה מבוססת (לא פתיחת-ראלי).

**3. סוגי-יום** (פסק): FULL/FULL/FULL/REDUCED/SKIP/SKIP/SKIP/SKIP. חוזים: FULL→3 סגנון / 4 קבוע; REDUCED→2 תיאורטי.

**4. מחסומים ייחודיים** — SPEC_V2 paint×6 (שקט); YELLOW; playbook SKIP על Neu*/NT; cont_trend_filter; entry_not_confirmed; eod_cutoff.  
DLL fallback ZLR אם Python החמיץ (`woodies_system.py:465-524`).

**5. מימוש** — עוגן ZLR ~15pt (`stop_anchors.yaml`); רצפת-רוטציה 0.8×ATR כולל Normal אם `NORMAL_ROTATION_FIX_V1` (`stop_resolver.py:75-81`); יעדים structural לפי סוג-יום; BE אחרי T1 (סגנון).

**6. 🔴** — אם SPEC_V2 ON: נעול לצבע כמו GB100 → B1. `_s4_day_type` מתעלם מ-override (`woodies_system.py:640-669`) → T2/runner שגויים (MGMT A6).

---

### 2) TLB · S4 CONT

**1.** Linreg 10 CCI; LONG: slope<-2, current>pred+10, rising (`tlb.py:16,:132-137`). SPEC_V2: קיצון ±200 ב-12 + שותף GB100/ZLR/TT (`:84-112`). AP8.  
**2.** בר אחרון — שבירת קו-רגרסיה. אמצע תיקון/חידוש.  
**3.** FULL/FULL/FULL/REDUCED/SKIP/**REDUCED**/SKIP/SKIP.  
**4.** SPEC_V2 שותף חסר → שקט; cont_trend; entry_confirm.  
**5.** עוגן ~15pt; סטנדרט CONT.  
**6. 🔴** — planHelp תואם קוד. Neutral_Extreme=REDUCED (לא SKIP) — ייחודי מול ZLR.

---

### 3) TT · S4 CONT

**1.** מינ׳ 3; **דורש** `trend==BLUE/RED` + רצף TCCI was/touch/bounce ±5/±10 (`tt.py:54-85,:141-144`); AP7 gap≥5; AP8.  
**2.** ניתור TCCI על בר אחרון — ריענון מומנטום.  
**3.** REDUCED×4 סוגי-מגמה/רוטציה; SKIP Neu*/NT/NC.  
**4.** **Paint GRAY = דחייה שקטה לפני gateway** (B1).  
**5.** עוגן ~15pt.  
**6. 🔴** — נעול-צבע; קורבן ראשי של פיגור-paint.

---

### 4) GB100 · S4 CONT

**1.** מינ׳ 3; BLUE + חצייה טרייה 100 על 3 ברים (`gb100.py:91`); AP2 YELLOW; AP6 ≤6 ברים נגד-ZL; AP8.  
**2.** בר חצייה טרייה — סוף תיקון רדוד.  
**3.** כמו TT — REDUCED על Trend/Var/Normal; SKIP Neu*.  
**4.** **Paint + fresh-cross** — ביום-גאפ מפספס (MISS F4).  
**5.** עוגן ~15pt.  
**6. 🔴** — זהה ל-TT + דרישת-fresh (חלון 1-בר).

---

### 5) HTLB · S4 REV

**1.** חלון 15, ≥2 נגיעות ±15, שבירה ±5 (`htlb.py:16-18,:125,:189`). AP4/AP8. Zones ל-bias `[±100,±200]` (`:22-23,:85-104`).  
**2.** שבירת קו אופקי — היפוך/שחרור.  
**3.** FULL/FULL/FULL/REDUCED/REDUCED/REDUCED/SKIP/SKIP.  
**4.** `HTLB_DIRECTION_GATE` מפיל S4 נגד latch (`woodies_system.py:572-590`) — שקט יחסית לפיד.  
**5.** עוגן REV 12–20pt.  
**6. 🔴** — latch ישן מלילה יכול לחסום פתיחה (audit 07-14).

---

### 6) VEGAS · S4 REV

**1.** `VEGAS_SPEC_V2` ON: cup-and-handle CCI, חלון 20, קיצון ±200, rim ±100, handle≥**2**, retrace<50%, כניסה חציית-rim (`vegas.py:75-190,:204-257`). Legacy divergence רק כש-V2 OFF (`:259-407`). AP8; AP3 רק ב-legacy.  
**2.** חציית שפה — סוף מבנה היפוך.  
**3.** SKIP/SKIP/REDUCED/FULL/FULL/FULL/SKIP/SKIP.  
**4.** אין paint; cont_trend לא (REV); entry_confirm כן.  
**5.** עוגן REV.  
**6. 🔴** — `planHelp.ts:274-280` **תואם** cup-and-handle ≥2. `FLAG_INDEX` שאומר handle≥3 — **מיושן**. לא להסתמך על תיעוד divergence כש-V2 ON.

---

### 7) GHOST · S4 REV

**1.** חלון 20; 3 פסגות/שפלים מקומיים; ראש קיצוני; שבירת כתף-3 (`ghost.py:16,:80-86,:140-146`). AP8.  
**2.** שבירת כתף — מאוחר במבנה.  
**3.** כמו VEGAS.  
**4.** entry_not_confirmed חסם GHOST ב-07-17 (EOD).  
**5.** עוגן REV.  
**6. 🔴** — רגיש ל-entry_confirm (B2 פסיקה).

---

### 8) FAMIR · S4 REV

**1.** 5 ברים; כשל ב-[170,210) / מראה; היפוך ≥20; AP9 LSMA (`famir.py:15-16,:72-78,:135-141`).  
**2.** כשל-קיצון — מאוחר במגמה.  
**3.** כמו VEGAS.  
**4.** AP9 LSMA שקט; entry_confirm; eod.  
**5.** עוגן REV.  
**6. 🔴** — LSMA צד הפוך = דחייה בלי פיד-playbook.

---

### 9) HFE · S4 · **מושבת**

**1.** DLL-only trade path; AP5 bars_ago∈[2,12] (`hfe.py:239-259`). `HFE_DISABLED` מסנן (`woodies_system.py:454-457`).  
**2.** —  
**3.** אין תא פלייבוק חי (מוערם כ-disabled ב-YAML `:147`).  
**4.** דגל מושבת — לא מגיע ל-gateway.  
**5.** —  
**6. 🔴** — מושבת במכוון (−$2,987). לא לפתוח בלי פסיקה.

---

### 10) REACTIVE · S2 REV

**1.** B1–B4; מינ׳ buffer 7 (`five_min_system.py:34,:617-815`). B2: VSA UNION מול avg20 **או** 10% מ-B1. COT/AMT רק אם `S2_REQUIRE_COT_AMT=1` (default off). CVD אופציונלי fail-open.  
**2.** B4 מעבר לקיצון B3 — **מאוחר בדהייה**.  
**3.** FULL על כל הסוגים חוץ NT/NC SKIP; `require_with_trend` על Trend/Var.  
**4.** שקט: Nontrend skip (`:1138`); FHB 1–3; VSA avg; CVD reject אם דק; location_gate; emit auth.  
**5.** עוגן ~15pt; structural לפי סוג-יום.  
**6. 🔴** — B2 avg מורעל; FHB; require_with_trend יכול SKIP נגד-מגמה למרות תא FULL.

---

### 11) INITIATIVE · S2 CONT

**1.** B1 הרחבה 1.3–2.5×ATR; B2 test; B3 join; B4 מעל קיצון B1 (`:817-934`).  
**2.** מבחן שני — אמצע–סוף impulse.  
**3.** FULL/FULL/FULL/REDUCED/SKIP/SKIP/SKIP/SKIP.  
**4.** FHB≥7; Auth SKIP על Normal/Neu* בטבלה — אבל **A5:** מפתח `OFA_Initiative` לא נפתר → over-fire FULL (`sizing.py:32-46`).  
**5.** עוגן ~12pt.  
**6. 🔴** — A5 over-fire על Normal (פלייבוק REDUCED / auth SKIP נעקף).

---

### 12) HNS · S2 REV (chart)

**1.** מינ׳ 12; חלון 30; צוואר+1T (`head_shoulders.py:26-31,:141-206`).  
**2.** שבירת צוואר — מאוחר.  
**3.** REDUCED/REDUCED/FULL/FULL/FULL/FULL/SKIP/SKIP + require_with_trend.  
**4.** שקט: `chart_patterns_allowed` על `current_day_type` לא live (`five_min_system.py:1170`); None→skip; רק DAY_TYPE_MODE; dedup 30.  
**5.** T1/T2 = 0.50/0.74 × measure (`:1496-1501`).  
**6. 🔴** — MGMT A4 stale day-type.

---

### 13) DBDT · S2 REV (chart)

**1.** מינ׳ 10; EE/AA; צוואר (`double_bt.py:30-36`).  
**2.** מאוחר אחרי תבנית כפולה.  
**3.** SKIP/REDUCED/REDUCED/FULL/FULL/FULL/SKIP/SKIP.  
**4.** כמו HNS (5a allow-list).  
**5.** כמו HNS.  
**6. 🔴** — A4; Trend_Normal=SKIP בפלייבוק (מודע).

---

### 14) FLAGS · S2 CONT (chart)

**1.** מוט 5–15 ≥16T; דגל 3–8 ≤50% retrace; פריצה+1T (`flags.py:32-40,:141-200`).  
**2.** אמצע המשך אחרי מוט.  
**3.** FULL/FULL/FULL/REDUCED/SKIP/REDUCED/SKIP/SKIP.  
**4.** Pkg 5c allow-list; T2 על `current_day_type` לא `_emit_day_type` (`five_min_system.py:1551`) — A7.  
**5.** T1 יחסי ל-stop; T2 day-fork.  
**6. 🔴** — A7 management; #400 לייב הוכיח שהצינור עובד כשעוברים שערים.

---

### 15) CONFLUENCE_RI_ZLR · S2×S4 CONT

**1.** אין B1–B4; join אותה dir, ts/≤5s, \|Δentry\|≤1pt; G-fresh (`confluence_ri_zlr.py:84-210`).  
**2.** אותו בר כמו ההורים.  
**3.** FULL×4 / SKIP Neu*/NT/NC; require_with_trend.  
**4.** `CONFLUENCE_RI_ZLR_V1` default OFF; LIVE flag נפרד — בלי LIVE נשאר shadow (`trading_gateway.py` ~1642).  
**5.** C1/C2 ±4/±8; stop≤7pt; **2 חוזים** (exempt מ-FIXED_4).  
**6. 🔴** — דגל OFF = לא חי למרות תאי FULL.

---

## חלק ג' — מטריצה 15×8

פסק מ-`daytype_playbook.yaml`.  
**🚫** = קיים שער (לרוב שקט או post-detect) שיכול לחסום למרות שהפסק ≠ SKIP.  
עמודות: TN=Trend_Normal · DD=Trend_DD · Var=Variation · Nor=Normal · NC=Neutral_Center · NE=Neutral_Extreme · NT=Nontrend · NCv=Nonconviction.

| תבנית | TN | DD | Var | Nor | NC | NE | NT | NCv |
|---|---|---|---|---|---|---|---|---|
| ZLR | FULL🚫¹ | FULL🚫¹ | FULL🚫¹ | RED🚫¹ | SKIP | SKIP | SKIP | SKIP |
| TLB | FULL🚫¹ | FULL🚫¹ | FULL🚫¹ | RED🚫¹ | SKIP | RED🚫¹ | SKIP | SKIP |
| TT | RED🚫² | RED🚫² | RED🚫² | RED🚫² | SKIP | SKIP | SKIP | SKIP |
| GB100 | RED🚫² | RED🚫² | RED🚫² | RED🚫² | SKIP | SKIP | SKIP | SKIP |
| HTLB | FULL🚫³ | FULL🚫³ | FULL🚫³ | RED🚫³ | RED🚫³ | RED🚫³ | SKIP | SKIP |
| VEGAS | SKIP | SKIP | RED🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | SKIP | SKIP |
| GHOST | SKIP | SKIP | RED🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | SKIP | SKIP |
| FAMIR | SKIP | SKIP | RED🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | FULL🚫⁴ | SKIP | SKIP |
| HFE | — מושבת — | | | | | | | |
| REACTIVE | FULL🚫⁵ | FULL🚫⁵ | FULL🚫⁵ | FULL🚫⁶ | FULL🚫⁶ | FULL🚫⁶ | SKIP | SKIP |
| INITIATIVE | FULL🚫⁶ | FULL🚫⁶ | FULL🚫⁶ | RED⚠⁷ | SKIP | SKIP | SKIP | SKIP |
| HNS | RED🚫⁸ | RED🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | SKIP | SKIP |
| DBDT | SKIP | RED🚫⁸ | RED🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | SKIP | SKIP |
| FLAGS | FULL🚫⁸ | FULL🚫⁸ | FULL🚫⁸ | RED🚫⁸ | SKIP | RED🚫⁸ | SKIP | SKIP |
| CONFLUENCE | FULL🚫⁹ | FULL🚫⁹ | FULL🚫⁹ | FULL🚫⁹ | SKIP | SKIP | SKIP | SKIP |

**מקרא 🚫:**  
¹ SPEC_V2/YELLOW/cont_trend/entry_confirm/eod/14:30  
² **Paint GRAY** (B1) + fresh-cross + אותם שערי-gateway  
³ HTLB latch-gate + gateway  
⁴ entry_confirm (GHOST/FAMIR ב-07-17) + eod + direction על Trend (לא רלוונטי — SKIP)  
⁵ require_with_trend + FHB + VSA + Nontrend-stale  
⁶ FHB + VSA + Nontrend-stale + location  
⁷ **over-fire** (A5) — הפוך מ-🚫: פסק REDUCED/auth SKIP נעקף  
⁸ chart allow-list על `current_day_type` stale/None + DAY_TYPE_MODE בלבד  
⁹ דגל V1/LIVE כבוי → לא יורה לייב למרות FULL  

`sim_matrix` מאמת רק שכבת-playbook (112 תאים, 0 mismatches) — **לא** את שערי-הצבע/FHB/VSA. לכן המטריצה למעלה מחמירה יותר מ-sim_matrix.

---

## סתירות מדורגות (עלות-עסקאות פוטנציאלית)

| דירוג | סתירה | למה כואב | Cite |
|---|---|---|---|
| 1 | Paint-lag + `current_bar` בלי CCI-direct | S4 TT/GB100/(ZLR v2) עיוורים בראלי; 07-17 בוקר | `bars.py:1073-1096`; `gb100.py:91` |
| 2 | S2 מבני-מאוחר (B4+FHB+VSA avg) | מפספס פתיחות; "תמיד מאוחר" | `five_min_system.py:617-815,:658-659`; FHB |
| 3 | FIXED_4 מתעלם מ-REDUCED | פלייבוק "מופחת" לא ממומש בגודל | `trading_gateway.py:633`; `sierra_command.py:235` |
| 4 | A5 OFA_Initiative | INITIATIVE×Normal over-fire | `sizing.py:32-46` |
| 5 | A2/A4 stale day-type על S2 detection | עיוורון שקט / chart skip | `five_min_system.py:1138-1195` |
| 6 | A6 S4 day-type בלי override | T2/runner שגוי | `woodies_system.py:640-669` |
| 7 | entry_not_confirmed על REV מלאים | GHOST/FAMIR missed 07-17 | `trading_gateway.py:1345-1370` |
| 8 | CONFLUENCE FULL בפלייבוק אבל flag OFF | תא ירוק, ירי לא-חי | `confluence_ri_zlr.py:96-98` |

---

## מה לא הצלחתי להכריע מהקוד

1. **Input המדויק של Sierra Study ID:1** (בר-persistence) — לא בריפו; רק קונבנציה+A1.  
2. **מספרי `audit_pattern_miss` על 15/16/17-07** — Postgres לא זמין בסשן זה (`trust` dialog). להריץ על MacBook המסחר ולהדביק.  
3. **האם `ZLR_SPEC_V2` / `VEGAS_SPEC_V2` / `S2_VSA_VOLUME` דלוקים עכשיו ב-.env** — אסור לקרוא `.env` במשימה; `audit_pattern_miss` מניח ON; הקוד default של רבים הוא OFF. **לא-מוכרע בלי פלט `flag_guard` / FLAG_INDEX חי.**  
4. **BE/runner wiring בפועל מ-`daytype_style.stop_be_early`** — שדה ב-YAML; לא עקבתי עד trade_manager בכל נתיב.  
5. **האם location_gate / DIRECTION_CONTEXT דלוקים חי** — תלוי flags; standing decisions ב-CLAUDE.md לכמה שערי-chop, לא לכל השערים כאן.  
6. **השוואת נקודות מדויקת "כניסת S2 אחרי כמה pt מהקצה"** — דורש audit על DB.  
7. **האם YELLOW בכלל מגיע מ-DLL החי** — בנתיב Study ID:1 נראה שלא; לא אומת בלוג חי.

---

## איך מייקל עובר על זה

1. קרא **B1 + B2** (למעלה).  
2. לכל תבנית שחשובה מחר — כרטיס + שורת-מטריצה.  
3. כל 🚫 על תא FULL/REDUCED = מועמד לפסיקה או לתיקון (לא "באג אוטומטי").  
4. אל תסמן "אין מחסומים" לפי `sim_matrix` בלבד — הוא לא רואה צבע/FHB/VSA.
