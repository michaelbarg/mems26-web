# PREFLIGHT — אפס פערי-פיתוח (עדכון W3 · 2026-07-19 ערב)

**בעלים:** cursor-agent · **אימות:** cowork (חוק-5)  
**מדד:** דגל-פתוח × [טסט / UI / סים] × 🟢/🔴 · **🔴 חדש = התרעה ב-LIVE_CHANNEL**

| דגל / פריט | טסט | UI | סים | סטטוס | שינוי מול ערב |
|---|---|---|---|---|---|
| G2+G3 `S2_DETECTION_LIVE_DAYTYPE_V1` | 🟢 T9 | 🟢 | צריך הדלקה | 🟡 מוכן-לבנייה | — |
| G6 S4 fail-honest | 🟢 T10 | 🟢 | צריך | 🟡 מוכן-לבנייה | — |
| D1 position/direction | 🟢 T11 | 🟢 T12 | צריך | 🟡 · בסיס W2: 4 against CONT לייב | W2 מספרים |
| G4 honest-prelock | 🟢 | 🟢 | הדלקה | 🟡 | — |
| **G7 FIXED_4↔REDUCED** | — | 🟡 | — | 🟢 **נסגר** | פסיקת-מייקל `6039dbb6` keep-4-always · G-03 resolved |
| **G8 Neutral/escalation** | — | — | — | 🟡 ממתין-חתימה | **W5 pack** `G8_NEUTRAL_ESCALATION_DOCTRINE_2026-07-19.md` |
| B1 ORPHAN | 🟢 | 🟡 | 🟡 A1.6 | 🟡 סים | — |
| B2 STOP_WIDEN | 🟢 | — | 🟡 | 🟡 סים | — |
| G1 paint | 🟢 | 🟢 | — | 🟢 | — |
| T15 morning stage-E | 🔴 אין קוד E | — | — | 🔴 | פסיקה: stage-E **חובה** (`6039dbb6`) — עדיין לא בנוי |
| T16 S6 reversal | 🟡 W1 hunt | — | ALERT-first | 🟡 | **W1:** 0 whipsaw-hurt על N=15; עדיין לא AUTO |
| T17 4-contracts | 🟡 | 🟡 | E2E | 🟡 | BE-after-**real-T1** נפסק (`6039dbb6`) |

## התרעות 🔴 פתוחות (לא חדשות ממנוע-cc הערב)
1. **T15 stage-E** — חובה לפי פסיקה, **טרם ממומש** → חוסם GO-בוקר אמין.  
2. אין 🔴 חדש מקוד-cc מאז T12 (G2/G3/G6/D1 עדיין לא נבנו).

## W4 (פרונטאנד)
אין diff-מנוע חדש מ-cc מאז T12. Render-check 2026-07-19:
`http://127.0.0.1:3000/` → 200 · `/board` 200 · `/build` 200 ·  
API: `direction_now` dir/sustained · `day_type/live` · `woodies/current` cci/trend — חיים.

כש-cc ימזג G2/G3/G6/D1 — חובה ביטוי-UI + render-check באותו מחזור.
