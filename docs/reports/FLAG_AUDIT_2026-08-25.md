# ביקורת-אמת של 204 הדגלים הפסוקים — 2026-08-25

מקור: `config/RULED_FLAGS.yaml` (204 דגלים) · `.env` (580 שורות) · קוד-ייצור · `/tmp/backend.err.log` (22-25.08) · Postgres `mems26`.
backend PID 64102, עלה 15:58:14. `flag_guard`: **0 סטיות** בין `.env` ל-`expected` — כלומר השאלה איננה "האם הדגל דלוק" אלא "האם הוא עושה משהו".

**מקרא:** ✅ מבצע · ⚠️ חלקי (רץ, לא מגיע לתא) · ❌ מת (מחלקה 1-5 + file:line) · ❓ לא-נבדק (לא הופעל)

**מחלקות-הכשל:** 1=מקור-מת · 2=צרכן-מת · 3=ענף בלתי-נגיש · 4=חריגה נבלעת · 5=נקרא ולא שוער

---

## סיכום מספרי

| | דגלים דלוקים (174) | דגלים כבויים (30) |
|---|---|---|
| ✅ מבצע | **84** | 29 (כבויים כהלכה) |
| ⚠️ חלקי | **41** | — |
| ❌ מת | **18** | 1 (`LOCAL_ALERTS_V1` — ברירת-מחדל-בקוד ON, כובה ידנית) |
| ❓ לא-נבדק | **31** | — |

### 🔴 המספר שמייקל חיכה לו: **59 מתוך 174 הדגלים הדלוקים אינם מבצעים את מה שנפסק** (18 מתים לגמרי + 41 חלקיים). רק 84 (48%) מוכחים כעובדים.

---

## 1 · שער-המסחר — `backend/v9/gateway/trading_gateway.py` (44 דגלים)

| דגל | .env | מה אמור לעשות | file:line | מבצע? | ראיה | פער-פיתוח |
|---|---|---|---|---|---|---|
| CHASE_MIN_SESSION_BARS | 8 | מינימום ברי-סשן לפני מבחן-הרדיפה | `trading_gateway.py:2082` | ✅ | לוג 08-24 17:00 `SESSION-MATURITY bypass: 7 bars < 8` — ברירת-מחדל 6 לא הייתה עוקפת | — |
| COLD_START_GUARD_V1 | 1 | אין ירי עד שמאגר-הברים מלא אחרי ריסטארט | `trading_gateway.py:960-992` | ❓ | 0 hits `grep -ci cold_start`; מסלול-PASS שקט | אין שורת-PASS — אי-אפשר להוכיח כניסה לענף |
| CONFLUENCE_RI_ZLR_LIVE | 1 | ניתוב תבנית-קונפלואנס ללייב במקום צל | `trading_gateway.py:3436` | ❓ | 0 שורות ניתוב; `_confluence_fixed` (`:921`) מעולם לא True ב-4 ימים | — |
| CONT_TREND_FILTER | 1 | תבניות-CONT רק עם מגמה מתמשכת | `trading_gateway.py:1673-1749` | ✅ | 2 חסימות `ZLR (CONT) setup UP vs sustained DOWN` | עיוור ל-`S2_DELTA_DBL_*` (family=None) — ראה §שורש-א |
| DAYTYPE_LOCATION_GATE | 1 | דעיכת-REV רק בקצה-הערך הנכון | `trading_gateway.py:1551`·`location_gate.py:163-227` | ⚠️ | 0 חסימות ב-4 ימים; `location_gate.py:180-181` מאשר לכל family≠REV; 105/108 מהחסימות = S2_DELTA_DBL | לא מגיע לתא REV — REVים מתים קודם בפלייבוק `:1192` |
| DAYTYPE_PLAYBOOK | 1 | וטו לתאי SKIP של תבנית×סוג-יום | `trading_gateway.py:1192` | ✅ | 8 חסימות `BLOCKED by day-type playbook: FAMIR SKIP on Variation` | ל-`daytype_playbook.yaml` 0 שורות delta |
| DIRECTION_CONTEXT | 1 | חסימת ירי נגד CVD+פריצה חיים | `trading_gateway.py:1662` | ✅ | 31 חסימות (26 `setup DOWN vs UP`, 5 הפוך) | — |
| EARLY_ATR_FLOOR_V1 | 1 | רצפת-ATR מוקדמת מ-ATR של אתמול | `trading_gateway.py:2478-2501` | ⚠️ | 0 שורות `FIX-8 ATR floor` | `:2463` מגביל מקור ל-`LIMIT 12` ⇒ מבחן `<14` ב-`:2479` **תמיד אמת** — לא מוגבל-לפתיחה בכלל |
| ENTRY_BUDGET_QUALITY_V1 | 1 | סלוט-תקציב נוסף למועמד conf גבוה | `trading_gateway.py:1991` | ❌ **מחלקה 3** | הורה `DAYTYPE_ENTRY_BUDGET_V1=0` (`.env:253`) עוטף הכל ב-`trading_gateway.py:1943`; 0 שורות entry-budget | פסיקת 21.08 החיה לא מיושמת באף מסלול פעיל |
| ENTRY_BUDGET_SKIP_LOSERS_V1 | 1 | עסקה ≤−1R לא צורכת מכסה | `trading_gateway.py:1972` | ❌ **מחלקה 3** | אותו הורה `:1943` / `.env:253` | כנ"ל |
| ENTRY_CONFIRM_TOL_MIN_PTS | 0.5 | רצפה לסובלנות בר-האישור | `trading_gateway.py:3112` | ✅ | 08-24 20:40 `no bearish confirm bar (c=7668.0 >= o=7667.0 + tol=0.5)` | הערך == ברירת-המחדל בקוד ⇒ שורת-ה-.env לא משנה |
| EOD_RISK_WINDOW_V1 | 1 | אין כניסות 45 דק' לפני 15:00 CT | `trading_gateway.py:995` | ✅ | 08-24 22:35 `BLOCKED by EOD entry cutoff: 25 min before close` | — |
| EXTREME_CHASE_GUARD_V1 | 1 | חסימת כניסה שרודפת קצה-סשן | `trading_gateway.py:2029` | ✅ | 3 שורות `extreme-chase-guard SESSION-MATURITY bypass` (הקוד רץ) | 0 חסימות בפועל; רואה רק ZLR/GB100/INITIATIVE |
| EXTREME_CHASE_SCOPE | CONT | הגבלת השומר ל-CONT | `trading_gateway.py:2037-2040` | ✅ | נקרא ל-`_ecg_in_scope`, השומר רץ | `"CONT"` **הוא** ברירת-המחדל ⇒ אפס דלתא |
| LEG_EXEMPT_LSMA_FLAT_V1 | 1 | פטור מ-lsma-flat כשיש רגל-חיה מסכימה | `trading_gateway.py:1925-1926` | ❓ | 2 חסימות lsma_flat קרו (בלי פטור); אין שורת-לוג כשהפטור **כן** חל | פטור שקט = בלתי-ניתן-לאימות מהלוג |
| LEG_RIDE_V1 | 1 | זיהוי רגל-חיה + פטור משערי-יום | `trading_gateway.py:112-139` | ✅ | 82 שורות `LEG_RIDE: live UP leg (age 5) agrees with LONG` | — |
| LIVE_EXECUTION_V1 | 1 | שליחת פקודות סיירה אמיתיות | `trading_gateway.py:4209` | ✅ | 0 שורות stub; 5 `LIVE fire BLOCKED pre-send` (`:4294`, במורד הזרם) | — |
| LSMA_FLAT_ATR_V1 | 1 | סף-שיטוח יחסי-ל-ATR | `trading_gateway.py:1890-1909` | ✅ | 08-24 18:25 סף `0.2243` מול קבוע `0.2500` ב-17:35 | — |
| LSMA_FLAT_GATE_V1 | 1 | חסימה כש-LSMA אופקי מדי | `trading_gateway.py:1882` | ✅ | 2 חסימות `BLOCKED by lsma-flat gate … scope=ALL` | — |
| NEUTRAL_RESPONSIVE_V1 | 1 | פטור דעיכות-REV מ-direction-context ברוטציה | `trading_gateway.py:1765-1794` | ⚠️ | 0 שורות `EXEMPT (neutral-responsive)`; כל 31 החסימות = S2_DELTA_DBL ⇒ family None≠"REV" | לא מגיע לתא (שורש-א) |
| **TREND_LEG_CHASE_EXEMPT_V1** | 1 | ביטול-שלילת-פטור לכניסות-מגמה עם-רגל | `trading_gateway.py:2120-2138` | ❌ **מחלקה 4 + 3** | `:2124` קורא `.get("day_type")` על **מחרוזת** מ-`get_live_day_type()` (`trade_context.py:565`) ⇒ AttributeError נבלע ב-`:2137-2138`. ובנוסף הצרכן היחיד `:2148` דורש `EXTREME_CHASE_TIP_REVOKE_V1` שלא קיים ב-.env | תיקון ה-`.get()` לבדו לא ישנה כלום — הזוג צריך פסיקה משותפת |
| NORMAL_ROTATION_FIX_V1 | 1 | הוספת "Normal" לרשימות ימי-רוטציה | `trading_gateway.py:1785`·`stop_resolver.py:80` | ⚠️ | `[StopResolver] IB floor 9.71pt > ATR floor 3.17pt` ב-69/69 — `STOP_FLOOR_IB_V1` גובר תמיד; אתר-הגייטוויי 0 הפעלות | ההרחבה 0.5→0.8 נבלעת ע"י רצפת-IB |
| PATTERN_STOP_COOLDOWN_V1 | 1 | חסימת כניסה חוזרת ≤30דק' אחרי סטופ | `trading_gateway.py:2233`→`:217-253` | ❓ | מקור חי (52 שורות `stop_hit_ts`), אך `max(stop_hit_ts)=2026-08-21 22:52` — אפס סטופים בחלון; כל 13 העסקאות `mode='shadow'` שהשאילתה מסננת | יום-צל לא יכול להפעיל אותו |
| RELEASE_LEG_EXEMPT_V1 | 1 | פטור משער-שחרור כשהכניסה מסכימה עם הרגל | `trading_gateway.py:2328-2336` | ✅ | `release-gate LEG EXEMPT` ×69 (61 SHORT / 8 LONG) 08-24 | — |
| REQUIRE_WITH_TREND_DAY_DIRECTION_V1 | 1 | הזנת day_direction לפלייבוק במקום trend_state | `trading_gateway.py:1231`·`daytype_playbook.py:71,196` | ⚠️ | מקור-עדיפות-1 מת: `get_live_expansion()` קורא `backend.v9.app` (**מחלקה 1**, `trade_context.py:878`) ⇒ תמיד None | להפוך `S1_DAY_DIRECTION_V1` מ-shadow ל-1 |
| RESPONSIVE_WITH_DAY_TREND_V1 | 1 | fallback ל-dir_bias מ-LSMA | `trading_gateway.py:1250-1257`·`daytype_playbook.py:216` | ✅ | `trend_state` 6 אחרונים RED⇒DOWN; 08-24 130 RED/119 BLUE; 0 כשלים | **הספק היחיד החי** של day_direction — נקודת-כשל-יחידה |
| REV_EDGE_DAY_STRUCTURE_V1 | 1 | דעיכת-REV בקצה יום/IB עם probe | `location_gate.py:205`·`trading_gateway.py:1581` | ❓ | 0 שורות location-gate ב-4 ימים; REVים נחסמו קודם בפלייבוק (`:1192` רץ לפני `:1551`) | סדר-השערים מסתיר את שער-המיקום |
| RISK_DAILY_LOSS_CAP | 800 | סף-עצירה ב-$ | `trading_gateway.py:3339` | ⚠️ | נקרא, אבל 3 אתרי-קריאה עם 3 ברירות-מחדל שונות (450 / 400 ב-`mobile_monitor.py:345`) | לאחד |
| RISK_HALT_V1 | 1 | עצירת-יום כש-P&L ≤ −cap | `trading_gateway.py:3337-3350` | ⚠️ | `self._daily_pnl += pnl` יושב בתוך `if self.live_slot…` (`:3730-3736`); demo/shadow לא מעדכנים; הידרציה `WHERE mode='live'` (`:624`). 08-24 הפסיד **−$1,491 בצל** מול תקרת $800 ⇒ 0 עצירות | ההערה ב-`:3331` טוענת "Enforced in ALL modes" — סתירה. חלון-דמו ייתן ירוק-כוזב |
| RR_ENTRY_GATE_V1 | 1 | חסימה כש-T1 קרוב מ-stop×rr_min | `trading_gateway.py:3128` | ✅ | `blocked_by=rr_entry_gate` ×52 | — |
| S4_ENTRY_CONFIRM_V1 | 1 | דרישת בר-אישור בכיוון | `trading_gateway.py:3097-3121` | ✅ | 08-24 20:40 `BLOCKED by entry-confirm: no bearish confirm bar` | — |
| STEP_SCALED_LADDER_V1 | 1 | סטופ+יעדים לפי מדרגה-חציונית | `trading_gateway.py:2914-2976` | ✅ | `StepLadder … median_step=9.75 → stop=…` ×68 | — |
| STOP_RESOLVER_V1 | 1 | סטופ מבני במקום סטופ-ממומן | `trading_gateway.py:2453-2572` | ⚠️ | שרד **1 מ-69**: `STOP ARBITRATION: STEP_SCALED_LADDER OVERRODE StopResolver` ×68; `no valid rung in band → rejected` ×61 | שני כותבים לאותו סטופ — להכריע בעלות |
| STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1 | 1 | וטו יעדים בצד-הלא-נכון + רצפת R:R | `trading_gateway.py:2673`·`:3163` | ✅ | `blocked_by=structural_targets_wrong_side` ×1, `BLOCKED rr_hard_floor` ×2 | — |
| T1_STRUCTURE_END_V1 | 1 | שמירת T1 המבני מפני דריסת C1/מדף | `trading_gateway.py:2756-2764`·`:2820-2828` | ✅ | `T1_STRUCTURE_END: keeping structural t1=7651.46` ×108 | אתר 2 (`:2827`) 0 hits |
| T2T3_NO_STOMP_V1 | 1 | שמירת t2/t3 מבניים מול R-multiples | `trading_gateway.py:2833-2841` | ✅ | `PATTERN_T1_OVERRIDE … (no-stomp: structural t2/t3 preserved)` ×4 | — |
| TARGET_STRUCTURE_CLAMP_V1 | 1 | מהדק יעדים מעבר-ל-IB לקצה-IB | `trading_gateway.py:3009` | ✅ | `[TargetClamp] TP-1 applied … t1 7685.25 → IB-edge 7682.75` ×66 | — |
| TARGET_ZONES_V1 | 1 | חידוד t2/t3 למדפי-קונפלואנס | `trading_gateway.py:2852-2893` | ✅ | `TARGET_ZONES_V1: t2 7678.5 → 7692.25 (shelf strength 3)` ×2 | תדירות נמוכה |
| TREND_STEP_STRUCT_EXEMPT_V1 | 1 | פטור רגלי-TREND_STEP מווטו-A1 | `trading_gateway.py:2704` | ✅ | 08-24 19:30 `TREND_STEP_STRUCT_EXEMPT: A1 … SKIPPED` | — |
| VARIATION_WITH_TREND_CONT_V1 | 1 | המשך עם-מגמה ביום-Variation כיווני | `daytype_playbook.py:259`·`trading_gateway.py:1303` | ❓ | צנרת תקינה, אך 0 hits לשלוש התוצאות; `variation_phase` מעולם לא EXPANSION | `VARIATION_PHASE_STALL_BARS=6` אולי מחמיר מדי |
| EXCESS_COUNTER_ENTRY_V1 | 1 | פטור דעיכות-EXCESS ב-Variation EXPANSION | `daytype_playbook.py:283-323` | ❓ | רץ רק בתוך ענף `:274` שלא נפתח אף פעם | תלוי לגמרי ב-VARIATION_WITH_TREND_CONT_V1 |
| NEVERFADE_TREND_ONLY_V1 | 1 | הגבלת "לעולם-אל-תדעך" לימי-Trend בלבד | `daytype_playbook.py:227-232` | ✅ | מציב `_wt_on=False` ב-Variation — בדיוק מה שניתב את ההחלטה שנצפתה | הוא גם ה**תנאי-המקדים** לענף VARIATION_WITH_TREND_CONT (`:257`) — צימוד לא-מתועד |
| RELEASE_ENTRY_GATE_V1 | 1 | החזקת כניסה עד יציאה מהאזור-הדביק | `release_gate.py:49`·gw `:2293-2348` | ⚠️ | `blocked_by=awaiting_release` ×85; **`release-gate PASSED` = 0** ב-4 ימים | יחס 85/0 = וטו-דה-פקטו; קריטריון-השחרור אולי בלתי-נגיש |
| RELEASE_TREND_BYPASS_PTS | 12 | עקיפת ההחזקה כשהסשן זז ≥12 נק' | `release_gate.py:191-216`·gw `:2337` | ❌ **מחלקה 3** `trading_gateway.py:2332-2337` | 0 `TREND BYPASS` למרות ש-08-24 היו **45 ברים עם \|disp\|≥12**; כל הערכה נכנסה ל-`if` הקודם (`LEG EXEMPT` ×69) והבייפס הוא ה-`elif` | שינוי הערך לא היה משנה אף פסק |

## 2 · S2 / חמש-דקות / פתיחה (28 דגלים)

| דגל | .env | מה אמור לעשות | file:line | מבצע? | ראיה | פער-פיתוח |
|---|---|---|---|---|---|---|
| OPENING_ANCHOR_ET_V1 | 1 | עיגון חלון-הפתיחה ל-09:30 ET | `five_min_system.py:1518-1521` | ✅ | בר-פתיחה נאסף 08-25, החזקה נרשמה 16:35:03 IL = 09:35 ET | ET≡IL באוגוסט ⇒ אין דלתא עד שעון-חורף |
| OPENING_DIR_FUSION_V1 | 1 | שער-כיוון מאושר-נפח על כניסות-פתיחה | `five_min_system.py:1494,1631` | ⚠️ | 5 דחיות, כולן `(fusion=None)`; `opening_vol 114585 < median 114590` | וטו-שמיכה; פער-נפח של 5 יחידות |
| OPENING_ENTRY_V1 | 1 | הרצת מנוע-טריגר-הפתיחה | `five_min_system.py:1481-1482` | ✅ | הלוגים הפנימיים קיימים רק בתוך הבלוק | — |
| OPENING_FIRE_V1 | 1 | חלון 30→60 דק' + PULLBACK-CONT | `five_min_system.py:1489-1490` | ✅ | טריגרים הוערכו ב-17:10-17:25 IL = ברים 9-12 | — |
| OPENING_FIRST_TRADE_STRICT_V1 | 1 | עסקת-פתיחה ראשונה: conf≥0.6 + בר-אישור | `five_min_system.py:1641`·`opening_entry.py:419` | ⚠️ **וטו-100%** | 7/7 החזקות, **כולן** `opening confidence 0.0 < 0.6` — מקור-ה-conf מת (שורש-ב) | חוסם כל עסקת-פתיחה, תמיד |
| RR_MIN_ROTATION | 0.65 | ריכוך רצפת-RR ל-0.65 ברוטציה | `trading_gateway.py:704` (+2) | ✅ | `structure exhausted ahead (3.00pt < 0.65×risk 15.00)` ×39 | בשני אתרים 0.65 הוא גם ברירת-המחדל |
| S2_ADAPTIVE_THRESHOLDS_V1 | 1 | רצפת-התפשטות יחסית + ירידת-נפח יחסית | `five_min_system.py:1155-1166` / `:919` מת | ⚠️ | INITIATIVE מוכח (`b1_exp=1 b1_range=4.2 exp=[5.9,11.4]`); זרוע REACTIVE היא `elif` אחרי `if S2_VSA_VOLUME:` ו-`.env:28 S2_VSA_VOLUME=1` | להוציא את זרוע-b2 מהצל |
| S2_CVD_DETECTION_V1 | shadow | אישור-CVD על ירי-S2 | `five_min_system.py:1001,1070,1215,1244` | ⚠️ | 6,910 שורות `[S2-CVD] … delta_read=`, **0** `rejected` (`_cvd_mode != "shadow"`) | תצפית בלבד לפי הפסיקה |
| S2_DETECTION_LIVE_DAYTYPE_V1 | 1 | זיהוי קורא סוג-יום חי | `five_min_system.py:1796-1801` | ✅ | הערך שוער ב-`:1806`, `:1852/1864`, `:2397` | — |
| S2_INITIATIVE_JOIN_ATR_CAP_V1 | 1 | תקרת דרישת-join ב-0.55×ATR | `five_min_system.py:1172-1183` | ✅ | חושב מ-`[S2-DL] exp=[5.9,11.4]` ⇒ תקרה ≈2.5 < `_join_req` 4.2 ⇒ כובל | הלוג ב-DEBUG — לא נראה ב-INFO |
| S2_REACTIVE_DAYTYPE_V1 | 1 | כיול נפח+גיאומטריה פר-סוג-יום | `five_min_system.py:955,1037` (`:925` מת) | ⚠️ | בלוק ה-`volume:` מוצל ע"י `S2_VSA_VOLUME=1`; ל-`context.ease_mult` ו-`geometry.b2_range_max_atr` **אפס קוראים** | 3 מ-5 כפתורי-ה-YAML אינרטיים |
| S2_REACTIVE_EDGE_FIX_V1 | 1 | תיקון POC-הפוך + דחיית COT/AMT בסייזינג-הישן | `five_min_system.py:1306` | ❌ **מחלקה 3** (`five_min_system.py:2232`) | `calculate_size()` רץ רק כש-`v2_sizing_result is None`; לוג: 13 FIRE / 13 `V2 sizing:` / **0** SKIP / 0 failed | המסלול-הישן בלתי-נגיש כל עוד `STOP_ANCHORS_V2=1` |
| SIZE_CAP_CUT_V1 | 1 | חיתוך גודל כשהסיכון עובר תקרת-ATR | `sizing.py:135-157` | ✅ | 33 שורות `SIZE_CAP_CUT: risk 9.0pt > cap 3.8pt → contracts 3→2` | — |
| STOP_WINDOW_COMPLETED_V1 | 1 | חלון-סטופ על ברים גמורים בלבד | `five_min_system.py:2034-2037` | ✅ | `[FiveMin] V2 cap_exceeded: family=OFA/Reactive` מוכיח מסלול `if cfg:` | — |
| STRUCTURAL_STOP_ORIGIN_V1 | 1 | עיגון סטופ על קיצון-סווינג b1..b3 | `five_min_system.py:1992-1994` | ❌ **מחלקה 5** | הצרכנים היחידים של `structural_anchor` (`:2047` else, `:2067`, `:2074`) לא נגישים: Reactive=`support_zone/4`, OFA=`breakout_bar/1` ⇒ שניהם לוקחים את ענף-החלון ב-`:2014` | no-op מלא תחת `STOP_ANCHORS_V2=1` |
| T1_BANK_R | 1.5 | T1 = 1.5×risk כשהמבנה מוצה | `woodies_system.py:1058` (+2) | ✅ | 08-25 16:37 ZLR SHORT: entry 7695.50, risk 15 ⇒ T1 7673.00 = 1.5R בדיוק | טקסט-הלוג עדיין אומר "T1=1R" |
| AUTH_LOWCONF_REDUCED_V1 | 1 | SKIP של Auth-Table → REDUCED-2 | `setup_emitter.py:149,171` | ✅ | 3 SKIPים 08-24 לקחו את ה-`else` ב-`:180` נכון (conf 0.58, IB נעול) | ההיפוך לא נצפה בחלון |
| DAYTYPE_HONEST_PRELOCK_V1 | 1 | תווית טרום-נעילה מורידה וטו לייעוץ | `setup_emitter.py:167-171` / gw `:1440` מת | ⚠️ | זרוע-הגייטוויי היא `elif` אחרי `if not _pb_conf_ok`; DB: שלבים A2/A3 `max(confidence)=0.35`, **0 שורות ≥0.4** ⇒ ענף-ה-conf תמיד גובר | ל-`or` במקום `elif` |
| DOUBLE_TOP_ADAM_FIX_V1 | 1 | חלון 30→32 + סובלנות-שיא 2 טיקים | `double_bt.py:35,71` | ✅ | `DOUBLE_TOP_AA_SHORT` נפלט 08-24 19:40 | `SEARCH_WINDOW` נקרא ב-import — דורש ריסטארט |
| TREND_STEP_ENTRY_V1 | shadow | זיהוי מדרגות, ניתוב דרך השערים, בלי סלוט | `trend_step/detector.py:47,54` | ✅ | `[TrendStep] CANDIDATE SHORT @7669.50` 08-24; `shadow_only` נשמר ב-`trading_gateway.py:3508` | — |
| TREND_STEP_STAIR_OR_V1 | 1 | גרם-מדרגות מאומת מחליף מבחן-קצה-סשן | `trend_step/detector.py:61,184` | ❓ | מועמד יחיד ב-4 ימים; `reason` נבנה ללא-תנאי ב-`:268` ⇒ אי-אפשר לייחס | להוסיף `stair`/`session_ext` ל-reason |
| OPENING_CONF_ENGINE_FUSE_V1 | 1 | ציון-מנוע גובר על ציון-גלאי ≈0 | `opening_entry.py:406-409` | ❌ **מחלקה 3** | השומר הוא `conf >= 0.5`, וכל conf שנצפה = `0.0`; 0 שורות `CONF_FUSE` | סותר את ה-docstring — נבנה בדיוק כדי להציל conf=0.0 |
| OPENING_OR_ATR_SCALE_V1 | 1 | תקרת-OR = max(10, 0.25×ATR-יומי) | `opening_entry.py:159-163` | ⚠️ | ATR-14 יומי נמדד **38.44 נק'** ⇒ 0.25× = 9.61 < רצפת 10.0 ⇒ `max()` מחזיר את הישן | אינרטי אריתמטית; דרוש ATR>40 |
| OPENING_PLAYBOOK_V1 | 1 | פטור OPENING_* מ-awaiting_release/lsma_flat | `trading_gateway.py:97-107` | ❓ | חיווט תקין, אך 0 שורות `OPENING_*` ב-4 ימים (נחסם במעלה ע"י וטו-ה-conf) | — |
| OPENING_RUNNER_RIDE_V1 | 1 | טריילינג מבני לראנר של עסקת-פתיחה | `opening_runner.py:27` | ❌ **מחלקה 2** | grep רפו-רחב ל-`opening_runner`: רק טסט, שני `_INDEX.md` ו-`FLAG_REGISTRY.yaml`. **אפס מייבאים בייצור** | לחווט או להוציא-לגמלאות |
| OPENING_DALTON_GAPS_V1 | 1 | ציר-מאזן (B1) · ביטול-drive (B2) · התראת AUCTION_OUT (B3) | `opening_detector_v2.py:28,106,139,191` | ⚠️ | רק B2 יכול לשנות פסק; `balance_state`/`balance_conviction`/`invalidated` נכתבים ואיש לא קורא (הצרכנים קוראים רק `opening_type`) | B1/B3 = צרכן-מת |
| OPENING_WINDOW_FIRE_V1 | 1 | עקיפת סירובי-סוג-יום ב-30 הדק' הראשונות | `opening_type_gate.py:261,305` | ❓ | אתרי-הקריאה נגישים, אך כל הסירובים היו **מחוץ** ל-08:30-09:00 CT | — |
| **OPENING_WINDOWS_V1** | 1 | (לכאורה) חלונות-פתיחה מדורגים + מיקום-drive | `opening_windows.py:19` — **docstring בלבד** | ❌ **מחלקה 2** | `grep -n "getenv\|environ" opening_windows.py` → **ריק**. הצרכן היחיד `evaluate_drive_location` מיובא ב-`trading_gateway.py:1130` בתוך `if OPENING_DRIVE_EXHAUSTION_VETO_V1` = `.env:481 → 0` | דגל-רפאים: לא קיים בשום קוד |

## 3 · סוג-יום / כיוון / הקשר (31 דגלים)

| דגל | .env | מה אמור לעשות | file:line | מבצע? | ראיה | פער-פיתוח |
|---|---|---|---|---|---|---|
| S1_ACCEPTANCE_RECLASS_V1 | 1 | שבירה מאושרת מסווגת-מחדש מיד | `daytype_classifier.py:255-298` | ❓ | 0 מ-26 שורות-reason מכילות "reclass" | דרוש יום עם שבירת PDH/PDL מאושרת-נפח |
| S1_COMMITTED_PROVISIONAL_V1 | 1 | @30דק' לקבע סוג-יום זמני | `daytype_classifier.py:307-311` | ❌ **מחלקה 3** | יושב תחת `n < ib_lock_bars(12)`, אך הקורא החי `main.py:390` דורש `ib_locked` **וגם** `:467 len(bars)>=12` ⇒ n≥12 תמיד. 0 שורות "@30m provisional" | המקדם-החי לא יכול לקרוא לפני נעילת-IB |
| S1_CONFIDENCE_V2 | 1 | ביטחון קנוני יחיד בכל פלט | `daytype_classifier.py:239-240` | ✅ | DB 08-24: 0.25/0.50/0.67/0.75/1.00 = צורות k/8 ו-k/3 | — |
| S1_CONF_SMOOTH_V1 | 1 | הגבלת קצב-שינוי ל-0.25/בר | `daytype_classifier.py:171-182` | ✅ | DB 08-24 מכיל 0.42/0.58/0.63/0.92 — בלתי-אפשרי מ-`_confidence` | — |
| S1_DD_INVALIDATION_V1 | 1 | צוואר שהתמלא ⇒ ביטול תווית Trend_DD | `daytype_classifier.py:400-402` | ❓ | 0 שורות Trend_DD אי-פעם; 08-24 `profile_shape='b'` | — |
| S1_NEUTRAL_PRECEDENCE_V1 | 1 | sides==2 גובר על אישור חד-צדדי | `daytype_classifier.py:228,255` | ❓ | 08-24 sides 0→1; 0 reasons דו-צדדיים בכל הטבלה | — |
| S1_NONCONVICTION_V1 | 1 | שם ליום אפס-OTF ⇒ לעמוד בצד | `daytype_classifier.py:321-329` | ❌ **מחלקה 3** | `main.py:528-537` `_DT_MAP` חסר "Nonconviction" ⇒ `_new_dt=None`; המפרסם `main.py:552` דורש `NONCONVICTION_ACTIVE_V1` שאינו ב-.env | התווית מיוצרת ונזרקת |
| S1_RECLASS_REQUIRES_IB_EXT_V1 | 1 | סיווג-מחדש פוסט-נעילה דורש הרחבת-IB | `daytype_classifier.py:268-277` | ❓ | מקונן בתוך בלוק-ה-reclass שלא ירה (0/26) | — |
| S1_TREND_CONTROL_V1 | 1 | מדרגות מקדמות ל-Trend בלי rib≥2.5 | `daytype_classifier.py:434-473` | ⚠️ | הבלוק הוערך (הזרימה הגיעה ל-`:498`), אך rib 1.0631 < סף 1.8 | הרצפה לא נענתה ביום היחיד בחלון |
| S1_TREND_ELONGATION_V1 | 1 | rib≥2.5 + סגירה בקצה ⇒ Trend | `daytype_classifier.py:481-494` | ⚠️ | rib 1.0631 < 2.5; 0 שורות elongation-path אי-פעם | — |
| S1_VALUE_MIGRATION_V1 | 1 | וטו Trend כשהערך עדיין חופף לאתמול | `daytype_classifier.py:444-447` | ⚠️ | `_vm_veto` מחושב ונקרא **רק** בתוך `:463` שמעולם לא עבר | וטו מקונן תחת תא שלא נפתח |
| DAYTYPE_SIDES_MECHANICAL_V1 | 1 | ספירת-צדדים מכנית ולא לפי-נפח | `relative_features.py:262,306` | ✅ | `:306` דורס ללא-תנאי; `sides=1` שפורסם 08-24 הוא הערך הזה | — |
| IB_BREAK_ANY_EXPANSION_V1 | 1 | רצפת-רעש → 0.5 נק' | `relative_features.py:268-274` | ✅ **הפך פסק** | 08-24: דלוק ⇒ sides=1 ⇒ **Variation**; כבוי ⇒ רצפה 5.55 ⇒ sides=0 ⇒ **Normal** | — |
| S1_IB_SANITY_V1 | 1 | fallback ל-IB-מברים כשסיירה מעופש | `classifier_core.py:82-92` | ⚠️ | 08-24 IB סיירה == IB-ברים בדיוק ⇒ אין מה לתפוס | הבדיקה רצה, לא הופעלה |
| DAYTYPE_RTH_RESET_V1 | 1 | השלכת תווית טרום-RTH בפתיחה | `state_machine.py:326-335` | ✅ | 08-25 16:30:11 `FIX-9 RTH-boundary reset: dropping carried pre-RTH state` | — |
| DAYTYPE_ANTIFLAP_V1 | 1 | שינוי-תווית חייב להחזיק 600ש' | `trade_context.py:622-625` | ✅ **משנה פסקים** | 08-24: הטבלה ב-14:10 UTC=Variation אך עסקה #778 הוחתמה Trend_Normal; ב-14:30 הפוך | `_ANTIFLAP_STATE:487` בלי איפוס-סשן ⇒ `raw is None → return stable` (`:502`) מדליף תווית של אתמול |
| OPENING_TYPE_SEEDS_S1_V1 | 1 | זריעת כיוון-יום מסוג-הפתיחה ב-15 הדק' | `trade_context.py:993-1046` | ⚠️ | `seed=DOWN` ×12 מול `seed=None` ×661; הצרכן הוא שכבה-3 מאחורי `get_live_dir_bias` שכמעט תמיד עונה | הערך אמיתי, הסלוט תפוס |
| S1_DAY_DIRECTION_V1 | shadow | קריאת `last_cls_result` מהאפליקציה החיה | `trade_context.py:868-878,926` | ⚠️ (**מסלול-ההחזרה מחלקה 1**) | `_shadow` ⇒ `backend.v9.app` (`:878`) בעוד הכותב היחיד הוא `backend.main:674`. `expansion=None` ב-**673/673** שורות System0 | להפוך ל-`1` — זה כל התיקון |
| S1_NEW_CLASSIFIER | 1 | תווית 7-סוגים מחתימה וגם משערת | `trade_context.py:675-683` | ✅ | `v9_trades.day_type_at_entry` 08-24 = Trend_Normal / Normal / Variation | — |
| BOOT_DAYTYPE_REPLAY_V1 | 1 | ריפליי ברי-RTH של היום בעלייה | `main.py:852-912` | ⚠️ | נכנס בכל 5 העליות, אך כולן `boot-replay: no RTH bars yet` (כולן טרום-פתיחה) | ריסטארט אמצע-סשן לא נבחן |
| BOOT_HYDRATION_V1 | 1 | שחזור מוני-P&L יומיים בעלייה | `main.py:1291-1298` | ✅ | 08-25 15:58:15 `[Boot-Verify] HYDRATION \| daily_pnl=$0.00 \| source=v9_trades` | — |
| DAYTYPE_ACCEPTANCE_DEMOTION_V1 | 1 | Trend→Variation אחרי K ברים בתוך IB | `main.py:682-715` | ✅ | 08-24 17:10:01 `ACCEPTANCE-DEMOTION: Trend_Normal → Normal_Variation (K=3 …)` | — |
| DAYTYPE_BOOT_SEED_CANONICAL_V1 | 1 | זריעת תווית קנונית בעלייה | `main.py:919-956` | ❓ | מקונן במסלול-ההצלחה של boot-replay שחזר ב-`:869-870` בכל 5 העליות | חסום ע"י ההורה, לא ע"י עצמו |
| DAYTYPE_RECLASS_STABILITY_V1 | 1 | שינוי-תווית חייב לחזור N=2 ברים | `main.py:570-602` | ✅ | 08-24 17:30 `held … (pending Normal 1/2)` → 17:35 `promoted` | — |
| CONT_TREND_STATE_CERT_V1 | 1 | BLUE/RED + שיפוע מאשרים את הצד | `direction_context_live.py:201,213,265` | ✅ | 08-25 16:39:40 `FIX-7 CERT: lsma_side +1→-1 (RED + slope=-0.5800)` | — |
| DAYTYPE_ONE_SOURCE_V1 | 1 | שערים קוראים מהמכונה החיה ולא מהטבלה | `direction_context_live.py:152-157` | ⚠️ | `get_live_day_type()` החזיר None בכל קריאה היום ⇒ נפילה לטבלה: 5× `v9_day_type_state STALE (1615s ago)` | "מקור אחד" מתדרדר לשניים בדיוק כשהתווית UNKNOWN |
| LSMA_SUSTAIN_BARS | 2 | K ברים בצד-LSMA אחד = מגמה מתמשכת | `direction_context_live.py:241` | ✅ | אותה שורת-CERT מדפיסה `RED×2` | — |
| DAYTYPE_PATTERN_AWARE_V1 | 1 | CONT נחסם בימים מאוזנים, REV בימי-מגמה | `daytype_position_gate.py:105` | ❌ **מחלקה 3** | `.env DAYTYPE_POSITION_GATE=0` (שורת-boot של env_loader מאשרת); `decide()` חוזר ב-`:93-94` לפני `:105`; וגם `trading_gateway.py:1634` לא נכנס | שתי הריגות עצמאיות |
| DIRECTION_COMPASS_V1 | 1 | מצפן-מאוחד חוסם סטאפים נגד-כיוון | `direction_compass.py:393-409`·gw `:1826-1839` | ⚠️ | השער נגיש (מאות חסימות בשערים מאוחרים יותר), אך **0** `BLOCKED by direction-compass` ו-0 שורות `[Compass]` | `_compass_or` ב-`:1702/:1754` מזריק את המצפן ל-cont_trend_filter ול-direction_context **בלי לוג** — עלול לשנות פסקים בהיחבא |
| DELTA_FEATURES_V1 | 1 | פיצ'רי-דלתא ברדאר + וטו הרחבה לא-מגובה | `context_radar.py:197-215` | ⚠️ (**מחלקה 5 בקובץ זה**) | `/radar` תצוגתי; הצרכן-המשער `daytype_classifier.py:283` דורש `delta_confirms_ext is False`, אך היצוא החי מכיל **4 נקודות** ו-`delta_features.py:47,66` מחזירים None מתחת ל-5 | `cumulative_delta.json` מורעב |
| MARKET_CONTEXT_V1 | 1 | חשיפת balance_state/acceptance של System-0 | `context_radar.py:220-232` | ❌ **מחלקה 1** | `balance_state` נגזר רק מ-`_current.opening_type` שנקרא מ-`app.state.opening_type_result` (`market_context.py:112`) — **אפס כותבים בייצור**; ריצה: `balance=UNKNOWN` ב-**673/673** שורות System0 | וגם `acceptance` (`market_context.py:34`) לעולם לא מוצב ⇒ תמיד "pending" |

## 4 · ביצוע / מנהל-עסקאות / רקונסיילר (36 דגלים)

| דגל | .env | מה אמור לעשות | file:line | מבצע? | ראיה | פער-פיתוח |
|---|---|---|---|---|---|---|
| **SCALE_IN_V1** | 1 | חיזוק מנצח בחוזים נוספים | `bar_level_detector.py:1285` | ❌ **מחלקה 4** | `V9Trade` (`db/models/trades.py:13`) מגדיר `stop` (`:27`) — **`stop_price` לא קיים** (grep exit=1). `trade.stop_price` ⇒ AttributeError שאינו ב-`except (TypeError, ValueError)` (`:1287`), נבלע ב-`:815-816`. נוסף 2026-08-23 (`2e9a92c5a`); הילדים האחרונים #770/#775 היו 08-21 | `trade.stop` + להוסיף AttributeError ל-except |
| **SCALE_IN_P3_V1** | 1 | ריווח ATR/R + סטופ-ממוצע + איסור-קצה | `bar_level_detector.py:1285` | ❌ **מחלקה 4** | אותה שורה, נזרקת לפני `should_scale_in()` — P3 מעולם לא הוערך | אותו תיקון |
| PROTECTED_QTY_GUARD_V1 | 1 | התראה כשהסטופים לא מכסים את הכמות | `sierra_position_reconciler.py:818` | ⚠️ | הקורא היחיד בתוך `if tm_qty == sierra_qty:`; היום TM=0/סיירה=−3 ⇒ לא נקרא במשך 1:46 שעות DESYNC חי | לקרוא גם בענף-הסטייה — שם הסיכון הכי גבוה |
| MANUAL_GUARD_AUTOPROTECT_V1 | 1 | הנחת סטופ מבני על פוזיציה ידנית עירומה | `sierra_position_reconciler.py:1024` | ⚠️ | היום 02:02-08:18 על 1c עירום אמיתי: `🛡️ AUTOPROTECT[NO_RECOMMENDATION:avg missing]` ×5 | 9.5 שעות עירום עם שומר דרוך. fallback ל-`last_price`/יומן-אירועים |
| POSITION_TRUTH_SYNC_V1 | 1 | מעקב אחרי הפוזיציה הנקייה של סיירה | `fill_poller.py:238` | ⚠️ | עובד (4 עסקאות `exit_reason='SIERRA_FLAT'`), אך **9,231** `POSITION_TRUTH sync errored … invalid transaction is rolled back` ב-08-23 = עיוור סשן שלם | `ensure_clean` (`:164`) רץ רק ב-except החיצוני |
| ORDER_REJECT_DETECT_V1 | 1 | קורלציה דחיית-ברוקר → CANCELLED | `fill_poller.py:600` | ⚠️ | היום 10:11/12:44/13:32 `FIX-10 ORDER_REJECT seen (Insufficient Account Value (NLV)) but no PENDING demo/live trade to correlate` | דחיות בלי בעלים — להעלות כאנומליה |
| MANUAL_POSITION_GUARD_V1 | 1 | CRITICAL+push על פוזיציה ידנית עירומה | `sierra_position_reconciler.py:251` | ✅ | היום 08:18:00 `🔴 MANUAL POSITION NAKED: 1c with NO working stop for 34125s` | — |
| RECONCILER_OWNERSHIP_AWARE_V1 | 1 | פוזיציה ידנית ≠ אורפן ⇒ INFO ולא CRITICAL | `sierra_position_reconciler.py:947` | ✅ | היום 16:48:32 `ℹ️ 🔴 DESYNC: Sierra -3c, no open system trade → ANOMALY` (נגיש רק כשהדגל דלוק) | — |
| PHANTOM_HEAL_V1 | 1 | סגירת עסקת-רפאים כשסיירה שטוחה | `sierra_position_reconciler.py:835` | ✅ | 11 שורות `exit_reason='phantom_reconcile'` (כותב יחיד `:843`) | — |
| SIERRA_RECONCILER_V1 | 1 | רקונסיילר TM↔סיירה כל 30ש' | `fill_poller.py:576` | ✅ | `[Reconciler] SYS-3` כל 10 דק' עד 16:48:32 היום | — |
| EXIT_TRACK_ACTIVITY_V1 | 1 | סגירה דרך יומן CLOSED_TRADE_PNL | `fill_poller.py:361` | ✅ | היום 15:18:29 `W2 CLOSED_TRADE_PNL seen (1 events)` | — |
| SYSTEM6_SUPERVISOR | 1 | 9 אינווריאנטים פר-בר | `bar_level_detector.py:77` | ✅ | OPS_LOG 08-21: `[system6] eod_open_position ALERT` | — |
| SYSTEM6_JOURNAL_AUTOLOOP_V1 | 1 | יומן 8 אותות-יציאה פר-בר | `bar_level_detector.py:294` | ✅ | `v9_exit_decisions` 7,234 שורות, כולן `decided_by='auto_loop'` | — |
| TARGET_REALISM_V1 | 1 | מהדק יעד לא-ריאלי לתקרת-הסשן | `manager.py:962`·gw `:3040` | ✅ | היום 16:55:56 `FIX16 realism: trade 789 t2 7671.00 → 7688.50`; 137 שורות | — |
| BE_AFTER_REAL_T1_V1 | 1 | מיפוי DLL T1→T0 בסולם-4 | `manager.py:559` | ✅ | 19,797 שורות `T0_HIT`; `target=="T0"` קיים רק דרך המיפוי | — |
| T0_TARGET_PTS | 3.0 | לקיחה ראשונה מהירה ב-±3.0 | `sierra_command.py:856`·`manager.py:404` | ✅ | 142 עסקאות נושאות `quality.has_t0`/`t0_target_pts` | `v9_trades.t4` NULL ב-**680/680** — הרגל הרביעית בלתי-נראית ל-DB |
| STOP_STRUCTURE_TRAIL_V1 | 1 | סטופ פוסט-T1 למבנה הקרוב, לא BE | `manager.py:798` | ✅ | 81 שורות `reason='structure-trail after T1'`, אחרונה 08-25 | — |
| STOP_PERBAR_STRUCT_V1 | 1 | בדיקת עוגן-חלון בכל בר פוסט-T1 | `manager.py:913` | ✅ | 90 שורות `STRUCT_TRAIL` עם `source='window_anchor_fix15'` | — |
| ZLR_MGMT_V1 | 1 | ZLR: סטופ קבוע → BE ב-T1 | `manager.py:92`·`sierra_command.py:768` | ✅ | 61 שורות `SMART_BE {"zlr":true}`, אחרונה 08-25 | — |
| SIZE_CAP_OVER_FIXED_V1 | 1 | חיתוך-גודל שורד את FIXED_CONTRACTS | `sierra_command.py:692` | ✅ | 16:50:18 `SIZE_CAP_CUT: 3→2` **וגם** עסקה #789 `quality.contracts=2` | — |
| FIXED_CONTRACTS_3 | 1 | כל ירי = 3 חוזים | `contract_size.py:72` | ✅ | `ruled_contracts()`=3; #790 (16:55:03) contracts=3 | קדימות `_6>_5>_4>_2>_3` — הדלקת דגל גבוה מייתרת בשקט |
| MARGIN_AWARE_SIZING_V1 | 1 | לא לשלוח פקודה שהחשבון לא נושא | `margin_sizing.py:39` | ✅ | 08-24 ×7 `MARGIN SIZING 6 → 4 … $817.41 usable cannot carry 6×$386.20` | — |
| PHONE_ALERTS_V1 | 1 | דחיפת התראות CRITICAL לפלאפון | `phone_alert.py:33` | ✅ | `push()` הופעל 5× היום; Pushover validate `{"status":1,"devices":["iphone"]}`; 0 כשלים ב-4 ימים | 🔴 `LOCAL_ALERTS_V1=0` (`.env:408`) ⇒ Pushover הוא **הערוץ היחיד** |
| CANDIDATE_LEDGER_V1 | 1 | כתיבת DETECTED/EMIT_DECISION | `candidate_ledger.py:51` | ✅ | `gateway_decisions.jsonl` היום: 7 DETECTED + 5 EMIT_DECISION | — |
| LIVE_LEDGER_V1 | 1 | הגשת הליגר ממקור-סיירה | `live_ledger_routes.py:27` | ✅ | `curl /api/v9/live_ledger` → `{"enabled":true,"source":"trade_fills.json",…}` | — |
| FEED_WATCHDOG | 1 | HALT כשהברים הקנוניים קפואים | `feed_watchdog.py:96`→gw `:1019` | ✅ | **925** החלטות `blocked_by="feed_watchdog"` בארכיון | — |
| NEWS_BLACKOUT_V1 | 1 | חסימת כניסות סביב אירועים אדומים | `news_blackout.py:102`→gw `:2368` | ✅ | החלטה אחת `blocked_by="news_blackout"`; רענון-לוח 15:58:16 | — |
| EOD_FLATTEN_V1 | 1 | CANCEL לפתוחות demo/live בסגירה | `bar_level_detector.py:585` | ❓ | הגיע לשער 15:59 ET ב-08-24 (2,988 דיספאצ'ים) אך `active` ריק | דרושה עסקה חיה עד 16:00 ET |
| EOD_CLOSE_T10_V1 | 1 | FLATTEN ב-15:50 ET | `bar_level_detector.py:541` | ❓ | `live_active` ריק בכל בר בחלון | — |
| C4_TREND_FLATTEN_V1 | 1 | שיטוח ראנרים ביום-Trend ב-15:45 ET | `bar_level_detector.py:626` | ❓ | אין עסקאות demo/live; **אין** באג `.get()`-על-מחרוזת כאן — `:642` משתמש ב-`.startswith` נכון | — |
| RECONCILE_LIVE_V1 | 1 | רקונסיילר סלוט↔DB↔סיירה פר-בר | `bar_level_detector.py:681` | ❓ | 0 שורות `[Reconcile-live]`; הגייטוויי מחווט אך הסלוטים ריקים | — |
| STOP_RETRY_ON_NONE_V1 | 1 | שליחה-חוזרת של MODIFY_STOP | `fill_poller.py:917` | ❓ | `grep -c MODIFY_STOP_NONE` → **0** | — |
| RUNNER_TRAIL_V2 | 1 | רגל-ראנר stop-only + טרייל-סווינג | `manager.py:1072`·`sierra_command.py:924` | ❓ 🔴 | פעולת `SWING_TRAIL`: **0 שורות** ב-`v9_trade_management_log` (כל-הזמנים); 0 שורות `F5 RUNNER_TRAIL_V2` | הודלק 08-20 ולא הפיק שום ארטיפקט. `manager.py:1074` מחזיר False לכל ZLR — ורוב הירי הוא S4/ZLR |
| C4_RULING6_V1 | 1 | פתרון t4 פר-סוג-יום כשרגל-T3 None | `sierra_command.py:877` | ❓ | דורש `contracts>=4`; היום `ruled_contracts()=3` ⇒ בלוק-T0 (`:859`) מדולג | בלתי-נגיש בהגדרה תחת FIXED_CONTRACTS_3 |
| EXIT_VERIFY_V1 | 1 | הספרים נסגרים רק כשסיירה מוכיחה flat | `exit_verifier.py:44` | ❓ | `verify_pending()` נקרא בכל מחזור; 0 שורות `[ExitVerify]` — אין יציאה מ-08-21. הקוד נבדק, לא נמצא פגם | — |
| MANUAL_FLATTEN_V1 | 1 | שער ל-FLATTEN החירום מהפלאפון | `mobile_monitor.py:423` | ❓ | הנקודה לא נקראה. השער אפקטיבי כאן (`MOBILE_REMOTE_URL` ריק) | ⚠️ במכונה עם `MOBILE_REMOTE_URL` מוגדר, ה-forward חוזר ב-`:420` **לפני** בדיקת-הדגל |

## 5 · סטופים / יעדים / סייזינג / סיכון / קליטה (35 דגלים)

| דגל | .env | מה אמור לעשות | file:line | מבצע? | ראיה | פער-פיתוח |
|---|---|---|---|---|---|---|
| STOP_FLOOR_IB_V1 | 1 | רצפת-סטופ ל-35% מ-IB | `stop_resolver.py:92-102` | ✅ | 51 שורות `IB floor 9.71pt (35% of IB 27.75) > ATR floor 4.12pt` | — |
| STOP_FLOOR_ROTATION_ATR | 0.8 | רצפת-ATR רחבה יותר ברוטציה | `stop_resolver.py:80-87` | ✅ | 08-24 20:40 `ATR floor 3.27pt` (ATR 4.083 × 0.8) | — |
| STOP_WIDEN_TO_STRUCTURE_V1 | 1 | קבלת סטופ מבני מעל-התקרה במקום דחייה | `stop_resolver.py:137-148` | ✅ | 7× `WIDEN-TO-STRUCTURE`, **0×** `no_stop_in_band` | הסטופ נדרס במורד ×68 |
| S2_AUTH_MATRIX_SINGLE_SOURCE_V1 | 1 | הפלייבוק = סמכות יחידה לתבנית×יום | `sizing.py:84-85` | ⚠️ | 0× `[V2Sizing] no auth cell` ב-43 קריאות כולל ZLR/GB100/FAMIR (שאינם במטריצה) ⇒ הענף עוקף | 85 תאי-פסק ב-`auth_matrix.yaml` בלתי-נגישים |
| SIZE_CAP_FLOOR_CONTRACTS | 2 | חיתוך לא ירד מתחת ל-2 | `sizing.py:143-157` | ✅ | 08-24 22:00 `SIZE_CAP_CUT: 6→2 (floor=2)` — בלי רצפה היה 1 | — |
| PATTERN_RISK_CAPS | 1 | תקרת-סיכון פר-תבנית ⇒ SKIP/SIZE_DOWN | `woodies_system.py:884-986` | ❌ **מחלקה 3** (מוצל ע"י `:853-864`) | 26× `STOP_STRUCTURE_EXTREME cap-clamp … exceeds cap 15.0pt` (הטריגר קרה) מול **0×** `RISK_CAP_SIZE_DOWN`/`RISK_CAP_SKIP`/`GIANT_BAR_STOP` | ה-clamp ב-`:853` רץ לפני חישוב `_s4_risk` ב-`:874` ⇒ `_s4_risk > _rc_max` ב-`:927/:938` תמיד False. הורג גם PATTERN_LOSS_BREAKER + GIANT_BAR_STOP + פאזה-3 של SIZING_CONSOLIDATION |
| S4_HONEST_DAYTYPE_FALLBACK_V1 | 1 | ויתור על קריאת-טבלה מתה + סינתזת "Normal" | `woodies_system.py:700-718` | ❓ | כובל רק אם 3 מקורות קודמים נכשלים; התווית החיה הייתה קיימת | להוסיף שורת-לוג של המקור המנצח |
| S4_OVERRIDE_AWARE_V1 | 1 | S4 מכבד DAY_TYPE_MANUAL_OVERRIDE | `woodies_system.py:675-680` | ⚠️ | `DAY_TYPE_MANUAL_OVERRIDE` לא מוגדר ב-.env ⇒ תא-העקיפה לא נגיש | מטרת-הדגל לא נבחנה חי |
| SIZING_CONSOLIDATION_V1 | 1 | V2 מנצח; דחיות תקרת-סיכון כ-blocked_by | `woodies_system.py:631,1287`·gw `:3383-3400` | ⚠️ | פאזה-2 חיה; 0× `blocked_by=s4_risk_cap`/`pattern_loss_breaker` | היצרן היחיד של פאזה-3 הוא PATTERN_RISK_CAPS המת |
| STOP_ANCHORS_V2 | 1 | צנרת עוגן/סייזינג V2 ל-S4 | `woodies_system.py:722` +7 מודולים | ✅ | 28× `[Woodies] V2 sizing: ZLR/GB100/FAMIR/VEGAS contracts=…` | — |
| STOP_STRUCTURE_EXTREME_V1 | 1 | סטופ מאחורי קיצון-מבנה 12 ברים | `woodies_system.py:828-876,1309` | ✅ | 33× `STOP_STRUCTURE_EXTREME: ZLR SHORT stop 7680.00→7688.25` | ה-cap-clamp שלו הורג את PATTERN_RISK_CAPS |
| MEMS_MIN_RISK_POINTS | 2 | דחיית/הרמת סטופים מנוונים | `pre_fire_validator.py:73`·`atr_stop.py:215` | ⚠️ | ATR חי 3.8-4.6 ⇒ רצפת-הרצועה `0.5×ATR` ≥2.04 כבר עוברת את 2.0 | תוצאות שלב-A7 לא מגיעות ל-backend.err.log |
| MEMS_MAX_RISK_POINTS | 60 | דחיית סטופים מוגזמים | `pre_fire_validator.py:74,79` | ❓ | סיכון מקסימלי שנצפה 31.25 נק' | 60 ≈ פי-2 מכל מה שהמערכת מייצרת — תקרה חסרת-משמעות |
| S4_GRAY_RELABEL_CCI | 100 | GRAY→BLUE/RED ב-±100 | `trend_relabel.py:42-47` | ❌ **מחלקה 3** | `.env:332 S4_GRAY_RELABEL_V1=0` ⇒ הסף לא נקרא כלל | פרמטר-פסוק שההורה שלו כבוי |
| TARGET_MIN_SPACING_V1 | shadow | מדידת סולם-מרווח (בלי להחיל) | `target_spacing.py:88-95` | ✅ | `[TargetSpacing] SHADOW would-be: t1..t3 = 7679.50/7682.75/— (min_gap=2.8875pt)` | — |
| EXTREMES_AWARE_REALIZE_V1 | 1 | EXCESS⇒מימוש-מיידי, POOR⇒דיכוי | `target_approach_realize.py:112` | ❌ **מחלקה 3** (`:60-61`) | `.env:472 S6_TARGET_APPROACH_REALIZE_V1=0` ⇒ `should_realize()` חוזר 50 שורות לפני | תיקון-K5 (`bar_level_detector.py:895`) מזין פונקציה שיוצאת קודם |
| S6_MAE_SCRATCH_V1 | 1 | FLATTEN טרום-T1 כש-MAE ≥ סף | `mae_scratch.py:229` | ❓ | רץ רק `if _is_demo_live` (`bar_level_detector.py:1017`); 0 עסקאות live מאז 08-21 | — |
| S6_MAE_SCRATCH_ATR_V1 | 1 | סף יחסי-ל-ATR `max(k×ATR14, 4.0)` | `mae_scratch.py:101-130,246-269` | ❓ בריצה — **הקוד תואם את הפסיקה במדויק** | yaml: `default_k 1.3333`=8/6, `ZLR 1.0`=6/6, `GB100 1.6667`, `INIT_LONG 2.6667`=16/6, `floor_pts 4.0`; `stop_gap_mode: skip` + `:261-267 return (False,"")` ⇒ מהדק-P2-9 **הפך ל-SKIP** | חסום באותו היעדר-עסקה-חיה |
| SYSTEM6_AUTOCORRECT | protective | רק תיקונים מקטיני-סיכון | `system6_supervisor.py:296` | ✅ (מפרש) / ❓ לא-הופעל | grep ממצה של `"op":` במפקח: MODIFY_STOP ×3, DROP_TARGET ×1, MODIFY_TARGET ×2 — **אין op=EXIT** | ⚠️ סחף-תיעוד: הסט כולל היום גם `MODIFY_TARGET` (`:275-280` **לא-משוער**) — CLAUDE.md אומר "רק MODIFY_STOP + DROP_TARGET" |
| SYSTEM6_EXIT_SIGNALS | 1 | הערכת 8 אותות יציאה/החזקה | `system6_exit_signals.py:340` | ✅ | `v9_exit_decisions` 7,234 שורות / 8 סוגי-אות | רדום מאז העסקה החיה האחרונה |
| SYSTEM6_EXIT_JOURNAL | 1 | שימור אות+תוצאה ללמידה | `system6_journal.py:41` | ✅ | 08-21: 800 שורות, 60 `fired`, 232 `outcome_helped` | — |
| RR_BREAKOUT_MM_V1 | 1 | הצלת R:R של t2-מהודק דרך מכפיל-ספק | `pre_fire_validator.py:97-115` | ✅ | 08-24 19:20 `RR_BREAKOUT_MM: capped-t2 R:R 0.51 rescued (risk=31.25 mm_reward=46.88)` ×2 | — |
| STOP_ANCHOR_OFFSET_TICKS_OVERRIDE | 16 | היסט-עוגן 16T במקום 6T מה-yaml | `config_loader.py:382-388` | ✅ | `STOP_STRUCTURE_EXTREME … (structure 7682.75 **+16T** over 12 bars)` | — |
| PROBE_REJECT_MIN_PTS | 0.0 | ריכוך מרחק-הדחייה של probe | `location_gate.py:75` | ⚠️ | הקורא היחיד `:210` בתוך ענף `REV_EDGE_DAY_STRUCTURE_V1`; ה-probe הראשי ב-`:28-53` לא קורא env בכלל | הכיול חל רק על ענף-הצד |
| S7_SHADOW_LOG_V1 | 1 | לוג ציון-S7 על כל fire | `s7_shadow.py:32` | ✅ | `v9_s7_shadow_log` 89 שורות / 11 ימים, אחרונה 08-25 16:50:18 | — |
| TSF_SHADOW_LOG_V1 | 1 | לוג רצפת-סטופ-הייתה-עושה | `tsf_shadow.py:35` | ⚠️ (**מחלקה 1 באתר-הקריאה**) | `SELECT would_apply,count(day_type),count(ib_width)` → `f \| 0 \| 0` מתוך 89 ⇒ `would_apply` קבוע-false, `floor_pts` קבוע 6.0 | `trading_gateway.py:3871-3881` קורא `cross_context…["systems"]["day_type_machine"]` שלא נושא day_type/ib_width במסלול-הצל |
| RISK_CUTOFF_HOUR_ET | 15 | אין כניסות-לייב אחרי 15:30 ET | `risk_checks.py:44` | ⚠️ | `_env_int(...,15)` == ברירת-המחדל; live-only; 0 עסקאות live מאז 08-21 | קבוע ברמת-מודול — נקרא ב-import |
| RISK_CUTOFF_MINUTE_ET | 30 | ↑ | `risk_checks.py:45` | ⚠️ | כנ"ל | כנ"ל |
| RISK_MAX_TRADES_DAY | 999 | ביטול מכסת-עסקאות יומית | `risk_checks.py:35` | ⚠️ | דורס את ברירת-המחדל 5, אך live-only ולא הופעל | דורש ריסטארט לשינוי |
| BAR_SEAM_REJECT_V1 | 1 | הסגר לברים עם פער-תפר >15 נק' | `bars.py:1285-1344` | ❓ | DB: `lag()` על 468 ברים סמוכים מאז 08-22 ⇒ **0** פערים >15 נק' | — |
| TREND_CCI_DIRECT_V1 | 1 | מגמה עוקבת CCI, ביטול שער-SWI | `bars.py:416-427`, מוחל `:1348` | ✅ | מאז 08-22, **178/468** ברים עומדים בכלל החדש שה-DLL היה צובע GRAY | — |
| TREND_CCI_DIRECT_PT | 50 | סף \|CCI\| לכלל הנ"ל | `bars.py:422` | ⚠️ | הסף כובל, אך הערך == ברירת-המחדל בקוד | — |
| TS_OFFSET_INGEST_GATE_V1 | 1 | דחיית מנות-ts חיות-אך-ממותגות-שגוי | `bars.py:575`, נקרא `:636`,`:1233` | ❓ | הפיד היה טרי כל החלון | (הערה: השורה `TS-OFFSET-GATE: non-advancing batch 59576s old` הופיעה 16:27 היום — כלומר הוא **כן** פעיל, אך על ענף ה-non-advancing) |
| IB_BARS_VALIDATE_V1 | 1 | הגשת IB-מברים כשסיירה חולקת | `tpo_routes.py:341-375` | ❓ | 0 שורות `IB CORRECTION`; IB בשימוש 08-24 == IB-מברים בדיוק | — |
| CONFLUENCE_RI_ZLR_V1 | 1 | זיהוי חיבור S2×S4 באותו בר | `confluence_ri_zlr.py:98`·gw `:745` | ✅ | 08-24 18:30:08 `[Confluence] join found but G-fresh REJECT` | חיבור אחד ב-4 ימים |

## 6 · 30 הדגלים הכבויים (פסוקים `0` / `unset_or_0`)

כל 30 נבדקו: **ברירת-המחדל בקוד היא OFF** בכולם חוץ מ-`LOCAL_ALERTS_V1`. כלומר קלון/ריסטארט לא ידליק אותם בטעות — הדיסציפלינה של CLAUDE.md מקוימת.

| דגל | .env | file:line של הקריאה | הערה |
|---|---|---|---|
| LOCAL_ALERTS_V1 | 0 | `local_alert.py:59` — **ברירת-מחדל בקוד "1"** | 🔴 רשת-הביטחון המקומית (צליל+מודאל) כובתה ידנית ⇒ Pushover הוא הערוץ היחיד. זה בדיוק מחלקת-הכשל של 12.08 |
| DAYTYPE_ENTRY_BUDGET_V1 | 0 | `trading_gateway.py:1943` | **הורג 2 דגלים פסוקים-דלוקים** (ENTRY_BUDGET_SKIP_LOSERS/QUALITY) |
| S6_TARGET_APPROACH_REALIZE_V1 | 0 | `target_approach_realize.py:60` | **הורג את EXTREMES_AWARE_REALIZE_V1** |
| S4_GRAY_RELABEL_V1 | 0 | `trend_relabel.py:42` | **הורג את S4_GRAY_RELABEL_CCI=100** |
| DAYTYPE_POSITION_GATE | 0 | `daytype_position_gate.py:76`·gw `:1513` | **הורג את DAYTYPE_PATTERN_AWARE_V1** |
| OPENING_DRIVE_EXHAUSTION_VETO_V1 | 0 | `trading_gateway.py:1128` | היחיד שמייבא את מודול `opening_windows` |
| STALL_EXIT | unset | **אין קורא בקוד כלל** | מצוין: אינרטי-במבנה, בדיוק כדרישת CLAUDE.md (op=EXIT) |
| OPPOSITE_EXIT_V1 | unset | `trading_gateway.py:3446` | כבוי כנדרש |
| ORPHAN_AUTO_FLATTEN_V1 | unset | `sierra_position_reconciler.py:519` | כבוי כפסיקת 28.07 |
| LAYER0_CHOP_GATE | unset | `trading_gateway.py:1084` | כבוי כפסיקת 08.06 |
| S2_CHOPPINESS_GATE | unset | `s2_inspector.py:167` | כבוי כפסיקת 08.06 |
| S2_REQUIRE_COT_AMT | unset | `five_min_system.py:885,1142,1307` | כבוי כפסיקת 08.06 |
| WOODIES_TS_HOUR_FIX | 0 | `bars.py:450` (kill-switch הפוך) | =0 ⇒ הפונקציה חוזרת 0 מיד. נכון לפסיקת 22.07 |
| TS_WHOLE_HOUR_NORMALIZE_V1 | 0 | `bars.py:510` | כבוי |
| VARIATION_SUBTYPE_V1 | 0 | `daytype_playbook.py:239`·gw `:1364` | כבוי |
| MORNING_LABEL_CONFIRM_V1 | 0 | `trading_gateway.py:1448` | כבוי (וגם בלתי-נגיש — מחלקה 3, כפי שנמצא היום) |
| RISK_CONSECUTIVE_LOSS_LIMIT | 0 | `trading_gateway.py:3369` | כבוי כפסיקת 20.07 |
| FIXED_CONTRACTS_2/4/5/6 | 0 | `contract_size.py:64-70` | כבויים; `_3` הוא הפעיל |
| DAY_DIRECTION_STRUCTURAL_V1 | 0 | `trading_gateway.py:1206` | כבוי |
| OPENING_TYPE_GATE | 0 | `opening_type_gate.py:25`·gw `:1097` | כבוי |
| SSV_GATE_V1 | 0 | `trading_gateway.py:1044` | כבוי |
| ZONE_LIMIT_ENTRY_V1 | 0 | `trading_gateway.py:3268` | כבוי |
| STOP_WIDEN_TO_FLOOR_ON_REJECT_V1 | unset | `trading_gateway.py:2603` | כבוי |
| MANUAL_CANCEL_DETECT_V1 | unset | `sierra_position_reconciler.py:836` | כבוי |
| SYSTEM6_REVERSAL_TIGHTEN_V1 | 0 | `system6_supervisor.py:243` | כבוי |
| PATTERN_LOSS_BREAKER | 0 | `woodies_system.py:894` | כבוי (וממילא בלתי-נגיש — מקונן ב-PATTERN_RISK_CAPS המת) |
| T1_LADDER_V2 | unset | `sizing.py:163` +2 | כבוי |

---

## 7 · שלושה שורשים חוצי-דגלים

**שורש-א · `_pattern_family()` מחזיר None ל-`S2_DELTA_DBL_*`** — `daytype_position_gate.py:55-72`: המזהה לא נמצא ב-`_CONT_PATTERNS` (`:33-41`) ולא ב-`_REV_PATTERNS` (`:42-48`). S2_DELTA_DBL הוא **105 מ-108 חסימות-הגייטוויי** ב-4 ימים. לכן הוא בלתי-נראה ל-`CONT_TREND_FILTER` (fail-open), ל-`DAYTYPE_LOCATION_GATE` (`location_gate.py:180-181`), ל-`NEUTRAL_RESPONSIVE_V1`, להיקף `EXTREME_CHASE_GUARD`, ול-`daytype_playbook.yaml` (0 שורות delta). התיקון הוא שורה אחת — אבל הוא **שינוי-סיכון-מסחר** (מדליק 4 שערים רדומים על התבנית הכי פעילה) ⇒ דורש פסיקה, לא טלאי שקט.

**שורש-ב · `backend.v9.app` מול `backend.main`** — שני קוראים חיים מייבאים את המודול הלא-נכון:
- `trade_context.py:878` (`get_live_expansion`) — הכותב היחיד הוא `backend.main:674` ⇒ `expansion=None` ב-**673/673** שורות System0 ⇒ עדיפות-1 של `day_direction` מתה.
- `market_context.py:112` (`app.state.opening_type_result`) — **אפס כותבים בייצור** ⇒ `opening_conf` תמיד 0.0 ⇒ `balance=UNKNOWN` ב-673/673.

הדומינו של שורש-ב: `MARKET_CONTEXT_V1` ❌ → `OPENING_FIRST_TRADE_STRICT_V1` חוסם 7/7 עסקאות-פתיחה → `OPENING_CONF_ENGINE_FUSE_V1` ❌ (נבנה בדיוק להציל conf=0.0, אך שומר על `conf>=0.5`) → `OPENING_PLAYBOOK_V1` ו-`OPENING_WINDOW_FIRE_V1` לא מקבלים סטאפ לפעול עליו. **חמישה דגלים פסוקים, תכונה מתה אחת.**

**שורש-ג · שני כותבים לאותו סטופ** — `STEP_SCALED_LADDER_V1` (`:2914`) רץ אחרי `STOP_RESOLVER_V1` (`:2453`) ודורס: `STOP ARBITRATION: STEP_SCALED_LADDER OVERRODE StopResolver` ×68 מול הישרדות אחת. בנוסף `no valid rung in band → rejected` ב-61/69.

---

## 8 · עשרת החמורים — דלוקים שמייקל חושב שהם מגנים עליו

| # | דגל | למה זה כואב | file:line |
|---|---|---|---|
| 1 | **SCALE_IN_V1 + SCALE_IN_P3_V1** | רגרסיה בת-יומיים: כל מנצח עתידי מפסיד את החיזוק. `AttributeError` על שדה שלא קיים במודל, לא נתפס | `bar_level_detector.py:1285` (+`:1287` except צר) · `db/models/trades.py:27` |
| 2 | **PATTERN_RISK_CAPS** | תקרת-הסיכון פר-תבנית — 26 אירועי-חריגה מוכחים ב-4 ימים, **0** פסקי SKIP/SIZE_DOWN. מוצל ע"י ה-cap-clamp של STOP_STRUCTURE_EXTREME 20 שורות קודם. גורר גם PATTERN_LOSS_BREAKER + GIANT_BAR_STOP + פאזה-3 | `woodies_system.py:853-864` חוסם `:927/:938` |
| 3 | **OPENING_FIRST_TRADE_STRICT_V1** | לא מת — **חוסם-100%**: 7/7 החזקות, כולן `conf 0.0 < 0.6`, כי מקור-ה-conf מת. אף עסקת-פתיחה לא תיפתח אף פעם | `opening_entry.py:419` + `market_context.py:112` |
| 4 | **MARKET_CONTEXT_V1** | balance/acceptance של System-0 קבועים UNKNOWN/pending ב-673/673. שורש ל-4 דגלי-פתיחה נוספים | `market_context.py:112,34` |
| 5 | **TREND_LEG_CHASE_EXEMPT_V1** | פסיקת-לייב 11.08 (5 שורטים עם-המגמה שנחסמו) — מתה פעמיים: חריגה נבלעת + הצרכן דורש דגל שלא קיים ב-.env | `trading_gateway.py:2124`,`:2137`,`:2148` |
| 6 | **RUNNER_TRAIL_V2** | הודלק 08-20 ומאז **אפס ארטיפקטים** — 0 שורות `SWING_TRAIL` בטבלה בכל-הזמנים, 0 שורות F5 בלוג. ו-`manager.py:1074` מחזיר False לכל ZLR, שהוא רוב הירי | `manager.py:1072-1074` |
| 7 | **EXTREMES_AWARE_REALIZE_V1** | פסיקת שלב-1-דלתון (06.08, replay +$410) — ההורה `S6_TARGET_APPROACH_REALIZE_V1` כובה ב-21.08 והבן נשאר "דלוק" | `target_approach_realize.py:60` |
| 8 | **S1_NONCONVICTION_V1** | "יום אפס-OTF ⇒ לעמוד בצד" — התווית מיוצרת ונזרקת: `_DT_MAP` לא מכיר אותה, והמפרסם דורש `NONCONVICTION_ACTIVE_V1` שלא ב-.env | `main.py:528-537,552` |
| 9 | **DAYTYPE_PATTERN_AWARE_V1** | CONT-על-יום-מאוזן / REV-על-יום-מגמה לא נחסמים כלל; שתי הריגות עצמאיות | `daytype_position_gate.py:93-94` · `.env DAYTYPE_POSITION_GATE=0` |
| 10 | **RELEASE_ENTRY_GATE_V1** (⚠️) + **RELEASE_TREND_BYPASS_PTS** (❌) | שער-השחרור החזיק 85 פעם ושחרר **0** — וטו-דה-פקטו. והבייפס ב-12 נק' לא ירה אף פעם למרות 45 ברים כשירים, כי הוא `elif` אחרי LEG_EXEMPT | `release_gate.py` · `trading_gateway.py:2332-2337` |

**כמעט-עשירייה (ראויים לשורה):** `RISK_HALT_V1` — המונה שלו מוזן רק מ-`live_slot` בעוד ההערה טוענת "ALL modes"; 08-24 הפסיד −$1,491 בצל מול תקרת $800 בלי עצירה. חלון-דמו ייתן ירוק-כוזב. · `S2_REACTIVE_EDGE_FIX_V1` + `STRUCTURAL_STOP_ORIGIN_V1` — שניהם בקוד-מת תחת `STOP_ANCHORS_V2=1`. · `S2_AUTH_MATRIX_SINGLE_SOURCE_V1` — 85 תאי-פסק ב-`auth_matrix.yaml` בלתי-נגישים.

---

## 9 · פערי-פיתוח מרוכזים (דגלים חלקיים — מה חסר להם)

1. **פטורים שקטים** — `LEG_EXEMPT_LSMA_FLAT_V1`, פטור-הרגל של location-gate (`:1618-1622`), `DIRECTION_COMPASS_V1` דרך `_compass_or` (`:1702/:1754`): כולם משנים פסק **בלי שורת-לוג**. אי-אפשר לאמת אותם לעולם. `LEG_RIDE_V1` עושה זאת נכון (WARNING) — לאמץ את אותה תבנית.
2. **פרמטרים ששווים לברירת-המחדל** ולכן שורת-ה-.env אינרטית: `ENTRY_CONFIRM_TOL_MIN_PTS`, `EXTREME_CHASE_SCOPE`, `TREND_CCI_DIRECT_PT`, `RISK_CUTOFF_HOUR_ET`, `RISK_CUTOFF_MINUTE_ET`, `RR_MIN_ROTATION` (בשניים מ-3 האתרים).
3. **פרמטרים אינרטיים אריתמטית:** `OPENING_OR_ATR_SCALE_V1` (0.25×38.44=9.61 < רצפת 10) · `MEMS_MIN_RISK_POINTS` (רצפת-רצועה כבר גבוהה יותר) · `MEMS_MAX_RISK_POINTS=60` (פי-2 מהמקסימום שנצפה).
4. **`elif` שמוצל ע"י `if` תמיד-אמת:** זרוע-REACTIVE של `S2_ADAPTIVE_THRESHOLDS_V1` ובלוק-ה-volume של `S2_REACTIVE_DAYTYPE_V1` (מוצלים ע"י `S2_VSA_VOLUME=1`) · זרוע-הגייטוויי של `DAYTYPE_HONEST_PRELOCK_V1` · `RELEASE_TREND_BYPASS_PTS`.
5. **מקורות מורעבים:** `cumulative_delta.json` מייצא 4 נקודות מול מינימום 5 ⇒ `DELTA_FEATURES_V1` לא יכול להצביע · `TSF_SHADOW_LOG_V1` מקבל day_type/ib_width NULL ב-89/89 ⇒ `would_apply` קבוע-false · `v9_day_type_state` היה 3 שעות מעופש היום (`DAYTYPE_WATCHDOG ESCALATION-3` ב-16:30).
6. **`_ANTIFLAP_STATE` בלי איפוס-סשן** (`trade_context.py:487,502`) — `raw is None → return stable` מדליף את תווית-אתמול לבוקר הבא אם אין ריסטארט.
7. **`v9_trades.t4` NULL ב-680/680** — `V9Trade(...)` ב-`manager.py:434` לא מציב t4; הרגל הרביעית בלתי-נראית לכל צרכני-DB.
8. **`v9_decisions` לא קיים ב-Postgres** — פיד-ההחלטות חי רק ב-`/tmp/backend.err.log` וב-`decisions_archive/*.jsonl`. אין היסטוריית-החלטות ניתנת-לשאילתה, וזה מה שהפך את הביקורת הזו ליקרה.

---

## 10 · ממצאים תפעוליים שצצו תוך-כדי (לא דגלים)

- 🔴 **כרגע:** סיירה מחזיקה `position_qty=-3, is_sim=0` בעוד ל-TM אין עסקה פתוחה — `DESYNC ANOMALY` נרשם 16:48:32. שתי העסקאות של היום (#789/#790) הן `mode=shadow`.
- 🔴 `MANUAL_GUARD_AUTOPROTECT_V1` היה דרוך 9.5 שעות היום (02:02-08:18) על 1c עירום אמיתי ולא יכול היה לפעול: `AUTOPROTECT[NO_RECOMMENDATION:avg missing]` ×5.
- 🔴 שלוש דחיות-פקודה `Insufficient Account Value (NLV)` היום (10:11/12:44/13:32) בלי עסקה תואמת.
- 🔴 `POSITION_TRUTH sync errored … invalid transaction is rolled back` — **9,231** פעמים ב-08-23 (סשן עיוור).
- ⚠️ סחף-תיעוד ב-CLAUDE.md: הסט של `SYSTEM6_AUTOCORRECT=protective` כולל היום גם `MODIFY_TARGET` (`system6_supervisor.py:275-280`, לא-משוער). בפועל אינרטי — המבצע (`bar_level_detector.py:108-120`) מטפל רק ב-MODIFY_STOP/DROP_TARGET.
- ✅ **op=EXIT נקי:** ל-`_emit_exit` אפס קוראים לא-טסטיים; `write_exit` נגיש רק מהמסלול הידני `api/v9/trade_commands.py:112`; `STALL_EXIT`/`OPPOSITE_EXIT_V1` אינם ב-.env. אף אחד מ-204 הדגלים לא מנתב אליו.

---

## 11 · מגבלות-הביקורת (יושר-מדידה)

- חלון-הלוג הוא **22-25.08 בלבד**, והכיל **13 עסקאות-צל ו-0 עסקאות live/demo**. העסקה החיה האחרונה: #775, 2026-08-21 22:48. לכן כל שער שקלטו הוא `mode IN ('live','demo')` או `live_slot` קיבל קלט ריק **מבנית** — שתיקתו היא "לא-הופעל", לא "שבור". זו הסיבה ש-31 דגלים סומנו ❓ ולא ❌.
- לא הופעל אף קוד ולא שונה אף קובץ. כל השאילתות היו SELECT.
- כל ❌ בדוח הזה נשען על file:line או על פקודה+פלט. אין ❌ מהיגיון בלבד.
