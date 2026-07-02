# CC Prompt — 2026-07-02 · Restart + Verify + Commit Cowork docs

**Paste-ready prompt for Claude Code. Prepared by Cowork 2026-07-02 ~03:00 CT (pre-market).**

---

You are CC on Michael's Mac, repo `~/Downloads/mems26_web_git`. Read `CLAUDE.md` and
`docs/handoff/CC_HANDOFF_CONTRACT.md` first, then execute
`docs/handoff/CC_FINALIZE_WIP_AND_RESTART_2026-07-02.md` with these **state updates**
(verified by Cowork 2026-07-02, git HEAD e7cfca0):

## State updates — do NOT redo finished work
1. **Step 1 of the handoff is already committed:** `d6c7648` (S2 bar-key normalization),
   `69051a6` (Woodies Mechanism-C), `e7cfca0` (docs). Do not re-implement.
   **Remaining from Step 1:** verify `69051a6` carries a regression test proving Mechanism-C
   cannot double-detect/double-fire the same `bar_ts` on a non-new-bar push. If no such test
   exists — write it BEFORE the restart (anti-tautological: assert on emitted-fire count for a
   replayed duplicate push, not on internals).
2. **NEW — commit Cowork's docs-only working tree (~132 files):** index refresh
   (`SYSTEM_INDEX.md` + 109 `_INDEX.md`, regenerated 07-02), `docs/spec_authority/PATTERN_RECONCILIATION_2026-07-02.md`,
   `docs/SYSTEM_TREE.html`, `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`, and this file.
   Review `git status` — **everything should be docs/index only. If ANY code file shows
   modified — STOP and ask Michael** (do not commit blind). Suggested message:
   `docs: index refresh + pattern reconciliation + system tree (Cowork 2026-07-02)`.
   End state: `git status` clean.

## Then execute Steps 2-3 of the handoff as written
3. **ONE clean restart** — window is open now (pre-market; RTH opens 08:30 CT).
   Check no duplicate listener on 127.0.0.1:8000, then
   `launchctl kickstart -k gui/$(id -u)/com.mems26.backend`.
4. **Post-restart verification — paste RAW output (Rule 5):**
   (a) `[env_loader]` boot-line: `FIXED_CONTRACTS_3=1 · DAYTYPE_TARGETS_STRUCTURAL=1 ·
   DAYTYPE_POSITION_GATE=0`, `OPPOSITE_EXIT_V1` unset.
   (b) warm-start: Woodies `buf=50`, `day_type≠UNKNOWN`, VA present, `hydrate_demo_slot` logged.
   (c-e) during RTH after real fires: first `trade_command.json` shows `"contracts":3`
   (especially a MEDIUM/LOW-tier fire) · targets structural+capped (no −92pt T1) ·
   `demo_slot` frees on a NORMAL close. Paste the JSON.

## Constraints (standing)
- Do NOT touch `.env`/flags/standing decisions. Expected state: `DAYTYPE_POSITION_GATE=0` +
  `DAYTYPE_PLAYBOOK=1`. **Known consequence (PATTERN_RECONCILIATION F-1): with gate=0 the
  playbook matrix is ACTIVE at the gateway (SKIP cells enforce; REDUCED is inert).** This is
  documented and awaiting Michael's D-2 ruling — do not "fix" it, do not flip flags.
- Read `docs/spec_authority/PATTERN_RECONCILIATION_2026-07-02.md` for awareness. **D-1..D-9
  await Michael. Do NOT implement the resolver completion (F-2 / work-queue P1) without his
  D-3 sign-off.**
- No `.env`/DLL/LaunchAgent edits expected; if one becomes necessary — `scripts/mems26_snapshot.sh` first.
- After verification: update `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (roadmap-auto-update
  rule) with the raw evidence, and end your report with a mandatory **NOT-DONE** section.
