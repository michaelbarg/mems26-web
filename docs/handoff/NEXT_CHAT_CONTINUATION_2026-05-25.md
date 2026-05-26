# Next Chat Continuation · 2026-05-25 (PM)

**For:** the next Cursor agent picking up MEMS26 Pre-LIVE Pipeline V2.
**Drafted by:** Cursor agent · 2026-05-25 14:00 IL.
**Read time:** ~5 min. **Time to first action:** ~10 min after reading.

---

## §0 · TL;DR (read this first · 30 seconds)

You are mid-pipeline on MEMS26 V9 → LIVE futures trading. **Phase A code
is COMPLETE — every package G3 PASS GREEN**. The pipeline has shifted
from "build + G3 review" to "**G4 UAT execution + final package (Pkg 6)
+ frontend sync + SHADOW gate**".

**Phase A G3 status (all GREEN as of 25/5):**
- Pkg 0, 1, 2a, 2bc ✅
- Pkg 3a Stream 1, 1.5, 2 ✅
- Pkg 3b Stream 1 ✅ · Stream 2 (🔴 strategic stop · **superseded by 3b-3**) · Stream 3 ✅ · Stream 3.1 ✅
- Pkg 3c ✅
- Pkg 4a + 4b · **DEFERRED via D-095** (scope absorbed into 3b-3)
- Pkg 5a, 5b, 5c ✅
- Pkg 8 ✅
- Pkg 6 · LAST · deps ALL G4 ⬜

**What's actually pending** (in priority order):
1. **Axis 2 Recency decision** for Pkg 5a/5b (Michael's call — 4 options)
2. **G4 UAT execution** — smoke trades for every Phase A package (Michael executes · you assist)
3. **Frontend strategy decision** — Cursor recommends Option D-then-B (~30 LOC minimal sync)
4. **Pkg 6 spec work** — TradeManager extensible · starts AFTER all G4s green
5. **Open question carry-overs** (Pipeline 2/3/4/5 · Michael blockers · do NOT touch without Michael)

**Source of truth: §1.** **What to do first: §2.** **Open decisions: §6.**

---

## §1 · Source of truth · ALWAYS read these before acting

| Authority tier | Document | Status |
|---|---|---|
| 1 · Mandatory rules | `.cursor/rules/mems26-pre-live-protocol.mdc` | LOCKED — re-read at start of every session |
| 1 · Mandatory rules | `.cursor/rules/mems26-stability.mdc` | LOCKED — bridge local-only · no LaunchAgent changes |
| 1 · Mandatory rules | `CLAUDE.md` | LOCKED — Sierra source authority · polling floors · reporting workflow |
| 2 · Live status | `docs/plans/STATUS_BOARD.md` | LIVE — updated 2026-05-25 13:55 IL · all Phase A G3 GREEN |
| 2 · Pipeline plan | `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` V2 | LOCKED · partially superseded by D-095 (Pkg 4a/4b defer) |
| 3 · Decision docs (LOCKED) | `docs/decisions/D-091_S2_LIVE_SCOPE.md` | patterns + day type + contract distribution |
| 3 · Decision docs (LOCKED) | `docs/decisions/D-092_S4_WOODIES_UPDATE.md` | S4 patterns + thresholds (Pipeline 2 spec) |
| 3 · Decision docs (LOCKED) | `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` | Pkg 3b trail + Layer 4 wiring · 22 sub-locks |
| 3 · Decision docs (LOCKED) | `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md` | **NEW · 25/5 11:18** · Pkg 4a/4b DEFERRED · scope absorbed by 3b-3 |
| 3 · Decision docs (OPEN) | `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` | Q1 (Gateway canonical) + Q2 (DEMO acct) — Michael TODO |
| 4 · Mega-prompts (history · executed) | `docs/handoff/MEGA_PROMPT_PKG3B_STREAM2.md` | strategic stop in 23c8456 · superseded by Stream 3 |
| 4 · Mega-prompts (history · executed) | `docs/handoff/MEGA_PROMPT_PKG3B_STREAM3.md` | executed in `1e01c4a` · G3 PASS |
| 4 · UAT prep | `docs/handoff/G4_UAT_PKG5A_5B_PREP.md` | 4-axis spec · scaffolding G3 PASS · Axis 2 Recency decision pending |
| 5 · G3 PASS reports (recent) | `docs/reports/PKG3B_STREAM1_G3_PASS_2026-05-24.md` · `PKG3C_G3_PASS_2026-05-24.md` · `PKG8_G3_PASS_2026-05-25.md` · `G4_UAT_PKG5A_5B_SCAFFOLDING_G3_PASS_2026-05-24.md` | proof of GREEN |

**Sierra DLL contract:** `sc_study/v9_woodies_export.h` (read-only).
**Spec authority:** `docs/spec_authority/S2_EXIT_DEFINITION_V6.md`, `docs/spec_authority/S2_AUTH_TABLE_V1.md`, `docs/spec_authority/S4_WOODIES_*.csv/xlsx`.

---

## §2 · Immediate next task

### Recommended flow (Cursor opinion):

**Step 1 · Resolve §6.1 Axis 2 Recency (~5 min — needs Michael lock)**

Block: `backend/v9/systems/five_min/five_min_system.py:771` uses
`datetime.now(timezone.utc)` instead of `bar.get("ts")`. Confirmed gap
from G4 UAT scaffolding G3 review. Michael skipped the decision on 24/5
20:50 IL — re-surface and get a lock.

**Step 2 · Frontend audit (~30 min — diagnostic only · no code)**

Look at the M `.tsx` files in working tree at session start (ChartArea,
ChartV5a, WoodiesCciPanel, SidePanel, TopBar, Switcher, FiveMinPill,
FootprintPill, WoodiesPill, etc.) and classify each:
- KEEP — change unrelated to new patterns · skip
- ADAPT — needs new pattern names · queue for §6.2 minimal sync
- REPLACE — broken · prioritize
- DEFER — purely Phase B feature work · skip

Output: `docs/reports/FRONTEND_AUDIT_2026-05-25.md` (one row per file ·
~30 LOC report).

**Step 3 · §6.2 Frontend minimal sync (~45 min — code · ~30 LOC)**

Per Cursor recommendation Option B:
- pattern label map (INVERSE_HNS_LONG / HNS_TOP_SHORT / DOUBLE_BOTTOM_EE_LONG / DOUBLE_TOP_AA_SHORT / BULL_FLAG_LONG / BEAR_FLAG_SHORT → display strings)
- NeuE / NeuC split in `DayTypePill.tsx`
- That's it. No trail visualization · no MFE peak · no chandelier badge · no Layer 4 events journal (all Phase B).

**Step 4 · Help Michael execute G4 UATs (~variable)**

The G4 UAT queue is in §3. You don't EXECUTE the smoke trades (Michael
does · he holds Sierra DEMO + has the bridge running). You support:
- Pre-flight: confirm fixtures + expected outcomes per the UAT prep doc
- Post-flight: read CC output / DB / logs · verify the 4 axes (Quality / Recency / Cardinality / Latency)
- Document: write `docs/reports/G4_UAT_<pkg>_RESULTS_<date>.md` per the §5 acceptance criteria

**Step 5 · Once all G4 PASS · open Pkg 6**

Pkg 6 (TradeManager extensible · LAST) consolidates `RiskRule` interface
wrapping the 5 Layer 4 services (per D-095) + makes TradeManager pluggable
for future systems. Spec is NOT WRITTEN YET — that's the next agent's
authoring task once G4s green.

---

## §3 · G4 UAT queue · in priority order

These are the smoke trades that need to happen before SHADOW gate. Each
follows the 4-axis discipline (Quality / Recency / Cardinality / Latency).

| Pkg | UAT scope | Pre-req | Owner | Time |
|---|---|---|---|---|
| 5a + 5b | 4 chart-pattern smoke trades (Inv H&S · H&S Top · DB EE · DT AA) | Axis 2 Recency decision (§6.1) | Michael + Cursor | ~45 min |
| 5c | 2 flag smoke trades (Bull Flag · Bear Flag) | none | Michael + Cursor | ~30 min |
| 3b stack | Day re-classifies to NO_TRADE → `close_trade(reason="DAY_TYPE_NO_TRADE_RECLASS")` fires | none | Michael + Cursor | ~30 min |
| 3b stack | TCCI cross against direction → EXIT short-circuits + close_trade fires | requires S4 Woodies bars in DB | Michael + Cursor | ~30 min |
| 3b stack | MFE peak ≥ 80% T2 → TIGHTEN_STOP via `_apply_tightest_stop` · stop moves to entry + 50% of MFE distance | requires trade to reach +80% | Michael + Cursor | ~30 min |
| 3b stack | Chandelier engages at T2 hit · frozen ATR-14 · max_high - mult * ATR | requires trade to hit T2 | Michael + Cursor | ~30 min |
| 1 + 2a + 2bc | Smoke trade in DB (carry-over since 23/5) | none | Michael | ~30 min |
| 8 | Quality V2 + Auth Table V1 (post-RTH only · sizing verification per pattern × day_type cell) | RTH open | Michael | ~variable · runs during a trading session |

**G5 SHADOW gate criteria (from `PRE_LIVE_PIPELINE_2026-05-23.md` §7):**
- All Phase A G4s green
- `pytest tests/v9/ -q` green (currently 42 pre-existing failures · documented · same set)
- UAT 4 axes on `/api/v9/cockpit/systems-snapshot` green
- 60 min green · zero open warnings
- Michael sign-off explicit

---

## §4 · Current commit chain · what is G3'd

| Commit | Pkg | G3 status | Report |
|---|---|---|---|
| `12edadc` | test fix (Pkg 3a Stream 2 None contract) | trivial · part of Pkg 3a Stream 2 G3 | — |
| `bbf5044` | asyncio.run substitutions | trivial · test refactor | — |
| `151fdba` | Pkg 8 G3 PASS report (DOCS only) | n/a | — |
| `773f056` | test patch fix | trivial · part of Pkg 8 G3 | — |
| `9bc3925` | Pkg 8 · Quality V2 + Auth Table V1 | ✅ GREEN 25/5 13:20 | `PKG8_G3_PASS_2026-05-25.md` |
| `1e01c4a` | **Pkg 3b-3 · D-094 retrofit + Layer 4 wiring** (amended with 3b-3.1 hotfix) | ✅ GREEN 24/5 21:45 (14/14) | status board row 72 · 59/59 tests · zero regressions |
| `31e493e` | G4 UAT scaffolding 5a/5b | ✅ GREEN 24/5 21:00 | `G4_UAT_PKG5A_5B_SCAFFOLDING_G3_PASS_2026-05-24.md` |
| `23c8456` | Pkg 3b-2 · TrailEngine + persistence | 🔴 STRATEGIC STOP 24/5 20:15 · **superseded by 1e01c4a** | status board row 71 |
| `c917d42` | Pkg 3c · contract split | ✅ GREEN | `PKG3C_G3_PASS_2026-05-24.md` |
| `427d687` | Pkg 5c · Bull/Bear Flag | ✅ GREEN | (status board row 79) |
| `6dfce93` | Pkg 3b-1 · ATR caps + BE+1T | ✅ GREEN | `PKG3B_STREAM1_G3_PASS_2026-05-24.md` |
| `2c001a2` | Pkg 5b · Double Bottom/Top | ✅ GREEN | (status board row 78) |
| `7ffab50` | Pkg 5a · Inv H&S + H&S Top | ✅ GREEN | (status board row 77) |
| `cf6383e` | Pkg 3a Stream 2 · day-type targets | ✅ GREEN | (status board row 69) |
| `548f1f6` | Pkg 3a Stream 1.5 · prev_day wiring | ✅ GREEN | (status board row 68) |
| earlier · `dd9c34f`/`a58ee61`/`689ac41` | Pkg 3a Stream 1 · EXIT_V6 | ✅ GREEN | (status board row 67) |

---

## §5 · Pre-existing test failures (baseline · do NOT regress · do NOT fix)

When running regression, the current baseline at HEAD is **42 failures ·
1114 passes · 1 skipped** (per the 3b-3 G3 PASS verification on 24/5
21:45). Within the 42 failures the documented buckets are:

| Bucket | Approximate count | Source |
|---|---|---|
| TestDBPersistence (trade_manager DB session) | 2 | Pkg 3b-1 G3 noted · ongoing |
| TestSlotMath parametrized (TPO snapshotter) | 7 | Pkg 3c G3 noted |
| Snapshot capture lifecycle | 9 | Pkg 3c G3 noted |
| Trade time dual TZ | ~1 | frontend test |
| Other carry-over | ~23 | various pre-LIVE legacy |

If any NEW failure appears at HEAD that is NOT in this baseline · it IS
a regression and must be diagnosed before proceeding.

Baseline check command:
```
pytest tests/v9/ -q --ignore=tests/v9/api 2>&1 | tail -3
```

---

## §6 · Open decisions awaiting Michael · do NOT decide alone

### §6.1 · Axis 2 Recency hotfix for Pkg 5a/5b ⚠️ **BLOCKING G4**

`backend/v9/systems/five_min/five_min_system.py:771` writes
`ts=datetime.now(timezone.utc)` to `V9FiveMinSetup` instead of bar's `ts`.
Confirmed gap during G4 UAT scaffolding G3 review.

Options presented (Michael skipped on 2026-05-24 20:50):
- **A** · Hotfix now · 1-line change · mini-G3 (~10 min) → G4 fully closed
- **B** · Bundle into Pkg 6 TradeManager rewrite (defer · SHADOW will see wall-clock ts)
- **C** · Ship as observation · G4 PASS with known gap
- **D** · Hotfix + bundle 3 G3 observations from G4 scaffolding G3 together (~30 min)

**Cursor recommendation: A** — smallest correct change · low risk · closes G4 fully.

### §6.2 · Frontend sync strategy

Frontend has **ZERO** awareness of new pattern names (INVERSE_HNS / HNS_TOP /
DOUBLE_BOTTOM_EE / DOUBLE_TOP_AA / BULL_FLAG / BEAR_FLAG) and new day
type classifications (NeuE / NeuC). Confirmed by Cursor 2026-05-25 11:30
IL via `grep` returning 0 matches in `frontend/v9/src/`.

Options presented (Michael said "מה אתה ממליץ"):
- **A** · Defer entirely to post-SHADOW
- **B** · Minimal pre-SHADOW (~30 LOC · pattern label map + NeuE/NeuC split)
- **C** · Full sync now (3-5 days · delays SHADOW)
- **D** · Audit working tree M files first (~30 min · cheap diagnostic)

**Cursor recommendation: D then B** — audit first (the dangling M tsx
files visible at session start) to understand what's already in progress
without conflicting · then ~30 LOC minimal sync.

### §6.3 · D-093.Q1 + Q2 (Gateway canonical · Sierra DEMO acct)

Open since 2026-05-23. Block LIVE bring-up but NOT SHADOW. Michael TODO ·
no action from next agent unless explicitly asked.

### §6.4 · Pipeline 2 (Woodies) · 10 P-W open questions

`STATUS_BOARD.md` Pipeline 2 section: 10 P-W questions block S4 build
start. Michael TODO · do not start S4 spec without all 10 locked.

### §6.5 · Pipeline 3 + 4 verify reports (S1 Day Type · S3 Footprint)

Both blocked on Michael writing verification reports. No agent action
until Michael delivers.

---

## §7 · Pkg 6 (TradeManager extensible · LAST) · what to expect

**Status:** G0 spec NOT WRITTEN YET. Open the next agent should start
ONLY after every G4 UAT is green.

**Scope (per D-095 §Decision and PRE_LIVE_PIPELINE plan):**
- Make `TradeManager` pluggable for future systems (S2, S4, future S7 etc.)
- Consolidate `RiskRule` interface wrapping the 5 Layer 4 services
- Extension points for Pipeline 2 (S4 Woodies firing path)
- Persistence schema for trade state versioning
- NO behavior change to existing 5 Layer 4 rules (they already work via
  `_apply_layer4` in `1e01c4a`)

**Pkg 6 estimated size:** ~600-1000 LOC + ~50 tests · 2-3 day CC effort
+ ~half day G3 + UAT.

**Pre-requisite reads before drafting Pkg 6 spec:**
- `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md` (RiskRule consolidation rationale)
- `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` Gap 9 (SRP boundary between TrailEngine and TradeManager)
- `backend/v9/services/trail_engine.py` v3 final state (the consumer model Pkg 6 must support)
- `backend/v9/services/trade_manager/manager.py` current state (the target of extensibility)

---

## §8 · Pre-LIVE discipline reminders (mandatory · re-read before any code change)

From `.cursor/rules/mems26-pre-live-protocol.mdc`:

1. **Diagnose first · fix second.** Read the actual code via Read tool before any change.
2. **Audit existing surfaces before building.** Classify KEEP / ADAPT / REPLACE / DEFER.
3. **Smallest correct change.** No "while I'm here" refactors.
4. **Four UAT axes for any data/chart endpoint:** Quality · Recency · Cardinality · Latency.
5. **No silent failures.** Replace `logger.debug` on push/connect errors with `logger.warning` rate-limited.
6. **One thread at a time.** Finish + report before opening next P-ID.
7. **Update reports immediately** when state changes.
8. **Strategic stop and ask Michael** at phase gates · plan contradictions · trading-logic/risk-surface changes.

### Bridge stability (LOCKED · do NOT change)

- Bridge pushes to `http://localhost:8000` ONLY
- LaunchAgent: conditional KeepAlive (SuccessfulExit=false) + `V9_DISABLE_WATCHDOG=1`
- Do NOT run `npm run dev` / `next dev` / `scripts/start_all.sh` during audits

### Frontend polling floors (do NOT increase without Michael approval)

| File | Interval |
|---|---|
| `useSystemStatePolling` (V9Dashboard.tsx) | 5000ms |
| `SoundProvider` | 10000ms |
| `useLivePricePoll` | 5000ms |
| `WoodiesCciPanel` | 5000ms |
| `StreamHealthPanel` | 15000ms |
| `Layer0Strip` | 15000ms |
| `TopBar` heartbeat | 15000ms |
| `TradeHistoryStrip` | 30000ms |

### Forbidden zones (NEVER edit · per D-094 §5.B + D-091 + protocol)

- `backend/v9/services/layer4/*.py` — FROZEN per D-094 §5.B (consumed by `1e01c4a`)
- `sc_study/` (Sierra DLL) — DLL ops only via `docs/runbooks/SIERRA_DLL_OPS.md`
- `bridge/` — push to localhost only
- `backend/v9/systems/five_min/adaptive_stop.py` — Pkg 1 untouchable per D-094 §3.D Option 3
- `backend/v9/systems/five_min/atr_caps.py` — Pkg 3b-1 shipped
- `backend/v9/db/models/trades.py` (`V9Trade`) — no schema migrations
- `backend/v9/services/bar_router.py` — stable
- `backend/v9/services/trail_engine.py` — Pkg 3b-3 v3 final · do not modify until Pkg 6
- `backend/v9/systems/day_type/targets_table.py` — Pkg 3a + 3b-1 shipped

---

## §9 · How to start (5-minute startup ritual)

1. Read this file (§0–§8) · ~5 min.
2. Read `.cursor/rules/mems26-pre-live-protocol.mdc` + `CLAUDE.md` · ~3 min.
3. Read `docs/plans/STATUS_BOARD.md` rows 63–81 (Phase A queue) and `docs/decisions/D-095_*.md` · ~3 min.
4. Run baseline regression to confirm 42 known failures · ~1114 passes:
   ```
   pytest tests/v9/ -q --ignore=tests/v9/api 2>&1 | tail -3
   ```
5. Ask Michael:
   - "Axis 2 Recency decision (Pkg 5a/5b) — Cursor recommends Option A. OK?"
   - "Frontend strategy — Option D (audit) then B (minimal sync). OK?"
   - "Which G4 UAT do we run first today?"
6. Once Michael answers · proceed to §2 Step 1 → 2 → 3 → 4.

---

## §10 · Recent agent transcripts (cite if needed)

- [Pkg 4 audit + frontend gap + handoff prompt](269fc8b5-cc57-4e78-80cd-81eddb6b27e8) (this session · 24/5 + 25/5)
- Earlier sessions cited in commit log + G3 PASS reports — search by Pkg number or commit hash.

Use the transcript folder when an exact wording/ID/path/error context is
needed. Search keywords first · don't read end-to-end.

---

## §11 · Quick-reference state at 25/5 14:00 IL

```
HEAD:                   12edadc
Branch:                 stabilize/mems26-local-truth-2026-05-16
Ahead of origin:        16 commits
Phase A G3 status:      ALL GREEN (Pkg 0,1,2a,2bc,3a*3,3b*3,3c,5a,5b,5c,8 · 4a/4b DEFERRED)
Phase A G4 status:      0/8 done · waiting Michael smoke trades
Frontend sync:          0% · zero awareness of new patterns + day types
Open decisions:         §6.1 Axis 2 Recency · §6.2 Frontend · §6.3 D-093 · §6.4 P-W · §6.5 verify reports
Bridge:                 localhost-only · LaunchAgent stable
Forbidden zones:        see §8
Next major milestone:   G5 SHADOW gate (deps · all G4 green + frontend §6.2 decision)
```

End of continuation prompt. **First action: ask Michael about §6.1 + §6.2.**
