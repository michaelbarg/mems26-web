# D-049: Suffering Side Veto — Full Implementation Spec

**Decision**: D-049  
**Status**: SPEC READY  
**Priority**: Sprint 4 Quick Win  
**Source**: חוזים.docx — "Suffering Side Rule"  

---

## 1. Source Citation

From Michael's methodology notes (חוזים.docx, "Suffering Side Rule"):

> "אנחנו אף פעם לא מצטרפים לצד הסובל"  
> (We never join the suffering side)

**Principle**: If price is on the wrong side of the day's Point of Control (POC), the side you'd be joining is "suffering" — trapped traders who are underwater. Joining them means fighting the dominant auction. This is a hard veto.

---

## 2. Logic

```python
def suffering_side_veto(setup: dict, market_profile: dict) -> dict | None:
    """
    Veto setups where we'd join the suffering side relative to day POC.
    
    Args:
        setup: Must contain 'direction' ('LONG'/'SHORT') and 'entry_price' (float)
        market_profile: Must contain 'poc' (float) — current day POC
    
    Returns:
        None if setup passes (no veto)
        dict with 'reason' if setup is vetoed
    """
    direction = setup.get("direction")
    entry_price = setup.get("entry_price")
    day_poc = market_profile.get("poc")
    
    # Guard: need all fields
    if not direction or not entry_price or not day_poc:
        return None  # Can't evaluate — let it pass
    
    # LONG below POC — buyers are suffering, we'd be joining them
    if direction == "LONG" and entry_price < day_poc:
        return {
            "gate": "suffering_side",
            "reason": f"LONG below POC — buyers suffer (entry {entry_price} < POC {day_poc})",
            "entry_price": entry_price,
            "day_poc": day_poc,
            "direction": direction,
        }
    
    # SHORT above POC — sellers are suffering, we'd be joining them
    if direction == "SHORT" and entry_price > day_poc:
        return {
            "gate": "suffering_side",
            "reason": f"SHORT above POC — sellers suffer (entry {entry_price} > POC {day_poc})",
            "entry_price": entry_price,
            "day_poc": day_poc,
            "direction": direction,
        }
    
    # Entry at POC — not strictly suffering (edge case)
    return None
```

### Decision Table

| Direction | Entry vs POC | Result | Reasoning |
|-----------|-------------|--------|-----------|
| LONG | entry < POC | **VETO** | Buyers below POC are trapped — we'd join losers |
| LONG | entry >= POC | Pass | Buyers above POC have auction support |
| SHORT | entry > POC | **VETO** | Sellers above POC are trapped — we'd join losers |
| SHORT | entry <= POC | Pass | Sellers below POC have auction support |
| Any | entry == POC | Pass | At POC — neutral, not strictly suffering |

---

## 3. Required Data

| Field | Source | Current Status |
|-------|--------|----------------|
| `setup.direction` | Frontend `calcSetups()` / Backend setup detection | ✅ Exists — `'LONG'` or `'SHORT'` |
| `setup.entry_price` | Frontend `calcSetups()` / Backend trade execution | ✅ Exists — `entry_price` field in setup and trade objects |
| `market_profile.poc` | Sierra → Bridge → Redis → Backend | ✅ Exists — `profile.poc` in market data (current day POC) |

**Note on field names**:
- Current day POC: `profile.poc` (in frontend), `market_profile.poc` (in backend/Redis)
- Previous day POC: `profile.prev_day_poc` / `market_profile.prev_day_poc`
- This gate uses **current day POC** (`poc`), not previous day

---

## 4. Backtest Plan

### Dataset
- **Source**: Backend PostgreSQL — `setups` table
- **Count**: ~1,973 historical setups (per current DB state)
- **Period**: All recorded setups with both direction and market profile data

### Methodology
1. For each setup, retrieve `direction`, `entry_price`, and `poc` at time of setup
2. Apply `suffering_side_veto()` logic
3. Split into two groups:
   - **Blocked**: setups that would have been vetoed
   - **Passed**: setups that would have passed

### Metrics to Compute
| Metric | Blocked Group | Passed Group |
|--------|---------------|--------------|
| Count | n_blocked | n_passed |
| Win Rate | WR_blocked | WR_passed |
| Avg PnL (pts) | avg_pnl_blocked | avg_pnl_passed |
| Max Drawdown | max_dd_blocked | max_dd_passed |
| Profit Factor | pf_blocked | pf_passed |

### Expected Results
- **Block rate**: 30-40% of all setups
- **WR of blocked group**: Lower than passed group (these are bad trades we'd avoid)
- **Key validation**: `WR_blocked < WR_passed` by at least 5 percentage points
- **If block rate > 50%**: Gate is too aggressive — review POC calculation or add tolerance band

### SQL Query (approximate)
```sql
SELECT 
    s.setup_id,
    s.direction,
    s.entry_price,
    s.market_snapshot->>'poc' AS day_poc,
    s.outcome,  -- 'win' / 'loss' / 'breakeven'
    s.pnl_pts,
    CASE 
        WHEN s.direction = 'LONG' AND s.entry_price < (s.market_snapshot->>'poc')::float THEN 'BLOCKED'
        WHEN s.direction = 'SHORT' AND s.entry_price > (s.market_snapshot->>'poc')::float THEN 'BLOCKED'
        ELSE 'PASSED'
    END AS veto_status
FROM setups s
WHERE s.direction IS NOT NULL
  AND s.entry_price IS NOT NULL
  AND s.market_snapshot->>'poc' IS NOT NULL;
```

---

## 5. Implementation Locations

| Layer | File | Change | Effort |
|-------|------|--------|--------|
| DLL (Sierra) | — | Nothing | — |
| Bridge | — | Nothing | — |
| Backend | `backend/gates/suffering_side.py` (new) | Gate function + integration with gate pipeline | 2 hours |
| Backend | `backend/main.py` | Add gate call in trade execution flow (near line ~2709, alongside Quality Score Gate) | 30 min |
| Frontend | `frontend/src/components/Dashboard.tsx` | Add "Suffering Side" badge to setup card | 1 hour |
| Backtest | `tools/backtest/suffering_side_backtest.py` (new) | Backtest script | 2 hours |

### Backend Integration Point

In `backend/main.py`, the gate pipeline is around line 2630+. The suffering side check should be added as an early gate — before Quality Score Gate:

```python
# === Suffering Side Gate (D-049) ===
from gates.suffering_side import suffering_side_veto

_ss_result = suffering_side_veto(
    {"direction": direction, "entry_price": entry_price},
    {"poc": latest_market.get("market_profile", {}).get("poc", 0)}
)
if _ss_result and not _skip_gates:
    return {"blocked": True, "gate": "suffering_side", "reason": _ss_result["reason"]}
```

### Frontend Badge

In the setup card (around line 2949), add a badge:

```tsx
{/* Suffering Side indicator */}
<span style={{ 
    color: entryPrice >= poc ? '#22c55e' : '#ef4444',
    fontSize: 12 
}}>
    Suffering Side: {entryPrice >= poc ? '✅' : '❌'}
</span>
```

---

## 6. Test Cases

| # | Direction | Entry Price | Day POC | Expected | Reasoning |
|---|-----------|-------------|---------|----------|-----------|
| 1 | LONG | 5732 | 5740 | **VETO** | LONG below POC — buyers suffer |
| 2 | LONG | 5745 | 5740 | Pass | LONG above POC — buyers have support |
| 3 | SHORT | 5750 | 5740 | **VETO** | SHORT above POC — sellers suffer |
| 4 | SHORT | 5735 | 5740 | Pass | SHORT below POC — sellers have support |
| 5 | LONG | 5740 | 5740 | Pass | At POC — not strictly suffering (edge case) |
| 6 | SHORT | 5740 | 5740 | Pass | At POC — not strictly suffering (edge case) |
| 7 | LONG | 5739.75 | 5740 | **VETO** | Just below POC — still suffering |
| 8 | SHORT | 5740.25 | 5740 | **VETO** | Just above POC — still suffering |
| 9 | LONG | None | 5740 | Pass | Missing entry price — can't evaluate |
| 10 | LONG | 5735 | None | Pass | Missing POC — can't evaluate |

### Unit Test Structure

```python
import pytest
from gates.suffering_side import suffering_side_veto

@pytest.mark.parametrize("direction,entry,poc,should_veto", [
    ("LONG",  5732,    5740, True),
    ("LONG",  5745,    5740, False),
    ("SHORT", 5750,    5740, True),
    ("SHORT", 5735,    5740, False),
    ("LONG",  5740,    5740, False),
    ("SHORT", 5740,    5740, False),
    ("LONG",  5739.75, 5740, True),
    ("SHORT", 5740.25, 5740, True),
])
def test_suffering_side_veto(direction, entry, poc, should_veto):
    result = suffering_side_veto(
        {"direction": direction, "entry_price": entry},
        {"poc": poc}
    )
    if should_veto:
        assert result is not None
        assert result["gate"] == "suffering_side"
    else:
        assert result is None

def test_missing_fields():
    assert suffering_side_veto({"direction": "LONG"}, {"poc": 5740}) is None
    assert suffering_side_veto({"direction": "LONG", "entry_price": 5735}, {}) is None
```

---

## 7. Deployment Plan

### Phase 1: Observation Mode (Day 1-2)

Deploy the gate in **log-only** mode. It evaluates every setup but does NOT block:

```python
_ss_result = suffering_side_veto(setup, market_profile)
if _ss_result:
    logger.info(f"[SUFFERING_SIDE] Would veto: {_ss_result['reason']}")
    # Add to setup metadata for tracking
    setup_metadata["suffering_side_veto"] = _ss_result
    # But do NOT return blocked
```

**Monitor**:
- How many setups get flagged per day
- Compare flagged-setup outcomes vs non-flagged
- Verify no false positives on obviously good trades

### Phase 2: Hard Veto (Day 3+)

After reviewing 1-2 days of observation data:
- If block rate is 25-45% and blocked WR is worse → activate hard veto
- If block rate > 50% → too aggressive, add tolerance band (e.g., entry within 2pt of POC → pass)
- If WR difference < 3pp → gate doesn't add value, reconsider

### Rollback Plan

If gate causes problems:
1. Set `SUFFERING_SIDE_ENABLED=false` in environment
2. Or comment out gate call in `main.py`
3. No schema changes needed — it's a pure logic gate

---

## 8. Open Questions for Michael

1. **Tolerance band**: Should entries within 1-2 points of POC also be vetoed, or only strict below/above?
   - *Current spec*: strict comparison, entry == POC passes
   - *Alternative*: add 1pt buffer (entry must be >= POC + 1 for LONG to pass)

2. **Which POC**: Current day POC (`poc`) or developing POC (`tpo_poc`)?
   - *Current spec*: uses `poc` (day POC from market profile)
   - `tpo_poc` updates more frequently — might be more accurate but noisier

3. **Pre-market/overnight**: Should this gate apply outside RTH when POC isn't established yet?
   - *Current spec*: gate returns None (pass) if POC is missing/zero
