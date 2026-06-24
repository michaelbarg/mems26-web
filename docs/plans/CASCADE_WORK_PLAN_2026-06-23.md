# Work Plan — Restore the S1 → S2/S4 → Targets Cascade
### "fire in accordance with the day-type" — 2026-06-23

**Owner:** Cowork (plan) → CC (build per phase). **Risk:** trading-surface → **Michael sign-off per phase**,
flag-OFF default, SHADOW-validate, backtest the fire-set change. One phase at a time; strategic-stop at each gate.
**Grounded in:** `docs/reports/CASCADE_AUDIT_S1_S2_S4_2026-06-23.md` (root-causes R1–R6) + the 06-22 fires.

## Diagnosis in one line
The cascade breaks at the **joint**, not the parts. S1 classifies correctly; S2/S4 fire on pure geometry
**by design** (they don't consult day-type); the gate that should translate *day-type → allowed patterns* —
`DAYTYPE_PLAYBOOK.decide()` (`daytype_playbook.py:104`) — is a **dead no-op** (returns FULL for every pattern
while `DAYTYPE_POSITION_GATE=1`), and the gate that runs instead (`daytype_position_gate.py:36`) is
**pattern-blind**. Result: nothing enforces "fire in accordance with the day-type" → HFE reversals (191/193/194)
+ the REACTIVE fade-wall (197–212) fired on a directional Variation/`with_extension` day.

## Your model ↔ the gap ↔ the phase
| Your intent | Current reality | Gap (root-cause) | Phase |
|---|---|---|---|
| **S1** sets the day-type **and how to trade it** | S1 emits a day-type **label** only | the "how-to-trade" object isn't consumed by the firing gates (R5) | **P2** |
| **S2/S4** fire **only in accordance** with the day-type | playbook matrix is **dead** (R1); the live gate is **pattern-blind** (R2); Nontrend **orphaned** (R3) | no day-type→pattern enforcement | **P1** |
| **patterns** set targets per day-type **+ the opportunity** | targets per-day-type but **no opportunity/location dimension**; stops not day-type-driven (R6) | missing the opportunity axis | **P3** |

## The plan (dependency-ordered)

### Phase 0 — Foundation (mostly done — verify only)
- **Feed-fix #0** (CC) so the day-type isn't blinded by `v9_bars_5min` gaps [in progress].
- **Opening / dedup / width gates ON for the morning window** (R4): the flags were enabled 06-22 **17:22**,
  *after* the 08:30–10:20 fires — so 188/190 (counter-drive into OPEN_DRIVE) + 199/200 (double-fire) hit an
  un-gated surface. They're on now; **verify** they actually engage at 08:30 on a replay.
- S1 7-type classifier (`S1_ENGINE_NEW_CLASSIFIER`) — **KEEP** (06-22 day-type trustworthy).
- **Verify:** replay 06-22 with flags on → the un-gated morning fires are now blocked.

### Phase 1 — Restore the day-type → firing translation  ★ root fix, highest leverage
**Goal:** S2 **and** S4 fire ONLY in accordance with the day-type.
- **R1:** make `DAYTYPE_PLAYBOOK.decide()` actually evaluate `config/daytype_playbook.yaml` (stop returning FULL).
- **R2:** make it **pattern-aware** — classify each pattern *continuation* vs *reversal*; apply the day-type's
  allow / SKIP / REDUCED + `require_with_trend` (e.g. Trend / Variation-`with_extension` → SKIP counter-trend
  reversals like HFE / REACTIVE-fade).
- **R3:** close coverage — **every (day_type × pattern) has an explicit rule**; Nontrend owned, not default-allow.
- Route **both S2 and S4** through this one gate.
- **Files:** `daytype_playbook.py`, `config/daytype_playbook.yaml`, `gateway/trading_gateway.py`. **Flag:** restore
  `DAYTYPE_PLAYBOOK` as the live matrix (Michael sign-off — trading surface; **not** a standing-OFF, this is
  dead-wiring per the "wire the full pipeline" rule).
- **Verify:** matrix has **0 gaps**; replay 06-22 → HFE 191/193/194 + REACTIVE wall `blocked_by=daytype_playbook`;
  replay a clean **trend** day → continuation patterns **still fire**. Anti-tautological tests per CC contract.

### Phase 2 — S1 emits a "how-to-trade" object (not just a label)
**Goal:** one source of truth for "how to trade this day," consumed by **both** firing (P1) **and** targets (P3).
- **R5:** S1 exposes the `daytype_style`/mode object (bias, allowed-patterns, target-style, contracts, runner) at
  entry; the firing gate and the targets both read it. **Reconcile the contracts disagreement** (`daytype_style`
  vs `targets_table`: Variation 3 vs 2 — pick one source).
- **Files:** `day_type/*`, `trade_context.py`, `structural_targets.py`.
- **Verify:** a single mode object drives both surfaces; no divergent contracts.

### Phase 3 — Targets / stops per day-type **+ opportunity**
**Goal:** each fired pattern sets profit/loss targets per day-type **and** the trade's opportunity (location/room).
- **R6:** add the **opportunity/location dimension** to targets (scale by room to the next structural level /
  setup quality); make **stops day-type/opportunity-driven** (not only anchor/volatility); finish the
  per-pattern × day-type **stop/target table** (already a tracked TODO).
- **Files:** `services/trade_manager/*`, `structural_targets.py`, `config/stop_anchors.yaml` + the stop/target table.
- **Verify:** targets/stops differ correctly across day-type × location; **backtest the P&L effect**.

### Phase 4 — Verification per day-type (use the replay/brain-view tool)
**Goal:** confirm fires + targets match the characterization, per day-type.
- Replay each day-type's representative day through the replay tool (now real after CC's export) and assert:
  fires only the day-type-allowed patterns; targets/stops per the table. The four-UAT-axes discipline, applied
  to the cascade.

## Discipline (every phase)
Flag-gated default-OFF · SHADOW-validate · backtest the fire-set change · anti-tautological tests · Michael
sign-off (trading surface) · update `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md`. **Phase 1 first** — it's the
smallest correct root-fix and stops yesterday's misaligned fires.
