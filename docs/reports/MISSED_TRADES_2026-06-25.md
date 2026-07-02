# ניתוח עסקאות-שלא-בוצעו · 2026-06-25 (EOD · Cowork autonomous)

**שער-זמן:** רץ ב-**15:27 CT** (אחרי סגירת RTH 15:00, `TZ=America/Chicago`) ✓. ריצה אוטונומית — Michael לא נוכח. **לא שונה קוד.**

> 🔴🔴 **ממצא-העל — מוות-feed אמצע-RTH @09:40 CT (I-45). ~82% מ-RTH ללא-נתונים (320/390 דק' · 63/~78 ברים) ⇒ "הפספוסים" אינם gate-blocked, הם חושך.**
> שני מקורות-הברים קפאו-יחד על הבר **09:40 CT** (14:40 UTC): `woodies/chart` `export_ts=09:41:33 CT`, `age_s≈20,600` (**5.73h stale**), `stale:true`;
> `chart/bars5min` בר-אחרון `2026-06-25 17:40+03:00` = **09:40 CT** זהה. `readiness.bridge_streams_fresh=false` → **`dead: cumulative_delta,volume_profile,imbalance,bars_5min`**.
> **`live_price` המשיך לתקתק** (7451→7446.5→7447.25 בין-קריאות) ⇒ **מסווה את הקפיאה** (זהה לתסמין שתועד הבוקר ב-memory `export_tmp_promotion_freeze`).
> ⇒ מ-**09:40→15:00 CT (5h20m)** המערכת **עיוורת**: אין ברים, אין סטאדיז, אין detection, אין fires, אין exits, אין missed-logging. **ירי-בודד היום: id245 תקוע FILLED.**
> זהו **המשך-הקפיאה של הבוקר שלא-נפתרה** (10:41 ET diagnose → לא-התאושש עד-סגירה), **לא** אירוע-חדש.

**הקשר (החלון-החי-היחיד, 08:30→09:40 CT, 15 ברי-woodies; woodies≡bars5min מסכימים):**
פתיחה ~7470 → **דרייב-ירידה-פתיחה חד 7469→LOW 7390 (08:55, −79 נק' ב-25 דק')** (cci צלל ל-**−307** @08:40, trend GRAY→RED רק @08:55 בתחתית) →
**V-reversal-מעלה חד 7390→7467.75 (09:30, +77 נק')** (cci −180→+55, tcci התהפך −104→**+141**, trend RED→GRAY @09:20) → 09:35 C7463 → **09:40 FREEZE** (בר-חלקי C7447.25).
`live_price` בעת-האודיט **7447.25** (ת'מחיר זרם; הברים לא). **day_type=Normal** (סווג @09:00 CT לפני-הקפיאה — באג-ה-UNKNOWN-כל-סשן **לא-חזר**). `trend_state` תקוע **GRAY** מ-09:40.

## מקורות-אמת + כיסוי (הצלבה ל-CC) — **מקור-CCI = Sierra**

| endpoint | כיסוי (CT) | הערה |
|---|---|---|
| `/api/v9/woodies/chart?limit=80` | **05:35→09:40 (50 ברים); RTH 08:30→09:40 = 15 ברים** | מקור-אמת CCI = Sierra (`sierra_woodies_5min_json` v9.4.5-wc-fix). 🔴 **`stale:true`, `age_s≈20,600` (5.73h), `studies_stale:true`.** בר-אחרון 09:40 CT. ⚠️ **חריג-לטובה:** הפעם יש woodies-CCI **לבוקר** (08:30→09:40) — בניגוד לימים-קודמים שעיוורים <11:15 — אבל **רק** עד-הקפיאה. |
| `/api/v9/chart/bars5min?limit=80` | **בר-אחרון 09:40 CT** (`2026-06-25 17:40+03:00`) | 🔴 **קפוא זהה ל-woodies @09:40.** 🟢 **מסכים-woodies בבוקר** (09:30 C7460.5 · 09:35 C7463 בשניהם) ⇒ **אין source-split (I-40 מכונס).** |
| `/api/v9/trades/recent?limit=100` | **היום: 1 (id245)** | `limit=200`→**422** (cap=100, I-25). **n_today=1.** id245 REACTIVE_LONG `state=FILLED` (פתוח). **gap-id 244 חסר** (I-32 נמשך). מיון יורד (245→132); כיסוי-מלא-עד-06-16. |
| `/api/v9/build/pattern-status` | live post-close | ⚠️ **הנתיב בקובץ-המשימה `/build_status/pattern-status` נותן 404**; הנתיב-החי = `/build/pattern-status`. `session_date=2026-06-25` · `verdict=DEGRADED` (`trend_state=GRAY`) · `errors=[]` · fired_today **S2=1/S4=0** (תואם-DB). bridge `fresh:false`; **S2/S4 `fresh:true`** (lag 20,847≫threshold 660 — **I-46 דגל-משקר**). |
| `/api/v9/missed-trades` | **ריק (count=0)** | אין buffer-artifact היום (≠06-16/18/19/22). `v9_missed_trades` לא-מאוכלסת ⇒ אין candidate-list. |

## טבלת setups — **רק החלון-החי 08:30→09:40 CT** (rolling-6-bar · stop-first replay)
entry=close/swing-בר-האות · stop=swing±0.5 · T1=1R · replay על OHLC-חי **עד-הקפיאה בלבד**. **09:40→15:00 = אין-נתונים ⇒ לא-ניתן-לזהות/לשחזר.**

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop(risk) | T1/T2 | R-נגד (replay חלקי) | gate-שחסם / מה-קרה | I-# |
|---|---|---|---|---|---|---|---|---|---|
| **08:30–08:55** | **דרייב-ירידה-פתיחה (initiative-SHORT)** | S2/S4 | ⚠️ `hfe=Y` @08:30/08:50/08:55 (HFE-DOWN, observability) | ~7464 (שבירת 08:35 L) | ~7491 (27, מעל 08:30 H) | 7437 / 7410 | **≈+2R (מחלוקת)** (08:55 L**7390**=MFE **+2.7R**; lows ירדו ⇒ לא-stopped) | **לא-נותב:** (1) **`HFE_DISABLED=1`** (HFE=lifetime-#1-loser, מ-06-24) ⇒ HFE-DOWN לא-יורה-בעיצוב; (2) **trend תקוע GRAY עד-08:55** (התהפך RED **בתחתית** 7390) ⇒ שער-trend-S4 לא-אישר עד-תום-המהלך; (3) **opening-lag** (day_type סווג רק @09:00). ⇒ **דילוג-מבני/בעיצוב, לא חסם-gate נקי.** | HFE_DISABLED · I-1/I-36 (opening) |
| **08:55–09:30** | **V-reversal LONG** | S2 | ✅ **ירה id245** (אך מאוחר) | id245 **7460.5** (09:35) | 7443.5 (17) | 7469 / 7494.5 | **late-slippage ≈+1R** (entry-אידאלי 09:00–09:05 ~7427–7445 = benchmark slot-2; ירה 09:35 @7460.5 = **~25–33 נק' מאוחר**) | **נתפס-לא-פוספס, אך מאוחר-ב-~30דק'.** ה-reversal הוכר; הכניסה איחרה את ה-V-bottom. | I-26 (timing) |
| 08:55–09:30 (replay id245) | — | S2 | ✅ FILLED | 7460.5 | 7443.5 (17) | 7469 / 7494.5 | **לא-הוכרע** (09:35 H7465.5/L7452.25 · 09:40 H7464/L7458 — לא T1 ולא stop) → **FREEZE** | 🔴 **תקוע FILLED ~6h** (sub-I-45): אין ברים אחרי-09:40 לפתור T1/T2/stop. ב-SHADOW=זיהום; **ב-LIVE=פוזיציה-עיוורת ללא-stop-mgmt.** | **I-45 (orphan)** |
| **09:40→15:00** | **כל setup אחר (incl. benchmark slot-5 10:00 SHORT)** | — | ⚫ **אין-נתונים** | — | — | — | **לא-ניתן-לכמת** | 🔴🔴 **feed מת (I-45)** — ~82% מ-RTH חשוך. שום setup-אחה"צ לא-ניתן לזהות או לשחזר. | **I-45** |

**ΣR-נגד (פספוס-אמת, חלון-חי 08:30→09:40) ≈ +2R (מחלוקת)** — שולט: דרייב-הירידה-הפתיחה (−79 נק' ל-7390, MFE +2.7R) שלא-נותב (HFE-DOWN-disabled + trend-GRAY-עד-התחתית).
ה-reversal-LONG **נתפס** (id245) אך **מאוחר ~30דק'** (≈+1R late-slippage). **שאר-היום (09:40→15:00, ~82% מ-RTH) — לא-ניתן-לכמת מחמת קפיאת-ה-feed.**
⇒ **"הפספוס" המהותי היום אינו setup-חסום-gate — הוא הסשן-החשוך כולו.** השאלה הנכונה לא "כמה setups פוספסו" אלא **"למה ה-feed מת ולמה זה לא-צף חי"**.

## 🟢 הסיפור-האמיתי — ירי-בודד + פוזיציה-יתומה (ground-truth מ-`v9_trades`)
**ירי-RTH יחיד היום: id245.** המערכת ירתה פעם-אחת (09:35, 5 דק' לפני-הקפיאה) ואז התעוורה.

| זמן(CT) | id | תבנית | מע' | dir | entry | risk | stop | T1/T2 | state | $ | הערה |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 09:35 | 245 | REACTIVE_LONG (grp NO_SETUP) | S2 | LONG | 7460.5 | 17 | 7443.5 | 7469 / 7494.5 | **FILLED (פתוח)** | **0** (לא-נסגר) | **with-reversal LONG** תקין-בכיוון, אך מאוחר ל-V-bottom · `day_type=Normal` · `wtrend=GRAY` · `blocked_by=null` · `mode=shadow` · `sizing=2` (לא-ניתן-לאמת sizing→PnL כי pnl=0, I-34). **תקוע FILLED ~6h (I-45/sub).** |

**פילוח:** 1 ירי, 0 סגירות, $0 ממומש. **אין W/L** (הפוזיציה-היחידה פתוחה). זו **לא** עסקה-מפסידה — היא **עסקה-לא-מנוהלת** עקב מוות-ה-feed. **I-34 (sizing) לא-נבדק היום** (id245 לא-נסגר). **I-31 🟢** (fired S2=1/S4=0 תואם-DB-בדיוק, אך n=1 ⇒ מבחן-חלש). **I-32** נמשך (244 חסר).

## 🎯 BENCHMARK — 5 הסלוטים של Michael (06-05 יום-יורד) מול היום
היום בוקר = **דרייב-ירידה-פתיחה→V-reversal-מעלה** (מעורב), ו-**אחה"צ חשוך** ⇒ התאמה-חלקית-בלבד + אי-יכולת-הערכה לסלוט-5.

| # | סלוט(CT) | סוג(benchmark) | מה קרה היום | ירה? | הערה |
|---|---|---|---|---|---|
| 1 | 8:35 | REVERSAL (S2/FHB) | 08:35 = **אמצע-דרייב-ירידה** (עוד יורד ל-7390); reversal-אמיתי רק 08:55–09:00 | ❌ אין-ירי | **דילוג-נכון** — 08:35 אינו נקודת-היפוך (עוד-יורד). |
| 2 | 9:00–9:05 | **LONG טקטי** | **bounce חד מ-7390** (09:00 C7427.75 · 09:05 C7444.75) | ⚠️ id245 LONG **@09:35** | ✅ **כיוון-תואם (LONG)** — היום הסלוט-היחיד-שתואם-מבנית; אך ירה **מאוחר ~30דק'** (7460.5 מול ~7427 אידאלי). |
| 3 | 9:20 | SHORT | 09:20 = **אמצע-bounce-מעלה** (7446, cci+6) | ❌ short יהיה-שגוי | מבנה-הפוך: 09:20 = עלייה, לא ירידה. |
| 4 | 9:35 | SHORT | 09:35 = עולה (7463) | ❌ (ירה LONG id245) | benchmark=SHORT, היום=LONG-נכון. אי-התאמה-כיוונית-מבנית. |
| 5 | 10:00 | SHORT | **⚫ אחרי-הקפיאה — אין-נתונים** | ⚫ לא-ניתן-להעריך | feed מת @09:40 ⇒ 10:00 חשוך. |

**שורת-benchmark: K/5 = 1/5 סלוטים ראו-ירי (slot-2 LONG, כיוון-נכון, מאוחר ~30דק').** slots 1/3/4 ללא-ירי (1 דילוג-נכון + 2 אי-התאמה-מבנית down-day-מול-up-bounce); **slot-5 חשוך (לא-ניתן-להעריך).**
ה-benchmark הוא template-יום-יורד; היום הבוקר היה down-drive→up-reversal ⇒ התאמה-חלקית, וה-**אי-וודאות העיקרית היא קפיאת-ה-feed, לא ה-detector.**

## פירוק לפי gate
| gate | #setups | סטטוס |
|---|---|---|
| **🔴🔴 feed-death (I-45)** | **כל 09:40→15:00 (~82% RTH)** | **החוסם-המוביל-המוחלט.** לא gate-לוגי — מוות-נתונים. שני-מקורות קפאו @09:40; bridge `fresh:false`; 1 ירי תקוע. שורש טרם-מאומת-Mac (`.tmp`-fresh / `.json`-stale promotion-freeze, memory). D34. |
| **🔴 orphaned-open (sub-I-45)** | id245 | פוזיציה FILLED ~6h ללא-סגירה. חסר **feed-loss-flatten + EOD-reconcile**. ב-LIVE = פוזיציה-עיוורת. D35 (→Michael). |
| **🟡 freshness-lie (I-46)** | S2/S4 badge | `fresh:true` post-close למרות lag 20,847≫660; bridge נכון-`false`. מותנה-`in_session` ⇒ **מסווה-stall**. הפרד `data_current` מ-`fresh_for_trading`. D36. |
| **HFE_DISABLED (by-design)** | דרייב-ירידה-פתיחה | HFE-DOWN לא-נותב (lifetime-#1-loser, 06-24). דילוג-בעיצוב. |
| **trend-GRAY-עד-תחתית + opening-lag (I-1/I-36)** | דרייב-ירידה-פתיחה | trend אישר RED רק @08:55 (בתחתית 7390) ⇒ short-trend-following לא-תוקף עד-תום-המהלך. |
| **late-timing (I-26)** | reversal-LONG (id245) | נתפס אך מאוחר ~30דק' ל-V-bottom (~+1R slippage). |
| **source-split (I-40)** | 0 | 🟢 **מכונס** — woodies≡bars5min בבוקר. |
| **missed-endpoint artifact** | 0 (count=0) | 🟢 ריק. |
| **sizing (I-34)** | id245 | ⏸️ **לא-נבדק** — id245 לא-נסגר (pnl=0). נשאר חוסם-LIVE. |

### תוקנו/השתפרו מול פתוחים (זווית-הפספוסים)
- **🔴🔴 I-45 (feed-death @09:40) — המנוף-המוביל-המוחלט.** ~82% מ-RTH חשוך; ההמשך-של-קפיאת-הבוקר (10:41 ET) שלא-התאוששה. **אומת-API (Rule 2).** שורש דורש-Mac: `ls -la ~/SierraChart_Data/v9_export/*.json{,.tmp}` (mtime/last-ts), `tail /tmp/bridge.err.log`, `launchctl list | grep com.mems26.bridge`, `psql … MAX(ts) v9_bars_5min_woodies`. **דרוש watchdog feed-silence in-session.** D34.
- **🔴 orphaned id245 (sub-I-45) — חוסם-LIVE-קריטי.** פוזיציה פתוחה ~6h ללא-stop-management. **דרוש flatten-on-feed-loss + EOD-reconcile** לפני-LIVE. D35 → Michael.
- **🟡 I-46 (freshness-lie) — silent-failure.** ה-badge הירוק-השקרי הוא **בדיוק** מה שמונע מהקפיאה לצוף חי. הפרדת `data_current`/`fresh_for_trading`. D36.
- **🟢 I-40 (source-split) — מכונס** (woodies≡bars5min בבוקר). **🟢 missed-endpoint ריק.** **🟢 day_type לא-UNKNOWN** (סווג Normal @09:00 לפני-הקפיאה).
- **🟢 I-41 (הטיה-כיוונית) — n/a היום** (ירי-בודד; אי-אפשר-להעריך איזון). **🟡 I-32** נמשך (244 חסר). **🟡 I-25** (limit 200→422→cap 100).
- **⏸️ D30/D31/D32 (06-24: cvd-fix / day-type-unify / S4-reversal-bleed) — לא-נבדקו** (feed מת ⇒ 0 S4-fires). **אל-תסמן closed בלי replay** (Rule 5) — ממתינים ליום-feed-תקין.
- **⚪ הערת-מערכת:** גייטי-chop **מושבתים** (standing 2026-06-08: S2 `choppiness_ok` + Layer-0). **אין המלצה להפעיל מחדש** — החלטת-Michael בלבד. תצפית-בלבד. **לא שונה קוד.**

## נטיפיקציה ל-Michael
**🔴🔴 יום-חשוך: ה-feed מת @09:40 CT (I-45) — ~82% מ-RTH ללא-נתונים.** שני-מקורות-הברים (bars5min+woodies) קפאו-יחד על בר-09:40; `export_ts=09:41:33 CT`, **5.73h stale**; bridge `fresh:false` (`dead: bars_5min,cvd,volume_profile,imbalance`).
**`live_price` המשיך לתקתק (מסווה את הקפיאה)** — בדיוק ה-silent-staleness שתועד הבוקר (promotion `.tmp`→`.json` נעצר 10:41 ET, לא-התאושש).
**ירי-בודד היום: id245 (S2 REACTIVE_LONG, 09:35, e7460.5) — תקוע FILLED ~6h ללא-סגירה (sub-I-45; ב-LIVE=פוזיציה-עיוורת).**
**setups פוספסו:** בחלון-החי-היחיד (08:30→09:40) — **1 דילוג-מבני** (דרייב-ירידה-פתיחה ל-7390, HFE-disabled+trend-GRAY-עד-תחתית) + **1 late-fire** (reversal-LONG נתפס-מאוחר ~30דק'). **כל 09:40→15:00 לא-ניתן-לכמת (חשוך).**
**ΣR-נגד(חלון-חי) ≈ +2R (מחלוקת)** · **החוסם-המוביל = I-45 (feed-death), לא gate-לוגי** · **benchmark: K/5 = 1/5** (slot-2 LONG מאוחר; slot-5 חשוך).
**🟠 דגלי-CC (קדימויות):** (1) **I-45 שורש-Mac** + **watchdog feed-silence in-session**; (2) **flatten-on-feed-loss + EOD-reconcile** ל-id245-class (sub-I-45, חוסם-LIVE); (3) **I-46** הפרד freshness display/gate (silent-failure). גייט-chop מושבת (standing, **לא-להפעיל**). **לא שונה קוד.**

---
*נוצר אוטונומית ע"י Cowork (15:27 CT, 2026-06-25). מקור-CCI מאומת מ-Sierra (`sierra_woodies_5min_json` v9.4.5-wc-fix) — אך **`stale:true age_s≈20,600`**. timestamps אומתו-בקוד: woodies-ts=**UTC** (14:40 UTC=09:40 CT), bars5min-ts=**+03:00** (17:40+03=09:40 CT), export_ts=1782398493=09:41:33 CT. trades n_today=1 (id245 FILLED). missed-endpoint count=0. אין source-split (I-40 מכונס). replay=OHLC-חי stop-first עד-הקפיאה. משלים את ה-EOD-consolidation שתיעד I-45/I-46. **לא שונה קוד.***
