# D-WDIAG · Extreme Trend Relabel — SHADOW Runtime Audit + `trend_original` Impl
**תאריך:** 2026-06-02  
**תווית:** D-WDIAG  
**מאת:** Claude Code → **אל:** Michael  
**חוזה:** `docs/handoff/CC_HANDOFF_CONTRACT.md`  
**אישור:** APPROVED 2026-06-02, Michael — `docs/plans/DECISION_LEDGER.md`

---

## טבלת Phases

| # | Phase | Status | Evidence | Deviation |
|---|-------|--------|----------|-----------|
| 1 | `S4_EXTREME_TREND_RELABEL` דלוק ב-runtime | **DONE** | §1: `ps eww` → `S4_EXTREME_TREND_RELABEL=true` | — |
| 2a | HFE trade נרשם ב-SHADOW | **DONE** | §2a: שרשרת relabel→A1→gateway→v9_trades | — |
| P1 | `trend_original` נשמר ב-`trend_relabel.py` | **DONE** | §P1: `grep -rn trend_original backend/` | — |
| P2 | `trend_original` ב-`current_state.update()` | **DONE** | §P2: litmus revert→4 RED, restore→10 GREEN | — |
| P3 | `trend_original` בתצוגת סיכום | **DONE** | §P3: `trade_context.py:342` | — |
| Test | טסט אנטי-טאוטולוגי (B1) | **DONE** | §Test: 10 passed, litmus confirmed | — |

---

## §1 · דגל חי ב-runtime (מ-audit ראשון)

```
$ ps eww -p 23884 | tr ' ' '\n' | grep S4_EXTREME
S4_EXTREME_TREND_RELABEL=true
```

**מקור:** `~/Library/LaunchAgents/com.mems26.backend.plist` שורה 11.  
**קוד:** `backend/v9/shared/atr.py:89` — ברירת מחדל OFF, plist מדליק.  
**מסקנה:** הדגל ON ב-runtime.

---

## §2a · שרשרת HFE → SHADOW trade

1. `woodies_system.py:279` → `apply_extreme_trend_relabel(studies)` → YELLOW/GRAY → BLUE/RED
2. `woodies_system.py:311` → `detect_all_patterns()` → HFE
3. `woodies_system.py:490` → `gateway.route_setup(setup, 4)`
4. `trading_gateway.py:116` → `_execute_shadow()` → `v9_trades` row

---

## §P1 · שמירת המקור — `trend_relabel.py`

**שינוי:** שורה אחת נוספה **לפני** בדיקת הדגל, כך ש-`trend_original` תמיד קיים:

```python
# D-WDIAG: preserve original trend for A/B comparison (always, even no-op)
studies["trend_original"] = studies.get("trend_state")
```

**ראיה:**
```
$ grep -rn "trend_original" backend/
backend/v9/systems/woodies/trend_relabel.py:19:    Always sets studies["trend_original"]...
backend/v9/systems/woodies/trend_relabel.py:22:    studies["trend_original"] = studies.get("trend_state")
backend/v9/systems/woodies/woodies_system.py:433:    "trend_original": studies.get("trend_original"),  # D-WDIAG
backend/v9/services/trade_context.py:342:    for key in ("trend_state", "trend_original", "cci_14"...  # D-WDIAG
```

---

## §P2 · current_state.update — הנגיעה הקריטית

**הבעיה שאותרה ע"י Cowork:** `woodies_system.py:425-432` הוא `current_state.update({מילון מפורש})` — **לא** `update(studies)`. מפתח חדש ב-`studies` לא זורם אוטומטית.

**תיקון:** הוספת שורה למילון המפורש:
```python
"trend_original": studies.get("trend_original"),  # D-WDIAG: A/B relabel
```

**שרשרת הזרימה המלאה:**
`trend_relabel.py` → `studies["trend_original"]` → `current_state.update({..., "trend_original": ...})` → `get_current()` (`:733-734`) → `_capture_cross_context()` (`:399-410`) → `v9_trades.cross_context` JSON

---

## §P3 · תצוגת סיכום — `trade_context.py`

**שינוי:** `trade_context.py:342` — הוספת `"trend_original"` ל-tuple:
```python
for key in ("trend_state", "trend_original", "cci_14", "signal", "classification"):  # D-WDIAG
```

---

## §Test · טסט אנטי-טאוטולוגי

**קובץ:** `tests/v9/regression/test_d_wdiag_trend_original.py`

4 טסטים שקוראים לקוד הייצור end-to-end:
1. **Flag ON + YELLOW + CCI=250** → `get_current()["trend_original"]=="YELLOW"`, `["trend_state"]=="BLUE"`
2. **Flag OFF + YELLOW + CCI=250** → `trend_original=="YELLOW"`, `trend_state=="YELLOW"` (no relabel)
3. **Flag ON + BLUE (natural) + CCI=250** → `trend_original=="BLUE"`, `trend_state=="BLUE"`
4. **Flag ON + GRAY + CCI=-220** → `trend_original=="GRAY"`, `trend_state=="RED"`

**if reverted P2 → RED because** השדה לא מגיע ל-`current_state` ולכן לא ל-`cross_context`.

### ראיה: all pass

```
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_d_wdiag_trend_original.py tests/v9/regression/test_d_wdiag_extreme_trend.py -v
======================== 10 passed, 2 warnings in 0.10s ========================
```

### ראיה: litmus revert P2 → RED

```
# After reverting ONLY P2 (woodies_system.py:433), keeping P1:
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_d_wdiag_trend_original.py -v
FAILED test_trend_original_in_get_current_after_relabel
FAILED test_trend_original_no_relabel_when_flag_off
FAILED test_trend_original_blue_stays_blue
FAILED test_trend_original_negative_extreme
======================== 4 failed, 2 warnings in 0.20s =========================
```

---

## NOT DONE / DEVIATIONS

None.

## Open

1. **ממתין לבר ±200 RTH ראשון** — רק אז ניתן לראות ראיה חיה ש-`cross_context` JSON ב-`v9_trades` מכיל `trend_original`.
2. **שאילתת A/B:** `SELECT * FROM v9_trades WHERE cross_context LIKE '%"trend_original": "YELLOW"%' OR cross_context LIKE '%"trend_original": "GRAY"%'` = trades שעברו relabel. trades עם `trend_original == trend_state` = trend טבעי.
