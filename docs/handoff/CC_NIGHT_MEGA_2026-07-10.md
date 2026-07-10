# CC — מגה-לילה 09→10/07: מבצע הכל + מדווח ל-Cowork

**פסיקת מייקל (22:4x, בכתב):** CC מבצע את כל התור הלילה ומדווח. השוק סגור מ-23:00 —
יש לך חופש-פעולה מלא בכפוף לשערים למטה.

## חוזה-דיווח (חדש — לפני הכל)
פתח `docs/reports/CC_NIGHT_REPORT_2026-07-10.md` ועדכן אותו **אחרי כל פאזה** (לא בסוף):
פאזה · מה בוצע · פקודה+פלט גולמי (Rule 5) · NOT-DONE · שאלות-בוקר למייקל. ‏Cowork
מבקר את הדוח בבריפינג-הבוקר — דוח חסר = הפאזה לא קרתה. בנוסף: שורת STATUS_BOARD
פר-פריט, ‏task_board.json בסיום, ‏gen_index+gen_flag_index אחרי שינויים מבניים/דגלים.

## שערים (ליל 09→10/07 בלבד)
- **ריסטארט backend: מותר** רק כש-flat + אחרי 23:00 (פסיקת מייקל מהערב). ‏snapshot לפני.
- **‏Sierra DLL reload: מותר** אחרי 23:05 (שוק סגור), עם snapshot + הוכחת-סים אחרי.
- דגלים: אסור לשנות פסוקים; דגל חדש = default-OFF + רישום REGISTRY+RULED (unset_or_0).
- ‏.env: רק בצמוד ל-snapshot; ‏flag_guard חייב PASS אחרי כל נגיעה.
- קובץ משותף שכבר נערך ע"י אחר היום (direction_context_live!) — הרץ את איחוד הטסטים.

## ההקשר (קרא לפני): docs/reports/MISSED_TRADES_2026-07-09.md + ‏STATUS_BOARD ערכי 07-09
היום: 33 מועמדים → עסקה 1 (+$117.5). ‏5 שורשים תוקנו, ‏FIX-8 פתוח, ‏2 פסיקות-בוקר.

## P0 — אמת-פריסה (ראשון, 10 דקות)
משימת-הלילה של Cowork רצה ב-22:30 (ריסטארט+אימות). ודא: ‏boot אחרי הקומיט האחרון
(‏uptime מול `git log -1 --format=%ci`), ‏flag_guard PASS 39, ‏fire_drill 🟢, והתיקונים
בקוד הרץ (0dd5792 hotfix-CERT, ‏b50b6c4 FIX-7, ‏f5da1b0 D2). אם ה-boot ישן מהקומיטים —
‏snapshot → kickstart → אימות מלא (מורשה, ראה שערים). צטט הכל בדוח.

## P1 — DECISION_REPLAY (הפריט הכי חשוב הלילה — התשובה ל"למה לא נתפס לפני")
`scripts/decision_replay.py --date YYYY-MM-DD [--env-profile current|fixed]`:
מריץ את ברי-woodies של התאריך דרך גלאי S2+S4 + **כל שרשרת שערי ה-gateway** (אותם דגלים
כמו ריצה חיה, מוזרקים; בלי סיירה, בלי DB-writes) ופולט ledger: מועמד · שעה · תבנית ·
כיוון · סטופ/יעדים שחושבו · עבר/נחסם+מי חסם. ‏KEEP/ADAPT: יש כבר classify_replay
(‏daytype_classify_routes) ו-tp_audit — אותו עיקרון, על שכבת-ההחלטה.
**ולידציה (DoD):** ‏(א) על 07-09 עם פרופיל-הקוד-הישן → משחזר את 33/1 של היום (±2);
‏(ב) עם הקוד הנוכחי → ‏≈5 ‏fires כמו הקונטרפקטואל; ‏(ג) הרץ גם 07-08 + 06-30 וצרף diff.
**חיווט לשגרה:** שלב ב-fire_drill (או סקריפט-בוקר נפרד שנקרא ממנו): כל בוקר —
‏replay של אתמול, והשוואה לירי-בפועל; פער לא-מוסבר = NO-GO. זה הביטוח שבאג-שער
לעולם לא שורד לילה.

## P2 — הצעת-היעדים מ-TP-audit (כבר הוגדר — עדכון 22:3x במגה הקודם)
טבלת T1 מוצע פר-תבנית×יום (עוגן p25-p50 של MFE, כפוף ל-TP-1) + 5 השינויים הגדולים.
לפסיקת-בוקר. בלי לגעת ב-targets.yaml.

## P3 — FIX-8 + חוב-טסט CERT
‏FIX-8: ‏EARLY_ATR_FLOOR_V1 (default OFF) — עד 14 ברי-סשן, ‏ATR14=max(חלקי,
‏ATR-סגירת-אתמול); מזין את תקרת-הסטופ, ‏cap_risk_points וסובלנות-האישור. טסט עם
פיקסטורת 16:40 האמיתית (rung1 ‏10.75 מול cap 8.22 → עם הדגל: הסטופ המבני מתקבל).
חוב-CERT: פיקסטורת 21:00 האמיתית (DOWN-גולמי → cert מרים ל-UP; ישן=DOWN).

## P4 — החייאת-הכותב (מאושר) + יישור הראפר
‏persist-on-promotion (‏main.py:475) + תיקון עצירת-הכותב במעבר PRE_MARKET→RTH +
‏/api/v9/day_type/state קורא את המקור החי. טסט: אחרי promotion יש שורה חדשה בטבלה.

## P5 — D1: ‏DLL (שוק סגור = החלון שלך)
‏(א) ‏EXIT op error=-1; ‏(ב) קיפאון last-trade price. ‏build_monolithic_cpp.sh --deploy
(auto-snapshot) → reload → הוכחת EXIT חלקי על סים + מחיר חי זז. אם Sierra לא זמינה
ללא-מייקל — NOT-DONE מפורש עם מה שכן הוכן (קוד+בילד מוכן-לפריסה).

## P6 — D4 (בר-ישן 06-09) + D5 (audit חיווט item-4/20/System6-poll) + ניקיונות
‏D2-residual: ודא שאין עוד עמודות varchar צרות בנתיב הסגירה (סריקה שיטתית של המודל).

## P7 — חבילת-בוקר (סוף הלילה)
עדכן ROADMAP_TO_LIVE.html (סעיף 07-09 + "אתה כאן") + STATUS_BOARD + task_board.json.
סכם בדוח-הלילה: טבלת פסיקות-בוקר למייקל — ‏(1) הדלקת EARLY_ATR_FLOOR_V1 ‏(2) מדיניות
auth-UNKNOWN ‏16:30-17:00 ‏(3) רצפת confirm-tol ‏(4) טבלת-היעדים ‏(5) כיול antiflap-hold
אם ה-replay מראה איחור-סיווג. ‏Cowork מריץ בבוקר: ביקורת-דוח + flag_guard + fire_drill +
‏decision_replay-של-אתמול לפני ה-GO.

**סדר: ‏P0→P1→P2→P3→P4→P5→P6→P7. פריט נתקע >45 דק' → NOT-DONE + הלאה. בהצלחה.**

## P1.5 — חוזה-הידרציה בעליית-מערכת (פסיקת מייקל 23:1x — "כל ריסטארט שובר הכל")
**העיקרון:** ריסטארט חייב לשחזר את עצמו מההיסטוריה — לא להתחיל עיוור. כל רכיב-מצב
בונה את עצמו מחדש בבוט מ-DB/קבצים של **3 הימים האחרונים כולל הברים**, ולא מחכה לנתונים חיים:

| רכיב | מקור-שחזור | קיים היום? |
|---|---|---|
| באפר ברי-Woodies (S4) | ‏v9_bars_5min_woodies אחרונים | ✓ (buf=50 — עובד) |
| ‏S1 מצב-יום (שלב, ‏opening_type, ‏IB, סיווג) | ‏replay ברי-היום דרך המסווג + ‏v9_tpo_sessions | ⚠ חלקי — one-source מחשב, אבל stage/accumulators לא משוחזרים |
| צוברי S2 ‏(COT/AMT, קונטקסט) | חישוב-מחדש מברי-היום | ✗ מתחיל ריק |
| ‏direction_context / ‏Layer-0 | חישוב-מחדש מהיום (יש cache 20s — לוודא ריצה ראשונה) | ⚠ |
| רמות-מפתח (PDH/PDL/VAH/VAL/POC אתמול-שלשום) | ‏v9_tpo_sessions ‏3 ימים | לבדוק |
| ‏daily_pnl של ה-gateway (עצירת ‏−$400!) | סכימת v9_trades סגורות-היום | ✗ מתאפס בריסטארט — **חור-סיכון: אחרי ריסטארט העצירה היומית שוכחת הפסדים** |
| ‏slots/עסקאות פתוחות | ‏rehydration קיים + ‏reconciler | ✓ לוודא |

**ביצוע:** ‏(1) ‏audit של main.py boot — טבלת רכיב×משוחזר?; ‏(2) השלם את החסרים
(דגש: ‏daily_pnl ו-S1-stage — שניהם risk-surface, בנה flag-OFF ‏BOOT_HYDRATION_V1 ופסיקת-בוקר);
‏(3) **boot-verify**: בסוף עליית-מערכת רוץ אימות שמשווה כל רכיב מול חישוב-טרי מה-DB
ומדפיס טבלת HYDRATION בלוג — פער = WARNING רועש; ‏(4) טסטים: ריסטארט-סימולציה באמצע-יום
מדומה → ‏day_type/צוברים/daily_pnl זהים לפני-ואחרי. זה סוגר את S1-STATE-PERSIST מהשורש.

## עדכון 18:0x — תקריות-לייב של 07-10 (נכנס לראש התור, לפני הכל)
**FIX-9 — איפוס-תווית בגבול-RTH:** תווית-לילה "Nontrend" גיטתה את הפתיחה עד ~17:25 (6 חסימות
playbook על ZLR). ה-one-source חייב לאפס ל-UNKNOWN ב-16:30 ולתת לשלבי-S1 לקבוע (16:45/17:00).
**FIX-10 — דחיית-אורדר = REJECTED, לא BE:** ‏337: ‏PLACE 17:55 → ‏submit-ack (8700) → דחיית-מרג'ין
בסיירה → המערכת רשמה CLOSED/BE/pnl=0. חובה: זיהוי rejection מה-DLL/activity → ‏state=CANCELLED,
outcome=REJECTED, באנר אדום, שחרור slot, אפס השפעה על counters. טסט עם התרחיש האמיתי.
**FIX-11 — FLATTEN-יתומה:** ‏DLL FLATTEN עובד רק לפי bracket-id שלו; פוזיציה ידנית/יתומה לא
נסגרת מהמערכת (הוכח 18:02 פעמיים). להוסיף אופ FLATTEN_ACCOUNT (סגירת נטו-פוזיציה ברמת חשבון).
**‏reconciler עבד מושלם** (DIVERGENCE כל 30ש') — נשאר: באנר-UI + הקפאה כמתוכנן, וגם התראה
כשה-divergence הוא פוזיציה-בלי-רשומה (orphan-adopt per SYS-3 שלב-הבא, פסיקת מייקל).
**וגם:** 337 קיבלה t1=t2=t3=7583.75 (סולם קרס לערך אחד) — לאבחן. Redis מת בריבוט (ws push) —
להוסיף redis+frontend+feeder ל-LaunchAgents. עיוורון-CERT בוויפסו (17:27-17:30) — הרחבת הפיקסטורות.

## עדכון 19:0x — FIX-12: ‏smart-BE/structure-trail לא רץ אחרי T1 אמיתי (עסקת-סים 340)
‏340 ‏SHORT 2@7596: ‏T1 מולא באמת 7587 (journal kind="T1", אורדר 8706), הרשומה עודכנה
‏HIT_TARGET — אבל אפס תזוזת-סטופ: אין SMART_BE בלוג-ניהול, אין MODIFY_STOP, ‏stop נשאר 7603.75.
**שורש מאומת בקוד (manager.py:521-523):** ‏on_target_hit רץ (state=PARTIAL), ‏BE נקרא —
אבל ‏_structure_stop_after_t1 החזיר מבנה-שורט ~7605 (סווינג-היי) שרחב מהסטופ 7603.75 →
‏never-widen → ‏return שקט. **הפער: הנפילה ל-BE+tick קורית רק כש-structure=None, לא כשהמבנה
רחב מהנוכחי.** תקן לפי כוונת-מייקל ("לקרב לכניסה... באזור המבנה"): סדר-עדיפות = המבנה
הקרוב-ביותר שהוא הדוק-מהנוכחי; אין כזה → ‏BE+tick. ‏+לוג INFO גם על no-op (SYS-2: בלי דילוגים
שקטים בנתיב-הכסף). טסט עם פיקסטורת-340 האמיתית: ‏SHORT ‏7596, סטופ 7603.75, מבנה 7605 →
חדש: סטופ זז ל-BE±tick + ‏MODIFY_STOP נשלח; ישן: כלום. וגם:
‏NAKED_STOP_SUSPECT צועק על ORDER_SUBMITTED ישן — לכייל שלא יזעק כשברקט-סטופ קיים ותקין.

## עדכון 19:2x — FIX-13: ‏DLL STATE EXPORT — "עיניים על סיירה בכל רגע" (פסיקת מייקל)
**הפתרון השורשי לכל משפחת records≠reality.** ה-DLL רואה הכל נטיבית — במקום לפרסר לוגים:
1. **‏DLL (אותו בילד של D1 הלילה):** כל ~1ש' לכתוב `sierra_state.json` אטומי (דרך אותו
   ‏promoter של Wine-rename): ‏{ts, account, is_sim, position_qty, avg_price,
   working_orders:[{id,type,buy_sell,price,qty}], last_fill_ts, buying_power אם נגיש ב-sc}.
2. **‏Backend:** ‏SierraStateReader — ה-reconciler עובר להשוות מולו (אמת בת-שנייה, בלי
   שבריריות-פרסינג); ‏endpoint ‏/api/v9/sierra_state; ה-NAKED_STOP הופך מדויק (רואים את
   רשימת-האורדרים האמיתית במקום היוריסטיקה).
3. **דשבורד:** ווידג'ט "סיירה עכשיו" ב-TopBar — ‏qty · ממוצע · ‏N אורדרים · ‏sim/live —
   מייקל רואה את אמת-סיירה בכל רגע בלי להחליף מסך.
4. **מייתר:** את תלות-הפידר בשם-קובץ-חשבון (תעלומת ה-None), את עיוורון-FLATTEN-יתומה
   (הפוזיציה גלויה), ואת רוב תרחישי 333/337/8704 של יומיים אחרונים.
‏DoD: קובץ מתעדכן ≤2ש' בסים ובאמת · ‏reconciler קורא ממנו · ווידג'ט חי · טסט E2E על סים.

## עדכון 19:4x — FIX-14 (פסיקת-דוקטרינה, מייקל 07-10): ספירת-הצדדים של Neutral = RE מכני
**הפסיקה:** "נייטרלי לפי דלתון = יום מבולגן עם פריצה משני הצדדים — בדיוק מה שהיה היום."
המחברת (DALTON_DOCTRINE.md שורות 117-118, עמ' 27-29) תומכת: ‏sides==2 לפי **Range-Extension**,
לא לפי קבלה. המסווג כיום מסנן צדדים ב"volume-accepted" → ספר 07-10 כ-sides=1 → ‏Variation
במקום Neutral. **תקן:** ספירת-צד מכנית לפי RE מעבר ל-IB, עם **סף-רעש לכיול** (הצעה:
‏RE נספר כשההרחבה ≥ max(2pt, 20%×IB) — מיישב את שני הימים: ‏07-10 ‏down 31pt/up 17.75 על IB
‏5.25 → ‏sides=2 → ‏Neutral ✓; ‏07-09 ‏down 3pt על IB ‏37 (8%) → לא נספר → ‏Variation ✓).
הסף = פסיקת-בוקר למייקל עם הצמד 07-09/07-10 כפיקסטורות-כיול. ‏DoD: ‏classify_replay על
‏07-10 → ‏Neutral_Center/Extreme (לפי הסגירה); על 07-09 → נשאר Normal_Variation; ‏S1-chat
מיושר. השפעה מעשית: ביום Neutral נפתחות עסקאות-responsive בקצוות (NEUTRAL_RESPONSIVE_V1 שכבר ON).

## עדכון 19:5x — 2 endpoints לתמיכה ב-UX (פסיקות מייקל; הפרונט אצל צ'אט-המערכות)
1. ‏GET /api/v9/s6/diagnose/{trade_id} — מריץ diagnose_trade() (System6) על עסקה פתוחה,
   מחזיר 9 אינווריאנטים ✓/✗ + שיפוט. ‏2. ‏GET /api/v9/trades/{id}/timeline — ציר-זמן מאוחד:
   ‏fills + stop_moves (cross_context audit) + management-log + חסימות. ‏FIX-15 (per-bar
   structure re-check בטרייל-הדינמי, אותה לוגיקת FIX-12 tighter-or-BE+log) — אושר ע"י מייקל.

## עדכון 20:2x — FIX-16: יעד ריאלי (פסיקת מייקל, ראיית עסקה 350) + ממצאי-פידר קשים
**FIX-16 — T1 חייב להיות ריאלי-למימוש, לא 2R עיוור.** עסקה 350 (‏ZLR LONG ‏7608.5, ‏19:44):
‏resolve_structural_targets מצא את **כל** המבנה מתחת לכניסה (‏VAH ‏7600/POC ‏7591.5/IB ‏7589;
לוג: "c2=7591.62 on wrong side of LONG entry → R-fallback") → נפל ל-2R מכני = ‏T1 ‏7617.5,
**מעל שיא-היום ~7614**, ביום שסווג Variation/נייטרלי בערב. השוואה: מועמד 19:35 קיבל מבנה
‏C1=7613.25 (הגיוני). **תקן (פסיקת מייקל):** כשאין מבנה בצד-הרווח — עוגן-T1 = ‏min(2R,
‏retest שיא/שפל-יום ± **גודל-הפריצה-הממוצע של אותו יום** (ממוצע האימפולסים מעבר לסווינג,
או p50-MFE מ-tp_audit פר-תבנית×יום)). ‏+ **הערכת-יעד פר-בר** (tighten-only, לעולם לא
להרחיק) סימטרית ל-FIX-15 — יעד שהתגלה כלא-ריאלי (מעל שיא-יום מתעדכן, מבנה חדש נוצר)
מתקרב, עם MODIFY לאורדר-היעד ב-DLL ולוג-audit ‏event=target_move+reason. טסט: פיקסטורת-350
(מבנה כולו מתחת, ‏2R מעל שיא-יום) → ‏T1 מעוגן-מבנה; ‏+ פיקסטורת 19:35 (מבנה קיים) → ללא שינוי.
**ממצאי-פידר (20:1x, ‏Cowork):** ‏(א) שני פידרים רצו במקביל (ברירת-מחדל 37138283 + ‏Sim1)
וחלקו **קובץ-offset אחד** (‏.trade_activity_offset) → קריאות-מחדש ואירועים ישנים הוזרקו
כטריים; הרגתי את פידר-האמת, נשאר פידר-סים יחיד. ‏offset חייב להיות פר-חשבון. ‏(ב) קובץ
ה-activity הסימולטיבי **לא מכיל שורות Position quantity** כמו קובץ-האמת → ‏SYS-3 עיוור-סים
מבנית; ה-DIVERGENCE שנצעק הערב על 350 = ‏false-positive מהרעלת-האירועים הישנים. זה מחזק
את FIX-13 (sierra_state.json = מקור-אמת יחיד) — ותייג account בכל אירוע-פידר ביומן.

## עדכון 21:4x — ⚠️ COWORK ביצע חלק מהתור בעצמו (פסיקת מייקל "עכשיו") — אל תבנה כפול!
**בוצע ע"י Cowork (קוד+טסטים ירוקים, ייפרס בריסטארט ≤23:00; ודא בקומיטים לפני שאתה נוגע):**
- ‏FIX-9 → ‏DAYTYPE_RTH_RESET_V1 (state_machine.process_bar; ‏4 טסטים)
- ‏FIX-10 → ‏ORDER_REJECT_DETECT_V1 (feeder ORDER_REJECT regex + ‏fill_poller._check_rejections; ‏6 טסטים, שורת-Teton האמיתית של 337)
- ‏FIX-14 → ‏DAYTYPE_SIDES_MECHANICAL_V1 + ‏NOISE_PTS/IB_FRAC (relative_features; צמד-כיול 07-09/07-10; ‏6 טסטים; ‏acceptance נשמר ל-accepted_break)
- ‏FIX-15 → ‏STOP_PERBAR_STRUCT_V1 (‏_apply_window_anchor_trail + ‏3 נקודות-חיווט בטרייל; ‏5 טסטים)
- ‏FIX-16 → ‏TARGET_REALISM_V1 (תיקון באג side-flip ב-_cap_target! + ‏realism_ceiling + שער-gateway + ‏apply_target_realism_perbar + חיווט bar_level_detector; ‏10 טסטים)
- ‏FIX-11 → אופ ‏FLATTEN_ACCOUNT ב-DLL (לא מותנה-arm) + ‏VALID_ACTIONS ב-API
- ‏FIX-13 → יצוא ‏sierra_state.json ‏~1s ב-DLL (position+orders+is_sim) + ‏reconciler מעדיף state-קובץ טרי (‏4 טסטים). מונולית מורכב (3406 שורות) — ‏**פריסת DLL ב-23:05 + הוכחת-סים = שלך/Cowork יחד**.
**נשאר לך הלילה:** ‏hydration-PG (הסרת SQLite fallback) · ‏LaunchAgents (feeder פר-חשבון+offset פר-חשבון, frontend, redis) · ‏D1-EXIT — הבהרה: דריל-ה-"SELL" של אחה"צ פגע בנתיב PLACE (ל-API אין action EXIT!) — ההוכחה האמיתית = ‏write_exit_command פנימי על סים אחרי ה-reload · ‏🆕 **באג גרירת-יעד**: ‏MODIFY_STOP הזיז סטופ 7604→7611.25 וסיירה גררה את יעד-8721 ‏7622→7629.25 (Δ זהה, שימור-אופסט) — צוד במונולית הפרוס/twconfig; היעד חייב להישאר במקומו · ‏CERT-fixtures · ‏t1=t2=t3 ladder · ‏2 endpoints ‏(s6/diagnose, timeline) · ‏NAKED_STOP calibration · ‏decision_replay של 07-10.
