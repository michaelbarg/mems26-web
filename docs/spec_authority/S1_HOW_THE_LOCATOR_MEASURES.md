# S1 — איך ה"מאתר" מודד כל קלט (המנגנון בפועל, מהקוד)
*`relative_features.py` · `cvd_features.py` · `context_features.py` · `opening_detector_v2.py`. 2026-06-20.*
*זה ה**מנגנון** — איך כל מספר מחושב מהברים הגולמיים. הספים (מתי זה הופך לסוג-יום) הם במסמך נפרד.*

| קלט | מה הוא מודד | המנגנון המדויק | חומר-גלם | ✏️ נכון? |
|---|---|---|---|---|
| **IB** | טווח השעה הראשונה | `max(high)`, `min(low)` של **12 הברים הראשונים** (09:30–10:30). `IB_width = high − low` | ברים 5-דק׳ | |
| **sides** | כמה צדדי-IB נפרצו | סף = `IB_edge ± max(0.3×IB_width, 2 טיק)`. הרצף-**הרציף**-הארוך-ביותר של closes מעבר לסף; ≥**2 ברים** = "נפרץ". `sides = עליון+תחתון` | closes + IB | |
| **rib** | טווח÷IB (סיגנל מרכזי) | `(session_high − session_low) ÷ IB_width` | ברים + IB | |
| **close_pos** | מיקום הסגירה בטווח | `(last_close − session_low) ÷ (session_high − session_low)` ∈ 0..1 | ברים | |
| **one_tf** | מגמה חד-זמנית | תקופות 30-דק׳ (6 ברים); `UP` אם אף תקופה לא עושה Lower-Low · `DOWN` אם אף תקופה לא עושה Higher-High · אחרת None | ברים | |
| **returned_through_open** | דרייב-פתיחה שבוטל | כיוון מ-2 ברים ראשונים; בעלייה נדלק אם בר מאוחר סוגר מתחת ל-open (להפך בירידה) | closes + open | |
| **opening_type** | סוג הפתיחה | סדר: Drive(כל lows≥open+מונוטוני) → Test-Drive(poke-נכשל) → Rejection(היפוך-מלא) → Auction | 6 ברים + רמות | |
| **cvd_pos** | מיקום CVD בטווח-הסשן | `(cvd_now − cvd_min) ÷ (cvd_max − cvd_min)`. תומך-כיוון רק אם הקצה נוצר ב-5 ברים אחרונים | סדרת CVD | |
| **vol_ratio** | השתתפות יחסית | `session_volume ÷ median(ווליום-ימים-קודמים)` | ווליום + היסטוריה | |
| **poc_drift** | נדידת-ערך | `(poc_now − poc_at_IB) ÷ IB_width` | TPO 30-דק׳ | |
| **dd_second_dist** | התפלגות-שנייה (Trend_DD) | **proxy**: קפיצת-POC ≥0.8×IB שמחזיקה ≥2 תקופות. **לא** single-print אמיתי | TPO POCs | |
| **IB-class** | צר/בינוני/רחב | מוחלט: ≤7 צר · 7–13 בינוני · ≥13 רחב | IB_width | |

## ה-flaws במנגנון עצמו (שאני רואה)
1. **OPEN_DRIVE — המנגנון נוקשה מדי.** דורש שאף בר מ-6 לא יחזור מתחת ל-open. בפועל המחיר כמעט תמיד נוגע מתחת לפתיחה → **0 ימים** יצאו Drive בסריקה → הפתיחה כמעט תמיד Auction → **Trend_Normal כמעט בלתי-נגיש**. ⟵ כנראה ה-flaw המרכזי.
2. **sides — מבוסס closes בלבד.** הרחבה אמיתית עם פתיל (wick) שלא נסגר מעבר — לא נספרת. ייתכן שצריך גם high/low ולא רק close.
3. **dd_second_dist — proxy.** קפיצת-POC נדלקת-יתר; צריך single-print אמיתי.
4. **vol_ratio + IB — חומר-גלם מזוהם** לימים פרה-גלגול.
