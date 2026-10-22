# מוכנות העץ 3.4.0 לכל סוג-פתיחה × שלב × סוג-יום (T-631, 22.10)

סטטוס: **ready** = יש לפחות עלה TAKE · **skip_only** = יש שורות אבל כולן SKIP · **stand_down** = אין שורת-דוקטרינה (העץ עומד בצד).
עמודת TAKE = מספר העלים המאשרים; kinds = סוגי-הכניסה המותרים; measured = n/usd מהעלים (tree_measure).

## OPEN_DRIVE
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Trend_Normal | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Trend_DD | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Normal_Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Normal | ready | 12 | 9 | 0 | *, WITH_DRIVE | bias, kind, location, stand_down | 0 / +998 |
| A | Neutral_Center | ready | 12 | 9 | 0 | *, WITH_DRIVE | bias, kind, location, stand_down | 0 / +998 |
| A | Neutral_Extreme | ready | 12 | 9 | 0 | *, WITH_DRIVE | bias, kind, location, stand_down | 0 / +998 |
| A | Nontrend | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| A | Nonconviction | ready | 4 | 2 | 0 | *, WITH_DRIVE | bias, kind | 0 / +332 |
| B | FORMING | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_Normal | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_DD | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Normal_Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Normal | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Center | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Extreme | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Nontrend | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Nonconviction | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

## OPEN_TEST_DRIVE
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | FORMING | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_Normal | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_DD | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Normal_Variation | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Normal | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Center | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Extreme | ready | 12 | 9 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Nontrend | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| B | Nonconviction | ready | 4 | 2 | 0 | *, WITH_DRIVE|PULLBACK | bias, kind | 0 / +332 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

## OPEN_REJECTION_REVERSE
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | FORMING | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_Normal | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Trend_DD | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Variation | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Normal_Variation | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Normal | ready | 12 | 9 | 0 | *, REVERSAL|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Center | ready | 12 | 9 | 0 | *, REVERSAL|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Neutral_Extreme | ready | 12 | 9 | 0 | *, REVERSAL|PULLBACK | bias, kind, location, stand_down | 0 / +998 |
| B | Nontrend | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| B | Nonconviction | ready | 4 | 2 | 0 | *, REVERSAL|PULLBACK | bias, kind | 0 / +332 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

## OPEN_AUCTION_IN
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | FORMING | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Trend_Normal | ready | 4 | 1 | 0 | *, BREAK, EDGE_FADE, REVERSAL | kind | 33 / +373 |
| B | Trend_DD | ready | 4 | 1 | 0 | *, BREAK, EDGE_FADE, REVERSAL | kind | 33 / +373 |
| B | Variation | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Normal_Variation | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Normal | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Nontrend | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Nonconviction | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

## OPEN_AUCTION_OUT
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | FORMING | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Trend_Normal | ready | 4 | 1 | 0 | *, BREAK, EDGE_FADE, REVERSAL | kind | 33 / +373 |
| B | Trend_DD | ready | 4 | 1 | 0 | *, BREAK, EDGE_FADE, REVERSAL | kind | 33 / +373 |
| B | Variation | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Normal_Variation | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Normal | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE, REVERSAL | kind, location, stand_down | 50 / +544 |
| B | Nontrend | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| B | Nonconviction | ready | 3 | 1 | 0 | *, EDGE_FADE, REVERSAL | kind | 25 / +272 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

## UNKNOWN
| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |
|---|---|---|---|---|---|---|---|---|
| A | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| A | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| A | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Trend_Normal | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Trend_DD | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Normal_Variation | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Normal | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| B | Neutral_Center | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| B | Neutral_Extreme | skip_only | 0 | 7 | 0 | — | location, stand_down | 0 / +0 |
| B | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| B | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| C | Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal_Variation | ready | 5 | 3 | 0 | *, BREAK|VALUE_RETURN | bias, kind | 0 / +499 |
| C | Normal | ready | 20 | 12 | 0 | *, BREAK|VALUE_RETURN, EDGE_FADE, EDGE_FADE|VALUE_RETURN | bias, kind, location, stand_down | 58 / +2679 |
| C | Neutral_Center | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Neutral_Extreme | ready | 8 | 5 | 0 | *, EDGE_FADE | kind, location, stand_down | 0 / +1132 |
| C | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| C | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | FORMING | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Trend_Normal | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Trend_DD | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal_Variation | ready | 1 | 1 | 0 | — | stand_down | 19 / +160 |
| D | Normal | ready | 1 | 2 | 0 | — | stand_down | 19 / +160 |
| D | Neutral_Center | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Neutral_Extreme | ready | 4 | 2 | 0 | *, PULLBACK|BREAK | bias, kind | 0 / +499 |
| D | Nontrend | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |
| D | Nonconviction | stand_down | 0 | 1 | 0 | — | stand_down | 0 / +0 |

**סיכום:** 240 תאים · ready 138 · skip_only 18 · stand_down 84
