# item-11 — sizing consolidation: work plan (audited 2026-07-05)

Grounded in the actual code (Rule 2), not the prompt's assumptions.

## Rule-2 correction to the prompt
The prompt said "~5 files incl. decision_tree.py + stop_anchors/sizing.py". Actual:
- **3 legacy `calculate_size` definitions:** `woodies_system.py:1197` (S4) ·
  `footprint_system.py:383` (S3 — **MUTED/dead**, S3_MUTE) · `five_min_system.py:938` (S2).
- **4 live call sites:** woodies :573, :983 · footprint :439 (dead) · five_min :1336.
- `stop_anchors/sizing.py` is NOT legacy — it's the **V2 authority**
  (`compute_v2_sizing`); `get_quality_tier_v2` (`quality_tier.py:70`) is the S2 V2.
  `decision_tree.py` has no `calculate_size` call.
- **The real culprit is not the NUMBER — it's the S4 `"reject"` branches.**
  `woodies_system.py` sets `sizing = "reject"` in ~9 places (546, 641, 645, 709,
  713, 725, 726, 761, 767) — risk-cap / geometry vetoes that block a fire from
  INSIDE the detector, independent of V2 and the gateway. That's the "A5 reject
  while V2 said 3" symptom. Under `FIXED_CONTRACTS_3=1` the number is masked, but
  the reject-veto still kills fires silently.

## The fix in one line
One sizing AUTHORITY (V2) for the number; the S4 risk-cap "reject" becomes an
EXPLICIT gateway `blocked_by`, never a swallowed in-detector veto.

## Phased plan (all reversible)
**Phase 0 — audit + freeze (paste raw, Rule 5).** grep every `calculate_size`
call + every S4 `"reject"` branch; classify KEEP/ADAPT/REPLACE/DEAD; mark which
run at runtime vs dead import.

**Phase 1 — classify (expected):**
- S3 footprint :383/:439 → **DEAD** (S3 muted) — remove or shim, no behavior change.
- S2 five_min :938/:1336 → **ADAPT** — route the number through `get_quality_tier_v2`.
- S4 woodies :1197/:573/:983 → **REPLACE** the number with V2; **SEPARATE** the
  `"reject"` risk-cap logic out of sizing.

**Phase 2 — single number authority.** `calculate_size` → thin shim delegating to
V2 (or removed at dead sites). Prove: under `FIXED_CONTRACTS_3=1`, contracts == 3
at every source, **before == after** (paste the diff).

**Phase 3 — reject → explicit gateway veto.** Move the S4 risk-cap rejects to a
logged gateway `blocked_by = "s4_risk_cap"` (no silent failures). A sizing module
must not veto a fire the gateway approved.

**Phase 4 — guard I-58.** Confirm no legacy sizing path re-introduces an unmapped
FillPoller "most-recent-active" close (the demo-only fallback stays demo-only).

**Phase 5 — tests (anti-tautological, fail-on-old):**
1. A fire the legacy path would `reject` but V2 approves → routes after the fix.
2. `FIXED_CONTRACTS_3=1`: contract count == 3 at every sizing source, before==after.
3. No unmapped/unrelated close path survives.

**Phase 6 — flag-gate.** If any live number/verdict changes →
`SIZING_CONSOLIDATION_V1` default-OFF + strategic-stop for Michael. If provably a
pure no-op under `FIXED_CONTRACTS_3=1` → may land un-flagged WITH the before/after proof.

**Phase 7 — close-out.** `gen_index` + `gen_flag_index` if structure/flags change;
STATUS_BOARD + ROADMAP + MICHAEL_ISSUES_LEDGER (item-11 row) with finding+fix+raw
verification; restart via kickstart (0 open first); mandatory NOT-DONE section.

## Phase 0 — AUDIT RESULT (done 2026-07-05, read-only)
Both per-system sizers return a STRING verdict `'full'(3) | 'half'(2) | 'reject'(0)`
— i.e. the fire-VETO is embedded in the sizing function in BOTH systems:
- **S4** `woodies_system.py:1197` — 'reject' on tier/SWI/CZI/TCCI/LSMA/EMA34
  misalignment + the ~9 risk-cap reject branches (540-770). Call sites :573, :983.
  → **REPLACE** the number with V2; **SEPARATE** every 'reject' into an explicit
  gateway veto.
- **S2** `five_min_system.py:938` — 'reject' on `bars_formed<3` (maturity) + COT/AMT
  alignment (already bypassed by the S2⟂S3 standing decision). Call site :1336.
  → **ADAPT** to V2 for the number; keep maturity as an explicit early veto.
- **S3** `footprint_system.py:383/439` — S3 muted (S3_MUTE) → **DEAD**, remove/shim.
Confirmed authority: `get_quality_tier_v2` (S2) + `compute_v2_sizing` (S4).
Conclusion: consolidation = split "how many contracts" (→ V2, one authority) from
"should we fire at all" (→ explicit gateway `blocked_by`, no in-sizer reject).

## Owner + guardrail
Owner: Claude Code (real trading-risk-surface refactor). This does NOT block the
Monday DEMO validation of item-4/22/6 — it can land in parallel, flag-gated. Do
NOT touch the deferred items (12/13/16/17/7/8).
