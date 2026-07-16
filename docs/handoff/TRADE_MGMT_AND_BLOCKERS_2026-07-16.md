# ניהול-עסקה + מפת-חסמים מלאה — S1/S2/S4/S6 · 2026-07-16 (מייקל: "עכשיו, כולל כל מה שיכול לחסום עסקאות איכותיות")

**מבצע: cc-imac (לייב). קריאה-בלבד. אמת כל שורה מול הקוד/הקונפיג החי + סמן ✅/⚠️/❌ עם ראיה (Rule 5). דווח ל-SYNC + EXECUTION_REPORT.**
כל הערכים כאן נשלפו מהקוד (`sierra_command.py`, `stop_anchors.yaml`, `RULED_FLAGS.yaml`) — המשימה שלך: לוודא שהם מיושמים חי על ה-iMac ושאף אחד מהם לא חוסם עסקה **דוקטרינית-נכונה**.

## פסקה 1 — כל הבדיקות שצריך להריץ עכשיו (על סים, is_sim=1 gate לפני כל פקודה)
עבור בסדר: ‏(א) **בריאות-מערכת** — `health` ok · `flag_guard` PASS (73) · `sync_env --check` "already matches" · `post_restart_verify` GREEN · feed age<10s · mid שפוי. ‏(ב) **מנוע-חי** — על בר-RTH ראשון: שורת-`S2-DL`/`process_bar` טרייה בלוג + `day_type` מתאכלס + `decisions`-feed עונה. ‏(ג) **דימוי-שערים פר-תבנית** (S2: 10 תבניות · S4: ZLR/GB100/FAMIR/HFE/CONT) — סטאפ-כשר במיקום-נכון עובר, סטאפ-מיקום-שגוי נחסם בשער-הנכון. ‏(ד) **פקודות-DLL** — PLACE 4×OCO (T0=3.5) → MODIFY_STOP×4 → מילוי-חלקי → FLATTEN → CANCEL → STATUS (בלי EXIT). ‏(ה) **שרשרת-רישום** — אותה עסקה ב-command→fills→v9_trades→ledger→דשבורד/כיס. ‏(ו) **ניהול-פר-סוג-יום** — טבלה 2 למטה מיושמת. ‏(ז) **מפת-חסמים** — טבלה 3: לכל שער, לוודא שאינו חוסם עסקה דוקטרינית.

## טבלה 1 — מפת-המערכות
| מערכת | תפקיד | תבניות/פלט | "ניהול" = |
|---|---|---|---|
| **S1** | מסווג סוג-יום (7-type Market Profile) | ‏Trend/Normal_Var/Neutral/… → מזין playbook+location+RR+רצפת-סטופ | תקינות-הסיווג (הבאג של Neutral↔Variation) |
| **S2** | חמש-דקות (T1_NUMBER_BAR) | REACTIVE L/S · INITIATIVE L/S · INV_HNS/HNS_TOP · DOUBLE_BOTTOM/TOP · BULL/BEAR_FLAG | סולם 4-חוזים + T0 |
| **S4** | Woodies | ZLR · GB100 · FAMIR · HFE · CONT_TREND | ZLR_MGMT ייחודי + סולם |
| **S6** | מפקח-עסקה (מגן) | — (מנהל פוזיציה פתוחה) | BE-completion + הפלת-יעד-בצד-שגוי |

## טבלה 2 — ניהול-עסקה (חוזים · T0-T3 · סטופ · BE), מיושם חי
| פרמטר | ערך (מהקוד) | דגל/מקור | הערה |
|---|---|---|---|
| חוזים | **4** (FIXED_CONTRACTS_4, קדימות-עליונה 6 נק'-חנק) | RULED | SIZE_CAP_OVER_FIXED מקטין למטה בלבד (min) |
| **T0** | חוזה-1 יוצא ב-**±3.5 נק'** | T0_TARGET_PTS=3.5 | סולם מוזח: C2→T1 · C3→T2 · C4→T3 |
| T1/T2/T3 | יעדים-מבניים (מדף/זון) או R לפי-סיכון | stop_anchors t1_ladder | רצפת-T1 3 נק' · R: ≤5נק'→1.0 · ≤10→0.75 · ≤15→0.65 |
| סטופ | **מבני תמיד גובר** (3 ticks מעבר לקצה) · ATR=שער-גודל בלבד · רצפה 4 ticks | stop_anchors principles | ATR לא מזיז סטופ לתוך-הנר |
| **רצפת-סטופ×ATR** | רוטציה **0.8×ATR** · מגמה **0.5×ATR** | STOP_FLOOR_ROTATION_ATR=0.8 | שורש מות-#372 |
| BE | אחרי T1 → סטופ ל-break-even | ZLR_MGMT / S6 | |
| **ZLR (S4) ייחודי** | **T1=2 חוזים · T2=1 · אפס-תזוזת-סטופ לפני T1 · אחרי T1→BE** | ZLR_MGMT_V1=1 | REACTIVE נשאר 1/1/1 |
| תקרת-סיכון | 25 נק'/חוזה ($125) · סולם: ≤15נק'→3c ≤25→2c >25→1c | stop_anchors (V2=SHADOW) | חי = FIXED_4 + SIZE_CAP |
| מפקח (S6) | protective: BE-completion + הפלת-יעד-בצד-שגוי; עירום/רוחב=ALERT; **לעולם לא op=EXIT** | SYSTEM6_AUTOCORRECT=protective | |
| יציאות עובדות | T0/T1/T2/T3 (OCO צד-סיירה) · MODIFY_STOP · FLATTEN_ACCOUNT | — | op=EXIT שבור-ידוע, אסור |

## טבלה 3 — כל מה שיכול לחסום עסקה (26 שערי-gateway, לפי הסדר) + סיווג-סיכון-לאיכות
לכל שער: מה בודק · האם יכול לחסום **עסקה איכותית** (🟢=בטוח/דוקטריני · 🟡=לכייל/עבר-הרעלה · 🔴=חסם-איכות-ידוע-שתוקן).
| # | שער | חוסם כש… | סיכון-לאיכות |
|---|---|---|---|
|1|kill_switch|מתג-חירום ידני|🟢|
|2|session_gate_closed|מחוץ 16:30–22:00|🟢 (מונע רק מחוץ-חלון)|
|3|eod_entry_cutoff|קרוב-לסגירה|🟢|
|4|feed_watchdog|פיד תקוע/ישן|🟢 (הגנה; אם יורה-כוזב על TZ→🟡, תוקן ל-DB)|
|5|cooldown|צינון אחרי-עסקה|🟡 (יכול לחסום המשך-מהיר)|
|6|**suffering_side_veto (SSV)**|צד הפסיד שוב-ושוב|🔴→תוקן: **כבוי** (SSV_GATE_V1=0) + הזנה live/demo בלבד|
|7|duplicate_fire|אותו איתות ממש|🟢|
|8|chop_searching|Layer-0 chop|🟢 (כבוי כברירת-מחדל)|
|9|opening_type_gate|סוג-פתיחה לא-מתיר|🟡|
|10|**daytype_playbook**|SKIP לסוג-יום|🔴→תוקן: Variation=FULL קצה-אל-קצה+POC|
|11|trend_direction_gate|נגד-מגמת-היום|🟡|
|12|reactive_location|fade לא-בקצה|🟢 (דוקטריני)|
|13|**location_gate**|כיוון≠מיקום (VAH/VAL)|🟢 חדש (מונע #372: לונג רק ברצפה, שורט רק בתקרה)|
|14|daytype_position_gate|משפחה≠סוג-יום|🟡 (הוסרו 2 היפוכי-דוקטרינה)|
|15|**cont_trend_filter**|נגד-צבע/כיוון LSMA|🔴→תוקן: LSMA_SUSTAIN 3→2 (פיגור-היפוך)|
|16|direction_context|נגד-הקשר-יומי|🟡 (פטור-fade בימי-רוטציה)|
|17|lsma_flat|אין-שיפוע לעסקת-המשך|🟡|
|18|news_blackout|חלון-מאקרו|🟢|
|19|day_direction_doctrine|דוקטרינת-כיוון|🟡|
|20|entry_not_confirmed|בר-אישור S4 לא-הגיע|🟡 (ציר פיגור-זיהוי — מנוטר)|
|21|t1_wrong_side|T1 בצד-הפוך|🟢 (סטאפ-פסול)|
|22|**rr_entry_gate**|R:R ל-T1 מתחת-סף|🔴→תוקן: RR_MIN_ROTATION=0.65 בימי-רוטציה|
|23|daily_loss_halt|−$400 נפרץ|🟢|
|24|consecutive_loss_halt|רצף-הפסדים|🟢 (סף לא-מוגדר=כבוי)|
|25|**s4_risk_cap**|סיכון>תקרה / pattern_loss_breaker|🔴→תוקן: loss_breaker mode≠shadow (הרעלת-צל)|
|26|cluster_guard|צבירה באזור|🟡|

**מבוקש ממך (CC):** לכל 🔴 — אשר שהתיקון חי (דגל/קוד + טסט). לכל 🟡 — ודא שאינו חוסם סטאפ דוקטריני-נכון בסוג-היום הנוכחי (בדיקת-דימוי). כל ❌ = דווח מיד. סכם: "מפת-חסמים: N שערים · X בטוחים · Y מנוטרים · 0 חוסמי-איכות פתוחים" — או את החריגה.
