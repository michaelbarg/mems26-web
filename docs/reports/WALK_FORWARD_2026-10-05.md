# Walk-forward · t529b · 65 סשנים (2026-06-15 → 2026-10-02) — 2026-10-05

**פקודה:** `python3 scripts/walk_forward.py `  
**מקור:** `harness_out/t466/t529b_*.json` (ריפליי קונפיג-הלייב, עץ 3.2.0 + כל השערים) · ברים: `v9_bars_5min_woodies` (SELECT בלבד, 80 ימים, 1.6s). מודל-הערכה = `tree_measure.py`: סטופ של המועמד, יעד 1.5R, נגיעה ראשונה (סטופ קודם בתיקו), סגירת-EOD, חוזה 1, 2.60$. Σ$ של ענף = מה שהמועמדים שנותבו אליו היו עושים **אילו נלקחו** — איכות-הדעה, לא תיק.

## 1 · ספירות גולמיות

```
sessions=65 dev=55 (2026-06-15..2026-09-18) holdout=10 (2026-09-21..2026-10-02)
routes=4412 with_tree=4398 scored=4205 unscored_no_bars=0 injected_live_routes=192
branches=221 take=120 skip=101 | TAKE scored OOS=37 KEEP=6 REVERT=31 (neg_oos_n>=10: 8 · thin_oos_n<10: 23) unscored=83
ruled present=['auction_B_reversal', 'auction_B_trend_break', 'd_with_extension', 'failed_extension', 'location', 'take_failed_ext_responsive', 'take_with_extension']
ruled missing in this run=['time_cutoff']
dev     TAKE 1875 · 43% · +636$ | SKIP 1560 · 41% · -6,513$
HOLDOUT TAKE 400 · 39% · -3,212$ | SKIP 370 · 43% · +53$
```

**הגדרות.** RULED = עלה עם `ruling:` ב-`config/decision_tree_v3.yaml` (מקובץ לפי `id`, על פני כל הנתיבים); in-sample = הסשנים עד תאריך-הפסיקה, OOS = 10 הסשנים הבאים. UNRULED = כל עלה אחר לפי הנתיב המלא; הליכה מתרחבת אחת: ה-k הראשון שבו in-sample מחזיק ≥10 מועמדים פותח את אזור-ה-OOS עד תחילת ה-holdout (כל מועמד נספר פעם אחת), ובנוסף ממוצע $/מועמד על חלונות של 10 סשנים בצעד של סשן. **HOLDOUT** = 10 הסשנים האחרונים — לא משתתפים בשום הכרעת KEEP/REVERT. **KEEP** = TAKE עם OOS Σ$ > 0 **וגם** OOS n ≥ 10; אחרת **REVERT-TO-SKIP כהמלצה** (העץ החי לא נערך). SKIP-HOLDS / SKIP-COSTS = אינפורמטיבי (אין הוספת-עלה).

## 2 · הענפים הנפסקים — OOS אחרי תאריך-הפסיקה

| ענף | פעולה | פסיקה | in-sample n · win · Σ$ | OOS סשנים | OOS n · win · Σ$ | holdout n · win · Σ$ | פסק-דין | הערה |
|---|---|---|---|---|---|---|---|---|
| `failed_extension` | TAKE | S7 / T-329 — failed-extension flip (take_failed_ext, no id) · ruled 2026-09-27 | 407 · 43% · +1,207$ | 5 | 25 · 68% · +707$ | 86 · 48% · +697$ | **KEEP** | only 5 sessions after the ruling (window 10) · OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |
| `auction_B_trend_break` | TAKE | T-484 — auction-B first hour reads Trend, BREAK · ruled 2026-09-25 | 67 · 55% · +811$ | 5 | 8 · 62% · +214$ | 15 · 53% · -201$ | **REVERT-TO-SKIP (OOS n=8 < 10)** | only 5 sessions after the ruling (window 10) · OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |
| `take_failed_ext_responsive` | TAKE | T-529 — failed-extension before the location skip · ruled 2026-10-03 | 4 · 50% · +129$ | 0 | 0 · - · 0$ | 1 · 100% · +159$ | **REVERT-TO-SKIP (OOS n=0 < 10)** | no session after the ruling date yet — OOS not measurable |
| `take_with_extension` | TAKE | T-466/T-480 — Normal label, IB extended → with it · ruled 2026-09-25 | 36 · 25% · -1,137$ | 5 | 1 · 0% · -43$ | 3 · 67% · +86$ | **REVERT-TO-SKIP (OOS n=1 < 10)** | only 5 sessions after the ruling (window 10) · OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |
| `auction_B_reversal` | TAKE | S5 / T-494 — auction-B reversal at the opening extreme · ruled 2026-09-27 | 49 · 47% · +696$ | 5 | 9 · 44% · -60$ | 13 · 38% · -151$ | **REVERT-TO-SKIP (OOS n=9 < 10)** | only 5 sessions after the ruling (window 10) · OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |
| `d_with_extension` | TAKE | S1 / T-494 — phase D with the extension · ruled 2026-09-27 | 305 · 41% · -2,417$ | 5 | 30 · 20% · -684$ | 60 · 33% · -794$ | **REVERT-TO-SKIP** | only 5 sessions after the ruling (window 10) · OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |
| `location` | SKIP | T-319b — responsive location rule (SKIP) · ruled 2026-09-11 | 218 · 46% · +649$ | 10 | 87 · 26% · -2,291$ | 66 · 38% · -506$ | **SKIP-HOLDS** | OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these |

לא קיימים בריצה הזו (הקונפיג ש-`t529b` ריץ קדם להם): `time_cutoff` (T-538 — no new entries from 20:00 IL (tree 3.3.0), 2026-10-05) — אין להם מספר OOS כאן; T-538 כבר נמדד על holdout נפרד ב-`harness_out/t538`.

## 3 · עלי-TAKE לא-נפסקים — הליכה מתרחבת (dev בלבד, 55 סשנים)

### הטובים (15 מתוך 31)

| נתיב-העץ | in-sample n · win · Σ$ | OOS n · win · Σ$ | ממוצע $/מועמד בחלון (חלונות) | holdout n · win · Σ$ | פסק-דין |
|---|---|---|---|---|---|
| `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(FORMING)/rel_bias=with` | 10 · 100% · +1,007$ | 19 · 68% · +826$ | +56.5$ (24) | 5 · 20% · -170$ | **KEEP** |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=Trend_Normal/kind=*(EDGE_FADE)/kind=EDGE_FADE` | 10 · 40% · +118$ | 49 · 61% · +701$ | +1.9$ (43) | 9 · 44% · +43$ | **KEEP** |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=EDGE_FADE` | 11 · 73% · +286$ | 46 · 48% · +252$ | -3.0$ (46) | 11 · 27% · -122$ | **KEEP** |
| `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(Trend_Normal)/rel_bias=with` | 11 · 82% · +459$ | 13 · 46% · +216$ | -4.9$ (26) | 4 · 25% · -14$ | **KEEP** |
| `opening_type=OPEN_DRIVE/phase=B/day_type=*(FORMING)/rel_bias=with` | 11 · 45% · +161$ | 11 · 55% · +159$ | +24.9$ (35) | 4 · 75% · +101$ | **KEEP** |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Trend_Normal/rel_bias=with` | 11 · 18% · -252$ | 5 · 80% · +137$ | +25.0$ (14) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=5 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=EDGE_FADE` | 10 · 50% · +48$ | 5 · 60% · +134$ | +27.4$ (25) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=5 < 10)** |
| `opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with` | 17 · 76% · +346$ | 1 · 100% · +114$ | +113.7$ (10) | 26 · 85% · +2,084$ | **REVERT-TO-SKIP (OOS n=1 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Trend_Normal/rel_bias=with` | 13 · 69% · +272$ | 5 · 80% · +47$ | -0.8$ (15) | 2 · 0% · -84$ | **REVERT-TO-SKIP (OOS n=5 < 10)** |
| `opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=*(none)/direction=SHORT/zone=near_vah` | 11 · 55% · +118$ | 8 · 62% · +10$ | +27.8$ (13) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=8 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(DOUBLE_BOTTOM_EE_LONG)/rel_bias=with` | 10 · 20% · -402$ | 0 · - · 0$ | - | 3 · 67% · +56$ | **REVERT-TO-SKIP (OOS n=0 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(GHOST)/rel_bias=*(none)/kind=BREAK` | 14 · 50% · +454$ | 0 · - · 0$ | - | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=0 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Neutral_Extreme/direction=LONG/zone=below_value` | 12 · 33% · -106$ | 0 · - · 0$ | - | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=0 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(DOUBLE_TOP_AA_SHORT)/rel_bias=with` | 12 · 50% · +237$ | 4 · 25% · -25$ | -40.6$ (6) | 1 · 0% · -103$ | **REVERT-TO-SKIP (OOS n=4 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Neutral_Extreme/rel_bias=with` | 18 · 56% · -219$ | 15 · 33% · -39$ | -2.6$ (6) | 0 · - · 0$ | **REVERT-TO-SKIP** |

### הגרועים (15)

| נתיב-העץ | in-sample n · win · Σ$ | OOS n · win · Σ$ | ממוצע $/מועמד בחלון (חלונות) | holdout n · win · Σ$ | פסק-דין |
|---|---|---|---|---|---|
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with` | 11 · 27% · -79$ | 103 · 37% · -1,676$ | -24.3$ (46) | 55 · 20% · -2,682$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with` | 10 · 100% · +1,090$ | 26 · 0% · -1,550$ | -59.2$ (27) | 10 · 0% · -610$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_DRIVE/phase=B/day_type=*(Trend_Normal)/rel_bias=with` | 11 · 9% · -567$ | 7 · 14% · -423$ | -49.2$ (11) | 2 · 100% · +142$ | **REVERT-TO-SKIP (OOS n=7 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Normal/structure=*(none)/direction=SHORT/zone=near_vah` | 12 · 17% · -207$ | 38 · 29% · -393$ | -11.6$ (38) | 9 · 56% · +140$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Normal/structure=*(none)/direction=LONG/zone=near_val` | 11 · 9% · -268$ | 21 · 14% · -373$ | -12.3$ (19) | 2 · 100% · +111$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=with` | 10 · 30% · -119$ | 54 · 41% · -312$ | -3.0$ (40) | 6 · 33% · -77$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(GHOST)/rel_bias=with` | 10 · 40% · -397$ | 4 · 0% · -209$ | -52.3$ (10) | 5 · 0% · -434$ | **REVERT-TO-SKIP (OOS n=4 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(INITIATIVE_LONG)/rel_bias=with` | 10 · 30% · -75$ | 3 · 0% · -202$ | -70.5$ (19) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=3 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(INITIATIVE_SHORT)/rel_bias=with` | 12 · 75% · +550$ | 6 · 17% · -119$ | -22.6$ (16) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=6 < 10)** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=*(none)/kind=BREAK` | 10 · 70% · +590$ | 19 · 47% · -105$ | +5.8$ (17) | 3 · 100% · +63$ | **REVERT-TO-SKIP** |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(REACTIVE_LONG)/rel_bias=with` | 11 · 55% · +20$ | 1 · 0% · -95$ | -95.1$ (4) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=1 < 10)** |
| `opening_type=OPEN_DRIVE/phase=C/day_type=Normal/structure=*(none)/direction=LONG/zone=near_val` | 18 · 61% · +67$ | 8 · 25% · -89$ | -18.0$ (11) | 4 · 0% · -98$ | **REVERT-TO-SKIP (OOS n=8 < 10)** |
| `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=with` | 12 · 50% · +19$ | 9 · 33% · -69$ | -7.8$ (6) | 8 · 38% · -18$ | **REVERT-TO-SKIP (OOS n=9 < 10)** |
| `opening_type=OPEN_DRIVE/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with` | 14 · 36% · +236$ | 2 · 0% · -65$ | -32.6$ (8) | 2 · 100% · +220$ | **REVERT-TO-SKIP (OOS n=2 < 10)** |
| `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Neutral_Extreme/direction=SHORT/zone=above_value` | 10 · 20% · -215$ | 9 · 44% · -62$ | -6.9$ (10) | 0 · - · 0$ | **REVERT-TO-SKIP (OOS n=9 < 10)** |

**לא נמדדו** (83 עלי-TAKE עם פחות מ-10 מועמדים לפני ה-holdout; מוצגים 26 עם ≥5 מועמדים סה״כ):

- `opening_type=OPEN_DRIVE/phase=D/day_type=Trend_Normal/rel_bias=with` — סה״כ 15 · 7% · -671$ · holdout 9 · 0% · -457$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=*(none)/direction=SHORT/zone=near_vah` — סה״כ 13 · 31% · -133$ · holdout 4 · 25% · -52$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(DOUBLE_TOP_AA_SHORT)/rel_bias=with` — סה״כ 12 · 33% · -345$ · holdout 4 · 0% · -285$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Trend_Normal/rel_bias=*(none)/kind=BREAK` — סה״כ 10 · 30% · +28$ · holdout 3 · 33% · -21$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(REACTIVE_SHORT)/rel_bias=with` — סה״כ 10 · 40% · -122$ · holdout 2 · 0% · -149$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Normal/structure=*(none)/direction=LONG/zone=near_val` — סה״כ 9 · 22% · -230$ · holdout 2 · 0% · -71$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Neutral_Center/direction=LONG/zone=near_val` — סה״כ 9 · 22% · -197$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Trend_DD/rel_bias=with` — סה״כ 9 · 100% · +204$ · holdout 0 · - · 0$
- `opening_type=OPEN_DRIVE/phase=D/day_type=Neutral_Extreme/rel_bias=with` — סה״כ 9 · 33% · -82$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Normal/structure=*(none)/direction=SHORT/zone=above_value` — סה״כ 8 · 50% · +12$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Neutral_Extreme/direction=LONG/zone=near_val` — סה״כ 8 · 12% · -310$ · holdout 0 · - · 0$
- `opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Trend_DD/rel_bias=with` — סה״כ 7 · 100% · +459$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(DOUBLE_BOTTOM_EE_LONG)/rel_bias=*(none)/kind=BREAK` — סה״כ 7 · 0% · -582$ · holdout 1 · 0% · -115$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CONFLUENCE_RI_ZLR)/rel_bias=with` — סה״כ 7 · 43% · -1$ · holdout 1 · 0% · -38$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(INITIATIVE_SHORT)/rel_bias=*(none)/kind=BREAK` — סה״כ 7 · 86% · +611$ · holdout 0 · - · 0$
- `opening_type=OPEN_DRIVE/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=with` — סה״כ 7 · 29% · -35$ · holdout 0 · - · 0$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(INITIATIVE_SHORT)/rel_bias=with` — סה״כ 7 · 29% · -149$ · holdout 1 · 0% · -58$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=*(none)/kind=BREAK` — סה״כ 7 · 100% · +96$ · holdout 2 · 100% · +41$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(GB100)/rel_bias=with` — סה״כ 6 · 50% · -32$ · holdout 1 · 0% · -78$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(GHOST)/rel_bias=with` — סה״כ 6 · 33% · -69$ · holdout 2 · 0% · -144$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Neutral_Center/direction=SHORT/zone=near_vah` — סה״כ 6 · 33% · -90$ · holdout 6 · 33% · -90$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Trend_Normal/rel_bias=with` — סה״כ 5 · 60% · +90$ · holdout 1 · 100% · +44$
- `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(GB100)/rel_bias=with` — סה״כ 5 · 40% · -37$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(DOUBLE_TOP_AA_SHORT)/rel_bias=*(none)/kind=BREAK` — סה״כ 5 · 60% · +206$ · holdout 0 · - · 0$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(VA_FADE_LONG)/rel_bias=with` — סה״כ 5 · 40% · -23$ · holdout 1 · 0% · -23$
- `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_SHORT)/rel_bias=with` — סה״כ 5 · 80% · +123$ · holdout 0 · - · 0$

## 4 · עלי-SKIP — מה היה עולה/חוסך (אינפורמטיבי; הקפאת-ענפים: אין הוספת עלה)

| ענף | id | in-sample n · Σ$ | OOS n · win · Σ$ אילו נלקחו | holdout n · Σ$ | פסק-דין |
|---|---|---|---|---|---|
| `opening_type=OPEN_DRIVE/phase=D/day_type=Variation/rel_bias=*(against)` | path | 13 · 100% · +799$ | 32 · 75% · +1,236$ | 9 · 0% · -491$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Variation/rel_bias=*(none)` | path | 13 · 31% · -131$ | 65 · 49% · +725$ | 17 · 35% · -363$ | SKIP-COSTS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(Trend_Normal)/rel_bias=against/edge=*(none)` | path | 10 · 10% · -507$ | 10 · 70% · +322$ | 8 · 25% · -466$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=*(none)/kind=*(EDGE_FADE)/edge=*(none)` | path | 11 · 45% · +69$ | 37 · 62% · +278$ | 3 · 33% · -53$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(GHOST)/rel_bias=against/edge=*(none)` | path | 11 · 18% · -410$ | 13 · 38% · +69$ | 1 · 100% · +132$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(BREAK)/edge=*(none)` | path | 11 · 73% · +546$ | 7 · 57% · +69$ | 0 · - · 0$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(INITIATIVE_SHORT)/rel_bias=against/edge=*(none)` | path | 10 · 60% · +80$ | 5 · 20% · +45$ | 2 · 100% · +265$ | SKIP-COSTS |
| `opening_type=OPEN_DRIVE/phase=B/day_type=*(FORMING)/rel_bias=against/edge=*(none)` | path | 10 · 70% · +565$ | 16 · 50% · +5$ | 0 · - · 0$ | SKIP-COSTS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Trend_Normal/rel_bias=against/edge=*(none)` | path | 10 · 20% · -215$ | 0 · - · 0$ | 0 · - · 0$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(REACTIVE_SHORT)/rel_bias=against/edge=*(none)` | path | 11 · 73% · +400$ | 0 · - · 0$ | 1 · 100% · +159$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Normal/structure=*(none)` | path | 18 · 50% · -146$ | 0 · - · 0$ | 0 · - · 0$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Neutral_Extreme/rel_bias=against/edge=*(none)` | path | 16 · 56% · +220$ | 0 · - · 0$ | 0 · - · 0$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=*(PULLBACK)/edge=*(none)` | path | 10 · 30% · -203$ | 5 · 40% · -11$ | 3 · 33% · -30$ | SKIP-HOLDS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Variation/rel_bias=*(none)` | path | 11 · 55% · -162$ | 9 · 33% · -20$ | 4 · 100% · +119$ | SKIP-HOLDS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=against/edge=*(none)` | path | 10 · 0% · -262$ | 15 · 33% · -108$ | 20 · 30% · -83$ | SKIP-HOLDS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=against/edge=*(none)` | path | 15 · 67% · +165$ | 3 · 0% · -145$ | 19 · 58% · +308$ | SKIP-HOLDS |
| `opening_type=*(UNKNOWN)/phase=A/day_type=*(FORMING)` | path | 11 · 82% · +333$ | 155 · 45% · -288$ | 30 · 43% · +46$ | SKIP-HOLDS |
| `opening_type=OPEN_DRIVE/phase=D/day_type=Normal/structure=*(none)` | path | 10 · 20% · -375$ | 10 · 20% · -335$ | 0 · - · 0$ | SKIP-HOLDS |
| `opening_type=OPEN_DRIVE/phase=B/day_type=*(Trend_Normal)/rel_bias=against/edge=*(none)` | path | 11 · 55% · +208$ | 12 · 33% · -381$ | 1 · 0% · -31$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=*(BREAK)/edge=*(none)` | path | 10 · 50% · +34$ | 24 · 25% · -444$ | 3 · 67% · +101$ | SKIP-HOLDS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(FORMING)/rel_bias=against/edge=*(none)` | path | 11 · 36% · -214$ | 14 · 21% · -455$ | 3 · 0% · -229$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=against/edge=*(none)` | path | 10 · 10% · -75$ | 71 · 34% · -641$ | 10 · 40% · -38$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=*(Neutral_Center)` | path | 10 · 10% · -658$ | 38 · 24% · -680$ | 25 · 28% · -599$ | SKIP-HOLDS |
| `opening_type=OPEN_REJECTION_REVERSE/phase=D/day_type=Variation/rel_bias=*(against)` | path | 19 · 16% · -413$ | 37 · 27% · -975$ | 25 · 64% · +109$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=against/edge=*(none)` | path | 11 · 45% · +65$ | 59 · 34% · -1,297$ | 4 · 100% · +393$ | SKIP-HOLDS |
| `location` | ruled | 218 · 46% · +649$ | 87 · 26% · -2,291$ | 66 · 38% · -506$ | SKIP-HOLDS |
| `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Variation/rel_bias=*(against)` | path | 14 · 57% · +216$ | 140 · 26% · -2,296$ | 50 · 44% · +542$ | SKIP-HOLDS |

## 5 · HOLDOUT — 10 הסשנים האחרונים (2026-09-21 → 2026-10-02), לא שימשו לשום הכרעה

| | TAKE (מה שהעץ לקח) | SKIP (מה שהעץ דחה) |
|---|---|---|
| dev (55 סשנים) | 1875 · 43% · +636$ | 1560 · 41% · -6,513$ |
| **holdout (10)** | **400 · 39% · -3,212$** | **370 · 43% · +53$** |

הפרדה בריאה = TAKE חיובי ו-SKIP שלילי; היפוך-הסימן בשורת-ה-holdout הוא בדיוק החתימה שסעיף 1(ב) של ביקורת-השיטה מצא על 6 הסשנים האחרונים. ⚠️ הפסיקות של 25.09/27.09/03.10 נמדדו על **כל** הסשנים כולל ה-holdout — עבור הענפים הנפסקים ה-holdout אינו נקי; רק עלי-ה-path (סעיף 3) נבדקו נגדו בלי שראו אותו.

## 6 · הקשר בלי תווית — (מבנה-IB, שעה, סוג-כניסה), כל המועמדים, n ≥ 10

| structure | hour | kind | n | win% | Σ$ אילו נלקחו | מהם TAKE | holdout n · Σ$ |
|---|---|---|---|---|---|---|---|
| none | 20h+ | BREAK | 103 | 61% | +2,081$ | 36 | 22 · +1,630$ |
| forming | 16h | EDGE_FADE | 212 | 53% | +1,876$ | 72 | 32 · -255$ |
| forming | 17h | BREAK | 145 | 52% | +1,316$ | 107 | 26 · +48$ |
| forming | 17h | EDGE_FADE | 144 | 51% | +1,078$ | 110 | 16 · +0$ |
| forming | 16h | WITH_DRIVE | 30 | 60% | +944$ | 26 | 3 · +279$ |
| none | 18-19h | BREAK | 120 | 48% | +824$ | 37 | 28 · +617$ |
| down | 18-19h | EDGE_FADE | 236 | 45% | +730$ | 116 | 61 · +782$ |
| none | 18-19h | EDGE_FADE | 167 | 40% | +522$ | 126 | 29 · +171$ |
| forming | 16h | REVERSAL | 82 | 44% | +406$ | 44 | 11 · -176$ |
| down | 18-19h | REVERSAL | 25 | 48% | +250$ | 24 | 6 · +126$ |
| forming | 17h | REVERSAL | 32 | 44% | +222$ | 21 | 6 · -277$ |
| up | 18-19h | REVERSAL | 27 | 37% | +214$ | 27 | 2 · -40$ |
| none | 17h | BREAK | 111 | 46% | +210$ | 23 | 32 · -9$ |
| up | 18-19h | BREAK | 210 | 42% | +85$ | 148 | 19 · +1,399$ |
| down | 17h | BREAK | 22 | 45% | +80$ | 20 | 4 · -276$ |
| none | 17h | REVERSAL | 14 | 43% | +77$ | 5 | 6 · -50$ |
| up | 17h | EDGE_FADE | 14 | 36% | -73$ | 9 | 0 · +0$ |
| forming | 16h | PULLBACK | 23 | 39% | -111$ | 4 | 4 · -107$ |
| down | 20h+ | REVERSAL | 33 | 45% | -192$ | 22 | 6 · +25$ |
| up | 20h+ | REVERSAL | 28 | 39% | -378$ | 17 | 6 · -114$ |
| down | 17h | EDGE_FADE | 17 | 6% | -428$ | 6 | 2 · -56$ |
| none | 20h+ | EDGE_FADE | 80 | 31% | -499$ | 26 | 10 · +87$ |
| up | 18-19h | EDGE_FADE | 205 | 40% | -527$ | 145 | 12 · +150$ |
| up | 17h | BREAK | 13 | 31% | -728$ | 11 | 0 · +0$ |
| forming | 16h | BREAK | 128 | 38% | -797$ | 10 | 16 · +38$ |
| none | 17h | EDGE_FADE | 113 | 36% | -864$ | 70 | 21 · +49$ |
| up | 20h+ | EDGE_FADE | 227 | 40% | -1,117$ | 122 | 32 · -474$ |
| two_sided | 20h+ | EDGE_FADE | 106 | 30% | -1,315$ | 57 | 17 · -587$ |
| two_sided | 20h+ | BREAK | 102 | 33% | -1,504$ | 30 | 29 · -892$ |
| up | 20h+ | BREAK | 319 | 43% | -1,742$ | 184 | 43 · -550$ |
| down | 20h+ | EDGE_FADE | 345 | 37% | -2,028$ | 170 | 92 · -699$ |
| down | 20h+ | BREAK | 446 | 41% | -3,432$ | 222 | 96 · -1,435$ |
| down | 18-19h | BREAK | 269 | 34% | -3,968$ | 187 | 69 · -2,326$ |

השדות נקראו מ-`tree_v3.vec` (`structure`, `hour` = שעת-IL של המועמד, `kind`) — כפי שהגייטוויי כתב אותם; לא חושב דבר מחדש. זו טבלת-הייחוס לווריאנט-ההקשר של ליל ד׳ (walk-forward, לא Σ in-sample).

## 7 · מה זה אומר ל-23:40

- **המספר:** holdout (10 סשנים) TAKE 400 · 39% · -3,212$ מול SKIP 370 · 43% · +53$ — העץ בחר הפוך. dev: TAKE 1875 · 43% · +636$ מול SKIP 1560 · 41% · -6,513$.
- **רשימת-הגיזום (דוקטרינה שלב 6) — 8 עלי-TAKE עם OOS ≤ 0 ו-n ≥ 10** (ראיה שלילית, לא חוסר-ראיה). המלצה בלבד; `config/decision_tree_v3.yaml` לא נערך הלילה:
  - `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with` — OOS 103 · 37% · -1,676$ · holdout 55 · 20% · -2,682$
  - `opening_type=OPEN_REJECTION_REVERSE/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with` — OOS 26 · 0% · -1,550$ · holdout 10 · 0% · -610$
  - `d_with_extension` — OOS 30 · 20% · -684$ · holdout 60 · 33% · -794$ · S1 / T-494 — phase D with the extension · ruled 2026-09-27
  - `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Normal/structure=*(none)/direction=SHORT/zone=near_vah` — OOS 38 · 29% · -393$ · holdout 9 · 56% · +140$
  - `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Normal/structure=*(none)/direction=LONG/zone=near_val` — OOS 21 · 14% · -373$ · holdout 2 · 100% · +111$
  - `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(CEILING_FLIP_TOUCH2)/rel_bias=with` — OOS 54 · 41% · -312$ · holdout 6 · 33% · -77$
  - `opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=*(none)/kind=BREAK` — OOS 19 · 47% · -105$ · holdout 3 · 100% · +63$
  - `opening_type=OPEN_AUCTION_IN/phase=D/day_type=Neutral_Extreme/rel_bias=with` — OOS 15 · 33% · -39$ · holdout 0 · - · 0$
- **דקים (REVERT מכוח הכלל, OOS n < 10):** 23 — אין להם ראיה לכאן או לכאן; ענף ללא OOS (T-529: 0 סשנים אחרי 03.10) הוא "עדיין בלי מספר", לא "שלילי".
- **KEEP:** 6 — `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(FORMING)/rel_bias=with` (OOS 19 · 68% · +826$), `failed_extension` (OOS 25 · 68% · +707$), `opening_type=OPEN_AUCTION_IN/phase=B/day_type=Trend_Normal/kind=*(EDGE_FADE)/kind=EDGE_FADE` (OOS 49 · 61% · +701$), `opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=EDGE_FADE` (OOS 46 · 48% · +252$), `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(Trend_Normal)/rel_bias=with` (OOS 13 · 46% · +216$), `opening_type=OPEN_DRIVE/phase=B/day_type=*(FORMING)/rel_bias=with` (OOS 11 · 55% · +159$).
- אין עלה חדש הלילה. שלב C/D בלי תווית (סעיף 6) נמדד ביום ד׳ מול `t529b` באותו לילה, walk-forward.
- **הסתייגויות:** רמת-מועמד ≠ יום-שלם (סלוט יחיד, שערים אחרי העץ); 5 סשנים אחרי פסיקות 25–27.09 הם N קטן; משטר יוני–אוקטובר (שורטים) עלול להתהפך; 192 מסלולי-לייב מוזרקים נספרים כמועמדים (כמו ב-`tree_measure`).
