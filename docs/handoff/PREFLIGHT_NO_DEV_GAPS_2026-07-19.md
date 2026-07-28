# PREFLIGHT — אפס פערי-פיתוח (W3 refresh · 2026-07-19 ~22:45 IL)

**בעלים:** cursor-agent · **🔴 חדש = התרעה ב-LIVE_CHANNEL**

| דגל / פריט | טסט | UI | סים | סטטוס | הערת-ערב |
|---|---|---|---|---|---|
| G2+G3 detection-live | 🟢 T9 | 🟢 | הדלקה | 🟡 מוכן-לבנייה | אין קוד-cc עדיין |
| G6 S4 fail-honest | 🟢 T10 | 🟢 | הדלקה | 🟡 מוכן-לבנייה | — |
| D1 position/direction | 🟢 T11 | 🟢 T12 | הדלקה | 🟡 · W2: 4 against CONT | — |
| G4 honest-prelock | 🟢 | 🟢 | הדלקה | 🟡 | — |
| G7 FIXED_4↔REDUCED | — | 🟡 | — | 🟢 keep-4 | נפסק |
| G8 Neutral/escalation | — | — | — | 🟡 ממתין-חתימה | **W5 pack** |
| B1 ORPHAN / FLATTEN_ORPHAN | 🟢 harness+tests | 🟡 | 🟡 A1.6 | 🟡 סים | `verify_orphan_place_stop_sim.py` |
| B2 STOP_WIDEN | 🟢 | — | 🟡 | 🟡 סים | — |
| G1 paint | 🟢 | 🟢 | — | 🟢 | ב-`bars.py` |
| **T15 morning stage-E** | 🟢 5 tests | — | cowork+פסיקת-הדלקה | **🟡 בנוי OFF** | 07-17 GO 1/7 · 07-16 INDETERMINATE |
| **T16 S6 reversal** | 🟢 W1 hunt | — | ALERT→סים | 🟡 לבנייה | פסיקה **א'** · trigger=CVD+2closes |
| T17 4-contracts | 🟢 harness | 🟡 | E2E cc | 🟡 | `verify_t17_e2e_4contract_sim.py` |
| Phone MOBILE_REMOTE | — | 🟡 paint/dir | — | 🟡 שארית | שורש URL תוקן cowork |

## התרעות 🔴
1. **אין 🔴 חדש** ממנוע-cc מאז T12 (G2/G3/G6/D1 לא נבנו הערב).
2. **T15 stage-E 🟡** — בנוי flag-OFF; ממתין אימות-cowork + פסיקת-הדלקה.

## W4 (צמוד)
אין diff-מנוע חדש מ-cc הדורש UI נוסף מעבר ל-T12/T14.  
Render 2026-07-19 22:40: `:3000/` `/board` `/build` → **200**.  
API: `direction_now` · `day_type/live` · `woodies/current` חיים (pre-RTH: NEUTRAL/null/GRAY).
