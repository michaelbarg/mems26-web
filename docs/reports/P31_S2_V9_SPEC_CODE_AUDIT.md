# P31 — S2 V9 Spec ↔ Code Audit

**Date:** 2026-05-21 · **Branch:** `stabilize/mems26-local-truth-2026-05-16` (per terminal cwd)
**Authority:** V9 (LOCKED 10/5/2026) — pre-10/5 trees ARCHIVED
**Mode:** READ-ONLY · evidence-based · file:line citations
**Scope:** S2 5-min Tree V3.3 (Drive `1dP8x4vaat49BAw0L1DgOBTBqQ4Ci1YllUoWTwoy1DSQ`)

---

## §0 · Spec source resolution

The Drive doc is auth-gated; export-as-text returns a Google sign-in page,
not the document body. This audit therefore uses the **local V3.3 chain**:

| Source | Path | Role |
|---|---|---|
| Compliance manifest | `backend/v9/systems/five_min/compliance_manifest.yaml` | Declares spec_version V3.3 + 8 nodes + status |
| Master Index V2 | `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` | Confirms Drive ID `1dP8x4vaat49…` ↔ S2 V3.3 |
| Pre-Wave audit | `docs/reports/AUDIT_PROMPT_3b-S2.md` | Wave 0 maps V3.3 §Stage A/B/C/D/E to code |
| MEGA report | `docs/reports/REPORT_S2_MEGA_FINAL.md` | Final 67-test wire-up + V3.3 stages claim COMPLETE |
| Constitution V3 FINAL | `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | T1 4-bar Reactive/Initiative narrative |
| Designer spec | `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` § S2 | Endpoint contracts, file map |

**OPEN QUESTION FOR MICHAEL (Q1):** the verbatim Drive V3.3 doc is not
mirrored locally. The above chain is consistent with V3.3 stages, but I
cannot diff line-by-line against the Drive source. If you want a strict
verbatim diff, paste the V3.3 body into a local `docs/spec_authority/S2_V3_3.md`
or use `scripts/drive_sync_upload.py` in **download** direction (the script
today only uploads).

---

## §1 · Spec node map · PASS / DRIFT / MISSING

Cross-reference of compliance_manifest.yaml nodes + Tree V3.3 stages
documented in `AUDIT_PROMPT_3b-S2.md` against the live runtime path:

| # | V3.3 Node | Manifest claim | Code present? | **Wired into runtime?** | Verdict |
|---|---|---|---|---|---|
| 1 | T1Setup output schema (D-041) | IMPLEMENTED | YES — `output_schema.py` (T1Setup) | YES via `setup_emitter` | **PASS** |
| 2 | Reactive 4-bar (LONG / SHORT) | IMPLEMENTED | YES — `five_min_system.py:290-342` | YES (`process_bar`) | **PASS (with sub-drift, see §3)** |
| 3 | Initiative 4-bar (LONG / SHORT) | IMPLEMENTED | YES — `five_min_system.py:344-397` | YES (`process_bar`) | **PASS (with sub-drift, see §3)** |
| 4 | COT vs AMT constraint | IMPLEMENTED | YES — direct module `cot_amt.py` + HTTP fallback | Mixed: prod uses `_get_cot/amt_from_footprint` (HTTP/in-process), `cot_amt.py` is **only used in tests** | **DRIFT** |
| 5 | S/R proximity (Reactive gate) | IMPLEMENTED | YES — `sr_proximity.py` (68 LOC + 4 tests) | **NOT WIRED** — no caller in `process_bar` or `setup_emitter` | **DRIFT** |
| 6 | Layer 3 cluster + empty zone | PARTIAL | Cluster module exists; `setup_wrapper.py` graceful degradation written | **NOT WIRED** in `process_bar` (uses bar-extreme stops at line 506, not cluster/empty zone) | **DRIFT** |
| 7 | `/api/v9/five_min/fire` endpoint | IMPLEMENTED | YES — `backend/v9/api/v9/five_min/routes.py:37-54` | Read endpoint only — does not trigger fires | **PASS** |
| 8 | Anti-pattern AP1 (no bypass of pre_fire_validator) | PARTIAL | `setup_emitter.py:81` runs validator | YES (validator at L81) **but** patterns can also fire via `chart_5min/detector.py` route which uses `pre_fire_routes.py` separately | **PASS at primary path · OPEN at secondary path** |
| 9 | §Stage A — First Hour Buffer (4-12 bars dynamic) | (not in manifest) | YES — `first_hour_buffer.py:35-79` (5 states: ACCUMULATING / EARLY / DEVELOPING / MATURE / COMPLETE) | **NOT WIRED** in `FiveMinSystem.process_bar` — only used by tests (`tests/test_first_hour_buffer.py`) and `chart_5min/detector.py` has its own different bands | **DRIFT (critical)** |
| 10 | §Stage A — Opening Choppiness (0-100) | (not in manifest) | YES — `choppiness.py` (3 components, 0-100) | **NOT WIRED** | **DRIFT** |
| 11 | §Stage B — Q0 Pre/Post-Lock dispatcher (10:30 ET) | (not in manifest) | YES — `q0_dispatcher.py` (uses `market_clock.now_et()`) | **NOT WIRED** in `process_bar` — mode set via `SessionClassifier` (D-083) instead | **DRIFT** |
| 12 | §Stage C — First Hour Matrix (5 OT × direction) | (not in manifest) | YES — `first_hour_matrix.py:20-36` (5 OT keys × 2 dirs) | **NOT WIRED** | **DRIFT** |
| 13 | §Stage D — Confluence count (max 4) | (not in manifest) | YES — `confluence.py` (+1 base/+1 OT/+1 KZ/+1 ref/-1 chop) | **NOT WIRED** in `process_bar` — `last_confluence` is stored but never computed via this module (`five_min_system.py:523` sets it from raw pattern conf×100) | **DRIFT** |
| 14 | §Stage E — 10:30 transition to Day Type Mode | (not in manifest) | YES — `q0_dispatcher.is_transition_bar()` exists | Transition is handled by `SessionClassifier.classify().session == CASH_HOURS` at `five_min_system.py:201-203` — **uses different timing source** than V3.3 spec but functionally equivalent | **PASS (alternate impl)** |
| 15 | Quality Tier H/M/L (S5 TPO location) | IMPLEMENTED | YES — `quality_tier.py` (HIGH=3 / MEDIUM=2 / LOW=1) | YES via `setup_emitter` | **PASS (with sizing-clamp drift, see §3)** |
| 16 | time_stop mapper (S1 Day Type) | IMPLEMENTED | YES — `time_stop_mapper.py` (reads `targets_table.get_targets`) | YES via `setup_emitter` | **PASS** |
| 17 | pre_fire_validator chain (M18 · D-063) | IMPLEMENTED | YES — `backend/v9/shared/pre_fire_validator.py` | YES — **VERIFIED at `setup_emitter.py:81`** (per Michael's anchor) | **PASS** |

**Summary:** 8 PASS · 7 DRIFT · 0 MISSING.

---

## §2 · Cross-check on Michael's two V3.3 anchors

### Anchor 1 — "First Hour Buffer (4-12 bars dynamic per V3.3)"

**VERIFIED, with one architectural drift:**

```18:32:backend/v9/systems/five_min/first_hour_buffer.py
class BufferState(str, Enum):
    ACCUMULATING = "ACCUMULATING"   # bars 1-3, no patterns
    EARLY = "EARLY"                 # bars 4-6, reactive only
    DEVELOPING = "DEVELOPING"       # bars 7-9, reactive + initiative
    MATURE = "MATURE"               # bars 10-12, all patterns
    COMPLETE = "COMPLETE"           # bar 13+, buffer done
```

The 4-12 dynamic bands are present and tested (`tests/test_first_hour_buffer.py`,
5 tests). However:

- **DRIFT-A:** The class is **never imported** by `five_min_system.py` (the
 production runtime). Only consumers are `confluence.py` (which is itself
 not wired) and the test file. Live `process_bar` enforces only the
 minimum-4-bar guard at `five_min_system.py:303` and `:357`.
- **DRIFT-B:** `chart_5min/detector.py:212-221` (`_first_hour_eligible`)
 implements a **different** band scheme (`bc < 4 / < 6 / < 10`, 3 bands
 instead of 5). This is the band scheme used by the EventDispatcher path.
- **DRIFT-C:** Module docstring (`first_hour_buffer.py:1`) says "Tree V3.3
 §Stage B" but Wave 0 audit says "§Stage A" (`AUDIT_PROMPT_3b-S2.md:137`).
 Minor doc drift.

### Anchor 2 — "pre_fire_validator chain (already VERIFIED at setup_emitter.py:81)"

**VERIFIED at line 81 exactly:**

```70:85:backend/v9/systems/five_min/setup_emitter.py
    # Validate via pre_fire_validator (M18 · D-063)
    req = FireRequest(
        system_id=setup.system_id,
        direction=setup.direction,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        t1_price=setup.t1_price,
        t2_price=setup.t2_price,
        time_stop_minutes=setup.time_stop_minutes,
        confidence=setup.confidence,
    )
    resp = validate_fire(req)

    if not resp.valid:
        logger.warning("[S2] pre_fire_validator REJECTED: %s", resp.fail_reason)
        return None
```

Validator runs 5 explicit logical checks + 4 implicit Pydantic field
constraints (system_id enum, direction enum, confidence range, time_stop range)
giving the **7 checks claimed in the docstring** at
`backend/v9/shared/pre_fire_validator.py:5-12`. The wiring is correct.

**OPEN QUESTION FOR MICHAEL (Q2):** the docstring says "7 checks" but only
3 are coded as branches in `validate_fire`; the other 4 are enforced by
Pydantic at request construction. Functionally equivalent, but if a caller
ever bypasses Pydantic (e.g. raw dict), only 3 checks run. Is that an
acceptable trade-off, or should `validate_fire` re-assert all 7 explicitly?

---

## §3 · Sub-drifts inside the patterns themselves

### DRIFT-3.1 · Sizing clamp at `setup_emitter.py:47`

```41:48:backend/v9/systems/five_min/setup_emitter.py
    # Quality tier from TPO location
    price_for_tier = current_price or entry_price
    quality_tier, sizing = get_quality_tier(price_for_tier, tpo_data=tpo_data)

    # S5 TPO quality is advisory context. It may reduce size, but only the
    # explicit pre_fire validator below can reject the setup at this layer.
    sizing = max(1, sizing)
```

`quality_tier.py:53` returns `('LOW', 1)` for "outside value area" — never 0.
But `first_hour_matrix.py:18` defines `0.0 = skip`. The matrix's "skip"
semantic exists in code but cannot reach this clamp because the matrix is
not wired into `setup_emitter`. **Open spec question:** does V3.3 want
"LOW = 1 contract advisory" or "OT-mismatch = SKIP"? Today both possibilities
exist as separate modules but neither produces a true zero-size setup.

### DRIFT-3.2 · S6 zone naming mismatch in `confluence.py:28`

```27:28:backend/v9/systems/five_min/confluence.py
KILLZONE_ENDPOINT = "http://localhost:8000/api/v9/killzone/current"
HIGH_EDGE_ZONES = {"NY_OPEN_VOLATILITY", "NY_PRIME", "PM_PRIME"}
```

Compared to S6's actual zone names per
`docs/architecture/for_designer/02_SYSTEMS_SPEC.md:478-486`:
`LONDON_OPEN, NY_AM, LUNCH, NY_PM, LONDON_CLOSE, WEEKEND` — the
HIGH_EDGE_ZONES set will **never match** in production. Even if `confluence.py`
were wired, the +1 killzone bonus would never fire. (Mitigated by the fact
that `confluence.py` is currently un-wired anyway, but this is a latent bug
to fix when wiring proceeds.)

Additionally, `confluence.py:60` reads `killzone_data["current_zone"]["name"]`
but S6 returns `{"zone": "NY_AM", "edge_class": "A", ...}` — schema also
doesn't match. Same module, two field-name mismatches.

### DRIFT-3.3 · Silent failures violate pre-LIVE protocol

`first_hour_matrix.py:46`, `quality_tier.py:60`, `confluence.py:81`,
`five_min_system.py:227`, `:234`, `:474` all use the pattern:

```py
try: ... except Exception: ... return None / {}
```

with no logging. Per `CLAUDE.md` § "No silent failures" and
`.cursor/rules/mems26-pre-live-protocol.mdc` § "Process Discipline" → these
should be `logger.warning` (rate-limited) before LIVE. Not a P31 blocker
but flagged for the pre-LIVE checklist.

### DRIFT-3.4 · Two parallel S2 implementations

| Path | Entry point | Active in production? | Has V3.3 stages wired? |
|---|---|---|---|
| **A · `five_min/`** | `FiveMinSystem.process_bar` (subscribed via BarRouter at `backend/main.py:88`) | **YES — primary firing path** | **NO** — bypasses Q0 / FHB / FHM / Choppiness / Confluence / SR / setup_wrapper / cot_amt direct |
| **B · `chart_5min/`** | `Chart5MinSystem.analyze` via `init_event_dispatcher` (`backend/v9/app.py:294`) | YES — generates `Signal` objects through EventDispatcher | YES — full V3.3 flow with **own** chop / confluence / matrix implementations (different from `five_min/` siblings) |

These are **two parallel V3.3 implementations** with subtly different band
schemes (FHB 4/6/9/12 vs chart_5min 4/6/10), different chop scoring, and
different confluence formulas (`chart_5min`'s adds `+2 tier_34_confirms`
and `+1 woodies_cci` not present in `five_min/confluence.py`). Only **A**
auto-routes to the gateway (`five_min_system.py:585`); **B**'s `Signal`
objects flow into the EventDispatcher signal queue, not the trading gateway.

The compliance manifest only describes path A. Path B is referenced in
`02_SYSTEMS_SPEC.md:140-141` (`/api/v9/chart_5min/state`) but **the
`chart_5min/api.py` router is NOT mounted in `backend/v9/app.py`** —
the documented endpoint is dead. Verified by inspection of `app.py:10-30`
imports.

**OPEN QUESTION FOR MICHAEL (Q3):** is path B (`chart_5min/`) intentionally
kept as legacy SHADOW analytics, or should it be deleted? Today it doubles
CPU on every bar (two full pattern runs) without affecting fire decisions.
This is the single biggest drift in the audit.

---

## §4 · Architecture diagram (actual current runtime, not aspirational)

```
                BarRouter "5min" event
                            ↓
              ┌─────────────────────────────┐
              │ FiveMinSystem.process_bar   │  five_min_system.py:484
              │ (no Q0, no FHB, no FHM,     │
              │  no Choppiness, no SR gate, │
              │  no Confluence)             │
              └─────────────┬───────────────┘
                            │
              ┌─────────────▼───────────────┐
              │ _detect_reactive            │  L290 (4-bar + COT/AMT/belly)
              │ _detect_initiative          │  L344 (4-bar + expansion)
              └─────────────┬───────────────┘
                            │ (direction, conf, info)
              ┌─────────────▼───────────────┐
              │ calculate_size              │  L401 — full/half/reject
              │ (S2 internal, no x-system)  │
              └─────────────┬───────────────┘
                            │
              ┌─────────────▼───────────────┐
              │ DB persist V9FiveMinSetup   │  L536-553
              └─────────────┬───────────────┘
                            │
              ┌─────────────▼───────────────┐
              │ emit_t1_setup               │  setup_emitter.py:23
              │  ├─ get_quality_tier (S5)   │  :43
              │  ├─ sizing = max(1, …)      │  :47   ← see DRIFT-3.1
              │  ├─ get_time_stop (S1)      │  :50
              │  ├─ build T1Setup           │  :53
              │  └─ validate_fire (M18)     │  :81   ← Michael's anchor 2
              └─────────────┬───────────────┘
                            │ valid T1Setup
              ┌─────────────▼───────────────┐
              │ gateway.route_setup         │  five_min_system.py:585
              │ (ShadowExecutor, mode=…)    │
              └─────────────────────────────┘

NOT REACHED IN THIS PATH (modules + tests exist, never called):
   q0_dispatcher.py · first_hour_buffer.py · first_hour_matrix.py
   choppiness.py · confluence.py · sr_proximity.py · setup_wrapper.py
   cot_amt.py (direct Sierra read)

PARALLEL PATH (chart_5min/, generates Signals only — does NOT fire):
   Chart5MinSystem.analyze ──→ Chart5MinDetector.process_bar ──→ Signal
   (full V3.3 stages with different band/chop/confluence formulas)
```

---

## §5 · Pre-LIVE risk register for S2

| Risk | Severity | Evidence | Mitigation |
|---|---|---|---|
| V3.3 stage modules unused → confluence/choppiness never gate fires | HIGH | §1 nodes 9-13 | Wire FHB/FHM/Conf/Chop/SR into `process_bar` before LIVE, OR formally archive them and update manifest |
| Two parallel S2 paths burn CPU + diverge | MEDIUM | §3.4 | Delete `chart_5min/` path or document it as legacy |
| Killzone naming mismatch in confluence | LOW (currently un-wired) | §3.2 | Fix when wiring confluence |
| Silent excepts on TPO/Killzone fetch | LOW | §3.3 | Replace with `logger.warning` before LIVE |
| `chart_5min/api.py` documented but not mounted | LOW | `backend/v9/app.py:10-30` vs `02_SYSTEMS_SPEC.md:140` | Either mount the router or remove from designer spec |
| Spec docstring drift (Stage A vs B) | TRIVIAL | §2 anchor 1 DRIFT-C | Doc-only fix |

---

## §6 · Recommended next steps (read-only audit closes here)

1. **Decide path A vs path B** (Q3 above). Until decided, don't add code.
2. **Optionally save the V3.3 Drive doc into `docs/spec_authority/S2_V3_3.md`**
 so future audits can run a verbatim diff.
3. **Run `pytest tests/v9/systems/test_five_min/ -q`** to confirm the
 67 tests in `REPORT_S2_MEGA_FINAL.md:25-33` still all pass on this branch.
 (Not run by this audit per READ-ONLY scope.)
4. **Stop here for Michael's strategic call** — DRIFTs identified in §1
 nodes 9-13 are non-trivial enough to warrant a stop/go conversation
 before any wiring change.

---

## §7 · Open questions for Michael (consolidated)

- **Q1** — Drive V3.3 spec is auth-gated. OK to proceed with the local
 chain-of-custody (compliance_manifest + AUDIT_PROMPT_3b-S2 + MEGA_FINAL),
 or do you want to paste the verbatim V3.3 body locally first?
- **Q2** — `pre_fire_validator` 7-check semantics: explicit-all vs
 Pydantic-implicit. Acceptable as-is?
- **Q3** — Path A (`five_min/`) vs Path B (`chart_5min/`): which is
 authoritative for V9 LIVE? Today they coexist with diverging V3.3 formulas.
- **Q4** — Does V3.3 specify "LOW tier = 1 contract advisory" or
 "OT-mismatch = 0 contract skip"? Code today implements both as separate
 modules but only the advisory clamp is reachable.
- **Q5** — Is the `chart_5min/api.py` router (not mounted in `app.py`)
 supposed to be live? Frontend `02_SYSTEMS_SPEC.md` documents the endpoints
 but they 404 today.

---

## Footer

```
   ─────────────────────────────────────────
   📊 STATUS — P31 Task 1 of 3
   ─────────────────────────────────────────
   Current Phase: P31 — Strategic V9 Audit
   Current Task:  Task 1 — S2 V9 Spec ↔ Code Audit (this report)
   Verdict:       8 PASS · 7 DRIFT · 0 MISSING (17 nodes audited)
   Top drift:     V3.3 stages 9-13 exist but un-wired in production
   Anchor 1:      ✓ first_hour_buffer 4-12 verified
   Anchor 2:      ✓ pre_fire_validator at setup_emitter.py:81 verified
   Read-only:     ✓ no code changes
   Next concrete: Michael's call on Q3 (path A vs B) before any wiring
   ─────────────────────────────────────────
```

## §8 · Refresh — post-15:30 commits (2026-05-21 PM verification)

Three commits landed on `stabilize/mems26-local-truth-2026-05-16` between
this audit's first draft and the V9-anchored re-prompt at ~15:36 IL. Each
is checked against the audit's findings.

| Commit | What it changed | Effect on this audit |
|---|---|---|
| `5b75101` `feat(day_type): extract prev_day loader …` | New module `backend/v9/systems/day_type/prev_day.py` | Out-of-scope for S2; no audit verdict changes |
| `12b376f` `[P31-02b] FiveMinSystem in-process footprint` | Added `set_footprint_system()` (`five_min_system.py:63-72`) + `_footprint_state()` helper (`:216-235`) + redirected `_compute_location_vs_poc` to `_load_sierra_tpo()` direct read (`:443-475`) | Affects nodes 4 (COT/AMT) and DRIFT-3.4 — see below |
| `0f5960d` `[P31-02b] wire-up FiveMinSystem ← footprint_system` | 7 lines in `backend/main.py` injecting `app.state.footprint_system` after gateway wire-up | Wires the in-process helper into production startup |

### Re-verification of two anchors

**Anchor 1 — First Hour Buffer (4-12 dynamic):** `first_hour_buffer.py`
unchanged; lines 18-32 still define ACCUMULATING/EARLY/DEVELOPING/MATURE/COMPLETE
bands. **DRIFT-A still holds** — `five_min_system.py:484-606` (`process_bar`)
does not import or call this module. Confirmed by re-reading the full
`process_bar` body at `five_min_system.py:484-592`.

**Anchor 2 — pre_fire_validator at line 81:** Re-read
`backend/v9/systems/five_min/setup_emitter.py:70-85` — `resp = validate_fire(req)`
is at line 81 exactly. **PASS unchanged.**

### Updates to §1 verdict table

| # | V3.3 Node | Previous verdict | Refreshed verdict | Reason |
|---|---|---|---|---|
| 4 | COT vs AMT constraint | DRIFT (HTTP fallback only) | **DRIFT (lessened)** — in-process path now wired via `_footprint_state()` `:216-235`; `_get_cot_from_footprint` `:280-282` and `_get_amt_from_footprint` `:284-286` are 2-liners that hit in-process when injected | The 8s SLOW symptom is gone post-wire-up, but the **production runtime still uses Footprint System helpers** rather than the standalone `cot_amt.py` module that the manifest cites (`backend/v9/systems/five_min/cot_amt.py` — still **only used in tests**). Manifest evidence path is still inaccurate. |
| (n/a) | DRIFT-3.4 — two parallel paths | Open | **Unchanged** — `chart_5min/` still parallel, `chart_5min/api.py` still un-mounted in `backend/v9/app.py`. The in-process refactor only touched Path A. |

### Sub-drift status after refresh

| Drift | Pre-12b376f | Post-12b376f | Notes |
|---|---|---|---|
| 3.1 sizing clamp `setup_emitter.py:47` | open | unchanged | `sizing = max(1, sizing)` still at line 47 verbatim |
| 3.2 S6 zone naming mismatch in `confluence.py:28` | open | unchanged | `confluence.py` still un-wired regardless |
| 3.3 silent excepts (no logging) | open | **partially mitigated** | `_footprint_state()` `:227` now has explicit `except Exception: return {}` but still no log. `_compute_location_vs_poc` `:474` still silent. Pattern persists. |
| 3.4 two parallel paths | open | unchanged | See above |

### New observations introduced by P31-02b

- `_footprint_state()` `:216-235` adds a **graceful HTTP fallback** when
  `_footprint_system` is `None`. This is correct defensive coding for tests
  but means the 8s SLOW symptom can silently re-appear if the wire-up at
  `backend/main.py` is removed or bypassed. Recommend adding a
  `_logger.warning("[FiveMin] HTTP fallback in use — wire-up missing")`
  on first fallback hit (rate-limited) per pre-LIVE protocol §"No silent failures".
- `_compute_location_vs_poc` `:443-475` now imports `_load_sierra_tpo` from
  `backend/v9/api/v9/tpo_routes` (a route handler module). This is the right
  **data source** but it cross-imports an API module from a system module —
  a layering inversion. Functionally fine; flagged for future cleanup.

### Refreshed summary

**No change to audit verdict total: 8 PASS · 7 DRIFT · 0 MISSING.**
DRIFT severity reduced for node 4 (COT/AMT) but classification stands.
P31-02b improves runtime performance, **not spec compliance**.

### Q3 (path A vs B) — still the most important strategic question

The §3.4 finding remains the single biggest drift. Until Michael answers
Q3, we are running two parallel V3.3 implementations with different formulas
on every bar. The in-process refactor reduced the **CPU cost** of Path A but
did not eliminate Path B nor reconcile their pattern outputs.

---

*End of P31_S2_V9_SPEC_CODE_AUDIT.md · 2026-05-21 · Cursor Strategic Partner · Refreshed 15:36 IL*
