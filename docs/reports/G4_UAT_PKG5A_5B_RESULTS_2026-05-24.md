# G4 UAT Results · Pkg 5a + 5b · 2026-05-24

## Axis Results

| Axis | Status | Details |
|------|--------|---------|
| 1 Quality | PASS | 32/32 golden tests (16 H&S + 16 Double BT) |
| 2 Recency | KNOWN GAP | `setup.ts` uses `datetime.now(timezone.utc)` at line 771 (not bar timestamp). See Gaps section. Integration tests pass at detector level (pattern fires correctly). |
| 3 Cardinality | PASS | All 4 chart patterns fire exactly once. Follow-up bars do not re-trigger (buffer shifts away from pattern shape). |
| 4 Latency | PASS | p50=7.90ms, p95=11.08ms, p99=39.85ms (well within 50ms/80ms budget) |

## Gaps Found

### Gap 1 · Axis 2 Recency (KNOWN · deferred)

`backend/v9/systems/five_min/five_min_system.py:771` writes `ts=datetime.now(timezone.utc)` to `V9FiveMinSetup` instead of using the bar's timestamp. This means the persisted setup timestamp reflects wall-clock time, not the bar's closing time.

**Impact:** SHADOW analysis that correlates setup timing with bar timing will see a small delta (typically <1s in production, up to minutes on replay/backtest). Not blocking for SHADOW soak (setups still fire correctly), but should be fixed before LIVE.

**Proposed fix:** Replace `ts=datetime.now(timezone.utc)` with `ts=datetime.fromtimestamp(bar.get("ts", 0), tz=timezone.utc)` — requires modifying `five_min_system.py` (sealed Pkg 5a/5b code).

**Decision deferred to Michael:** apply as separate hotfix Pkg or bundle into Pkg 6 TradeManager rewrite.

## Hotfix Proposals (pending Michael approval)

1. **Recency fix** — 1-line change at `five_min_system.py:771`. Low risk. Modifies sealed 5a/5b code.

## Regression Check

- Pre-G4 baseline: 682 passed, 1 skipped
- Post-scaffolding: 686 passed, 1 skipped (+4 new integration tests)
- Delta: +4 new, 0 regressions

## Verdict

- [x] G4 PENDING · 1 known gap (Recency line 771) · awaiting Michael approval on hotfix
- Axes 1 (Quality), 3 (Cardinality), 4 (Latency): all GREEN
- Axis 2 (Recency): KNOWN GAP at DB persistence layer (detector logic correct)
