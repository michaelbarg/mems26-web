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
- [ ] T2.14 — Cluster Identification
- [ ] T2.15 — Empty Zone Identification
- [ ] T2.16 — Entry Execution Logic
