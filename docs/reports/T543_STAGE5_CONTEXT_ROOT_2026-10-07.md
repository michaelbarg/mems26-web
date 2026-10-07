# T-543 שלב 5 — שורש-הקשר (מבנה-IB · שעה · סוג-כניסה) לשלבי C/D, walk-forward מול t529b · 2026-10-07

**כותב:** cowork (Claude-session) · **נמדד:** 07.10 15:25–15:27 IL, קריאה-בלבד (JSON קיימים + SELECT ברים), אפס הרנס, אפס עץ/.env/ריסטארט · **הזמנה:** `docs/handoff/cc_orders/CC_ORDER_2026-10-05_DAILY_DALTON.md` §3 שלב 5 = BRIEF §2.4 · **טבלת-הייחוס:** `docs/reports/WALK_FORWARD_2026-10-05.md` §6 (Cursor).

## השורה
**לא עובר.** על כל 55 סשני-ה-walk-forward שורש-ההקשר לוקח פחות מהעץ (Δ −304$ במדידה הייצוגית; −176…−2,276$ לפי N_MIN), ושני חודשים שליליים (יולי −712, ספטמבר −204). רק ההחזקה-10 טובה יותר (+1,282$) — וזה בדיוק המלכוד של 05.10: החזקה לבדה אינה פסיקה. כלל-הקבלה (BRIEF §2ד: החזקה ≥ 0 **וגם** Δ > 0 על כל הסט **וגם** כל חודש ≥ 0) — נכשל בשני התנאים האחרונים. העץ החי נשאר; אין עלה, אין .env, אין ריסטארט.

## השיטה (מה נמדד בדיוק)
- וריאנט: בשלבים C/D השורש הוא התא (structure, hour-bucket, kind) כפי שהגייטוויי כתב ב-`tree_v3.vec`; התווית מידע בלבד. שלבים A/B — העלה של העץ בשני הצדדים.
- walk-forward: לסשן t הטבלה נבנית **רק** מהסשנים לפניו; תא = TAKE כש-n ≥ N_MIN ו-Σ > 0, אחרת SKIP. 10 סשני-חימום מזינים בלבד; 55 נמדדים (06.07 → 02.10).
- ניקוד זהה לשני הצדדים: המודל הקבוע של `scripts/context_table.py` (סטופ-של-המועמד, יעד 1.5R, נגיעה ראשונה על ברי-5-דקות, סגירת-יום, 5$/נק׳, עמלה 2.60$). **בריכות, לא סלוט** — אין סימולציית עסקה-אחת-בכל-רגע; נאמר, לא מוסתר.
- חיתוך 22:00 (העץ החי 3.4.0) מוחל על שני הצדדים.
- **המדידה הייצוגית** = מועמדים ברי-לייב בלבד (לא מפיקי-צל), שעברו את שערי-אחרי-העץ (`blocked_by` ריק או `tree:*`), ודה-דופליקציה של 30 דק׳ לכל (תבנית, כיוון). ההצדקה במספרים: בריכת-ה-TAKE של העץ במדידה הזו = +1,868$ מול +1,968$ שההרנס ביצע בפועל על אותם סשנים — קרוב. בלי הסינון (כל 4,162 המועמדים) בריכת-העץ היא −4,037$ — 75 "TAKE" ביום אחד (26 פעמים אותו CEILING_FLIP_TOUCH2) — מדד שלא מתאר את המערכת, ולכן לא פוסק (הפלט שלו למטה, לשקיפות).
- הטיה לטובת הווריאנט: מועמד שהעץ דילג עליו לא עבר את שערי-אחרי-העץ (הגייטוויי עוצר בעץ), ולכן ה"לקיחות הנוספות" של הווריאנט אינן מסוננות-שער — אופטימי לווריאנט. גם כך הוא לא עובר.

## הפקודה והפלט המלא (המדידה הייצוגית)
```
$ python3 scripts/stage5_context_root_wf.py --live-only --gated --dedup 30
T-543 stage 5 — context root (structure · hour · kind) for phases C/D, walk-forward vs t529b
sessions 65 (2026-06-15 → 2026-10-02) · N_MIN 10 · warm-up 10 · cutoff 22:00 IL on both sides · scorer = context_table fixed model (own stop, 1.5R, first touch, EOD)
candidate filter: live-only=True · gated=True · dedup=30 min per (pattern, direction)
candidates 1201 · phase C/D 924 · phase A/B 277 (A/B keep the tree's leaf on both sides)

session    label  harness   tT     tree$   vT  variant$    delta$
2026-07-06 Trend_      -51   16    -261.6   15    -374.0    -112.4
2026-07-07 Variat     +159    5    +142.0    5     +72.0     -70.0
2026-07-08 Variat      +66    5    +429.5    6    +361.3     -68.2
2026-07-09 Variat      -42    5    +156.4    3     +51.6    -104.8
2026-07-13 Normal      -40    6     +84.4    6    +151.9     +67.5
2026-07-14 Variat      -36   10    -201.0    8    -253.3     -52.3
2026-07-15 Variat     +186   11    +464.5   13    +464.3      -0.2
2026-07-16 Variat      -41   10    +183.4    9    +310.3    +127.0
2026-07-17 Variat      +81    6     +19.4    6    +295.0    +275.6
2026-07-20 Variat      -75    3    -214.0    9    -578.4    -364.4
2026-07-21 Variat      -14    4      +0.8    8    +106.1    +105.2
2026-07-23 Variat      -50    7    -489.5   12    -704.3    -214.9
2026-07-27 Variat     +160   10    +236.5    6     +56.9    -179.6
2026-07-30 Variat     +112    8    +213.0    7    +281.8     +68.9
2026-07-31 Normal       +0    3    +121.0    1     -68.8    -189.8
2026-08-03 Trend_     +111   13    +399.3   10    +487.1     +87.8
2026-08-05 Trend_     +236    5    +461.4    5    +120.1    -341.2
2026-08-06 Variat     -162    3    -144.0    2     -95.2     +48.8
2026-08-10 Variat       +0    3     -51.5    6     +75.7    +127.2
2026-08-11 Trend_      +42    6     -25.6    3     +26.0     +51.6
2026-08-12 Variat     -146    9    -450.3    9    -406.5     +43.8
2026-08-13 Variat     +238   10    +487.8    9    +187.8    -299.9
2026-08-14 Variat      -80   10    -200.4    1     -50.1    +150.3
2026-08-17 Normal      +21    5    +142.6   10    +450.2    +307.6
2026-08-18 Variat      -55    4     -74.2    3     -20.3     +53.9
2026-08-19 Variat      -45    8     +45.5   15    +169.1    +123.7
2026-08-20 Variat     +149   10    -126.6   12     -38.7     +87.9
2026-08-21 Variat      -40    6    -103.1   17    -416.7    -313.6
2026-08-24 Variat      +70    6    -193.1   14    -258.9     -65.8
2026-08-25 Variat      +69    9    -359.7    2     +37.3    +397.0
2026-08-26 Variat      +66    2    +134.5    1     -80.1    -214.6
2026-08-27 Variat      +80    6    +108.2   12     -72.4    -180.6
2026-08-28 Neutra      -62    8    +200.8    7    +373.4    +172.6
2026-08-31 Normal      -66    3     -72.8   11    -126.7     -53.9
2026-09-01 Variat     +221    7    -169.4    8     -84.5     +84.9
2026-09-02 Variat     +101   10     -30.3   13    -224.4    -194.0
2026-09-03 Variat       -4    6     +23.2    5     -71.7     -94.9
2026-09-04 Variat     +115    8     +31.7    2     +19.8     -11.9
2026-09-08 Variat      +48   20    +356.7   16     +64.7    -292.1
2026-09-09 Variat      -15    7     -99.5    3     -24.1     +75.4
2026-09-10 Normal       +4    2     -86.4    4     -85.4      +1.1
2026-09-11 Variat      -86    9    +185.3    3    -132.8    -318.1
2026-09-14 Neutra     +149    5     +58.9   11     +66.4      +7.5
2026-09-15 Variat      +18    9    -203.4    0      +0.0    +203.4
2026-09-18 Variat      +82    1     +79.9    9    -437.1    -517.0
2026-09-21 Trend_     +230   14   +1254.9   11   +1120.2    -134.7
2026-09-22 Variat     +162   12    -261.8    5      +7.6    +269.4
2026-09-23 Variat     +156    6     +93.8    7    +136.2     +42.4
2026-09-24 Neutra      +22    6     +11.9    2     +56.1     +44.1
2026-09-25 Variat      -35    5     -78.0    5    -139.2     -61.2
2026-09-28 Neutra      -41    4     -43.5    4     -45.4      -1.9
2026-09-29 Variat      -53    5    -208.6    2    -112.7     +95.9
2026-09-30 Variat     -148    8    -272.7    8    +324.8    +597.5
2026-10-01 Variat     +182    6    +236.9    5    +520.1    +283.2
2026-10-02 Variat      +21    9     -74.6    1     +72.4    +147.0

THE NUMBERS (walk-forward sessions 55, 2026-07-06 → 2026-10-02; pools, not slots)
  tree TAKE pool ........   +1868.1$  (394 candidates taken)
  variant (context root)    +1564.1$  (387 candidates taken)
  delta .................    -304.0$   better 29 / worse 26 / same 0 sessions
  holdout-10 (2026-09-21 → 2026-10-02): tree   +658.1$ · variant  +1940.0$ · delta  +1281.9$
  by month (tree / variant / delta): 2026-07 +885 / +172 / -712 · 2026-08 +179 / +361 / +182 · 2026-09 +643 / +438 / -204 · 2026-10 +162 / +593 / +430
  harness-executed t529b on the same sessions (reference, slot-aware, real exits): +1968.05$
  acceptance rule (holdout >= 0 AND delta > 0 AND every month >= 0): does NOT pass

the context table after all 65 sessions (phase C/D; TAKE = n >= 10 and sum > 0):
  structure  hour    kind            n      sum$    per$  verdict
  up         18-19h  BREAK          70     +2266   +32.4  TAKE
  none       18-19h  BREAK          60     +1340   +22.3  TAKE
  none       20h+    BREAK          51      +588   +11.5  TAKE
  down       18-19h  EDGE_FADE      19      +434   +22.8  TAKE
  none       18-19h  EDGE_FADE      16      +323   +20.2  TAKE
  down       18-19h  REVERSAL       21      +293   +13.9  TAKE
  up         18-19h  REVERSAL       24      +249   +10.4  TAKE
  up         18-19h  EDGE_FADE      20      +189    +9.4  TAKE
  up         20h+    EDGE_FADE      20       -30    -1.5  SKIP
  down       20h+    EDGE_FADE      22       -49    -2.2  SKIP
  none       17h     REVERSAL       11       -55    -5.0  SKIP
  down       20h+    REVERSAL       22      -153    -7.0  SKIP
  up         20h+    REVERSAL       17      -246   -14.5  SKIP
  two_sided  20h+    BREAK          40      -303    -7.6  SKIP
  none       17h     BREAK          61      -339    -5.6  SKIP
  up         20h+    BREAK         130      -714    -5.5  SKIP
  down       18-19h  BREAK         104      -728    -7.0  SKIP
  down       20h+    BREAK         166     -1460    -8.8  SKIP
report: docs/reports/T543_STAGE5_CONTEXT_ROOT_2026-10-02.md
```

## רגישות (אותו סינון)
```
$ python3 scripts/stage5_context_root_wf.py --live-only --gated --dedup 30 --nmin 5
  variant +1691.8$ (429) · delta -176.3$ · better 28 / worse 26 · holdout delta +1326.5$ · months 07 -681 · 08 +340 · 09 -146 · 10 +310
$ python3 scripts/stage5_context_root_wf.py --live-only --gated --dedup 30 --nmin 20
  variant -408.3$ (299) · delta -2276.4$ · better 25 / worse 30 · holdout delta +647.0$ · months 07 -1872 · 08 -250 · 09 -288 · 10 +132
$ python3 scripts/stage5_context_root_wf.py --live-only --gated --dedup 30 --cutoff 0
  tree +1695.7$ (406) · variant +1175.7$ (403) · delta -520.0$ · holdout delta +1372.1$     # בלי 22:00: העץ מאבד 172$, הווריאנט 388$
```

## הפלט הגולמי (כל המועמדים, בלי סינון — לשקיפות בלבד, אינו פוסק)
```
$ python3 scripts/stage5_context_root_wf.py
THE NUMBERS (walk-forward sessions 55, 2026-07-06 → 2026-10-02; pools, not slots)
  tree TAKE pool ........   -4036.7$  (1786 candidates taken)
  variant (context root)     -586.9$  (1325 candidates taken)
  delta .................   +3449.9$   better 30 / worse 25 / same 0 sessions
  holdout-10 (2026-09-21 → 2026-10-02): tree  -2611.0$ · variant  +1684.5$ · delta  +4295.5$
  by month (tree / variant / delta): 2026-07 +4634 / +2558 / -2076 · 2026-08 -3494 / -1411 / +2083 · 2026-09 -4101 / -1229 / +2872 · 2026-10 -1076 / -505 / +571
  harness-executed t529b on the same sessions (reference, slot-aware, real exits): +1968.05$
  acceptance rule (holdout >= 0 AND delta > 0 AND every month >= 0): does NOT pass

```

## מה זה אומר
1. התווית (day_type) אינה הבעיה שחשבנו שהיא: שורש שמתעלם ממנה לגמרי מפסיד לעץ על כל הסט, בכל N_MIN. מה שהתווית תורמת (ההטיה, המיקום-מול-הערך, הפטורים) שווה יותר ממה שהרעש שלה עולה — לפחות במודל-המועמד הזה.
2. ההחזקה-10 הטובה-יותר של הווריאנט (+1,282$) חוזרת בכל וריאציה. זה אות למדידה ברמת-הרנס (סלוט, יציאות אמיתיות): 55 עצי-וריאנט (אחד לסשן, מהסשנים שלפניו) × הרנס ≈ 1.5–2 שעות בחלון-בוקר, ≤2 במקביל. זו הדרך היחידה להכריע אם ה-+1,282 הוא אמת או ארטיפקט של המודל-הקבוע. לא רץ היום (RTH). מועמד לבוקר הבא — אם מייקל רוצה.
3. הצעד הבא בתור-הכיול לפי BRIEF §2 (סדר קבוע): §2.2 רשימת-ההיתרים מהכיול, וריאנט-עץ אחד לכל היתר.

*אפס שינוי חי. העץ 3.4.0 נשאר. הסקריפט `scripts/stage5_context_root_wf.py` והפלטים `harness_out/t543/stage5_wf*.out` — בעץ-העבודה (קבצי-שלב; קומיט רק אם מייקל מבקש).*
