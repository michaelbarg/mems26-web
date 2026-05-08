# MEMS26 FIRST — Decision Log

**Version**: V2  
**Status**: ACTIVE  
**Last Modified**: 8 May 2026  
**Maintainer**: Michael Barg  

---

## About This Document

Canonical decision log for the MEMS26 project. Each D-XXX entry records a significant decision with full context, reasoning, and traceability. Once **locked**, a decision can only be changed by creating a new D-XXX that explicitly supersedes it.

### Schema

Each entry follows this structure:
- **Status**: DRAFT | LOCKED | SUPERSEDED
- **Date**: When decided (YYYY-MM-DD)
- **Decided by**: Who made the call
- **Source**: Meeting, document, or conversation reference
- **Decision**: What was decided
- **Reasoning**: Why this choice
- **Alternatives considered**: What else was on the table
- **Risks**: Known risks of this decision
- **Linked**: Related decisions (D-XXX references)

---

## Prior Decisions (D-001 through D-060)

Decisions D-001 through D-060 are documented in project conversations and earlier documents. Key decisions include:

- **D-037**: Anti-pattern filters
- **D-038**: Direction-specific checklists (LONG vs SHORT)
- **D-043**: Agent architecture (12-agent system)
- **D-044**: Agent personas
- **D-049**: Suffering Side Veto rule (spec in `docs/specs/D-049_suffering_side_veto.md`)
- **D-060**: Slack integration plan

> TODO: Migrate D-001 through D-060 into this file with full schema entries.

---

## D-061: CC-First Protocol

- **Status**: LOCKED
- **Date**: 2026-05-08
- **Decided by**: Michael
- **Source**: Operational review — CC workflow optimization
- **Decision**: All infrastructure, tooling, and documentation work is done by Claude Code (CC) first. Michael reviews and approves, but does not write tools/docs from scratch.
- **Reasoning**: CC produces consistent, well-structured output faster than manual work. Michael's time is better spent on trading methodology, review, and strategic decisions. This creates a sustainable workflow where CC handles volume and Michael handles judgment.
- **Alternatives considered**:
  - Michael writes everything manually — slower, doesn't scale
  - Split work 50/50 — coordination overhead, inconsistent style
  - External contractor — cost, onboarding time, no context
- **Risks**:
  - CC may make assumptions that don't match Michael's intent → mitigated by review-before-merge protocol
  - Over-reliance on CC → mitigated by Michael maintaining full understanding of all code
- **Linked**: D-063 (Question Discipline), D-065 (CC Tiered Permissions)

---

## D-062: Secrets Handling Protocol

- **Status**: LOCKED
- **Date**: 2026-05-08
- **Decided by**: Michael
- **Source**: Post-incident review — accidental secret exposure risk
- **Decision**: CC must NEVER read, write, or reference `.env` files or any file containing API keys, tokens, or credentials. All secret management is performed manually by Michael. CC may reference environment variable names (e.g., `SLACK_BOT_TOKEN`) in documentation but never their values.
- **Reasoning**: CC operates in a terminal environment where tool outputs are logged. Secret values in CC context could be persisted in conversation logs, memory files, or committed to git. Zero-tolerance is simpler and safer than "careful handling."
- **Alternatives considered**:
  - Allow CC to read .env with masking — too error-prone, masking could fail
  - Use a secrets manager CC can query — adds complexity, still creates exposure surface
  - Encrypted .env files — CC would need decryption key, defeats purpose
- **Risks**:
  - CC can't debug environment-specific issues → mitigated by Michael providing sanitized error output
  - Slower troubleshooting → acceptable tradeoff for security
- **Linked**: D-065 (CC Tiered Permissions — .env in deny list)

---

## D-063: Question Discipline

- **Status**: LOCKED
- **Date**: 2026-05-08
- **Decided by**: Michael
- **Source**: Operational review — CC interaction patterns
- **Decision**: When CC encounters ambiguity or needs a decision that isn't documented, CC must STOP the current task, write a `BLOCKED.md` file in the task directory explaining what's needed and why, and continue to the next task. CC must not guess, assume, or "creatively work around" missing information.
- **Reasoning**: Wrong assumptions cost more than delays. A `BLOCKED.md` creates a clear async handoff — Michael can answer when available, and CC has a clean resumption point. This is especially important for weekend/offline autonomous work.
- **Alternatives considered**:
  - CC makes best guess and flags it — risks going down wrong path for hours
  - CC asks interactively and waits — blocks progress on all other tasks
  - CC documents assumption inline — easy to miss, not actionable
- **Risks**:
  - Too many BLOCKED.md files → may indicate specs are underspecified
  - Slows down individual tasks → but preserves overall quality
- **Linked**: D-061 (CC-First Protocol)

---

## D-064: Milestone Logging Protocol

- **Status**: LOCKED
- **Date**: 2026-05-08
- **Decided by**: Michael
- **Source**: Operational review — progress tracking
- **Decision**: After completing each task in an autonomous batch, CC must log: task name, commit hash, files added/modified, and line count. At batch completion, CC prints a summary table. This creates an audit trail for Michael to review progress quickly.
- **Reasoning**: When Michael is offline (weekends, mobile), he needs a fast way to assess what CC accomplished. A structured summary is faster to parse than reading git logs on a phone.
- **Alternatives considered**:
  - Git log only — requires terminal access, verbose
  - Slack notification per commit — too noisy during batch work
  - Single summary at end only — no intermediate checkpoints
- **Risks**:
  - Summary format may not capture all relevant info → iterate on format
  - Logging overhead slows CC slightly → negligible compared to task time
- **Linked**: D-061 (CC-First Protocol)

---

## D-065: CC Tiered Permissions

- **Status**: LOCKED
- **Date**: 2026-05-08
- **Decided by**: Michael
- **Source**: CC operational security review
- **Decision**: CC operates under a three-tier permission model configured in `.claude/settings.json`:
  - **Tier 0 (Auto-allowed)**: Read any file, search, edit tools/docs, git status/log/commit, run tool scripts
  - **Tier 1 (Confirmation required)**: Edit files outside tools/docs scope
  - **Tier 2 (Denied)**: Push, force operations, install packages, read/write .env, edit production code (app/backend/bridge/frontend/sc_study)
- **Reasoning**: CC needs autonomy for infrastructure work (tools/, docs/) without being able to accidentally modify production code or expose secrets. The tier system makes the boundary explicit and enforceable. Tier 0 enables weekend autonomous batches. Tier 2 prevents catastrophic mistakes.
- **Alternatives considered**:
  - No restrictions (trust CC fully) — too risky for production code
  - Restrict everything (manual approval for all) — too slow, defeats CC-First
  - Branch-based restrictions — harder to configure, doesn't prevent .env access
- **Risks**:
  - Tier boundaries may need adjustment as project grows → settings.json is easy to update
  - CC may need Tier 1 access for legitimate work → Michael approves on case-by-case basis
- **Linked**: D-061 (CC-First Protocol), D-062 (Secrets Handling)
