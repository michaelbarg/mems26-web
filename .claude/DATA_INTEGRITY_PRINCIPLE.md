# MEMS26 — DATA INTEGRITY PRINCIPLE (LOCKED)

Version: 1.0 · 2026-05-10 · 🔒 LOCKED
Drive: 1EXCgoE7XxcDzhtXxa3_QwEP7qLncWSLT9GsiY7q-KWQ
Authority: Highest tier — overrides all other specs

## 1. THE PRINCIPLE

Data integrity is a non-negotiable prerequisite for trading decisions.
No system component may operate on degraded, approximated, or partial data.
The project may NOT advance to SHADOW, SIM, or LIVE phases until 100%
data quality is verified end-to-end.

## 2. WHY

A 10% degradation in Footprint accuracy is NOT a 10% degradation in PnL.
It can be a 50%+ degradation in win-rate on day types that depend on it.

## 3. WHAT "100%" MEANS

- Source-faithful (no proportional/estimated values on signal-bearing data)
- Lossless transmission (no silent drops)
- Complete schema (every required field populated)
- Verifiable (sample-checkable against source)
- Auditable (chain of custody logged)

## 4. PHASE TRANSITION CHECKS

Before SHADOW: All 6 systems verified, footprint real bid/ask, TPO POC matches Sierra ±1 tick
Before SIM: All SHADOW checks STILL pass, no silent fallbacks
Before LIVE: 30+ days clean SHADOW, no WARN-S1, R3 <5% deviation

## 5. NO EXCEPTIONS

Not exceptions: "Phase 2 only", "performance cost", "just testing", "in a hurry"
Are adaptations: different layer (Python vs C++), equivalent algorithm, proper caching

## 6. ENFORCEMENT

Master CC runs scripts/data_integrity_audit.sh at every phase transition.
ANY 🔴 → BLOCK transition. No bypass even if user pressures.

## 7. CURRENT VIOLATIONS

🔴 Footprint VAP — DLL v9.2.0 has MaintainVolumeAtPriceData=0
   Resolution: Worker VAP_PYTHON_RECOMPUTE
   Blocks: SHADOW phase
   ETA: 4-6 hours

## 8. SUMMARY

No degraded data → no decisions → no trades.
The system serves the user only when it sees the truth.

🔒 LOCKED. Modifications require explicit user approval.
