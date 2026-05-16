# Woodies — מפת עץ החלטות (21 שלבים)

**תאריך:** 2026-05-16  
**מימוש:** Option B · `backend/v9/systems/woodies/decision_tree.py`  
**עקרון:** D-067 — החלטה ב-Woodies · ביצוע (B שלבים) ב-`trade_manager` / `layer4` / `gateway`

---

## לפני כניסה (A1–A7)

| שלב | משמעות במסחר | מי מריץ | סטטוס Wave 1 |
|-----|--------------|---------|--------------|
| A1 | האם יש טרנד CCI ברור | Woodies | ✅ |
| A2 | כל 11 המחוונים חושבו | Woodies | ✅ |
| A3 | איזה דפוס (ZLR, VEGAS…) | Woodies | ✅ |
| A4 | הקשר מיום / TPO / Killzone | Touch-Point APIs | 🟡 PENDING |
| A5 | גודל עסקה (full/half/reject) | Woodies | ✅ |
| A6 | ריאקטיבי vs יוזם | Woodies | ✅ (ממפה TACTICAL→REACTIVE) |
| A7 | סטופ, R:R, מגבלות | pre_fire_validator | ✅ כשיש fire_setup |

## בעסקה פתוחה (B1–B14)

כל שלבי B **מסומנים DELEGATED** — הלוגיקה ב-`trade_manager` ו-`layer4` (לא כפילות).

DEMO/LIVE: **סלוט אחד** ב-`TradingGateway` — מערכת אחרת לא יורה עד סגירה.

---

## קריאה ב-runtime

אחרי כל בר 30 דקות, ב-`current_state`:

- `decision_tree` — תוצאות כל שלב
- `ready_to_route` — האם עברו A שלבים בלי FAIL
- `entry_classification_spec` — REACTIVE / INITIATIVE

---

## עדיין לא LIVE

Option B = מפה + שלד. כסף אמיתי דורש: שאר P0 (S1, S6…), אינטגרציה מלאה, DEMO, אישור שלך.
