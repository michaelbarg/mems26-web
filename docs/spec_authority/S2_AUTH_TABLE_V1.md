# S2 Authority Table V1

**Status:** 🔒 LOCKED · 2026-05-25 12:22 IL (Michael chat approval)
**File:** `docs/spec_authority/S2_AUTH_TABLE_V1.md`
**Authority:** Michael Barg
**Source:** Michael Auth Table sent in chat 25/5 11:50 IL
**Consumed by:** Pkg 8 (Quality V2) · `backend/v9/systems/five_min/quality_tier.py` rewrite
**Replaces (partial):** Constitution V3 §Layer 2 Quality Tier (`HIGH=3 · MEDIUM=2 · LOW=1` — superseded by this per-pattern × per-day_type table)
**Scope:** D-095 Path A · 10 existing PatternName values only · 6 future patterns deferred to Pkg 5d/5e

---

## 1 · Decisions captured (Michael chat 25/5)

| Q | Decision | Implication |
|---|---|---|
| Q1 · "OFA Core *" disposition | **α · Umbrella row · ignored** | Sizing for OFA family comes from rows 12-15 (Reactive Long/Short + Initiative Long/Short) only. No new PatternName added. |
| Q4 · H&S + Inv H&S sizing | **Same sizing both (default · per chat row 8 combination)** | `INVERSE_HNS_LONG` and `HNS_TOP_SHORT` use identical row · pending Michael formal confirmation on spec review |
| Q6 · Max contracts | **q · cap at 3 · ×0.75 + round half-up** | `4→3 · 3→2 · 2→2 · 1→1 · 0→0` |
| Typo · Bull Flag NeuC LOW | **t1 · typo · use 0/0/0** | Source said `0/0/2` · corrected per Michael 25/5 12:11 |
| Audit alignment · 4 dead cells | **B · Zero out · align with detector gates** | H&S TDD · Double TN · Double TDD · Initiative Norm → all ❌ 0/0/0 · per Michael 25/5 12:20 |

---

## 2 · Pattern scope (Path A · D-095)

### IN scope (10 PatternName values · live in `output_schema.py`)

`REACTIVE_LONG · REACTIVE_SHORT · INITIATIVE_LONG · INITIATIVE_SHORT · INVERSE_HNS_LONG · HNS_TOP_SHORT · DOUBLE_BOTTOM_EE_LONG · DOUBLE_TOP_AA_SHORT · BULL_FLAG_LONG · BEAR_FLAG_SHORT`

### DEFERRED (6 patterns · not in code · Pkg 5d/5e queue)

`Pennant · Triangle Asc/Desc · Triangle Sym (BUST) · Cup & Handle · Wedge · Wyckoff Spring`

Reason: no detector exists in `backend/v9/systems/five_min/patterns/` for these. Auth Table sizing for them is captured in Michael's source table (chat 25/5 11:50) for future use, but not encoded in Pkg 8.

---

## 3 · Day-type mapping (verbatim from `DayType` enum)

| Short | DayType enum | Notes |
|---|---|---|
| TN | `Trend_Normal` | |
| TDD | `Trend_DD` | |
| NeuE | `Neutral_Extreme` | D-091.Q1 lock · 45min · open at VA edge |
| NV | `Variation` | "Normal Variation" in Michael's table |
| NeuC | `Neutral_Center` | D-091.Q1 lock · 30min · open inside VA |
| Norm | `Normal` | |
| NT | `Nontrend` | EXIT_V6 + D-091 · global NO_TRADE |

**`Neutral` (deprecated enum) and `UNKNOWN`** → not in Auth Table · treated as fallback (see §6).

---

## 4 · Lookup table (final · post-transformation)

Format: `(HIGH / MEDIUM / LOW)` contracts · prefixed by verdict (✅ full / ⚠️ reduced / ❌ skip).

### OFA · Reactive

| PatternName | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| `REACTIVE_LONG` | ⚠️ 2/1/0 | ⚠️ 2/1/0 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ❌ 0/0/0 |
| `REACTIVE_SHORT` | ⚠️ 2/2/0 | ⚠️ 2/2/0 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ❌ 0/0/0 |

### OFA · Initiative

| PatternName | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| `INITIATIVE_LONG` | ✅ 3/2/1 | ✅ 3/2/1 | ❌ 0/0/0 | ✅ 3/2/1 | ❌ 0/0/0 | ❌ 0/0/0 *(audit B)* | ❌ 0/0/0 |
| `INITIATIVE_SHORT` | ✅ 3/2/1 | ✅ 3/2/1 | ❌ 0/0/0 | ✅ 3/2/1 | ❌ 0/0/0 | ❌ 0/0/0 *(audit B)* | ❌ 0/0/0 |

### H&S (`INVERSE_HNS_LONG` + `HNS_TOP_SHORT` · identical row · pending Michael formal confirm on spec review)

| PatternName | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| `INVERSE_HNS_LONG` | ❌ 0/0/0 | ❌ 0/0/0 *(audit B)* | ✅ 3/2/1 | ⚠️ 2/1/0 | ✅ 3/2/1 | ✅ 3/2/1 | ❌ 0/0/0 |
| `HNS_TOP_SHORT` | ❌ 0/0/0 | ❌ 0/0/0 *(audit B)* | ✅ 3/2/1 | ⚠️ 2/1/0 | ✅ 3/2/1 | ✅ 3/2/1 | ❌ 0/0/0 |

### Double

| PatternName | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| `DOUBLE_BOTTOM_EE_LONG` | ❌ 0/0/0 *(audit B)* | ❌ 0/0/0 *(audit B)* | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ❌ 0/0/0 |
| `DOUBLE_TOP_AA_SHORT` | ❌ 0/0/0 *(audit B)* | ❌ 0/0/0 *(audit B)* | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ✅ 3/2/2 | ❌ 0/0/0 |

### Flag

| PatternName | TN | TDD | NeuE | NV | NeuC | Norm | NT |
|---|---|---|---|---|---|---|---|
| `BULL_FLAG_LONG` | ✅ 3/2/2 | ✅ 3/2/2 | ⚠️ 2/2/0 | ✅ 3/2/2 | ❌ 0/0/0 *(typo fix)* | ⚠️ 2/2/0 | ❌ 0/0/0 |
| `BEAR_FLAG_SHORT` | ✅ 3/2/2 | ✅ 3/2/2 | ⚠️ 2/2/0 | ✅ 3/2/1 | ❌ 0/0/0 | ⚠️ 2/1/0 | ❌ 0/0/0 |

---

## 5 · Transformation audit · Michael source → final

Each cell scaled by `× 0.75` (cap 3 instead of 4), then rounded half-up. Source from Michael chat 25/5 11:50.

| Source value | Scaled (×0.75) | Final (half-up) |
|---|---|---|
| 4 | 3.00 | **3** |
| 3 | 2.25 | **2** |
| 2 | 1.50 | **2** |
| 1 | 0.75 | **1** |
| 0 | 0.00 | **0** |

**Verdict (✅/⚠️/❌) is preserved verbatim** — only the contract numbers are scaled.

### Sanity check · totals

- Source max: `4 contracts` (e.g., OFA Core / Bull Flag TN)
- Final max: `3 contracts` (matches Constitution V3 §Layer 2 cap pre-Auth-Table)
- Source min (non-zero): `1 contract`
- Final min (non-zero): `1 contract`

---

## 5.1 · Audit alignment · live code gate cross-check (Michael 25/5 12:20)

Cursor cross-checked the V1 Auth Table against `backend/v9/systems/five_min/five_min_system.py` day-type gates (`lines 665-704`) and D-091 §"Coverage Matrix" (lines 33-50). 4 cells were found to allocate non-zero contracts to (pattern × day_type) combinations that the live detector cannot reach. Per Michael's choice of option B (25/5 12:20 chat), these are zeroed out to match the detector gates · clean alignment, no dead cells.

| # | Cell | Pre-audit value | Post-audit value | Reason |
|---|---|---|---|---|
| 1 | `INVERSE_HNS_LONG` × TDD | ⚠️ 2/1/0 | ❌ 0/0/0 | Detector gate (line 683-686) excludes TDD · D-091 line 35 lists NeuE/NeuC/Norm/NV only |
| 2 | `HNS_TOP_SHORT` × TDD | ⚠️ 2/1/0 | ❌ 0/0/0 | Same gate · D-091 line 36 mirrors line 35 |
| 3 | `DOUBLE_BOTTOM_EE_LONG` × TN | ⚠️ 2/1/0 | ❌ 0/0/0 | Gate excludes TN · D-091 line 37 lists NV/NeuE/NeuC/Norm only |
| 4 | `DOUBLE_BOTTOM_EE_LONG` × TDD | ⚠️ 2/1/0 | ❌ 0/0/0 | Gate excludes TDD · D-091 line 37 |
| 5 | `DOUBLE_TOP_AA_SHORT` × TN | ⚠️ 2/1/0 | ❌ 0/0/0 | Gate excludes TN · D-091 line 38 |
| 6 | `DOUBLE_TOP_AA_SHORT` × TDD | ⚠️ 2/1/0 | ❌ 0/0/0 | Gate excludes TDD · D-091 line 38 |
| 7 | `INITIATIVE_LONG` × Norm | ⚠️ 2/2/0 | ❌ 0/0/0 | D-091 line 33 lists TN/TDD/NV only · Auth Table is the sizing gate (detector itself ungated) |
| 8 | `INITIATIVE_SHORT` × Norm | ⚠️ 2/2/0 | ❌ 0/0/0 | D-091 line 34 mirrors line 33 |

### Forward compatibility note (post-LIVE)

If future SHADOW/LIVE evidence shows that a deferred detector gate expansion is profitable (e.g., H&S firing on TDD with reduced size), the corresponding Auth Table cells can be reactivated. The original Michael source values (Auth Table chat 25/5 11:50) are preserved in §12 audit trail for that purpose. **No silent fallback** — explicit decision required to re-enable.

---

## 6 · Special cases · `quality_tier.py` semantics

### 6.1 NT (Nontrend) day = global skip

If `current_day_type == "Nontrend"` → **all patterns return `(verdict='SKIP', contracts=0)`**.

This is consistent with EXIT_V6 + D-091 NT NO_TRADE gate (Pkg 3a Stream 2 already wires NT as `no_trade=True` in `targets_table`). Auth Table entry is **redundant defense in depth** at sizing layer.

### 6.2 Verdict semantics

- **✅ Full** → use HIGH/MEDIUM/LOW per quality tier classification
- **⚠️ Reduced** → use HIGH/MEDIUM/LOW per quality tier · sizes already reduced in table (no extra penalty)
- **❌ Skip** → return `(verdict='SKIP', contracts=0)` for the cell · the setup is NOT FIRED (caller short-circuits in `setup_emitter.py`)

### 6.3 Quality tier source (unchanged from V1)

Quality tier (HIGH/MEDIUM/LOW) still comes from S5 TPO location (proximity to POC/VAH/VAL). Unchanged from current `quality_tier.py` lines 35-53.

### 6.4 Unknown day_type / missing day_type

If `current_day_type is None` OR `current_day_type in ("UNKNOWN", "Neutral_legacy")`:
- Default to **`Neutral_Center` row** (matches D-091.Q1 fallback for legacy `Neutral` enum → `Neutral_Center`)
- Log `WARN` to cross_context (no silent failure per pre-LIVE protocol)

### 6.5 Unknown pattern_name

If `pattern_name not in PatternName Literal`:
- Raise `ValueError` (no silent fallback · consistent with `contract_split.get_contract_split()` at `contract_split.py:46-48`)

---

## 7 · API signature (proposed)

```python
# backend/v9/systems/five_min/quality_tier.py (V2 rewrite)

from typing import Literal, Tuple, Optional

QualityVerdict = Literal['FULL', 'REDUCED', 'SKIP']
QualityTier = Literal['HIGH', 'MEDIUM', 'LOW']


def get_quality_tier_v2(
    pattern_name: str,
    day_type: str,
    price: float,
    *,
    tpo_data: Optional[dict] = None,
) -> Tuple[QualityVerdict, QualityTier, int]:
    """Return (verdict, tier, contracts) for the (pattern × day_type × tier) cell.

    Args:
        pattern_name: PatternName Literal value (e.g., 'BULL_FLAG_LONG')
        day_type: DayType enum value (e.g., 'Trend_Normal')
        price: current price for TPO proximity classification
        tpo_data: optional TPO snapshot (defaults to S5 /api/v9/tpo/current fetch)

    Returns:
        (verdict, tier, contracts):
            verdict ∈ {'FULL', 'REDUCED', 'SKIP'}
            tier    ∈ {'HIGH', 'MEDIUM', 'LOW'}
            contracts ∈ {0, 1, 2, 3}

    Raises:
        ValueError if pattern_name not in PatternName Literal.
    """
```

### Backward compat

- Old `get_quality_tier(price, tpo_data=...)` → keep as thin wrapper that:
  - Returns tier+contracts only (V1 signature)
  - Uses `day_type='Neutral_Center'` and `pattern_name=None` (fallback to V1 logic)
  - Emits `DeprecationWarning`
- Callers migrated to V2 in Pkg 6 (TradeManager extensible).

---

## 8 · Constitution V3 update required

Constitution V3 §Layer 2 says verbatim:
> HIGH (3 contracts) · MEDIUM (2 contracts) · LOW (1 contract)

This is **no longer the source of truth**. With Auth Table V1:
- Max contracts remains 3 (Q6=q cap)
- But sizing is now (pattern × day_type × tier) → 0-3 contracts · not a flat tier mapping

**Action:** add Constitution V3 amendment note (or new §Layer 2.1) pointing to `S2_AUTH_TABLE_V1.md` as the operative source for contract sizing. Cursor will draft after Michael approves this DRAFT.

---

## 9 · Test plan (Pkg 8 G3 criteria · for CC handoff)

### 9.1 Coverage tests

1. **All 70 entries covered** · `len(_AUTH_TABLE_V1) == 10 patterns × 7 day_types == 70`
2. **All verdicts in {FULL, REDUCED, SKIP}**
3. **All contract values in {0, 1, 2, 3}**
4. **NT row global zeros** · `all(cell.contracts == 0 for cell in pattern_row['Nontrend'] for pattern in PatternName)`
5. **PatternName Literal coverage perfect** · `set(_AUTH_TABLE_V1.keys()) == set(get_args(PatternName))`

### 9.2 Behavior tests (per cell · ~30 representative)

- 10 ✅ cells · verify (verdict='FULL', contracts=N) per tier
- 10 ⚠️ cells · verify (verdict='REDUCED', contracts=N)
- 10 ❌ cells · verify (verdict='SKIP', contracts=0) regardless of tier

### 9.3 Edge cases

- Unknown `pattern_name` → `ValueError` raised
- Unknown `day_type` → falls back to `Neutral_Center` row + `WARN` log
- `tpo_data=None` → fetch from S5 endpoint · fail-safe to `MEDIUM` tier per V1 behavior
- All POC/VAH/VAL inputs `None` → fail-safe to `MEDIUM` tier

### 9.4 Regression tests

- All 3 existing `test_quality_tier.py` tests still PASS (with V1 wrapper)
- Full suite `pytest tests/v9/ -q` shows zero new failures

---

## 10 · Forbidden zones (Pkg 8 CC scope · forward-looking)

CC must NOT touch:
- `backend/v9/systems/five_min/contract_split.py` (Pkg 3c · emit-only · separate concern)
- `backend/v9/systems/five_min/adaptive_stop.py` (Pkg 1 · stop sizing)
- `backend/v9/services/trail_engine.py` (Pkg 3b-3)
- `backend/v9/services/trade_manager/manager.py` (reserved for Pkg 6)
- Day type system files
- DLL / frontend / DB schema

CC MAY touch:
- `backend/v9/systems/five_min/quality_tier.py` (rewrite)
- `backend/v9/systems/five_min/auth_table_v1.py` (NEW · const dict)
- `backend/v9/systems/five_min/setup_emitter.py` (minimal · pass `pattern_name` + `day_type` into quality_tier call)
- `tests/v9/systems/test_five_min/test_quality_tier.py` (expand)
- `tests/v9/systems/test_five_min/test_auth_table_v1.py` (NEW)

---

## 11 · Open questions before LOCK

| # | Question | Default | Action |
|---|---|---|---|
| 1 | H&S + Inv H&S same sizing? | Yes (Michael's row 8 combines them) | ⏳ Michael confirm in review · default proceeds |
| 2 | Does Auth Table override Constitution V3 §Layer 2? | Yes (per Q6 implicit) | ⏳ Michael confirm + Cursor drafts Constitution V3 §Layer 2.1 amendment |
| 3 | Final table (§4 post-audit) matches your intent? | (review) | ⏳ Michael review · flag any cell that's wrong |
| 4 | Approve LOCK as `S2_AUTH_TABLE_V1.md`? | (pending) | Rename on approval · Cursor proceeds to Pkg 8 handoff for CC |
| Audit-1 | Option B applied to 8 cells? | Yes (Michael 25/5 12:20) | ✅ DONE 25/5 12:?? · §5.1 documents the alignment |

---

## 12 · Audit trail

| Date | Event |
|---|---|
| 2026-05-23 17:30 | V2 plan added Pkg 8 (Quality V2) · noted Auth Table dependency · spec source TBD |
| 2026-05-25 11:18 | D-095 locked · 4a+4b deferred · Pkg 8 promoted to NEXT · BLOCKED on Auth Table from Michael |
| 2026-05-25 11:50 | Michael sent raw Auth Table (15 patterns · 7 day types · 4/3/2/1/0 contracts) |
| 2026-05-25 11:54 | Michael selected Path A (10 existing patterns only · defer 6 future) |
| 2026-05-25 11:59 | Michael answered Q1=α (OFA Core umbrella ignored) · Q6=q (cap max=3) · Q4="b" (ambiguous) |
| 2026-05-25 12:06 | Michael confirmed rounding rule = half-up (`(i)`) |
| 2026-05-25 12:11 | Michael confirmed typo · Bull Flag NeuC LOW=2 → 0 |
| 2026-05-25 12:16 | DRAFT v1 written · Michael requested audit vs live code before formal LOCK |
| 2026-05-25 12:20 | Cursor audit found 4 dead cells (H&S TDD · Double TN · Double TDD · Initiative Norm) · Michael chose option B (zero out · align with gates) |
| 2026-05-25 12:21 | DRAFT v2 written with §5.1 audit alignment + 8 cells zeroed (2 H&S + 4 Double + 2 Initiative) |
| 2026-05-25 12:22 | **🔒 LOCKED** · Michael approved all 4 open questions (§11) · renamed `S2_AUTH_TABLE_V1_DRAFT.md` → `S2_AUTH_TABLE_V1.md` · Constitution V3 §Layer 2 + §Entry amendment queued |
