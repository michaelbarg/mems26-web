# משימת-קורסור (+סוכן): האם ה-UI משקף את מה שהמנוע רואה? — טרנד · סוג-יום · כיוון

**פסיקת-מייקל 2026-07-19:** *"האם ה-UI מכיר בעדכון החדש ויידע לתאר לי? האם בכל מקום רלוונטי מעודכן
באתר? אם לא — משימה לקורסור שיבצע עם סוכן."*

**מבצע: cursor-agent + סוכן (fan-out על הפרונטאנד — קריאה-בלבד).** מאמת: cowork-dev.
**תוצר: `docs/handoff/UI_CONSISTENCY_AUDIT_2026-07-19.md`** — טבלת "מה ה-UI מציג מול מה שהמנוע רואה".

## הרקע (מה השתנה ולמה השאלה)
G1 (`bars.py:1167`, `8dcb4a79`) גרם ל**מנוע** (S4) לראות **טרנד-עדכני על הבר-החי** (`_trend_from_cci`
על `current_bar`). אבל ה-override של `current_bar` **רק מנתב ל-S4 (`_route_bar`) — לא כותב ל-DB ולא
לאף endpoint.** לכן:
- **בר-סגור:** ה-UI כבר תקין (DB `v9_bars_5min_woodies` עם relabel מאז `:1087`, לפני G1).
- **בר-חי + סוג-יום + כיוון:** ה-UI **כנראה לא** משקף את מה שהמנוע פועל לפיו — זו מחלקת-G5/G-16
  (UI קורא `classify_replay`/raw, לא `get_live_day_type`). **צריך לאמת בכל מקום.**

## המשימה — 3 שאלות, בכל מקום רלוונטי
לכל רכיב-UI שמציג **טרנד(paint)** / **סוג-יום** / **כיוון-מותר**, קבע (עם `file:line`):
1. **מאיפה הוא קורא?** endpoint + שדה (DB-סגור? `classify_replay`? `get_live_day_type`? raw live?).
2. **האם זה תואם את מה שהמנוע/השער פועל לפיו?** (השער קורא `get_live_day_type`; הטרנד-החי אחרי G1
   הוא `_trend_from_cci`). סמן ✅ תואם / 🔴 מפגר-או-שונה.
3. **אם 🔴 — מה המשתמש רואה בפועל** (למשל GRAY-דביק על הבר-החי בזמן ש-S4 כבר RED; או סוג-יום ישן
   בזמן ש-override פעיל).

## איפה לחפש (fan-out — סוכן)
- **טרנד/paint:** `ChartV5b`/`ChartV5`/candle-overlays · `WoodiesCciPanel` · כל רכיב עם `trend_state`/
  `BLUE`/`RED`/`GRAY`.
- **סוג-יום:** `TopBar` · `DayTypeLens`/`DayTypeLensContent` · Build-Status · הפילים/הסטריפ.
- **כיוון:** כל תצוגת "כיוון מותר"/direction/LONG-SHORT bias · Systems-panel.
- **endpoints שמאכילים אותם:** `chart/bars5min` · `day_type/*` · `systems`/`cockpit` · `live_price`.
  קבע לכל אחד: DB-סגור (relabeled) / raw / override-aware.

## הצלבות (חובה, code-cited)
- `docs/SOURCE_OF_TRUTH.md` §Day-type (מה קנוני ל-UI מול מסחר) · `S1_ACTIVE_CANONICAL.md`.
- `GAP_REGISTER.md` G-16 (UI SoT) — **המשימה הזו מרחיבה אותו** לכלול טרנד-חי + כיוון, לא רק סוג-יום.
- הבר-החי: `bars.py:1137-1169` (override מנתב-בלבד, לא-כותב-DB) — ל-UI אין את הטרנד-החי-המתוקן היום.

## תוצר
טבלה: `רכיב | מציג | מקור(file:line) | תואם-מנוע? | מה-המשתמש-רואה-אם-🔴 | תיקון-מוצע`.
בסוף: **רשימת-🔴 ממוינת** + לכל אחד תיקון-מוצע (בד"כ: לקרוא שדה override-aware/DB-relabeled קיים; אם
צריך endpoint — לא לשכפל מנוע, להוסיף שדה). **הצעות בלבד — אל תיגע בקוד.**

## מה אסור / מותר
❌ שינוי-קוד/.env · ❌ דוקטרינה בלי `file:line`. ✅ קריאת-קוד + `chart/day_type` endpoints (GET) לאימות-תצוגה.
שורת-LOG ב-`LIVE_CHANNEL`: `UI_CONSISTENCY ✅/🔴 · N surfaces · M mismatches`. cowork מאמת (חוק-5).
