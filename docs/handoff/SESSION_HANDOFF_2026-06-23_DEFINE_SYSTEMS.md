# SESSION HANDOFF — Define S1 / S2 / S4 from first principles · 2026-06-23

**For the next chat.** Michael works in **Hebrew — reply in Hebrew.** Read this + `CLAUDE.md` +
`docs/SOURCE_OF_TRUTH.md` first. This is a **definition** exercise: Michael defines each system in his own
words; the agent captures it, THEN maps to code. Do **not** start from "what the code does" or from the
existing matrix — start from Michael's model.

## Why this handoff (the correction that triggered it)
The prior thread tried to fix the cascade by *enforcing the existing pattern×day-type matrix*
(`config/daytype_playbook.yaml`). Michael clarified: **that matrix is NOT the core of what he defined.**
His model has two axes, and the next chat must be built on them:

1. **DAY-TYPE (S1) defines HOW to trade the day** — the trading *mode/approach* for that day-type
   (fade vs with-trend vs range vs stand-aside; where targets and stops belong). Not just a label.
2. **A "RADAR" tells us WHERE in the process we are — beginning / middle / end of a process (תהליך):**
   - **beginning** → a confirmed turn/break is starting a new move → **enter early**;
   - **middle** → the move is developing → **hold / manage**;
   - **end** → exhaustion at the "new place" (climax / delta-divergence) → **scale out, keep one runner,
     stand aside — do NOT chase.**
   The radar relates to the existing `direction_context` / ARM-DISARM and the auction-stage idea, **but
   Michael wants it defined fresh** (operationally: what marks beginning vs middle vs end, via price
   structure + volume + CVD). It is the missing piece, not the matrix.

**Patterns (S2/S4) are triggers that must fire in accordance with BOTH axes** — the day-type mode AND the
radar stage. They are secondary to the two axes above.

## Next-chat agenda — define each system, in order
Go **system by system** and define **what each does** from Michael's model (job · inputs · outputs · how it
uses the day-type mode + the radar stage). After each is defined, reconcile with code (KEEP / ADAPT /
REPLACE) — but definition first.

1. **System 1 — day-type.** Output = the day-type **and** the "how-to-trade" mode for the day. Decide
   whether the **radar (beginning/middle/end)** lives inside S1 or is its own layer.
2. **System 2 — 5-min (Reactive / Initiative).** Define when/what it should fire, per day-type mode +
   radar stage.
3. **System 4 — Woodies (ZLR / HFE / TLB / …).** Define when/what it should fire, per day-type mode +
   radar stage.

Start with **System 1**: ask Michael to define, in his words, what S1 must output and where the radar lives.
Capture it, then map to code.

## Current state — context only, NOT the target
- **Cascade is wired but broken at the joint** — `docs/reports/CASCADE_AUDIT_S1_S2_S4_2026-06-23.md` (R1–R6):
  S1 classifies fine; S2/S4 fire on pure geometry (don't consult day-type); the gate meant to translate
  day-type→allowed-patterns is a **dead no-op** (R1, `daytype_playbook.py:104`); the gate that runs is
  **pattern-blind** (R2); targets lack the **opportunity** dimension (R6). The "radar / process-stage" is
  **not implemented as Michael means it**.
- **A pattern×day-type matrix already EXISTS but is NOT the core of his model:**
  `config/daytype_playbook.yaml` `patterns:` block (13 patterns × 7 day-types, FULL/REDUCED/SKIP +
  `require_with_trend`) + spec authority `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv`
  (63 cells with entry-hints + targets). Treat it as **one input**, not the goal.
- **`daytype_style`** (same yaml) already sketches per-day-type management (bias, ref_points, c1/c2/c3,
  contracts, runner) — this is the closest existing thing to "how to trade the day-type"; good raw material
  for the S1-mode definition.
- **Replay / brain-view tool** is built (`tools/replay_brain_view.py`); CC exported real data for
  2026-06-09 / 06-16 / 06-19 / 06-22 — **use it to ground each definition in real days** (e.g. show where
  the radar should have said "end of process" yesterday).
- **The unified-brain prototype is NOT a proven edge** (clean-days flat −$11; barely fires). The radar /
  stage detection is exactly what must be defined + calibrated before any build.
- **Plan from the prior thread:** `docs/plans/CASCADE_WORK_PLAN_2026-06-23.md` — keep as reference; it may
  be revised once the systems are defined Michael's way.

## Yesterday (06-22) as the worked example
Day-type Variation/`with_extension`, opening OPEN_DRIVE, 19 fires ALL SHORT, every one `blocked_by=None`.
Out-of-accordance fires: counter-drive TLB (188/190), HFE reversals (191/193/194), and the REACTIVE
fade-wall (197–212). In Michael's terms: the **radar** should have flagged the morning as *beginning/middle*
of a down-process (enter early, hold) and the afternoon lows as *end of process* (stand aside, don't fade) —
but there is no radar, so patterns fired at every stage. Use this day to test each definition.

## Discipline / working style
Hebrew. **Define-first** (Michael's model) before touching code. Honesty over flattering numbers.
Diagnose-first. Pre-LIVE: paste raw output (**Rule 5**); smallest correct change; no service starts;
**honest failure > synthetic value**. Don't `present_files` for tracking-file edits (roadmap/status/CLAUDE.md).
Trading-surface changes → Michael sign-off, flag-OFF default, SHADOW-validate. After any task: update
`ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md`.
