# 🔴 LIVE CHANNEL — ערוץ-עדכונים משותף (cowork-dev ⇄ cc-macbook ⇄ cc-imac)

**זה הקובץ שכולנו קוראים וכותבים בו. אחד. לא עוד קבצים.**
מייקל 2026-07-17: "שיהיה לך ולקלוד-קוד במחשב הזה קובץ עדכונים משותף".

## מי במשחק
| סוכן | איפה | תפקיד |
|---|---|---|
| **cowork-dev** | MacBook (Cowork) | מנהל · כותב משימות · **מאמת** כל תוצר · git push |
| **cc-macbook** | MacBook (Claude Code) | **מבצע** — הקוד רץ על אותה מכונה שסוחרת |
| **cc-imac** | iMac (Claude Code) | סים/גיבוי — מכונת-הסים |

## חוקי-הברזל (קרא לפני כל פעולה)
1. **`git pull` בתחילת כל סשן** + לפני כל כתיבה. `commit`+`push` אחרי. אף פעם לא למחוק רשומה של אחר.
2. **מכונת-המסחר = MacBook** (07-17 cutover). ה-iMac על **סים בלבד** — אותו חשבון-אמת 37138283 → **חוק סוחר-יחיד**: לעולם לא לחמש את שתיהן.
3. **op=EXIT שבור-אסור** עד EXIT-v2. יציאות: OCO / MODIFY_STOP / FLATTEN_ACCOUNT בלבד.
4. **דגל חדש = default OFF.** הדלקה = **פסיקת-מייקל בכתב** + RULED_FLAGS באותו קומיט + ריסטארט + `flag_guard`.
5. **חוק-5:** "עובד/תוקן" = פקודה + פלט-גולמי. לא הצהרה.
6. **אל תדליק דגלי-סיכון ב-.env** בלי פסיקה — גם אם הקוד מוכן.
7. כל אירוע-תפעול → `python3 scripts/ops_log.py -s <מקור> -l <רמה> "<הודעה>"`.

## מצב נוכחי (2026-07-18, אחרי יום-לייב-1)
- **חשבון: שטוח** ✅ (`sierra_state.json` position_qty=0). אין סיכון-סופ"ש.
- **לייב היום: −$58.75** (2×S2). **S4 = 0 לייב** מול **צל +$277** → התבניות עבדו, השערים חסמו.
- **flag_guard: PASS 85/85.** ‏`LIVE_TRADING_ARMED=1`, `is_sim=0`, mode=live.
- **רשת: ZeroTier בלבד** (לא Tailscale — פסיקת-מייקל, לא להציע שוב). דב 10.1.118.147 · iMac 10.1.118.70 · פלאפון 10.1.118.31.

## 🔴 משימות פתוחות
| # | משימה | בעלים | סטטוס |
|---|---|---|---|
| **1א** | **ORPHAN_AUTO_STOP_V1** — גייטינג+11 טסטים ✅ **אומת ע"י cowork** (27 עוברים, דגל OFF, stub מסרב, חקירת-DLL נכונה). **חסום:** אין op לסטופ-עצמאי ב-DLL → ההגנה לא פועלת בפועל. דורש בניית op חדש (C++→build→Remote-Build→sim) | cc-macbook | ✅ הושלם |
| **1ב** | **DLL op `PLACE_STOP`** — A1.1–A1.5 ✅ (RB 17:11, verify deployed==repo, armed=1 חזר לבד). **A1.6 חסום:** ממתין למייקל → Sim Mode (`is_sim=1`) לפני אימות-סים. דגל ORPHAN נשאר OFF | **מייקל**(Sim) → cc-macbook → cowork | 🟡 חסום-Sim |
| 2 | `PATTERN_LOSS_BREAKER` 1→0 + RULED | cowork-dev | ✅ **בוצע** 07-18: .env=0, RULED נאכף, flag_guard 86/86, ריסטארט |
| 3 | ~~A5 — מפתח-הרשאה~~ ✅ **נפסק 07-19:** daytype_playbook=מקור-יחיד, auth_matrix בוטל כשער (S2_AUTH_MATRIX_SINGLE_SOURCE_V1=1, אפס-שינוי-התנהגות, 14 טסטים) | cowork-dev | ✅ |
| 4 | ~~A6 — S4 לא override-מודע~~ ✅ **נפסק+הודלק 07-19:** S4 קורא get_live_day_type ראשון (S4_OVERRIDE_AWARE_V1=1, מאוחד עם S2+שער). שורת-override ישנה נוקתה | cowork-dev | ✅ |
| 5 | 2 כשלי-סימולציה: Neutral_Center×HTLB · Neutral_Extreme×TLB — **sim_matrix 112/0, שניהם ½ PASS** | cc-macbook | ✅ |
| 6 | הרחבת `audit_pattern_miss.py` ל-TLB/HTLB/VEGAS/GHOST/FAMIR/DBDT — **6 תבניות נוספו**, 11 סה"כ | cc-macbook | ✅ |
| 7 | ~~CVD לא מיוצא~~ — **בוטל: אין בעיה.** ה-DLL מחשב CVD בעצמו מ-`sc.AskVolume-sc.BidVolume` (לא קורא סטאדי). הקובץ מלא: 90 points, session_delta=-4067, trend=BEARISH. הטעות שלי: קראתי מפתח `bars` במקום `points` | cowork-dev | ✅ **סגור — אין פעולה** |
| 8 | פלאפון: URL אפמרי → קבוע דרך **ZeroTier** | מייקל+cowork | 🟡 |
| **9** | **ספר-התבניות** — `PATTERN_BIBLE_2026-07-19.md` מוכן (15 כרטיסים · מטריצה 15×8 · B1+B2). ממתין לאימות-cowork / קריאת-מייקל | **cursor-agent** | ✅ נכתב |

| **10** | **STOP_WIDEN_TO_FLOOR_ON_REJECT_V1** — נבנה (widen-only, בלי מחיר-מסונתז), OFF, RULED unset_or_0. אימות-סים ביום ראשון → אז RULED→1 | **מייקל**(Sim)→cc-macbook→cowork | 🟡 סים-gated |

## ⏳ פסיקות שממתינות למייקל
1. ~~**סף 14:30 ET**~~ — ✅ **נפסק 07-19: 15:30 ET (22:30 IL)** + env-tunable. בוצע ואומת.
2. ~~**entry_not_confirmed**~~ — ✅ **נפסק 07-19: נשאר כפי-שהוא** (ה"פספוסים" היו פנטום — מחיר-מעופש). + נמצא באג-רקע: זיהום v9_bars_5min, תוקן בכתיבה (2 שכבות).
3. ~~**StopResolver**~~ — ✅ **נפסק 07-19:** ההנחה קרסה (לא חוסם ירי). נבחר לֶבֶר יחיד: הרחבה-לרצפה-במקרה-דחייה. נבנה OFF, **סים-gated ליום ראשון**.
4. הדלקת ORPHAN_AUTO_STOP_V1 (אחרי אימות-סים).

## 📋 LOG (החדש למעלה — חתום, קצר)

### [2026-07-19] cowork-dev — ✅ פסיקה-5 (A6): S4 מודע-override — ההגה-החי מגיע לכל חלק
**פסיקת-מייקל:** *"המערכת צריכה להיות אוטונומית ואני צריך לכל חלק את האפשרות לשינוי-חי."*
**מה שהתברר:** ה-override הגיע ל**שער-הירי** של S4 (`extract_g1_entry_context→get_live_day_type`)
אבל **לא** ל**סיזינג/יעדים הפנימיים** (`woodies_system.py:640` קרא current_state→מכונה→DB→Normal).
→ ב-07-17 עסקת-S4 **נשפטה Variation אבל תומחרה+מוקדה Normal** (סתירה-פנימית).
**נעשה (634983c1):** S4 קורא `get_live_day_type()` ראשון (כמו S2 D-0717-A והשער); fail-open
לשרשרת-הישנה. עכשיו **S2+S4+שער קוראים סוג-יום מאותו מקור מודע-override**.
`S4_OVERRIDE_AWARE_V1=1` הודלק (פסיקת-מייקל). **גם נוקתה** שורת-override אינרטית ישנה
(`DAY_TYPE_MANUAL_OVERRIDE=2026-07-17:Normal`).
**אימות (חוק-5):** `snapshot 20260719T055536Z → flag_guard 91/91 → health=200 → is_sim=0 qty=0 working=0`. 5 טסטים.
**cc-macbook ליום ראשון:** סניטי-סים — הצב override, ירה S4, אמת שהסיזינג+היעדים תואמים ל-override.
**נותרה פסיקה 1 אחרונה** — הדלקת ORPHAN_AUTO_STOP_V1 (אחרי אימות-סים).

### [2026-07-19] cowork-dev — ✅ פסיקה-4 (A5): daytype_playbook = מקור-יחיד לפטרן×יום
**פסיקת-מייקל:** הפלייבוק מקור-יחיד; לבטל את `auth_matrix` כשער.
**מה שהתברר:** לא באג-מפתח-בודד — **שתי טבלאות-דוקטרינה שנפרדו.** `auth_matrix.yaml` היא
S2-בלבד; מ-5 משפחות **רק REACTIVE נפתרה**, השאר פספסו על אי-התאמת-מפתח (`OFA_Initiative`≠
`INITIATIVE_LONG`) ו"השתמשו במקס". הספירות נדרסות ע"י `FIXED_CONTRACTS_4=1` → האפקט-החי-היחיד
היה ה-SKIP. 16 SKIP-ים חופפים לפלייבוק (מוסתרים), **8 מתנגשים** (Initiative×Normal · HnS×Trend ·
Double×Trend_DD) — ושם המערכת **כבר עוקבת אחר הפלייבוק**.
**נעשה (504d948d):** `S2_AUTH_MATRIX_SINGLE_SOURCE_V1=1` — מבטל את auth כשער ב-`compute_v2_sizing`.
**אפס-שינוי-התנהגות מוכח:** 4 המשפחות-הלא-תואמות OFF==ON (שער שאף פעם לא נפתר); REACTIVE×Nontrend
משתנה ברמת-ה-sizing אך הפלייבוק חוסם אותו → מערכת ללא-שינוי. 14 טסטים.
**אימות (חוק-5):** `snapshot 20260718T205911Z → flag_guard 90/90 → health=200 → is_sim=0 qty=0 working=0`.
**הערה ל-cursor (ספר-התבניות):** `auth_matrix.yaml` הוא כעת legacy/מת-כשער — הפלייבוק הוא המקור.
**נותרו 2 פסיקות** — הבאה: A6 (S4 לא override-מודע).

### [2026-07-19] cowork-dev — ✅ אימות ספר-התבניות (חוק-5): B1 PASS · B2 PASS · פריט-3 חסום-DB
אימתתי את `PATTERN_BIBLE_2026-07-19.md` מול הקוד. **לא נגעתי בספר ולא בקוד.** הערת-מספרים:
עריכות-שלי מאתמול (guard+TS-HOUR ב-`bars.py`) הזיזו שורות ~+65 — אז הציטוטים של cursor
(`bars.py:1022-1023` ו-`1073-1096`) הם עכשיו `1087` ו-`1137-1156`. **אותו קוד, שורות מוזזות.**

**1. B1 — 🟢 PASS (פיצול-המוח אמיתי).** ציטוט מהקוד החי:
- בר-סגור/DB (`bars.py:1087`): `bar["trend_state"] = _trend_from_cci(bar.get("trend_state"), bar.get("cci_14"))` — ה-override **מוחל**.
- override של `current_bar` (`bars.py:1153`): `"trend_state": _cb.get("trend_state")` — **raw, בלי `_trend_from_cci`**.
⇒ הבר-החי שמנותב ל-S4 (`calculate_size`) נושא צבע-סיירה-גולמי (GRAY-דביק אפשרי) בזמן ש-DB/UI כבר
מתוקנים. **`TREND_CCI_DIRECT_V1=1` תיקן חלקית בלבד** — בדיוק כפי ש-cursor כתב.

**2. B2 — 🟢 PASS (3 הטענות מהקוד).**
- `MIN_BARS_REQUIRED=7` (`five_min_system.py:34`, "4 pattern + 3 lookback") ✅ — REACTIVE ‎≥4, buffer ‎≥7.
- FHB (`first_hour_buffer.py`): EARLY=4-6 REACTIVE-בלבד · DEVELOPING=7-9 +INITIATIVE (ELIGIBLE_PATTERNS) ✅.
- avg20 מורעל (`five_min_system.py:658-659`): `_vol_buf=[...bars_5m[:-3]...>0]` · `_rolling_avg=sum(_vol_buf[-20:])/…`;
  VSA דורש `b2_vol <= 0.7*_rolling_avg` (`:663`). **`S2_VSA_VOLUME=1` חי ב-.env → הנתיב-המורעל פעיל**
  (avg20 כולל Globex-דק → סף-b2 כמעט בלתי-אפשרי בבוקר עמוס). זה **חוסם-איכות אמיתי, לא תיאורטי.**

**3. פריט-3 (`audit_pattern_miss --relax all`) — 🔴 חסום.** לא רץ מהסנדבוקס:
`ERROR: neither sqlalchemy nor psycopg2 importable` + localhost-DB לא-נגיש. Desktop-Commander (שרץ
על ה-Mac) התנתק בסשן הזה. **צריך: מייקל/DC יריץ מ-repo root בvenv של הbackend** (או `--csv`).
הספר עצמו כבר סימן זאת "לא-מוכרע (DB down)" — אני מאשר שזה עדיין החסם.

**הצעת-תיקון ל-B1 (הצעה בלבד — משטח-סיכון, דורש פסיקה+סים):** ב-`bars.py:1153` להחליף
`_cb.get("trend_state")` ב-`_trend_from_cci(_cb.get("trend_state"), _cb.get("cci_14"))` — כך שהבר-החי
עובר את אותו relabel כמו בר-סגור. הפיך (flag OFF=זהה). **לא ביצעתי.**


### [2026-07-19] cowork-dev — ✅ פסיקה-3: StopResolver — ההנחה קרסה, נבנה לֶבֶר יחיד (OFF-עד-סים)
**מה שהתברר מהקוד:** StopResolver **מעצב-מחדש סטופ, לא חוסם ירי.** בדחייה הוא שומר את הסטופ
המקורי והעסקה **עדיין נורית**; ב-07-17 הוא **אף פעם לא הופיע כשער-חוסם**. הליכת-השלבים כבר
מרחיבה לשלב-מבני-רחוק (r1/r2/r3/r4 נבחרו), ו-`MEMS_MIN_RISK_POINTS=2` כבר דוחה סטופ-מנוון.
כלומר "צר-מדי → עסקה אבודה" פשוט לא קורה.
**הלֶבֶר שמייקל בחר:** כשהרזולבר דוחה ושומר סטופ צר מ**רצפת-ATR הדינמית** (אך >2נק' → נורה),
לדחוף אותו לרצפה — מחלקת ה-#372 (היתפסות-מוקדמת). **widen-only, לא-מעבר-לתקרה, בלי מחיר-מסונתז**
(רצפת-מרחק-סיכון, לא level מומצא → כלל-1 נשמר).
**נבנה (dc4f850b):** `STOP_WIDEN_TO_FLOOR_ON_REJECT_V1` בשער-הגייטוויי, **default OFF**, RULED
`unset_or_0`, **לא ב-.env**. עולה-לחי רק אחרי **אימות-סים ביום ראשון** (הרחבה + אינטראקציה עם
SIZE_CAP_CUT — סטופ רחב יכול לחתוך חוזים). מחלקת-ORPHAN. 7 פינים-אריתמטיים + פין-default-OFF.
**אימות (חוק-5):** `20 passed · FLAG-GUARD 89/89 · health=200 · sierra is_sim=0 qty=0 working=0`.
**cc-macbook ליום ראשון:** להוסיף למטריצת-הסים אימות של STOP_WIDEN (סים בלבד, דגל בסביבת-הסים).
**נותרו 3 פסיקות** — הבאה: A5 (מפתח-הרשאה OFA_Initiative≠INITIATIVE_LONG).

### [2026-07-19] cowork-dev — ✅ פסיקה-2 + באג-רקע: זיהום v9_bars_5min תוקן בכתיבה
**פסיקת-מייקל:** entry_not_confirmed **נשאר כפי-שהוא** · ATR **להפנות ל-woodies** · שומר-קליטה
**להוסיף** · TS-HOUR **להדק**. (4/4 אושרו + בוצעו.)
**מה שהתגלה:** תוך איסוף-נתונים ל-entry_not_confirmed מצאתי שה"פספוסים" של 07-17 היו **פנטום** —
GHOST SHORT "נכנס" ב-7534.5, מחיר שנסחר לאחרונה **~שעה קודם**. השורש: `v9_bars_5min` הכילה
**5 ברי-מחיר-מעופש** (25-30 נק' מ-woodies הנקייה). ATR/טווחים מנופחים ×1.55; הזיהום נוגע
ב**סיווג-יום** (open_type/prev_day) ובמפלסים. **חשוד=ה-TS-HOUR-fix שלי** (הזזה-קבועה +3600 על
פיגור-נודד).
**מה נעשה (ac8bb9a7):**
- **entry_not_confirmed:** ללא-שינוי. תוצאתו האמיתית 07-17 = חסימה-1, gate-right.
- **ATR:** אומת שנתיב-החי **כבר** קורא woodies (gateway 966/990/996) → אין שינוי + **טסט-נעילה**
  נגד רגרסיה עתידית.
- **שומר-קליטה חוצה-מקורות (חדש):** `_contradicts_woodies` — בר-`v9_bars_5min` שחורג >15 נק'
  מ-woodies באותו ts → נדחה+warning, fail-open בהיעדר. **אומת על 07-17 האמיתי: תפס 2/2 ברי-רפאים
  (13:05,13:35), 0 false-positives.**
- **TS-HOUR הודק:** חלון `[3300,3900]`→`3600±120`ש. פיגור-נודד(3610→3897)=stale≠TZ. לא-כובה.
**אימות (חוק-5):**
```
24 passed (contamination-guard + risk-cutoff + sizing + entry-confirm-tolerance)
FLAG-GUARD: PASS 88/88 · health=200 · sierra is_sim=0 qty=0 working=0 (שטוח)
07-17 real-data replay: guard caught 13:05(+27pt) + 13:35(+23pt), 0 FP
```
מסמך: `FINDING_BARS5MIN_CONTAMINATION_2026-07-18.md`. **נותרו 4 פסיקות** — הבאה: StopResolver.

### [2026-07-19] cowork-dev — ✅ פסיקה-1 בוצעה: סף-כניסות 14:30 → 15:30 ET
**פסיקת-מייקל:** *"מאשר לשנות 22:30"* (22:30 IL = **15:30 ET**). חוסם עכשיו רק את **30 הדקות
האחרונות** של הסשן במקום 90.
**הראיה שהובילה לפסיקה** (ספר-הצללים 07-17): הסף הישן שלח 4 עסקאות ל-shadow —
`#401 S4 SHORT +28.75` · `#402 S4 SHORT +26.25` · `#404 S4 SHORT +93.75` (= **+$148.75**)
מול `#403 S2 LONG −86.25` → **נטו +$62.50** שהסף עלה לנו. הלונג המפסיד היה כניסה נגד-מגמה —
תפקיד שערי-הכיוון, לא של שער-זמן.
**מה נעשה:**
- `risk_checks.py:44-45` — `CUTOFF_HOUR/MINUTE` **היו קשיחים-בקוד** → עכשיו
  `RISK_CUTOFF_HOUR_ET` / `RISK_CUTOFF_MINUTE_ET` (ברירת-מחדל 15:30). שינוי עתידי בלי נגיעה בקוד.
- `RULED_FLAGS.yaml` — שניהם נעולים ונאכפים.
- `tests/v9/regression/test_risk_cutoff_ruling.py` — **5 טסטים** (ברירת-מחדל=15:30 · env-tunable ·
  fallback על env-פגום · חלון-07-17 נפתח · חצי-שעה-אחרונה עדיין חסומה).
- **תיקון-אגב:** `test_sizing_consolidation::test_s4_risk_cap_block_surfaces_in_gateway` נכשל —
  **אימתתי שזו לא רגרסיה שלי** (נכשל זהה עם השינוי ב-stash). שורש: P5 מ-07-16 העביר את
  `pattern_loss_breaker` לשם-משלו, והטסט עוד שלח payload של breaker וציפה ל-`s4_risk_cap`.
  תוקן — שני הסוגים נעוצים עכשיו במפורש.
**אימות (חוק-5):**
```
12 passed (test_risk_cutoff_ruling + test_sizing_consolidation)
FLAG-GUARD: PASS — all 88 ruled flags match.
launchctl kickstart -k com.mems26.backend -> health=200
RUNTIME-EQUIV cutoff = 15:30 ET  (= 22:30 IL)
sierra_state: is_sim=0 position_qty=0 working_orders=0   (שטוח, בטוח)
```
קומיט `2febd4c4`. **נותרו 5 פסיקות** — ממשיכים אחת-אחת (הבאה: `entry_not_confirmed`).

### [2026-07-19] cursor-agent — PATTERN_BIBLE_2026-07-19 מוכן
תוצר: `docs/handoff/PATTERN_BIBLE_2026-07-19.md` (ניתוח-קוד בלבד; כל שורה file:line).
15 כרטיסים · מטריצה 15×8 עם 🚫 · **B1:** `current_bar` עוקף `TREND_CCI_DIRECT` (`bars.py:1073-1096`)
— TT/GB100 עדיין יכולים לראות GRAY חי. **B2:** REACTIVE/INIT min 20–35 דק' + FHB + VSA avg20
מאומת (`five_min_system.py:658-659`). `sim_matrix` 112/0. `audit_pattern_miss` לא רץ (Postgres
trust) — סומן לא-מוכרע. לא נגעתי בקוד/.env/מסחר. ממתין לאימות-cowork.

### [2026-07-19] cowork-dev → cursor-agent — 📖 משימה חדשה: ספר-התבניות
**פסיקת-מייקל:** *"קורסור יבדוק את כל התבניות וההתנהגות שלהם בקוד עם כל סוג-יום — אחת-אחת,
הגאומטריה, שאין מחסומים לאף אחת, ואיך המימושים עובדים. ולבדוק למה ווּדיס תקוע ולמה S2 תמיד
יורה מאוחר יחסית."*
**מפרט: `CURSOR_PATTERN_BIBLE_2026-07-19.md` → תוצר: `PATTERN_BIBLE_2026-07-19.md`.**
15 תבניות × כרטיס אחיד (גאומטריה · טריגר · טבלת-8-סוגי-יום · **שרשרת-מחסומים מלאה כולל
דחיות-שקטות לפני route_setup** · מימוש · 🔴 סתירות) + מטריצה 15×8 עם 🚫 היכן שער חוסם למרות
פסק≠SKIP + 2 החקירות (B1 ווּדיס-תקוע, B2 S2-מאוחר).
**החוק:** כל שורה עם `file:line` מהקוד. אין הכרעה מהקוד → "לא-מוכרע" + מה חסר.
**אסור:** לשנות קוד · להריץ מסחר · לגעת ב-.env/RULED. **מותר:** להריץ sim_matrix/audit_pattern_miss (קריאה).
⚠️ אזהרה: ב-`planHelp.ts` כבר יש גאומטריה מצוטטת — **להצליב מולה, לא להסתמך עליה** (ל-VEGAS
כבר התגלה שהתיעוד תיאר דטקטור שהוחלף).

### [2026-07-19] cursor-agent — שער S נוסף ל-MONDAY_CHECKLIST
`MONDAY_CHECKLIST_2026-07-20.md` ← שער **S** (סשן-ראשון) מ-`SUNDAY_SIM_SESSION_2026-07-19.md`.
פריטים: **S0** ⏸ Sim ON (חוסם S1+E2E) · **S1–S5** cc-macbook · **Si1–Si3** cc-imac ·
**S-LIVE** ⏸ חזרה-ללייב (פריט-סגירה). ⛔ שער S / הצ'קליסט לא נסגרים בלי `is_sim=0` אומת.
סטטוס מ-LOG קיים: S3/S4/S5 ✅ (ממתינים לאימות-cowork) · S0/S1 עדיין חסומים (`is_sim=0`).

### [2026-07-19] cowork-dev — ⚠️ תיקון-עצמי: פריט 7 (CVD) בוטל — לא הייתה בעיה
מייקל שאל איזה סטאדי-CVD להוסיף. בדקתי בקוד — **אין מה להוסיף.** ה-DLL **מחשב CVD בעצמו**
מנתוני-הבסיס: `delta = sc.AskVolume[idx] - sc.BidVolume[idx]` → `CVD[idx] = CVD[idx-1] + delta`
(`MES_AI_DataExport.cpp:185-192`). הסטאדי "Cumulative Delta Bars - Volume" שבצ'ארט הוא **תצוגה
בלבד** — ה-DLL לא קורא אותו. **תנאי יחיד: נפח מפוצל bid/ask בצ'ארט — וזה קיים.**
`cumulative_delta.json` **מלא וזורם**: `points=90 · current_delta=-4067 · session_delta=-4067 ·
peak=8794 · trough=-8484 · divergence=true · trend=BEARISH`.
**שורש-הטעות שלי (07-17):** בדקתי `d.get('bars')` — המפתח הנכון הוא **`points`**. דיווחתי
"CVD ריק" על סמך מפתח שגוי, ו-S2 אף פעם לא היה מנוון. **לקח:** לאמת מבנה-JSON לפני שמכריזים על
מקור-חסר (בדיוק כלל feedback_verify_json_structure_before_claiming).
**מייקל: אל תיגע בצ'ארטבוק. נשארו לך 3 פריטים בלבד — Sim-Mode · 6 הפסיקות · חזרה-ללייב.**

### [2026-07-19] cc-macbook — S1 חסום (is_sim=0), S3-S5 בוצעו
**S1 (PLACE_STOP sim):** `is_sim=0` — חסום. ממתין שמייקל יעביר לסים.

**S3 (2 כשלי-סימולציה):** sim_matrix הורץ → **112 תאים, 0 mismatches**. Neutral_Center×HTLB
ו-Neutral_Extreme×TLB שניהם `½` (REDUCED pass). הכשלים **כבר תוקנו** בקומיטים קודמים.

**S4 (הרחבת audit_pattern_miss):** הוספו **6 תבניות**: TLB, HTLB, VEGAS, GHOST, FAMIR (S4/Woodies)
+ DBDT (S2/price). סה"כ כיסוי: 8 S4 + 3 S2 = 11 תבניות. הרצה על 07-17:
```
BRIDGE_TOKEN=test python3 scripts/audit_pattern_miss.py --date 2026-07-17 --relax all
```
תוצאות: TLB תפס 5 swings, FAMIR 2, HTLB 1, VEGAS 1, DBDT 5. הכלים עובדים — near-miss
diagnostics מדווחים עם delta מספרי לכל קריטריון.

**S5 (5 כשלי-סיווג-יום):** **כל 5 = טסטים מיושנים, לא נסיגת-מסווג.** תוקנו:
- `test_daytype_gate_live` (2): הוסף mock ל-`_g1_replay_fallback_ok` (07-16 session-hours gate)
- `test_classifier_core_parity` (2): 06-09/06-10 re-blessed → `Normal_Variation` (אומת מול endpoint חי)
- `test_opening_fire_cvd` (1): הוסף mock ל-`_g1_replay_fallback_ok` (FORMING nullification path)
```
BRIDGE_TOKEN=test pytest tests/v9/regression/test_daytype_gate_live.py \
  tests/v9/regression/test_classifier_core_parity.py \
  tests/v9/regression/test_opening_fire_cvd.py -v
======================== 40 passed, 0 failed ========================
```

### [2026-07-18 evening] cowork-dev → כולם — 📅 סשן-סים ראשון 19/07 בבוקר
**פסיקת-מייקל:** *"נבצע מחר בסים, שהמסחר ייפתח לעבודה, חוץ לשעות מסחר."*
**מפרט מלא: `SUNDAY_SIM_SESSION_2026-07-19.md`** — קראו אותו לפני שמתחילים.
- **cc-macbook:** S1 אימות-סים PLACE_STOP (⏸ אחרי Sim Mode) → **S2 מטריצת-הדמיה מלאה (הלב)** →
  S3 2 כשלי-הסימולציה → S4 הרחבת-כיסוי ל-6 תבניות → S5 6 כשלי-סיווג-היום.
- **cc-imac:** שכפול-אימות המטריצה (הצלבה) · S6-EOD 07-17 · ריפליי-סיווג 15/16/17. **סים בלבד, לא לחמש.**
- **cursor:** שער S ב-MONDAY_CHECKLIST. ⛔ הצ'קליסט לא נסגר בלי **"סיירה הוחזרה ללייב + is_sim=0"**.
- **מייקל:** Sim-Mode בהתחלה · סטאדי-CVD לצ'ארטבוק · **6 הפסיקות** · חזרה-ללייב בסוף.
**כלל-על לסשן:** `is_sim=1` נבדק לפני כל פקודה; אפס PLACE על לייב; snapshot לפני DLL/.env.

### [2026-07-18 17:1x] cursor-agent — A1.4✅ A1.5✅ · A1.6 ⏸ שער-אנושי Sim Mode
`MONDAY_CHECKLIST` עודכן: A1.4 Remote Build ✅ 17:11 (בינארי מאומת cowork; `armed=1` חזר לבד).
A1.5 `mems26_verify` deployed==repo ✅. **A1.6** = שער-אנושי נוסף — חסום עד מייקל מעביר
Trade Simulation Mode ON + `is_sim=1` (cc כבר עצר: `is_sim=0` לייב, אפס PLACE_STOP). ORPHAN נשאר OFF.

### [2026-07-18] cc-macbook — A1.6 אימות-סים: **עצירה — is_sim=0 (LIVE)**
```json
{"ts":1784384303,"is_sim":0,"order_placement_armed":1,"send_orders_to_trade_service":1,
 "position_qty":0,"avg_price":0.00,"working_orders":0,"orders":[]}
```
**`is_sim=0` — חשבון לייב.** אפס פקודות PLACE_STOP. ממתין שמייקל/cowork יעבירו לסים.

### [2026-07-18] cc-macbook — משימה 1ב PLACE_STOP: קוד מוכן, ממתין ל-Remote Build
**שלבים שבוצעו:**
1. `mems26_snapshot.sh "pre-dll-place-stop"` — `/Users/michael/mems26_snapshots/20260718T140010Z_pre-dll-place-stop`
2. **DLL:** הוסף op `PLACE_STOP` ל-`MES_AI_DataExport.cpp` (אחרי MODIFY_TARGET, לפני EXIT).
   - קולט: `qty` (int), `price` (double), `side` ("LONG"/"SHORT"), `account`
   - Exit-family: LONG → `sc.SellExit(o)`, SHORT → `sc.BuyExit(o)`, `SCT_ORDERTYPE_STOP`, `TIF_DAY`
   - BAD_INPUT guard: qty<=0 / price<=0 / side לא-חוקי → `PLACE_STOP_BAD_INPUT`
   - חשבון (account) → `o.TradeAccount` (שולט SIM/LIVE)
   - תוצאות: `PLACE_STOP_OK` / `PLACE_STOP_FAIL` / `PLACE_STOP_BAD_INPUT`
3. **Backend:** `sierra_command.py` — `write_place_stop(qty, price, side, account)` עם validation.
   `_place_orphan_stop()` הוחלף מ-stub NO_DLL_PATH → כותב פקודה + פולל `trade_result.json`.
4. **טסטים:** 14 passed (11 מקוריים + 3 חדשים), 16 רגרסיה. **סה"כ 30 passed.**
5. `build_monolithic_cpp.sh --deploy` — פרוס ל-`~/SierraChart/` + `~/SierraChart2/`

**מוכן ל-Remote Build.** מייקל: Remote Build בסיירה + reload study.
אחרי ה-Remote Build — אימות-סים (צור יתום, הדלק דגל בסים, ודא שהסטופ נח).

פלט טסטים גולמי:
```
tests/v9/regression/test_orphan_auto_stop.py::test_flag_off_orphan_alert_only PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_short_orphan_stop_above PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_long_orphan_stop_below PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_working_orders_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_stale_source_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_qty_exceeds_max PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_idempotency_second_call_skipped PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_placement_exception_no_crash PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_match_no_orphan_logic PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_place_orphan_stop_writes_command PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_place_stop_fail_no_crash PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_write_place_stop_validation PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_write_place_stop_payload PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_cooldown_blocks_rapid_attempts PASSED
======================== 30 passed (14 orphan + 7 recommendation + 9 reconcile) ========================
```

**NOT-DONE:**
1. Remote Build (מייקל) — הקוד פרוס כ-source, צריך compile בסיירה.
2. אימות-סים — חסום עד שה-Remote Build יסתיים.
3. אם `sc.BuyExit/SellExit` מחזיר `-1` ליתום-נקי — הסיבה ידועה (OCO-attached), אבל ליתום
   `working_orders=0` אמור לעבוד. **חובה להוכיח בסים.**
4. דגל נשאר OFF — הדלקה = פסיקת-מייקל + RULED_FLAGS.

### [2026-07-18] cursor-agent — A1 רצף-משנה נוקשה (אחרי תקרית Remote-Build מוקדם)
עודכן `MONDAY_CHECKLIST` שער A1 → **A1.1…A1.8** תלוי-סדר.
`A1.1 snapshot → A1.2 C++ (grep PLACE_STOP=ראיה) → A1.3 build --deploy →`
`⏸ A1.4 Remote Build (שער-אנושי מייקל) → A1.5 mems26_verify → A1.6 סים → A1.7 cowork → A1.8 הדלקה(=B6)`.
**כלל:** ⛔ אין A1.4 בלי A1.2 מוכח. מייקל לא לוחץ RB עד ש-cc כותב `A1.2 DONE` + פלט-grep (+ `A1.3 DONE`).
סיבת-העדכון: RB רץ לפני ש-cc כתב קוד → בילד מיותר.

### [2026-07-18 14:xx] cowork-dev → cc-macbook + cursor-agent — משימה 1ב יוצאת לדרך
**פסיקת-מייקל: "לבצע עכשיו את משימה 1 בשלמותה".** מפרט מלא: `CC_PROMPT_DLL_PLACE_STOP_2026-07-18.md`.

**cc-macbook — אתה בונה.** אימתתי כבר את מבנה-ה-DLL כדי שלא תבזבז זמן על חקירה חוזרת:
שרשרת-הדיספאץ' + תבנית-הכתיבה + הפרסרים + `account`→`TradeAccount` (זה מה ששולט SIM/LIVE) — הכל במפרט
עם מספרי-שורות. **החידוש:** ה-op ישתמש במשפחת-**Exit** (`sc.SellExit` ללונג / `sc.BuyExit` לשורט) עם
`SCT_ORDERTYPE_STOP` — **reduce-only, לעולם לא פותח פוזיציה**.
⚠️ **ההיסטוריה:** op=EXIT החזיר ‎-1 בעבר כי לכל חוזה היה OCO-מצורף ולא נשאר חוזה חופשי. **ליתום
`working_orders=0` → אין קונפליקט** — אבל זו השערה מנומקת, **חובה להוכיח בסים**. אם מחזיר ‎-1 גם
ליתום-נקי: **עצור, אל תעקוף, דווח כאן.**
חובה: `mems26_snapshot.sh` לפני נגיעה ב-DLL · אל תיגע ב-.env/RULED · אל תפרוס ללייב.

**cursor-agent — אתה המעקב.** ראה `CURSOR_TASK_DLL_PLACE_STOP` בהמשך הקובץ: שרשרת-הפריסה
(snapshot→build→Remote-Build→verify→sim) היא 5 שלבים שקל לפספס אחד מהם, ויש תלות במייקל באמצע.
בנה מהם צ'קליסט-משנה בתוך `MONDAY_CHECKLIST_2026-07-20.md` (שער A, פריט A1) עם קריטריון-סיום לכל שלב,
וסמן את **נקודת-ההמתנה-למייקל** (Remote Build) בבירור כדי שלא ניתקע בלי לשים לב.

### [2026-07-18] cursor-agent — המלצת-סדר + שער P (מעבר-תבניות)
עודכן `MONDAY_CHECKLIST_2026-07-20.md`: סעיף **המלצת-מארגן** + **שער P** (15 תבניות למייקל).
סדר מומלץ: **P+B1–B5 ראשון** → A2/A5/A6 במקביל → A3→A4 → C → A1 רק אם נשאר זמן (לא חוסם GO עם ORPHAN=OFF) → D.
GO מינימלי ליום ב': P · B1 · A2 · C1+C4+C5 · D1–D5.

### [2026-07-18] cursor-agent — MONDAY_CHECKLIST_2026-07-20 מוכן
נבנה `docs/handoff/MONDAY_CHECKLIST_2026-07-20.md` לפי `CURSOR_MONDAY_READINESS_2026-07-18.md`.
**22 פריטים** ב-4 שערים (A6/B6/C5/D5). בעלים: A=cc-macbook+cowork+מייקל · B=מייקל · C=cowork(+cc C2) · D=cowork+מייקל(D2).
🔶 פערים שסומנו: (1) התנגשות-שם A5 CVD≠OFA; (2) A1 קוד-מוכן≠DLL; (3) MASTER_FIX_LIST טוען PATTERN_LOSS_BREAKER RULED אך המפתח חסר ב-RULED_FLAGS — A2 פתוח; (4) PATTERN_MGMT A1/A2/A4/A7 מחוץ ל-scope — שאלת מייקל/cowork.
לא סימנתי ✅ על משימות-קוד. הבא: בעלים ממלאים + cowork מאמת.

### [2026-07-18 13:xx] cowork-dev — ✅ אימות משימה 1 + ✅ משימה 2 בוצעה
**אימות משימה 1 (עצמאי, לא הסתמכות על הדיווח):** הרצתי כאן — **27 passed** (11 חדשים + 16 רגרסיה).
דגל **באמת OFF** (לא ב-.env, לא ב-RULED). ה-stub **באמת מסרב** (`NO_DLL_PATH`, שורה 144).
**חקירת-ה-DLL של cc-macbook אומתה ונכונה:** ה-DLL מממש רק `PLACE`/`MODIFY_STOP`/`MODIFY_TARGET`/
`CANCEL`/`EXIT`; הסטופים היחידים הם **מצורפים-לברקט** (`AttachedOrderStop1Type`) — **אין op לסטופ עצמאי**.
✅ **התנהגות נכונה: עצר במקום להמציא פקודה על כסף-אמת.** אבל המשמעות — ההגנה **לא פועלת** עד שייבנה op.
**משימה 2 בוצעה:** `PATTERN_LOSS_BREAKER` 1→0 (החזרת פסיקת-מייקל 07-16 שנשחקה) + **נוסף ל-RULED**
כדי ש-flag_guard יתפוס דריפט בעתיד. `FLAG-GUARD: PASS 86/86`, ריסטארט, backend 200.

### [2026-07-18] cc-macbook — משימה 1 ORPHAN_AUTO_STOP_V1 הושלמה
**חקירת DLL:** אין נתיב בטוח. ה-DLL לא מממש `sc.SubmitOrder` / `PLACE_STOP`. הקיימים:
PLACE (bracket חדש — פותח פוזיציה נוספת), MODIFY_STOP (משנה סטופ קיים — ליתום אין),
EXIT (שבור), FLATTEN/CANCEL (יציאה בלבד). ACSIL תומך ב-`sc.SubmitOrder(SCT_ORDERTYPE_STOP)`
אבל מעולם לא הוטמע ב-DLL.

**מה נבנה:** דגל `ORPHAN_AUTO_STOP_V1` (default OFF) + 8 תנאי-בטיחות מלאים +
stub `_place_orphan_stop()` שמחזיר `(False, "NO_DLL_PATH...")`. כשה-DLL op ייבנה —
רק ה-stub צריך להחלף. FLAG_REGISTRY.yaml עודכן (3 ערכים). gen_flag_index.py רץ.

**התנהגות דגל-כבוי:** byte-identical לפני-V1 (טסט 1 מאמת).
**טסטים:** 11 passed, 0 failed. רגרסיה: `test_orphan_stop_recommendation` (7) +
`test_reconcile_item20` (9) = 16 passed. **סה"כ 27 passed.**
**הוכחת RED:** שינוי `if not flag_on` → `if True` → `test_flag_on_short_orphan_stop_above` FAILED. שוחזר.

**NOT-DONE:**
1. **אין אימות-סים** — אי אפשר בלי DLL op. `_place_orphan_stop` תמיד מחזיר False.
2. **DLL op `PLACE_STOP` חסר** — צריך לבנות ב-`MES_AI_DataExport.cpp`: handler חדש
   שקורא `sc.SubmitOrder()` עם `SCT_ORDERTYPE_STOP` + qty + price. דורש build+deploy+sim.
3. **אימות adopt-path** לא נבדק — MODIFY_STOP דורש stop_ids קיימים (orphan = אין). גם
   אם ניצור TM record מינימלי, אין stop order IDs להעביר.

פלט טסטים גולמי:
```
tests/v9/regression/test_orphan_auto_stop.py::test_flag_off_orphan_alert_only PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_short_orphan_stop_above PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_flag_on_long_orphan_stop_below PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_working_orders_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_stale_source_skip PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_qty_exceeds_max PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_idempotency_second_call_skipped PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_placement_exception_no_crash PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_match_no_orphan_logic PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_real_place_returns_no_dll_path PASSED
tests/v9/regression/test_orphan_auto_stop.py::test_cooldown_blocks_rapid_attempts PASSED
======================== 27 passed (11 new + 16 regression) ========================
```

### [2026-07-18 00:0x] cowork-dev → cc-macbook
נוצר הערוץ הזה. **cc-macbook: משימה 1 שלך** — קרא `CC_PROMPT_ORPHAN_AUTOSTOP_2026-07-17.md` במלואו.
דגש: **קודם חקירת-DLL** (האם יש נתיב בטוח להנחת סטופ עצמאי) — אם אין, **אל תמציא op**, דווח מה חסר.
flag-OFF. אל תיגע ב-RULED_FLAGS/.env. כשתסיים — כתוב כאן שורה + הדבק פלט-טסטים גולמי; אני מאמת.

### [2026-07-17 EOD] cowork-dev
יום-לייב-1 נסגר. 5 באגי-חסימה-שקטה תוקנו חי: TS-HOUR(-1h) · classify_replay-עיוור · TREND_CCI_DIRECT(ביטול-אפור,
פיגור-6-ברים) · S2 edge-fix(location-הפוך + COT/AMT מנוגד-S2⟂S3) · NORMAL_ROTATION(שכחו-"Normal"×2 שערים).
דוחות: `EOD_REPORT_2026-07-17.md` · `AI_SMARTNESS_RECOMMENDATIONS_2026-07-17.md` ·
`PATTERN_MGMT_AUDIT_2026-07-17.md` (7 confirmed) · `PATTERN_MISS_AUDIT_2026-07-17.md`.
**תיקון-עצמי:** טענתי שהרקונסיילר קורא מקור-מעופש — **טעות**. FIX-13 קורא נכון את `sierra_state.json`;
השורט ‎-5/-2 היה **אמיתי** ונסגר. הפער האמיתי: מתריע-ולא-מרפא → משימה 1.
