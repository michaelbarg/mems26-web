# יומן הימים — T-646 משימה 1 (81 ימי ריפליי, הקוד של 23.10)

אמת: פתיחה = v2 (מה שהעץ ראה אחרי הנעילה); סוג-יום = ייחוס-דלתון חוקי (IB, הרחבה שהתקבלה = 2 סגירות, מיקום-הסגירה). ריפליי = הרנס T-640 (live, ‎.env של 23.10); $ = של ההרנס בגודל החוזים האמיתי; נק׳ = לחוזה אחד.

**סה״כ 77 ימים מלאים:** ריפליי -533$ · ימים חיוביים 35 · שליליים 40 · בלי עסקה 2 · רגליים שפוספסו Σ 10083 נק׳ · נתפסו Σ 2934 נק׳.

## לפי תא: סוג-פתיחה (v2) × סוג-יום (ייחוס)

| פתיחה | סוג-יום | ימים | ריפליי $ | ממוצע ליום | +/− | עסקאות | פוספס נק׳ | נתפס נק׳ | 'היה-יורה' נק׳ | חסימה מובילה |
|---|---|---|---|---|---|---|---|---|---|---|
| Test-Drive | וריאציה | 10 | -1942 | -194 | 2/8 | 35 | 1733 | 194 | +5 | tree:location |
| Drive | וריאציה | 16 | -785 | -49 | 7/8 | 39 | 1937 | 491 | +100 | tree:bias |
| Auction-Out | וריאציה | 12 | -718 | -60 | 4/8 | 45 | 1496 | 668 | -145 | tree:bias |
| Test-Drive | ניטרלי | 1 | -659 | -659 | 0/1 | 4 | 178 | 16 | -78 | tree:location |
| ORR | וריאציה | 3 | -404 | -135 | 1/2 | 10 | 437 | 103 | -66 | tree:bias |
| Drive | נורמלי | 1 | -269 | -269 | 0/1 | 3 | 103 | 12 | -6 | tree:location |
| Test-Drive | נורמלי | 1 | -190 | -190 | 0/1 | 2 | 90 | 21 | +0 | tree:location |
| Auction-Out | מגמה | 2 | -99 | -49 | 1/1 | 5 | 234 | 78 | -27 | mid_value_no_edge_test |
| Drive | מגמה | 1 | -75 | -75 | 0/1 | 4 | 21 | 102 | -30 | tree:time_cutoff |
| Auction-In | ללא-מגמה | 1 | +78 | +78 | 1/0 | 3 | 57 | 58 | +9 | tree:time_cutoff |
| Drive | ללא-מגמה | 3 | +181 | +60 | 2/0 | 4 | 675 | 35 | -41 | tree:location |
| Auction-In | מגמה | 3 | +222 | +74 | 2/1 | 11 | 268 | 168 | +168 | tree:location |
| Auction-In | וריאציה | 13 | +255 | +20 | 5/8 | 33 | 1464 | 442 | -71 | tree:stand_down |
| ORR | ללא-מגמה | 1 | +406 | +406 | 1/0 | 2 | 133 | 81 | +62 | tree:location |
| Test-Drive | ללא-מגמה | 1 | +430 | +430 | 1/0 | 1 | 250 | 36 | +1 | tree:location |
| Test-Drive | מגמה | 1 | +441 | +441 | 1/0 | 5 | 199 | 64 | +5 | tree:stand_down |
| Auction-In | ניטרלי | 1 | +718 | +718 | 1/0 | 1 | 106 | 194 | +28 | tree:time_cutoff |
| Drive | ניטרלי | 4 | +865 | +216 | 4/0 | 7 | 466 | 52 | -125 | tree:bias |
| Auction-Out | ניטרלי | 2 | +1012 | +506 | 2/0 | 4 | 237 | 120 | -45 | tree:bias |

## יום אחר יום

| תאריך | פתיחה (v2) | סוג-יום (ייחוס) | S1 בסוף-יום | תווית נכונה מ- (דק׳) | ריפליי: עסקאות · $ | לייב/דמו $ | פוספס (נק׳) | הפספוס הגדול | חסימה מובילה |
|---|---|---|---|---|---|---|---|---|---|
| 2026-06-15 | Drive↑ | Variation | Variation | 25 | 3 · +22 | — | 120 | ↑ 17:35–18:30 25 (אף מועמד) | tree:bias ×15 |
| 2026-06-16 | Auction-In | Trend_Normal | Trend_DD | 250 | 4 · +298 | — | 79 | ↑ 18:45–19:10 24 (אף מועמד) | tree:bias ×10 |
| 2026-06-22 | Drive↑ | Variation | Variation | 25 | 0 · +0 | — | 227 | ↓ 17:10–17:55 72 (CEILING_FLIP/tree:bias, DOUBLE_TB/entry_location_quality) | tree:time_cutoff ×13 |
| 2026-06-23 | Test-Drive↑ | Nontrend | Normal ✗ | — | 1 · +430 | — | 250 | ↑ 16:30–17:20 76 (DALTON_EDGE/tree:stand_down, CEILING_FLIP/tree:stand_down, FAILED_BREAK/entry_location_quality) | tree:location ×11 |
| 2026-06-24 | Auction-In | Neutral_Center | Neutral_Extreme | 240 | 1 · +718 | — | 106 | ↓ 21:25–21:50 35 (אף מועמד) | tree:time_cutoff ×14 |
| 2026-06-25 | Drive↓ | Nontrend | Normal ✗ | — | 0 · +0 | — | 452 | ↓ 16:30–16:55 100 (CEILING_FLIP/tree:stand_down, FAILED_BREAK/tree:stand_down) | tree:location ×18 |
| 2026-06-29 | Test-Drive↓ | Variation | Variation | 25 | 2 · -212 | — | 237 | ↓ 16:50–17:15 81 (DALTON_EDGE/tree:bias, FAILED_BREAK/tree:bias, CEILING_FLIP/tree:bias) | tree:location ×9 |
| 2026-06-30 | Drive↑ | Variation | Variation | 25 | 3 · -256 | — | 118 | ↑ 17:55–20:00 43 (ZLR/structural_targets_wrong_side, ZLR/wait_for_test, REACTIVE/entry_location_quality) | tree:bias ×13 |
| 2026-07-01 | Test-Drive↑ | Variation | Variation | 25 | 3 · -325 | — | 138 | ↑ 16:35–17:25 48 (CEILING_FLIP/tree:stand_down, ZLR/tree:bias, ZLR/tree:kind) | tree:stand_down ×15 |
| 2026-07-02 | Drive↑ | Variation | Variation | 25 | 3 · -550 | — | 190 | ↑ 16:30–16:50 42 (CEILING_FLIP/tree:stand_down, ZLR/tree:stand_down, FAILED_BREAK/tree:stand_down) | entry_location_quality ×13 |
| 2026-07-06 | Auction-Out | Variation | Variation | 100 | 6 · -569 | — | 139 | ↑ 17:00–17:30 25 (ZLR/tree:location, GB100/tree:location) | wait_for_test ×10 |
| 2026-07-07 | Drive↓ | Variation | Variation | 25 | 3 · +470 | +121 | 133 | ↑ 18:40–20:05 40 (HTLB/tree:bias, CEILING_FLIP/wait_for_test, CEILING_FLIP/mid_value_no_edge_test) | mid_value_no_edge_test ×20 |
| 2026-07-08 | Drive↑ | Neutral_Extreme | Neutral_Center | 245 | 4 · +45 | +22 | 191 | ↑ 18:50–19:30 39 (REACTIVE/tree:bias, REACTIVE/tree:kind, DOUBLE_TB/mid_value_no_edge_test) | tree:bias ×21 |
| 2026-07-09 | Test-Drive↑ | Variation | Variation | 25 | 4 · -275 | +118 | 122 | ↑ 17:50–20:45 48 (ZLR/tree:location, ZLR/entry_location_quality, REACTIVE/entry_location_quality) | entry_location_quality ×14 |
| 2026-07-13 | Auction-In | Variation | Variation | 25 | 3 · -114 | +92 | 143 | ↓ 18:00–19:35 42 (REACTIVE/tree:location, ZLR/tree:location) | tree:location ×16 |
| 2026-07-14 | Auction-In | Variation | Variation | 25 | 3 · +179 | -90 | 84 | ↓ 16:45–17:15 32 (DALTON_EDGE/tree:bias, CEILING_FLIP/tree:bias, ZLR/tree:bias) | tree:bias ×13 |
| 2026-07-15 (חלקי) | Drive↓ | Variation | Variation | — | 1 · +548 | -161 | 87 | ↓ 17:30–18:40 37 (ZLR/tree:location, GB100/tree:location, REACTIVE/tree:location) | mid_value_no_edge_test ×15 |
| 2026-07-16 (חלקי) | Auction-In | Variation | Trend_Normal | — | 1 · +615 | — | 74 | ↓ 17:50–18:25 27 (GHOST/tree:stand_down, CEILING_FLIP/tree:stand_down) | wait_for_test ×12 |
| 2026-07-17 | Auction-Out | Neutral_Center | Neutral_Center | 240 | 2 · +459 | -78 | 123 | ↑ 17:35–18:00 27 (אף מועמד) | tree:location ×8 |
| 2026-07-20 | Test-Drive↓ | Variation | Variation | 175 | 3 · -26 | -75 | 209 | ↓ 20:35–21:15 29 (INITIATIVE/wait_for_test, DOUBLE_TB/wait_for_test, INITIATIVE/entry_location_quality) | tree:location ×11 |
| 2026-07-21 (חלקי) | Auction-In | Variation | Variation | — | 4 · -266 | -214 | 54 | ↑ 17:00–17:25 22 (CEILING_FLIP/tree:location) | tree:stand_down ×8 |
| 2026-07-23 | Auction-Out | Variation | Variation | 25 | 3 · -268 | -222 | 191 | ↑ 21:45–22:00 38 (אף מועמד) | wait_for_test ×14 |
| 2026-07-27 | Auction-Out | Variation | Variation | 25 | 6 · -87 | -120 | 227 | ↓ 16:30–17:40 88 (CEILING_FLIP/tree:stand_down, REACTIVE/entry_location_quality, FAILED_BREAK/entry_location_quality) | tree:bias ×10 |
| 2026-07-30 | ORR↑ | Variation | Neutral_Extreme ✗ | — | 4 · -479 | +69 | 175 | ↑ 19:40–22:15 48 (GB100/structural_targets_wrong_side, FLAG/wait_for_test) | tree:location ×8 |
| 2026-07-31 | Test-Drive↓ | Variation | Variation | 25 | 3 · -388 | -154 | 230 | ↑ 18:40–20:35 56 (אף מועמד) | tree:stand_down ×16 |
| 2026-08-03 | Drive↑ | Variation | Variation | 25 | 4 · +305 | +168 | 30 | ↑ 16:40–17:00 30 (ZLR/entry_location_quality) | wait_for_test ×12 |
| 2026-08-05 | Auction-Out | Trend_Normal | Variation ✗ | 130 | 3 · +276 | +209 | 152 | ↓ 21:05–22:55 29 (GHOST/mid_value_no_edge_test, GHOST/tree:time_cutoff) | tree:stand_down ×12 |
| 2026-08-06 | Test-Drive↑ | Variation | Variation | 120 | 2 · +65 | -101 | 219 | ↓ 18:00–18:35 30 (CEILING_FLIP/tree:location) | wait_for_test ×9 |
| 2026-08-07 | Auction-In | Variation | Variation | 25 | 3 · +523 | -86 | 87 | ↑ 21:40–22:15 26 (אף מועמד) | tree:time_cutoff ×11 |
| 2026-08-10 | Auction-In | Variation | Neutral_Center ✗ | 85 | 2 · -150 | -85 | 98 | ↓ 19:00–19:30 28 (CEILING_FLIP/tree:bias, REACTIVE/tree:bias) | mid_value_no_edge_test ×8 |
| 2026-08-11 | Drive↓ | Variation | Variation | 25 | 2 · -294 | — | 78 | ↓ 17:50–18:15 19 (CEILING_FLIP/mid_value_no_edge_test) | tree:bias ×7 |
| 2026-08-12 | Drive↓ | Variation | Variation | 25 | 1 · +175 | +74 | 80 | ↓ 16:30–16:45 26 (CEILING_FLIP/tree:stand_down, GB100/tree:stand_down) | tree:bias ×26 |
| 2026-08-13 | Auction-In | Nontrend | Normal ✗ | — | 3 · +78 | +69 | 57 | ↑ 16:40–17:35 38 (FAILED_BREAK/tree:stand_down, INITIATIVE/tree:kind, SCALE_IN/tree:kind) | tree:time_cutoff ×7 |
| 2026-08-14 | Auction-In | Variation | Variation | 25 | 1 · +304 | -124 | 28 | ↓ 17:35–18:25 16 (TREND_STEP/tree:stand_down, ZLR/structural_targets_wrong_side) | tree:stand_down ×11 |
| 2026-08-17 | Auction-In | Trend_Normal | Trend_DD | 45 | 4 · +161 | +109 | 13 | ↓ 16:45–17:00 13 (אף מועמד) | tree:location ×15 |
| 2026-08-18 | Auction-Out | Variation | Variation | 25 | 3 · +238 | — | 26 | ↓ 16:40–16:55 14 (CEILING_FLIP/entry_location_quality, ZLR/tree:kind) | mid_value_no_edge_test ×13 |
| 2026-08-19 | Auction-Out | Variation | Variation | 25 | 3 · +284 | -4 | 108 | ↓ 16:30–16:50 26 (CEILING_FLIP/tree:stand_down, FAILED_BREAK/tree:stand_down, GB100/tree:stand_down) | tree:bias ×20 |
| 2026-08-20 | Drive↑ | Trend_Normal | Neutral_Extreme ✗ | 50 | 4 · -75 | +11 | 21 | ↓ 16:40–17:05 21 (אף מועמד) | tree:time_cutoff ×11 |
| 2026-08-21 | Drive↓ | Variation | Variation | 25 | 2 · +109 | -45 | 67 | ↑ 18:25–18:40 20 (ZLR/entry_not_confirmed, GHOST/structural_targets_wrong_side) | tree:time_cutoff ×21 |
| 2026-08-24 | Drive↓ | Nontrend | Normal ✗ | — | 2 · +147 | — | 137 | ↓ 16:30–16:45 28 (CEILING_FLIP/tree:stand_down) | tree:location ×10 |
| 2026-08-25 | Auction-Out | Variation | Variation | 25 | 3 · -220 | — | 107 | ↓ 16:45–17:30 38 (CEILING_FLIP/entry_not_confirmed, GHOST/tree:kind) | tree:bias ×18 |
| 2026-08-26 | Drive↑ | Neutral_Center | Neutral_Extreme | 345 | 1 · +89 | +25 | 122 | ↓ 17:00–17:25 22 (CEILING_FLIP/tree:bias, FAILED_BREAK/tree:bias, VA_FADE/tree:bias) | tree:time_cutoff ×14 |
| 2026-08-27 | Auction-Out | Variation | Variation | 90 | 7 · -139 | +122 | 88 | ↑ 21:55–22:55 22 (INITIATIVE/tree:time_cutoff) | tree:stand_down ×17 |
| 2026-08-28 | Test-Drive↓ | Neutral_Center | Neutral_Extreme | 185 | 4 · -659 | +390 | 178 | ↓ 18:25–19:00 48 (VA_FADE/tree:kind, CEILING_FLIP/wait_for_test) | tree:location ×23 |
| 2026-08-31 | Drive↓ | Nontrend | Normal ✗ | — | 2 · +34 | -65 | 86 | ↑ 21:40–22:40 22 (CEILING_FLIP/tree:stand_down) | tree:location ×15 |
| 2026-09-01 | Auction-Out | Neutral_Center | Neutral_Center | 310 | 2 · +554 | -230 | 114 | ↑ 16:55–17:35 32 (אף מועמד) | tree:bias ×13 |
| 2026-09-02 | Auction-In | Variation | Variation | 80 | 2 · -194 | +31 | 111 | ↑ 16:50–17:25 36 (ZLR/tree:kind, CEILING_FLIP/rr_hard_floor, HTLB/tree:location) | mid_value_no_edge_test ×20 |
| 2026-09-03 | Auction-Out | Trend_Normal | Trend_Normal | 50 | 2 · -375 | -284 | 82 | ↓ 16:50–17:10 26 (CEILING_FLIP/tree:bias, DALTON_EDGE/tree:bias) | mid_value_no_edge_test ×17 |
| 2026-09-04 | ORR↓ | Variation | Variation | 90 | 4 · -34 | -116 | 57 | ↓ 17:15–18:00 27 (אף מועמד) | tree:stand_down ×11 |
| 2026-09-08 | Test-Drive↓ | Normal | Normal | 60 | 2 · -190 | -181 | 90 | ↓ 20:35–21:45 23 (אף מועמד) | tree:location ×21 |
| 2026-09-09 | Auction-Out | Variation | Variation | 25 | 1 · +255 | -178 | 78 | ↓ 17:25–18:10 27 (CEILING_FLIP/tree:kind, CEILING_FLIP/rr_entry_gate, ZLR/tree:location) | tree:bias ×11 |
| 2026-09-10 (חלקי) | ORR↓ | Nontrend | Normal | — | 2 · -244 | -34 | 152 | ↑ 17:05–17:20 34 (CEILING_FLIP/tree:bias) | tree:location ×17 |
| 2026-09-11 | Auction-Out | Variation | Variation | 25 | 2 · -29 | +49 | 48 | ↓ 16:55–17:15 18 (FAILED_BREAK/mid_value_no_edge_test, CEILING_FLIP/mid_value_no_edge_test) | tree:bias ×18 |
| 2026-09-14 | Test-Drive↑ | Variation | Neutral_Center ✗ | — | 4 · +344 | -138 | 159 | ↑ 18:15–18:40 38 (אף מועמד) | tree:location ×24 |
| 2026-09-15 | Drive↓ | Variation | Variation | 25 | 3 · -2 | -141 | 57 | ↑ 19:05–19:55 15 (CEILING_FLIP/tree:bias, ZLR/mid_value_no_edge_test, REACTIVE/tree:bias) | mid_value_no_edge_test ×18 |
| 2026-09-18 | Drive↓ | Normal | Normal | 25 | 3 · -269 | +8 | 103 | ↑ 19:25–21:50 41 (CEILING_FLIP/tree:bias, REACTIVE/tree:bias, ZLR/tree:bias) | tree:location ×16 |
| 2026-09-21 | Drive↑ | Variation | Trend_Normal ✗ | 25 | 3 · +24 | +91 | 81 | ↑ 17:05–17:35 26 (GHOST/entry_not_confirmed) | wait_for_test ×13 |
| 2026-09-22 | Auction-In | Variation | Variation | 25 | 3 · +56 | +14 | 61 | ↓ 17:10–17:45 19 (CEILING_FLIP/mid_value_no_edge_test, ZLR/tree:kind) | tree:stand_down ×15 |
| 2026-09-23 | Drive↓ | Variation | Variation | 25 | 2 · -112 | -19 | 158 | ↓ 16:30–17:25 48 (CEILING_FLIP/tree:stand_down, OPENING_DRIVE/opening_half_range) | tree:stand_down ×12 |
| 2026-09-24 | Drive↑ | Neutral_Center | Neutral_Center | 180 | 1 · +353 | -39 | 114 | ↓ 17:25–18:10 32 (CEILING_FLIP/tree:bias, CEILING_FLIP/tree:location) | mid_value_no_edge_test ×10 |
| 2026-09-25 | Test-Drive↓ | Variation | Variation | 25 | 5 · -398 | +72 | 148 | ↑ 18:45–19:30 41 (CEILING_FLIP/tree:location, CEILING_FLIP/rr_entry_gate, ZLR/structural_targets_wrong_side) | tree:stand_down ×16 |
| 2026-09-28 | Auction-In | Variation | Neutral_Center ✗ | 25 | 1 · -138 | -95 | 189 | ↑ 18:40–19:25 50 (CEILING_FLIP/tree:kind, CEILING_FLIP/tree:bias, REACTIVE/tree:kind) | tree:location ×14 |
| 2026-09-29 | Drive↓ | Variation | Variation | 25 | 2 · -181 | -2 | 99 | ↓ 17:55–18:25 30 (ZLR/tree:location, CEILING_FLIP/mid_value_no_edge_test, DOUBLE_TB/tree:location) | tree:time_cutoff ×15 |
| 2026-09-30 | Auction-In | Trend_Normal | Neutral_Extreme ✗ | 45 | 3 · -236 | -39 | 176 | ↓ 22:10–22:55 46 (ZLR/tree:time_cutoff, REACTIVE/tree:time_cutoff, CONFLUENCE_RI_ZLR/tree:time_cutoff) | tree:location ×22 |
| 2026-10-01 | ORR↓ | Variation | Variation | 105 | 2 · +109 | +141 | 205 | ↑ 19:55–20:45 52 (ZLR/tree:bias, DOUBLE_TB/tree:bias, INITIATIVE/tree:bias) | tree:bias ×31 |
| 2026-10-02 | Auction-Out | Variation | Variation | 115 | 3 · -171 | -68 | 131 | ↑ 16:30–16:45 27 (ZLR/tree:stand_down) | tree:bias ×26 |
| 2026-10-05 | Drive↑ | Variation | Variation | 145 | 4 · -309 | -28 | 100 | ↑ 17:00–17:25 30 (ZLR/tree:location, GHOST/tree:location, FAILED_BREAK/tree:location) | tree:location ×15 |
| 2026-10-06 | Drive↑ | Variation | Variation | 25 | 1 · +305 | -6 | 106 | ↑ 17:30–18:25 31 (DOUBLE_TB/entry_not_confirmed, CEILING_FLIP/mid_value_no_edge_test, DOUBLE_TB/tree:location) | mid_value_no_edge_test ×14 |
| 2026-10-07 | Drive↓ | Neutral_Center | Neutral_Center | 150 | 1 · +379 | -106 | 39 | ↑ 18:20–18:50 22 (GHOST/tree:bias, ZLR/tree:bias) | tree:bias ×13 |
| 2026-10-08 | Auction-In | Variation | Variation | 25 | 4 · -132 | -152 | 156 | ↓ 19:15–19:50 47 (CEILING_FLIP/tree:bias) | tree:stand_down ×11 |
| 2026-10-09 | Auction-In | Variation | Variation | 100 | 3 · -245 | -80 | 60 | ↑ 20:15–21:50 18 (ZLR/entry_location_quality) | tree:stand_down ×13 |
| 2026-10-12 | Test-Drive↓ | Variation | Variation | 295 | 3 · -262 | — | 51 | ↑ 18:30–19:05 13 (ZLR/tree:location, REACTIVE/mid_value_no_edge_test, VEGAS/tree:location) | tree:location ×10 |
| 2026-10-13 | Auction-In | Variation | Variation | 25 | 4 · -236 | — | 87 | ↓ 16:40–17:05 17 (אף מועמד) | tree:stand_down ×14 |
| 2026-10-14 | Test-Drive↓ | Variation | Variation | 90 | 6 · -465 | — | 220 | ↓ 20:00–21:00 40 (ZLR/wait_for_test, DOUBLE_TB/entry_location_quality, ZLR/entry_location_quality) | entry_location_quality ×22 |
| 2026-10-15 | Test-Drive↑ | Trend_Normal | Variation ✗ | 125 | 5 · +441 | — | 199 | ↑ 21:25–22:20 37 (INITIATIVE/mid_value_no_edge_test) | tree:stand_down ×11 |
| 2026-10-16 | Drive↓ | Variation | Trend_Normal ✗ | 25 | 3 · -490 | — | 294 | ↓ 19:15–20:20 59 (ZLR/entry_location_quality, INITIATIVE/entry_location_quality, CONFLUENCE_RI_ZLR/entry_location_quality) | wait_for_test ×21 |
| 2026-10-19 | Auction-In | Variation | Variation | 25 | 1 · -100 | -82 | 202 | ↑ 17:50–18:25 30 (ZLR/tree:location) | mid_value_no_edge_test ×18 |
| 2026-10-20 | ORR↑ | Nontrend | Normal ✗ | — | 2 · +406 | -199 | 133 | ↓ 17:55–18:10 44 (אף מועמד) | tree:location ×20 |
| 2026-10-21 | Auction-In | Variation | Variation | 130 | 3 · +502 | -376 | 158 | ↓ 21:15–22:00 41 (CEILING_FLIP/tree:stand_down) | entry_location_quality ×16 |
| 2026-10-22 | Auction-Out | Variation | Variation | 25 | 3 · +589 | +202 | 239 | ↑ 18:40–19:00 31 (CEILING_FLIP/entry_not_confirmed) | mid_value_no_edge_test ×18 |
| 2026-10-23 | Auction-Out | Variation | Variation | 25 | 5 · -601 | -389 | 113 | ↓ 17:00–17:15 26 (ZLR/tree:kind) | entry_location_quality ×14 |
