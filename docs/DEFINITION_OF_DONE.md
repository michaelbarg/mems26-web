# MEMS26 — Definition of Done (per Prompt)

Every prompt is complete when ALL of the following are true:

## Code Quality
- [ ] All new Python files have been tested (pytest passes)
- [ ] Frontend builds cleanly (`npx next build` — zero errors)
- [ ] No test mock values (e.g. `5412.`) in production paths
- [ ] No TODO/FIXME/XXX in committed code (use GitHub issues instead)
- [ ] No secrets in committed code (API keys, tokens, passwords)

## Verification
- [ ] `./scripts/uat_prompt_N.sh` exits 0
- [ ] UAT report written to `docs/UAT_REPORTS/`
- [ ] All verification checks from prompt spec marked pass or skip (with reason)

## Integration
- [ ] Backend starts without import errors
- [ ] Bridge can import all streams without errors
- [ ] New WS endpoints reachable (verify via `/api/v9/ws/status`)
- [ ] Frontend renders dashboard without React errors

## Documentation
- [ ] `docs/PROMPT_N_REPORT.md` written with component status table
- [ ] `docs/MANUAL_STEPS_QUEUE.md` updated if Sierra changes needed
- [ ] `docs/RUNBOOK.md` updated with new start/stop/troubleshoot info

## Git
- [ ] Committed on correct branch (`feature/v9_architecture_rebuild`)
- [ ] One commit per component group (clean history)
- [ ] `git tag pre-prompt-N` created before destructive changes
- [ ] No force-push, no amend of pushed commits

## Anti-Patterns (must NOT be present)
- [ ] No `std::max`/`std::min` in DLL code (AP-T01)
- [ ] No Windows paths in DLL (AP-T03) — Mac paths only
- [ ] No `sc.GetPersistentString` — use `sc.GetPersistentSCString` (AP-T04)
- [ ] No methodology iteration mid-build (AP-M01)
- [ ] No manual UAT steps (AP-M04) — scripts must cover everything
