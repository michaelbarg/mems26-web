# S1 — אינדקס נתוני-Sierra (מקור-האמת) · השתמש בזה, אל תמציא
*2026-06-20. כל זיהוי-יום נבנה אך ורק מהשדות כאן — נתון אמיתי מ-Sierra, נקלט ושמור. אסור proxy/סינתזה (Rule 1).*

## העיקרון (מחייב כל אגנט)
1. **לפני שמחשבים קלט כלשהו** — חפש אותו באינדקס הזה. אם הוא קיים מ-Sierra → השתמש בו ישירות. **אל תחשב מחדש ואל תמציא.**
2. אם השדה קיים ב-Sierra אבל לא נקלט — קולטים אותו (stream + טבלה), לא ממציאים proxy.
3. אם Sierra באמת לא נותנת אותו — מחזירים `None`/"missing" (Rule 1), לא מסנתזים.

## האינדקס — export → טבלה → שדות → סיגנל
| Sierra export | טבלה | שדות-מפתח | סיגנל S1 | סטטוס שימוש |
|---|---|---|---|---|
| `5min.json` | `v9_bars_5min` | OHLCV, poc_vol, vah, val, cumulative_delta | טווח, sides, CVD | בשימוש |
| `woodies_5min.json` | `v9_bars_5min_woodies` | OHLCV, cci, trend_state, zlr/hfe, proj_hi/lo | מגמה, תבניות S4 | בשימוש (OHLCV) |
| `cumulative_delta.json` | `v9_bars_cumulative_delta` | delta, cumulative, direction | CVD (cvd_pos) | ✅ בשימוש |
| `volume_profile.json` | `v9_bars_volume_profile` | **profile (ווליום/מחיר), poc, vah, val, total_volume** | **HVN/LVN, צוואר, DD, tails, רוחב-VA** | ❌ **לא בשימוש — הבא לחבר** |
| `footprint.json` | `v9_bars_footprint` | delta, poc_price, levels, stacked_buy/sell | order-flow, ספיגה | S3 (מושתק) |
| `tpo.json` | `v9_tpo_sessions` / `v9_tpo_history` | poc/vah/val, ib_high/low, **profile_shape**, opening_type, range_high/low, hvn/lvn_zones, poc_migration, ib_class | DD-shape, IB, VA, open-location | ✅ חלקי (IB, shape) |

## מיפוי כל קלט-S1 → מקור-Sierra מאומת
| קלט | מקור Sierra | סטטוס |
|---|---|---|
| IB high/low/width | `v9_tpo_sessions.ib_high/ib_low` | ✅ |
| POC/VAH/VAL (היום) | `v9_tpo_sessions` / `v9_bars_volume_profile` | ✅ |
| POC/VAH/VAL (אתמול) | `v9_tpo_sessions` (prior trading_date) | ✅ |
| CVD (cvd_pos) | `v9_bars_cumulative_delta.cumulative` | ✅ |
| profile_shape (DD) | `v9_tpo_sessions.profile_shape` (B/DD=double) | ✅ |
| **HVN/LVN, צוואר, tails, רוחב-VA** | **`v9_bars_volume_profile.profile`** | ❌ לחבר |
| opening_type | `v9_tpo_sessions.opening_type` (Sierra מחשבת!) | ❌ לבדוק/לחבר במקום הגלאי-שלי |
| range (high/low) | bars / `v9_tpo_sessions.range_high/low` | ✅ |
| trend_state | `v9_bars_5min_woodies.trend_state` | זמין |

## הבא (בלי להמציא): לחבר את `v9_bars_volume_profile`
ממנו נגזרים, מנתון-Sierra אמיתי: HVN/LVN (ההתפלגויות), הצוואר (LVN בין שתי גבעות → DD אמיתי), tails (ווליום-דק בקצוות → דחיית-Neutral), רוחב-VA (Normal/Nontrend). וגם לבדוק את `v9_tpo_sessions.opening_type` (אולי Sierra כבר נותנת סוג-פתיחה מדויק במקום הגלאי-השבור שלי).
