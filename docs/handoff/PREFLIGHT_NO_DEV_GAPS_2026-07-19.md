# PREFLIGHT — אפס פערי-פיתוח מחר (T13)

**תאריך:** 2026-07-19 · **בעלים:** cursor-agent · **אימות:** cowork (חוק-5)

**מדד:** כל דגל-פתוח × [טסט / UI / קריטריון-סים] × 🟢/🔴.  
**🔴 = פער לסגור לפני בוקר** (או מפורש: חסום-פסיקה/סים בלבד).

| דגל / פריט | טסט מוכן | UI משקף | קריטריון-סים | סטטוס |
|---|---|---|---|---|
| **G2+G3** `S2_DETECTION_LIVE_DAYTYPE_V1` (עדיין לא בקוד) | 🟢 `test_s2_detection_live_daytype.py` (contract + xfail wiring) | 🟢 יום-live כבר ב-TopBar/Switcher/KeyLevels | sim_matrix + E2E תחת דגל ON; OFF=byte-identical | 🟡 מוכן-לבנייה · קוד=cc |
| **G6** S4 fail-honest (דגל מוצע) | 🟢 `test_s4_honest_daytype_fallback.py` | 🟢 N/A (מקור-יום; UI live-aware) | אין Normal-synth כש-live None | 🟡 מוכן-לבנייה · קוד=cc |
| **D1** `DAYTYPE_POSITION_GATE` / `DIRECTION_AUTHORITY_V1` | 🟢 T6+T11 ב-`test_direction_authority_map.py` (+ existing `test_daytype_position_gate.py`) · xfail mig | 🟢 T12: DirectionStrip sustained · Switcher setup≠allowed · BuildTree GATE | against-Dalton ↓ · 0 false blocks | 🟡 מוכן-לבנייה · הדלקה=מייקל+סים |
| **G4** `DAYTYPE_HONEST_PRELOCK_V1` | 🟢 `test_daytype_honest_prelock.py` | 🟢 תווית פרה-IB (live) | pre-IB → None/forming לא תווית-ישנה | 🟡 הדלקה=cowork+מייקל |
| **G7** FIXED_4 ↔ REDUCED | 🔴 אין טסט "REDUCED survives FIXED_4" מפורש | 🟡 תצוגת-חוזים חלקית | playbook REDUCED לא נבלע | 🔴 פער · פסיקת-מייקל לפני קוד |
| **G8** Neutral doctrine | 🔴 spec בלבד | — | — | 🔴 דוקטרינה |
| **B1** `ORPHAN_AUTO_STOP_V1` | 🟢 `test_orphan_auto_stop.py` | 🟡 אופציונלי | PLACE_STOP orphan · qty לא גדל | 🟡 סים-gated (A1.6) |
| **B2** `STOP_WIDEN_TO_FLOOR_*` | 🟢 `test_stop_widen_to_floor_reject.py` | — | widen + SIZE_CAP_CUT | 🟡 סים-gated |
| **G1 paint** `TREND_CCI_DIRECT_V1` | 🟢 (cowork) | 🟢 woodies chart `_trend_from_cci` | — | 🟢 (שליטת cowork) |
| **T15 morning GO** | 🔴 אין fire-readiness-real | — | GO רק אם setups אמיתיים עוברים גייטים | 🔴 ביקורת במסמך · חוסם GO אמין |
| **T16 S6 reversal** | 🟡 supervisor ALERT בלבד | — | MODIFY_STOP+MODIFY_TARGET בסים | 🔴 הצעה · מימוש=cc |
| **T17 4-contracts** | 🟡 effective_contracts + fire_drill C | 🟡 | E2E 4 fills + stop per stage | 🔴 ביקורת · `system6_routes` עדיין `expected=3` במקום אחד |

## סיכום ערב
- **מוכן ל-cc מחר (בלי פער טסט/UI):** G2/G3, G6, D1 (POC חלק), G4, B1/B2 (סים).
- **עדיין 🔴 לפני "אפס פערים":** G7 (פסיקה), G8 (דוקטרינה), T15 (פרוטוקול-בוקר), T16/T17 (מימוש אחרי פסיקה+סים).
- **לא לממש מסחר כאן:** G2/G3/G6/D1/S6/sizing = cc-macbook.

## חוק-5 (ריצת טסטים מקומית)
ראה LOG ב-`LIVE_CHANNEL` אחרי pytest.
