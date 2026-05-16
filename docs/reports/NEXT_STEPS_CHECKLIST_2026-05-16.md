# MEMS26 Next Steps Checklist — Local Truth

**Date:** 2026-05-16  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Rule:** no SHADOW until readiness gates pass. No DEMO/LIVE without Michael approval.

## Level 0 — Git Safety

- [x] Local work committed into clear commits.
- [x] Working tree clean before backup branch.
- [ ] Push backup branch to GitHub.
- [ ] Open PR for review only.
- [ ] Do not merge until Sierra/UAT gates are complete.

## Level 1 — System Truth

- [x] Full inventory updated.
- [x] Compliance and atomic suite passes: `254 passed`.
- [x] S1/S2/S3/S4/S5/S6 are traceable through local docs and manifests.
- [ ] Review compatibility shims before merge.

## Level 2 — Woodies D-074

- [x] D-074 documented: Woodies target timeframe is 5 minutes.
- [x] Impact map created.
- [ ] Implement actual 5m runtime migration:
  DLL export -> Bridge stream -> DB table -> backend subscription -> UI labels.
- [ ] Keep `woodies_30min` as legacy only if needed for replay.

## Level 3 — Execution Path

- [x] `/api/v9/woodies/fire` added.
- [x] Woodies fire path uses `pre_fire_validator`.
- [x] DEMO command writer added for `trade_command.json`.
- [ ] Manual Sierra Sim UAT: confirm Sierra reads command and returns result.
- [ ] No LIVE command path until explicit approval.

## Level 4 — Ops / Slack

- [x] One-way Slack scripts added.
- [x] Post-commit hook can send summaries.
- [ ] Configure `SLACK_UAT_WEBHOOK` or `SLACK_WEBHOOK_URL` locally.
- [ ] Send one test Slack message.
- [ ] Decide later if two-way Slack approvals are needed.

## Level 5 — UI / Designer

- [x] UI data contract created.
- [x] Active trade, system status, reason tree, and mode display are defined.
- [ ] Designer can start from mock contract.
- [ ] Connect UI to real SHADOW data only after readiness gate.

## Level 6 — Readiness Gates

- [ ] Backup PR exists.
- [ ] D-074 5m implemented and tested.
- [ ] Sierra Sim DEMO command UAT passes.
- [ ] Michael reviews SHADOW checklist.
- [ ] SHADOW enabled only after explicit approval.
- [ ] DEMO enabled only after SHADOW evidence is reviewed.
- [ ] LIVE enabled only after separate explicit approval.

