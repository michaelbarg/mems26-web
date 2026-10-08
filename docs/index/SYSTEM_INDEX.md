# MEMS26 · אינדקס-המערכת (נוצר אוטומטית — `scripts/system_index.py`)

**נוצר:** 2026-10-08 06:11:37 · **HEAD:** `8f8c0eb7 2026-10-08 02:43 fix-agent 08.10 02:45: Sierra not running since 00:15 IL (exports frozen, last bar 23:55) — inbox + LIVE_CHANNEL observation, no actio` · **ענף:** `stabilize/mems26-local-truth-2026-05-16` · **קבצים לא-מקומטים:** 9784 · **עץ:** 3.4.1 · **דגלים פסוקים:** 274 (ON 216 · shadow 14 · עם measured 24 · אי-התאמה 0)

## 1 · מדיד-עכשיו (פריטים פתוחים עם צעד-מדידה, לפי חומרה) — 40

| # | סטטוס | כותרת | הצעד הבא |
|---|---|---|---|
| T-537 | 🔴 | ביקורת-השיטה (מייקל 05.10 15:10: "מפקח על מפקח על מפקח … עוד פלסתר — תבדוק האם השיטה נכונה והאם רעיון-הענפים ע | פסיקות-מייקל על סעיף 3 בדוח: (1) הקפאת הוספת-ענפים עד פרוטוקול-ולידציה מחוץ-לדגימה (walk-forward, 10 סשנים אחרונים = סט-החזקה); (2) מדידת קונפיג-ליבה (תבניות חסונות × שעה, ארבעת שערי-האיכות, חיתוך 20: |
| T-458 | 🔴 | ענפי-יום-וריאציה לביצוע (מייקל 24.09 08:00: "רוב הימים בשנה הם וריאציה או כאלה שמסתיימים ככה — עליך לדאוג שיהי | (ה) ריפליי-עדיפות-סלוט: ב-75 המקרים — מי החזיק את הסלוט ומה עשה מול מה ש-VAR_CONT היה עושה (עדיף באופן שיטתי ⇒ כלל-עדיפות בגייטוויי, מספר לפני דגל); (ו) שלב-D ביום-וריאציה (36 חסימות; במודל 21:xx n=14 |
| T-456 | 🔴 | 23.09 — "המערכת לא תפקדה טוב: לא סחרה את הפתיחה, לא זיהתה את סוג-היום, לא לקחה את העסקאות" (מייקל 22:45). הראי | (1) שער-15:30 24.09 טוען; אימות: `grep "T-451 RTH boundary" /tmp/backend.err.log` ב-16:30 + וקטור-16:45 עם `extension=none`; (2) ריפליי-רגרסיה של 23.09 בהרנס עם השומר דלוק/כבוי (התקרית = מקרה-ריפליי); |
| T-441 | 🔴 | מדידת-הצל של עץ-v2 הייתה מתה מיום לידתה — אפס שורות `TREE_SHADOW` ב-`v9_decision_vectors` (16.09→22.09: רק `BA | שבוע-מדידה (22–26.09) של v2 מול v1 מהשורות — ורק אז עמוד-ההכרעה למייקל. |
| T-426 | 🔴 | התיקון של [[T-422]] עובד — והשער זורק את התוצאה: כל מועמד-פתיחה מוקדם שנולד ממנו נחסם ב-`dalton_intent:kind`/` | (1) **להציג למייקל את השאלה האמיתית:** האם בשלב B, כשסוג-הפתיחה עדיין `OPEN_AUCTION_IN` אבל בר-אישור סגור כבר אישר דרייב, מותר `WITH_DRIVE`? זו **פסיקה**, לא באג — `config/dalton_playbook.yaml` מתיר ש |
| T-382 | 🔴 | שער-הבוקר הכריז "המרגין מכסה 5 חוזים" בעוד הפנוי מכסה  | (1) **ממתין לפסיקת-מייקל** על סגירת-הזרה מול אתי — עד אז אפס פעולה על הפוזיציה. (2) **תיקון-מדידה, בסמכות, ללא סיכון:** בכל ריצת-שער לקרוא `acct_available_funds` ו**לעולם לא** `acct_cash_balance`, ולה |
| T-353 | 🔴 | המרג'ין הפנוי אינו מממן את הגודל-הפסוק: `$448.66` פנוי מול `$1,931.00` הדרושים ל-5 חוזים ⇒ חוסר `$1,482.34`. ה | (1) **שער-15:30-16:10** — למדוד `acct_available_funds` מחדש במועד-האמת: `≥$1,931` ⇒ GO על 5; `<$1,931` ⇒ NO-GO-על-5 ומדווח במקרה (ד) עם המספר. (2) **פסיקת-מייקל נשאלה בטלפון 14.09 11:44** (מקרה ג, 323 |
| T-315 | 🔴 | נפתח-מחדש ע"י cowork 11.09 10:55 — הפריט סומן ✅ אך אימות-cowork בן 19 דקות (`d6dfdc76` ב-10:36, `docs/handoff/ | cc — (1) מבחן-רגרסיה שנכשל על `7f641a3f` ועובר על `49dcb7a7` (בר שבו מנצח-S2 נחסם **בשער** ⇒ `DOUBLE_TOP_AA` מנותב באותו בר עם `starved_by`); (2) למדוד את אותה דלתא גם על 08-03/08-04 לפני ✅. |
| T-290 | 🔴 | הספרים רשמו ‏+$30  | (1) לא לערוך את הרשומה ביד — לתקן בשורש: ב-`fill_poller` נתיב `W2 EXIT-TRACK` להתנות ייחוס `CLOSED_TRADE_PNL` לעסקה בקיום `entry_ts`/submit-ack, אחרת לסגור `CANCELLED` עם `pnl=0` ולא `WIN`. (2) להוסיף |
| T-276 | 🔴 | הירי-החי הראשון של 08.09 נדחה בשער-האחרון ולא הגיע לברוקר — `T-214` (חגורת-t3, פסיקת-מייקל 01.09) ירה בפעם הרא | (1) **למפות אילו נתיבי-`t3` קיימים ואיזה מהם נגיש לפני נעילת-IB** — `trading_gateway.py:3161 / 3229 / 3290 / 3357 / 3402` — ולקבוע בכמה מהם `OPENING_DRIVE` יכול לזכות. בלי זה לא ניתן לומר אם זו תקלה י |
| T-216 | 🔴 | `DOUBLE_TOP_AA_SHORT` נחסם שיטתית ע"י `location_gate` — 0 עסקאות-לייב אי-פעם — והשורש הוא סתירה מבנית בין סמנט | **לא להכריע על הנתונים האלה.** לבנות קודם את המדידה — `docs/handoff/SPEC_T219_SHADOW_BLOCKED_2026-09-01.md` |
| T-200 | 🔴 | `acct_available_funds` מחזיר `DBL_MAX` (1.7976931348623157e+308) — קלט-השער של T-34 הוא סנטינל "לא-זמין" שנראה | **(א) בשער-15:30 היום, לפני כל השוואה:** `if not (0 < avail < 1e12): הקלט אינו מדיד ⇒ אפס עריכה ב-.env, אפס ריסטארט, הגודל נשאר `ruled_contracts()` כפי שהוא, ומדווח למייקל בטלפון כ"מרג'ין לא-נמדד" — * |
| T-544 | 🟠 | חוסם-הלייב של 05.10 התחלף באמצע הסשן — מ | (1) **ריצת-RTH הבאה:** מה קרה ל-4 התאומים הפתוחים (3003/3004/3006/3008) — הם הופכים את המאזן להכרעה או משאירים אותו תלוי; (2) **מועמד-ריפליי צר** ([[דוקטרינת-הלמידה]] — ריפליי קודם דגל): להריץ את 10 ס |
| T-535 | 🟠 | שמונה עלים בשלים לפיצול במדידת-העץ של 05.10 (t529b, 65 סשנים, 4,398 מועמדים) — ובראשם SKIP שמרוויח: `OPEN_AUCT | (1) וריאנט ל-(1): ב-`responsive_normal` SHORT/mid_value → TAKE רק תחת `OPEN_AUCTION_IN` (או split נוסף: `structure`/`prior_zone`) — הרנס מול ייחוס; (2) (5): למדוד את עלה-S1 **עם** השערים שאחריו כפי שה |
| T-531 | 🟠 | ‏`#2913 DOUBLE_TOP_AA_SHORT` (18:45 @7773.25) ישבה 4 שעות עם מקסימום +7.5 נק׳ ונסגרה בפלטן-ה-EOD ב-−23.75$ — ש | (1) על כל עסקאות live+shadow עם ≥2 מועמדי-T1 בשרשרת — איזה T1 היה מתמלא (structure-end / step / §3 מבני) וה-$ של כל בחירה, לפי סוג-יום; (2) וריאנט-יציאה: `GRADE-A` לפני T1 ⇒ הידוק ל-BE / time-stop — ע |
| T-530 | 🟠 | קונבנציית-ORR של העץ הייתה הפוכה לשוק פעמיים ב-02.10 — `hint = היפוך-הדרייב` בשלבים A/B חסם 9 לונגים בעלייה, ו | (1) לספור ימי-`OPEN_REJECTION_REVERSE` ב-65 הסשנים — אם < ~10, לרשום "N לא מספיק" ולעצור; (2) אם מספיק: CC בונה דגל `TREE_ORR_HINT_MODE_V1` (`reverse_AB` = הנוכחי / `drive` / `reverse_until_structure` |
| T-528 | 🟠 | בר-הטריגר, לא השער: ב-02.10 הרגל הגדולה של היום לא פוספסה מחוסר-ראייה — ירינו עליה בכיוון הנכון, חמש דקות מוקד | (1) להוציא מ-`review.json` את כל המקרים שבהם **ירייה חיה והכניסה-האידיאלית נופלות על אותה רגל בהפרש ≤2 ברים** — זו קבוצה מדידה ולא סיפור יחיד; (2) למדוד בהרנס את ההפרש בין סטופ-הכניסה-שלנו לסטופ-בר-הט |
| T-527 | 🟠 | `SIERRA_FLAT` היא מחלקת-היציאה הגרועה בספרים — כל פעם שפלטן-ה-EOD של T-10 עושה את עבודתו, הכסף של אותה עסקה אי | (1) ריצת-הלילה 23:00-23:30 מריצה `broker_truth.py --since 2026-09-01 --write` ולאמת שהיא מכסה את `#2913` — אם לא, שורת "אין רישום-ברוקר ל-#2913" ב-LIVE_CHANNEL. (2) לאחר-מכן למדוד אם `broker_truth` סו |
| T-523 | 🟠 | ‏`v9_footprint_journal` לא קלט שורה אמיתית מאז `05.06` — כותב-ה-epoch נדחה ~35/דקה, ו-`max(ts)` מורעל בחותמות  | (1) **קודם כל** — לקבוע אם ריפליי-[[T-478]] קורא את היומן או את `v9_bars_footprint`; זה מפריד "רעש-לוג" מ-"הרעבת-נתון לפסיקה ממתינה", וזהו גם סעיף (5) של T-521. (2) התיקון בצד-**הקורא**, כמו ב-T-414:  |
| T-514 | 🟠 | אחרי שני הפסדי-הלייב של 28.09 (−95$ ברוקר) — ארבעה "תיקונים" נמדדו יום-כולל מול העץ החי 3.1.0 (61 סשנים כולל 2 | שני גלאים חדשים ולא כוונון — (1) שבירת-IB עם ווליום אחרי שעה-ראשונה צרה (28.09 17:35: −35 נק׳); (2) חזרה חדה לתוך ה-IB אחרי שבירה כושלת (28.09 19:15: +43 נק׳, הלונגים נדחו ב-tree:bias) — כל אחד ⇒ וריא |
| T-512 | 🟠 | לעץ אין שורת-דוקטרינה לנתיב `opening_type=OPEN_AUCTION_IN/phase=D/day_type=*(Neutral_Center)` — ולכן  | (1) **מקרה-ריפליי, לא דגל** (דוקטרינת-הלמידה 09.09: "הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל") — להוסיף את הנתיב `OPEN_AUCTION_IN/phase=D/Neutral_Center` לסט-הרגרסיה ולמדוד את הדלתא של ארבעת המועמדים האל |
| T-498 | 🟠 | שער אישור-הכניסה (`S4_ENTRY_CONFIRM_V1`) בודק בלייב לפעמים בר שנפתח לפני שניות — מרוץ בין כתיבת-שורת-הבר לבין  | אחרי הריסטארט של ב׳: כל `BLOCKED by entry-confirm` מצטט `o/c` של הבר **הסגור** הקודם (להשוות לשורת-הבר ב-DB); ובריפליי-הלילה של ב׳ — ריפליי ולייב מסכימים על השער. |
| T-493 | 🟠 | ריפליי התצורה החיה (עץ-V3 מחליט, נטען 25.09 19:15) על 61 הסשנים הנקיים + ביקורת כל נתיב בעץ (מייקל 27.09 14:14 | להכניס ללולאה-הלילית (תוכנית §6 שלב 6): אחרי EOD — ריפליי-היום בתצורה החיה + `gate_audit.py` + `tree_measure.py`; כל נתיב חדש שמסרב לכסף או מפסיד ⇒ וריאנט ⇒ יום-כולל. |
| T-484 | 🟠 | פסיקת-מייקל התקבלה: להדליק את ענף-הצל `auction_B_trend_break` חי — "כן" (25.09 14:11:49Z, `[56436c0f]`), בתשוב | ✅ **נסגר בריצה 12 (שער-15:30, cowork-dev 25.09 16:00) — מייקל לא נדרש ללחוץ על כלום.** המרוץ אושר במדידה: `.env` mtime `15:44:06` מול `[boot] … pid=87958` ב-`15:44:05` ⇒ הבוט הראשון קרא `shadow` (‏`tr |
| T-463 | 🟠 | `BarLevelDetector.on_bar` זורק `InvalidTransition: CLOSED -> CLOSED` כששני יעדים נפגעים באותו בר — והחריגה מפי | **(1)** **מקרה-ריפליי** על `24.09 09:40 ET` בסט-הרגרסיה — דוקטרינת-הלמידה: תקרית ⇒ ריפליי, **לא דגל**. המקרה חייב לשחזר שני יעדים על בר אחד. **(2)** לקרוא אם הלולאה ב-`on_bar` צריכה `try/except` **פר- |
| T-460 | 🟠 | `mfe_pts` בפלט-ההרנס סותר את עצמו ב-5 מתוך 10 רשומות שנבדקו — מדווח תנועה-לטובתנו גדולה מהמרחק ל-T1, בזמן ש-T1 | לאתר את חישוב `mfe_pts` בקוד-ההרנס ולבדוק חלון-זמן וסימן (חשד: מחושב על הסשן כולו ולא על תקופת-ההחזקה); מקרה-רגרסיה: עסקה שיצאה ב-STOP חייבת לקיים `mfe_pts < t1_pts`. |
| T-425 | 🟠 | אותו שורש של [[T-422]], שני צרכנים נוספים: `_oe_bars` הוא רשימת-snapshots קפואים, ו-`get_opening_dir_fusion` + | (1) **אין לתקן בלי פסיקה + מספר-ריפליי.** בניגוד ל-[[T-422]] — ששם הכלל "בר-אישור = בר סגור" כבר פסוק והתיקון רק החזיר את הקוד לדוקסטרינג שלו — כאן שינוי המקור **משנה אילו טריגרים נורים ואיזה כיוון עו |
| T-415 | 🟠 | [הורד מ-🔴 ב-18.09 12:14 — פסיקת-מייקל 12:05 הורידה את הגודל-הפסוק לחוזה אחד, והפער חדל לחסום. הצעד-הבא: אימות  | (1) **למדוד מחדש** את `acct_available_funds` מ-`sierra_state.json` לפני `fire_drill` — היתרה עשויה להשתנות בן-לילה; **אל תסתמך על `490.64`**. (2) אם עדיין `< 772.40` ⇒ זו **הכרעת-מייקל בלבד** (מקרה ד  |
| T-412 | 🟠 | דיוק REACTIVE/INITIATIVE עם ראיות (מייקל 17.09 19:20: "לבחון על התבניות שלנו ולדייק, לא לבנות מחדש"). | `evidence.py` + ראיות בתוך `_detect_reactive/_detect_initiative` תחת `S2_TRIGGER_QUALITY_V1=shadow` (ברירת-מחדל בקוד) · ריפליי מתוקן + הרנס 5 סשנים ⇒ פסיקת-מייקל להדלקה. **מה שאינו נטען:** N=8-12 בתאי |
| T-390 | 🟠 | וקטור-מצב (`SituationVector`) מחושב פעם אחת בשער לכל בר-החלטה ונרשם ל-`v9_decision_vectors` — גם כשאף מפיק לא  | cowork כותב `CC_NOW_2026-09-17_T390_SITUATION_VECTOR.md` אחרי דוח-T-389 (השדות נגזרים ממנו). קריטריון: התנהגות-זהה על 15.09+11.09 בהרנס (מחוץ ל-RTH), guards ירוקים. |
| T-385 | 🟠 | הספרים והברוקר חולקים על אותה עסקה — `$11.25` על `#1647`, והשורש הוא שהספרים רשמו את מחיר-האות כמחיר-המילוי. | (1) **לא תוקן בכוונה, ומסיבה:** זו שכבת-מדידה בנתיב-הכניסה של `TradeManager`, ושינוי קוד באמצע `RTH` אינו בסמכות-ניטור (§4 של `COWORK_DAILY_READ`) ⇒ לתיקון אחרי הפעמון או ל-cc. (2) **הכיוון המוצע (לא  |
| T-367 | 🟠 | תיקון-שורש ל-[[T-359]]: הרקונסיילר משווה `TM` מול מקור נעול-לסימבול-הצ'ארט ⇒ גלגול-חוזה משחרר את `T-43` על מקו | **לא לגעת לפני סגירת-הפתיחה של היום.** אחריה — cc קורא את `backend/v9/services/sierra_position_reconciler.py`, מציע את מקור-ההשוואה ברמת-חשבון, ומביא ריפליי/סים שמוכיח ש-`T-43` **אינו** משתחרר על גלגו |
| T-352 | 🟠 | `17,583` שורות `ERROR` ביום-א' שוק-סגור, כולן חתימה אחת — `TS-OFFSET-GATE`; ו-`53,522` מ-`67,953` שורות-הלוג ש | (1) **למדוד מחדש אחרי `01:00 IL`** כשברים טריים מגיעים: אם הזרם **נעצר** — זו תופעת-שוק-סגור וסוגרים את הפריט; אם **נמשך** — זו מחלקה חדשה ולא סוף-שבוע, והיא שייכת ל-[[T-164]]. (2) **עד אז — להתייחס ל |
| T-348 | 🟠 | ‏`21.4%` מהפסדי-הצל נחתכים ע"י כלל-סדר-הבדיקה ולא ע"י השוק — הבר שסגר אותם בסטופ נגע גם ב-`T1`. | (דוקטרינת-הלמידה: "הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל"): (1) ריפליי דקה/טיק על `116` הברים הדו-משמעיים ⇒ להוציא **מספר**: בכמה מהם `T1` נגע לפני הסטופ; (2) עד שיש מספר — **אין לגעת ב-`bar_level_dete |
| T-339 | 🟠 | הוראת-מייקל 11.09 `20:24:48` (‏`id=65774fa6` בת'רד-הטלפון): "אם אני סוגר את העסקה תנסה לעשות במחיר הטוב ביותר  | **(1) ההבהרה היחידה שנדרשת ממייקל, במשפט אחד:** האם "אני סוגר" = **אתה ביד ב-Sierra** (ואז ההוראה היא בעצם בקשה שהמערכת **לא** תשטח מתחתיך — כלומר [[T-338]], והתשובה שם), או = **אתה אומר למערכת לסגור* |
| T-321 | 🟠 | שער-המיקום של `DAYTYPE_LOCATION_GATE` ירה בלייב לראשונה היום — ו-13 מ-13 החסימות הן בצירופים שהדוקטרינה  | (1) **המדידה המכריעה, לפני כל דגל** ([[LEARNING_DOCTRINE]] — הוראה ⇒ קודם ריפליי): לספור על סט-הרגרסיה את **חיתוך (kinds מותרים)×(מפיקים חיים)** — כמה מועמדים **נולדו** ב-`near_vah×SHORT` / `near_val× |
| T-306 | 🟠 | צד-הסטופ בחשבון-המשותף מחזיק 8 חוזים מול פוזיציה של 5 — עודף של 3 — אחרי שאתי ירדה מ-5 חוזים ל-1 בלי לכווץ את  | ✅ **הוכרע במדידה ולא ב-Trade DOM** — `11114` היה **חי**; אם חי, לכווץ אותו ל-1 (זו פקודה שלו/של אתי — **אנחנו לא נוגעים**). **(2)** cowork — לחזור על סכימת-`qty`-לפי-צד בכל ריצת-ניטור כל עוד הפוזיציה  |
| T-286 | 🟠 | השער בחר שורת-פלייבוק לפי תווית סוג-יום בת ~10 דקות — פיגור שני ברים בין `v9_day_type_state` ל-`get_live_day_t | למדוד את הפיגור, לא לכוונן אותו — לקרוא את שכבת ה-antiflap ב-`trade_context.get_live_day_type` ולענות **בשתי שורות**: (א) כמה ברים היא מחזיקה תווית ישנה ובאיזה תנאי, (ב) האם זה מכוון (יש פסיקה/`measur |
| T-285 | 🟠 | הכיוון צדק וההצבה לא — שתי עסקאות-לייב SHORT של 08.09 היו בכיוון-היום ובהסכמה מלאה עם צל-S1DayDir, ונעצרו לפני | להוסיף את 1224/1231/1262 כ**מקרי-ריפליי** לסט-הרגרסיה (דוקטרינת-הלמידה: תקרית ⇒ מקרה-ריפליי, לא דגל), ולמדוד את עוגן-הסטופ **פר-סוג-יום** — לא גלובלית, כי הריפליי הגלובלי כבר נדחה. אין שינוי-התנהגות ע |
| T-277 | 🟠 | הספרים והברוקר נושאים מחירי-ברקט שונים על עסקת-הלייב הפתוחה `#1231` — הזזה מסודרת פר-חוזה, לא רעש-עיגול. | (1) **לתפוס את המטען הגולמי לפני שהוא נמחק** — הנתיב היחיד להכרעה: להוסיף שמירת-עותק של `cmd_*.json` (או לוג של המטען) לפני ה-ACK, או לקרוא את הצד השני מהיומן של סיירה. בלי זה השאלה בלתי-מדידה גם בעסק |

## 2 · מפיקים (DECISION ב-30 הימים האחרונים)

| תבנית | מערכת | החלטות | עברו-עץ+שערים | ירי-לייב | P&L לייב | live-capable | מפסק | 3 התוצאות הנפוצות |
|---|---|---|---|---|---|---|---|---|
| ZLR | 4 | 591 | 170 | 0 | 0.0 | False | `ZLR_SHADOW_V1` | tree:stand_down 174 · (passed) 170 · tree:location 96 |
| CEILING_FLIP_TOUCH2 | 2 | 388 | 201 | 2 | -137.5 | False | `CEILING_FLIP_TOUCH2_V1` | (passed) 201 · dalton_intent:stand_down 48 · tree:stand_down 45 |
| REACTIVE_SHORT | 2 | 70 | 3 | 0 | 0.0 | True | `live producer` | tree:stand_down 61 · (passed) 3 · tree:bias 2 |
| GHOST | 4 | 49 | 17 | 5 | -93.75 | True | `live producer` | (passed) 17 · tree:stand_down 10 · dalton_intent:stand_down 8 |
|  | 4 | 40 | 3 | 0 | 0.0 | True | `live producer` | dalton_intent:stand_down 18 · tree:stand_down 12 · dalton_intent:bias 9 |
| INITIATIVE_LONG | 2 | 37 | 9 | 3 | 5.0 | True | `live producer` | (passed) 9 · tree:bias 8 · tree:stand_down 7 |
| GB100 | 4 | 36 | 8 | 4 | -25.0 | True | `live producer` | dalton_intent:stand_down 9 · (passed) 8 · tree:bias 5 |
| TREND_STEP | 4 | 31 | 9 | 0 | 0.0 | False | `TREND_STEP_ENTRY_V1` | (passed) 9 · tree:location 8 · dalton_intent:stand_down 3 |
| DOUBLE_BOTTOM_EE_LONG | 2 | 31 | 4 | 2 | 102.5 | True | `live producer` | tree:bias 7 · dalton_intent:stand_down 6 · tree:stand_down 5 |
| DOUBLE_BOTTOM_EE | 4 | 30 | 0 | 0 | 0.0 | True | `live producer` | tree:stand_down 15 · variation_mid_value 12 · dalton_intent:stand_down 3 |
| FAMIR | 4 | 30 | 8 | 3 | -17.5 | True | `live producer` | tree:stand_down 10 · tree:bias 9 · (passed) 8 |
| REACTIVE_LONG | 2 | 28 | 6 | 4 | 10.0 | True | `live producer` | tree:stand_down 6 · (passed) 6 · tree:bias 6 |
| S2_DELTA_DBL_SHORT | 2 | 25 | 7 | 0 | 0.0 | False | `S2_DELTA_DBL_V1` | (passed) 7 · tree:location 6 · dalton_intent:bias 6 |
| CONFLUENCE_RI_ZLR | 4 | 20 | 0 | 0 | 0.0 | True | `CONFLUENCE_RI_ZLR_LIVE` | tree:stand_down 20 |
| DOUBLE_TOP_AA_SHORT | 2 | 19 | 8 | 3 | 7.5 | True | `live producer` | (passed) 8 · tree:location 4 · tree:bias 3 |
| FAILED_RE_IB | 2 | 17 | 2 | 0 | 0.0 | False | `RE_ACCEPTANCE_V1` | tree:stand_down 4 · dalton_intent:bias 3 · tree:location 3 |
| CEILING_FLIP_SHORT | 2 | 16 | 10 | 3 | -72.5 | True | `CEILING_FLIP_SHORT_V1` | (passed) 10 · dalton_intent:stand_down 3 · tree:location 2 |
| CEILING_FLIP_LONG | 2 | 15 | 12 | 4 | -56.25 | True | `CEILING_FLIP_SHORT_V1` | (passed) 12 · dalton_intent:bias 1 · tree:location 1 |
| INITIATIVE_SHORT | 2 | 14 | 6 | 5 | -371.25 | True | `live producer` | (passed) 6 · tree:bias 4 · tree:time_cutoff 2 |
| HTLB | 4 | 12 | 2 | 0 | 0.0 | True | `live producer` | tree:bias 5 · dalton_intent:stand_down 3 · (passed) 2 |
| FAILED_BREAK_LONG | 2 | 11 | 2 | 0 | 0.0 | False | `failed_break.py: shadow_only by code` | tree:stand_down 4 · dalton_intent:stand_down 3 · (passed) 2 |
| VA_FADE_SHORT | 2 | 10 | 4 | 0 | 0.0 | False | `va_fade.py: shadow_only by code` | (passed) 4 · tree:bias 3 · tree:kind 1 |
| FAILED_BREAK_SHORT | 2 | 10 | 4 | 0 | 0.0 | False | `failed_break.py: shadow_only by code` | (passed) 4 · tree:stand_down 2 · tree:location 2 |
| VEGAS | 4 | 9 | 1 | 2 | -73.75 | True | `live producer` | tree:location 2 · dalton_intent:stand_down 2 · tree:bias 2 |
| VA_FADE_LONG | 2 | 9 | 4 | 0 | 0.0 | False | `va_fade.py: shadow_only by code` | (passed) 4 · tree:bias 3 · tree:location 1 |
| DALTON_EDGE_LONG | 2 | 8 | 3 | 1 | 28.75 | True | `DALTON_EDGE_V1` | (passed) 3 · tree:stand_down 1 · tree:bias 1 |
| OPENING_DRIVE | 2 | 7 | 5 | 5 | -77.5 | True | `OPENING_ENTRY_V1` | (passed) 5 · dalton_intent:bias 1 · tree:kind 1 |
| OPENING_EXTREME_REJECT | 2 | 7 | 4 | 1 | -61.25 | True | `OPENING_ENTRY_V1` | (passed) 4 · dalton_intent:kind 2 · tree:location 1 |
| S2_DELTA_DBL_LONG | 2 | 7 | 3 | 0 | 0.0 | False | `S2_DELTA_DBL_V1` | (passed) 3 · tree:location 3 · dalton_intent:bias 1 |
| DALTON_EDGE_SHORT | 2 | 6 | 2 | 1 | 46.25 | True | `DALTON_EDGE_V1` | (passed) 2 · dalton_intent:stand_down 1 · tree:time_cutoff 1 |
| REACTIVE | 4 | 6 | 0 | 0 | 0.0 | True | `live producer` | tree:stand_down 5 · dalton_intent:stand_down 1 |
| OPENING_PULLBACK_CONT | 2 | 5 | 0 | 0 | 0.0 | True | `OPENING_ENTRY_V1` | tree:kind 3 · dalton_intent:kind 1 · tree:bias 1 |
| BULL_FLAG_LONG | 2 | 4 | 2 | 2 | -131.25 | True | `live producer` | (passed) 2 · tree:stand_down 2 |
| STRATEGIC | 2 | 4 | 0 | 0 | 0.0 | True | `live producer` | tree:stand_down 4 |
| TT | 4 | 2 | 0 | 0 | 0.0 | True | `live producer` | tree:location 1 · dalton_intent:bias 1 |
| OPENING_TEST_DRIVE | 2 | 2 | 2 | 1 | 127.5 | True | `OPENING_ENTRY_V1` | (passed) 2 |
|  | 2 | 2 | 0 | 0 | 0.0 | True | `live producer` | dalton_intent:stand_down 18 · tree:stand_down 12 · dalton_intent:bias 9 |
| OPENING_ORR | 2 | 1 | 1 | 0 | 0.0 | True | `OPENING_ENTRY_V1` | (passed) 1 |
| RE_ACCEPTANCE | 2 | 1 | 0 | 0 | 0.0 | False | `RE_ACCEPTANCE_V1` | tree:stand_down 1 |

## 3 · שערים (blocked_by, 30 יום)

| שער | n |
|---|---|
| `(passed)` | 522 |
| `tree:stand_down` | 398 |
| `dalton_intent:stand_down` | 206 |
| `tree:location` | 169 |
| `tree:bias` | 134 |
| `dalton_intent:bias` | 77 |
| `tree:time_cutoff` | 53 |
| `tree:kind` | 25 |
| `dalton_intent:kind` | 14 |
| `variation_mid_value` | 12 |

## 4 · העץ (3.4.1)

עלים: 611 · TAKE 339 · SKIP 272 · SHADOW 0 · עלים עם פסיקה+מדידה: 202

| עלה | סשנים | $ | $ נטו | תאריך |
|---|---|---|---|---|
| `time_cutoff` | 65 | 88.75 | 104.35 | 2026-10-06 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=*/rel_bias=against/edge=failed_extension` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=A/day_type=*/rel_bias=*/kind=*/edge=failed_extension` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme/dire` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=*/rel_bias=against/edge=failed_extension` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=B/day_type=*/rel_bias=*/kind=*/edge=failed_extension` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=against/edg` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind=PULL` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind=*/ed` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=against/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=*/kind=B` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=*/kind=*` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=two_sided/direction=LONG/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=two_sided/direction=SHORT` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=*/direction=LONG/zone=unk` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=*/direction=SHORT/zone=un` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Neutral_Center/direction=LONG/zone=unknown` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Neutral_Center/direction=SHORT/zone=unknow` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=LONG/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=SHORT` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=Normal|Neutral_Center|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=*/rel_bias=against/edge=failed_extens` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=B/day_type=*/rel_bias=*/kind=*/edge=failed_exten` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=agains` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Variation|Normal_Variation/pattern=*/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=aga` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=*/k` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=up|down/rel_bias=*/k` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=two_sided/direction=` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=two_sided/direction=` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=*/direction=LONG/zon` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Normal/structure=*/direction=SHORT/zo` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Neutral_Center/direction=LONG/zone=un` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Neutral_Center/direction=SHORT/zone=u` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_TEST_DRIVE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=Normal|Neutral_Center|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*/rel_bias=against/edge=failed` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*/rel_bias=*/kind=*/edge=faile` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation|Normal_Variation/pat` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation|Normal_Variation/pat` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation|Normal_Variation/pat` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=up|down/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=up|down/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=up|down/rel_b` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=two_sided/dir` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=two_sided/dir` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=*/direction=L` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=*/direction=S` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Neutral_Center/direction=LONG/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Neutral_Center/direction=SHORT` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Neutral_Extreme/rel_bias=*/dir` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Neutral_Extreme/rel_bias=*/dir` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `auction_B_reversal` | 60 | 105.55 | 69.15 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=B/day_type=Normal|Neutral_Cente` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `auction_B_reversal` | 60 | 105.55 | 69.15 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=B/day_type=Normal|Neutral_Cente` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `auction_B_trend_break` | 58 | 101.25 | 83.05 | 2026-09-25 |
| `auction_B_reversal` | 60 | 105.55 | 69.15 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=B/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `auction_B_reversal` | 60 | 105.55 | 69.15 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=B/day_type=*/kind=*/edge=failed` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Variation|Normal_Var` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Variation|Normal_Var` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Variation|Normal_Var` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=up|` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=up|` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=up|` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=two` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=two` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=*/d` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Normal/structure=*/d` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Neutral_Center/direc` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Neutral_Center/direc` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Neutral_Extreme/rel_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=C/day_type=Neutral_Extreme/rel_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=D/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=D/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=OPEN_AUCTION_IN|OPEN_AUCTION_OUT/phase=D/day_type=Trend_Normal|Trend_D` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=against/edge=failed_` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind=PULLBACK|BREA` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Trend_Normal|Trend_DD/rel_bias=*/kind=*/edge=failed` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_bias=again` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_bias=*/kin` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Variation|Normal_Variation/pattern=*/rel_bias=*/kin` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=up|down/rel_bias=against/edge=fail` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=up|down/rel_bias=*/kind=BREAK|VALU` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=up|down/rel_bias=*/kind=*/edge=fai` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=two_sided/direction=LONG/zone=unkn` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=two_sided/direction=SHORT/zone=unk` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=*/direction=LONG/zone=unknown/kind` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Normal/structure=*/direction=SHORT/zone=unknown/kin` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Neutral_Center/direction=LONG/zone=unknown/kind=*/e` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Neutral_Center/direction=SHORT/zone=unknown/kind=*/` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `take_with_extension` | 58 | -85.0 | None | 2026-09-24 |
| `hour=*/opening_type=*/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=LONG/zone=unkn` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=C/day_type=Neutral_Extreme/rel_bias=*/direction=SHORT/zone=unk` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `take_failed_ext_responsive` | 65 | 400.0 | 371.4 | 2026-10-03 |
| `hour=*/opening_type=*/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_bias=agai` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_bias=*/ki` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `hour=*/opening_type=*/phase=D/day_type=Trend_Normal|Trend_DD|Neutral_Extreme/rel_bias=*/ki` | 60 | 166.25 | 163.65 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |
| `d_with_extension` | 60 | 160.0 | 110.6 | 2026-09-27 |

## 5 · דגלים פסוקים (RULED_FLAGS ↔ .env)

| דגל | צפוי | בפועל | ✓ | פסק | תאריך | measured |
|---|---|---|---|---|---|---|
| `APP_STATE_ROOT_FIX_V1` | shadow | shadow | ✓ | מייקל | 2026-08-26 |  |
| `AUTH_LOWCONF_REDUCED_V1` | 1 | 1 | ✓ | מייקל | 2026-07-30 |  |
| `BAR_SEAM_REJECT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `BE_AFTER_REAL_T1_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `BLOCKED_TWIN_V1` | shadow | shadow | ✓ | מייקל | 2026-09-03 |  |
| `BOOT_DAYTYPE_REPLAY_V1` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `BOOT_HYDRATION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `C4_RULING6_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `C4_TREND_FLATTEN_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `CANDIDATE_LEDGER_V1` | 1 | 1 | ✓ | מייקל | 2026-08-25 |  |
| `CEILING_FLIP_SHORT_V1` | 1 | 1 | ✓ | מייקל | 2026-09-11 | ✓ |
| `CEILING_FLIP_TOUCH2_V1` | shadow | shadow | ✓ | מייקל | 2026-09-15 | ✓ |
| `CEILING_FLOOR_STATE_V1` | shadow | shadow | ✓ | מייקל | 2026-08-28 |  |
| `CHASE_MIN_SESSION_BARS` | 8 | 8 | ✓ | מייקל | 2026-08-11 |  |
| `COLD_START_GUARD_V1` | 1 | 1 | ✓ | מייקל | 2026-08-11 |  |
| `CONFLUENCE_RI_ZLR_LIVE` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `CONFLUENCE_RI_ZLR_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `CONT_TREND_FILTER` | 1 | 1 | ✓ | מייקל | 2026-07-07 |  |
| `CONT_TREND_FILTER_FULL_SCOPE` | unset_or_0 |  | ✓ | מייקל | 2026-08-28 |  |
| `CONT_TREND_STATE_CERT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `DALTON_EDGE_COMPASS_EXEMPT_V1` | 1 | 1 | ✓ | מייקל | 2026-08-28 |  |
| `DALTON_EDGE_V1` | live | live | ✓ | מייקל | 2026-08-28 |  |
| `DALTON_PLAYBOOK_V1` | 1 | 1 | ✓ | מייקל | 2026-09-09 |  |
| `DAYTYPE_ACCEPTANCE_DEMOTION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `DAYTYPE_ANTIFLAP_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `DAYTYPE_BOOT_SEED_CANONICAL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `DAYTYPE_ENTRY_BUDGET_V1` | 0 | 0 | ✓ | מייקל | 2026-08-21 |  |
| `DAYTYPE_HONEST_PRELOCK_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `DAYTYPE_LOCATION_GATE` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `DAYTYPE_ONE_SOURCE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `DAYTYPE_PATTERN_AWARE_V1` | 1 | 1 | ✓ | מייקל | 2026-06-30 |  |
| `DAYTYPE_PLAYBOOK` | 1 | 1 | ✓ | מייקל | 2026-06-19 |  |
| `DAYTYPE_POSITION_GATE` | 0 | 0 | ✓ | מייקל | 2026-07-01 |  |
| `DAYTYPE_RECLASS_STABILITY_V1` | 1 | 1 | ✓ | מייקל | 2026-09-10 |  |
| `DAYTYPE_RTH_RESET_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `DAYTYPE_SIDES_MECHANICAL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `DAY_DIRECTION_STRUCTURAL_V1` | 0 | 0 | ✓ | מייקל | 2026-08-25 |  |
| `DECISION_TREE_V3` | 1 | 1 | ✓ | Michael | 2026-09-25 | ✓ |
| `DELTA_BREAKOUT_RELEASE_V1` | shadow | shadow | ✓ | מייקל | 2026-09-06 |  |
| `DELTA_FEATURES_V1` | 1 | 1 | ✓ | מייקל | 2026-08-02 |  |
| `DIRECTION_COMPASS_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `DIRECTION_CONTEXT` | 0 | 0 | ✓ | מייקל | 2026-08-28 |  |
| `DOUBLE_TOP_ADAM_FIX_V1` | 1 | 1 | ✓ | מייקל | 2026-08-23 |  |
| `EARLY_ATR_FLOOR_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `EDGE_ENTRY_LOCATION_FIX_V1` | 1 | 1 | ✓ | מייקל | 2026-09-02 |  |
| `EDGE_FADE_TARGETS_V1` | unset_or_0 |  | ✓ | מייקל | 2026-09-14 | ✓ |
| `ELQ_LEG_FROM_BREAK_V1` | 1 | 1 | ✓ | מייקל | 2026-09-06 |  |
| `ENTRY_BUDGET_QUALITY_V1` | 1 | 1 | ✓ | מייקל | 2026-08-21 |  |
| `ENTRY_BUDGET_SKIP_LOSERS_V1` | 1 | 1 | ✓ | מייקל | 2026-08-21 |  |
| `ENTRY_CONFIRM_TOL_MIN_PTS` | 0.5 | 0.5 | ✓ | מייקל | 2026-07-10 |  |
| `ENTRY_GUARD_OWNERSHIP_V1` | 1 | 1 | ✓ | מייקל | 2026-08-26 |  |
| `ENTRY_LOCATION_QUALITY_V1` | 1 | 1 | ✓ | מייקל | 2026-08-28 |  |
| `EOD_CLOSE_T10_V1` | 1 | 1 | ✓ | מייקל | 2026-08-24 |  |
| `EOD_FLATTEN_V1` | 1 | 1 | ✓ | מייקל | 2026-07-07 |  |
| `EOD_RISK_WINDOW_V1` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `EXCESS_COUNTER_ENTRY_V1` | 1 | 1 | ✓ | מייקל | 2026-08-11 |  |
| `EXIT_TRACK_ACTIVITY_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `EXIT_VERIFY_V1` | 1 | 1 | ✓ | מייקל | 2026-08-15 |  |
| `EXTREMES_AWARE_REALIZE_V1` | 1 | 1 | ✓ | מייקל | 2026-08-06 |  |
| `EXTREME_CHASE_GUARD_V1` | 1 | 1 | ✓ | מייקל | 2026-07-23 |  |
| `EXTREME_CHASE_SCOPE` | CONT | CONT | ✓ | מייקל | 2026-08-11 |  |
| `FAILED_BREAK_VA_V1` | shadow | shadow | ✓ | מייקל | 2026-08-26 |  |
| `FAILED_RE_IB_V1` | shadow | shadow | ✓ | מייקל | 2026-09-07 |  |
| `FEED_WATCHDOG` | 1 | 1 | ✓ | מייקל | 2026-07-14 |  |
| `FIXED_CONTRACTS_1` | 1 | 1 | ✓ | מייקל | 2026-09-18 | ✓ |
| `FIXED_CONTRACTS_2` | 0 | 0 | ✓ | מייקל | 2026-09-18 | ✓ |
| `FIXED_CONTRACTS_3` | 0 | 0 | ✓ | מייקל | 2026-09-16 |  |
| `FIXED_CONTRACTS_4` | 0 | 0 | ✓ | מייקל | 2026-08-25 |  |
| `FIXED_CONTRACTS_5` | 0 | 0 | ✓ | מייקל | 2026-09-15 |  |
| `FIXED_CONTRACTS_6` | 0 | 0 | ✓ | מייקל | 2026-08-25 |  |
| `FOOTPRINT_DISABLED` | 0 | 0 | ✓ | Michael | 2026-09-25 | ✓ |
| `FRESH_EXTREME_GATE_V1` | 0 | 0 | ✓ | מייקל | 2026-09-14 | ✓ |
| `FRESH_EXTREME_MIN_BARS` | 3 | 3 | ✓ | מייקל | 2026-09-14 |  |
| `IB_BARS_VALIDATE_V1` | 1 | 1 | ✓ | מייקל | 2026-08-14 |  |
| `IB_BREAK_ANY_EXPANSION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `IB_RETURN_HINT_RELEASE_V1` | returning | returning | ✓ | מייקל | 2026-09-30 | ✓ |
| `IB_RETURN_RELEASE_FLOW` | unset_or_0 |  | ✓ | cowork | 2026-09-30 | ✓ |
| `LAYER0_CHOP_GATE` | unset_or_0 |  | ✓ | מייקל | 2026-06-08 |  |
| `LEGACY_CONF_GATES` | unset_or_0 |  | ✓ | מייקל | 2026-08-26 |  |
| `LEG_EXEMPT_LSMA_FLAT_V1` | 1 | 1 | ✓ | מייקל | 2026-08-11 |  |
| `LEG_RIDE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-31 |  |
| `LIVE_EXECUTION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-06 |  |
| `LIVE_LEDGER_V1` | 1 | 1 | ✓ | מייקל | 2026-07-08 |  |
| `LOCAL_ALERTS_V1` | 0 | 0 | ✓ | מייקל | 2026-07-27 |  |
| `LSMA_FLAT_ATR_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `LSMA_FLAT_GATE_V1` | 0 | 0 | ✓ | מייקל | 2026-08-28 |  |
| `LSMA_SUSTAIN_BARS` | 2 | 2 | ✓ | מייקל | 2026-07-15 |  |
| `MANUAL_CANCEL_DETECT_V1` | unset_or_0 |  | ✓ | מייקל | 2026-07-20 |  |
| `MANUAL_FLATTEN_V1` | 1 | 1 | ✓ | מייקל | 2026-07-15 |  |
| `MANUAL_GUARD_AUTOPROTECT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `MANUAL_POSITION_GUARD_V1` | 1 | 1 | ✓ | מייקל | 2026-07-25 |  |
| `MARGIN_AWARE_SIZING_V1` | 1 | 1 | ✓ | מייקל | 2026-08-19 |  |
| `MARKET_CONTEXT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `MEMS_MAX_RISK_POINTS` | 60 | 60 | ✓ | מייקל | 2026-07-02 |  |
| `MEMS_MIN_RISK_POINTS` | 2 | 2 | ✓ | מייקל | 2026-07-02 |  |
| `MORNING_LABEL_CONFIRM_V1` | 0 | 0 | ✓ | מייקל | 2026-08-25 |  |
| `NEUTRAL_RESPONSIVE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-08 |  |
| `NEVERFADE_TREND_ONLY_V1` | 1 | 1 | ✓ | מייקל | 2026-07-23 |  |
| `NEWS_BLACKOUT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `NORMAL_ROTATION_FIX_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `NO_LABEL_NO_FIRE_V1` | 1 | 1 | ✓ | מייקל | 2026-09-09 |  |
| `OPENING_ANCHOR_ET_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `OPENING_ATR_RTH_SEED_V1` | unset_or_0 |  | ✓ | cowork | 2026-09-02 |  |
| `OPENING_CONF_ENGINE_FUSE_V1` | unset_or_0 |  | ✓ | מייקל | 2026-08-26 |  |
| `OPENING_DALTON_GAPS_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `OPENING_DIR_FUSION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-24 |  |
| `OPENING_DRIVE_BRANCH_V1` | 1 | 1 | ✓ | מייקל | 2026-09-24 | ✓ |
| `OPENING_DRIVE_EXHAUSTION_VETO_V1` | 0 | 0 | ✓ | מייקל | 2026-08-19 |  |
| `OPENING_DRIVE_PROVISIONAL_V1` | 1 | 1 | ✓ | מייקל | 2026-09-20 | ✓ |
| `OPENING_DRIVE_SKIP_V1` | 0 | 0 | ✓ | מייקל | 2026-09-01 |  |
| `OPENING_DRIVE_T1_R` | 1.5 | 1.5 | ✓ | מייקל | 2026-09-24 | ✓ |
| `OPENING_ENGINE_CLOSED_BARS_V1` | 1 | 1 | ✓ | cowork | 2026-09-20 | ✓ |
| `OPENING_ENTRY_V1` | 1 | 1 | ✓ | מייקל | 2026-07-24 |  |
| `OPENING_FIRE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-24 |  |
| `OPENING_FIRST_TRADE_STRICT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-31 |  |
| `OPENING_LADDER_V1` | 1 | 1 | ✓ | מייקל | 2026-09-08 |  |
| `OPENING_OR_ATR_SCALE_V1` | 1 | 1 | ✓ | מייקל | 2026-08-12 |  |
| `OPENING_PLAYBOOK_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `OPENING_RUNNER_RIDE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-29 |  |
| `OPENING_STOP_STRUCTURAL_V1` | 1 | 1 | ✓ | מייקל | 2026-09-20 | ✓ |
| `OPENING_TYPE_GATE` | 0 | 0 | ✓ | מייקל | 2026-08-13 |  |
| `OPENING_TYPE_SEEDS_S1_V1` | 1 | 1 | ✓ | מייקל | 2026-07-23 |  |
| `OPENING_WINDOWS_V1` | 1 | 1 | ✓ | מייקל | 2026-08-06 |  |
| `OPENING_WINDOW_FIRE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-15 |  |
| `OPPOSITE_EXIT_V1` | unset_or_0 |  | ✓ | מייקל | 2026-07-14 |  |
| `ORDER_REJECT_DETECT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `ORPHAN_AUTO_FLATTEN_V1` | unset_or_0 |  | ✓ | מייקל | 2026-07-28 |  |
| `PATTERN_FAMILY_DELTA_DBL_V1` | unset_or_0 |  | ✓ | מייקל | 2026-08-25 |  |
| `PATTERN_LOSS_BREAKER` | 0 | 0 | ✓ | מייקל | 2026-07-16 |  |
| `PATTERN_RISK_CAPS` | 1 | 1 | ✓ | מייקל | 2026-06-12 |  |
| `PATTERN_STOP_COOLDOWN_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `PHANTOM_HEAL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `PHANTOM_SLOT_RELEASE_V1` | 1 | 1 | ✓ | cowork-dev | 2026-09-01 |  |
| `PHASE_B_LOCATION_V1` | unset_or_0 |  | ✓ | מייקל | 2026-09-14 | ✓ |
| `PHONE_ALERTS_V1` | 1 | 1 | ✓ | מייקל | 2026-08-13 |  |
| `PNL_REQUIRES_EXIT_PRICE_V1` | 1 | 1 | ✓ | מייקל |  2026-08-30 |  |
| `POSITION_MISMATCH_BLOCK_V1` | 0 | 0 | ✓ | cowork | 2026-08-29 |  |
| `POSITION_REF_PRICE_V1` | 1 | 1 | ✓ | מייקל | 2026-08-28 |  |
| `POSITION_TRUTH_SYNC_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `PROBE_REJECT_MIN_PTS` | 0.0 | 0.0 | ✓ | מייקל | 2026-07-23 |  |
| `PROTECTED_QTY_GUARD_V1` | 1 | 1 | ✓ | מייקל | 2026-08-18 |  |
| `RECONCILER_OWNERSHIP_AWARE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-24 |  |
| `RECONCILE_LIVE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-07 |  |
| `RELEASE_ENTRY_GATE_V1` | 0 | 0 | ✓ | מייקל | 2026-09-08 |  |
| `RELEASE_LEG_EXEMPT_V1` | 1 | 1 | ✓ | מייקל | 2026-08-14 |  |
| `RELEASE_TREND_BYPASS_PTS` | 12 | 12 | ✓ | מייקל | 2026-08-12 |  |
| `REQUIRE_WITH_TREND_DAY_DIRECTION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `RESPONSIVE_WITH_DAY_TREND_V1` | 1 | 1 | ✓ | מייקל | 2026-07-23 |  |
| `REV_EDGE_DAY_STRUCTURE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `RE_ACCEPTANCE_V1` | shadow | shadow | ✓ | מייקל | 2026-09-06 |  |
| `RISK_BUDGET_SIZING_V1` | 1 | 1 | ✓ | מייקל | 2026-09-01 |  |
| `RISK_BUDGET_USD` | 225 | 225 | ✓ | מייקל | 2026-09-01 |  |
| `RISK_CONSECUTIVE_LOSS_LIMIT` | 0 | 0 | ✓ | מייקל | 2026-07-20 |  |
| `RISK_CUTOFF_HOUR_ET` | 15 | 15 | ✓ | מייקל | 2026-07-19 |  |
| `RISK_CUTOFF_MINUTE_ET` | 30 | 30 | ✓ | מייקל | 2026-07-19 |  |
| `RISK_DAILY_LOSS_CAP` | 800 | 800 | ✓ | מייקל | 2026-09-16 |  |
| `RISK_HALT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-06 |  |
| `RISK_MAX_PTS_HARD` | 30 | 30 | ✓ | מייקל | 2026-09-01 |  |
| `RISK_MAX_TRADES_DAY` | 999 | 999 | ✓ | מייקל | 2026-07-20 |  |
| `RISK_MIN_CONTRACTS` | 3 | 3 | ✓ | מייקל | 2026-09-01 |  |
| `RR_BREAKOUT_MM_V1` | 1 | 1 | ✓ | מייקל | 2026-07-30 |  |
| `RR_ENTRY_GATE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-03 |  |
| `RR_MIN_ROTATION` | 0.65 | 0.65 | ✓ | מייקל | 2026-07-15 |  |
| `RR_NO_SELF_INFLICTED_V1` | 1 | 1 | ✓ | מייקל | 2026-09-08 |  |
| `RUNNER_BY_DAYTYPE_V1` | 1 | 1 | ✓ | מייקל | 2026-09-06 |  |
| `RUNNER_TRAIL_V1` | 0 | 0 | ✓ | מייקל | 2026-09-08 |  |
| `RUNNER_TRAIL_V2` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `S1_ACCEPTANCE_RECLASS_V1` | 1 | 1 | ✓ | מייקל | 2026-07-12 |  |
| `S1_BAR_REFRESH_V1` | 1 | 1 | ✓ | מייקל | 2026-09-06 |  |
| `S1_COMMITTED_PROVISIONAL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `S1_CONFIDENCE_V2` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `S1_CONF_SMOOTH_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `S1_DAY_DIRECTION_V1` | shadow | shadow | ✓ | מייקל | 2026-08-25 |  |
| `S1_DD_INVALIDATION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-12 |  |
| `S1_IB_SANITY_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `S1_NEUTRAL_PRECEDENCE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `S1_NEW_CLASSIFIER` | 1 | 1 | ✓ | מייקל | 2026-06-20 |  |
| `S1_NONCONVICTION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-12 |  |
| `S1_RECLASS_REQUIRES_IB_EXT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-31 |  |
| `S1_TREND_CONTROL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-12 |  |
| `S1_TREND_ELONGATION_V1` | 1 | 1 | ✓ | מייקל | 2026-08-09 |  |
| `S1_VALUE_MIGRATION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-12 |  |
| `S2_ADAPTIVE_THRESHOLDS_V1` | 1 | 1 | ✓ | מייקל | 2026-08-19 |  |
| `S2_AUTH_MATRIX_SINGLE_SOURCE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-19 |  |
| `S2_CHOPPINESS_GATE` | unset_or_0 |  | ✓ | מייקל | 2026-06-08 |  |
| `S2_CVD_DETECTION_V1` | shadow | shadow | ✓ | מייקל | 2026-08-23 |  |
| `S2_DELTA_DBL_LIVE_RELEASE` | unset_or_0 |  | ✓ | מייקל (T-153, יישום T-179) | 2026-08-31 |  |
| `S2_DETECTION_LIVE_DAYTYPE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `S2_INITIATIVE_JOIN_ATR_CAP_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `S2_REACTIVE_DAYTYPE_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `S2_REACTIVE_EDGE_FIX_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `S2_READ_FOOTPRINT_V1` | 0 | 0 | ✓ | Michael | 2026-09-25 | ✓ |
| `S2_REQUIRE_COT_AMT` | unset_or_0 |  | ✓ | מייקל | 2026-06-08 |  |
| `S2_TRIGGER_QUALITY_V1` | unset_or_0 |  | ✓ | cowork | 2026-09-17 | ✓ |
| `S3_MUTE` | 0 | 0 | ✓ | Michael | 2026-09-25 | ✓ |
| `S4_ENTRY_CONFIRM_V1` | 1 | 1 | ✓ | מייקל | 2026-07-05 |  |
| `S4_GRAY_RELABEL_CCI` | 100 | 100 | ✓ | מייקל | 2026-07-17 |  |
| `S4_GRAY_RELABEL_V1` | 0 | 0 | ✓ | מייקל | 2026-07-17 |  |
| `S4_HONEST_DAYTYPE_FALLBACK_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `S4_OVERRIDE_AWARE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-19 |  |
| `S6_MAE_SCRATCH_ATR_V1` | 1 | 1 | ✓ | מייקל | 2026-08-21 |  |
| `S6_MAE_SCRATCH_V1` | 0 | 0 | ✓ | מייקל | 2026-09-30 |  |
| `S6_STUCK_TO_BE_V1` | 1 | 1 | ✓ | מייקל | 2026-09-16 |  |
| `S6_TARGET_APPROACH_REALIZE_V1` | 0 | 0 | ✓ | מייקל | 2026-08-21 |  |
| `S7_SHADOW_LOG_V1` | 1 | 1 | ✓ | מייקל | 2026-08-06 |  |
| `SCALE_IN_MARGIN_PRECHECK_V1` | 1 | 1 | ✓ | מנדט-הלילה 27-28.08 (T-111) | 2026-08-28 |  |
| `SCALE_IN_P3_V1` | 1 | 1 | ✓ | מייקל | 2026-08-24 |  |
| `SCALE_IN_V1` | 1 | 1 | ✓ | מייקל | 2026-08-13 |  |
| `SIERRA_RECONCILER_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `SIZE_CAP_CUT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-09 |  |
| `SIZE_CAP_FLOOR_CONTRACTS` | 2 | 2 | ✓ | מייקל | 2026-08-19 |  |
| `SIZE_CAP_OVER_FIXED_V1` | 1 | 1 | ✓ | מייקל | 2026-07-14 |  |
| `SIZING_CONSOLIDATION_V1` | 1 | 1 | ✓ | מייקל | 2026-07-05 |  |
| `SSV_GATE_V1` | 0 | 0 | ✓ | מייקל | 2026-07-15 |  |
| `STALL_EXIT` | unset_or_0 |  | ✓ | מייקל | 2026-07-14 |  |
| `STEP_SCALED_LADDER_V1` | 1 | 1 | ✓ | מייקל | 2026-08-12 |  |
| `STOP_ANCHORS_V2` | 1 | 1 | ✓ | מייקל | 2026-06-07 |  |
| `STOP_ANCHOR_OFFSET_TICKS_OVERRIDE` | 16 | 16 | ✓ | מייקל | 2026-07-23 |  |
| `STOP_FLOOR_IB_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `STOP_FLOOR_ROTATION_ATR` | 0.8 | 0.8 | ✓ | מייקל | 2026-07-15 |  |
| `STOP_MOVE_TARGET_RESTORE_V1` | 0 | 0 | ✓ | מייקל | 2026-09-07 |  |
| `STOP_PERBAR_STRUCT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `STOP_RESOLVER_V1` | 1 | 1 | ✓ | מייקל | 2026-07-05 |  |
| `STOP_RETRY_ON_NONE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `STOP_STRUCTURE_EXTREME_V1` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `STOP_STRUCTURE_TRAIL_V1` | 1 | 1 | ✓ | מייקל | 2026-07-08 |  |
| `STOP_WIDEN_TO_FLOOR_ON_REJECT_V1` | unset_or_0 |  | ✓ | מייקל | 2026-07-19 |  |
| `STOP_WIDEN_TO_STRUCTURE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `STOP_WINDOW_COMPLETED_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `STRUCTURAL_STOP_ORIGIN_V1` | 1 | 1 | ✓ | מייקל | 2026-07-20 |  |
| `STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1` | 1 | 1 | ✓ | מייקל | 2026-08-27 |  |
| `STRUCTURE_EXIT_DOUBLE_V1` | unset_or_0 |  | ✓ | מייקל | 2026-08-30 |  |
| `STRUCTURE_EXIT_FAILBREAK_V1` | shadow | shadow | ✓ | מייקל | 2026-08-31 |  |
| `STRUCTURE_EXIT_REALIZE_PRE_T1_V1` | unset_or_0 |  | ✓ | מייקל | 2026-09-11 | ✓ |
| `STRUCTURE_EXIT_REALIZE_V1` | live | live | ✓ | מייקל | 2026-09-02 |  |
| `STRUCTURE_EXIT_REVERSAL_V1` | unset_or_0 |  | ✓ | מייקל | 2026-08-30 |  |
| `STRUCT_TARGETS_WIN_V1` | 1 | 1 | ✓ | מייקל | 2026-09-06 |  |
| `SYSTEM6_AUTOCORRECT` | protective | protective | ✓ | מייקל | 2026-07-15 |  |
| `SYSTEM6_EXIT_JOURNAL` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `SYSTEM6_EXIT_SIGNALS` | 1 | 1 | ✓ | מייקל | 2026-07-13 |  |
| `SYSTEM6_JOURNAL_AUTOLOOP_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `SYSTEM6_REVERSAL_TIGHTEN_V1` | 0 | 0 | ✓ | מייקל | 2026-08-17 |  |
| `SYSTEM6_SUPERVISOR` | 1 | 1 | ✓ | מייקל | 2026-07-05 |  |
| `T0_TARGET_PTS` | 3.0 | 3.0 | ✓ | מייקל | 2026-07-21 |  |
| `T1_BANK_R` | 1.5 | 1.5 | ✓ | מייקל | 2026-07-23 |  |
| `T1_LADDER_V2` | unset_or_0 |  | ✓ | מייקל | 2026-06-18 |  |
| `T1_REALISM_FLOOR_R_V1` | 1.5 | 1.5 | ✓ | מייקל | 2026-09-30 | ✓ |
| `T1_STRUCTURE_END_V1` | 1 | 1 | ✓ | מייקל | 2026-07-22 |  |
| `T2T3_NO_STOMP_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `T3_REQUIRED_V1` | 1 | 1 | ✓ | מייקל | 2026-09-02 |  |
| `TARGET_MIN_SPACING_V1` | shadow | shadow | ✓ | מייקל | 2026-08-21 |  |
| `TARGET_REALISM_V1` | 1 | 1 | ✓ | מייקל | 2026-07-10 |  |
| `TARGET_STRUCTURE_CLAMP_V1` | 1 | 1 | ✓ | מייקל | 2026-07-08 |  |
| `TARGET_ZONES_V1` | 1 | 1 | ✓ | מייקל | 2026-07-05 |  |
| `TRADE_ECONOMICS_AUTHORITY_V1` | diff | diff | ✓ | cowork-night (measure-only, no ruling needed) | 2026-09-09 | ✓ |
| `TREE_EDGE_FAMILIES` | CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM | CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM | ✓ | מייקל | 2026-10-03 | ✓ |
| `TREND_CCI_DIRECT_PT` | 50 | 50 | ✓ | מייקל | 2026-07-17 |  |
| `TREND_CCI_DIRECT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-17 |  |
| `TREND_LEG_CHASE_EXEMPT_V1` | 1 | 1 | ✓ | מייקל | 2026-08-11 |  |
| `TREND_STEP_ENTRY_V1` | shadow | shadow | ✓ | מייקל | 2026-08-23 |  |
| `TREND_STEP_STAIR_OR_V1` | 1 | 1 | ✓ | מייקל | 2026-08-18 |  |
| `TREND_STEP_STRUCT_EXEMPT_V1` | 1 | 1 | ✓ | מייקל | 2026-08-20 |  |
| `TREND_UPGRADE_ADD_V1` | unset_or_0 |  | ✓ | מייקל (בנייה) — הדלקה טרם-נפסקה | 2026-08-28 |  |
| `TSF_SHADOW_LOG_V1` | 1 | 1 | ✓ | מייקל | 2026-08-06 |  |
| `TS_OFFSET_INGEST_GATE_V1` | 1 | 1 | ✓ | מייקל | 2026-07-21 |  |
| `TS_WHOLE_HOUR_NORMALIZE_V1` | 0 | 0 | ✓ | מייקל | 2026-07-30 |  |
| `VARIATION_SUBTYPE_V1` | 0 | 0 | ✓ | מייקל | 2026-08-25 |  |
| `VARIATION_WITH_EXTENSION_V1` | 0 | 0 | ✓ | מייקל | 2026-09-17 | ✓ |
| `VARIATION_WITH_TREND_CONT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-27 |  |
| `VA_FADE_V1` | shadow | shadow | ✓ | מייקל | 2026-08-26 |  |
| `WOODIES_TS_HOUR_FIX` | 0 | 0 | ✓ | מייקל | 2026-07-22 |  |
| `ZLR_MGMT_V1` | 1 | 1 | ✓ | מייקל | 2026-07-14 |  |
| `ZLR_SHADOW_V1` | 1 | 1 | ✓ | מייקל | 2026-09-07 |  |
| `ZONE_LIMIT_ENTRY_V1` | 0 | 0 | ✓ | מייקל | 2026-08-14 |  |

## 6 · טבלאות-DB

| טבלה | שורות | max ts (IL) |
|---|---|---|
| `v9_trades` | 3083 | 2026-10-07 23:00 |
| `v9_decision_vectors` | 192994 | 2026-10-07 23:55 |
| `v9_bars_5min_woodies` | 21716 | 2026-10-07 23:55 |
| `v9_bars_5min` | 5054 | 2026-10-07 23:55 |
| `v9_day_type_state` | 63 |  |
| `v9_exit_decisions` | 16695 |  |
| `v9_trade_management_log` | 352511 |  |
| `v9_woodies_signals` | 3913 |  |
| `v9_footprint_journal` | 9958 | 179088-12-30 00:00 |
| `v9_bars_cumulative_delta` | 9090 | 2026-10-07 23:55 |
| `broker_truth` | None | missing |

## 7 · LaunchAgents

| label | pid | rc |
|---|---|---|
| `com.mems26.agents_bootstrap` | - | 0 |
| `com.mems26.mobile_relay` | 1629 | 0 |
| `com.mems26.backend` | 49501 | -15 |
| `com.mems26.update_check` | - | 0 |
| `com.mems26.export_promoter` | 1619 | 0 |
| `com.mems26.startup_check` | - | 0 |
| `com.mems26.eod_handoff` | - | 0 |
| `com.mems26.frontend` | 621 | 0 |
| `com.mems26.bridge` | 637 | 0 |
| `com.mems26.activity_feed` | 1624 | 0 |

## 8 · תיקטים — 406 סה״כ · 339 פתוחים · {'🔴': 104, '🟠': 163, '🟡': 29, '✅': 51, '🔵': 43, '⚠️': 3, '🔴🔴': 9, '🟢': 1, '📄': 1, '📊': 1, '⚪': 1}

| # | סטטוס | כותרת | הצעד הבא |
|---|---|---|---|
| T-545 | 🔴 | פוזיציית-לייב פתוחה בברוקר שהספרים סגרו כהפסד  | תור-הלילה מנקה ל-#3046 את `entry_ts` **וגם** את `pnl_sierra`, וכותב ב-LIVE_CHANNEL "אין רישום-ברוקר ל-#3046" + מסמן את ה-`+53.75` כ-`unmatched` במפורש. 🆕 **ריצה |
| T-540 | 🔴 | ולידציה מחוץ-לדגימה של ענפי-העץ — `scripts/walk_forward.py` → `docs/reports/WALK_FORWARD_2026-10-05.md` (05.10 | (1) סוכן-ה-23:40 קורא `docs/reports/WALK_FORWARD_2026-10-05.md` §7 **לפני כל עלה חדש** — רשימת-הגיזום (8 עלים, OOS ≤ 0, n≥10) היא הסדר-יום, לא T-531/T-528; הליל |
| T-537 | 🔴 | ביקורת-השיטה (מייקל 05.10 15:10: "מפקח על מפקח על מפקח … עוד פלסתר — תבדוק האם השיטה נכונה והאם רעיון-הענפים ע | פסיקות-מייקל על סעיף 3 בדוח: (1) הקפאת הוספת-ענפים עד פרוטוקול-ולידציה מחוץ-לדגימה (walk-forward, 10 סשנים אחרונים = סט-החזקה); (2) מדידת קונפיג-ליבה (תבניות חס |
| T-532 | 🔴 | סדרת-הברים של סיירה קפואה על שישי `23:55` 60 שעות, בעוד היצוא נכתב כל 3 שניות עם חותמת-עכשיו והציטוט חי וזז —  | הפוסק הוא **woodies** — woodies רועש אחרי `16:35` או `max(ts)` לא בן <10 דק' ⇒ NO-GO + מקרה (ג); **רעש `[bars/5min]` לבדו בעוד woodies טרי אינו NO-GO** (מלכודות |
| T-521 | 🔴 | פוטפרינט זורם אבל חסר זהות-בר ⇒ הריפליי של [[T-478]] בלתי-אפשרי (cowork-dev 30.09 23:35, אומת פעמיים). | (1) `to_dict()` יפלוט `"ts": self.bar_start_ts`; (2) מיגרציה ל-UNIQUE על `(ts, symbol)` + `ON CONFLICT` מפורש; (3) ריסטארט-ברידג' **מחוץ לשעות** (לפני 16:10 או  |
| T-520 | 🔴 | החוסם של 30.09 אינו המרג'ין אלא `pre_send_entry_guard` — העץ אישר 5 מצבים ושלושה ירי-לייב נחסמו *לפני* השליחה, | **(1) עלות-החסימה — נמדדה חלקית בריצה 113 (`20:05-20:12`), וההפתעה היא הסימן:** הנחסמות אינן 3 אלא **8** (‏`16:50→20:05`, כל הסשן, sys 2+4, 7 לונג + 1 שורט): `# |
| T-487 | 🔴 | העץ החליט על `opening_type=OPEN_AUCTION_IN` ביום שבו המסווג הקנוני לא הפיק את הערך הזה אף פעם — הוא אמר `NA`,  | (1) לברר **מהקוד** מאיזה שדה `trading_gateway` מזין `opening_type` לווקטור-העץ, ולהעמיד אותו מול הכותב של `v9_day_type_state` — האם זה מסווג שני עצמאי, קאש שלא  |
| T-486 | 🔴 | שני שערים חוסמים ירי-לייב כשמייקל/אתי מחזיקים פוזיציה ידנית — ורק הראשון ניתן לפתוח מתוך פסיקה קיימת. השני (`T | לסגור את השורט לפני הפתיחה, או להשאיר ולוותר על יום-הלייב. **ואם מייקל בוחר "להשאיר ולסחור":** זו פסיקה חדשה על `working > 0` ⇒ (1) לקרוא כמה פעמים הוא חסם היסט |
| T-481 | 🔴 | הכניסה החיה מגיעה בשליש האחרון של המהלך, לא בתחילתו — #2340 נכנסה 25 דק' ו-15.5 נק' אחרי הכניסה-האידיאלית, לתו | **(1)** להוציא על 58 הסשנים את ההתפלגות `(זמן-כניסה-חי − זמן-כניסה-אידיאלי)` ו-`(מחיר-כניסה-חי − מחיר-אידיאלי)` לכל מהלך שנתפס — **מספר אחד מכריע אם 'טריגר-מאוח |
| T-458 | 🔴 | ענפי-יום-וריאציה לביצוע (מייקל 24.09 08:00: "רוב הימים בשנה הם וריאציה או כאלה שמסתיימים ככה — עליך לדאוג שיהי | (ה) ריפליי-עדיפות-סלוט: ב-75 המקרים — מי החזיק את הסלוט ומה עשה מול מה ש-VAR_CONT היה עושה (עדיף באופן שיטתי ⇒ כלל-עדיפות בגייטוויי, מספר לפני דגל); (ו) שלב-D ב |
| T-456 | 🔴 | 23.09 — "המערכת לא תפקדה טוב: לא סחרה את הפתיחה, לא זיהתה את סוג-היום, לא לקחה את העסקאות" (מייקל 22:45). הראי | (1) שער-15:30 24.09 טוען; אימות: `grep "T-451 RTH boundary" /tmp/backend.err.log` ב-16:30 + וקטור-16:45 עם `extension=none`; (2) ריפליי-רגרסיה של 23.09 בהרנס עם |
| T-442 | 🔴 | הריבוט של 22.09 09:34 החזיר 3 סוכנים מתוך 9 — `mobile_relay` (מראת-הטלפון) ו-`export_promoter` בין הנופלים, וה | נמדד ב-13:35, שעתיים לפני השער: `v9_bars_5min` **אינו מתקדם** (`09-22/90/23:55`, אפס שורות ב-23.09) וה-`TS-OFFSET-GATE` **אינו שקט** (`non-advancing batch 49247 |
| T-441 | 🔴 | מדידת-הצל של עץ-v2 הייתה מתה מיום לידתה — אפס שורות `TREE_SHADOW` ב-`v9_decision_vectors` (16.09→22.09: רק `BA | שבוע-מדידה (22–26.09) של v2 מול v1 מהשורות — ורק אז עמוד-ההכרעה למייקל. |
| T-438 | 🔴 | ירייה-חיה נדחתה ב-`T-335 LADDER INVALID` ולא הייתה רשומה בשום מקום — `v9_trades` מדלג מ-`2037` ל-`2039` והחור  | **(1)** ✅ **בוצע** — `tests/v9/regression/test_t438_ladder_sanitize.py` (253 שורות, 10 מבחנים) משחזר את הסולם המדויק שהגיע ל-`sierra_command.py:920`. **פלט גולמ |
| T-436 | 🔴 | הספרים והברוקר מעולם לא הושוו — `pnl_sierra` ריק בכל שורה, ולכן סבב-מסחר שלם שלא שלנו נעלם מהדיווח, ושדה-P&L ב | אימות אחרי ריסטארט-15:30 — `grep "T-436 pnl_sierra" /tmp/backend.err.log` אחרי הסגירה הראשונה ⇒ שורה אחת לכל עסקה; EOD מריץ `broker_truth.py --write` כרשת-ביטחו |
| T-433 | 🔴 | דוח-`20.09` שמייקל הסתמך עליו היה שגוי בשני מרכיביו — בלבול-ימים הפך שבת רגילה ל"תקלת-פיד", וייצר ריקונקט מיות | **(1)** כל דוח-יום חייב לגזור את שם-היום מ-`date`/`to_char(ts,'Dy')` **ולהדפיס אותו ליד התאריך** — לעולם לא לכתוב "שישי" מהראש; זהו בדיוק הבלוק `DAY=$(...)` של  |
| T-430 | 🔴 | פיד-הנתונים של סיירה מת בשישי 19.09 00:24 IL ונשאר מת עד עכשיו — והשומרים לא ראו: | (1) **מבחן-ההכרעה היחיד — `01:00 IL` ליל שני:** אם `max(ts)` מתקדם אחרי פתיחת-Globex ⇒ **T-430 נסגר, ושני אינו NO-GO על-רקע-פיד**; אם הוא קפוא גם ב-`01:30` ⇒ T- |
| T-426 | 🔴 | התיקון של [[T-422]] עובד — והשער זורק את התוצאה: כל מועמד-פתיחה מוקדם שנולד ממנו נחסם ב-`dalton_intent:kind`/` | (1) **להציג למייקל את השאלה האמיתית:** האם בשלב B, כשסוג-הפתיחה עדיין `OPEN_AUCTION_IN` אבל בר-אישור סגור כבר אישר דרייב, מותר `WITH_DRIVE`? זו **פסיקה**, לא בא |
| T-422 | 🔴 | באג: בר-האישור של הפתיחה נבדק על הבר המתפתח (o≈c בשנייה ה-3), לא על הבר הסגור ⇒ הדרייב מוחזק עד הקצה. | (1) ✅ **בוצע ואומת — cowork-dev 21.09 23:05-23:20 (תור-הלילה).** הקוד נטען בריסטארט `15:42:40` (מאזין `79317`), והמקור הקנוני נקרא בהצלחה: `grep -c "T-425 close |
| T-405 | 🔴 | הפרת-כלל-הטלפון: ריצת-הניטור 17:41 שלחה מקרה (ג) על הפוזיציה הידנית וחתמה בשאלה "היא שלך?" — שש דקות אחרי ש-[[ | בוצע — **מלכודת 16** ב-`COWORK_DAILY_READ.md` (פוזיציה ≠ TM = פסיקה ולא אזעקה; `TASK_LOG` לפני כל מסקנה מבצעית). ל-Render אין מחיקה והודעת-תיקון היא בעצמה הפרה  |
| T-398 | 🔴 | ה-ack האוטומטי של `cc` שולח למייקל P&L שאינו של היום ואינו שלנו — מלכודת `COWORK_DAILY_READ §3.5` שהפכה מדיווח | (1) **ל-cc** — ה-ack יצטט `acct_daily_pl`, או **עדיף: יוותר על שדה-P&L לגמרי** ויציג `עסקאות-שלנו היום: N` מ-`v9_trades`, כי ack אוטומטי **אינו יכול** להריץ את  |
| T-383 | 🔴 | המסחר-החי כובה בסיירה ב-`~17:44` אחרי שהחשבון החי חצה את תקרת-ההפסד-היומית שלו — וההפסד כולו אינו שלנו; `fire_ | (1) **ממתין לפסיקת-מייקל** — החזרת החשבון החי היא פעולה בסיירה על חשבון-מסחר, מחוץ לסמכות-ניטור; עד אז אפס פעולה. (2) **בניטור-RTH הבא:** לדגום `is_sim` + `send |
| T-382 | 🔴 | שער-הבוקר הכריז "המרגין מכסה 5 חוזים" בעוד הפנוי מכסה  | (1) **ממתין לפסיקת-מייקל** על סגירת-הזרה מול אתי — עד אז אפס פעולה על הפוזיציה. (2) **תיקון-מדידה, בסמכות, ללא סיכון:** בכל ריצת-שער לקרוא `acct_available_funds |
| T-375 | 🔴 | הריסטארט של `19:14` ניתק את העסקה-הפתוחה ממוני-הסיכון של השער — `RISK_HALT_V1` מודד מרצפה נמוכה ב-`$183.75` מה | (1) **הזול והמיידי, בלי קוד:** אחרי כל ריסטארט בתוך RTH — להצליב `/gateway/status.daily_pnl` מול `SUM(pnl_usd)` ב-`v9_trades` לאותו יום ולדווח דלתא; זו בדיקה של |
| T-373 | 🔴 | `ib_locked` מסונתז מ-`ib_found` — השדה שמגדיר "חלון-ה-IB נסגר" דולק מהפעמון ולא מ-`10:30 ET`, ו-`§5a` מנתב לצל | **לא לגעת בלי פסיקה** — תיקון `ib_locked` משנה **מתי** לייב יורה. (1) לקרוא את מקור-ה-DLL: האם `MES_AI_DataExport.cpp` יכול לפלוט `ib_locked` אמיתי (לפי §Sierra |
| T-372 | 🔴 | פוזיציה-זרה חדשה (שורט 8 חוזים) הופיעה `~15:53-16:05` וחוסמת את גודל-הפתיחה — ה-GO של `15:55` בוטל על ציר-המרג | אם הפוזיציה נסגרת לפני `16:30` — `avail` חוזר ל-`~2,818` והגודל ממומן שוב (בדיוק מה שקרה ב-`15:01`, [[T-353]]); אם לא — הפתיחה נכנסת עם מרג'ין שאינו נושא `5` חו |
| T-368 | 🔴 | הזמנת-מרג'ין של פקודה-שנדחתה נראית בייצוא כקריסת-מרג'ין — ובדגימה-אחת היא הופכת שער-GO ל-NO-GO כוזב. | כל בדיקת-מרג'ין בשער = **≥5 דגימות על ≥30 שניות + הצהרת-יציבות**, לעולם לא קריאה יחידה; נרטיב ומספר נבדקים **יחד** לפני שליחה. המחסום כבר מיושם בסקריפט-השליחה ( |
| T-365 | 🔴 | `restart_all` יצר שני מפעילים ל-backend ⇒ לולאת `Errno 48` כל ~30 שנ'. | `scripts/start_all.sh` אינו בודק אם launchd כבר מחזיק את `:8000` לפני שהוא פותח `screen` — ‏`grep -n 'pgrep -f "uvicorn backend"' scripts/start_all.sh` ⇒ שורה ` |
| T-354 | 🔴 | `edge_fade_targets` (פריט 3, `37326a55`) הוא הכרזה ולא אכיפה — ובדרך הסיר חסימת-rr. |  |
| T-353 | 🔴 | המרג'ין הפנוי אינו מממן את הגודל-הפסוק: `$448.66` פנוי מול `$1,931.00` הדרושים ל-5 חוזים ⇒ חוסר `$1,482.34`. ה | (1) **שער-15:30-16:10** — למדוד `acct_available_funds` מחדש במועד-האמת: `≥$1,931` ⇒ GO על 5; `<$1,931` ⇒ NO-GO-על-5 ומדווח במקרה (ד) עם המספר. (2) **פסיקת-מייקל |
| T-350 | 🔴 | `pnl_sierra` ריק ב-`0/3` עסקאות-הלייב האחרונות (`09-10` · `09-11`) אחרי `6/6` ב-`09-07..09-09` — ולשלושתן דווק | (1) **לקרוא את נתיב-הכתיבה** של `pnl_sierra` ולקבוע אם הוא **מונע-אירוע** (נכתב בסגירה) או **כלי-אצווה** — זו השאלה היחידה שמפרידה בין "רגרסיה חיה" ל-"כלי שלא ה |
| T-343 | 🔴 | ציר-הדולרים של הצל אינו בר-השוואה ללייב — מדד-השער השבועי של [[T-303]] היה נבנה על בסיס פגום. | **(1)** לקרוא את מקור-`pnl_usd` בנתיב-הצל ולקבוע בקוד אם הוא per-fill או per-position — זו ההפרדה שמכריעה בין (שפיר) ל-(פגם). **(2)** לאתר את מקור 5 מחירי-היציא |
| T-338 | 🔴 | התיקון ל-`EOD_CLOSE_T10` קיים בקומיט `359bc3c3` (`19:55:03`) ו | **(0) מה שהשתנה:** אין עוד החלטה-עד-`22:50`; שלוש האפשרויות שלמטה כבר אינן תחת שעון, ואפשרות (א) "לא-כלום" **התממשה מעצמה**. **הפסיקה היחידה שנותרה, ואין בה דחי |
| T-337 | 🔴 | רובד של 8 חוזים שאינו שלנו רוכב  | **(1) 🔴 `22:50` היום, ודורש את מייקל:** `EOD_CLOSE_T10_V1` שולח `FLATTEN_ACCOUNT` **ברמת-החשבון** ⇒ אם שתי השכבות פתוחות ב-`15:50 ET`, הוא יסגור **גם את `1512`  |
| T-336 | 🔴 | ‏`pre_send_entry_guard` חסם ירי-לייב אמיתי ב-`19:30:11` בגלל פוזיציה זרה — וזו ה | **(1) השאלה למייקל, במשפט אחד:** כשפוזיציה **מוכחת-זרה** פתוחה בחשבון-המשותף (אתי — [[project_account_shared_with_eti]]), האם הלייב שלנו צריך **להיחסם** (המצב ה |
| T-334 | 🔴 | ‏`acct_available_funds = 332.39` — הלייב אינו יכול לממן 5 חוזים כל עוד הפוזיציה הזרה פתוחה. השער חוסם קודם, ול | (1) **לאתר בקוד את נקודת-בדיקת-המימון** (`grep -rn "available_funds\/acct_available" backend/`) ולקבוע מה קורה כשהגודל-הפסוק אינו ממומן: דחייה, מילוי-חלקי, או כ |
| T-333 | 🔴 | פוזיציה זרה `-10` פתוחה בחשבון מ-`18:53:08`, ו-`EOD_CLOSE_T10_V1` ישלח `FLATTEN_ACCOUNT` ב-`22:50 IL` — כלומר  | (1) **מייקל מכריע לפני `22:50`** באחת משתיים: (א) להשאיר — ואז לדעת שהפוזיציה תיסגר; (ב) לבקש דילוג חד-פעמי. ⚠️ **כיבוי `EOD_CLOSE_T10_V1` הוא שינוי-משטח-סיכון* |
| T-315 | 🔴 | נפתח-מחדש ע"י cowork 11.09 10:55 — הפריט סומן ✅ אך אימות-cowork בן 19 דקות (`d6dfdc76` ב-10:36, `docs/handoff/ | cc — (1) מבחן-רגרסיה שנכשל על `7f641a3f` ועובר על `49dcb7a7` (בר שבו מנצח-S2 נחסם **בשער** ⇒ `DOUBLE_TOP_AA` מנותב באותו בר עם `starved_by`); (2) למדוד את אותה  |
| T-314 | 🔴 | נפתח-מחדש ע"י cowork 11.09 10:55 — הפריט סומן ✅ אך אימות-cowork בן 19 דקות (`d6dfdc76` ב-10:36, `docs/handoff/ | cc — קובץ-מבחן ל-`opening_lock.py` שנכשל על `35ab5541` ועובר על `330f5806`: סגירה מתחת ל-`rej_low` ⇒ UP **מופרך**; סגירה מעל `rej_high` ⇒ UP **אינו** מופרך (הכי |
| T-309 | 🔴 | הלייב חסום בשקט מאז 18:55:17 — פוזיציה זרה מנעה את שחרור `live_slot`, והחשבון כבר שטוח אבל הסלוט לא. |  |
| T-308 | 🔴 | שרידי-הקוד של [[T-307]]: הפוזיציה נסגרה, שלושת הבאגים שהיא חשפה חיים. | **(1)** לקרוא את מקור-המכפיל ב-`sierra_position_reconciler`, לתקן ל-`$5` ל-MES (רצוי מטבלת-סימבול ולא קבוע), + רגרסיה. **(2)** להחיל בעלות גם על נוסח-ה-ANOMALY. |
| T-307 | 🔴 | 12 חוזים שורט עירומים בחשבון-המשותף (אפס פקודות-הגנה), והמרג'ין-הזמין נשחק מ-$2,276 ל-$67 בתוך 26 דקות — מרחק  | `$67` זמין מול 12 חוזים ללא סטופ. ההכרעה שלו בלבד (חשבון משותף — [[T-288]]/[[T-289]]); **דווח-טלפון יצא 19:15:34Z** (2,940 תווים, אומת ב-`GET /chat`). **(2)** c |
| T-305 | 🔴 | הברקט של עסקת-הלייב `#1409` הוזז ידנית בחשבון-המשותף — כל חמש הרגליים הנותרות בדיוק `+6.00` נקודות — והספרים ע | מייקל — אישור לסנכרן `stop`/`t1`/`t2`/`t3` של **עסקה פתוחה** מתוך `USER_ORDER_MODIFY`. הנתיב קיים חלקית: `backend/v9/api/v9/live_ledger_routes.py:73,92` כבר קור |
| T-296 | 🔴 | הפלייבוק חי ונכשל בשער-הקבלה של עצמו. | — להשאיר חי או להחזיר לצל עד שהשער עובר |
| T-295 | 🔴 | נגד-ההרחבה הוא כל ההפסד: 19 עסקאות, −$715, 32% הצלחה — מול +$158.75/59% עם-ההרחבה (39 סשנים, מתומחר-ברוקר בלבד | — לחסום כיוון-נגדי בימי-Variation ו/או לחווט `day_bias` מהצל אל `direction_hint` |
| T-290 | 🔴 | הספרים רשמו ‏+$30  | (1) לא לערוך את הרשומה ביד — לתקן בשורש: ב-`fill_poller` נתיב `W2 EXIT-TRACK` להתנות ייחוס `CLOSED_TRADE_PNL` לעסקה בקיום `entry_ts`/submit-ack, אחרת לסגור `CAN |
| T-284 | 🔴 | מאגר-החיבורים של הבקאנד ל-DB התרוקן, ההזנה עצרה 30 דק', והמערכת לא מתאוששת לבד (cowork 09.09 12:08-12:41). | מייקל פוסק ריסטארט-או-לא; במקביל **cc מתקן את הדליפה** לפי `docs/reports/T284_LEAK_SITE_2026-09-09.md` (‏`bars.py:1050-1146 post_cumulative_delta`) / **(1) הריס |
| T-283 | 🔴 | דוקטרינת-הלמידה (מייקל 09.09 10:40: "איך נלמד ונייעל לאורך זמן… לא כללים טיפשים אלא חשיבה על סמך המצב") — `doc |  |
| T-280 | 🔴 | מלאי-הפערים המלא (מייקל 09.09 09:20: "להשלים חוסרים שלא פותחו ולעשות סדר במערכת כולה") — `docs/reports/GAP_INV |  |
| T-279 | 🔴 | שתי פסיקות של מייקל סותרות זו את זו על אותו נתיב-ירי, ואף שומר לא רואה את הסתירה — `ZLR_SHADOW_V1=1` (07.09: " |  |
| T-276 | 🔴 | הירי-החי הראשון של 08.09 נדחה בשער-האחרון ולא הגיע לברוקר — `T-214` (חגורת-t3, פסיקת-מייקל 01.09) ירה בפעם הרא | (1) **למפות אילו נתיבי-`t3` קיימים ואיזה מהם נגיש לפני נעילת-IB** — `trading_gateway.py:3161 / 3229 / 3290 / 3357 / 3402` — ולקבוע בכמה מהם `OPENING_DRIVE` יכול |
| T-275 | 🔴 | שלושה סוכנים בלתי-תלויים (6 ימי-קיצון + 17 סשנים) הגיעו לאותו ממצא משלושה כיוונים: אנחנו רואים את העסקה, נחסמי | (1) **המועמד היחיד עם n>=10 ויחס>1 שאינו נוגע בהיגיון-הכניסה: תקרת 2 חוזים כשהסטופ-ההתחלתי מתחת ל-6.0 נק'** — n=12 (8 מפסידות, 4 מנצחות), `saved $467.50 / block |
| T-273 | 🔴 | פטור-הבעלות (`ENTRY_GUARD_OWNERSHIP_V1`) בלתי-נגיש-מבנית כשלפוזיציה-הידנית יש הגנה: הוא נופל דרך אל בדיקת-`wor | (1) **מותנה — ייתכן שיתמוסס לבד:** אם מייקל יסגור את הידנית ויבטל את הברקט לפני 16:30, `pos=0/working=0` והשער נפתח מעצמו. **לאמת שוב בשער-הקדם-פתיחה 15:30-16:1 |
| T-268 | 🔴 | ZLR נכנס ללייב ב-17:55:53 — ‏40 דק' אחרי שהוא נפסק לצל. ‏`ZLR_SHADOW_V1` מכסה ענף-זיהוי אחד מתוך שניים, והענף  | (1) **מייקל — הכרעה על הפוזיציה החיה:** להשאיר עד סטופ/יעד (סיכון מוגדר ‎$32.50, כרית-מרג'ין ‎$2,359 ≫ ‎$1,595) או `FLATTEN_ACCOUNT`. אין פעולה אוטומטית — cowor |
| T-266 | 🔴 | `day_type=UNKNOWN` אינו מגן על S4 — שלושה דפוסי-וודיס `armed` ויכולים לירות לייב מ-16:30, שעה לפני השער של 17: | (1) **הכרעת-מייקל, לא של סוכן:** לכסות את `16:30–17:15` (השהיית S4 עד השער) או להריץ על טייפ-חג. נשלח לטלפון `16:12:16`, **אומת-במסירה** (`EXACT MATCH=True`, `1 |
| T-264 | 🔴 | `session_gate.is_within_firing_window()` עיוור-לחגים — והשאלה-הפתוחה של הרשומה הקודמת הוכרעה: שומר-החג קיים, א | (1) **ההכרעה של מייקל, ואינה שלי** — פירוק-זרוע להיום, או ריצה על סשן-חג דליל. נשלח לטלפון 14:20 ואומת-במסירה (`GET /chat` ⇒ הפריט האחרון, 1255 תווים, שלם). **c |
| T-263 | 🔴 | שישה דגלי-מסחר חדשים דלוקים ב-`.env`, והקוד שמממש אותם אינו מקומם — ‏`0` אתרי-קריאה ב-`HEAD` מול `4` בעץ-העבוד | (1) **cc-macbook: לסיים, להריץ טסטים, ולקמט את 328 השורות.** עד אז אין לבצע ריסטארט. (2) **אימות-סים לששת הדגלים** לפני שהם רואים מסחר-לייב — שניים מהם נוגעים י |
| T-262 | 🔴 | `eod_handoff` מעולם לא הגיע לריפו — הסקריפט רץ ב-`/`, נכשל בכל שלב, ו-launchd רשם `exit 0`. שני שורשים בלתי-תל |  |
| T-261 | 🔴 | `eod_handoff` שהועלה היום ב-20:38 יריץ הלילה ב-23:05 `git stash` → `git pull --rebase` → `git stash pop --quie | (3) `stash@{0}` מ-01.09 — עדיין יתום; (4) להוסיף `StandardOutPath`/`StandardErrorPath` ל-`eod_handoff.plist` — אחרת הפלט של הלילה (`PUSHED` / `PUSH REJECTED`) ה |
| T-259 | 🔴 | שישה LaunchAgents של mems26 לא נרשמו כלל ב-launchd אחרי ריסטארט-המק של `17:03` — ביניהם `com.mems26.mobile_rel | **השורש נמצא (05.10, `sfltool dumpbtm`):** macOS Background-Task-Management משייך LaunchAgent לפי `ProgramArguments[0]` — ששת הסוכנים שמופעלים ב-Python משויכים  |
| T-251 | 🔴 | הספרים סגרו את הלייב `#1008` בעוד חוזה אחד עדיין חי בשוק — והשומר שאמור לתפוס בדיוק את זה קפוא על `stuck_secon | (1) **הפעלה** — הקוד של `71e47cd1`+`a25c82a8` יושב ב-HEAD ולא רץ; ריסטארט מותר **רק** מחוץ ל-16:10-23:00 ועם `git status` נקי, ואז לאמת `ps -o lstart` על ה-PID  |
| T-242 | 🔴 | בפעמון-הפתיחה ל-`entry_location_quality` אין רגל למדוד — הוא ממציא אחת מתוך בר-בן-4-שניות וחוסם עליה. הקורבן ה | לפני הקריאה ב-`1803`, אם חלון-הסשן מחזיק פחות מ-`N` ברים **סגורים** (מוצע `N=2`) או `L` קטן מרצפה (מוצע `max(1.0pt, 0.5×ATR)`) ⇒ להעביר `leg_base=None`/`leg_ext |
| T-236 | 🔴 | הראלי 7698.25→7759.75 (03.09, ~60 נק') עבר במלואו מחוץ למערכת — 7 כניסות-לונג חסומות ברצף ע"י `entry_location_ | לחבר את `has_pullback` בגייטוויי = מימוש פסיקת-28.08 כלשונה, **בלי להרפות שום סף** (השער ימשיך לחסום רודף-אמיתי) ⇒ תיקון-באג, לא הרפיית-סיכון, ולפי כלל-הפסיקות- |
| T-232 | 🔴 | פוזיציה-ידנית LIVE ‎−8 חוזים (נפתחה 10:51 IL) יושבת ללא פקודת-הגנה אצל הברוקר, ומוחקת את כרית-המרג'ין: `acct_a | **(1)** כל עוד הפוזיציה פתוחה, שער-15:30 ייכשל בשני צעדים נפרדים: **(א)** בדיקת-T-34 תדווח 🔴 (`avail 413.38 < 1,595`) — **דיווח בלבד, אסור לגעת ב-`.env`** לפי נ |
| T-230 | 🔴 | `flag_guard` — השומר שכל תפקידו לתפוס דריפט-דגלים —  | (1) להחליף את הפרסר-היד ב-`yaml.safe_load` **ולהפוך פריט-שלא-נתפס לכישלון קולני** במקום `if em:` בלי `else`; (2) הטסט: כל מפתח ב-`ruled` חייב להופיע בפלט-השומר  |
| T-227 | 🔴 | ספרי-הלייב של 02.09 מנפחים את תרומת-המערכת ב-$252.50 — רשום `+$277.50`, המציאות `+$25.00` — והשרשרת נסגרת בדיו | (1) `backfill` למפרע — **דורש פסיקת-מייקל**; הכלי מוכן ומחזיר `REFUSED` בלי `--i-have-michaels-ruling`. (2) להסיר את דריסת עמודות-היעד עצמה — משנה את מה ש-Syste |
| T-225 | 🔴 | אף עסקה של 01.09 לא נכנסה בגודל-הפסוק 5 — `MARGIN SIZING 5 → 4` ירה על כל מועמד, כל היום, ואיש לא ראה זאת. | **(א) בשער-היום (cowork, מיידי, בסמכות):** להוסיף לשער את הבדיקה `cap_contracts(ruled_contracts())` ולדווח את **התוצאה** ולא רק את `effective_contracts` — כלומר |
| T-221 | 🔴 | פוזיציה זרה בחשבון חוסמת את המסחר של היום — שורט 6 חוזים @7624.00 ללא פקודת-הגנה, ו-`T-43` חוסם כניסות חדשות מ | (1) *"הפוזיציה שלי/של אתי"* ⇒ אין תקלה; נותר רק להחליט אם לסגור אותה לפני 16:30 כדי לשחרר את `T-43` ואת המרג'ין, אחרת אין מסחר היום. (2) *"לא שלי"* ⇒ בירור-מקור |
| T-220 | 🔴 | `/api/v9/day_type/state` החזיר מצב-מומצא ממנוע-מת — בלי סימון, בלי לוג — ושישה צרכנים חיים קראו משם. | לעדכן את `fire_drill.py` שייכשל על `meta.degraded=true` במקום לעבור בשקט — שינוי שער-פתיחה, לא נגעתי |
| T-219 | 🔴 | מה שנחסם — לא נמדד. גם לא בצל ⇒ אי-אפשר להכריע על אף שער אי-פעם. | תיקון בן מילה אחת — `self._capture_cross_context(setup)` ⇒ `self._capture_cross_context()` ב-`trading_gateway.py:826`; ואז טסט-רגרסיה שמריץ `route_setup` על מוע |
| T-216 | 🔴 | `DOUBLE_TOP_AA_SHORT` נחסם שיטתית ע"י `location_gate` — 0 עסקאות-לייב אי-פעם — והשורש הוא סתירה מבנית בין סמנט | **לא להכריע על הנתונים האלה.** לבנות קודם את המדידה — `docs/handoff/SPEC_T219_SHADOW_BLOCKED_2026-09-01.md` |
| T-214 | 🔴 | המימוש אינו מסתגל לשינוי סוג-היום |  |
| T-213 | 🔴 | T2 לא מולא למרות שהמחיר עבר אותו ב-4 נק' (#942 היום) | לתקן את בחירת-`order_id` שתכבד את היסט-ה-remap — **נתיב-ביצוע ⇒ עצירה-אסטרטגית + אישור-מייקל לפני קוד** **🔴🔴 הסלמה 02.09 18:10 — אותו שורש, אבל עכשיו הוא גם *דו |
| T-211 | 🔴 | רגל-יציאה שבוצעה בפועל נמחקה מהספרים — `quality.exit_fills` נדרס במקום להצטבר, ו-P&L של העסקה-החיה הראשונה של  | backfill היסטורי של 79 העסקאות מיומן-המילויים — **לא בוצע**, דורש פסיקה (משנה P&L רשום למפרע) |
| T-209 | 🔴 | ארבעת תיקוני-01.09 אינם חיים — חלון-הריסטארט עבר (פסיקת-מייקל 16:28: לא נוגעים) | לאמת את `FIX-8` בלבד ואז לסגור; **ולתעד שהבסיס-להשוואה של היום הוא התצורה החדשה (מ-15:11) ולא הישנה** — אחרת ניתוח-הדלתא של מחר ישווה יום-חדש מול יום-חדש ויכריז |
| T-208 | 🔴 | שלוש הערות-מסך של מייקל מ-31.08 מעולם לא נפתחו כמשימה — הן קיימות רק ב-`MICHAEL_INBOX` ובצ'אט, ולכן אין להן בע | **(1) כרטיס-עסקה אמיתי בממסר** (`render_mobile_relay/app.py` **בלבד** — לפי הוראת (ג); הנתונים כבר נדחפים ואין צורך בנתיב-מסחר חדש): חוזים-חיים מ-`position_qty` |
| T-206 | 🔴 | `task_log_guard` נכשל על פריט פתוח — קרא ✅ מתוך תיאור-הפרוזה במקום מעמודת-הסטטוס, ובכך חסם את שער-הפתיחה. | אין — נסגר ואומת. **אם מישהו נוגע ב-`_status_cell`:** `tests/v9/regression/test_task_log_guard_status_cell.py` (11 טסטים) חייב להישאר ירוק, ובפרט `test_genuinel |
| T-205 | 🔴 | שורת-הלוג של T-43 מכריזה "BLOCKING new entries until resolved" — ודוחפת פוש-טלפון priority=1 — על שער שרוּת OF | (`sierra_position_reconciler.py` הוא מסלול-בטיחות חי) ⇒ נרשם וממתין, לא תוקן. **התיקון המינימלי (אינו משנה התנהגות-מסחר):** להעביר את ה-`WARNING` **ואת הפוש** א |
| T-204 | 🔴 | אין לולאת-למידה — כל שיפור עובר דרך שלושה גורמים ידניים, וזו הסיבה שכשלים חיים חודשים. | `docs/handoff/CC_LEARNING_LOOP_2026-09-01.md`. **פריט 0 דחוף עד 14:30:** `OPENING_DRIVE_SKIP_V1` — הדפוס **אינו ב-`daytype_playbook.yaml` כלל** (אומת: אפס הזכרו |
| T-201 | 🔴 | אין מדידה של רוחב-הסטופ בכניסה — שני המקורות פסולים, וניתוח שנשען עליהם בוטל. | `docs/handoff/CC_WORKORDER_2_2026-09-01.md` פריט 1 — עמודת `entry_stop` **בלתי-משתנה**, נכתבת פעם אחת ב-`accept_setup`/`on_fill`, **עם טסט שנכשל אם יש יותר מאתר |
| T-200 | 🔴 | `acct_available_funds` מחזיר `DBL_MAX` (1.7976931348623157e+308) — קלט-השער של T-34 הוא סנטינל "לא-זמין" שנראה | **(א) בשער-15:30 היום, לפני כל השוואה:** `if not (0 < avail < 1e12): הקלט אינו מדיד ⇒ אפס עריכה ב-.env, אפס ריסטארט, הגודל נשאר `ruled_contracts()` כפי שהוא, ומ |
| T-199 | 🔴 | חמישה פריטי-DLL פתוחים, אפס בוצעו — ואימות-הסים נחסם על הנחה שגויה. | `docs/handoff/CC_WORKORDER_DLL_2026-09-01.md` (מחליף ומכיל את `CC_EXIT_V2`). סדר: **1 → 2 → 4 → 5 → 3**. **🔴 שער-בטיחות יחיד וקריטי:** מתג-הסים הוא **של מייקל ב |
| T-198 | 🔴 | [ממשיך את T-194 — התנגשות-מזהים שתוקנה 01.09; אותו שורש בדיוק] | `docs/handoff/CC_WORKORDER_RISK_SIZING_2026-09-01.md` — שינוי של שורה אחת (`contracts=_n` ⇒ `min(_n, budget)`), דילוג על `SIZE_CAP_CUT` כשהדגל דלוק, `RULED_FLAG |
| T-194 | 🔴 | `SIZE_CAP_CUT` בורר מבנית כניסות מאוחרות — התקרה (3.1-4.0 נק') קטנה מהסטופ שעסקת-דלתון-בקצה דורשת (8-11 נק'). | תקרה נפרדת לעסקת-דהייה-בקצה — כשהכניסה בתוך סובלנות של VAL/VAH או של קצה-היום **וגם** הדפוס REV, לאפשר סטופ עד ~1.15×(מרחק-לקצה) או תקרה מוחלטת ~11 נק', במקום ` |
| T-182 | 🔴 | `safe_execute` בולע כתיבות כושלות — סקריפט דיווח "Marked 62 trades" בעוד אפס נכתבו. | 23 אתרי-ייצור **מתעלמים מערך-ההחזרה**. **אזהרה:** "לבדוק את ההחזרה" הוא תיקון-שגוי כפי-שהוא — הפונקציה מחזירה `lastrowid`, ו-psycopg2 מחזיר `None` ל-UPDATE/DELE |
| T-180 | 🔴 | ריסטארט-בקאנד לא-מכוון ב-21:07:42 בתוך חלון-האיסור 16:10-23:00 — דיווח-עצמי; ככל-הנראה נגרם ע"י `git stash` שא | (1) **לקח מיידי, כבר חל — `git stash` אסור על הריפו החי בחלון-המסחר.** אם `pull` נכשל על unstaged ⇒ **לוותר על ה-pull**, לא לנקות את עץ-העבודה; הריפו הזה הוא מש |
| T-160 | 🔴 | P&L סינתטי במסלול PHANTOM-HEAL — הספרים מזכים ברווח-יעד עסקאות שסיירה אמרה שלא קיימות. |  |
| T-159 | 🔴 | ציון-המודעות (מדד יומי-חובה) מעולם לא היה סקריפט מחויב-גיט |  |
| T-158 | 🔴 | מוקש-ממסר רדום ב-`.env` | להפנות את שלושתם ל-`RENDER_MOBILE_URL`/localhost או להסיר את הבדיקה |
| T-153 | 🔴 | חוסם יום-הצל |  |
| T-150 | 🔴 | פער-ערימה |  |
| T-146 | 🔴 | שאלת-מייקל: למה שום דבר לא עבר מצל ללייב |  |
| T-144 | 🔴 | תיקון-קריטי שנתפס באימות: |  |
| T-143 | 🔴 | אימות-cowork: STRUCTURE_EXIT נבנה אך אינו מחובר |  |
| T-140 | 🔴 | פסיקה נדרשת ממייקל |  |
| T-101 | 🔴 | RCA LIVE orphan 24.08: Sierra +6→+5, TM=0, תחילה working_orders=0; reconciler רק דיווח “system exit never exec |  |
| T-100 | 🔴 | Context-data אינו סיבתי: TPO lookahead 92.3% + CVD כפול-סותר. |  |
| T-99 | 🔴 | SCID truth נקי 34/34, אך DB OHLC תואם 100% רק ב-20/34 — תחזית-ההכנסה חסומה. |  |
| T-98 | 🔴 | `swallow_counter` בנוי אך לא מחובר — 334 בליעות-החריגה עדיין בלתי-מדידות. |  |
| T-96 | 🔴 | ‎`S2_CVD_DETECTION_V1`‎ הוא no-op מוחלט בייצור — נמדד ‎0 שורות ב-76/76 חלונות. |  |
| T-93 | 🔴 | התבניות-הטובות: למה הן לא יורות מספיק — ואיפה הכסף באמת (34 סשנים ‎07-07→08-21‎ · 4 ו-6 חוזים · 3 רמות-סליפג'  |  |
| T-88 | 🔴 | פער-הרישום: הספרים מפספסים מילויי-יציאה — היום −$107.50 בספרים מול  |  |
| T-86 | 🔴 | S2 מת חי — `NameError: name '_atr' is not defined` ב-`process_bar`, 19/19 ברים היום מ-16:50:02 IL. |  |
| T-74 | 🔴 | מסחר-ידני באותו חשבון חוסם את יריות-הלייב — 3 מ-4 נחסמו ב-20.08 (75%) |  |
| T-562 | 🟠 | קריאת-`position_qty=0` שקרית בת-20 שנ' ביצוא-סיירה סגרה בספרים עסקה שעודה פתוחה בברוקר — ומכאן הגייטוויי שלח ה | (1) ⛔ **לא** הודעת-טלפון — Sim1+דמו, אפס חשיפת-לייב, סטופ עובד, והתרופה היא חלון-קוד + דגל שפסיקה עומדת מחייבת להשאיר כבוי ⇒ **אין החלטה שנדרשת ממייקל עכשיו**;  |
| T-546 | 🟠 | `GET /chat` מחזיר `{"items":[]}` מחוץ ל-`10:00-23:30` גם כשיש חוט שלם — ולכן אימות-המסירה שההזמנה מחייבת שקר ב | **(1) ✅ בוצע ואומת — cowork-dev ריצה 203 (06.10 11:16-11:30):** נוספה **מלכודת 32** ל-`docs/runbooks/COWORK_DAILY_READ.md` עם טבלת-הפוסקים (ממתינה ⇒ `PHONE_THRE |
| T-544 | 🟠 | חוסם-הלייב של 05.10 התחלף באמצע הסשן — מ | (1) **ריצת-RTH הבאה:** מה קרה ל-4 התאומים הפתוחים (3003/3004/3006/3008) — הם הופכים את המאזן להכרעה או משאירים אותו תלוי; (2) **מועמד-ריפליי צר** ([[דוקטרינת-הל |
| T-535 | 🟠 | שמונה עלים בשלים לפיצול במדידת-העץ של 05.10 (t529b, 65 סשנים, 4,398 מועמדים) — ובראשם SKIP שמרוויח: `OPEN_AUCT | (1) וריאנט ל-(1): ב-`responsive_normal` SHORT/mid_value → TAKE רק תחת `OPEN_AUCTION_IN` (או split נוסף: `structure`/`prior_zone`) — הרנס מול ייחוס; (2) (5): למד |
| T-531 | 🟠 | ‏`#2913 DOUBLE_TOP_AA_SHORT` (18:45 @7773.25) ישבה 4 שעות עם מקסימום +7.5 נק׳ ונסגרה בפלטן-ה-EOD ב-−23.75$ — ש | (1) על כל עסקאות live+shadow עם ≥2 מועמדי-T1 בשרשרת — איזה T1 היה מתמלא (structure-end / step / §3 מבני) וה-$ של כל בחירה, לפי סוג-יום; (2) וריאנט-יציאה: `GRADE |
| T-530 | 🟠 | קונבנציית-ORR של העץ הייתה הפוכה לשוק פעמיים ב-02.10 — `hint = היפוך-הדרייב` בשלבים A/B חסם 9 לונגים בעלייה, ו | (1) לספור ימי-`OPEN_REJECTION_REVERSE` ב-65 הסשנים — אם < ~10, לרשום "N לא מספיק" ולעצור; (2) אם מספיק: CC בונה דגל `TREE_ORR_HINT_MODE_V1` (`reverse_AB` = הנוכ |
| T-528 | 🟠 | בר-הטריגר, לא השער: ב-02.10 הרגל הגדולה של היום לא פוספסה מחוסר-ראייה — ירינו עליה בכיוון הנכון, חמש דקות מוקד | (1) להוציא מ-`review.json` את כל המקרים שבהם **ירייה חיה והכניסה-האידיאלית נופלות על אותה רגל בהפרש ≤2 ברים** — זו קבוצה מדידה ולא סיפור יחיד; (2) למדוד בהרנס א |
| T-527 | 🟠 | `SIERRA_FLAT` היא מחלקת-היציאה הגרועה בספרים — כל פעם שפלטן-ה-EOD של T-10 עושה את עבודתו, הכסף של אותה עסקה אי | (1) ריצת-הלילה 23:00-23:30 מריצה `broker_truth.py --since 2026-09-01 --write` ולאמת שהיא מכסה את `#2913` — אם לא, שורת "אין רישום-ברוקר ל-#2913" ב-LIVE_CHANNEL. |
| T-526 | 🟠 | 12 ברים של `v9_bars_5min_woodies` (01.10 `18:00-18:55 IL`) נדרסו בערכי הברים של `19:00-19:55` — ‏`+4h` במקום ` | **(1) הכותב נמצא:** ה-backfill ההיסטורי של הגשר בעלייה (`bridge/v9_history.py::historical_load`, אזור קשיח `America/New_York` מול `V9_CHART_TZ=America/Chicago`  |
| T-524 | 🟠 | ‏`live_blocked_by="margin_zero_size"` נרשם על חסימה שהמרג'ין לא גרם לה — ומסך-הטלפון מתרגם אותה ל"אין מרג׳ין פ | (1) ב-`_effective_contracts_raw` להחזיר גם סיבה (או לקבע `self._last_size_reason`) בשלושת מסלולי-האפס: `risk_budget_reject` (נושא `risk_pts` ו-`n`), `sizer_skip |
| T-523 | 🟠 | ‏`v9_footprint_journal` לא קלט שורה אמיתית מאז `05.06` — כותב-ה-epoch נדחה ~35/דקה, ו-`max(ts)` מורעל בחותמות  | (1) **קודם כל** — לקבוע אם ריפליי-[[T-478]] קורא את היומן או את `v9_bars_footprint`; זה מפריד "רעש-לוג" מ-"הרעבת-נתון לפסיקה ממתינה", וזהו גם סעיף (5) של T-521. |
| T-518 | 🟠 | הבקאנד שורף `26.9%` CPU ברציפות עם שוק סגור, פוזיציה 0 ואפס עסקאות — אותה תופעה שמלכודת 23 תיארה ב-27.09, ואין | פרופיל 60 שנ' על `pid` הבקאנד מחוץ ל-RTH (`py-spy dump --pid` או `py-spy top --pid` אם מותקן; אחרת `faulthandler.dump_traceback_later` ×3 בהפרש 20 שנ') ⇒ לזהות  |
| T-517 | 🟠 | שינוי-הכיוון השני של 28.09 — חזרה לתוך ה-IB אחרי שבירה כושלת — ושער-ההטיה שחסם את הלונגים. |  |
| T-516 | 🟠 | `v9_bars_cumulative_delta` לא קיבלה שורה אחת ב-29.09 — בעוד זרם-הברידג' דוחף תקין והפיד הקנוני חי. |  |
| T-515 | 🟠 | מצב-היפוך בזמן-אמת (תקרה/רצפה כפולה בקצה-הסשן, מברים סגורים) — נבנה, רואה את 28.09 בזמן, ואף אחד מ-9 השימושים  |  |
| T-514 | 🟠 | אחרי שני הפסדי-הלייב של 28.09 (−95$ ברוקר) — ארבעה "תיקונים" נמדדו יום-כולל מול העץ החי 3.1.0 (61 סשנים כולל 2 | שני גלאים חדשים ולא כוונון — (1) שבירת-IB עם ווליום אחרי שעה-ראשונה צרה (28.09 17:35: −35 נק׳); (2) חזרה חדה לתוך ה-IB אחרי שבירה כושלת (28.09 19:15: +43 נק׳, ה |
| T-512 | 🟠 | לעץ אין שורת-דוקטרינה לנתיב `opening_type=OPEN_AUCTION_IN/phase=D/day_type=*(Neutral_Center)` — ולכן  | (1) **מקרה-ריפליי, לא דגל** (דוקטרינת-הלמידה 09.09: "הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל") — להוסיף את הנתיב `OPEN_AUCTION_IN/phase=D/Neutral_Center` לסט-הרגרס |
| T-510 | 🟠 | `CEILING_FLIP_TOUCH2` כותב ל-`v9_trades` סולם-יעדים הפוך (‏T2 קרוב מ-T1 בלונג), ושער-המונוטוניות `#1191` שנועד |  |
| T-508 | 🟠 | מרווח-המרג'ין לחוזה אחד נאכל תוך-סשן ונהיה שלילי, והשער היחיד שנשאר בין המערכת לבין הזמנה-שתידחה הוא הברוקר עצ |  |
| T-507 | 🟠 | זוג ה-`DETECTED`/`EMIT_DECISION` הראשון של כל יום-מסחר נכתב לפני שבדיקת-הרוטציה רצה — ולכן נגרף לארכיון של היו |  |
| T-506 | 🟠 | 6 מתוך 9 `ROUTED` של 25.09 נעלמים בשקט: העץ אמר TAKE, המועמד נותב, לייב לא יצא — ושום סיבה לא נרשמה. |  |
| T-502 | 🟠 | הריסטארט של 28.09 10:57 השאיר שישה מתוך תשעת ה-LaunchAgents של MEMS26 לא-טעונים — ביניהם `mobile_relay`, כלומר |  |
| T-498 | 🟠 | שער אישור-הכניסה (`S4_ENTRY_CONFIRM_V1`) בודק בלייב לפעמים בר שנפתח לפני שניות — מרוץ בין כתיבת-שורת-הבר לבין  | אחרי הריסטארט של ב׳: כל `BLOCKED by entry-confirm` מצטט `o/c` של הבר **הסגור** הקודם (להשוות לשורת-הבר ב-DB); ובריפליי-הלילה של ב׳ — ריפליי ולייב מסכימים על השע |
| T-497 | 🟠 | הליגר-המועמדים זרק כל אירוע `DETECTED` שה-`signal_bar_ts` שלו הגיע כמחרוזת-epoch — אותה מחלקה כמו [[T-495]]. | אחרי הריסטארט של ב׳: `grep -c 'candidate_ledger:DETECTED' /tmp/backend.err.log` מאז ה-lstart ⇒ 0 ⇒ ✅. |
| T-495 | 🟠 | אחרי ריסטארט באמצע-סשן העץ קרא קיצוני-סשן מהאתחול ולא של היום — כי אירועי-הבר החיים נושאים `ts` כשניות-epoch,  | אחרי ריסטארט-קדם-הפתיחה של ב׳ 28.09: (1) `grep DatetimeFieldOverflow` מאז ה-lstart החדש ⇒ 0; (2) קיצוני-הסשן בכרטיס-העץ = השפל/השיא האמיתיים של היום. שניהם ⇒ ✅  |
| T-494 | 🟠 | עשרה וריאנטים יום-כולל מול התצורה החיה (live0927, 60 סשנים Σ+1,373.75$) — אחד לכל נתיב שדולף ב-[[T-493]]; מדינ | "כן" של מייקל לחבילה (דוח-הלילה §5) ⇒ להעביר את העלים מ-`harness_out/t494/tree_pkg.yaml` ל-`config/decision_tree_v3.yaml` עם `ruling:` (הציטוט) + `measured:` (ה |
| T-493 | 🟠 | ריפליי התצורה החיה (עץ-V3 מחליט, נטען 25.09 19:15) על 61 הסשנים הנקיים + ביקורת כל נתיב בעץ (מייקל 27.09 14:14 | להכניס ללולאה-הלילית (תוכנית §6 שלב 6): אחרי EOD — ריפליי-היום בתצורה החיה + `gate_audit.py` + `tree_measure.py`; כל נתיב חדש שמסרב לכסף או מפסיד ⇒ וריאנט ⇒ יום |
| T-492 | 🟠 | פיד-הפוטפרינט מיוצא ואינו נכנס: ה-DLL כותב `footprint.json` כל כמה שניות, ו-`v9_bars_footprint` עומד על 22.09  | (1) בקדם-הפתיחה הבא, **בפוזיציה 0 ולפני 16:10**: `scripts/mems26_snapshot.sh "bridge-restart-footprint"` (‏CLAUDE.md §*Change-Safety*: הברידג' הוא משטח out-of-g |
| T-491 | 🟠 | מונה-ההסלמה של מועמדי-הענפים התאפס בשקט ביום שהעץ עלה לאוויר: אותו שער, באותה נסיבה בדיוק, נספר תחת שני שמות — | (1) למפות את שני מרחבי-השמות למפתח-צבירה אחד ב-`day_review.py` (‏`tree:X` ⇄ `dalton_intent:X` ⇒ `gate_key=X`) — **תיקון-דיווח בלבד, אפס נגיעה בשער עצמו ואפס דגל |
| T-490 | 🟠 | `select ts::time(0), … from <t> order by ts desc limit N` מחזיר את השורה עם  | (1) להוסיף מלכודת-18 ל-`docs/runbooks/COWORK_DAILY_READ.md` עם שלוש ריצות-הבקרה, והכלל: **לעולם לא לקסט עמודה לשמה-שלה בשאילתת-"אחרון"** — או alias מפורש (`ts:: |
| T-488 | 🟠 | כל הודעת-טלפון עלולה להופיע  | (1) לתקן ב-`render_mobile_relay/app.py::get_chat` — ⛔ **לא** לכווץ את המפתח ל-`(sender, text)` בלבד: מייקל חוזר על הודעות קצרות באמת (‏`11:11:49Z` = "כן"), וכיו |
| T-484 | 🟠 | פסיקת-מייקל התקבלה: להדליק את ענף-הצל `auction_B_trend_break` חי — "כן" (25.09 14:11:49Z, `[56436c0f]`), בתשוב | ✅ **נסגר בריצה 12 (שער-15:30, cowork-dev 25.09 16:00) — מייקל לא נדרש ללחוץ על כלום.** המרוץ אושר במדידה: `.env` mtime `15:44:06` מול `[boot] … pid=87958` ב-`15 |
| T-482 | 🟠 | `phone_request_guard.py` עיוור להודעת-תמונה-בלבד — בדיוק המחלקה שבגללה הוא נבנה. | לצרף ל-`COWORK_DAILY_READ.md` §המלכודות כמלכודת-21 (*"הודעת-תמונה אינה נספרת כבקשה — השומר קורא טקסט"*). |
| T-480 | 🟠 | עץ-ההחלטות V3 — עץ אמיתי, מקונן, בסדר של מייקל (25.09 12:10: "קודם סוג פתיחה, סוג היום, תבנית מתאימה… ממש צריך | (0) ✅ 25.09 19:15 ריסטארט בוצע (אישור מייקל) — נטען ואומת: `mode on`, תוכנית LONG ייקח/SHORT לא, fire_drill GO. היה בתור: פיצול `structure` תחת Normal (`take_wi |
| T-478 | 🟠 | מערכת 3 — נתונים קודם: להחזיר את פיד-הפוטפרינט (מייקל 25.09: "לייב מלא היום כולל מערכת 3" ⇒ ההמלצה שהתקבלה: "ט | (1) ריסטארט ברידג׳ + בקאנד בשער 15:30 של 28.09 (או תור-הלילה 23:00 לברידג׳ בלבד) ⇒ לאמת `select count(*) from v9_bars_footprint where ts > now()-interval '1 hou |
| T-473 | 🟠 | בדיקת-הנוכחות של עמודי-הערב בודקת נתיבים שאינם קיימים ⇒ `MISSING` שקרי. |  |
| T-471 | 🟠 | ארבעת עמודי-הערב של 24.09 לא רצו בחלון שלהם — ואין עמוד-יום למייקל עד שירוצו. | (1) `broker_truth.py --since 2026-09-01 --write` — לאמת `n/N` מלא; `#2340` כבר נושאת `pnl_sierra −38.75` ⇒ צפוי `1/1`, וכל פער ⇒ שורת *"אין רישום-ברוקר ל-#id"*. |
| T-467 | 🟠 | מסווג-ה-post-mortem עיוור להחזרת-רווח: `#2340` (24.09, עסקת-הלייב היחידה של היום) ירדה עד `7749.25` — `13.00`  |  |
| T-463 | 🟠 | `BarLevelDetector.on_bar` זורק `InvalidTransition: CLOSED -> CLOSED` כששני יעדים נפגעים באותו בר — והחריגה מפי | **(1)** **מקרה-ריפליי** על `24.09 09:40 ET` בסט-הרגרסיה — דוקטרינת-הלמידה: תקרית ⇒ ריפליי, **לא דגל**. המקרה חייב לשחזר שני יעדים על בר אחד. **(2)** לקרוא אם הל |
| T-462 | 🟠 | 140 מתוך 219 שורות-הליגר חסרות `ts` לחלוטין — כל ניתוח מתוארך של הליגר רואה 79 שורות בלבד, וזה חשוד כתורם ישיר | לאתר את אתר-הכתיבה של `candidate_ledger:DETECTED` (החשוד: `float(ts)` במקום `isoformat()`), לנרמל ל-ISO-עם-TZ, מקרה-רגרסיה שנכשל על epoch-float, ואז להריץ מחדש  |
| T-460 | 🟠 | `mfe_pts` בפלט-ההרנס סותר את עצמו ב-5 מתוך 10 רשומות שנבדקו — מדווח תנועה-לטובתנו גדולה מהמרחק ל-T1, בזמן ש-T1 | לאתר את חישוב `mfe_pts` בקוד-ההרנס ולבדוק חלון-זמן וסימן (חשד: מחושב על הסשן כולו ולא על תקופת-ההחזקה); מקרה-רגרסיה: עסקה שיצאה ב-STOP חייבת לקיים `mfe_pts < t1 |
| T-455 | 🟠 | המפתח `exit_ts` שקרי בשני המצבים — צל  | **(1)** **הזול והמכריע ראשון, מחוץ ל-RTH:** לקרוא באיזה מפתח מסננים `scripts/review_report.py` · בונה-*"מה עובד"* · `scripts/gen_tree_board.py` · `scripts/day_r |
| T-454 | 🟠 | דיברגנציית-הסטופ של הליגר היא פנטום קבוע — `sierra: 7680.0` זהה בכל שמונה עסקאות-הלייב האחרונות, ומייצרת `CRIT | **(1)** **הזול והמכריע ראשון:** לקרוא את הכותב של `divergences.sierra.stop` ולענות על שאלה אחת — האם `7680.0` מגיע משדה-סיירה חי, או מברירת-מחדל/ערך-מאותחל? שור |
| T-453 | 🟠 | ירי-חוזר בצל — `19.1%` משורות-הצל הן אותה (מערכת · תבנית · כיוון) באותה דקה; בלייב `0.0%`. | **(1)** **הבדיקה הרגישה ראשונה, והיא בת-דקה:** `R4n` (דחיית-קצה-IB, `N=24`, `+$291`, `+12.14$`/עסקה) הוא המועמד-לצל של [[T-450]] — `N` קטן ⇒ להריץ אותו על בסיס  |
| T-452 | 🟠 | `v9_day_type_state` עצרה ב-`14:00` — `187` דק' בלי שורה, בזמן שמכונת-סוג-היום עצמה חיה ומתקדמת; ו-`/api/v9/day | **(1)** **בשער-קדם-הפתיחה של מחר, מיד אחרי הריסטארט:** `select max(ts), count(*) from v9_day_type_state where ts>=current_date` — אם נכתבת שורה בריסטארט **ועוד  |
| T-451 | 🟠 | `v9_bars_cumulative_delta` — `0` שורות היום מול `126`/יום בששת ימי-המסחר הקודמים; וה„הפרכה" שנרשמה ב-[[T-442]] | **(1)** **הדגימה המכריעה של `16:36`** שנקבעה ב-[[T-442]] — הופעלה כסקריפט-רקע `/tmp/t451_sampler.sh` ⇒ פלטה ל-`/tmp/t451_sample.txt`: אם `rows_today > 0` ⇒ הפער |
| T-447 | 🟠 | `flag_guard` בודק רק דגלים שרשומים ב-`RULED_FLAGS.yaml` — ולכן `PASS 264/264` הוא עיוור ל-6 דגלים דלוקים-כבריר | **(1)** פסיקת-מייקל על 6 הערכים כמות-שהם (כולם ON היום בפועל ⇒ רישומם **אינו** שינוי-התנהגות, רק הפיכת המצב-הקיים לגלוי) — שאלה אחת: לאשר רישום `expected:"1"` ל |
| T-435 | 🟠 | `scripts/start_all.sh` מרים את הבאקנד על סופרוויזר שונה מה-LaunchAgent — לוג-עיוור, שלושה דגלים חסרים ולולאת-ר | **(1)** להכריע מי הבעלים הקנוני של הבאקנד — LaunchAgent (מומלץ: הוא נושא את 13 הדגלים ואת `KeepAlive` שהמערכת מסתמכת עליו) — ואז **או** ש-`start_all.sh` יקרא `l |
| T-432 | 🟠 | `9` ממבחני-הרגרסיה של נתיב-הפתיחה אדומים — ואדומים כבר על הקוד ש | **(1) היום אחרי ההרמה — תצפית-לייב, אפס עלות:** בבר-האישור `16:45` לבדוק אם הזרע מחזיר כיוון או `None` (`grep "^$DAY" /tmp/backend.err.log \/ grep -E "S1-OPENIN |
| T-431 | 🟠 | בקשת-מייקל בכתב 21.09 10:24 — "לדאוג לריסטארט ליישם את השינויים שדוּוחו ולתת דיווח שהמערכת מוכנה למסחר היום" — | (0) ✅ **אומת 21.09 11:10 — אין ריסטארטר שני:** `list_scheduled_tasks` ⇒ `mems26-preopen-restart-2109` **אינו קיים**, ושלוש משימות-הריסטארט בעץ (`1009`/`1109`/`1 |
| T-425 | 🟠 | אותו שורש של [[T-422]], שני צרכנים נוספים: `_oe_bars` הוא רשימת-snapshots קפואים, ו-`get_opening_dir_fusion` + | (1) **אין לתקן בלי פסיקה + מספר-ריפליי.** בניגוד ל-[[T-422]] — ששם הכלל "בר-אישור = בר סגור" כבר פסוק והתיקון רק החזיר את הקוד לדוקסטרינג שלו — כאן שינוי המקור  |
| T-423 | 🟠 | שמירת-היתום נדגמת ברגע אחד (`last_price`) ולא על טווח-הבר ⇒ חריגה אמיתית של קו-הסטופ עברה בלי האזעקה שפסיקת-מי | (1) **להכריע קודם על מקור-המחיר** — `sierra_state.json` כבר מכיל `high_during_pos` / `low_during_pos` שהבודק קורא באותה קריאה עצמה, כלומר התיקון הוא **החלפת-שדה |
| T-421 | 🟠 | ה-TM מסיק `T1` על מחיר שאין בו הזמנה חיה — ורושם 141 שורות "awaiting Sierra fill" ב-5 דקות על עסקת-לייב פתוחה. | (1) **להכריע קודם אם `7680` הונח או שונה** — יומן-סיירה של היום מכיל `User order modification. Requested Price: 7684.00. Requested Quantity: 1`, כלומר הזמנות ** |
| T-420 | 🟠 | שני שלבי-המשפך הראשונים של הליגר נכתבים בלי `ts` בכלל ⇒ אי-אפשר לחתוך אותם בזמן. | להוסיף `ts` בכתיבת שתי השורות באותו מקור-זמן שממנו נכתב `GATE_DECISION` (UTC ISO, לפי Rule 4 — TZ מפורש בערך עצמו), ולהוסיף טסט שנכשל על שורת-ליגר בלי `ts`. עד  |
| T-419 | 🟠 | הליגר כותב `trade_id` כבוליאני `true` במקום מזהה — וכל ספירה דרך השדה הזה שקרית. | למצוא את אתר-הכתיבה (הליגר נכתב מ-`backend/v9/services/candidate_ledger.py`; לחפש השמה מסוג `trade_id=bool(...)` או `trade_id=<truthy expr>` במקום המזהה עצמו),  |
| T-418 | 🟠 | בדיקת-בעלות-הריסטארט נשענת על פקודה שמחזירה את ה-pid הלא-נכון: `lsof -ti :8000 / ⚪ ארכיון 22.09 — נבדק בשער 21 | (1) לקרוא את המאזין **רק** עם `lsof -nP -iTCP:8000 -sTCP:LISTEN` (או `lsof -ti :8000 -sTCP:LISTEN`) ואז `ps -o lstart= -p <pid>` — **לא** `lsof -ti :8000 / head |
| T-416 | 🟠 | המכונה בהחלפת-זיכרון (`swap 2,617MB`, ‏`unused RAM 50MB`) — וריסטארט-קדם-הפתיחה עומד לרוץ עליה. | (1) **לשחרר ≈1.3GB מצרכנים-שאינם-מסחר** (`chrome 633 · adobe 297 · claude-agents 391`) — **אין לגעת במחסנית-המסחר** (`backend`/`sierra`/`postgres`/`bridge`/`pho |
| T-415 | 🟠 | [הורד מ-🔴 ב-18.09 12:14 — פסיקת-מייקל 12:05 הורידה את הגודל-הפסוק לחוזה אחד, והפער חדל לחסום. הצעד-הבא: אימות  | (1) **למדוד מחדש** את `acct_available_funds` מ-`sierra_state.json` לפני `fire_drill` — היתרה עשויה להשתנות בן-לילה; **אל תסתמך על `490.64`**. (2) אם עדיין `< 77 |
| T-414 | 🟠 | `safe_writer` דוחה כמחצית מכתיבות-`v9_decision_vectors`: epoch גולמי כמחרוזת נדחף לעמודת-timestamp — רגרסיה שנ | (1) **לאמת את השורש לפני תיקון** — `grep -rn "v9_decision_vectors" backend/` ולזהות את **שני** הקוראים; אם יש רק אחד, ההשערה על 50% שגויה והמספר דורש הסבר אחר.  |
| T-413 | 🟠 | כניסות-אידיאליות על כל הימים (מייקל 17.09 20:00: "לא העסקאות בפועל — הסטאפים שהיו צריכים להיכנס לתנועות הארוכו | F18 — recall/precision/$ לחתימות S1-S6 על כל הברים, OOS+CI+plateau, walk-forward (‏% ימים ≥ $200), שתי המשפחות (תחילת-רגל / המשך-בקיצון) בנפרד ⇒ `IDEAL_ENTRIES_ |
| T-412 | 🟠 | דיוק REACTIVE/INITIATIVE עם ראיות (מייקל 17.09 19:20: "לבחון על התבניות שלנו ולדייק, לא לבנות מחדש"). | `evidence.py` + ראיות בתוך `_detect_reactive/_detect_initiative` תחת `S2_TRIGGER_QUALITY_V1=shadow` (ברירת-מחדל בקוד) · ריפליי מתוקן + הרנס 5 סשנים ⇒ פסיקת-מייק |
| T-410 | 🟠 | Oracle validation v1 (cc `cd1b888a`, 18:44) — הקריאה המקצועית: | F16 (תיקוני-בודק + תאי תנאי×שלב×סוג-יום); יום א': עמוד-הענפים מבוסס על v2 בלבד, עם המספר המבני (ב) כנקודת-הפתיחה של הדיון — המפיקים הם הבעיה, לא השערים. |
| T-409 | 🟠 | פרוטוקול-דיוק ל-Oracle (מייקל 17.09 18:20: "מה קלוד קוד יכול לבדוק כדי לדייק?"): | `docs/reports/ORACLE_VALIDATION_2026-09-18.md`; cowork מסנן מזה את שורות-העץ ליום א'. **כלל:** לא משנים הגדרות כדי לשפר תוצאה — מדווחים. |
| T-408 | 🟠 | Oracle (מייקל 17.09 17:58): במקום לשאול "איזו תבנית", לשאול את הברים "איפה כניסה הייתה עובדת" — ולגזור מזה תנא | F14 — ה-Oracle בסריקה הלילית עם ניהול ($/עסקה במודל הקבוע), תנאים נוספים (ראש-כתפיים, ספל-ידית, פולבק מדויק, שבירה מאזור-ערך), פילוח שלב×סוג-יום; יום א': 10 התנ |
| T-406 | 🟠 | פיד-ההחלטות אינו רושם את חסימת-`T-43` כסיבה — מועמד שנחסם ע"י פוזיציה-זרה נראה בפיד כ-`shadow_only` בלי סיבה כ | לא "להוסיף סיבה" אלא **(1)** להזרים ל-`live_block_reason` את הסיבה שכבר קיימת בנתיב-ב (שורת-ה-`CRITICAL` של `pre-send`), ו**(2)** לברר למה נתיב-א מגיע ל-`shadow |
| T-404 | 🟠 | נוהל-הפתיחה מאחר: סוג-הפתיחה ננעל בבר 4 (16:50), ודלתון מזהה Open-Drive בבר 1-2. | (1) F11 — שדות-פתיחה בווקטור (cc, מחוץ ל-RTH); (2) הסריקה הלילה: על 85 סשנים — כמה פתיחות-דרייב (בר 1-2 ≥1.5×ATR בלי חזרה 50%) היו, ומה נתנה כניסה עם-הדרייב בעצ |
| T-403 | 🟠 | מרדף בקצה: הכניסה החיה #1806 INITIATIVE_SHORT 17:10 @7683 — 0 ברים מהשפל, 30 נק' מהפתיחה = 4.3×ATR — התהפכה מי | הסריקה הלילה — N ו-Σ$ של כניסות-BREAK עם 0 ברים מהקיצון ומהלך ≥3×ATR מהפתיחה, לפי שלב; אם שלילי ⇒ שורה חיה ב-v2 (יום א'). |
| T-396 | 🟠 | עסקאות-צל לא נסגרות בסוף-הסשן ⇒ ה-TradeManager מנהל אותן לנצח ⇒ backend ב-55-80% CPU, ~1,000 שורות-לוג/דקה, `S | (א) בבר-הסגירה של ה-RTH (‏23:00 IL) — כל עסקת-`shadow` ב-FILLED/PARTIAL נסגרת `STALE_UNRESOLVED` (אותו כלל-כנות של הסקריפט: בלי exit_price מומצא); (ב) הידרציית  |
| T-395 | 🟠 | התנגשות-מספור: `T-367` ו-`T-368` מסמנים שני פריטים שונים כל אחד — והמקוריים עוד פתוחים. | cc ממספר את עבודת-הבוקר מחדש ל-**`T-396` (Variation with extension)** ו-**`T-397` (System 6 stuck→BE)**, מעדכן את שתי ה-`note` ב-`config/RULED_FLAGS.yaml` למספר |
| T-394 | 🟠 | גרסת-עץ v2 — הענפים הראשונים מהנתונים (מ-T-389), מאושרים ע"י מייקל ✓/✗ על עמוד אחד, נבדקים כמכלול על 85 סשנים  | דוח-ענפים מוצע ליום א'; כל ענף: מצב ⇒ פעולה ⇒ ראיה. ‏21.09 רץ על הבסיס המוקפא או לא סוחרים — פסיקת-מייקל עד א'. ⏳ **20.09 10:46 (cowork-daily, חידוד-דדליין):**  |
| T-393 | 🟠 | דוח-EOD אוטומטי לטלפון בלי תלות באפליקציית-Cowork | אחרי T-389 (הסקריפט משתמש באותו חישוב-פער ליום אחד). LaunchAgent = משטח מחוץ-ל-git ⇒ `mems26_snapshot.sh` לפני; `KeepAlive` לא; ריצה חד-פעמית ב-23:10. שולח דרך  |
| T-392 | 🟠 | הגירת הכללים הקיימים לעץ-YAML בלי שינוי-התנהגות, ומחיקת הדגלים שלהם ("מסירים לפני שמוסיפים"). | אחרי T-391 — cowork כותב את שורות-ה-YAML עם `measured:`; קריטריון-מחיקת-דגל: `scripts/replay_admits.py` על 85 הסשנים ⇒ **אפס הבדל** בהחלטות מול הבסיס. העמוד למי |
| T-391 | 🟠 | `_match_condition` (‏`dalton_playbook.py:102`) מכיר רק `opening_type`/`day_type` ⇒ כל כלל שמערב מיקום/הרחבה/וו | לתקן את שתי השורות שמצטטות קובץ-רפאים, ולכתוב גולדן-תאימות-אחורה אמיתי שמעביר את שורות-`config/dalton_playbook.yaml` הקיימות דרך `_match_condition` עם `vector=N |
| T-390 | 🟠 | וקטור-מצב (`SituationVector`) מחושב פעם אחת בשער לכל בר-החלטה ונרשם ל-`v9_decision_vectors` — גם כשאף מפיק לא  | cowork כותב `CC_NOW_2026-09-17_T390_SITUATION_VECTOR.md` אחרי דוח-T-389 (השדות נגזרים ממנו). קריטריון: התנהגות-זהה על 15.09+11.09 בהרנס (מחוץ ל-RTH), guards ירו |
| T-389 | 🟠 | ניתוח-פער היסטורי על 85 סשני-RTH (יוני-ספטמבר): מה היום הציע מול מה נלקח, לכל תנועה שהוחמצה — אין-setup / נחסם | (1) לאמץ את `_systems_blob_at_entry` מ-`scripts/replay_s7_acceptance.py:55,75` — אדפטר שכבר קיים, לא לכתוב שלישי; (2) לחבר `classify_replay`; (3) `blocked_by` ⇒ |
| T-388 | 🟠 | שתי קריאות-`acct_available_funds` ב-`bar_level_detector` אינן מנקות את סנטינל-ה-`DBL_MAX` ⇒ `margin_precheck`  |  |
| T-387 | 🟠 | הגולדן של `§5a NO_LABEL` (‏= מה שההזמנה קוראת לו "T-365")  | (1) **הפסיקה על [[T-373]] היא החסם האמיתי** — כל עוד `ib_locked = ib_found`, `§5a` אינו *"אחרי נעילת-IB"* אלא *"אין תווית ⇒ צל"* ללא תנאי, וגם אחרי T-365 כך ייש |
| T-386 | 🟠 | מערכת-4 שלחה עסקת-`mode='live'` ב-`2` חוזים בעוד הפסיקה העומדת היא `3` — ונתיב-הגודל שלה אינו קורא את `ruled_c | (1) **לא תוקן בכוונה, ומסיבה מפורשת:** זהו **דגל-גודל + נתיב-סיכון-מסחר** ⇒ `CLAUDE.md` §"אסור לגעת בדגלי-גודל (פסיקת 31.08; T-225 נגרם מהנוסח הישן)" + אסור שינ |
| T-385 | 🟠 | הספרים והברוקר חולקים על אותה עסקה — `$11.25` על `#1647`, והשורש הוא שהספרים רשמו את מחיר-האות כמחיר-המילוי. | (1) **לא תוקן בכוונה, ומסיבה:** זו שכבת-מדידה בנתיב-הכניסה של `TradeManager`, ושינוי קוד באמצע `RTH` אינו בסמכות-ניטור (§4 של `COWORK_DAILY_READ`) ⇒ לתיקון אחרי |
| T-381 | 🟠 | לוג-האפליקציה נמחק בכל ריסטארט ⇒ שלושה שדות-חובה בסיכום-היומי אינם ניתנים-למדידה מבנית — `S1DayDir` · `EntryGu | (1) **הזול והמכריע, בלי לגעת ב-plist:** להוסיף גיבוי-לוג ל-`scripts/mems26_snapshot.sh` — הוא כבר רץ לפני כל שינוי out-of-git ושומר `.env`+plists, והלוג שייך לא |
| T-380 | 🟠 | זרם `bars_5min` תקוע על באטץ' של אתמול ויורה `~1,150` שורות `ERROR` בשעה — רעש שקובר שגיאות-אמת; הפיד הקנוני ( | `bars_5min` הוא נתיב-legacy שאף צרכן-מסחר אינו קורא, והפער קובץ⇄נדחף הוסבר ⇒ **שני התנאים שחסמו את (א) התקיימו**. הפעולה: **(א) להפסיק את דחיפת זרם `bars_5min`* |
| T-378 | 🟠 | מפקד-הרמות בחלון-מתגלגל (~30 דק') עיוור-מבנית לפרצי-לוג שנגמרו — `22,108` שורות משלוש משפחות החזירו `0` בחלון, | (1) **לשנות את ברירת-המחדל של מפקד-הרמות בריצות-הניטור שלי מ"חלון אחרון" ל"מכנה-סשן `16:30→now`"**, ולהדפיס תמיד את שתי העמודות זו-לצד-זו (`RTH` מול `win`) — פע |
| T-377 | 🟠 | שלוש שכבות-גודל החזירו שלושה מספרים שונים באותו חלון-מסחר — `5` פסוק · `4` מרג'ין · `2` מ-`§6` — ואף אחד מהם ל | (1) **לקרוא קוד ולהכריע — הזול והמכריע:** לאתר את אתר-הקריאה של `§6 RISK_BUDGET capped by sizer` ב-`sierra_command` ולקבוע אם הוא על נתיב-הלייב או על מועמדי-צל  |
| T-374 | 🟠 | פוזיציה-זרה שלישית באותו יום (לונג `8` @ `7692`) — הפנוי `$372-432` מול `$1,931` הדרושים לגודל-הפסוק. | ⚠️ **אינו נטען:** לא נקבע מתי בדיוק נפתחה (בין `16:22`, שבו נמדד `pos=0` ב-`13/13`, ל-`17:14`), ולא נקרא ה-`order_id` — יומן-הפעילות בינארי ([[T-368]]). **⬆️ הס |
| T-371 | 🟠 | `pnl_sierra` הפסיק להתמלא אחרי `09.09` — המאמת שנועד לחסום רווח-סינתטי כבוי בשקט. | (1) לזהות את הכותב של `pnl_sierra` (`grep -rn "pnl_sierra" backend/` — חשודים `fill_poller.py`/`sierra_ledger.py`) ולקרוא מתי הוא רץ; (2) להצליב את `11.09` מול  |
| T-370 | 🟠 | ה-backend עלה מחדש `15:35:03`, דקה אחרי `push` — הטריגר לא זוהה, והסיכון הוא ריסטארט-אוטומטי בתוך RTH. | (1) **מיידי וזול — עד לזיהוי: אין `push` בין `16:10` ל-`23:00`.** (2) לזהות את הטריגר: `launchctl list / grep mems26` + `StartInterval`/`WatchPaths` בכל ה-plist |
| T-369 | 🟠 | שני סוכני-cowork שלחו הודעת-GO נפרדת לאותו טלפון באותה דקה — תקלת-תיאום, לא תקלת-מדידה. | לפני שליחת הודעת-שער — `GET /chat` ל-`5` הדקות האחרונות; אם כבר יש הודעת-שער של סוכן אחר על אותו קומיט ⇒ **לא לשלוח**, ולכתוב את הדלתא ל-`LIVE_CHANNEL` בלבד. בנ |
| T-367 | 🟠 | תיקון-שורש ל-[[T-359]]: הרקונסיילר משווה `TM` מול מקור נעול-לסימבול-הצ'ארט ⇒ גלגול-חוזה משחרר את `T-43` על מקו | **לא לגעת לפני סגירת-הפתיחה של היום.** אחריה — cc קורא את `backend/v9/services/sierra_position_reconciler.py`, מציע את מקור-ההשוואה ברמת-חשבון, ומביא ריפליי/סים |
| T-366 | 🟠 | כתיבת-הליגר לא-נבחנה מאז `11.09` — חייבת אימות אחרי `16:30`. |  |
| T-352 | 🟠 | `17,583` שורות `ERROR` ביום-א' שוק-סגור, כולן חתימה אחת — `TS-OFFSET-GATE`; ו-`53,522` מ-`67,953` שורות-הלוג ש | (1) **למדוד מחדש אחרי `01:00 IL`** כשברים טריים מגיעים: אם הזרם **נעצר** — זו תופעת-שוק-סגור וסוגרים את הפריט; אם **נמשך** — זו מחלקה חדשה ולא סוף-שבוע, והיא שי |
| T-351 | 🟠 | `v9_trades.pnl_sierra` אינה בעלת-בעלים-יחיד: שני כלים כותבים אותה משני מקורות שונים ומקבלים מספרים שונים לאותה | (1) **מייקל קובע מי הבעלים** של `pnl_sierra` — יומן-המילויים או `TradeActivityLog`. עד שיש פסיקה **אין להריץ `--write` באף אחד מהשניים**, כי כל ריצה דורסת את קו |
| T-349 | 🟠 | ארכיון-הליגר אינו קורפוס אחיד: `72.8%` מהשורות מגיעות מ-4 קבצים בלבד (`08-11` · `08-17` · `08-18` · `08-19`),  | (1) **כל דוח שמצטט מכנה-ארכיון חייב להחריג את 4 הקבצים בשמם** (`08-11`/`08-17`/`08-18`/`08-19`) — **ולא לחתוך לפי טווח-תאריכים**, כי הטווח אינו רצף. שתי האמירות |
| T-348 | 🟠 | ‏`21.4%` מהפסדי-הצל נחתכים ע"י כלל-סדר-הבדיקה ולא ע"י השוק — הבר שסגר אותם בסטופ נגע גם ב-`T1`. | (דוקטרינת-הלמידה: "הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל"): (1) ריפליי דקה/טיק על `116` הברים הדו-משמעיים ⇒ להוציא **מספר**: בכמה מהם `T1` נגע לפני הסטופ; (2) עד |
| T-347 | 🟠 | `EXIT_TRACK_ACTIVITY_V1` דלוק ו-`FillPoller` מכריז על עצמו `BLIND` — מקור-התמחור של סיירה קפוא `46.3` שעות, וה | לאמת ש-`TradeActivityLog_2026-09-14_UTC.37138283.data` **נוצר** ושה-JSONL **מתקדם בתוכן** (‏`scan_ts` חדש, לא רק `mtime`) ברגע האירוע הראשון. אם אחרי הפתיחה הפו |
| T-346 | 🟠 | מוני-היום של השער (`trades_today`/`daily_pnl`) מדווחים `3` ו-`$47.50` ביום עם  |  |
| T-345 | 🟠 | עבודת-T-328 לא-מקומטת של cc יושבת על הדיסק 20 שעות וחוסמת את `git pull` — הצעד הראשון של שער-קדם-הפתיחה. |  |
| T-344 | 🟠 | מועמד-לייב יחיד עבר את  | **(1) 🔑 להפריד את השומר לשני מקרים** — פוזיציה זרה **מוכחת** (`order_id` שאינו בלוג-שלנו) היא **לא** "orphan/missed-fill" ולכן גם לא `CRITICAL ... Investigate`; |
| T-342 | 🟠 | ‏`live_slot` נתקע `13` דק' `32` שנ' אחרי סגירת `1512`, על ייחוס-בעלות הפוך ועל צילום-מצב שהתיישן תוך `26` שניו | **(1) 🔑 `T-43c` חייב לקרוא ל-`position_is_foreign()` לפני שהוא כותב `ownership=ours`** — הפונקציה **כבר קיימת** מ-[[T-311]] ו-`RECONCILER_OWNERSHIP_AWARE` חי מ- |
| T-341 | 🟠 | ~~המערכת שלנו שלחה `FLATTEN_ACCOUNT` ב-`21:33:37` שאיש לא ביקש~~ — הופרך 11.09 `22:16`: מייקל ביקש, מכפתור-הפל | בוצע חלקית**: האירוע הזה יוחס — אבל דרך לוג-הרלה, לא דרך הלוג-שלנו. סעיפים (1)+(2) נשארים מילה-במילה, וסעיף (3) **נענה**: יד-אדם, לא באג-לוגי.** **(1) 🔑 לכתוב א |
| T-340 | 🟠 | ‏`TradeManager` מדווח סטופ `7677.00` על `1512` בעוד הפקודה שעל ספר-סיירה יושבת על `7672.25` — והשוק הוכיח את ה | **(1) להוסיף `stop_price` לייצוא-הפקודות ב-DLL** (היום `orders[]` נושא `id/type/bs/price/qty` בלבד) ⇒ בלי זה **אי-אפשר בכלל להבחין** בין הדק ללימיט על `type=3`, |
| T-339 | 🟠 | הוראת-מייקל 11.09 `20:24:48` (‏`id=65774fa6` בת'רד-הטלפון): "אם אני סוגר את העסקה תנסה לעשות במחיר הטוב ביותר  | **(1) ההבהרה היחידה שנדרשת ממייקל, במשפט אחד:** האם "אני סוגר" = **אתה ביד ב-Sierra** (ואז ההוראה היא בעצם בקשה שהמערכת **לא** תשטח מתחתיך — כלומר [[T-338]], וה |
| T-332 | 🟠 | ‏705 אזעקות `System6 target_divergence` ב-8 דקות (‏~80/דק') — השורש הוא ש-`t2`/`t3` בשורת-ה-DB של 1498  | (1) **לקרוא את הקוד לפני כל תיקון** (Pre-LIVE: diagnose first) — לאתר את **הכותב** של `t2`/`t3` לשורת-`v9_trades` בנתיב `gateway → TradeManager`, ולהכריע אם `St |
| T-331 | 🟠 | נגיעה-יד בברקט של עסקת-לייב חיה (1498, חוזה-4) ב-`18:40:05` — והמפריד מוכיח שהמערכת שלנו לא שלחה אותה. | (1) **שאלה למייקל, לא שינוי-קוד:** האם נגיעה-יד בברקט של עסקת-מערכת היא מהלך מכוון ומותר (ואז צריך **מסלול-רישום** — תיוג-מייקל כנתון שנשמר, לפי [[LEARNING_DOCT |
| T-321 | 🟠 | שער-המיקום של `DAYTYPE_LOCATION_GATE` ירה בלייב לראשונה היום — ו-13 מ-13 החסימות הן בצירופים שהדוקטרינה  | (1) **המדידה המכריעה, לפני כל דגל** ([[LEARNING_DOCTRINE]] — הוראה ⇒ קודם ריפליי): לספור על סט-הרגרסיה את **חיתוך (kinds מותרים)×(מפיקים חיים)** — כמה מועמדים * |
| T-320 | 🟠 | ‏6,599 שורות `[ERROR]` ביום מחתימה אחת — `TS-OFFSET-GATE` דוחה את `bars/5min` בקצב ~1,180/שעה, וזה יבלע כל שגי | **(1)** לקבוע אם `v9_bars_5min` עדיין **נצרך** ע"י מישהו — `grep -rn "v9_bars_5min\b" backend/ bridge/ scripts/` והפרדה מפורשת מ-`v9_bars_5min_woodies`. אם אין  |
| T-316 | 🟠 | ‏`kind` לפי מיקום אינו ניתן למדידה היום — אין ולו רשומת-ליגר אחת הנושאת TPO. אומת עצמאית ע"י cowork 11.09 13:0 | **(1) הכרעה על IB לפני כל חיווט** — לקרוא את נתיב-הכתיבה של `v9_tpo_sessions` ולקבוע אם `ib_high/ib_low` בשורת-GLOBEX הם באג או כוונה. אם כוונה — `tpo_snapshot` |
| T-306 | 🟠 | צד-הסטופ בחשבון-המשותף מחזיק 8 חוזים מול פוזיציה של 5 — עודף של 3 — אחרי שאתי ירדה מ-5 חוזים ל-1 בלי לכווץ את  | ✅ **הוכרע במדידה ולא ב-Trade DOM** — `11114` היה **חי**; אם חי, לכווץ אותו ל-1 (זו פקודה שלו/של אתי — **אנחנו לא נוגעים**). **(2)** cowork — לחזור על סכימת-`qty |
| T-304 | 🟠 | ‏`System6 target_divergence` הוא אזעקת-שווא מבנית — הסולם מוסט ברגל אחת כי ה-T0 תופס את החריץ הראשון אצל סיירה |  |
| T-303 | 🟠 | יום-הלייב המלא הראשון של `DALTON_PLAYBOOK_V1`: 8 מ-9 המועמדים נחסמו על-ידו, 0 לייב — והתאומים-בצל של הנחסמים ה | **(1) ✅ בוצע — ציר-הספירה:** 57 חסימות-שער היום, מהן **49 דלתון = 86.0%** (`kind` 16 · `location` 13 · `stand_down` 12 · `bias` 8) ו-8 שערים אחרים; **שני מקורות |
| T-300 | 🟠 | ‏`.env` נערך 11:27 בעוד הבקאנד עלה 23:37 אמש ⇒ שני דגלים פסוקים יושבים בקובץ ואינם בתהליך-החי; ו-`flag_guard P | הריסטארט 15:45 סוגר את המופע הנוכחי מעצמו — **לאמת אחרי הבוט** שורת `[env_loader]` חדשה + הופעת `[ECON-DIFF]` בלוג. **(2)** cc — להוסיף ל-`flag_guard` בדיקת-טרי |
| T-299 | 🟠 | מוני-הסיכון היומיים של השער נושאים את ההפסד של אתמול לתוך היום — כי `reset_daily()` מדלג כשאין סטאפ מאז הריסטא | ריסטארט קדם-פתיחה **מאפס את זה מעצמו** — `hydrate_live_pnl` עוגן ל-09:30 ET, וריסטארט ב-15:45 IDT = 08:45 ET ⇒ קדם-סשן ⇒ מונים 0. אבל הריסטארט מותנה בפוזיציה 0  |
| T-297 | 🟠 | תיקון ל-T-285 של cc: `VA_FADE` לא ירה 0 — הוא ירה 3, וכולן בשעה הראשונה. | לאמת אם 3 הפעימות רצו מול VA של אתמול; אם כן — להחיל את שפיות-T-294 גם על VAH/VAL |
| T-287 | 🟠 | הרקונסיילר מסווג פוזיציה-ידנית מוכחת כ-`ANOMALY` ומוציא `CRITICAL`, כי הודעתו מקבעת בקוד "no manual trading pe |  |
| T-286 | 🟠 | השער בחר שורת-פלייבוק לפי תווית סוג-יום בת ~10 דקות — פיגור שני ברים בין `v9_day_type_state` ל-`get_live_day_t | למדוד את הפיגור, לא לכוונן אותו — לקרוא את שכבת ה-antiflap ב-`trade_context.get_live_day_type` ולענות **בשתי שורות**: (א) כמה ברים היא מחזיקה תווית ישנה ובאיזה  |
| T-285 | 🟠 | הכיוון צדק וההצבה לא — שתי עסקאות-לייב SHORT של 08.09 היו בכיוון-היום ובהסכמה מלאה עם צל-S1DayDir, ונעצרו לפני | להוסיף את 1224/1231/1262 כ**מקרי-ריפליי** לסט-הרגרסיה (דוקטרינת-הלמידה: תקרית ⇒ מקרה-ריפליי, לא דגל), ולמדוד את עוגן-הסטופ **פר-סוג-יום** — לא גלובלית, כי הריפל |
| T-281 | 🟠 | "הראנר רק ביום-מגמה; ואם לא יודעים למקם — מערכת שמרחיבה/מקטינה לפי התנהגות-המחיר, שכבר הייתה לנו" (מייקל 09.09 |  |
| T-278 | 🟠 | טבלת-הסירובים היומית אינה פריט-שער — היא נמדדה היום רק מפני שמייקל שאל, ולכן "השערים סירבו לסטאפים טובים" מתגל | (1) **לחבר את `blocked_candidate_audit.py` לדוח-ה-EOD** כך שטבלת-הסירובים של אותו יום תיווצר בכל יום בלי שמישהו יבקש, ותישמר לצד ספרי-היום — **תצפית טהורה, אפס  |
| T-277 | 🟠 | הספרים והברוקר נושאים מחירי-ברקט שונים על עסקת-הלייב הפתוחה `#1231` — הזזה מסודרת פר-חוזה, לא רעש-עיגול. | (1) **לתפוס את המטען הגולמי לפני שהוא נמחק** — הנתיב היחיד להכרעה: להוסיף שמירת-עותק של `cmd_*.json` (או לוג של המטען) לפני ה-ACK, או לקרוא את הצד השני מהיומן ש |
| T-272 | 🟠 | חיתוך-היעדים לקצה-ה-IB אינו ניתן למדידה (אירועי-החיתוך אינם נשמרים), וההנחה שמאחוריו נסתרת ב-n גדול. | (1) לא להוציא את Variation מרשימת-הפטורים על n=8 ונטו +$37.50 (שני זנבות מסבירים כמעט הכל). (2) **התיקון שאינו נוגע בדוקטרינה: להרחיב את סף ה-clamp SKIPPED מעבר |
| T-271 | 🟠 | "סוף-הרחבה = טריגר לצד השני" נמדד על 15 סשנים — הקריאה נכונה, מבנה-העסקה מפסיד. | (1) לא לבנות T1 בשום צורה שמשאירה סטופ בקיצון — גם וריאנט סטופ-על-בר-האות נמדד: -$432.50, -8.92R, 11/15 סטופים. (2) לא T3b (חזרה דרך מקור-הרגל) — 0 מועמדים ב-15 |
| T-270 | 🟠 | יומן-המילויים `quality.exit_fills` — העוגן שנבנה ב-T-62 כדי שכל רגל-יציאה תישא מחיר משלה — ריק בכל שלוש העסקאו | (א) לקבוע איזה נתיב סגר את `1191` — `grep -rn "BRACKET_EXIT_ACTIVITY" backend/` ולוודא אם הוא עובר ב-`on_target_hit`/`_record_exit_fill` בכלל; (ב) להכריע אם בצל |
| T-269 | 🟠 | בייצוא-סיירה יש שני שדות-רווח שסותרים זה את זה, ומי שיקרא את הלא-נכון ידווח יום-הפסד על יום-רווח: `daily_pnl=− | (1) **cc — לוודא שאף צרכן-דיווח אינו קורא `sierra.daily_pnl`:** לסרוק את הפאנל/`mobile_monitor`/`narrator_he` ולהחליף ל-`acct_daily_pl`; אם השדה נחוץ לתצוגה — ל |
| T-267 | 🟠 | האינווריאנט §9ב שנחת היום ב-13:15 נפל בריצה הראשונה אי-פעם שבה נבחן — קלט-הסיווג בנעילת-ה-IB רחב מה-IB עצמו, ו | (1) **cc — לקבוע חד-משמעית אם `rib>1.0` בנעילה הוא באג-קלט או התנהגות-צפויה:** ‏`rib` גדל מונוטונית (1.206→1.294) לאורך הברים שאחרי הנעילה, מה שמתיישב עם "הסיוו |
| T-265 | 🟠 | ייצוא-ה-RTH `5min.json` תקוע על שישי בזמן שהפיד חי — שער-הקליטה דוחה כל אצווה, ‏470 שגיאות ב-20 דק' ומטפס. | (1) **ניטור בריצות הבאות** — לדגום `max(ts)` ב-`5min.json` ואת מונה-ה-`REJECTED`; אם עד `~16:00` ה-RTH לא התיישר, זו **תקיעה** ולא טעינה, והיא **חוסמת את פתיחת  |
| T-260 | 🟠 | ערוץ-הטלפון מאבד הודעות-סוכן בשקט, בשני מסלולים בלתי-תלויים — ו-`phone_reply.py` מדפיס `ok` בשניהם. | (א) ב-`phone_reply.py`: לבדוק את קוד-התשובה ולהחזיר `exit(1)` + להדפיס את השגיאה במקום `except: pass`+`ok` — **כשל-רועש במקום שקט**; (ב) לפצל אוטומטית מסר >1900 |
| T-256 | 🟠 | פער-הספרים-מול-הברוקר של 04.09 פוענח: הוא  | (א) **הסעיף בעל-העדיפות —** לאתר למה `v9_trades.entry_price` נרשם 0.25-0.75 נק' מהפילוי בפועל (חשד: המחיר נלקח מהאות/המחיר-המבוקש ולא מ-`Fill` בפועל; יומן-הברוק |
| T-253 | 🟠 | `v9_day_type_state.ts` הוא `timestamp WITHOUT time zone` השומר UTC, בעוד `now()` הוא `timestamptz` ב-`Asia/Jer | (א) `grep -rn "v9_day_type_state" backend/ scripts/` ולסמן כל צרכן שמחשב `now() - ts` — כל אחד מהם מדווח היום פי-שעות; (ב) להכריע בחלון-הלילה בין **מיגרציה ל-`t |
| T-252 | 🟠 | עסקת-צל `#1004` תקועה בלולאת-`T3 HIT` אינסופית מ-17:45 — 1,785 אירועים ו-1,785 הודעות-סגירה לגייטוויי, והיא עד | (1) לחסום יצירת-עסקה עם `stop == entry` (R=0) בשני הכיוונים — אותה שכבה שתיקנה את T-242; (2) ב-`bar_level_detector`, מעבר-T3 חייב להיות **חד-פעמי** (עוגן `t3_hi |
| T-247 | 🟠 | הליגר מאבד 23% מהשורות בכל קריאה, בשקט — ושתי המדרגות העליונות של המשפך הן שנופלות. | (א) ב-`candidate_ledger.emit()` לכתוב `"ts"` באותו שדה שהגייטוויי כותב, ולהשאיר `observed_at` לתאימות-לאחור; (ב) טסט-רגרסיה שכל שורת-ליגר נושאת `ts` פרסבילי (‏` |
| T-246 | 🟠 | `S2_DELTA_DBL` אינו מסוגל לייצר מועמד לפני `~17:50 IL` —  | שתי הדרכים האלו מזינות לגלאי דלתא-חלקית-או-ריקה — בדיוק הסוג של-`Rule 1` אוסר. **(א) השאלה הנכונה קודם — למה ה-CVD מתחיל ב-16:30 ולא ב-13:30 בזמן-אמת?** הנתונים |
| T-244 | 🟠 | אחרי [[T-242]]+[[T-235]] שער-הצ'ייסר `entry_location_quality` הופך כמעט-אינרטי ביום-מגמה: בשחזור על  | אין לגעת בסף ואין להחזיר את החסימה. **למדוד יום-מסחר אחד** עם [[T-219]] (`mode='shadow_blocked'`, חי מ-`23:56:08`, `0` שורות עד עכשיו כי השוק היה סגור — `SELECT |
| T-243 | 🟠 | השליש השלישי של פסיקת-28.08 מת גם הוא: `expensive_stop` (‏`stop/ATR > 1.5`) מעולם לא ירה — כי `current_atr14`  | תיקון ה-import **מוסיף תנאי-חסימה חדש** לשער שכבר חסם 89% מההחלטות ⇒ **הרחבת שטח-סיכון בכיוון המחמיר**, לא תיקון-באג ניטרלי. נדרשת מדידה ראשונה: כמה מהמועמדים ש |
| T-241 | 🟠 | סיווג-היום החמיץ `Trend_DD` ב-1.67 נקודות — מייקל זיהה מהעין (03.09 `17:53:34Z`: *"זה נראה כמו double distribu | **(א) תיקון-הגלאי (בסמכות cc, אינו שטח-סיכון):** **אין להנמיך את `narrow_frac=0.7` בעיוורון** — למדוד קודם: להריץ את הגלאי רטרואקטיבית על 80 ימי `v9_day_type_hi |
| T-240 | 🟠 | הספרים רושמים את הסטופ-המבוקש ולא את הפילוי-בפועל — `#987` מוחסר ב-$12.50. | (א) לכמת — להריץ על `v9_trades` את כל `exit_reason='STOP_FILL'` ולהשוות `exit_price` מול `Closed Trade Profit/Loss` ביומני-הברוקר המקבילים; (ב) לאתר את הכותב של |
| T-238 | 🟠 | כפתור-ביטול-החוסם של מייקל אינו מכסה את `entry_location_quality` — החוסם הדומיננטי בפועל ⇒ מייקל לחץ ב-03.09 1 | קודם-כל [[T-236]]/[[T-235]] (חיבור `has_pullback`) — הוא מייתר את רוב הצורך בכפתור. בנפרד, **פסיקת-מייקל נדרשת** לשתי שאלות: (א) האם להוסיף `entry_location_qual |
| T-233 | 🟠 | שלב `RESOLVED` של הליגר חסר-יצרן — 0 מתוך 43 מועמדים ב-02.09, ומעולם לא נכתב. | לקרוא את `candidate_ledger._stage_key` (הוא כבר יודע לטפל ב-`RESOLVED`) ולחווט קורא יחיד בנקודת-סגירת-העסקה (`fill_poller`/`trade_manager` — היכן ש-`exit_reason |
| T-229 | 🟠 | `T-43` חוסם כניסות-חדשות על עסקת-הלייב שלנו עצמה — פעמיים היום, ~2 שעות — והשורש הוא ההסטה של T-213, לא פוזיצי | ל-`T0` אין עמודת `t0_hit_ts`, ולכן חשבון-החוזים-הפתוחים עיוור ליציאת-ה-T0 — זו המועמדת לשורש של `TM=5 Sierra=4`; **למדוד ישירות לפני שכותבים קוד**. [הקודם] ⛔ אפ |
| T-226 | 🟠 | `SCALE_IN` יצר עסקת-לייב-רפאים `#955` שמעולם לא הגיעה לשוק — שומר-`T-214` דחה את ה-`PLACE`, אך ה-TM שמר את העס | (א) הגודל — `RISK_BUDGET_SIZING_V1` ב-`sierra_command.py:692-727` מחזיר `min(_n, ruled_contracts())` ו**אינו** מתחשב ב-`setup["contracts"]`, ולכן הילד קיבל 4 במ |
| T-224 | 🟠 | הליגר כותב `trade_id: true` (בוליאני) במקום מזהה — 3 מ-9 שורות `ROUTED` של 01.09 נראות כ"נותבו ולא ירו", וזו ק |  |
| T-222 | 🟠 | `_MES_DOLLAR_PER_POINT = 12.50` — הרקונסיילר מנפח כל דיווח-הפסד פי 2.5, וזה הסף שמפעיל הברחה-אוטומטית. | `_MES_DOLLAR_PER_POINT = 5.00` + תיקון-ההערה, **ועימו טסט-רגרסיה** שמקבע את הזהות מול `acct_open_positions_pl` של סיירה (unrealized מחושב ≡ שדה-סיירה, בסבילות ס |
| T-215 | 🟠 | שתי שכבות-סייז צועקות `5→2` ואף אחת מהן אינה מחייבת — `SIZE_CAP_CUT` ו-`WIDEN-TO-STRUCTURE` מחשבים על סטופ ש-` | **(1) הקריאה לפני הכל:** לתחום היכן פלט-`compute_v2_sizing` נקטע בין `five_min_system` ל-`setup_emitter` — **אם הוא לא מחובר בתכן, זו התשובה והפריט נסגר כתיעוד* |
| T-212 | 🟠 | `STRUCTURE_EXIT_FAILBREAK_V1` זיהה נכון בפעם הראשונה על עסקה חיה — ובצל |  |
| T-210 | 🟠 | `DAYTYPE_WATCHDOG` יורה `CRITICAL` שנוקב בסיבה שקרית — *"the 5min feed (bridge/DLL) is likely dead"* — בזמן שה | אין |
| T-207 | 🟠 | נוסח שער-הגודל בקובץ-המשימה-המתוזמנת מיושן מול פסיקת-5-החוזים — והוא חי מחוץ לריפו, ולכן אף בודק לא תופס אותו. | **(א) בכל ריצת-שער עד שהנוסח יתוקן:** לקרוא את סעיף-הגודל כ*"אמת ש-`ruled_contracts()` מחזיק ושהמרג'ין מכסה אותו"* ו**לא** לכתוב `_4=1`/`_2=1` לצד `_5=1`; אם המ |
| T-197 | 🟠 | שתי עסקאות-הפתיחה של אתמול נלקחו כש-`day_type=UNKNOWN`, וביטחון מלא הגיע 45 דק' אחרי ששפל-היום כבר נקבע. | (1) לקרוא ב-`daytype_playbook.py`+`location_gate.py` מה קורה על `day_type` לא-מוכר ולתעד אם זה fail-open (חשד: כן, כמו `_pattern_family→None`); (2) להכריע אם 30 |
| T-196 | 🟠 | `awaiting_release` דורש 2 שפלים-עולים ⇒ אי-אפשר לקנות שפל — כולל בדפוס הרווחי-ביותר במערכת. | להתנות את הסף בהקשר ולא להחליפו — `1` שפל-עולה **רק** כאשר (א) המשפחה REV **וגם** (ב) הכניסה בתוך סובלנות של VAL/VAH או קצה-היום; בכל שאר המקרים **נשאר 2**. דגל |
| T-195 | 🟠 | `FAMIR` ו-`VEGAS` הם `SKIP` בכל שמונת סוגי-הימים — שורות מתות בפלייבוק, הסותרות את הקונפיג של עצמו. | להביא למייקל את הסתירה ולשאול אם ההשבתה מכוונת. אם לא — תאים כמו `DBDT` (`Normal: FULL` · `Neutral_*: FULL` · `Trend_*: SKIP`). **חסום ע"י T-194.** **אימות-סגיר |
| T-193 | 🟠 | יציאות-FLATTEN אינן מייצרות מילוי-ברקט ⇒ 53 עסקאות `incomplete` בלי מספר-ברוקר. | לגזור P&L של יציאת-FLATTEN מ**דלתת `sierra_state.daily_pnl`** סביב רגע-הסגירה (הוא ממומש-יומי ⇒ ההפרש לפני/אחרי הוא בדיוק הרווח/הפסד של אותה סגירה), ולכתוב אותו |
| T-191 | 🟠 | שני טסטי-`delta_dbl` נכשלים בבוקר אחרי שעברו בלילה — הטסט תלוי-מצב-שוק, לא הקוד. | לנתק את הטסט ממצב-השוק החי — לזייף (stub/monkeypatch) את השערים הקודמים ל-`shadow_only` (`awaiting_release`, `cold_start_guard`, `eod_entry_cutoff`) כך שהטסט יב |
| T-190 | 🟠 | `quality.exit_fills` קיים ב-12 עסקאות מתוך 413 — ולכן אי-אפשר לדעת איך עסקאות-צל יצאו. | לברר את 5 עסקאות-הלייב החסרות בלבד (נפרד מ-T-211, שנסגר) |
| T-188 | 🟠 | `MISMATCH_PHANTOM_SLOT` הוא קוד-מת מאז 27.07 — הגלאי שאמור היה לתפוס את חסימת-הלייב-בשקט של 31.08 (3.5 שעות) ל | מחוץ-לסמכות-cowork — הסבת `db_open_ids` ב-`gather_and_reconcile` מרשימת-שלילה לרשימת-היתר היא **נגיעה בגלאי-בטיחות חי** (מסלול-האורפן-העירום) ⇒ דורשת אישור-מייק |
| T-187 | 🟠 | `/api/v9/system6/diagnose` קורס על `int(dict)` ומחזיר `trade: null` בכל עסקה פתוחה — מזה 23 יום. | **(1) התיקון, `system6_routes.py:52`:** לחלץ את המזהה במקום להמיר את האובייקט — `_tid = slot.get("trade_id") if isinstance(slot, dict) else slot` ואז `{"id": in |
| T-185 | 🟠 | `market_ts`/`available_at` ב-TPO לא נוספו — `DALTON_EDGE=live` רץ על קלט שסיבתיותו אינה מדידה. | ‏`ALTER` להוספת שתי העמודות + backfill היסטורי. **חובה, בסדר הזה:** ‏`scripts/mems26_snapshot.sh 'tpo-market-ts'` → `SET lock_timeout='3s'` (הטבלה חיה; ראה T-53 |
| T-183 | 🟠 | אין אזעקה על `live_slot` תקוע — 4 שעות חסימה היום ואפס התראות. | (1) לאמת בשדה אחרי ריסטארט ש-`slot_health` מופיע ב-diagnose; (2) **תיקון-שורש נפרד**: `db_open_ids` ב-`gather_and_reconcile` עדיין ברשימת-שלילה ⇒ `MISMATCH_PHAN |
| T-181 | 🟠 | תשובה מדודה לשאלת-מייקל 31.08 20:56 (*"למה אין ירי ללונג מה חוסם ולמה? לתקן"*) — 97% מחסימות-הלונג הן `awaitin | **אין פעולה בסמכות-cowork.** הורדת-סף ב-`awaiting_release` (למשל 2→1 שפלים-עולים) היא **שינוי משטח-סיכון** ⇒ דורשת פסיקת-מייקל בכתב, ולפי עיקרון-העל (*נותנים לש |
| T-179 | 🟠 | `S2_DELTA_DBL` ירה היום בפעם הראשונה אי-פעם — 58 ירי ב-2.5 שעות, מתוכם 41 נחסמו כ-`duplicate_fire` — והוא לבדו | (1) **קלט מיידי להכרעת-T-178:** אם מייקל יורה על ריסטארט לשחרור-הסלוט, `S2_DELTA_DBL` הוא **המועמד הסביר ביותר לתפוס את הסלוט המשוחרר** (58 ירי ב-2.5ש' מול 4 מו |
| T-174 | 🟠 | `t3=0.00` על עסקת-לייב בת 5 חוזים — הרץ נשלח בלי יעד תקף. | לאתר מדוע נתיב-`OPENING_DRIVE` מחזיר `t3=None` (חשוד: `opening_entry` מספק t1 בלבד — `OPENING_ENTRY DRIVE SHORT entry=7689.50 stop=7703.75 t1=7668.12` — ו-`Targ |
| T-173 | 🟠 | פסיקת-5-החוזים נכונה בהגדרה ומגיעה 2 בפועל — `SIZE_CAP_CUT` חותך כל מועמד לרצפה. | מחוץ-לסמכות-cowork (גודל-עסקה = משטח-סיכון, והחיתוך עצמו **פסוק**) ⇒ *רשום וענה*. נמסר למייקל בטלפון 31.08 16:45. שלוש אפשרויות שההכרעה ביניהן היא **פסיקה שלו ו |
| T-172 | 🟠 | חמשת הדגלים שנפסקו מאז שישי לא נבחנו באף עסקה — ושאלת-מייקל עליהם (31.08 12:48:36Z) נענתה "לא-ניתן-להכרעה" ולא | דוח-ה-EOD של היום הוא **המדידה הראשונה** של חמשת הדגלים יחד, ולכן **אסור לצטט `sum(pnl_usd)` לבדו**. חובה לפצל: `SELECT (exit_reason='phantom_reconcile') ph, co |
| T-171 | 🟠 | `config/manual_position_ack.json` פג לפני 5 ימים — והחשבון משותף עם אתי. | מחוץ-לסמכות-cowork (כתיבה למשטח-המסחר) — נמסר למייקל בטלפון 31.08 15:20 עם השאלה האם לחדש. אם יאשר: לכתוב `{"date":"<היום>","owner":"michael","max_abs_qty":10," |
| T-103 | 🟠 | Candidate Ledger — פריט-1, אפס סיכון. |  |
| T-102 | 🟠 | Task-0: לאחד 52 כלי replay/backtest/study ל-Replay Kernel אחד. |  |
| T-89 | 🟠 | ביקורת המערכות-המתות (22.08, קריאה-בלבד) — 4 ממצאים חוסמים-אמת. | ‏(א) מייקל פוסק על (2) — או שהחיצוני חוזר ל-`1` או ששני הפנימיים ל-`0`; **לא להשאיר שלוש פסיקות סותרות**. (ב) cc: להעתיק את הפיקסצ'ר של 8 השורות מ-`backend/v9/t |
| T-552 | 🟡 | הודעת-טלפון יחידה הגיעה למייקל פעמיים — הכפילות ממוקמת אחרי ה-POST היחיד, לא בהרצה כפולה. | (1) **לא לשלוח הודעת-בדיקה לטלפון** כדי לשחזר — זו בדיוק ההצפה. (2) להכריע מלוגי-השרת: `list_logs` של שירות `mems26-mobile` ברנדר סביב `15:53:59-15:54:01Z` ⇒ ** |
| T-541 | 🟡 | לוח-ההחלטות לא יוכל להראות את חיתוך-20:00 של T-538 — נקודת-התצוגה אינה מאכלסת `hour`, ולכן נופלת תמיד ל-`"*":  | (1) **המבחן המכריע קודם לתיקון** — מועמד אמיתי אחרי 20:00 IL בליגר עם `hour=">19" ⇒ SKIP`; רק הוא מוכיח שהחיתוך פועל בנתיב-הירי; (2) אם אומת ⇒ החלטה אם לאכלס `h |
| T-511 | 🟡 | שורט ידני של מייקל (‏`InternalOrderID 11357`) פתח [[T-43]] ב-`20:27` ונעל את ירי-הלייב לשארית הסשן — והבעלות נ |  |
| T-483 | 🟡 | ציר-השלב בעץ הוא 4 שלבים גסים; מייקל דורש חצי-שעה — "בכל חצי שעה אנחנו יודעים יותר על הסיפור ויכולים לקבל החלט | (1) **בלי לגעת בעץ החי** — לבנות את הציר כגרסה (`phase_30m`: A 16:30-17:00 · B -17:30 · C -18:00 … H 21:00+) ולמדוד יום-כולל על 58-59 הסשנים מול הבסיס, כמו V1/V |
| T-457 | 🟡 | ענף-דרייב-הפתיחה נבנה ונמדד — `OPENING_DRIVE_BRANCH_V1` (כבוי-כברירת-מחדל, ממתין לפסיקה). | 16:31–16:46 לאמת שהקוד נטען (`ps -o lstart` של ה-backend אחרי 15:30; `grep -c 'T-457 ELQ skipped' /tmp/backend.err.log` — מופיע רק אם היה דרייב מאושר) ⇒ ✅ עם שו |
| T-446 | 🟡 | `v9_decision_vectors` (וקטור-המצב, T-390) רושם החלטה רק בשער-דלתון — התוצאה הסופית של הסטאפ (ELQ · מיקום · R:R | ב-`process_setup` לכתוב את `result` הסופי ל-`mode_result` של שורת-ה-DECISION (עדכון, לא שורה חדשה) — ואז המבחן-היומי ורשימת-הצל של v2 יעבדו ממקור אחד. |
| T-437 | 🟡 | בקשת-מייקל `21.09 14:47:00Z` (‏`id d4b975c1`) — "אבל אני לא רוצה חימוש אחרי יותר משעה וחצי אני רוצה חימוש אחרי | **(1)** **ריפליי ולא דגל** — להריץ את ארבעת הדפוסים תלויי-CCI על `09:30-10:40` בשלושה תרחישים: סף `14` (בסיס, = אפס ירי), סף `6`, וזריעה-מהסשן-הקודם; המוצר הוא  |
| T-328 | 🟡 | חבילת-הפעלה (מייקל 11.09 18:00 "אני רוצה שהיום המערכת תסחר"): §1 העוגן של התבנית מגיע לשער + שומר-רדיפה (2×tol |  |
| T-298 | 🟡 | `TRADE_ECONOMICS_AUTHORITY_V1` הועלה ל-`diff` (מדידה בלבד) — ונמצא ש-`=1` אינו ממומש כלל. | לקרוא `[ECON-DIFF]` מחר; `=1` דורש גם מימוש-הסתעפות וגם פסיקה |
| T-291 | 🟡 | הוראת-מייקל 09.09 22:39 (‏`id=18dee6b2` בת'רד-הטלפון): "המערכת לא צריכה להיכנס לעסקאות באזור ה-POC באף סוג יום |  |
| T-282 | 🟡 | רשימת-הניקוי — `docs/reports/CLEANUP_LIST_2026-09-09.md` ("לפנות כל מה שפוגע במסחר ולא יעיל", מייקל 09.09). |  |
| T-258 | 🟡 | ספרי-04.09 מדויקים לחלוטין מול יומן-המילויים (delta 0.00 בכל חמש) — ובכל-זאת חשבון-הברוקר נמוך ב-$18.75. שני מ | לקרוא את שורת-הכותרות של `TradeActivityLog_2026-09-04_UTC.37138283.data` ולבדוק האם `Closed Trade Profit/Loss` הוא **נטו-עמלות** והאם קיימת עמודת-עמלה נפרדת. אם |
| T-250 | 🟡 | בקשת-מייקל מהטלפון 04.09 (‏`4d0e8c9d` 17:43 + `a57bdf73` 18:02): "תאפשר למערכת לבצע תבניות שורט" · "לבטל את הד | (א) להשאיר `=1` ולתקן את **חלון-המדידה** של T-31 (החשד: שני הצדדים לא מודדים אותו חלון) · (ב) להחליף את הסף מחציון ל-אחוזון-נמוך (למשל 0.85×חציון) ⇒ נעבר ברוב ה |
| T-239 | 🟡 | `sierra.daily_pnl` ו-`acct_daily_pl` — שני שדות-יום באותו קובץ — נחלקו ב-$202.50, ורק אחד מהם מתיישב עם יומן-ה | לאתר את אתר-הכתיבה של `daily_pnl` ב-`sc_study/MES_AI_DataExport_merged.cpp` (מול `acct_daily_pl`, שהם **שני שדות-סיירה נפרדים** — לא לחשב אחד מהשני) ולתעד **מה  |
| T-237 | 🟡 | פער-גודל בעסקה 981: הסייזינג הצהיר 5 חוזים, בפועל נכנסו 3 — והסטופ יצא פי-3.15 מהסיכון שעליו חושב הגודל. | לאמת מול `ruled_contracts()` מי הקטין 5→3 (חשוד: `SIZE_CAP_CUT`/`StopResolver` שמרחיב סטופ *אחרי* הסייזינג) ולתעד. **אסור לגעת בדגלי-גודל** (T-225 נגרם בדיוק מכ |
| T-235 | 🟡 | `has_pullback` של EntryGuard מעולם לא מועבר בייצור ⇒ השער מחמיר מפסיקת-28.08 ("pos>0.66  | בפתיחת 04.09 לספור כמה חסימות `no pullback` נעלמו מול 03.09 (97) — זו המדידה הראשונה של השפעת-הפסיקה. |
| T-231 | 🟡 | אוטורן-cowork משאיר את שלושת עמודי-ה-readiness המיוצרים במצב-קונפליקט ⇒ רשומות `UU` באינדקס ⇒ *כל* `git pull`  | **(א)** `.gitignore` לשלושת העמודים המיוצרים (`docs/plans/MONDAY_READINESS.html` · `frontend/v9/public/readiness.html` · `render_mobile_relay/static/readiness.h |
| T-228 | 🟡 | `EDGE_ENTRY_LOCATION_FIX_V1` — פסיקת-מייקל של היום (02.09 13:35) — נשען כולו על מסלול-הגיבוי: מסלולו הראשי שוא | אין. [הקודם] ⛔ אפס פעולה בוצעה (איסור ריסטארט 16:10-23:00), וזהו קוד בתוך `location_gate` = משטח-סיכון-מסחר ⇒ מחוץ-לסמכות-cowork. תיקון בלי ריסטארט ממילא לא היה |
| T-218 | 🟡 | `extreme_chase_guard` חסם את שורט-היום בפער 0.35 נקודה — והמהלך שאחריו היה 19.5 נק'. | **אסור להכריע על n=1.** לבנות קודם את T-219; ההתפלגות שהתבקשה מוגשת ב-STATUS_BOARD ומראה בדיוק שאי-אפשר |
| T-217 | 🟡 | סוג-יום בביטחון 0.25-0.38 מפעיל `SKIP` מלא בפלייבוק — שער חוסם-מגמה שנשען על קלט חלש. | המדידה ל-20 יום שהתבקשה **הורצה ואינה מספיקה** — לא להכריע על `n=19`; לבנות קודם את T-219 |
| T-141 | 🟡 | פסיקה נדרשת |  |
| T-105 | 🟡 | `CONTEXT_ENTRY_V1` pure function אחת ל-replay+shadow+live. |  |
| T-104 | 🟡 | השלמת `S1_STRUCTURAL_BINARY_V1` + shadow ≥10 סשנים. |  |
| T-95 | 🟡 | רפליי-שבוע אחרי חבילת-התיקונים + ציד-פערים לא-מדווחים (2 דוחות, READ-ONLY). |  |
| T-94 | 🟡 | CVD · מאמץ-מול-תוצאה — הקריאה של מייקל על גרף 21.08 מול המספרים (34 סשנים ‎07-07→08-21‎ · דלתא-אמת מ-‎32.4M‎ ט |  |
| T-92 | 🟡 | אבחון פר-תבנית + שווי-החייאה מדוד — כל ‎19‎ הזהויות שמעולם לא הפיקו עסקה חיה (34 סשנים · 3 רמות-סליפג' · 4 ו-6 |  |
| T-91 | 🟡 | רפליי E1–E3 — כל שינוי-כניסה שהוצע, נמדד (34 סשני-לייב ‎07-07→08-21‎ · 3 רמות-סליפג' · עמלות בפנים · 4 חוזים). |  |
| T-90 | 🟡 | רפליי X1–X4 — כל שינוי-יציאה ושינוי-גודל שהוצע, נמדד (28/29 סשנים · 3 רמות-סליפג' · עמלות בפנים). |  |
| T-87 | 🟡 | תקציב-הכניסות של Normal ראשון-בא-ראשון-זוכה — ובזבז את שני הסלוטים על שני ZLR שורט בשפל-הסשן. |  |
| T-565 | 🔵 | 07.10 (דמו): שתי כניסות-LONG נדחו ע״י סיירה (`ORDER_FAILED:-1` = GENERAL_ERROR_OR_NOT_ENABLED; #3191 18:00 @78 |  |
| T-564 | 🔵 | היתר אחד מול ייחוס-אותו-בוקר (מייקל 07.10 17:52): INITIATIVE_SHORT ביום Variation 18–19h — BRIEF §2.2 #1. | פסיקת-מייקל על (2); היתר #2 REACTIVE_SHORT ו-#3 ZLR SHORT · Normal באותה תבנית, לילה הבא. ~~קודם:~~ **הצעד הבא:** `harness_out/t564/run.sh` (ברצף: t564ref → t56 |
| T-563 | 🔵 | זרם `v9_bars_tick_reversal` שותק מאז 01.10 23:06 (מייקל 07.10 17:52) — השורש נמצא 07.10 23:30, קריאה-בלבד, אפס |  |
| T-561 | 🔵 | הענף החזק בעץ מפסיד את רוב המועמדים שלו לסלוט-היחיד ולשער-האישור — לא לעץ. | (א) וריאנט-הרנס 'סלוט שני רק ל-`OPEN_DRIVE/C/Trend_Normal/with`' — דורש כפתור-env בגייטוויי (ברירת-מחדל זהה-בייט: סלוט אחד) + מבחן-זהות; בנייה דגל-כבוי (לילה),  |
| T-560 | 🔵 | `BarLevelDetector.on_bar`  | (1) ⛔ **לא** הודעת-טלפון — דמו, פוזיציה 0, אין החלטה שנדרשת ממייקל. (2) ⛔ **אפס שינוי-קוד בתוך RTH** — הנתיב הוא `trade_manager`, כלומר שינוי בו הוא סיכון-מסחר  |
| T-559 | 🔵 | שעון-הוותק של `daytype_watchdog` אינו מודע-לריסטארט/סשן ⇒ `CRITICAL` שקרי אחרי כל ריסטארט-טרום-פתיחה. | (1) ⛔ **לא** הודעת-טלפון — אינו אחד מארבעת המקרים. (2) **חיזוי בר-הפרכה:** ה-CRITICAL יחזור אחרי **כל** ריסטארט-טרום-פתיחה, כי השעון מודד מ-`last_write` ולא מ-` |
| T-557 | 🔵 | מבול-WARNING חדש שאינו מכוסה ב-[[מלכודת 33]]: `[S2-CVD] insufficient coverage: 1/20 rows (min=18) — returning  | (1) ⛔ **לא** הודעת-טלפון — זה דוח-ניטור, לא אחד מארבעת המקרים. (2) בריצת-ה-RTH של היום (16:30-23:00), למדוד את `[S2-CVD]` פר-שעה **בתוך** ה-RTH ואת `max(ts)` של |
| T-556 | 🔵 | סוכן-הכיול 23:40 אינו רשום באף אחד משני מרשמי-ההרצה שנמדדו — מה שמסביר "ריצה ריקה" בלי להניח תקלה בסוכן עצמו. | (1) ⛔ **לא** לשלוח הודעת-טלפון נוספת בנושא — השאלה כבר אצל מייקל, וחזרה עליה = [[T-369]]. (2) בתור-הלילה של 07.10, לסרוק את המשטח השלישי (צד-cc / רשימת-ה-10-age |
| T-555 | 🔵 | 17 שורות-צל של 06.10 נושאות `exit_ts` של 07.10 — ולכן כל מדידת-צל שנחתכת לפי `exit_ts::date` מייחסת ליום-היום  | בתור-הלילה של 07.10, **לפני** `day_review.py`/`review_report.py`/`gen_phone_pages.py` — לקרוא באיזה שדה הם חותכים את ספרי-היום. אם `entry_ts::date` ⇒ נקי, לסגור |
| T-554 | 🔵 | 17 שורות-צל נשארו פתוחות (`state=FILLED`) בסגירת 06.10, וכולן מ-06.10 עצמו — כלומר בשער של מחר הן "שורות-הצל ש | בשער 15:30-16:10 של **07.10**, ובסדר הזה: (1) `python3 scripts/close_stale_shadow.py` **דריי-ראן** ⇒ לוודא שהוא מציג את 17 השורות של 06.10 (אם הוא מציג פחות — ז |
| T-550 | 🔵 | שורת-הלוג `VIRTUAL STOP SET` של הריקונסיילר מפרסמת פלטן-אוטומטי שפסיקת מייקל 28.07 ביטלה — ולכן קורא-הלוג מסיק | לנסח את שורת-הלוג לפי הדגל בזמן-ריצה — `ALERT ONLY (ruling 07-28)` כשהדגל OFF, והנוסח הקיים רק כשהוא ON — **שינוי-טקסט בלבד ב-`sierra_position_reconciler.py:771 |
| T-549 | 🔵 | `harness_out/` אינו ב-`.gitignore` כלל — 1.88GB / 7,811 קבצי-ריפליי פר-יום יושבים כ-untracked בעץ-העבודה, ו-`g | כלל `.gitignore` **ממוקד-תיקייה** לבורות (`harness_out/t466/` ראשון, ואחריו `t458`/`t458a`/`t426`) + **אימות `git check-ignore -v` על זוג** — קובץ-פסולת אחד וקו |
| T-547 | 🔵 | הפוסק-לממתינות נבדק במפתח שלו עצמו — `PHONE_THREAD.jsonl` שלם, אבל הכותב מקבל `sender` ששווה לשם-דגל. | **(1)** להוסיף ל-`scripts/phone_reply.py` שער-קלט שנכשל בקול על `sender` ריק או כזה שמתחיל ב-`--` (לא לכתוב שורה בכלל) + מקרה-רגרסיה; תיקון-קטן בסקריפט לא-מסחרי |
| T-543 | 🔵 | נתב יומי דלתון (CC_ORDER 2026-10-05 17:11, Cursor → Claude) — עץ אחד, משפחת-ענפים לפי מצב-המכרז, שיפור בין-סשנ | **שלב 4 ✅ (06.10 ~18:05, cowork; קוד בלבד בזמן RTH — המאזין 71969 רץ בלי --reload ולא טוען קוד חדש):** `build_s2_gateway_setup` (`five_min_system.py`) מעתיק את  |
| T-539 | 🔵 | סוכנים מסביב לשעון + הנחיות ל-Claude Fable — `docs/runbooks/AGENT_BRIEF_FABLE.md` הוא מקור-האמת לכל הסוכנים המ | (1) ✅ 16:25–16:45 שלושת הפרומפטים (אינדקס/תיקונים/פיקוח) נפתחים ב"קרא את ה-BRIEF ופעל לפיו" (re-signed ע״י Claude Desktop); (2) ✅ 08:30 הכנת-פסיקות נוצרה (`trig |
| T-536 | 🔵 | סוכן-הפיקוח — `scripts/supervisor.py` (קריאה-בלבד): ימים-אנלוגיים לכל סשן מאז יוני (טביעת-אצבע: טווח/נטו אתמול | (1) ריצה ראשונה 15:35; הודעת-טלפון רק על אדום חדש או בסיכום 22:35; (2) v2: את "SKIP על עלה חיובי" להפוך למדידה אוטומטית של סוכן-התיקונים (וריאנט-יום-שלם); (3) ל |
| T-534 | 🔵 | סוכן-התיקונים — משימה מתוזמנת לילית (23:40 IL) שעובדת רק לפי דוקטרינת-הלמידה: מדידה בהרנס מול ייחוס-אותו-לילה  | ריצה 1 = **[[T-540]] walk-forward** — לקרוא `docs/reports/WALK_FORWARD_2026-10-05.md` §7 לפני כל עלה חדש; רשימת-הגיזום (OOS ≤ 0, n≥10) היא הסדר-יום, אפס עלה חדש |
| T-533 | 🔵 | סוכן-האינדקס — `scripts/system_index.py` → `docs/index/SYSTEM_INDEX.md` + `system_index.json`: כל המערכת בקריא | (1) המשימה המתוזמנת "MEMS26 — סוכן-אינדקס" מריצה כל בוקר, מאמתת ומקמטת `docs/index/` בלבד; (2) v2: שערי-הגייטוויי שאינם בעץ (entry_not_confirmed / rr_entry_gate |
| T-525 | 🔵 | בחירת קובץ-הלוג-החי כתובה קשיח בתיעוד במקום להיגזר מה-pid של המאזין — ולכן התהפכה פעמיים באותו יום, ובכל היפוך | (1) ⛔ **אל תתקן את §3.1** ב-`CLAUDE.md`/`COWORK_DAILY_READ.md` — נכון שוב מאז 23:06; (2) להוסיף ל-`COWORK_DAILY_READ.md` את הנוסחה במקום את שם-הקובץ: הלוג-החי = |
| T-513 | 🔵 | `session_phase`/`session_min` ב-`mes_ai_data.json` שקריים לאורך כל הסשן האמריקאי — ה-DLL  | **(1) לא לתקן ביום-מסחר ולא לבד:** התיקון יושב ב-DLL ⇒ `scripts/mems26_snapshot.sh` + `--deploy` + Remote Build + reload, **מחוץ לשעות-מסחר**, ו**מתלבש על הדיפל |
| T-509 | 🔵 | שתי ההערות של שער-`RISK_BUDGET` ב-`config/RULED_FLAGS.yaml` נשארו מעידן-`BUDGET=150` בזמן שהערך-הפסוק הוא `225 |  |
| T-504 | 🔵 | בגודל-הפסוק (חוזה 1) אף נתיב קדם-שליחה אינו חוסם על כסף, ומפסקי-החירום של הברוקר הם תצוגה-בלבד — ולכן `fire_dr | להוסיף ל-`fire_drill` ולהודעת-השער שורת-**דיווח** אחת עם `cap_contracts(1)` (המשפט מוכן מהפונקציה) + שלושת מפסקי-הברוקר (`acct_under_margin`/`acct_trading_disab |
| T-503 | 🔵 | סוויטת-הטסטים כותבת דוחות-פוסט-מורטם אמיתיים לתוך `docs/reports/postmortem/` המעוקב — זה המנוע שמלכלך את עץ-הע |  |
| T-501 | 🔵 | הברידג' כותב 1.1–1.2M אזהרות-DNS ביום (`672MB / 5.39M` שורות ב-`/tmp/bridge.log` מ-22.09) — `UPSTASH_REDIS_RES |  |
| T-499 | 🔵 | ההרנס קורס על 07.08 | לדלג על שורות בלי מחיר ב-`_inject_due` (עם אזהרה), להריץ 07.08 לכל התגים של 27.09. |
| T-485 | 🔵 | `v9_trades` מחזירה 10 שורות `exit_ts IS NULL` שכולן `state=CLOSED` מ-17.09 — כל שאילתת "מה פתוח" תספור אותן כפ | (1) לברר מהקוד **מי** משאיר `state=CLOSED` עם `exit_ts IS NULL` — הכותב של סגירת-הצל, או `STALE_UNRESOLVED` שכותב `state` בלי `exit_ts` (`#2363` מ-24.09 הוא בדי |
| T-468 | 🔵 | `SYS-3 DIVERGENCE` / `phantom-heal` נפתח על פוזיציית-לייב אמיתית: |  |
| T-427 | 🔵 | `close_stale_shadow.py` סוגר שורות-צל בלי לכתוב `exit_ts` ⇒ חור שקט של 14% בכל מדידת-צל שנחתכת לפי `exit_ts`. | (1) **לקרוא את `scripts/close_stale_shadow.py`** ולאשש בקוד — לא מה-DB — שנתיב-הסגירה אינו כותב `exit_ts` (ההסקה כאן היא מ-`exit_reason` אחיד, לא מקריאת-קוד). ( |
| T-424 | 🔵 | 304 נתיבים לא-מעוקבים בעץ-העבודה, והעלות כבר נמדדה בעץ עצמו: שאריות חסמו `git pull --rebase` בסשן. |  |
| T-402 | 🔵 | פסיקה עומדת (מייקל 17.09 17:35): כל פוזיציה שנפתחה לא על-ידי המערכת היא של מייקל. | אין FLATTEN, אין דיווח-חריגה על פוזיציה זרה; **השלכה שמייקל יודע:** בזמן שפוזיציה ידנית פתוחה באותו חשבון — T-43 חוסם את כניסות-המערכת (ועם 2 חוזים ידניים גם המ |
| T-401 | 🔵 | `CeilingFlipTouch2` פולט T2 בצד הלא-נכון של הכניסה ב-SHORT (‏T2 = כניסה + tick) — שני שערי-הגנה בלתי-תלויים כב | (1) **לקרוא** את מחולל-הצלעות של `CeilingFlipTouch2` ולאמת את השורש לפני תיקון — **אין לתקן מהזיכרון** (Pre-LIVE: diagnose first); לבדוק במיוחד אם `T2` נגזר מה- |
| T-400 | 🔵 | `InvalidTransition: CLOSED -> CLOSED` נזרק מ-`BarLevelDetector.on_bar` בזמן יציאת עסקת-לייב — מירוץ סגירה-כפול | (1) לקרוא את `state_machine.py` ולאמת את השורש לפני תיקון — **אין לתקן מהזיכרון** (Pre-LIVE: diagnose first). (2) אם אושר: להפוך `CLOSED→CLOSED` ל**אידמפוטנטי** |
| T-310 | 🔵 | נוסח-החסימה של `entry_guard` שקרי בשני שדות, והוא ינתב את החקירה הבאה לכיוון הלא-נכון. |  |
| T-234 | 🔵 | חידוש-ה-ack האוטומטי שמייקל אישר ב-01.09 טרם נבנה — `manual_position_ack.json` עדיין מתיישן כל בוקר בשקט. | לכתוב את החידוש לתוך שער-הקדם-פתיחה עצמו (הנקודה שכבר רצה כל בוקר לפני 16:10), לא כ-LaunchAgent נפרד: לכתוב `{"date":"<היום ET>","owner":"michael","max_abs_qty" |
| T-202 | 🔵 | גרירת-סטופ: 110 `MODIFY_STOP` מול 6 `PLACE` בארכיון — פי 18 יותר הזזות מכניסות, ואיש לא מדד את ההחלטות האלה. | לא לפני `T-103` — בלי `t1_before_stop` ו-MFE/MAE **רשומים**, כל שאלה על ניהול-עסקה תיענה ב-MFE ותטעה (קרה פעמיים היום, פי 4 הפרש). וכשיהיה: לספור מ-`_log_manage |
| T-184 | 🔵 | `lib.atr_from` מחשב ATR *יומי* ונקרא `ATR14` — פער-יחידה פי 12.7. | לשנות שם ל-`atr_daily_from` (ולהוסיף `atr_5min_from` אם צריך), + **טסט שנכשל על ערבוב** — קלט ברי-5-דק' ל-`atr_daily_from` ⇒ חריגה או ערך מסומן-יחידה. **אימות-ס |
| T-176 | 🔵 | פסיקת-מייקל 31.08 14:24:32Z (`e3b07c87`): "אין מסחר ב-15 הדקות הראשונות ללא מחקר למה העסקה היום נכשלה" | (1) לבנות `scripts/first_hour_audit.py --day YYYY-MM-DD` שמצליב לכל מועמד ב-16:30-17:30 את הבר שהפעיל אותו (`v9_bars_5min_woodies`), הסיווג שניתן (`pattern_id_a |
| T-175 | 🔵 | `NAKED_STOP_SUSPECT` שקרי בלולאה — 60 שורות `CRITICAL` ב-70 שניות על פוזיציה מכוסה 4/4. | (1) להחליף את מבחן-"הסטופ מאושר" מ-`last_result` ל**ספירת-סטופים מ-`sierra_state.orders` מול `abs(position_qty)`** (המקור שהפריך את האזעקה), ולהזעיק רק כש-`stop |
| T-170 | 🔵 | ייצוא `5min.json` קפוא מיום-שישי בעוד הקובץ נכתב-מחדש כל 5 שניות | (1) לברר בסיירה מדוע הצ'ארט שמייצא `5min.json` הפסיק להתקדם ב-28.08 15:55 UTC (חשוד: מחלקת "Bar-feed freeze" מ-25.06) — **לא לפני 16:10**, אין ריסטארט בחלון-המס |
| T-164 | 🔵 | רעש-לוג: `TS-OFFSET-GATE` מדווח ERROR על מצב-סופ"ש צפוי — 7,507 שורות ב-6.4 שעות (~1,180/שעה, גדל 1 ל-2ש'). | ריסטארט-`15:30` (חובה משלוש עילות אחרות ממילא) הוא הניסוי — אם הלולאה נעלמת אחריו, ההשערה אוששה והשורש הוא מצב-תהליך; אם היא שורדת, השורש בגשר/ביצוא ויש למדוד מ |
| T-163 | 🔵 | `LEG_REPLACES_SUSTAINED_V1` חסר לגמרי מ-`RULED_FLAGS.yaml` |  |
| T-162 | 🔵 | 8 סקריפטים-אחים באותה מחלקה |  |
| T-106 | 🔵 | Opportunity Ranker — חסום עד ≥300 candidate outcomes נקיים. |  |

## 9 · סקריפטים (254)

| קובץ | מה |
|---|---|
| `scripts/_probe_spacing_dist.py` | Derivation probe for TARGET_MIN_SPACING_V1's k/m — ladder-gap distribution |
| `scripts/agent_heartbeat.py` | Write docs/reports/AGENT_HEARTBEAT.json — the session-watch liveness beacon the |
| `scripts/apply_targets_diff.py` | apply_targets_diff — learning-loop v3: apply a PROPOSED_TARGETS_DIFF file to |
| `scripts/audit_pattern_miss.py` | audit_pattern_miss.py — quantified, doctrine-aware audit of WHY the pattern |
| `scripts/awareness_score.py` | awareness_score — ציון-המודעות היומי (T-159). READ-ONLY, מדד ולא שער. |
| `scripts/backtest_counter_flow.py` | Research: WHEN does opposing volume win, and is exiting there worth it? |
| `scripts/backtest_cvd_divergence.py` | Backtest cvd_divergence (literature-correct volume exit) on real trades. |
| `scripts/backtest_exit_signals.py` | Backtest System 6 exit signals on real managed trades (2026-07-05). |
| `scripts/backtest_manager_combined.py` | Combined System 6 manager backtest (2026-07-05). |
| `scripts/backtest_stop_resolver_item4.py` | Item-4 backtest — old stop vs STOP_RESOLVER_V1 structural stop, per pattern. |
| `scripts/bar_gap_monitor.py` | bar_gap_monitor — Track B (Michael 2026-07-16: "לדעת שיש את כל הנרות ללא חוסרים"). |
| `scripts/bar_integrity_check.py` | Bar-stream integrity check — the silent thief under everything (2026-07-29). |
| `scripts/blocked_candidate_audit.py` | What did the gates BLOCK — and would it have won? |
| `scripts/bridge_monitor.py` | Bridge Data Monitor — snapshots every 15 min, logs to file. |
| `scripts/broker_truth.py` | broker_truth.py — the broker's own closed-trade P&L, per system trade (Michael 23.09 07:40: |
| `scripts/build_monolithic.py` | build_monolithic.py — cross-platform monolith generator for Sierra Chart remote build. |
| `scripts/build_monolithic_cpp.sh` | build_monolithic_cpp.sh — Generate monolith DLL for Sierra Chart remote build |
| `scripts/candidate_resolver.py` | Candidate Resolver — EOD script that appends RESOLVED events to gateway_decisions.jsonl. |
| `scripts/channel_guard.py` | Is anyone actually answering? One check across all three channels. |
| `scripts/channel_post.py` | Post to the inter-agent channel with an id, so a reply can cite it. |
| `scripts/check_bars_ts_types.py` | D-0717-B diagnostic — print the ACTUAL ts column types + sample rows for |
| `scripts/check_env.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/check_status.sh` | MEMS26 Status Check — run anytime to see system health |
| `scripts/classifier_truth_audit.py` | D1 — Classifier truth audit: compare labels vs Dalton on .scid truth bars. |
| `scripts/close_stale_shadow.py` | Close SHADOW trades left open from a previous session. |
| `scripts/config_consumer_guard.py` | §9א config_consumer_guard — every YAML config field must have ≥1 consumer. |
| `scripts/context_table.py` | context_table.py — bar-by-bar calibration per day type (Michael 05.10 15:30: "לעבור בר-בר … ולהתאים את ההחלטות שבזיהוי |
| `scripts/credentials_self_test.sh` | scripts/credentials_self_test.sh — verifies CC can access all needed credentials |
| `scripts/cvd_effort_result.py` | cvd_effort_result.py — Michael's "price talking to CVD" (effort vs result) study. |
| `scripts/d1_exit_proof.sh` | D1-EXIT Proof Script — runs on SIM after Michael's Sierra reload. |
| `scripts/daily_dalton.py` | daily_dalton.py — נתב-דלתון יומי · שלב 1 (CC_ORDER 2026-10-05 17:11). |
| `scripts/daily_extremes_playbook.py` | daily_extremes_playbook.py — per-session "extremes & day-type playbook" study. |
| `scripts/data_integrity_audit.sh` | scripts/data_integrity_audit.sh |
| `scripts/day_review.py` | day_review.py — the daily exam after every trading day (Michael 23.09 07:40): |
| `scripts/daytype_stability_study.py` | daytype_stability_study.py — measure the day-type label instability (T-47 / F6). |
| `scripts/db_backup.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/db_init.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/db_repair_layer_a.py` | Layer-A CVD repair — workorder docs/handoff/CC_WORKORDER_DB_REPAIR_2026-08-25.md. |
| `scripts/db_restore.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/dead_pattern_replay.py` | dead_pattern_replay.py — replay the OWN signal of every pattern that has NEVER |
| `scripts/decision_replay.py` | Decision Replay — replay gateway decisions from log, compare old vs current flags. |
| `scripts/detector_contract_guard.py` | detector_contract_guard — verify detector enrichment on real buffer shape. |
| `scripts/direction_accuracy_replay.py` | direction_accuracy_replay.py — real-time direction-ID accuracy over all RTH days. |
| `scripts/drive_sync_upload.py` | Upload MEMS26 docs/ mirror to Google Drive per docs/drive/DRIVE_SYNC_MANIFEST.yaml. |
| `scripts/e2e_fire_proof.py` | E2E Fire Proof — 11-link chain audit per session day (Michael 2026-07-29). |
| `scripts/entry_side_replay.py` | entry_side_replay.py — E1/E2/E3 ENTRY-SIDE replays over every live-era session. |
| `scripts/entry_side_tables.py` | entry_side_tables.py — turn the entry_side_replay JSON dumps into the tables. |
| `scripts/eod_anchor_trial_report.py` | EOD Anchor Trial Report — per-trade audit + S2 histogram + counterfactual. |
| `scripts/eod_data_handoff.sh` | eod_data_handoff.sh — daily data packet from the TRADING machine to git, |
| `scripts/eod_review.py` | EOD review for ONE trading day (Michael 2026-07-22): today's trades, how |
| `scripts/extreme_detection_audit.py` | Extreme detection & bias audit — CC_NEXT_2026-08-23D. |
| `scripts/f1_compass_replay.py` | F1 replay — would DIRECTION_COMPASS_V1 have prevented the +$576 direction family? |
| `scripts/fill_truth.py` | אמת-המילויים — P&L ממחיר-מילוי בפועל, לא ממחיר-הפקודה. |
| `scripts/fire_drill.py` | fire_drill — ירי-יבש של שרשרת ההחלטה לפני פתיחה (מייקל 2026-07-08). |
| `scripts/fire_readiness_real.py` | Stage E: replay real RTH setups through read-only, pure readiness gates. |
| `scripts/flag_guard.py` | flag_guard — אימות שדגלים שנפסקו לא זזו (מייקל 2026-07-08). |
| `scripts/forward_gate.py` | forward_gate.py — forward production-path gate on golden sessions. |
| `scripts/fwd_harness.py` | fwd_harness.py — FORWARD production-path test (cowork-dev 2026-09-10). |
| `scripts/g4_pkg5_latency_probe.py` | g4_pkg5_latency_probe.py · G4 UAT Axis 4 · process_bar latency measurement. |
| `scripts/gap_analysis.py` | Gap Analysis — "if we made 10 points and the range was 200, there were lots |
| `scripts/gate_profit_audit.py` | gate_profit_audit — did a gate block a WINNER? (Michael 14.08) |
| `scripts/gate_scorecard.py` | gate_scorecard.py — the opinion quality of every gate and every shadow producer, on ALL their candidates |
| `scripts/gen_daily_report.py` | gen_daily_report — דוח-יומי אוטומטי (Michael 2026-07-16, "דוח יומי שגם יופיע בכיס"). |
| `scripts/gen_daily_trade_tables.py` | Generate per-day trade tables for every live session. |
| `scripts/gen_flag_index.py` | gen_flag_index.py — generate docs/FLAG_INDEX.md, the canonical index of every |
| `scripts/gen_index.py` | Generate a living index of the MEMS26 codebase. |
| `scripts/gen_measurement_index.py` | gen_measurement_index — one place that answers "did we already measure this? |
| `scripts/gen_pattern_visual.py` | OUT="/sessions/epic-jolly-sagan/mnt/mems26_web_git/docs/spec_authority/PATTERN_VISUAL_BY_DAYTYPE_2026-07-02.html |
| `scripts/gen_phone_pages.py` | gen_phone_pages.py — the phone's trade-review app (Michael 22.09 10:20 + 10:50): |
| `scripts/gen_readiness_page.py` | gen_readiness_page — תיק-המוכנות, מיוצר ממקור-האמת ולא נכתב ביד. |
| `scripts/gen_task_board.py` | gen_task_board — writes the static fallback frontend/v9/public/task_board.json |
| `scripts/gen_tree_board.py` | gen_tree_board.py — the Dalton tree drawn as a board that grows (Michael 23.09 09:20: "האם יש לנו עץ? |
| `scripts/generate_ts_types.py` | Generate TypeScript event types from registry.yaml. |
| `scripts/good_pattern_fix.py` | good_pattern_fix.py — why the patterns that MAKE money don't fire enough, and |
| `scripts/good_pattern_gates.py` | good_pattern_gates.py — gate-side census for the money-making patterns. |
| `scripts/good_pattern_oos.py` | good_pattern_oos.py — the honesty pass on top of good_pattern_fix.py. |
| `scripts/good_pattern_ts_ladder.py` | good_pattern_ts_ladder.py — TREND_STEP measured with ITS OWN ladder. |
| `scripts/guard_tests.sh` | guard_tests.sh — run the regression guards that protect live trading behaviour. |
| `scripts/ideal_entries.py` | ideal_entries.py — not our trades: for EVERY past session, the 2 biggest moves and |
| `scripts/ideal_precision.py` | ideal_precision.py — F18 · T-413 — Signature precision on ideal-entry bars. |
| `scripts/improvement_report.py` | improvement_report.py — "how much would the system have made on every past day, before vs after the fixes |
| `scripts/inbox_relay.py` | INBOX relay — polls Render for Michael's instructions, writes to MICHAEL_INBOX.md. |
| `scripts/inbox_update.py` | MICHAEL_INBOX — append a text entry to the inbox for Michael's review. |
| `scripts/income_forecast_after_fixes.py` | Session-block bootstrap income forecast from an integrated replay JSON. |
| `scripts/kill_switch.py` | Kill-switch CLI — engage/disengage/status via the backend API. |
| `scripts/leg_exemption_replay.py` | LEG-EXEMPTION replay — quantify, per gate, what a leg exemption would have paid. |
| `scripts/live_pnl.py` | live_pnl — the one number, and what it rests on. |
| `scripts/load_soak_test.py` | Load soak test — concurrent high-frequency pushes to all hot endpoints. |
| `scripts/machine_health.py` | machine_health.py — one-screen read-only health of the trading Mac. |
| `scripts/marks_vs_tree.py` | marks_vs_tree.py — every mark on the canvas (Michael's, and ours = the day-review ideal entries) becomes a |
| `scripts/mechanism_verdict.py` | §9ג mechanism_verdict — daily gate-by-gate verdict. |
| `scripts/mems26_arming_gate.py` | mems26_arming_gate — proves the SYSTEMS are armed, not just the services alive. |
| `scripts/mems26_bootstrap_agents.sh` | mems26_bootstrap_agents.sh — the nine mems26 LaunchAgents, in ONE place. |
| `scripts/mems26_doctor.sh` | ============================================================================ |
| `scripts/mems26_fingerprint.sh` | mems26_fingerprint.sh — machine-identity digest (Michael 2026-08-13: |
| `scripts/mems26_preflight.sh` | mems26_preflight.sh — "האם כל המערכות מחוברות כמו שצריך?" (מייקל 07-13). |
| `scripts/mems26_restore.sh` | mems26_restore.sh — roll an out-of-git surface back to a snapshot taken by mems26_snapshot.sh. |
| `scripts/mems26_snapshot.sh` | mems26_snapshot.sh — snapshot every out-of-git surface BEFORE a change, for rollback. |
| `scripts/mems26_startup_check.sh` | ============================================================================ |
| `scripts/mems26_update_check.sh` | mems26_update_check.sh — רץ כל שעה (LaunchAgent com.mems26.update_check): |
| `scripts/mems26_verify.sh` | mems26_verify.sh — one-shot "is everything consistent + up to date?" check. |
| `scripts/method_audit.py` | method_audit.py — is the method right, do the branches work (Michael 05.10 15:1x). Read-only. |
| `scripts/method_audit2.py` | method_audit2.py — which layer carries the edge (tree vs the gates after it), and label-free context cuts. Read-only. |
| `scripts/migrate_ts_varchar_to_timestamptz.py` | Gap #2: Migrate ts columns from varchar to timestamptz in 11 tables. |
| `scripts/missed_trade_watch.py` | Missed-trade / quality watch — live session supervisor (Michael 2026-07-17: |
| `scripts/missed_trades_study.py` | missed_trades_study.py — the moves we missed in the last N sessions, from candles / |
| `scripts/mobile_relay.py` | MEMS26 mobile relay — pushes snapshot + polls emergency commands from Render. |
| `scripts/morning_briefing.py` | בריפינג-בוקר — מה כל מערכת מחפשת היום + חשבון הסטופים (מייקל 2026-07-08). |
| `scripts/nightly_exit_review.py` | nightly_exit_review — the nightly learning loop (Michael ruling 2026-07-11/12). |
| `scripts/open_drive_branch_study.py` | open_drive_branch_study.py — the opening-drive BRANCH on every past session |
| `scripts/opening_atr_audit.py` | Is the stop band at the open calibrated on pre-market volatility? |
| `scripts/opening_signal_edge.py` | opening_signal_edge.py — which opening signals actually carry DIRECTION? |
| `scripts/ops_log.py` | Central ops log (N12 — Michael 2026-07-16: "קובץ לוג שמקבל את הכל"). |
| `scripts/oracle_engine.py` | oracle_engine.py — F14 · T-408 — Oracle as discovery engine in the nightly scan. |
| `scripts/oracle_study.py` | oracle_study.py — what the BARS say would have worked (cowork 17.09 18:05). |
| `scripts/oracle_validate.py` | oracle_validate.py — F15 · T-409 — Validation protocol for oracle conditions. |
| `scripts/oracle_vs_engine.py` | oracle_vs_engine.py — every session, the full-vision path vs what the engine did at those moments |
| `scripts/package_for_migration.sh` | package_for_migration.sh — bundle the FULL MEMS26 stack for the second (Sierra) machine. |
| `scripts/parity_report.py` | parity_report.py — EOD cross-machine parity check (cc-imac, 2026-08-19). |
| `scripts/patch_woodies_5min_hud.py` | Patch woodies_5min.json with P30.10 HUD fields (interim until DLL Export 8b is live). |
| `scripts/pattern_evidence_study.py` | pattern_evidence_study.py — OUR patterns × (location · sequence · trigger · volume). |
| `scripts/pattern_watch.py` | pattern_watch.py — poll build/pattern-status, log per-pattern blockers. |
| `scripts/phone_reply.py` | phone_reply.py — append an agent reply to the durable phone thread. |
| `scripts/phone_request_guard.py` | Requests Michael sent from the phone that no task log ever recorded. (T-208) |
| `scripts/pkg0_redis_migrate.py` | Pkg 0 · Redis migration · chart_5min → five_min |
| `scripts/place_test_demo_order.py` | Pipeline 5 — place ONE test DEMO entry to Sierra Sim. MICHAEL runs this (he holds the |
| `scripts/pnl_reconcile.py` | T-10 / T-62 — books vs broker, per trade, from the Sierra fills journal. |
| `scripts/post-commit-hook.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/post_restart_verify.sh` | post_restart_verify.sh — liveness gate after every restart/kickstart. |
| `scripts/pre-commit-hook.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/progress_study.py` | progress_study.py — "האם יש שיפור מיום ליום?" (מייקל 23.09 11:42). |
| `scripts/rebuild_bar_truth.py` | rebuild_bar_truth.py — Read Sierra .scid files and build 5-min truth bars. |
| `scripts/registry_audit.sh` | MEMS26 Registry Health Audit |
| `scripts/release_gate_review.py` | Hold the release gate to account (Michael 2026-07-28: "אם הוא ימנע עסקה לבדוק אותו"). |
| `scripts/repair_bars_ts_shift_2026_07_20.py` | One-shot repair — 2026-07-20 morning bars written -1h into PG (Michael approved 22:44 IL). |
| `scripts/replay_a1_wrong_side_veto.py` | A1 replay: scan 15 days of trades for wrong-side structural-target vetoes. |
| `scripts/replay_admits.py` | T-357 / פריט 5 — טבלת-ריפליי לכל setup שהגיע ל-ADMIT בהרנס. |
| `scripts/replay_c2_c3_c4_e2.py` | Consolidated replay acceptance for C2 / C3 / C4 / E2 (2026-08-11). |
| `scripts/replay_dalton_context.py` | replay_dalton_context.py — Dalton context simulation on past sessions. |
| `scripts/replay_dalton_edge.py` | Read-only DALTON_EDGE replay over v9_bars_5min_woodies (T-118). |
| `scripts/replay_dalton_over_detectors.py` | Dalton V2 context layer OVER the existing S2 detectors. |
| `scripts/replay_dalton_playbook.py` | replay_dalton_playbook.py — replay DaltonPlaybook on live/broker sessions. |
| `scripts/replay_day.py` | replay_day.py — replay all detectors on a day's bars from DB. |
| `scripts/replay_double_top_day.py` | import os, sys |
| `scripts/replay_edge_fade.py` | N1 — EDGE_FADE replay on truth bars from .scid (2026-08-02). |
| `scripts/replay_excess_counter.py` | K5 — EXCESS_COUNTER_ENTRY_V1 replay on historical bars (2026-08-09). |
| `scripts/replay_exit_size.py` | replay_exit_size.py — X1..X4: every proposed EXIT-side and SIZING change, |
| `scripts/replay_extremes_aware.py` | Replay EXTREMES_AWARE_REALIZE_V1 on historical trades. |
| `scripts/replay_f3_step_ladder.py` | F3 replay: step-scaled ladder impact on 15 days of trades. |
| `scripts/replay_f4_stair_struct_exempt.py` | F4 / G2 replay — every setup A1 ever killed, re-routed through the REAL gateway. |
| `scripts/replay_f5_runner_trail.py` | replay_f5_runner_trail.py — what RUNNER_TRAIL_V2 (F5) would have produced. |
| `scripts/replay_f6_daytype_stability.py` | replay_f6_daytype_stability.py — F6 / T-47 replay: does the stabilised label |
| `scripts/replay_fb_exit_study.py` | replay_fb_exit_study.py — FAILED_BREAK exit-policy study (E0-E5). |
| `scripts/replay_g1g2_opening_entry.py` | G1+G2 replay: opening entry triggers on 7 sessions (08-03..08-12). |
| `scripts/replay_hlst.py` | Replay Higher-Low Second Test (HLST) detector on historical 5-min RTH bars. |
| `scripts/replay_maximized_opportunity.py` | Counterfactual opportunity replay from candles + volume, never actual fires. |
| `scripts/replay_opening_windows.py` | Replay opening windows + drive location filter on historical sessions. |
| `scripts/replay_positive_map.py` | replay_positive_map.py — "ממתי ואיך זה כן עובד": תקרה/רצפה-כפולה × סוג-יום × צד-S1 × עידן. |
| `scripts/replay_release_leg_exempt.py` | replay_release_leg_exempt — H18: would a live-leg exemption on the release |
| `scripts/replay_s7_acceptance.py` | S7 Replay Acceptance — 14-day S7 score audit on historical trades (2026-08-05). |
| `scripts/replay_target_approach.py` | Replay S6_TARGET_APPROACH_REALIZE_V1 on historical trades. |
| `scripts/replay_target_spacing.py` | replay_target_spacing.py — what TARGET_MIN_SPACING_V1 would have done. |
| `scripts/replay_trade_economics.py` | replay_trade_economics.py — 5-number gate for trade_economics. |
| `scripts/replay_trend_step_entry.py` | TREND_STEP_ENTRY_V1 — research replay (2026-08-11, step-entry-agent). |
| `scripts/replay_trend_stop_floor.py` | Replay TREND_STOP_FLOOR_V1 on truth bars — GO/NO-GO for enable. |
| `scripts/report_blocked.sh` | Post a concise BLOCKED summary to Slack. |
| `scripts/restart_all.sh` | MEMS26 Restart All — stop + start |
| `scripts/restore_cvd_days.py` | restore_cvd_days.py — rebuild the CVD rows that the bar_id-keyed writer ate. |
| `scripts/review_lib.py` | review_lib.py — shared hindsight primitives for the day-review tools |
| `scripts/review_report.py` | review_report.py — the consolidated replay report over every reviewed day (Michael 23.09 09:20: |
| `scripts/ruled_flag_add.py` | Add or replace ONE entry in config/RULED_FLAGS.yaml (the enforcing memory of Michael's rulings). |
| `scripts/run_stage.sh` | MEMS26 Stage Runner — safe automation for prompt stages |
| `scripts/s4_full_audit.py` | SYSTEM-4 (Woodies CCI) FULL AUDIT — every trading day we have. |
| `scripts/s6_eod_report.py` | System-6 EOD report — ביקורת סטופ-חכם/מימוש-חכם על עסקאות היום (מייקל 2026-07-08). |
| `scripts/scratch_k_sweep.py` | סריקת-k לסף ה-MAE-scratch — מה היה קורה בכל סף, על נתוני-אמת. |
| `scripts/setup_engine.py` | setup_engine.py — F17 · T-411 — Multi-bar setup detection engine. |
| `scripts/setup_validate.py` | setup_validate.py — F17b — Validation protocol for setup_engine setups. |
| `scripts/shadow_promotion_board.py` | T-153: Shadow promotion board — reads the unified ledger and reports. |
| `scripts/shadow_slot_scan.py` | T-152 — what the ONE live slot could actually have taken from the shadow set. |
| `scripts/sierra_activity_join.py` | T-256 — per-trade books-vs-broker, joined on Sierra's **InternalOrderID**. |
| `scripts/signature_rule_test.py` | signature_rule_test.py — can a LOCATION / VOLUME / CANDLE rule find winning trades on its own? |
| `scripts/sim_drill_5_contracts.py` | SIM drill: does the compiled ladder actually protect all five contracts? |
| `scripts/sim_matrix.py` | N9 — day-type × pattern SIMULATION MATRIX (Michael 2026-07-16: "הדמיה לכל סוג-יום"). |
| `scripts/sim_matrix_e2e.py` | N9-hot — Sierra-sim FILL layer for the day-type × pattern matrix (2026-07-17). |
| `scripts/sim_woodies_replay.py` | import os, sys, datetime as dt, json |
| `scripts/simulate_trend_day.py` | Simulate a Trend Day through S4 (Woodies) and S2 (FiveMin). |
| `scripts/slack_notify.sh` | MEMS26 generic Slack notifier. |
| `scripts/sot_health.py` | SOT_HEALTH — Source of Truth Health Check. |
| `scripts/sot_map_guard.py` | Does the Source-of-Truth map still describe the code it points at? |
| `scripts/spec_compliance_audit.sh` | ──────────────────────────────────────────────────────────────── |
| `scripts/stage5_context_root_wf.py` | stage5_context_root_wf.py — T-543 stage 5 (CC_ORDER_2026-10-05_DAILY_DALTON §3, BRIEF §2.4), read-only. |
| `scripts/stair_hold.py` | STAIR_HOLD — the DAY_LESSONS walk-forward with ONE change: the exit (Michael 06.10 13:07 IL). |
| `scripts/stall_exit_backtest.py` | STALL_EXIT backtest — flag OFF, research only (Michael 2026-07-11). |
| `scripts/stall_exit_backtest_v2.py` | STALL_EXIT v2 backtest — drawdown-gated (Cowork, 2026-07-12). Research only. |
| `scripts/start_all.sh` | MEMS26 Start All — launches Bridge + Backend + Frontend in screen sessions |
| `scripts/start_audit.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/stop_all.sh` | MEMS26 Stop All — cleanly stops Bridge + Backend + Frontend |
| `scripts/structure_exit_replay.py` | When do the StructureExit conditions actually occur, and would exiting help? |
| `scripts/supervisor.py` | supervisor.py — פיקוח והמלצות (T-536, Michael 05.10: "פיקוח והמלצות לשיפור המערכת כדי למקסם רווחים כבר מהיום", |
| `scripts/swing_turn_test.py` | swing_turn_test.py — can a CAUSAL rule pick the rotation swings the full-vision oracle found? |
| `scripts/sync_env_from_ruled.py` | sync_env_from_ruled — make .env match Michael's RULED_FLAGS.yaml (Michael 07-13). |
| `scripts/system2_full_audit.py` | system2_full_audit.py — SYSTEM-2 full audit across every session we have. |
| `scripts/system_index.py` | system_index.py — the whole MEMS26 system in one read-only index (T-533, Michael 05.10 "סוכן שיבצע אינדקס על הכל"). |
| `scripts/t160_pnl_trust_audit.py` | T-160: P&L trust audit — marks trades without exit_price as untrusted. |
| `scripts/t211_backfill_apply.py` | T-211 backfill — add the missing T0 leg and recompute P&L from real fills. |
| `scripts/t211_t0_backfill.py` | SUPERSEDED (02.09): list-only, --apply branch was empty, filter missed #948. |
| `scripts/t316_kind_by_location.py` | T-316: kind_by_location measurement script — rewrite (2026-09-11). |
| `scripts/t317_pre_t1_realize_replay.py` | T-317 measurement: pre-T1 CEILING_FAILED/FLOOR_FAILED realize-on-confirm. |
| `scripts/t319a_normal_day_zones.py` | T-319a — Normal Day Zone Analysis |
| `scripts/t563_plist_footprint_fix.sh` | t563_plist_footprint_fix.sh — T-563 (cowork 08.10): let S3 run in SHADOW under the LaunchAgent. |
| `scripts/task_log_guard.py` | task_log_guard — make the task log fail loudly instead of going stale. |
| `scripts/test_binary_convergence.py` | Test structural binary classifier convergence against post-hoc. |
| `scripts/tp_audit.py` | TP audit v1 — האם המימושים (T1) נכונים פר-תבנית×סוג-יום מול מה שהיום נתן |
| `scripts/tp_audit_v2.py` | TP audit v2 — target placement analysis (30 days) via direct psql. |
| `scripts/trade_activity_feed.py` | Trade Activity Log feeder — extracts fill/stop-move events from Sierra's binary log. |
| `scripts/tree_diff.py` | T-392: Tree diff — compare real gate decisions vs draft tree v2. |
| `scripts/tree_learner.py` | tree_learner.py — a decision tree that SPLITS ON THE CIRCUMSTANCES of every candidate and grows with the data |
| `scripts/tree_measure.py` | tree_measure.py — the nightly measurement of DECISION_TREE_V3: every node and every leaf of the tree gets |
| `scripts/tree_prune_variant.py` | tree_prune_variant.py — build a replay VARIANT of the live tree with named leaves set to SKIP. |
| `scripts/uat_hotfix_4_3.sh` | set -e |
| `scripts/uat_hotfix_4_4.sh` | set -e |
| `scripts/uat_hotfix_4_5.sh` | set -e |
| `scripts/uat_lib.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_1.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_2.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_27_5b_live_price.sh` | P27.5b UAT — live_price freshness check |
| `scripts/uat_prompt_3.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_3_5.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_4.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_prompt_5.sh` | set -euo pipefail |
| `scripts/uat_prompt_6.sh` | set -e |
| `scripts/uat_prompt_7.sh` | set -e |
| `scripts/uat_prompt_8.sh` | set -e |
| `scripts/uat_prompt_9.sh` | set -e |
| `scripts/uat_prompt_d1.sh` | set -e |
| `scripts/uat_prompt_d2.sh` | set -e |
| `scripts/uat_template.sh` | ═══════════════════════════════════════════════════════════════ |
| `scripts/uat_tpo_stepped_lines.sh` | P31 Issue B — TPO stepped lines UAT. |
| `scripts/uat_woodies_live_tick.sh` | P30.10 — verify building-bar tick: current_bar merges into tail (close/CCI move between polls). |
| `scripts/update_news_calendar.py` | update_news_calendar — weekly auto-seed of config/news_calendar.yaml (Michael 07-13). |
| `scripts/v9_export_promoter.py` | v9_export_promoter.py — native-macOS `.tmp`→`.json` promoter. |
| `scripts/variation_playbook_test.py` | variation_playbook_test.py — branches for the days that make up most of the year: the day opens with |
| `scripts/verify_compliance_coverage.py` | MEMS26 V9 — Compliance Coverage Verification. |
| `scripts/verify_orphan_place_stop_sim.py` | Read-only sim harness for ORPHAN_AUTO_STOP_V1 (Michael 2026-07-20 doctrine). |
| `scripts/verify_place_stop_v2_sim.py` | W8 PLACE_STOP v2 — SIM verification script (2026-07-28). |
| `scripts/verify_sierra_dll_deploy.sh` | verify_sierra_dll_deploy.sh — confirm Sierra source/DLL/export alignment |
| `scripts/verify_t17_e2e_4contract_sim.py` | Read-only sim harness for T17 — 4-contract E2E ladder (Michael 07-19/07-20). |
| `scripts/walk_forward.py` | walk_forward.py — out-of-sample (OOS) validation of the live decision tree's branches (METHOD_AUDIT_2026-10-05 §3 step 1). |
| `scripts/week_replay.py` | Week Replay: per-day simulation of Aug 11-14 with today's code. |
| `scripts/weekly_report.py` | weekly_report — IDEA-3: the Friday-evening weekly report (Michael 07-13). |
| `scripts/what_works_study.py` | what_works_study.py — "מה מביא לנו תוצאה טובה יותר" (Michael 22.09 13:20). |
| `scripts/whatif_report.py` | WHATIF report — what would the CURRENT system detect on a historical session? |
| `scripts/winner_profile.py` | winner_profile.py — what did the WINNING trades have in common? (Michael 17.09 19:45: |
| `scripts/wire_guard.py` | wire_guard — prove every command/exit/alert call site can actually be called. |

## 10 · דוחות אחרונים

- `docs/reports/T564_ALLOW_INITIATIVE_SHORT_VAR_1819_2026-10-08.md` (2026-10-08 02:40)
- `docs/reports/NIGHT_INSIGHTS_2026-10-07.md` (2026-10-08 00:17)
- `docs/reports/T526_WOODIES_OVERWRITE_WRITER_2026-10-08.md` (2026-10-08 00:06)
- `docs/reports/OPS_LOG_2026-10-07.md` (2026-10-07 23:37)
- `docs/reports/REPLAY_REVIEW_2026-10-07.md` (2026-10-07 23:09)
- `docs/reports/DAY_REVIEW_2026-10-07.md` (2026-10-07 23:09)
- `docs/reports/SUPERVISION_LATEST.md` (2026-10-07 22:36)
- `docs/reports/SUPERVISION_2026-10-07_2236.md` (2026-10-07 22:36)
- `docs/reports/SUPERVISION_2026-10-07_2136.md` (2026-10-07 21:36)
- `docs/reports/SUPERVISION_2026-10-07_2036.md` (2026-10-07 20:37)
- `docs/reports/SUPERVISION_2026-10-07_1936.md` (2026-10-07 19:36)
- `docs/reports/SUPERVISION_2026-10-07_1836.md` (2026-10-07 18:37)

## 11 · ריצות-הרנס אחרונות

- `harness_out/t466` — ALL DONE treev3 Fri Sep 25 13:32:48 IDT 2026
- `harness_out/t564` — ALL DONE Thu Oct  8 02:37:50 IDT 2026
- `harness_out/t561` — 
- `harness_out/t543` — report: docs/reports/T543_STAGE5_CONTEXT_ROOT_2026-10-02.md
- `harness_out/t24` — PHASE_SUMS {'C': (200, -11825.96), 'B': (76, -698.43), 'D': (20, -66.46), 'A': (2, -450.0)}
- `harness_out/t542` — 25 passed, 2 warnings in 16.63s
- `harness_out/t538` — ALL DONE t538h Mon Oct  5 16:04:17 IDT 2026
- `harness_out/t529` — → /Users/michael/Downloads/mems26_web_git/docs/reports/TREE_V3_MEASURE_2026-10-05.md
- `harness_out/t523` — ALL DONE t523ref Thu Oct  1 23:39:08 IDT 2026
- `harness_out/t518` — ALL DONE t518pkg Wed Sep 30 11:11:08 IDT 2026
