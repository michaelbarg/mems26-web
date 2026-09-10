# למה היצרנים של TOWARD-POC הפסיקו להגיע לברוקר — ומה הכי-קטן שמחזיר אותם

**נכתב:** 2026-09-10 08:35→09:05 IL · **סוכן:** cowork-dev · **מצב:** READ-ONLY (אפס עריכת קוד/‏.env/‏שירותים/‏דגלים)
**בסיס-תמחור:** `pnl_sierra` בלבד · `mode='live'` · `state<>'CANCELLED'` · MES $5/נקודה
**קודמים:** `docs/reports/AUGUST_VS_SEPTEMBER_2026-09-10.md` · `docs/reports/LADDER_LOCATION_OPENING_2026-09-10.md`
**חלון A** = 2026-08-01…08-28 · **חלון B** = 2026-08-31…09-09 · **"עידן-נקי"** = מ-2026-08-19 09:22 IL (ראה §2)

---

## 0 · התשובה בארבע שורות

1. **השאלה מניחה קבוצת-יצרנים שאינה קיימת.** `TOWARD-POC` אינו יצרן — הוא **מיקום**.
   הדלי של +$1,261.25 באוגוסט מורכב מ-**ZLR (8 / +$473.75)**, REACTIVE_LONG (3 / +$400),
   INITIATIVE_SHORT, GB100, HTLB. **אותו ZLR** נתן גם 11 עסקאות `CHASE` באותו חודש.
   היצרנים לא נעלמו — **המיקום** נעלם.
2. **הירידה אינה בגילוי.** ריפליי של הגלאי עצמו על ברים אמיתיים, עם **הכלל מוקפא**, נותן
   **2.06 יריות-REACTIVE לסשן באוגוסט מול 2.12 בספטמבר**. "קריסת-הגילוי" שרואים בפיד-ההחלטות
   היא **ארטיפקט-מדידה** של באג שתוקן ב-19.08 09:22 (`_bar_buffer` היה מאפיין-מחלקה משותף).
3. **הירידה היא בשער.** ‏TOWARD-POC: שיעור-מעבר-השערים ירד **29.7% → 9.4%**, בעוד ש-CHASE-POC
   **עלה** 30.5% → 38.5%. החוסם הדומיננטי הוא **`awaiting_release`** (‏31 מ-52 באוגוסט-נקי,
   21 מ-45 בספטמבר) — והמנגנון מבני: `RELEASE_ENTRY_GATE_V1` דורש שהמחיר **יעזוב את האזור**,
   כלומר הוא הופך כניסה-לכיוון-הערך לכניסה-הרחק-מהערך, או מוחק אותה.
4. **🔴 והשער הזה כבר כבוי** (`.env:469 RELEASE_ENTRY_GATE_V1=0`, מ-08.09 18:02).
   בשני הסשנים שאחריו TOWARD עדיין עובר רק **5.9%** — כי **`dalton_intent` לקח את המקל**
   (8 מ-16 חסימות-TOWARD). ו-`DALTON_PLAYBOOK_V1` הודלק **אמש 23:36** ⇒ **היום הוא הסשן
   המלא הראשון שלו.** בריפליי הוא מסיר n=6 בשווי **+$1,194.38** בספטמבר ו-n=7 בשווי
   **+$948.75** באוגוסט — בדיוק את הדלי שהרוויח.

---

## 1 · תיקון-מסגרת: מי בכלל מייצר TOWARD-POC

`TOWARD-POC` = הכניסה מצביעה **חזרה** אל ה-POC (LONG מתחת ל-POC · SHORT מעליו),
POC-כפי-שהיה-בכניסה מ-`v9_tpo_history`. אותה הגדרה בדיוק כמו בדוח-הסולם §2.5.

| יצרן | A: TOWARD n / Σ$ / ניצחון | A: CHASE n / Σ$ | B: TOWARD | B: CHASE |
|---|---|---|---|---|
| **ZLR** | **8 / +473.75 / 75%** | 11 / +57.50 | 0 | 4 / −321.25 |
| **REACTIVE_LONG** | **3 / +400.00 / 100%** | — | 0 | — |
| INITIATIVE_SHORT | 2 / +208.75 / 100% | — | 0 | 4 / −271.25 |
| GB100 | 2 / +127.50 / 100% | 1 / +140.00 | 0 | 3 / −67.50 |
| (ללא-תווית) | 3 / +123.75 / 100% | 5 / −263.75 | 0 | 2 / −17.50 |
| HTLB | 1 / +83.75 | 1 / +28.75 | 0 | — |
| REACTIVE_SHORT | 2 / +37.50 / 50% | 1 / +41.25 | 0 | 1 / +116.25 |
| OPENING_ORR | 1 / −95.00 | — | 0 | — |
| TREND_STEP | 2 / −98.75 | 2 / −67.50 | 0 | — |
| GHOST / VEGAS | — | — | 1 / +76.25 · 1 / −40.00 | 1 / −52.50 |
| **סה״כ** | **24 / +1,261.25 / 75%** | **27 / −233.75 / 52%** | **2 / +36.25** | **21 / −708.75 / 38%** |

> **14 מ-24 עסקאות-ה-TOWARD של אוגוסט באו מיצרנים שממשיכים לירות בברוקר בספטמבר**
> (ZLR, GB100, INITIATIVE_SHORT, REACTIVE_SHORT) — **רק בצד ה-CHASE.**
> היחידים שבאמת נעלמו הם REACTIVE_LONG (+$400) ו-HTLB (+$83.75).

---

## 2 · 🔴 ארטיפקט-המדידה שחייבים לנטרל לפני כל השוואה

`git show 60a68845` (2026-08-19 09:22 IL), `five_min_system.py`:

```
+        # 2026-08-19 audit (S2-F3): _bar_buffer was ONLY a class attribute, so
+        # every FiveMinSystem() shared one list — /api/v9/status hydrates a
+        # scratch instance per poll and appended stale DB bars into the SAME
+        # buffer the live instance detects on (unbounded leak + replay-bar
+        # injection). Instance-own the buffer.
+        self._bar_buffer: List[Dict] = []
```

עד 19.08 09:22 **כל poll ל-`/api/v9/status` הזריק ברים היסטוריים לתוך החוצץ שהגלאי החי רץ עליו.**
מכאן שכל ספירת-מועמדים מהפיד לפני התאריך הזה מנופחת. כמותית, מול ריפליי-הגלאי על ברים אמיתיים:

| תקופה | מועמדי-REACTIVE בפיד (מדודד) | יריות בריפליי | יחס-ניפוח |
|---|---|---|---|
| 08-05…08-18 (‏10 סשנים, **לפני** התיקון) | **174** | 14 | **×12.4** |
| 08-19…08-28 (‏8 סשנים, **אחרי**) | 33 | 23 | ×1.43 |
| 08-31…09-09 (‏8 סשנים) | 23 | 17 | ×1.35 |

**מסקנה: כל השוואת-קצב יולי↔ספטמבר על הפיד היא חסרת-ערך. מ-19.08 ואילך הפיד מהימן.**
זו בדיוק מלכודת T-252 בגרסה חמורה יותר — לא כפילות פי-3, אלא פי-12.

---

## 3 · טבלת-הפירוק לפי יצרן — היכן בדיוק נופל, ובאיזה תאריך

מחרוזות-הסיווג **מהקוד**, לא מהזיכרון:
`f"{kind}_{direction}"` ב-`five_min_system.py:2913/2963` עם `kind="REACTIVE"` (`:1040` LONG, `:1110` SHORT) ⇒
`REACTIVE_LONG` / `REACTIVE_SHORT` · `re_acceptance.py:180-181` ⇒ `RE_ACCEPTANCE` ·
`va_fade.py:152` `f"VA_FADE_{direction}"` ⇒ `VA_FADE_LONG`/`VA_FADE_SHORT` ·
`failed_break.py:140` `f"FAILED_BREAK_{direction}"` · `five_min_system.py:1552` ⇒ `FAILED_RE_IB`.

| יצרן | גילוי (ריפליי, ברים אמיתיים) | הגיע ל-`route_setup` | עבר את השערים | הגיע לברוקר | **היכן נופל** | **תאריך** |
|---|---|---|---|---|---|---|
| **`REACTIVE_LONG`** | **חי** — 44 יריות / 38 סשנים; ספט׳ ≈ אוג׳ | חי (‏DETECTED≈ROUTED) | 6 מ-24 סשנים אחרי 04.08 | **אחרון 2026-08-04** | **שער + רגל-לייב** | **05.08** |
| **`REACTIVE_SHORT`** | **חי** — 48 יריות | חי | נדיר | אחרון **2026-08-31** (#877) | **שער** | **01.09** |
| `RE_ACCEPTANCE` | **0 בכל הארכיון ובכל המצבים** | 0 | 0 | 0 | **מעולם לא נבנה ללייב** — `RE_ACCEPTANCE_V1` לא-מוגדר עד 08.09, ואז `shadow` | — |
| `VA_FADE_LONG/SHORT` | 5 (‏09-02…09-08) | 5 | **0** | 0 | דגל `shadow` + חיווט בתוך בלוק-FIRST_HOUR | נולד 31.08 בצל |
| `FAILED_BREAK_LONG/SHORT` | 10 (‏08-28…09-08) | 10 | 1 | 0 | דגל `shadow` | נולד 27.08 בצל |
| `FAILED_RE_IB` | 4 (‏09-08/09) | 4 | **0** | 0 | דגל `shadow` | נולד 08.09 בצל |

> **ארבעה מששת היצרנים ששמם בפקודה מעולם לא הגיעו לברוקר — הם נולדו בצל בסוף-אוגוסט/ספטמבר.
> הם לא "הפסיקו"; הם לא התחילו.** רק REACTIVE אי-פעם ירה חי, והוא נופל בשער.

### 3.1 · ‏DETECTED מול ROUTED — הוכחה שאין חוסם-סמוי במעלה-הזרם

`candidate_ledger` דולק מ-2026-08-25. בעידן-הליגר, מדודד לפי `candidate_id`:

```
REACTIVE (08-25..09-09):   DETECTED=31   ROUTED=30
ZLR      (08-25..09-09):   DETECTED=256  ROUTED=238
```
**‏DETECTED ≈ ROUTED ⇒ שום `_trig=None` בתוך `five_min_system` אינו בולע REACTIVE.**
(זה **לא** נכון ליצרני-הפתיחה — שם הפער מבני, ראה דוח-הסולם §3.2.)

### 3.2 · ריפליי-הגלאי: הכלל מוקפא, רק הברים משתנים

`/tmp/whysilent/replay2.py` — מייבא את `FiveMinSystem` האמיתי, מזריק ברים מ-`v9_bars_5min_woodies`,
מנטרל את הפוטפרינט (COT/AMT/belly ⇒ `None`, כמו בלייב), `S2_VSA_VOLUME=1`, `variant=UNION`,
`S2_REACTIVE_DAYTYPE_V1=0` (המקל **מרפה** גיאומטריה — כיבויו הופך את המספר לרצפה שמרנית),
חלון-כניסה 16:30–23:00 IL.

```
A1 07-20..08-04: sessions=12  fires=38  per-session=3.17
A2 08-05..08-28: sessions=18  fires=37  per-session=2.06
B  08-31..09-09: sessions= 8  fires=17  per-session=2.12
TOTAL over 38 sessions: 92  (LONG 44 / SHORT 48)
```

> **הגלאי לא נחלש. ספטמבר (2.12/סשן) זהה לאוגוסט (2.06/סשן).**
> ‏17 יריות-REACTIVE בחלון-ספטמבר · **אפס הגיעו לברוקר.**

### 3.3 · שער-הנפח של VSA — ההשערה נבדקה ונדחתה

`config/s2_firing.yaml` ⇒ `variant: UNION` (מייקל 12.06). ב-UNION,
`b2_drop = _vsa_pass or _rvol_pass or _strict_pass` (`five_min_system.py:928-936`) — הווריאנט
ה**רפוי** ביותר, כך ש-`b2_vol <= 0.7 × rolling_avg` **אינו** התנאי הכובל היחיד.
בנוסף `S2_ADAPTIVE_THRESHOLDS_V1=1` הוא **אינרטי** לשער-הנפח: הוא יושב ב-`elif` אחרי
`if S2_VSA_VOLUME:` (`:928` מול `:937`), ו-`S2_VSA_VOLUME=1` מאז יוני.
`S2_CVD_DETECTION_V1` עבר `1`→`shadow` (‏~25.08, סנפשוט `20260825T072517Z`) — כלומר **הורפה**,
ובכל מקרה `_cvd is None` הוא fail-open (`:1025`). `S2_REQUIRE_COT_AMT` לא-מוגדר ⇒ עוקף (`:903-905`).
**המספר שמכריע:** הריפליי בסעיף 3.2 מריץ בדיוק את הקוד הזה על ברי-ספטמבר האמיתיים ומקבל
**אותו קצב-גילוי כמו באוגוסט**. אם משטר-הנפח היה מזיז את השער, זה היה מופיע שם. לא הופיע.

---

## 4 · השער: היכן TOWARD-POC נהרג, מתי, ובכמה

מדודד לפי `candidate_id`, RTH 16:30–23:00, **עידן-נקי בלבד**, מוגבל ל-17 היצרנים שהפיקו
לפחות עסקת-ברוקר אחת מ-20.07 (‏`LIVE_PATS`).

| | AUG-נקי 08-19…08-28 (8 סשנים) | SEP 08-31…09-09 (7 סשנים) | 09-08…09-09 (אחרי כיבוי release) |
|---|---|---|---|
| **TOWARD נוצרו** | 91 (‏11.4/סשן) | 53 (‏7.6/סשן) | 17 (‏8.5/סשן) |
| **TOWARD עברו שערים** | **27 = 29.7%** | **5 = 9.4%** | **1 = 5.9%** |
| TOWARD לברוקר | 8 | 4 | 1 |
| **CHASE נוצרו** | 262 (‏32.8/סשן) | 226 (‏32.3/סשן) | 74 (‏37.0/סשן) |
| **CHASE עברו שערים** | **80 = 30.5%** | **87 = 38.5%** | **26 = 35.1%** |
| CHASE לברוקר | 16 | 22 | 6 |

> **הייצור ירד ×0.67. שיעור-המעבר ירד ×0.32. ‏CHASE — ללא שינוי (ואף עלה).**
> **השער, ולא הגלאי, הוא הגורם הדומיננטי — והוא סלקטיבי כלפי TOWARD-POC.**

**מפקד-חוסמים ל-TOWARD (מדודד):**

```
AUG-נקי : awaiting_release 31 | eod_entry_cutoff 7 | lsma_flat 6 | daytype_playbook 5 |
          cont_trend_filter 4 | day_entry_budget 4 | rr_hard_floor 2 | cold_start_guard 2
SEP     : awaiting_release 21 | dalton_intent:stand_down 6 | daytype_playbook 5 |
          eod_entry_cutoff 5 | rr_entry_gate 3 | location_gate 2 | dalton_intent:kind 2
09-08/09: dalton_intent:stand_down 6 | rr_entry_gate 3 | location_gate 2 |
          eod_entry_cutoff 2 | dalton_intent:kind 2 | awaiting_release 1
```

### 4.1 · המנגנון, לא המתאם

`backend/v9/systems/release_gate.py:19-33` — שלושת התנאים של `RELEASE_ENTRY_GATE_V1`:

> `3. RELEASE — a bar CLOSES beyond the rotation zone, with volume above the contracted mean.`
> `Price actually leaves.`

**כניסת-TOWARD-POC היא בהגדרה כניסה שעדיין לא עזבה את האזור** — היא מצביעה **חזרה** אל הערך.
שער שמחייב "המחיר עזב" **חייב** להסיר בדיוק את הדלי הזה, או לדחות אותו עד שהמחיר כבר רחוק
מה-POC — כלומר **להפוך TOWARD ל-CHASE**. זה מנגנון מבני, לא מתאם.

### 4.2 · 🔴 והשער כבר כבוי

`.env:469 RELEASE_ENTRY_GATE_V1=0` (כובה 08.09 18:02, סנפשוט `20260908T141909Z`).
בשני הסשנים שאחרי — TOWARD עדיין עובר **5.9%**, ו-**`dalton_intent` הוא כעת החוסם הראשי**
(‏6 `stand_down` + 2 `kind` = 8 מ-16 חסימות-TOWARD).
`DALTON_PLAYBOOK_V1` עבר 0→1 ב-**09.09 23:36** (סנפשוט `20260909T203630Z`) ⇒
**10.09 הוא הסשן המלא הראשון שבו הוא רץ מהפתיחה.**

---

## 5 · השחזור, עם המספר

**כיול-המודל קודם (Rule 2).** אותו מודל "יעד-או-סטופ + BE-אחרי-T1" הורץ על **44 עסקאות-הברוקר
האמיתיות** של העידן-הנקי, עם הסטופ/היעדים שלהן עצמן:

```
CALIBRATION n=44  model Σ$-146.20  broker Σ$-292.50   ratio=0.50
```
**המודל אופטימי ב-‏$146.30 על 44 עסקאות ≈ +$3.3 לעסקה.** כל מספר להלן — נכה ממנו ~$3.3/עסקה.

**סימולציה רציפה, סלוט-לייב אחד, סייזינג `RISK_BUDGET_SIZING_V1` (‏225 / min 3 / cap 5),
הסולם הנוכחי.** ‏P&L אמיתי היכן שהעסקה באמת נסחרה; מודל היכן שהיא נחסמה
(סטופ/יעדים מ-`mfe_track` שהשער עצמו כתב — לא מומצאים).

| # | מדיניות | AUG-נקי n / Σ$ / ניצחון | SEP n / Σ$ / ניצחון | סטטוס-פסיקה |
|---|---|---|---|---|
| **BASE** | **מה שקרה בפועל (מה שהשערים העבירו)** | 14 / **+398.75** / 71% | 21 / **−655.00** / 38% | — |
| **P1** | TOWARD-POC בלבד, כל שאר השערים מוסרים | 17 / **+811.25** / 71% | 16 / **+720.12** / 56% | 🔴 התנהגות-סיכון חדשה |
| **P2** | P1 **+ DaltonPlaybook** (הדגל=1 היום) | 7 / **+13.25** / 57% | 10 / **−280.28** / 50% | חי כבר |
| **P3** | TOWARD-POC, כל השערים נשמרים **חוץ מ-`awaiting_release`** | 11 / **+946.25** / 73% | 9 / **+1,074.38** / 78% | השער כבר כבוי |
| **P4** | **הסטטוס-קוו + TOWARD שרק `awaiting_release` עצר** | 17 / **+981.25** / 71% | 20 / **+433.12** / 55% | השער כבר כבוי |

> **‏P4 מול BASE: ‏+$582.50 באוגוסט · +$1,088.12 בספטמבר. חיובי בשני המשטרים.**
> **אבל P4 אינו ניתן-לביצוע היום — `awaiting_release` כבר כבוי.** ‏P4 מודד את הנזק שהשער
> **כבר גרם** בין 31.08 ל-08.09, לא הזדמנות פתוחה.

### 5.1 · 🔴 מה ש-DaltonPlaybook עושה לדלי הזה — הפריט הדחוף

מריצים את `dalton_playbook.evaluate_gate` (‏`kinds_apply_to: counter_bias_only`, `phase_d: manage_only`)
על עסקאות-P3, סלוט-אחד:

| חלון | Dalton **משאיר** | Dalton **מסיר** | לפי כלל/שלב |
|---|---|---|---|
| AUG-נקי | n=4 · **Σ −$2.50** | **n=7 · Σ +$948.75** | `kind`/C ×3 · `kind`/B ×2 · `kind`/A ×1 · `stand_down`/D ×1 |
| SEP | n=3 · **Σ −$120.00** | **n=6 · Σ +$1,194.38** | `kind`/B ×2 · `kind`/C ×1 · `stand_down`/A ×2 · `stand_down`/D ×1 |

הפירוט לספטמבר (מודל, אלא אם צוין REAL):

```
2026-08-31 17:45 REACTIVE_LONG  LONG  MODEL +201.88  dalton_intent:kind        phase C
2026-09-01 16:50 GB100          LONG  MODEL  +82.50  dalton_intent:kind        phase B
2026-09-02 16:35 ZLR            LONG  MODEL +277.50  dalton_intent:stand_down  phase A
2026-09-02 19:10 ZLR            SHORT MODEL  +42.50  ALLOW                     phase C
2026-09-03 17:15 ZLR            LONG  MODEL +235.00  dalton_intent:kind        phase B
2026-09-03 19:30 GB100          SHORT MODEL -122.50  ALLOW                     phase C
2026-09-03 22:05 GB100          SHORT MODEL +185.00  dalton_intent:stand_down  phase D
2026-09-08 16:35 GB100          SHORT MODEL +212.50  dalton_intent:stand_down  phase A
2026-09-09 19:05 VEGAS          LONG  REAL   -40.00  ALLOW                     phase C
```

**המנגנון של `kind`:** `config/dalton_playbook.yaml` ממפה `ZLR: BREAK` ו-`GB100: BREAK` —
**ללא תלות במיקום**. אבל ZLR שמצביע חזרה אל ה-POC הוא **רוטציה אל הערך**, לא פריצה.
תחת `kinds_apply_to: counter_bias_only`, `BREAK` נגד-הטיה נדחה. כלומר הדלי הרווחי נדחה
**בגלל תווית שגויה**, לא בגלל שיפוט-סיכון.

### 5.2 · השינוי הכי-קטן, וזה שכבר קיים חצי ממנו בקוד

`five_min_system.py:1361-1385` — `_compute_location_vs_poc` כבר טוען את ה-POC החי מייצוא-סיירה
ומחשב מרחק, בדיוק בנקודת-הירי (`:2827`, נכנס ל-`setup["location_vs_poc_vol"]` ב-`:2909`):

```python
1380:            dist = abs(bar_mid - poc)
```

**ה-`abs()` בשורה 1380 הוא בדיוק המקום שבו הסימן המפריד בין דלי של +$1,261.25 לדלי של
−$233.75 נזרק.** ‏POC כבר טעון · המרחק כבר מחושב · הכיוון כבר ידוע. תווית-TOWARD/CHASE היא
**סימן, לא מקור-נתונים חדש**.

| אפשרות-שחזור | AUG n/Σ$/WR | SEP n/Σ$/WR | סטטוס-פסיקה |
|---|---|---|---|
| **R1 · לתעד את הסימן** (‏`location_vs_poc_signed` ל-quality/ליגר, אפס שינוי-החלטה) | — | — | **תיקון-קוד למימוש `LEARNING_DOCTRINE` — לא דורש פסיקה חדשה** |
| **R2 · פטור-מיקום ב-Dalton** (‏TOWARD-POC ⇒ `entry_kind` = `VALUE_RETURN`, לא `BREAK`) | +948.75 (n=7) שנשמרים | +1,194.38 (n=6) שנשמרים | 🔴 **התנהגות-סיכון חדשה — דורשת מילה של מייקל** |
| **R3 · להוציא `RE_ACCEPTANCE` מהצל** | **0 מועמדים בכל הארכיון** | **0** | חסר-משמעות — אין מה למדוד |
| **R4 · להוציא `VA_FADE` ל-כל-הסשן** | 0 מועמדים | 5 מועמדים · **0 עברו שער** | חסר-משמעות עדיין |
| **R5 · לכייל מחדש את יחס-ה-VSA (0.7×)** | — | — | **מופרך** — הווריאנט הפעיל הוא `UNION`; §3.3 |
| **R6 · להחזיר `RELEASE_ENTRY_GATE_V1`** | — | — | **לא. הוא כבר כבוי וזה נכון.** |

---

## 6 · מה המספרים **אינם** יכולים לומר

1. **‏n=9 בחלון-ספטמבר ו-n=11 באוגוסט אינם edge.** סף שמכויל על 74 עסקאות הוא התאמה-בתוך-המדגם.
   `LEARNING_DOCTRINE_2026-09-09`: **הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל.**
2. **המודל אופטימי ב-‏$3.3/עסקה** (‏§5, n=44). על P4-ספטמבר (n=20) זה ~$66 — לא הופך את הסימן
   של +$1,088, אבל מכרסם.
3. **‏P1/P3/P4 מתמחרים בעיקר מועמדים שנחסמו.** מועמד ש**עבר** אינו נושא `mfe_track`, ולכן
   הסימולציה משתמשת ב-P&L האמיתי שלו — אך מועמדים שעברו ולא נסחרו (‏`live_slot_occupied`)
   אינם ניתנים-לתמחור כלל (‏27 דילוגים בספטמבר).
4. **תווית-סוג-היום ב-Dalton נלקחה מ-`v9_day_type_history`** — התווית ה**מיושבת**, כלומר
   הצצה-קלה-לעתיד. ‏`direction_hint=None` עושה `drive/trend_direction ⇒ BOTH`, כלומר **מתירני
   יותר** מהלייב. שתי ההטיות פועלות לטובת Dalton בטבלה — כלומר הנזק האמיתי שלו כנראה גדול יותר.
5. **‏TOWARD/CHASE תלוי בתצלום-הערך שנבחר** — אזהרת דוח-הסולם §2.4 עומדת בעינה
   (‏POC-בכניסה שונה מהמיושב ב-40/51 באוגוסט). כאן נבחר POC-מתפתח כי זה מה שהמנוע רואה.
6. **יצרן שיורה 2 פעמים בסשן לא יכול לשאת ספר.** ‏REACTIVE = 17 יריות ב-8 סשנים.
   גם אם כל אחת הייתה עוברת, זה לא "מחזיר את אוגוסט".

---

## 7 · הפריט שנפתח כאן ולא נסגר

**מדוע ייצור-ה-TOWARD ירד ×0.67 (‏11.4 → 7.6 לסשן) בעוד CHASE נשאר שטוח?**
זה לא שער — זה הגלאי או השוק. לא נבדק כאן. הוא קטן מהאפקט של השער (×0.32) אבל אמיתי.

---

## 8 · נספח — פלט גולמי

כל המספרים הופקו 2026-09-10 08:35–09:05 IL מ-`postgresql://localhost/mems26` דרך `psycopg2`,
מ-`~/SierraChart_Data/v9_export/decisions_archive/` + `~/SierraChart_Data/v9_archive/*/`,
ומ-`~/mems26_snapshots/*/env/.env`. סקריפטים: `/tmp/whysilent/{s1,s2,s5,s6,s7,s8,s10,replay2,price,toward,toward2,sim,sim2,diag,final}.py`.

### 8.1 · דלי-המיקום לפי יצרן

```
=== TOWARD-POC producers, window A (the +$1,261.25 bucket) ===
  ZLR                      n= 8  $  +473.75  win=75%
  REACTIVE_LONG            n= 3  $  +400.00  win=100%
  INITIATIVE_SHORT         n= 2  $  +208.75  win=100%
  GB100                    n= 2  $  +127.50  win=100%
  (none)                   n= 3  $  +123.75  win=100%
  HTLB                     n= 1  $   +83.75  win=100%
  REACTIVE_SHORT           n= 2  $   +37.50  win=50%
  OPENING_ORR              n= 1  $   -95.00  win=0%
  TREND_STEP               n= 2  $   -98.75  win=0%
=== CHASE-POC producers, window A ===
  GB100 1 +140.00 | ZLR 11 +57.50 | REACTIVE_SHORT 1 +41.25 | TT 1 +33.75 | HTLB 1 +28.75
  INITIATIVE_LONG 3 +23.75 | TREND_STEP 2 -67.50 | DOUBLE_BOTTOM_EE_LONG 1 -85.00
  BEAR_FLAG_SHORT 1 -142.50 | (none) 5 -263.75
=== window B ===
  TOWARD: GHOST 1 +76.25 | VEGAS 1 -40.00
  CHASE : INITIATIVE_LONG 4 +142.50 | REACTIVE_SHORT 1 +116.25 | (none) 2 -17.50 | GHOST 1 -52.50
          GB100 3 -67.50 | OPENING_DRIVE 1 -100.00 | BULL_FLAG_LONG 1 -137.50
          INITIATIVE_SHORT 4 -271.25 | ZLR 4 -321.25
```

### 8.2 · שורות v9_trades לכל היצרנים שבפקודה (כל המצבים, כל ההיסטוריה)

```
('FAILED_BREAK_LONG',  'shadow',  4, 2026-09-01 .. 2026-09-08)
('FAILED_BREAK_SHORT', 'shadow',  2, 2026-09-04 .. 2026-09-08)
('FAILED_RE_IB',       'shadow',  4, 2026-09-08 .. 2026-09-09)
('VA_FADE_LONG',       'shadow',  3, 2026-09-04 .. 2026-09-08)
('REACTIVE_LONG',      'live',   10, 2026-07-07 .. 2026-08-04)   ← LIVE ENDS 08-04
('REACTIVE_LONG',      'shadow', 46, 2026-06-12 .. 2026-09-07)   ← DETECTION CONTINUES
('REACTIVE_SHORT',     'live',   18, 2026-07-07 .. 2026-08-31)
('REACTIVE_SHORT',     'shadow', 75, 2026-06-12 .. 2026-09-09)
('ZLR',                'live',   59, 2026-07-08 .. 2026-09-07)
('ZLR',                'shadow',346, 2026-06-09 .. 2026-09-09)
RE_ACCEPTANCE / VA_FADE_SHORT: no rows in any mode, ever.
```

### 8.3 · ריפליי-הגלאי, כלל מוקפא, ברים אמיתיים (‏38 סשנים)

```
2026-07-20  1 | 07-21  4 | 07-22  3 | 07-23  3 | 07-24  7 | 07-27  2 | 07-28  4 | 07-29  2
2026-07-30  3 | 07-31  4 | 08-03  3 | 08-04  2 | 08-05  4 | 08-06  1 | 08-07  1 | 08-10  1
2026-08-11  1 | 08-12  0 | 08-13  1 | 08-14  1 | 08-17  2 | 08-18  2 | 08-19  6 | 08-20  4
2026-08-21  3 | 08-24  4 | 08-25  1 | 08-26  0 | 08-27  3 | 08-28  2 | 08-31  2 | 09-01  2
2026-09-02  3 | 09-03  5 | 09-04  1 | 09-07  3 | 09-08  0 | 09-09  1
TOTAL 92 (LONG 44 / SHORT 48)
A1 07-20..08-04: 12 sessions, 38 fires, 3.17/session
A2 08-05..08-28: 18 sessions, 37 fires, 2.06/session
B  08-31..09-09:  8 sessions, 17 fires, 2.12/session
```

### 8.4 · מפקד-חסימות REACTIVE, מדודד, שלוש תקופות

```
P1  07-20..08-04 (304 מועמדים, מנופחים ×12 — ראה §2)
    daytype_playbook=81 feed_watchdog=30 awaiting_release=23 eod_entry_cutoff=15
    entry_not_confirmed=13 direction_context=13 location_gate=11 ...
    passed → LIVE-OK(shadow_only)=85, LIVE-OK(live)=13
P2  08-05..08-28 (281, מנופחים עד 18.08)
    cold_start_guard=154 daytype_playbook=22 session_gate_closed=17 awaiting_release=16 ...
    passed → shadow_only=36, live=3, live_slot_occupied=2
P3  08-31..09-09 (23, נקי)
    daytype_playbook=7 awaiting_release=6 location_gate=2 eod_entry_cutoff=2
    rr_hard_floor=1 dalton_intent:kind=1 direction_compass=1
    passed → live_slot_occupied=2, live=1
```

### 8.5 · שיעורי-מעבר TOWARD/CHASE, יצרנים חיים-בלבד

```
AUG-clean (8 sessions)  TOWARD gen= 91 (11.4/sess) passed=27 (29.7%) live=8
                        CHASE  gen=262 (32.8/sess) passed=80 (30.5%) live=16
SEP       (7 sessions)  TOWARD gen= 53 ( 7.6/sess) passed= 5 ( 9.4%) live=4
                        CHASE  gen=226 (32.3/sess) passed=87 (38.5%) live=22
SEP post-release-OFF    TOWARD gen= 17 ( 8.5/sess) passed= 1 ( 5.9%) live=1
(2 sessions)            CHASE  gen= 74 (37.0/sess) passed=26 (35.1%) live=6
```

### 8.6 · הסימולציה הרציפה

```
-- AUG-clean 08-19..08-28
  BASE-0) status quo: only what the gates passed             n= 14  Σ$  +398.75  win= 71%
  P1) TOWARD-POC only, every other gate removed              n= 17  Σ$  +811.25  win= 71%
  P2) P1 + DaltonPlaybook (flag is 1 today)                  n=  7  Σ$   +13.25  win= 57%
  P3) TOWARD + keep every gate except awaiting_release       n= 11  Σ$  +946.25  win= 73%
  P4) status quo PLUS TOWARD ones only awaiting_release stopped n=17 Σ$ +981.25  win= 71%
-- SEP 08-31..09-09
  BASE-0) status quo: only what the gates passed             n= 21  Σ$  -655.00  win= 38%
  P1) TOWARD-POC only, every other gate removed              n= 16  Σ$  +720.12  win= 56%
  P2) P1 + DaltonPlaybook (flag is 1 today)                  n= 10  Σ$  -280.28  win= 50%
  P3) TOWARD + keep every gate except awaiting_release       n=  9  Σ$ +1074.38  win= 78%
  P4) status quo PLUS TOWARD ones only awaiting_release stopped n=20 Σ$  +433.12  win= 55%
```

### 8.7 · כיול-המודל מול הברוקר (‏Rule 2)

```
CALIBRATION n=44  model Σ$-146.20  broker Σ$-292.50   ratio=0.50
  (44 real broker rows 08-19..09-09, each priced with its OWN initial_stop/t1/t2/t3
   and its OWN contract count, walked on v9_bars_5min_woodies to 23:00 IL)
```

### 8.8 · היסטוריית-הדגלים הרלוונטית (מ-`~/mems26_snapshots/*/env/.env`)

```
20260819T053705Z_margin-fallback-4-on        : (no S2_ADAPTIVE_THRESHOLDS_V1, no S2_REACTIVE_DAYTYPE_V1)
20260821T084053Z_pre-TARGET_MIN_SPACING...   : S2_ADAPTIVE_THRESHOLDS_V1=1 S2_REACTIVE_DAYTYPE_V1=1
20260825T072517Z_pre-4-contracts             : S2_CVD_DETECTION_V1=1 → shadow
20260831T071753Z_pre-5-contracts-ruling      : VA_FADE_V1=shadow (first appearance)
20260908T135402Z_opening-ladder-p0-08.09     : RE_ACCEPTANCE_V1=shadow, FAILED_RE_IB_V1=shadow (first)
20260908T141909Z_release-gate-off-live-08.09 : RELEASE_ENTRY_GATE_V1 1 → 0   ← 08.09 18:02 IL
20260909T203630Z_night-repair-0909           : DALTON_PLAYBOOK_V1 0 → 1      ← 09.09 23:36 IL
.env today: RELEASE_ENTRY_GATE_V1=0 (:469) · DALTON_PLAYBOOK_V1=1 (:124) ·
            RE_ACCEPTANCE_V1=shadow (:121) · VA_FADE_V1=shadow (:675) ·
            FAILED_RE_IB_V1=shadow (:122) · ZLR_SHADOW_V1=1 (:119) ·
            ENTRY_LOCATION_QUALITY_V1=1 (:713) · DAYTYPE_LOCATION_GATE=1 (:367)
```
