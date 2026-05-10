# MEMS26 — INDEPENDENT VERIFICATION PRINCIPLE (LOCKED)

Version: 1.0 · 2026-05-11 · 🔒 LOCKED
Drive: 1g27kZkDmzBDJ68jZV2HgNgCa5ML0AWfx6ZUwYAcMktw

## THE PRINCIPLE

A Worker that built a feature CANNOT certify that feature complete.
An INDEPENDENT verifier must:
1. Read the original spec
2. Verify every spec requirement is present in the result
3. Verify nothing that worked before is broken (regression check)
4. Sign off independently — only then status moves to VERIFIED

## RULES

1. Different agent, different prompt — Worker ≠ Verifier
2. Verification artifacts mandatory: spec checklist with ✅/🔴 + evidence
3. No self-certification — Worker says "submitted", not "DONE"
4. If Verifier finds gaps → status reverts to IN_PROGRESS, Worker recalled

## WORKER LANGUAGE

Workers MUST say: "submitted for verification"
Workers MUST NOT say: "DONE", "complete", "verified"
Only Verifier can declare "VERIFIED".

## TRIGGER

U1 Phase 7.1 reported DONE with build clean, but browser showed:
- TradingView NOT replaced
- POC/VAH/VAL MISSING (regression)
- Layout not matching spec

## INTEGRATION

- §6.7 audit: Verifier spawned after every Worker
- §6.10 Registry: status=VERIFIED only after Verifier signs off
- §18 Phase gates: require VERIFIED (not just IMPLEMENTED)

🔒 LOCKED. Modifications require explicit user approval.
