# FULL INVENTORY — MEMS26 V9

**Date:** 2026-05-16  
**HEAD:** `3d9353a` — S2 Phase3 + TPO otf_clarity  
**Branch:** `feature/v9_architecture_rebuild` — **116 commits ahead of origin**  
**Authority:** Master Index V2 · Constitution V3  
**Gate:** NO SHADOW until all 6 systems complete (A–E GREEN per system)

---

## 1. Executive Summary

| System | Overall | Completion |
|--------|---------|------------|
| S1 Day Type | YELLOW | ~80% |
| S2 Five-Min T1 | YELLOW | ~85% |
| S3 Footprint T3 | YELLOW | ~75% |
| S4 Woodies T2 | YELLOW | ~70% |
| S5 TPO | GREEN | ~90% |
| S6 Killzone | YELLOW | ~80% |

**Honest aggregate: ~78% complete.** Tests: 216 pass / 27 fail compliance. 65 pass atomic (five_min+woodies).

---

## 2. Decision Tree

```mermaid
flowchart TD
    START["Development Gate"]
    START --> G1{"6 systems A–E?"}
    G1 -->|No| BUILD["Wave 1+ builds"]
    G1 -->|Yes| G2{"L0–L4 + pre_fire wired?"}
    G2 -->|No| LAYERS["Shared layer work"]
    G2 -->|Yes| G3{"E2E: Sierra→Bridge→Backend→UI?"}
    G3 -->|No| INT["Integration RUNBOOK"]
    G3 -->|Yes| G4{"Michael UAT"}
    G4 -->|Pass| SHADOW["SHADOW Day 1/30"]
    G4 -->|Fail| BUILD
```

---

## 3. Master Table: S1–S6 × A–E

### S1 Day Type (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | GREEN | manifest: 30 impl, 5 partial, 2 missing (12.5% drift) |
| B Code | GREEN | 15 .py files, state_machine.py 800+ lines, decision_matrix, triggers, zohar_rules, extensions |
| C Data | YELLOW | Bridge 5min wired; pd_high/pd_low NOT populated from bridge |
| D API | GREEN | /day_type/current 200, /day_type/v9/current 200, /day_type/health 200 |
| E Tests | GREEN | compliance 20+ pass; atomic test_day_type_targets 15/15, test_day_type_classifier 5/5 |

**Top gaps:** pd_* not wired from bridge · 2 MISSING manifest items (news re-eval, shape)

### S2 Five-Min T1 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | YELLOW | NO manifest in `five_min/` (chart_5min has one: 40 impl, 0 missing) |
| B Code | GREEN | 31 .py files; multi_bar, cot_amt, belly, poc_vol, pattern detectors, five_min_system |
| C Data | GREEN | 5min bars in DB (v9_bars_5min), footprint cells for belly |
| D API | GREEN | /five_min/current 200, /five_min/fire 200 |
| E Tests | GREEN | 65 pass (five_min module tests); compliance via chart_5min manifest |

**Top gaps:** Own manifest needed · L3 wire (provisional T1Setup) · deprecate chart_5min · /fire route in registry

### S3 Footprint T3 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | YELLOW | NO manifest in `footprint/` (tick_reversal has 44 impl) |
| B Code | GREEN | 8 .py files + signals/ (absorption, stacked_imbalance, sweep_return, exhaustion) |
| C Data | GREEN | v9_bars_tick_reversal 626K+ rows, footprint_journal |
| D API | GREEN | /footprint/current 200, /footprint/fire 200, /footprint/journal 200 |
| E Tests | YELLOW | compliance via tick_reversal (44 impl); no footprint-specific compliance |

**Top gaps:** Own manifest · pre_fire on /fire · 7-stage alignment vs signal architecture

### S4 Woodies T2 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | GREEN | manifest: 43 impl; decision_tree_stages 21 rows; WOODIES_V1_GAPS.md |
| B Code | GREEN | 22 .py files; decision_tree.py (257 lines), 9 patterns, calculate_size |
| C Data | GREEN | v9_bars_30min_woodies, v9_woodies_signals (3184+ rows) |
| D API | YELLOW | /woodies/current 200, /woodies/signals 200; **/woodies/fire 404** |
| E Tests | GREEN | compliance 20/20; atomic decision_tree 5/5 |

**Top gaps:** /fire endpoint missing · A4 touch-points PENDING · priority dispatcher · 18 terminal states

### S5 TPO (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | GREEN | manifest: 48 impl, 2 partial, 0 missing (6.7% drift) |
| B Code | GREEN | 8 .py files; tpo_system, levels, tails, single_print, ufl_ufh |
| C Data | GREEN | v9_tpo_sessions, v9_tpo_journal |
| D API | GREEN | /tpo/current 200 |
| E Tests | YELLOW | compliance v1_generated (some fail: eod, degraded mode) |

**Top gaps:** 2 PARTIAL manifest items · eod module · degraded mode gap detection

### S6 Killzone (OBSERVING + GATE)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Spec | YELLOW | manifest: 41 impl, 0 partial, 2 missing (3.8% drift) |
| B Code | GREEN | 9 .py files; killzone_system, definitions, detector, gate, zone_playbook |
| C Data | GREEN | Time-based (no DB needed); definitions.py 8 zones |
| D API | GREEN | /killzone/current 200, /killzone/health 200 |
| E Tests | YELLOW | compliance fails: news_event, pre_market_blocking, half_day (3 failures) |

**Top gaps:** 2 MISSING manifest (D-061 codified, news block windows) · 3 test failures

---

## 4. Layers + Infra

| Component | Score | Evidence |
|-----------|-------|----------|
| L0 chop_score | GREEN | `layer0/chop_score.py` exists, /chop_score/current 200 |
| L1 firing pipeline | YELLOW | S2/S3 fire, S4 fire 404 |
| L2 touch-points | YELLOW | S4 A4 PENDING; other systems don't query TP |
| L3 cluster/handoff | GREEN | `layer3/cluster.py` + `empty_zone.py` + `entry_executor.py` |
| L4 trade_manager | GREEN | `services/trade_manager/` + `bar_level_detector.py` wired |
| pre_fire_validator | GREEN | `shared/pre_fire_validator.py` (2166 bytes) |
| Gateway slots | GREEN | `gateway/trading_gateway.py` — shadow/demo/live slots |
| Bridge | YELLOW | running, 4/11 streams active (stale Sierra) |
| DLL exports | GREEN | 11 JSON in `~/SierraChart_Data/v9_export/` |
| UI (Cockpit) | YELLOW | Chart V5b working; strips/banners/pills done; some not mounted |

---

## 5. Duplicates Register

| Issue | Canonical | Legacy | Action |
|-------|-----------|--------|--------|
| Two 5-min systems | `five_min/` (31 .py) | `chart_5min/` (27 .py) | Deprecate chart_5min |
| Two JSON dirs | `SierraChart_Data/v9_export/` (11) | `SierraChart/Data/` (9) | Use v9_export only |
| Two repos | `Downloads/mems26_web_git` | `Documents/GitHub/mems26-web` | Downloads is canonical |

---

## 6. CRITICAL+SPECIFIED from Registry

Only **1** item is both CRITICAL and SPECIFIED:
- `REQ-S-5MIN-PATTERNS` — Smoke test phase gates

Registry totals: 73 IMPLEMENTED, 57 SPECIFIED, 2 IN_PROGRESS, 2 VERIFIED

---

## 7. P0 Backlog (NO SHADOW until done)

| # | Item | Est. commits | Owner |
|---|------|--------------|-------|
| 1 | S4 /woodies/fire endpoint + wiring | 1 | backend |
| 2 | S4 A4 touch-points (query 6 endpoints) | 2 | backend |
| 3 | S4 priority dispatcher + terminal states | 3–5 | backend |
| 4 | S1 pd_high/pd_low/pd_close from bridge | 1–2 | bridge |
| 5 | S1 manifest 2 MISSING (news re-eval, shape) | 2 | backend |
| 6 | S6 D-061 + news block windows (EC4) | 2 | backend |
| 7 | S2 own manifest (migrate from chart_5min) | 1 | docs |
| 8 | S3 own manifest | 1 | docs |
| 9 | S2 L3 wire (remove provisional T1Setup) | 2 | backend |
| 10 | pre_fire on all /fire endpoints | 1 | backend |
| 11 | Fix 27 compliance failures | 5–8 | tests |
| 12 | Deprecate chart_5min formally | 1 | docs |

**Total est.: 22–30 focused commits**

---

## 8. Prompt Roadmap (suggested)

```
Prompt 2:  S4 /woodies/fire endpoint + pre_fire wire
Prompt 3:  S4 A4 touch-points + priority dispatcher skeleton
Prompt 4:  S1 pd_* wiring from bridge + manifest MISSING items
Prompt 5:  S6 D-061 codified + news block + 3 test fixes
Prompt 6:  S2/S3 manifest creation (migrate from legacy)
Prompt 7:  S2 L3 wire (remove provisional)
Prompt 8:  Compliance test triage (27 failures → categorize real vs drift)
Prompt 9:  Integration RUNBOOK (Sierra → Bridge → Backend → UI verify)
Prompt 10: Michael UAT prep (screenshots + SHADOW activation)
```

---

## 9. Reconciliation

| Source | Claim | Verified |
|--------|-------|----------|
| PROJECT_TRUTH_AUDIT §2 | 216 pass / 27 fail | CONFIRMED (same run today) |
| PROJECT_TRUTH_AUDIT §2 | pre_fire EXISTS | CONFIRMED (2166 bytes) |
| WAVE1_S4_AUDIT | Decision tree RED | NOW GREEN (257 lines, 5 tests pass) |
| COMPONENT_AUDIT | S4 tree MISSING | NOW EXISTS (decision_tree.py) |
| WAVE1_S4_AUDIT | Option B approved | CONFIRMED (wired in woodies_system.py) |

---

## 10. UNKNOWN (needs Michael / Sierra)

- [ ] Sierra Chart running with latest study (live JSON timestamps fresh?)
- [ ] Bridge 4/11 streams — which 7 are stale/missing?
- [ ] Whether chart_5min code is still used by ANY caller
- [ ] Master Index V2 full text (for S4 18 terminal states)
- [ ] HFE pattern DLL export (sc_study uncommitted edits)
- [ ] Woodies /fire endpoint — intentionally missing or oversight?

---

## Appendix: Raw Command Outputs

```
HEAD: 3d9353a (116 ahead)
Manifests: day_type 30/5/2 · chart_5min 40/0/0 · woodies 43/0/0 · tpo 48/2/0 · killzone 41/0/2
Tests: 216 pass 27 fail compliance · 5 pass decision_tree · 65 pass five_min
API: 67 unique routes
Duplicates: five_min 31 .py vs chart_5min 27 .py
Bridge: running, 4 streams, 77816 bars received
Gateway: demo_slot + live_slot + shadow implemented
```
