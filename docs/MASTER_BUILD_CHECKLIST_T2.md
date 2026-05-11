# MEMS26 — Terminal 2 Build Checklist (DLL + Woodies + Layer 3)
# Date: 2026-05-11
# Status: IN PROGRESS

## Wave 1: DLL Restoration + Foundation
- [x] T2.1 — DLL: Live Price Export (200ms) — commit 4ae6c37
- [ ] T2.2 — DLL: Trade Command Paths Restore — BLOCKED (needs Sierra Build for T2.1 first)
- [ ] T2.3 — DLL: 15-tick Reversal Chart Config
- [x] T2.4 — System H: Woodies CCI Engine Core — VERIFIED (cci_calc.py matches DLL, 45 tests pass)
- [x] T2.5 — Woodies Auxiliary Lines — VERIFIED (CZI, SWI, LSMA, EMA34 all in cci_calc.py, tests pass)

## Wave 2: 8 Woodies Patterns (VERIFY existing)
- [x] T2.6 — ZLR (Zero Line Reject) — VERIFIED (zlr.py 144 LOC, positive+negative+edge tests pass)
- [x] T2.7 — TLB (Trend Line Break) — VERIFIED (tlb.py 130 LOC, tests pass)
- [x] T2.8 — TT (Tony Trade) — VERIFIED (tt.py 129 LOC, tests pass)
- [x] T2.9 — GB100 — VERIFIED (gb100.py 106 LOC, tests pass)
- [x] T2.10 — VEGAS (Cup & Handle) — VERIFIED (vegas.py 150 LOC, tests pass)
- [x] T2.11 — GHOST (Head & Shoulders) — VERIFIED (ghost.py 139 LOC, tests pass)
- [x] T2.12 — FAMIR (Failed ZLR) — VERIFIED (famir.py 118 LOC, tests pass)
- [x] T2.13 — HTLB — VERIFIED (htlb.py 141 LOC, tests pass)

## Wave 2 Summary
- 112 tests total across test_woodies.py (45) + test_woodies_patterns.py (67)
- All 112 pass in 0.49s
- All 8 patterns have: positive detection, negative (no signal), edge cases
- All 8 registered in detect_all_patterns() via TestDetectAllPatterns::test_all_8_detectors_registered

## Wave 3: Layer 3 Entry Execution
- [x] T2.14 — Cluster Identification (cluster.py 100 LOC, 8 tests pass)
- [x] T2.15 — Empty Zone Identification (empty_zone.py 97 LOC, 5 tests pass)
- [x] T2.16 — Entry Execution Logic (entry_executor.py 152 LOC, 14 tests pass)

## Layer 3 Summary
- 27 tests total, all pass in 0.33s
- Cluster: yellow POC + 3-level primary cluster + density + dominant side
- Empty Zone: consecutive low-volume levels + single print detection
- Entry Executor: direction-aware entry/stop from microstructure, 6 day type configs
- DAY_TYPE_TARGETS: all 6 types with T1/T2/T3/time_stop/sizing per spec C3
