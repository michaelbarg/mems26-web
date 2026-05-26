# Pre-LIVE Pipeline · Master Work Plan

**Date:** 2026-05-23 · **Version:** V2 (full restructure per Master Summary alignment)
**Owner:** Michael Barg
**Authority hierarchy:**
1. **Latest chat decisions** (this version) — wins on conflict
2. `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` (🔒 LOCKED · A+B+C exit types)
3. `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` (🔒 LOCKED · 9 patterns · day-type matrix · 10 P-W open)
4. `~/Downloads/S2_Master_Summary.xlsx` (Michael's authoritative reference · 7 sheets)
5. D-090 (Path A canonical) · D-091 (S2 LIVE scope) · **D-092 (S4 Woodies V1 🔒 LOCKED 23/5)**
6. D-089 (S3 Firing) · Master Index V2 · Constitution V3

**Model:** Hybrid C (Pipeline per-system · system-by-system independent promotion)
**Status:** ✅ APPROVED 23/5 17:30 · awaiting Michael spec locks 1+3 before build start

---

## Amendments log

| Date | Change |
|---|---|
| 23/5 16:30 | V1 initial · 9 packages |
| 23/5 16:45 | News pause → DEMO phase only. Pkg 6 added (TradeManager rewrite per EXIT_V5). |
| 23/5 17:00 | EXIT V5 → V6 · Type C (DD-only time exit per Day Type). Pkg 4a `time_stop`→`news_countdown`. |
| 23/5 17:30 | **V2 full restructure** — aligned with Master Summary. Decomposed Pkg 2 → 2a/2b/2c, Pkg 3 → 3a/3b/3c. Added Pkg 8 Quality V2. Pkg 6 redesigned hook-based extensible. `time_stop approaching` moved to DEMO-1 (interpreted as news countdown). STC/BTC + Filters moved to DEMO. EXIT_V6 fix queued (7 day types: NeuE+NeuC split). |
| 23/5 18:00 | **D-092 S4 Woodies V1 LOCKED** — 9 patterns · ATR-14 stop arch · day-type matrix · 10 P-W open. Pipeline 2 (S4) fleshed out with 10 packages. xlsx + 3 CSV exports saved to `docs/spec_authority/`. |
| 23/5 18:15 | **Pkg 0 scope EXPANDED** — verify-first found `Chart5MinSystem` wired into `EventDispatcher` (app.py) while `FiveMinSystem` (canonical Path A) wired into `BarRouter` (main.py) · stale dual-registration. Path X chosen (drop Chart5Min · EventDispatcher 6→5 systems). Also fixes pre-existing SYSTEM_NAMES drift (`snapshot.py` says `"chart_5min"` vs `shadow_routes.py` says `"five_min"`). Estimated 1-2h → **1 day** · 10 sub-steps. |
| 23/5 18:25 | **Pipeline 2 (S4 D-092) fleshed** — 10 packages (W-0 audit · W-1 ATR-14 engine · W-2 trend states · W-3 day-type matrix · W-4 HFE dual-path · W-5 ZLR fix · W-6 existing 8 patterns refit · W-7 anti-patterns · W-8 dispatcher+confidence+YAML · W-9 TradeManager hooks). Code audit found 50 files in `woodies/` · 9 patterns already exist incl HFE → Pipeline 2 is conformance-to-spec, not greenfield. 6 packages can start now; 4 spec-blocked on P-W2/W-3/W-5/W-6/W-8/W-9 resolutions. Pipelines 3 (S1) + 4 (S3) verify checklists added. |
| 23/5 19:00 | **D-093 Sierra Order Routing LOCKED · Pipeline 5 added (9 packages)** — pre-LIVE deep dive found 4 gaps: (1) DLL `MES_AI_DataExport.cpp:813-815` is a TODO instead of `sc.SubmitOCOOrder()` so no trade has ever reached Sierra; (2) two `TradingGateway` impls coexist (legacy `backend/v9/gateway/` wired vs new `services/trading_gateway/` not wired); (3) 3 dead executor stubs in `gateway/{live,demo,shadow}_executor.py`; (4) `bridge/trade_commands.py::TradeCommandHandler` complete but unwired. Two sub-decisions deferred to verify-first: D-093.Q1 gateway canonical, D-093.Q2 DEMO account. ~9.5 CC days · blocks SHADOW + DEMO gates. |
| 23/5 19:05 | **Pkg 1 (S2 Adaptive Stop) handoff finalized** — 4 Claude Desktop review fixes applied: (1) §1 D-091 2 pseudo-code bugs documented as NOT-stop-signal, (2) §7 line 5 verify-before-edit safeguard against M13, (3) §4 test 6/7/8 numerics rewritten under corrected `min(max(A,B), floor)` formula with full arithmetic table, (4) §9 stop-signal trigger for accidental lines 206-208 modification (4 layers of guard total). Floor semantics locked = Option A (hard 4T minimum distance). D-091 also updated with corrected formula. Ready for Claude Desktop mega-prompt build. |
| 25/5 11:18 | **D-095 LOCKED · Pkg 4a + 4b DEFERRED · scope absorbed by 3b-3** (Michael 25/5 11:18 chat) — Cursor audit confirmed 4 of 5 originally-planned RiskRule classes (TCCIExit / SWITighten / CCIFlat / MFETighten) are 1:1 live in `TrailEngine._apply_layer4()` post-3b-3 (commit `1e01c4a`) · DirectionChangeRule partially live via `_handle_day_type_action` NO_TRADE escalation gate. Michael accepted that the 7-layer defense (Adaptive Stop · Time Stop · TCCI cross · CCI Flat · SWI · MFE peak · NO_TRADE reclass) is sufficient; per-DayType reclass extension deferred post-LIVE. Phase A queue collapses 15 → 13 packages (4a+4b removed · Pkg 6 absorbs RiskRule wrapper interface). Time saved ~10h CC + ~2h Cursor review. Pkg 8 promoted to NEXT but BLOCKED on Auth Table. Doc: `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md`. |

---

## 1 · Roles — מי עושה מה

| Role | אחריות | סוג טוקנים |
|---|---|---|
| **Michael** | החלטות אסטרטגיות · spec locks · D-092 doc · S1+S3 verify reports · sign-off ב-gates | החלטות בלבד |
| **Claude Desktop** | כתיבת mega prompts מלאים ל-CC לפי תבנית 7-שדות + Stop signal | Prompt writing |
| **Claude Code (CC)** | Execute mega prompts · code + tests + linter + commit local | Implementation |
| **Cursor (אני)** | פיקוח · review של CC ב-G3 · UAT 4 axes ב-G4 · strategic stop · plan/status update | Supervision · review |

---

## 2 · Source of truth — לקרוא לפני כל פעולה

| מסמך | סטטוס | אחראי |
|---|---|---|
| `docs/decisions/D-089_S3_FIRING_LOCKED.md` | 🔒 LOCKED | — |
| `docs/decisions/D-090_PATH_A_CANONICAL.md` | ⏳ move from ~/Downloads | Michael |
| `docs/decisions/D-091_S2_LIVE_SCOPE.md` | 🔒 LOCKED | — |
| `docs/decisions/D-092_S4_WOODIES_UPDATE.md` | 🔒 LOCKED 23/5 18:00 | — |
| `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` | 🔒 LOCKED · 7 day-types | — |
| `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` | 🔒 LOCKED | — |
| `docs/spec_authority/S4_WOODIES_TABLE_*.csv` (×3) | reference exports | — |
| `~/Downloads/S2_Master_Summary.xlsx` | 🔒 authoritative reference | — |
| `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` | 🔒 LOCKED | — |
| `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | 🔒 LOCKED | — |

---

## 3 · Pre-flight checklist

### Michael deliverables

| # | פריט | Required by | סטטוס |
|---|---|---|---|
| 1 | D-090 + D-091 from Downloads → `docs/decisions/` | Pkg 0/1/2 | ⬜ |
| 2 | **Spec lock 1: Zohar thresholds** — drop_threshold_pct=90%? · belly_dominance_ratio=1.5× (Master)? · cot/amt windows · expansion_ticks=6-7 (Master) · min_bars_for_drop=3 (Master) | Pkg 2a/2b/2c | ⬜ |
| 3 | ~~Spec lock 2 (Adaptive Stop multipliers)~~ — **ALREADY LOCKED in Master Summary Sheet 4** (Reactive 1.0× · OFA/Flag 1.5× · H&S/Double 2.0× · floor 4 ticks) | — | ✅ |
| 4 | **Spec lock 3: Bulkowski params** — Inv H&S · Double · Flag specifics (Master Sheet 2 covers most · only edge tolerances open) | Pkg 5a/5b/5c | ⬜ |
| 5 | D-092 Woodies update doc | Pipeline 2 | ⬜ |
| 6 | S1 Day Type verify report | Pipeline 3 | ⬜ |
| 7 | S3 Footprint verify report (incl. O-4 audit) | Pipeline 4 | ⬜ |
| 8 | Paste handoff message → Claude Desktop · receive Pkg 0 mega prompt | Build start | ⬜ |

### Cursor deliverables

| # | פריט | סטטוס |
|---|---|---|
| 9 | `docs/templates/MEGA_PROMPT_TEMPLATE.md` | ✅ DONE |
| 10 | `docs/templates/SPEC_LOCK_TEMPLATE.md` (simplified · drops multipliers) | ⏳ queued |
| 11 | `docs/plans/STATUS_BOARD.md` (V2 · new package list) | ⏳ queued |
| 12 | EXIT_V6 fix — 7 day types (NeuE 45min + NeuC 30min split) | ⏳ queued |

---

## 4 · Pipeline 1 · S2 D-091 — 17 packages

### Phase A · PRE-SHADOW build (~5 weeks)

| Pkg | Name | Files (Master Summary §6/§7) | Spec dep | Dev | Cursor review | UAT | SHADOW soak | Blocks LIVE? |
|---|---|---|---|---|---|---|---|---|
| **0** | Path B deletion + EventDispatcher rewire (Path X) | `backend/v9/systems/chart_5min/` (entire dir) · `wrappers.py` Chart5MinSystem class · `app.py` init_event_dispatcher · `snapshot.py` SYSTEM_NAMES sync · 7 test files | — | 1d | 1h | rg=0 + pytest + Redis key audit | n/a | hygiene + SYSTEM_NAMES drift fix |
| **1** | Adaptive Stop Engine | NEW `adaptive_stop.py` · baseline_atr + rolling_atr + today_typical + 3-layer cap | multipliers from Master (locked) | 1-2d | 4h | unit + 4 axes | 5d | YES |
| **2a** | OFA Entry signal fix | `five_min_system.py:319-340` · `_detect_reactive`/`_detect_initiative` | Spec lock 1 (entry signal) | 0.5d | 2h | regression on 3 existing SHADOW trades | 5d | YES |
| **2b** | OFA belly_ratio + min_bars config | `five_min_system.py:321` + config | Spec lock 1 (Zohar thresholds) | 1d | 3h | unit + config tests | 5d | YES |
| **2c** | OFA 7 validator checks | `setup_emitter.py:81` + `pre_fire_validator.py` | M18/D-063 spec | 0.5d | 2h | 7 unit per check | 5d | YES |
| **3a** | Day-type targets (7 schemas) | NEW `day_type_targets.py` + TradeManager wiring | EXIT_V6 + Day Type 7-state | 1d | 4h | unit × 7 day types | 5d | YES |
| **3b** | Trail logic | `manager.py` · T1→BE+1T · T2→HL/LH on 5-min closes · post-T2→ATR chandelier | Pkg 1 + 3a | 1d | 4h | unit + integration | 5d | YES |
| **3c** | Contract split per pattern | `manager.py` + per-pattern config · 50/30/20 default · 25/50/25 OFA · 33/33/34 reversal · 50/50 Flag | Pkg 3a | 0.5d | 2h | unit per family | 3d | YES |
| ~~**4a**~~ | ~~Risk Rules · Critical (2 EXIT rules)~~ **DEFERRED · D-095 25/5 11:18** | scope absorbed by 3b-3 · `tcci_cross_exit` + `_handle_day_type_action` NO_TRADE escalation already live in `TrailEngine._apply_layer4` | n/a | n/a | n/a | n/a | n/a | n/a |
| ~~**4b**~~ | ~~Risk Rules · Tightening (3)~~ **DEFERRED · D-095 25/5 11:18** | scope absorbed by 3b-3 · `mfe_peak_tighten` + `cci_flat_tighten` + `swi_tighten` already live in `TrailEngine._apply_layer4` | n/a | n/a | n/a | n/a | n/a | n/a |
| **5a** | Inverse H&S + H&S Top | NEW `patterns/head_shoulders.py` · 3 swing points · neckline · throwback | Spec lock 3 + Pkg 1+3 | 2d | 6h | golden fixtures × 15 | 5d | YES |
| **5b** | Double Bottom + Double Top | NEW `patterns/double_bt.py` · Eve&Eve · Adam&Adam · 0.15% tol | Spec lock 3 + Pkg 1+3 | 2d | 4h | golden fixtures × 15 | 5d | YES |
| **5c** | Bull Flag + Bear Flag | NEW `patterns/flags.py` · pole + consol + H2/L2 Brooks entry | Spec lock 3 + Pkg 1+3 | 2d | 4h | golden fixtures × 15 | 5d | YES |
| **8** | Quality V2 | `quality_tier.py` rewrite · fix V1 anti-correlation · 1/2/3 contracts per Auth Table | Auth Table + Pkg 5 patterns | 1d | 3h | unit × pattern × quality | 5d | YES |
| **6** | **TradeManager extensible (LAST)** | `manager.py` full rewrite per EXIT_V6 · hook-based architecture · plug-in rule system · **absorbs Pkg 4a+4b scope per D-095** (wraps 5 live Layer 4 services in `RiskRule` subclasses · zero functional change) | ALL previous (1+2+3+5+8) | 2.5-3d | 7h | unit × 18 (A×B×C per family) + integration | 5d | **YES — CRITICAL** |

**Pre-SHADOW sequencing (parallel streams · revised per D-095 25/5):**

```
Week 1: Pkg 0 (1d) → in parallel: Pkg 1, Pkg 2a/2b/2c → soak               [DONE 23/5]
Week 2: Pkg 3a → Pkg 3b → Pkg 3c (sequential — share manager.py)           [DONE 24/5]
Week 3: Pkg 5a + Pkg 5b + Pkg 5c (parallel)                                [DONE 24/5]
Week 4: ~~Pkg 4a + 4b (DEFERRED · D-095 · scope absorbed by 3b-3)~~        [SKIPPED]
Week 4: Pkg 8 Quality V2 (blocked on Auth Table from Michael)              [NEXT]
Week 5: Pkg 6 TradeManager (final integration · absorbs 4a+4b RiskRule interface)
Week 6: integration UAT + bug-fix from soaks
```

**Actual sequence (25/5):** 0 → 1 → 2a/2bc → 3a Stream 1/1.5/2 → 3b Stream 1/2 (stopped)/3 + 3c → 5a/5b/5c → **8 (NEXT · blocked Auth Table)** → 6 (LAST).

### Phase B · SHADOW (5-10 trading days)

≥20 trades per pattern OR 10 days of data (whichever first) · log analysis · threshold calibration.

### Phase C · DEMO (7 days on Sierra Sim)

| Pkg | Name | Why DEMO-only | Dev | Notes |
|---|---|---|---|---|
| **DEMO-1** | News pause + news_countdown rule | depends on news calendar feed | 1.5d | FOMC/NFP/CPI · 3 min before · 5 min after · countdown tightens stop 5 min pre-event |
| **DEMO-2** | Filters (lunch skip + FOMC time window) | sanity layer on top of patterns | 1d | lunch 12:00-13:30 ET skip · FOMC release time block |
| **Pkg 7** | STC/BTC time-of-day modes (optional · SHADOW-decided) | Brooks methodology · last 90 min behavior | 0.5d | only if SHADOW analysis shows runners losing money at close |

### Phase D · LIVE micro (P-L0 + P-L1)

1 contract · 1 day · explicit Michael approval.

---

## 4.1 · Pkg 0 expanded scope · Path X (verified 23/5 18:15)

**Background:** verify-first found 2 wired paths for `system_id=2`:
- **Path A** (canonical · D-090): `FiveMinSystem` → wired in `main.py` via `bar_router.subscribe()` → fires real signals
- **Path B** (stale): `Chart5MinSystem` (wrapper around `chart_5min/detector.py`) → wired in `app.py` via `dispatcher.register_system()` → 19 detectors return None or non-firing signals

**Cross-system impact verified** (`audit 23/5 18:10`):
- 5 other systems (S1/S3/S4/S5/S6) subscribe to **independent streams** — none depend on Chart5MinSystem
- "cumulative_delta" stream (where Chart5MinSystem subscribes) **still has S1 (DayType)** as subscriber → no orphaned stream
- Frontend: `rg "chart_5min" frontend/v9 → 0 hits` → zero UI impact
- `shadow_routes.py` already uses `"five_min"` name for system_id=2 → snapshot.py drift gets fixed

### 10 sub-steps (1 day · ~6h CC + 1h Cursor review)

| # | Step | File(s) | Risk | Verify |
|---|------|---------|------|--------|
| 1 | Remove `Chart5MinSystem` class definition | `backend/v9/systems/wrappers.py` (class block) | LOW | grep returns 0 hits |
| 2 | Remove `Chart5MinSystem` import + instantiation + `register_system()` call | `backend/v9/app.py::init_event_dispatcher` | LOW | dispatcher registers 5 systems instead of 6 |
| 3 | Update `dispatcher.py` docstring example | `backend/v9/services/event_dispatcher/dispatcher.py:24` | LOW | cosmetic only |
| 4 | Fix SYSTEM_NAMES drift: `2: "chart_5min"` → `2: "five_min"` | `backend/v9/services/snapshot_service/snapshot.py:23` | **MED** — Redis key reads | snapshot service can read existing Redis or migrate |
| 5 | Redis key audit + migration | runtime check + script | **MED** | enum `mems26:state:chart_5min` keys → rename or drop |
| 6 | Update `five_min/compliance_manifest.yaml` (remove chart_5min refs) | `backend/v9/systems/five_min/compliance_manifest.yaml` | LOW | grep returns 0 hits |
| 7 | Delete `backend/v9/systems/chart_5min/` entire directory (~2000 LOC · 19 patterns) | dir | LOW | dir gone |
| 8 | Delete 7 test files for chart_5min | `tests/v9/systems/test_chart_5min*/`, `tests/v9/compliance/test_chart_5min_compliance.py`, `tests/v9/compliance/v1_generated/test_system2_v1.py`, `tests/v9/compliance/v2_generated/test_snapshot_compliance.py` (if it only tests chart_5min naming), `tests/v9/services/test_event_dispatcher.py` (if it depends on Chart5MinSystem) | MED | refactor or delete · pytest green |
| 9 | Verify `pytest tests/v9/ -q` green | full suite | — | exit 0 |
| 10 | Verify `rg "chart_5min" backend/ tests/` returns 0 hits (only acceptable: history/decisions docs) | repo-wide | — | grep clean |

**Acceptance (G4 UAT):**
- ✅ `len(dispatcher._systems) == 5` (S1, S3, S4, S5, S6)
- ✅ Bar arrival on `cumulative_delta` routes ONLY to S1 (not Chart5MinSystem)
- ✅ FiveMinSystem still fires correctly via BarRouter (existing SHADOW trades reproduce)
- ✅ `pytest tests/v9/ -q` green
- ✅ Frontend cockpit shows S1/S2(five_min)/S3/S4/S5/S6 status unchanged
- ✅ Redis keys reconciled

**Side-effect benefit:** fixes 2 latent bugs:
1. SYSTEM_NAMES drift (snapshot.py vs shadow_routes.py)
2. EventDispatcher dispatches `cumulative_delta` to a non-firing path (CPU waste)

---

## 5 · Pkg 6 Hook-Based Architecture — per Michael 23/5 17:25

ה-TradeManager בנוי extensible — כל rule הוא plug-in. Future rules נכנסים בלי rewrite.

```python
class TradeManager:
    rules = [
        # Always-on (built pre-SHADOW · enabled at FIRE)
        TypeAExitRule(),         # Pkg 6 · close+vol thesis-broken
        TypeBNoiseRule(),        # Pkg 6 · skip wick/low-vol/throwback
        TypeCTimeExitRule(),     # Pkg 6 · DD-only · per Day Type window
        TCCIExitRule(),          # Pkg 4a · TCCI×CCI14 cross → EXIT
        DirectionChangeRule(),   # Pkg 4a · S1 reports change → EXIT
        SWITightenRule(),        # Pkg 4b · Sidewinder red → tighten 2-4T
        CCIFlatRule(),           # Pkg 4b · CCI flat 3+ bars → tighten
        MFETightenRule(),        # Pkg 4b · MFE ≥ 80% T2 → tighten
        # Future hooks (built pre-SHADOW · no-op if data unavailable)
        NewsCountdownRule(),     # DEMO-1 · tightens if news_feed available
        STCModeRule(),           # Pkg 7 · time-of-day if STC enabled
        BTCModeRule(),           # Pkg 7
        LunchSkipFilter(),       # DEMO-2 · skip during lunch window
    ]

    def on_bar(self, bar, state):
        # Type C clock check (independent of bars)
        if TypeCTimeExitRule().should_fire(state):
            return ExitAction(reason="type_c_time")
        # Per-bar rules in priority order
        for rule in self.rules:
            if not rule.is_data_available(state):
                continue  # silent skip · no error if dep missing
            action = rule.evaluate(state, bar)
            if action:
                return action
        return None  # hold position
```

**Acceptance:** הוספת DEMO-1 (news rule) → רק `is_data_available()` חוזר True כש-news feed פעיל · בלי lines אחרים בקוד.

---

## 6 · Quality gates per package

לכל package · החל מ-Pkg 0:

| Gate | מי בודק | קריטריון | אם נכשל |
|---|---|---|---|
| G0 · Spec ready | Cursor | spec locks חתומים · D-091 + Master Summary references resolved | STOP · ask Michael |
| G1 · Mega prompt written | Claude Desktop | 7 fields + Stop signal · golden fixtures · forbidden paths | revise |
| G2 · CC implementation | CC | pytest green · linter clean · self-report | max 2 retries → STOP |
| G3 · Independent review | Cursor | adversarial · silent excepts · drift · edge cases | fix prompt back to CC |
| G4 · UAT 4 axes | Cursor + Michael | Quality + Recency + Cardinality + Latency on live endpoint | STOP · fix · re-UAT |
| G5 · SHADOW soak | Michael monitor | ≥20 trades per pattern OR 5 trading days OR 4h ירוק רצוף | extended soak |
| G6 · Promote | Michael | sign-off explicit | hold |

---

## 7 · SHADOW gate (P-S0) — activation criteria

| # | תנאי | Status |
|---|---|---|
| 1 | All Phase A packages (0-6, 8) SHADOW-soak completed | ⬜ |
| 2 | `pytest tests/v9/ -q` ירוק | ⬜ |
| 3 | UAT 4 axes on `/api/v9/cockpit/systems-snapshot` ירוקים | ⬜ |
| 4 | 60min ירוק · zero open warnings | ⬜ |
| 5 | Michael sign-off explicit | ⬜ |

---

## 8 · DEMO gate criteria

| # | תנאי |
|---|---|
| 1 | All Phase A packages SHADOW-soak passed |
| 2 | D-092 (S4) done + soak passed |
| 3 | S1 + S3 verify reports closed או gaps fixed |
| 4 | ≥40 SHADOW trades on firing pattern combo |
| 5 | Zero open `logger.warning` (rate-limited 0/hour) for 24h |

DEMO phase builds DEMO-1 + DEMO-2 + (optional) Pkg 7 during DEMO soak.

---

## 9 · LIVE micro gate (P-L0)

| # | תנאי |
|---|---|
| 1 | DEMO 7 ימים completed · Sierra Sim |
| 2 | Zero bugs surfaced in DEMO |
| 3 | All 4 pipelines fully promoted (S2 + S4 D-092 + S1 verify + S3 verify) |
| 4 | DEMO-1 + DEMO-2 done + soak |
| 5 | P-L0 Preflight checklist 100% |
| 6 | Michael sign-off · 1 contract · 1 day |

---

## 10 · Pipeline 2 · S4 Woodies CCI (D-092) — 10 packages

**Status:** Spec ✅ LOCKED 23/5 18:00. Build queue open · 4 packages spec-blocked on P-W resolutions.
**Authority:** `docs/decisions/D-092_S4_WOODIES_UPDATE.md` + `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` (3 sheets)
**Context:** S4 code is **mature** — `backend/v9/systems/woodies/` has 50 files · 9 patterns already exist (including HFE in `patterns/hfe.py`) · stages a1-a7 + b1-b14 wired. Pipeline 2 is mostly **conformance-to-spec refit**, not greenfield.

### Build queue · 10 packages (~16-19 dev days · 4 weeks calendar with parallel streams)

| Pkg | Name | Scope | Spec dep | P-W blocker | Dev | Pkg deps | Blocks LIVE? |
|---|---|---|---|---|---|---|---|
| **W-0** | S4 Codebase Audit | Read all 50 files · document existing state per pattern (BUILT/STUB/PARTIAL) · existing stop logic · existing day-type integration · output `docs/reports/PIPELINE_2_S4_AUDIT.md` | D-092 (locked) | — | 1d | — | hygiene |
| **W-1** | ATR-14 Stop Engine | NEW `woodies/atr_stop.py` · ATR-14 calc + 3-layer cap (CONT 1.0× · MED 1.2× · REV 1.5×) + floor 4T | D-092 Stop Architecture (locked) | — | 1d | W-0 | YES |
| **W-2** | Trend State Machine | BLUE/RED/YELLOW/GRAY · Stage-1 gate per Liran (6 bars + 1 bar >±100) · researcher rec: BLOCK YELLOW for all 9 | D-092 §Trend State | **P-W5** YELLOW block decision | 1d | W-0 | YES |
| **W-3** | Day-Type Matrix gate | NEW `woodies/day_type_gate.py` consuming Sheet B (9 patterns × 7 day types = 63 cells) · ✅/⚠️/❌ with per-cell conditions (IB-extension direction · late-session · VA edges etc) | D-092 Sheet B (locked) | — | 1.5d | W-0, W-1, W-2 | YES |
| **W-4** | HFE dual-path | Audit existing `patterns/hfe.py` · implement DLL-primary + Python fallback per researcher rec (log divergences for SHADOW) | D-092 §Patterns · MEMS26-internal | **P-W2** DLL canonical? | 2d | W-0 | YES |
| **W-5** | ZLR fixtures repair | Audit 39 test failures (Master Index 16/5) · researcher hypothesis: Stage-1 incomplete fixtures (BLUE declared but no >+200 touch) · audit BEFORE assuming code regression | D-092 §Caveats #7 | **P-W3** root cause? | 1-2d | W-0 | YES |
| **W-6** | Existing 8 patterns refit | Wire ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB to ATR-14 stop + Day-Type Matrix + Trend State + Anti-patterns · per-pattern target scheme from Sheet A (CCI-scaffold · pattern-measure · R-multiples) | D-092 Sheet A + Sheet C | — | 3d | W-1, W-2, W-3, W-7, W-8 | YES |
| **W-7** | 9 Anti-patterns | NEW `woodies/anti_patterns.py` · 9 boolean gates (AP1-AP9) from Sheet C · pre-fire validator integration | D-092 §Anti-patterns (locked · 9 rules) | — | 1d | W-0 | YES |
| **W-8** | Dispatcher + Confidence + YAML | Update `dispatcher.py` per P-W6 hierarchical (DTV1-spec · same-direction max conf · opposite-direction Stage-1 tiebreak · CONT wins BLUE/RED) · normalize all-9 confidences [0,1] per z-score/min-max · YAML loader for thresholds | D-092 §P-W6, P-W8, P-W9 | **P-W6 + P-W8 + P-W9** | 2d | W-6 | YES |
| **W-9** | S4 TradeManager hooks | Add to S2 TradeManager hook system (Pkg 6): `LiranExitLadderRule` (T1 4T/5T → ±200 cross → ±100 cross → ZL cross → SWI red → new opposing pattern → CCI flat 3+ → TCCI cross) · trail post-T2 last-bar low/high | D-092 §Target Strategy + S2 Pkg 6 done | — | 1.5d | ALL S4 + S2 Pkg 6 | **YES — CRITICAL** |

### Pre-flight items (Michael owns)

| # | Item | Maps to | Status |
|---|------|---------|--------|
| W-PF1 | **P-W2** decision: DLL canonical? · Python fallback for audit/divergence logging? | W-4 | ⏳ open |
| W-PF2 | **P-W3** decision: ZLR 39 failures root cause hypothesis confirmed? Fix fixtures or fix detector? | W-5 | ⏳ open |
| W-PF3 | **P-W5** decision: YELLOW state — BLOCK all 9 (Wood WSI) or PASS? | W-2 | ⏳ open |
| W-PF4 | **P-W6** decision: Priority dispatcher rule when 2 patterns fire same bar | W-8 | ⏳ open |
| W-PF5 | **P-W8** decision: Confidence normalization method (z-score · min-max · per-pattern multiplier) | W-8 | ⏳ open |
| W-PF6 | **P-W9** decision: YAML schema for Woodies thresholds + default "Liran baseline" profile | W-8 | ⏳ open |
| W-PF7 | **P-W1** internal: DTV1 verbatim paste in repo | — | ⏳ open |
| W-PF8 | **P-W4** internal: JSON 18s gateway `_persist_trade` datetime bug — fixed yet? | — | ⏳ open |
| W-PF9 | **P-W7** internal: Master Index says 6 touch-points · Canvas shows 5 · reconcile | — | ⏳ open |
| W-PF10 | **P-W10** post-SHADOW: keep-all-9 vs data-driven drop · N≥500 + E[R] criteria | — | ⏳ defer to post-SHADOW |

**Build start gate:** Pkgs W-0/W-1/W-3/W-6/W-7/W-9 (6 packages) can start once D-092 is locked (already ✅). Packages W-2/W-4/W-5/W-8 (4 packages) need P-W resolutions first.

### Sequencing · Pipeline 2

```
Week 1: W-0 audit (1d) → in parallel: W-1 (ATR engine · 1d), W-7 (anti-patterns · 1d)
Week 2: W-3 (day-type matrix · 1.5d) → W-2 (trend states · spec gated) → W-5 (ZLR fix · spec gated)
Week 3: W-4 (HFE dual-path · spec gated) → W-8 (dispatcher · spec gated · 2d)
Week 4: W-6 (existing 8 patterns refit · 3d) → W-9 (TradeManager hooks · 1.5d after S2 Pkg 6)
```

### Pipeline 2 SHADOW soak

- 5-10 days per pattern · need ≥20 trades per pattern OR data-driven drop per P-W10 threshold
- Per D-092 Stage 2: post-W-0 SHADOW data extraction (hit-rate · MFE/MAE · E[R])

### Promotion rules (per D-092 Stage 4 · researcher)

- **🔴 NO_STATS → 🟢 promote:** N≥500 AND E[R]>0 AND T1 hit-rate >40%
- **🔴 NO_STATS → drop:** N≥500 AND E[R]<0 AND T1 hit-rate <35%
- Otherwise: extended SHADOW

---

## 11 · Pipeline 3 · S1 Day Type verify

**Sponsor:** Michael (verify pass · code unchanged unless verify finds gap)
**Authority:** D-088 D-073 D-074 · S1 = Observer (D-082 affirmed)
**Status:** ⏳ pending Michael

### Verify checklist (Michael owns)

| # | Item | Why |
|---|------|-----|
| 1 | 7 Day Type assignment correctness per 5+ historical days | Day Type 7-state used by S2 Pkg 3a target schemas |
| 2 | Mid-session restart re-seed (`docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19_FINDINGS.md`) | Already investigated · need closure |
| 3 | YAML loader · per-day-type config | matches S2 needs |
| 4 | Stream subscription health (`cumulative_delta + volume_profile`) | pre-flight for Pkg 0 |

Output: `docs/reports/PIPELINE_3_S1_VERIFY.md` with PASS/FIX/DEFER per item. Fixes (if any) become P-D1...P-Dn micro-packages.

---

## 12 · Pipeline 4 · S3 Footprint verify

**Sponsor:** Michael (verify pass · code unchanged unless verify finds gap)
**Authority:** D-089 (S3 FIRING locked) · D-082 (Footprint role) · O-4 (S3 entry/stop spec audit · open)
**Status:** ⏳ pending Michael

### Verify checklist (Michael owns)

| # | Item | Why |
|---|------|-----|
| 1 | **O-4 audit:** S3 entry signal definition · stop placement spec | OPEN issue · blocking LIVE per D-089 |
| 2 | `footprint_system.py::_fire()` LIVE safety net intact (Michael 23/5 explicit) | per pre-LIVE protocol |
| 3 | 5-min bar consumption sync (Path A FiveMinSystem reads from footprint) | post-Pkg 0 verification needed |
| 4 | T3 signal definition · Cluster Guard shadow (`tests/v9/gateway/test_d088_shadow_cluster_guard.py`) | D-088 |

Output: `docs/reports/PIPELINE_4_S3_VERIFY.md` with PASS/FIX/DEFER per item.

---

לא חוסם תחילת Pipeline 1.

---

## 13 · Pipeline 5 · Sierra Order Routing (D-093) — 9 packages

**Sponsor:** Michael (DLL ACSIL + gateway reconcile + bridge wiring)
**Authority:** D-093 (Sierra Order Routing · LOCKED 23/5)
**Status:** ⏳ awaiting D-093 sub-decisions (Q1 gateway canonicality · Q2 DEMO account)
**Discovery rationale:** pre-LIVE deep dive found that **no trade has ever reached Sierra** — DLL `MES_AI_DataExport.cpp:813-815` has a TODO instead of `sc.SubmitOCOOrder()`, both Python executors are stubs, and `bridge/trade_commands.py::TradeCommandHandler` (193 LOC complete) was never wired into bridge startup.

### Gap summary (from D-093)

| Gap | Where | State |
|-----|-------|-------|
| 1 · DLL never places orders | `MES_AI_DataExport.cpp:791-855` | `result_status = "ACK_SHADOW"` placeholder · no ACSIL call |
| 2 · Two gateway impls | `backend/v9/gateway/` (wired) vs `services/trading_gateway/` (richer · not wired) | needs P5-0 audit |
| 3 · 3 dead executor stubs | `gateway/{live,demo,shadow}_executor.py` | unimported · delete in P5-0 |
| 4 · Bridge handler unwired | `bridge/trade_commands.py::TradeCommandHandler` | full code exists · never instantiated |

### Packages (9 · ~9.5 CC days · ~5-6 calendar days)

| # | Package | CC days | Sub-steps |
|---|---------|---------|-----------|
| **P5-0** | Gateway reconciliation (verify-first) | 1.5 | a) CC audit report `docs/reports/P5_0_GATEWAY_AUDIT.md` (4-step audit per pre-LIVE protocol) → b) Michael decision (D-093.Q1 lock) → c) delete non-canonical path + 3 dead executor stubs → d) update tests to import from canonical only |
| **P5-1** | DLL `sc.SubmitOCOOrder()` (DEMO) | 2.0 | Replace TODO at `MES_AI_DataExport.cpp:813-816` · bracket order entry+stop+T1 · only fires when payload `"mode":"demo"` · returns real `sc_order_id` |
| **P5-2** | DLL result mapping | 1.0 | Replace `ACK_*` placeholders with `FILLED`/`REJECTED`/`PARTIAL`/`WORKING`/`CANCELLED` + `fill_price`/`fill_qty`/`error_code` |
| **P5-3** | Backend LIVE wiring | 0.5 | `_execute_live()` writes command file (currently stub) · gated by `BRIDGE_LIVE_ENABLED=1` env var (default off) |
| **P5-4** | Position reconciliation | 1.5 | DLL T2.4 new export `position_state.json` from `sc.PositionData` · backend `services/position_reconciler.py` raises `DRIFT_ALERT` |
| **P5-5** | Order modification | 1.0 | DLL handles MODIFY_STOP/MODIFY_TARGET/ARM_BE/SCALE_OUT/BAILOUT via `sc.CancelOrder()` + new `sc.SubmitOrder()` |
| **P5-6** | Heartbeat + watchdog | 0.5 | DLL writes `dll_heartbeat.json` every bar · backend `services/dll_watchdog.py` alerts if `last_seen > 30s` |
| **P5-7** | Bridge integration | 1.0 | Wire `TradeCommandHandler` in `bridge/v9_startup.py` (no code change in handler) · add `trade_handler_alive` health metric |
| **P5-8** | End-to-end UAT | 1.0 | Three mode runs on DEMO account (SHADOW · DEMO · LIVE-on-DEMO-acct with `BRIDGE_LIVE_ENABLED=1`) · verify all 4 UAT axes |

### Dependencies + ordering

- **P5-0 BLOCKS all others** — canonical path must be locked first.
- **P5-1, P5-7 can run in parallel** (DLL work + bridge wiring · independent).
- **P5-2 depends on P5-1** — result mapping needs real order IDs to map.
- **P5-3 depends on P5-1** — LIVE wiring must point to a real DLL handler.
- **P5-4, P5-5, P5-6 are post-P5-2** — they extend the working DEMO path.
- **P5-8 last** — full ladder UAT.

### Sub-decisions deferred to verify-first (Michael action items)

| Q | Decision | Trigger |
|---|----------|---------|
| D-093.Q1 | Gateway canonical = `backend/v9/gateway/` OR `services/trading_gateway/` | After CC delivers P5-0a audit report |
| D-093.Q2 | Sierra DEMO account identifier | Before P5-1 execution |

### Forbidden moves (from D-093)

- 🛑 Do NOT delete `bridge/trade_commands.py`
- 🛑 Do NOT call `sc.SubmitOrder()` in LIVE path before P5-3
- 🛑 Do NOT assume `PA-APEX-125218-01` is correct DEMO account (placeholder · Michael to confirm)
- 🛑 Do NOT skip P5-0 (other gateway may contain risk_validator wiring worth absorbing)
- 🛑 Do NOT modify `MES_AI_DataExport.cpp` outside lines 813-815 (P5-1) and the new T2.4 (P5-4) and T2.5/T2.6 (P5-5/P5-6) blocks — `sc_study/` is anti-regression per CLAUDE.md

### Cross-system impact

- S1 / S5 / S6 (observers): no change.
- S2 D-091 §Exit assumes OCO bracket — P5-1 satisfies the assumption.
- S3 D-089 routes to gateway — same OCO benefit.
- S4 D-092 Pipeline 2 deliverable depends on P5-1 (S4 fires need to reach Sierra).
- TradeManager Pkg 6 hooks for `MODIFY_STOP` + `ARM_BE` become real (P5-5) rather than logged-only.

### Output deliverables (per package)

- P5-0: `docs/reports/P5_0_GATEWAY_AUDIT.md`
- P5-1..P5-8: `docs/reports/PIPELINE_5_PKG_X_REPORT.md` per package
- Final: `docs/reports/PIPELINE_5_E2E_UAT.md` (P5-8 deliverable)

---

לא חוסם Pipeline 1 (S2 D-091) · Pipeline 2 (S4 D-092) · Pipeline 3 (S1 verify) · Pipeline 4 (S3 verify) — אבל **חוסם** SHADOW gate (P-S0) ו-DEMO gate · כי בלי P5-1 אין trade שמגיע לחשבון.

---

## 11 · Anti-patterns — אסור

- ❌ "While I'm here" refactors
- ❌ Push ל-main (D-067)
- ❌ הסרת `if mode == "LIVE":` safety net ב-S3
- ❌ הפעלת services במהלך stability audit
- ❌ Commit `*.pyc` / `__pycache__/`
- ❌ Cursor כותב code ש-CC יכול לכתוב
- ❌ Networking ל-cloud בלי אישור
- ❌ אסור לדלל הערות מ-spec נעול · byte-for-byte

---

## 12 · Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Spec drift תוך כדי dev | HIGH | spec lock-once policy · changes רק דרך D-XXX |
| 2 | CC hallucinated APIs | MED | mega prompt whitelist enforces |
| 3 | Silent excepts | HIGH | mega prompt forbids · Cursor adversarial scan G3 |
| 4 | Parallel streams stomp | MED | scope paths whitelist · pull rebase before stream start |
| 5 | SHADOW soak finds critical bug | HIGH | bug-fix budget 30-50% per package |
| 6 | Michael overload | MED | sequencing: spec locks 1+3 first |
| 7 | Master Summary drift from chat | MED | chat = source of truth · Master = reference |
| 8 | Pkg 6 extensibility insufficient — future rule needs core change | MED | Cursor adversarial review at G3 of Pkg 6 — must add 1 unit-test "future-rule" stub |

---

*End of plan V2 · Cursor agent · 2026-05-23 17:30 IL*
