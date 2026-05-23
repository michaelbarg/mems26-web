# P30 — Wave Agent Index (copy-paste prompts)

**Date:** 2026-05-20  
**Authority:** `docs/reports/P30_PRIORITY_TASK_TABLE.md`, `docs/reports/P30_ROAD_START_TO_LIVE.md`  
**Rule:** One wave gate at a time. No code agents until **Wave 0 = CC GO**.

---

## Flow

| Wave | Prompt file | Owner | Parallel with |
|------|-------------|-------|----------------|
| **0a** | [`WAVE_0_CC_VERIFY_PROMPT.md`](./WAVE_0_CC_VERIFY_PROMPT.md) | CC | 0b |
| **0b** | [`WAVE_0_MICHAEL_D087_PROMPT.md`](./WAVE_0_MICHAEL_D087_PROMPT.md) | Michael | 0a |
| **1a** | [`WAVE_1_S1_PREV_PROMPT.md`](./WAVE_1_S1_PREV_PROMPT.md) | Cursor Parent | ✅ `P30_S1_PREV_DONE.md` |
| **1b-fix** | [`WAVE_1B_D088_DEPLOY_VERIFY_PROMPT.md`](./WAVE_1B_D088_DEPLOY_VERIFY_PROMPT.md) | Other agent | ✅ `P30_D088_DEPLOY_VERIFY.md` |
| **1b** | [`WAVE_1_S1_WIRE_PROMPT.md`](./WAVE_1_S1_WIRE_PROMPT.md) | Cursor Parent | ✅ `P30_S1_WIRE_DONE.md` |
| **2** | [`WAVE_2_CLOCK_PROMPT.md`](./WAVE_2_CLOCK_PROMPT.md) | Cursor Parent | ✅ PARTIAL — `P30_P15_CLOCK_DONE.md` |
| **3** | [`WAVE_3_SHADOW_SOAK_PROMPT.md`](./WAVE_3_SHADOW_SOAK_PROMPT.md) | Michael + CC | no Cursor code |
| **4** | [`WAVE_4_PARALLEL_AUDIT_INDEX.md`](./WAVE_4_PARALLEL_AUDIT_INDEX.md) | 6× Cursor read-only | post-soak |

**Existing per-system audits (Wave 4):** `AGENT_S1_*.md` … `AGENT_S6_*.md`

**Permanent (every wave):** [`AGENT_DRIVE_SYNC.md`](./AGENT_DRIVE_SYNC.md) — upload all manifest docs to Google Drive

---

## Gates

| Gate | Requires | Unblocks |
|------|----------|----------|
| **G0** | CC GO + D-087 + D-088 deploy PASS | Wave 3 SHADOW (P-S0) |
| **G1** | S1-PREV + S1-WIRE pytest + Parent summary | Wave 2 |
| **G2** | P1.5 CLOCK audit/gaps + 5 commits (if needed) | Wave 3 SHADOW |
| **G3** | Soak review + Michael sign-off | Wave 4 + L4/L5 |

---

## Parent (Cursor main chat) duties

- Paste prompt into CC or subagent Task.
- Merge reports; update `P30_PRIORITY_TASK_TABLE.md` status rows.
- **No commit** unless Michael says go.
- Strategic stop: gateway, LIVE, D-086 fix, DLL, bridge, frontend.

---

*Wave pack · MEMS26 pre-LIVE · 2026-05-20*
