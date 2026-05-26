# CC Prompt · Phase A G3 PASS Bundle Report

**Copy-paste this entire prompt to Claude Code.** Cursor agent stays out of report drafting
per the MEMS26 reporting workflow rule.

---

## TASK

Draft a consolidated report titled **`docs/reports/PHASE_A_G3_BUNDLE_2026-05-23.md`**
that bundles the 6 Phase A packages that achieved G3 PASS today (23/5/2026) and lays out
exactly what Michael needs to do for G4 (UAT smoke trade).

Audience: **Michael** (will read it before deciding G4 cadence) + **future agents**
(needs enough context to resume Phase A work cold).

Length target: **300-500 lines.** This is a bundle/index, not 6 separate reports.

---

## SOURCE MATERIAL (READ-ONLY · do not modify)

### Primary: STATUS_BOARD amendments log

`docs/plans/STATUS_BOARD.md` — every row dated 2026-05-23 is in scope. Read the entire
amendments log (rows 188-onwards). The G3 PASS entries you must consolidate:

| Pkg | Commit chain | STATUS_BOARD row anchors |
|-----|--------------|--------------------------|
| 0 | `1c805ea` | 2026-05-23 18:15, 18:42, 18:47 |
| 1 | `dd5e2f2` | 2026-05-23 18:50, 19:00, 19:05, 19:27, 19:30, 19:32 |
| 2a | `847bb40` | 2026-05-23 19:35, 19:51, 19:55 |
| 2bc | `dfdf91f` | 2026-05-23 20:00, 20:10, 20:15, 20:30, 20:46, 20:50 |
| 3a Stream 1 | `dd9c34f` → `a58ee61` → `689ac41` | 2026-05-23 20:34, 20:38, 20:48, 20:50, 20:53, 20:55, 21:00 |
| 3a Stream 1.5 | `548f1f6` | 2026-05-23 21:05, 21:14, 21:18 |
| 3a Stream 2 | (handoff only, not yet executed) | 2026-05-23 21:42 |

### Secondary references

- `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` — V2 master plan
- `docs/decisions/D-090_PATH_A_CANONICAL.md` — drives Pkg 0
- `docs/decisions/D-091_S2_LIVE_SCOPE.md` — drives Pkg 1 + 2a + 2bc + 3a (all streams)
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` — context for what's NOT in Phase A
- `docs/handoff/DESKTOP_PKG*_HANDOFF.md` — the handoffs that drove each commit (one per Pkg)
- `git log --oneline 1c805ea^..548f1f6` to see the full commit timeline

### Verification (optional but encouraged)

You MAY run the following to verify final state, but do NOT re-do G3 reviews:

```bash
BRIDGE_TOKEN=dummy python3 -m pytest tests/v9/systems/ -q
BRIDGE_TOKEN=dummy python3 -m pytest tests/atomic/test_five_min_patterns.py -q
BRIDGE_TOKEN=dummy python3 -m pytest backend/v9/tests/test_state_machine_v9.py backend/v9/tests/e2e/test_day_type_e2e.py -q
git log --oneline 1c805ea^..548f1f6
```

Capture the final pass counts. Do NOT investigate any pre-existing failures unrelated to today's
6 packages — Cursor already verified those at baseline `dd5e2f2`.

---

## DELIVERABLE STRUCTURE

The report file must have these sections in order:

### §1 · Executive summary (≤30 lines)

- Date range, agent attribution, total commits, total tests added, final pass count.
- One sentence per package: status + commit + key outcome.
- "What Michael needs to do next" — a 3-bullet bottom-line.

### §2 · Pkg-by-pkg deep dive (6 subsections · ~40 lines each)

For each of Pkg 0, 1, 2a, 2bc, 3a Stream 1, 3a Stream 1.5:

```
### §2.N · Pkg X · <name>

**Commit:** `<sha>` <subject line>
**Files changed:** N files · +A/-B lines
**Authority doc:** D-XXX or handoff path
**G3 PASS:** YYYY-MM-DD HH:MM IL · M/M acceptance axes
**G4 status:** ⬜ pending · what Michael must do to advance

#### What it does (3-5 bullets)

#### Tests added (count + 1-line summary)

#### Known limitations / follow-ups
- Any non-blocking findings logged during G3
- Anything explicitly deferred to a future Pkg

#### G4 acceptance criteria (what UAT must verify)
- Concrete, runnable verification steps
- Expected behavior on a smoke trade or live data
```

For **3a Stream 1**, document the fix-up chain explicitly: round 1 FAIL (2 blockers + 4
informational), `a58ee61` fix-up, round 2 FAIL (1 NEW regression), `689ac41` fix-up, final PASS.
This is the lesson-rich one.

For **3a Stream 1.5**, note it was first-try clean (no fix-ups needed) and explain why
(small blast radius + explicit forbidden-zone spec).

### §3 · Cross-pkg dependency map

A small table or simple graph showing:
- Pkg 0 unblocks → Pkg 1, 2a
- Pkg 1 unblocks → 2a's family mapping bug fix · 3a tests
- Pkg 2a unblocks → Pkg 2bc
- Pkg 2bc unblocks → Pkg 3a Streams
- Pkg 3a Stream 1 unblocks → Stream 1.5 + Stream 2 (parallel)
- Stream 1.5 unblocks → retiring deprecated `DayType.Neutral`
- Stream 2 will close → D-091 entirely (final stream)

State explicitly what Stream 2 will produce (read `docs/handoff/DESKTOP_PKG3A_STREAM2_DAY_TYPE_TARGETS_HANDOFF.md` §1 + §2 for the source-of-truth scope).

### §4 · G4 (UAT smoke trade) cadence proposal

5 packages are awaiting G4. Three have NO LIVE behavior change (3a Streams) so G4 is N/A.
Two require Michael smoke trade (Pkg 1, 2a). Pkg 2bc needs smoke. Pkg 0 needs Redis decision.

Propose:
- Which to UAT first (recommended order)
- Estimated time per UAT
- What "evidence" each UAT needs (DB query / log grep / chart screenshot / WS event)
- What the GO/NO-GO decision criteria are per package

### §5 · Phase A remaining work (queued · not yet in flight)

| Pkg | Status | Blocker | ETA |
|-----|--------|---------|-----|
| 3a Stream 2 | handoff ready, awaiting CC | mega-prompt + CC | 4-6h |
| 3b · Trail logic | spec ⬜ | needs spec + handoff | TBD |
| 3c · Contract split | spec ⬜ | deps on 3a | TBD |
| 4a · Risk Critical | spec ⬜ | deps on 3 | TBD |
| 4b · Risk Tightening | spec ⬜ | deps on 4a | TBD |
| 5a/5b/5c · Patterns | spec ✅ lock 3 | needs handoffs | TBD |
| 8 · Quality V2 | spec ⬜ (Auth Table) | needs decision | TBD |
| 6 · TradeManager rewrite | spec ⬜ (deps ALL) | LAST | TBD |

### §6 · Cumulative test coverage

- Total tests in `tests/v9/systems/` before today: ~517
- Total tests after Stream 1.5: 554 passed, 1 skipped
- After Stream 2 (projected): ~572

Break it down by Pkg (how many new tests each shipped):
- Pkg 1 · adaptive_stop · 18
- Pkg 2a · 5min patterns · +11
- Pkg 2bc · footprint/patterns/validator · +14 net
- Pkg 3a Stream 1 · day_type · +24
- Pkg 3a Stream 1.5 · rescore · +9
- (Pkg 3a Stream 2 projected · +18)

### §7 · Risks & open questions

Pull from STATUS_BOARD `Risk tracker` section + Pre-flight items still ⬜:
- Pre-flight #6 (S1 Day Type verify report from Michael)
- Pre-flight #7 (S3 Footprint verify report)
- Pre-flight #11 (SPEC_LOCK_TEMPLATE V2 in progress)
- Pre-flight #17 (D-093.Q1 Gateway canonical · awaiting CC P5-0a audit)
- Pre-flight #18 (D-093.Q2 Sierra DEMO account)
- Pipeline 5 entirely blocked until P5-0 audit lands (separate workstream)

Plus: the 21 pre-existing test failures (replay/snapshot/chart_routes/test_no_shadow_demo_live)
are NOT today's regressions. Note them as known tech debt but explicitly out of Phase A scope.

### §8 · Appendix · forensic timeline

A chronological listing of all 7+ commits made today (oldest first), one per line:

```
HH:MM IL · <commit_sha> · <subject>
```

Use the actual times from STATUS_BOARD amendments log. This is the only place where the
fix-up commits (`a58ee61`, `689ac41`) appear individually as their own rows.

---

## CONSTRAINTS

1. **Do NOT re-run G3 reviews.** Cursor already passed all 6. You're consolidating, not re-judging.
2. **Do NOT modify any source code or tests.** Read-only operation.
3. **Do NOT create handoff documents** for future packages (3b, 3c, etc.). That's Cursor's job.
4. **Do NOT edit STATUS_BOARD.** That's also Cursor's job (write-side).
5. **Do NOT include `agent-transcript` references** in the report. Internal artifact.
6. **Cite commit SHAs verbatim.** First 7 chars is fine (e.g. `1c805ea`, not "the Pkg 0 commit").
7. **Cite STATUS_BOARD rows by timestamp** (e.g. "STATUS_BOARD 2026-05-23 20:48 row") so future readers can reconstruct context.
8. **No emojis** except where they already exist in source (e.g. ✅, ⬜, 🟡 from STATUS_BOARD).
9. **No marketing language.** "5 G3 PASSes in one session" is a fact; "incredible velocity" is not allowed.
10. **One file only.** Do not create supporting docs, scripts, or auxiliary files.
11. **If `docs/reports/PHASE_A_G3_BUNDLE_2026-05-23.md` already exists, ABORT and ask Michael** — do not overwrite.
12. **If you find a factual discrepancy** between STATUS_BOARD and the actual git/test state, document it inline as a `⚠️ Discrepancy note` block. Do NOT silently reconcile.

---

## ACCEPTANCE

After you write the file, run **exactly these 3 checks** and include their output in your reply
(not in the file):

```bash
wc -l docs/reports/PHASE_A_G3_BUNDLE_2026-05-23.md  # expect 300-500
rg -c "^### §" docs/reports/PHASE_A_G3_BUNDLE_2026-05-23.md  # expect ≥14 (8 sections + 6 pkg subsections)
git status docs/reports/PHASE_A_G3_BUNDLE_2026-05-23.md  # should show as untracked
```

Then in your reply to Michael:
- State the line count.
- State the section count.
- State whether you found any discrepancies (and what they were).
- State that the file is ready for Michael's review.
- Do NOT commit. Michael decides when/if to commit it.

---

## STOP SIGNALS

Abort and ask Michael if:
1. The report file already exists.
2. STATUS_BOARD doesn't show all 6 G3 PASSes you expected (Pkg 0, 1, 2a, 2bc, 3a S1, 3a S1.5).
3. Any of the 7+ commit SHAs listed above don't exist in git log.
4. The test counts don't match (e.g. `pytest tests/v9/systems/` returns < 554 passes).
5. You discover a non-trivial scope issue (e.g. a "G3 PASS" row in STATUS_BOARD that actually
   has unresolved blockers).
6. You can't decide between two interpretations of a commit's purpose — Michael resolves, not you.

---

*Prompt drafted by Cursor agent · 2026-05-23 21:55 IL · for paste-to-CC consumption.*
