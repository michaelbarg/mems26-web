# cc — פקודת-ראשון (תוכנית-סופ"ש מייקל 08.08) · יעד: שני = מסחר-מ-Mac2, 4 חוזים
מקורות-מחייבים: WEEKEND_AUDIT_GAPS_FIXES + WEEKEND_TRADING_RESEARCH + S6_S7_EXPLAINED (08.08).
Rule-5 בכל סעיף. שום חימוש לפני סגירת-K1.

## K1 — 🔴 חוסם-חימוש: תור-הפקודות שבור בפרודקשן
drain_command_queue() בלי אף caller ב-runtime; 3 קבצים תקועים; PLACE של #652 + CANCEL לא הגיעו
לסיירה. (א) חווט drainer ללופ-הרץ (backend loop/manager tick); (ב) נקה את התור-התקוע (בקרת-
מייקל: אל תשלח פקודות-עבר!); (ג) טסט-אינטגרציה end-to-end בסים: PLACE+MODIFY בזמן-אמת מגיעים
ל-DLL; (ד) פיוס-#652 (עסקת-פנטום, ep בלתי-אפשרי, contracts:0 — שורש+תיקון+רטרו).
## K2 — כותב-סוג-היום: שורש-המוות (self-heal לא עבד — פערי 55-60ד' שישי). לתקן את הסיבה, לא רק להריץ-מחדש.
## K3 — מסלול-Pullback (הפער-המרכזי של שישי):
(א) החיה את HLST (W6, מת — אפס callers): חיווט+דגל+טסטים; (ב) טריגר-מיקום: pullback-אל-LSMA/קצה-IB
ביום-מגמה/וריאציה עם-הרגל ⇒ כניסה עם סטופ-מבני-צר (17:45/17:55 שישי = מקרי-הקבלה, R:R 1.3);
(ג) awaiting_release: חריג-pullback (structure-turn איחר שם); (ד) סימטריית-chase ל-S4-ZLR
(עבר @3pt-מהשיא בעוד S2 נחסם @9.3) — ZLR-live −$396 מ-07-15 = מחיר-הצ'ייס. flag-OFF⇒replay⇒פסיקה.
## K4 — קונפלואנס S2×S4 כרכיב-S7: agreement=65%wr מול 50% solo (80/40 מ-07-15, n-קטן) ⇒
רכיב-ציון (לא שער-קשיח) + לוג. ## K5 — קונסיומר-EXCESS-קיצון + חריג-playbook לפייד-מאושר-קיצון
(שישי @7781.5: +$150-250 חסום-קטגורית) — flag-OFF⇒replay. ## K6 — Trend-path: 03/05.08 (rib-floor,
close-location) — פותח TREND_STOP_FLOOR+EDGE_FADE. ## K7 — השלמות: ntfy (PAUSE/EOD/חירום+rate-limit,
כשלים ל-warning) · כרטיס-Render · פוסט-מורטם-על-רטרו · 8 דגלים לרג'יסטרי · commit-חובות · דופליקט-.env.
## K8 — Mac2 (שני-בבוקר, עם cowork): פרוטוקול-סנכרון קבוע: אחרי כל push כאן ⇒ שם git pull+
kickstart+flag_guard+verify (סקריפט mac2_sync.sh). DLL: deploy שם + shasum==כאן. שער-GO מלא
(CUTOVER_MAC2) + K1-מאומת-שם ⇒ מייקל מחמש. ## K9 — הכנת-שני (לא להדליק לפני!): FIXED_CONTRACTS_4=1,
T0_TARGET_PTS=3.0 (פסיקת-מייקל 08.08: 4 חוזים, C1=T0-3נק'; מרג'ין $1,104<$2,724) — מוכן ב-RULED
כ-pending, הדלקה בבוקר-שני עם הפסיקה הסופית.
