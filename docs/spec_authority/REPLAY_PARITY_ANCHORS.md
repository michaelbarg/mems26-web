# MEMS26 Replay Kernel — Parity Anchors

**Stage:** 0A acceptance fixtures (no kernel implementation yet).  
**Pinned code:** `cba369a1454749dfa8c8c1ed0f476db03b673926`  

**Flag pinning:** full `.env` hash is not an acceptance fixture (it contains
unrelated/local state and changed after the research run). Stage 0C must pin a
secret-free sorted snapshot of only effective detector/day-type flags and its
`detector_flags_hash`. Stage 0B validates data only.

Candidate hash input:

```text
sorted canonical JSON:
{bar_ts_utc_z, family, pattern, direction}
```

## A1 · 2026-08-18 — clean BALANCE control

- 78 SCID RTH bars · 0 seams · 78/78 close-match.
- `Variation`; structural context stays BALANCE on all 67 determined bars.
- CVD: 90 unique rows · 0 conflicts.
- CURRENT_ALL candidates: **15**.
- Candidate hash:
  `3a0f215204fda29e27139ccd2284458cb33543dde5804f578f8f180a262eeea8`
- MAX_CONTEXT candidates: **1**.
- Candidate hash:
  `c8cb8d52f84ccfa4ccbecb6ac1eeb44e25abba8e2a7568a747e77a080d313233`
- Legacy execution baseline: current **5 / −$54.38**; max **1 / +$118.50**.
- Stage 0B expected data status: **PASS**.
- Candidate/execution hashes: **Stage 0C, not verified by Stage 0B**.

## A2 · 2026-08-17 — Trend_DD discovery down

- Live/entry/post-hoc all `Trend_DD`.
- Replay context: 64 `DISCOVERY:DOWN`, 3 BALANCE.
- CURRENT_ALL: **24**,
  `404a91530a29a47c19bdafaa146ad6db28f957a900959ce7ef8c8ea4566674df`.
- MAX_CONTEXT: **2**,
  `ecc098fa994fbebb311748b0736e560af1806e961ab18bdc97004064a52855db`.
- Execution: current **8 / −$535.12**; max **1 / +$11.62**.
- Stage 0B data status: **PASS**; full parity deferred to 0C.

## A3 · 2026-08-20 — Neutral / dual-IB-break

- IB high breaks 11:00 ET; IB low 11:40.
- structural replay emits `dual_ib_break` on 11:45 closed bar and stays BALANCE.
- CURRENT_ALL: **28**,
  `1e7bea8ae84c6db616eb9cffb57b1982737b537fd6bc9cd79e7479f745d389fd`.
- MAX_CONTEXT: **4**,
  `6e6bb14bf2c2368bc5bd800dc40fd8d13bdf4cab26e466fac43024bd729a284f`.
- Execution: current **10 / −$845.63**; max **2 / −$64.88**.
- CVD duplicate groups are identical values and must collapse deterministically.
- Stage 0B data status: **PASS**; full parity deferred to 0C.

## A4 · 2026-07-15 — intentional DB/SCID failure

- DB = 60 bars; SCID = 78; 0 SCID seams.
- Current validator close-match = 1/78.
- Legacy forensic candidates: 14,
  `5bf79e7599ea49f3ec35e67e404600e82d0fc813a1678fdea43ed3dcc6703fa4`.
- Expected kernel status:
  **NOT_JUDGEABLE** with at least `RTH_CARDINALITY`,
  `RTH_GRID_MISMATCH`, `SCID_TIMESTAMP_MISMATCH`.
- Current validator also correctly reports `CVD_CONFLICTS`,
  `SCID_OHLC_MISMATCH`, `SCID_VOLUME_MISMATCH`; close-match 1/78 is a metric,
  not a reason code.
- Candidate/P&L output is forbidden until T-99 repair.

## A5 · 2026-07-14 — intentional TPO/CVD causality failure

- OHLC control: 78 bars, 0 seams, 78/78 close-match.
- nominal TPO selection would consume future-created rows on 73/78 bars.
- `available_at` selection must produce **0** future reads.
- CVD: 24 conflicting timestamps, 54 conflicting rows, max spread 7,464.
- CVD hash changed across two identical read-only queries because `ORDER BY ts`
  cannot order conflicts.
- Expected kernel status: **NOT_JUDGEABLE / CVD_CONFLICTS**.
- Current full validator additionally finds one OHLC and one volume mismatch;
  both are valid fail-closed reasons.
- Existing candidate hash is forensic only and must not become golden.

## Required assertions

### Green anchors (A1–A3)

- data quality passes;
- Stage 0B: source hashes and quality metrics repeat deterministically.
- Stage 0C: candidate hash/count, context events, policy reasons and execution
  P&L match the pinned legacy scenario.

### Red anchors (A4–A5)

- fail closed with exact reason code;
- no headline P&L;
- no silent exclusion;
- repair is considered complete only when the same fixture turns green through
  validated DB data, not source substitution.

## Caveat

`FIRE_MATRIX_ALL_DAYS.md` “DB Match” currently validates close within 0.5pt,
not full timestamp/OHLCV parity. Green kernel fixtures require full timestamp,
OHLC and volume checks.

Stage 0B stores TPO `market_ts` and `available_at`; it does **not** yet run a
policy that selects levels. Zero future TPO consumption is a Stage 0C
Context/Policy assertion.
