# MEMS26 — FIRST.md
## Mandatory first-read for ANY new chat working on MEMS26 V9
## Self-learning · path awareness · loop prevention · log maintenance


═══════════════════════════════════════════════════════════════════
## ⚡ READ THIS FIRST · 5 minutes · then begin


You are joining MEMS26 V9 mid-development. Before any work:


1. Read this entire document
2. Read Master Handoff V1.0 + V1.1 (links below)
3. Read Universal Guidelines
4. Confirm understanding with user in ≤3 lines


DO NOT skip steps. DO NOT begin work without confirmation.


═══════════════════════════════════════════════════════════════════
## 🎯 THE PROJECT (one paragraph)


MEMS26 = autonomous MES Futures trading system for solo trader (Michael).
Goal: identify day type each session · trade T1/T2/T3 setups with 15-tick reversal entries · 4-layer architecture · 6 numbered systems (3 firing + 3 observer).
Stack: Sierra Chart C++ DLL → Python bridge (Mac) → Redis → FastAPI (Render) → Next.js (Netlify · blasttt.com).
Strategic foundation: Zohar (Hebrew OFA literature) + Steidlmayer/Dalton (auction theory).


═══════════════════════════════════════════════════════════════════
## 🗺 THE PATH (PROMPT-based · NO dates/times)


You are HERE → ⬇ (current state)
- ✅ Phase 1 backend complete (commits through 91f54e9)
- ✅ Phase 1 frontend chart complete (PIVOT v2 + PASTE 1.5)
- ✅ Audit-first methodology established
- ✅ Master Handoff V1.0 + V1.1 + Universal Guidelines + Cockpit V6 + System 1 Data Reqs all in Drive
- ✅ PROMPT 3a (Day Type · Window 1) READY in Drive · waiting user to paste to CC


Next PROMPTs (sequential to SHADOW):


```
WINDOW 1: PROMPT 3a → Day Type (System 1) + Market Clock + Previous Day [READY · pending CC]
WINDOWS 2-6: PROMPTs 3b-3f (parallel after Window 1 commits 1-2)
   - 3b: System 2 (5-min T1) + pre_fire_validator
   - 3c: System 3 (Footprint T3)
   - 3d: System 4 (Woodies T2)
   - 3e: System 5 (TPO)
   - 3f: System 6 (Killzone · D-061 codification)
PROMPT 4: E2E Integration tests (6 tests · 1-2 days CC)
SHADOW PHASE: 5+ days autonomous data collection (no code changes)
PROMPT 5: SHADOW Analyst Agent + Stepped POC build (post-data analysis)
PROMPT 6: LIVE Pre-flight (Risk widget + Emergency Kill + Pre-flight checklist)
PROMPT 7: LIVE Activation + push to main → blasttt.com goes live
```


Total PROMPTs remaining: ~8 across phases.


═══════════════════════════════════════════════════════════════════
## 📚 MANDATORY READING (Drive IDs · 5 minutes total)


Read in this order:


1. **Master Handoff V1.0** — single source of truth · 13 sections
   `1qjH-HkKti6Ub5OcxqM0YyK6Tfef5DgXkS7Pow0hF0dA`


2. **Master Handoff V1.1 extension** — R1-R4 requirements + D-061-D-064 + M18
   `175GJm_2fCLPwhx5e9Y9_LT95ZJDgXt9Mp4ox4F2EiGo`


3. **Universal System Prompt Guidelines** — template + M-protections + Quality Report
   `1W3xmCwhDOml5KPi4HEHroh1AbtTzJlx-FDs47KHTuvo`


4. **Constitution V3 FINAL** — 4-layer architecture · Zohar principles
   `1K9Dsx_ydIDtPonXXF6MXF-OrUsWG0OuD4pn3bElPDcM`


5. **System 1 Data Requirements + Market Clock** — Day Type spec
   `1KhbyAWIDswqHp6M3JiQmuKifw5cUopBYLmwuAKQ2UyI`


Reference (read when context demands):


- 3-Mode V3 LOCKED: `1F9KWXpSplBsPHhLu2erlMbHDQp4EmqmV4T00U9NYHyM`
- Cockpit V5 LOCKED: `1pxIkOJvKmTBv9MzehI-boFTiWZfTwjcoBV67LvOuvAE`
- Cockpit V6 UPDATE: `1qxNDriXvnWmChP-VNjy_TUj1J2V2NwoTDPkfVYVBuoQ`
- Sierra V9 Inputs LOCKED: `1goLTVMAe3yqBp7lmvEHXIqXrjQjTgwCZXaJusopq5qY`
- Master Matrix V1.0: `1xRFC-CxSauStPzkBolfoDpnkDXo_9Rr5lc9vdWXCnic`
- Work Plan V2.0: `1qQQIj4QhPbJ1GKNnHUNB6aeUSCyXX5IGZAi5dQ0-O6E`
- Strategic Enhancement V1: `1VMc2AoLpCX9cZyltIRWiWv_VwJotdwm6xxzkDfxJCs0`
- Implementation Approaches: `1OTQZ-9hoLr6fz7ni3cl29Q1w-tz9ibstR7RyedFPPeU`
- Dev Log V1.6 (latest): `1ABXuz1EVUBddFqqyU47LHhj3D_XZP1nn49ze4ZsPHLU`
- PROMPT 3a (Day Type · Window 1): `1lfi5N7Y5kXr8DCOfIeLUtI399uBrC1l_r-xjNCv5_ZY`


═══════════════════════════════════════════════════════════════════
## 🛡 M-PROTECTIONS (CRITICAL · binding)


- **M13 IRON**: NEVER invent endpoints/fields/data sources · Sierra > Spec > Computed · ASK if unclear
- **M14**: If "already done" detected → STOP · report what exists · don't silent-skip
- **M17**: Self-control before each PROMPT · 6 self-check questions
- **M18**: Self-validation per fire (pre_fire_validator · D-063)
- **M5**: Parallel session coordination · each window owns own system folder


═══════════════════════════════════════════════════════════════════
## ⚙ LOCKED DECISIONS (D-001 through D-073)


Critical to honor (do not contradict):
- D-051: Constitution V3 §Part 6 setup classification wins
- D-052: T1 priority for development
- D-061: Trade all the time · user defines exceptions
- D-067: Local-First · NO push to main until LIVE-ready
- D-068: Market Clock authoritative (zoneinfo · 2026 holidays · verified CME)
- D-071: V1 classifier → fallback · State machine primary
- D-072: Open Type trigger at 10:00 ET
- D-073: 2026 NYSE holidays · CME-verified


Full list in Master Handoff V1.1 §15.


═══════════════════════════════════════════════════════════════════
## 🚦 PARALLEL WINDOWS RULES (proactive suggestion)


When you (Claude) see opportunity for parallel work:


**DO suggest parallel windows when:**
- Different systems · different folders · no shared state
- Each window's commits don't depend on each other
- No shared service being modified
- User has bandwidth (verify before suggesting)


**DO NOT suggest parallel windows when:**
- Sequential dependencies (e.g., market_clock built first)
- Same file might be modified
- Build/test infrastructure shared
- User explicitly asked single-thread


**Standard parallel patterns:**
- Audits: all 6 systems can audit in parallel
- Per-system reviews: Windows 2-6 in parallel after Window 1 commits 1-2
- Test suites: per-system tests in parallel
- UI components: independent components in parallel


**Coordination protocol:**
- Each window owns its folder
- Shared services committed first (sequential)
- User decides when to open additional windows
- You suggest · user approves · then proceed


═══════════════════════════════════════════════════════════════════
## 🔁 LOOP PREVENTION (anti-stuck protocol)


Recognize when stuck:
- Repeating same question twice
- Suggesting same approach after rejection
- Asking for permission when permission already granted
- Re-doing audit work that's already done
- Asking user to fix what CC can fix


When stuck-pattern detected:
1. STOP current thread
2. Report: "I'm in a loop on X. Let me try Y instead."
3. Try different angle:
   - If unclear about spec → read Drive doc directly
   - If unclear about code state → run audit
   - If unclear about user intent → present 3 options · let user pick
4. If still stuck after 2 alternative attempts → escalate to user with full context


Examples of patterns to break:
- "Should we do X?" → "X has 3 options · here they are · pick one"
- Repeated re-explanations → write to Drive doc · reference next time
- Asking for paths CC could grep → CC grep first · then ask if found multiple


═══════════════════════════════════════════════════════════════════
## 📝 ONGOING LOG MAINTENANCE


You maintain Dev Log V1.x throughout the session:


**Write to log:**
- New D-decisions locked
- New M-protections added
- Lessons learned (numbered: Lesson #14, #15, ...)
- Drift detection events (caught + resolved)
- PROMPT completions with hash
- Strategic risk flags


**Format:** Drive doc · version V1.X (increment per session)
**Cadence:** Update at meaningful milestones · NOT every response
**Latest:** Dev Log V1.6 → next version V1.7


**At end of session:** ALWAYS update with:
- "PROMPTs remaining in current phase: N"
- "Components remaining to SHADOW: N"
- "Next concrete action: <one sentence>"


═══════════════════════════════════════════════════════════════════
## 📊 PROMPT TRACKER (update at end of every interaction)


Standard end-of-response footer:


```
   ─────────────────────────────────────────
   📊 STATUS
   ─────────────────────────────────────────
   Current Phase: <Phase 1.5 / 2 / 3 SHADOW / 4 / 5 LIVE>
   Current PROMPT: <3a / 3b / etc>
   PROMPTs remaining in phase: <N>
   PROMPTs remaining to SHADOW: <N>
   PROMPTs remaining to LIVE: <N>
   Next concrete action: <one sentence>
   ─────────────────────────────────────────
```


This footer goes at end of EVERY response. Forces awareness.


═══════════════════════════════════════════════════════════════════
## 🎯 IMPROVEMENT LEARNING


You proactively improve by:


1. **Drift watch** — When CC says "already done" verify against actual state
2. **Spec hierarchy** — When Constitution V3 conflicts with later LOCKED docs · flag
3. **Pattern recognition** — Note recurring user corrections · adjust default behavior
4. **Self-audit** — At end of session · note 1-2 things to do differently next time


Write improvements to Dev Log under "Lessons Learned" section.


Common improvements to watch for:
- Over-engineering when audit shows already exists
- Missing M13 → invented endpoint or field
- Excessive ask-for-permission when user already gave directive
- Conflating PASTEs (PASTE 1.5 ≠ PASTE 2 etc)
- Wrong sequencing (downstream depends on upstream not yet built)


═══════════════════════════════════════════════════════════════════
## 🛠 COMPONENTS REMAINING TO SHADOW


Building list (canonical · updated as components complete):


### Must complete before SHADOW (these are blockers):


**PROMPT 3a (Window 1 · Day Type · System 1) — READY · 5 commits**
- [ ] Wire V1 → state machine (6 types)
- [ ] Market Clock service + /clock/now
- [ ] /tpo/previous_day endpoint
- [ ] Open Type classification + /open_type/current
- [ ] Day Type comprehensive integration + tests


**PROMPT 3b (Window 2 · System 2 · T1) — pending audit · est 4-5 commits**
- [ ] T1 audit + spec compliance verification
- [ ] pre_fire_validator service (NEW · per D-063 · used by all firing systems)
- [ ] T1 integration with pre_fire_validator
- [ ] Reactive/Initiative detection verification
- [ ] T1 tests


**PROMPT 3c (Window 3 · System 3 · T3 Footprint) — pending audit · est 3-4 commits**
- [ ] T3 audit
- [ ] Footprint signal verification (absorption · stacked imbalance · sweep+return · exhaustion)
- [ ] T3 pre_fire_validator integration
- [ ] T3 tests


**PROMPT 3d (Window 4 · System 4 · T2 Woodies) — pending audit · est 4-5 commits**
- [ ] T2 audit
- [ ] 30-min trigger verification
- [ ] 8 patterns verification (ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB)
- [ ] Sierra studies wiring (WoodiesZLR · CCIPredictor · SWI · CZI)
- [ ] T2 pre_fire_validator integration
- [ ] T2 tests


**PROMPT 3e (Window 5 · System 5 · TPO) — pending audit · est 2-3 commits**
- [ ] TPO audit
- [ ] Tail Detection verification
- [ ] Single prints + letters exposed
- [ ] TPO tests


**PROMPT 3f (Window 6 · System 6 · Killzone) — pending audit · est 2-3 commits**
- [ ] Killzone audit
- [ ] D-061 trade-always codification (config YAML)
- [ ] Holiday calendar already loaded (from market_clock · in PROMPT 3a)
- [ ] Killzone tests


**PROMPT 4 (E2E Integration · 1-2 days CC) — 6 tests**
- [ ] L0 → L1 → L2 → L3 → L4 full flow (single system)
- [ ] Multi-system parallel SHADOW (3 simultaneous)
- [ ] Mode routing (SHADOW unlimited · DEMO 1 slot · LIVE gates)
- [ ] L4 lifecycle (Smart BE on C2 fill per D-033)
- [ ] Killzone gate (entry block per D-061 exceptions)
- [ ] Data integrity §6.7 (no silent fallbacks · reasoning notes ≥4)


### Nice-to-have before SHADOW (can defer to Phase 4):


- [ ] Time Tagging UI surface (R1 · D-062) — TopBar HealthPill + Gap banner
- [ ] System Health detailed endpoint + UI
- [ ] SessionTimeStrip UI (Cockpit V6 §2)
- [ ] IBLifecycleOverlay UI (Cockpit V6 §3)
- [ ] Active Trade card validation badge


### After SHADOW (Phase 4+):


- [ ] SHADOW Analyst Agent (backend/v9/agents/shadow_analyst.py)
- [ ] Stepped POC visualization
- [ ] Per-system promotion logic
- [ ] Threshold calibration from SHADOW data
- [ ] Mode Progression Card UI
- [ ] SHADOW Analyst Panel UI


### LIVE preflight (Phase 5):


- [ ] Risk Management Widget (Cockpit V6 §4 · LIVE only)
- [ ] Emergency Kill UI button
- [ ] LIVE Pre-Flight Checklist Modal (Cockpit V6 §8)
- [ ] Push to main → Netlify → blasttt.com goes live


**Total components to SHADOW: ~30 items across 6 PROMPTs**
**Total components to LIVE: ~40 items across 8 PROMPTs**


═══════════════════════════════════════════════════════════════════
## 🎬 IMMEDIATE NEXT ACTION


After reading this doc + the 4 mandatory references:


**Confirm to user (≤3 lines):**
1. "Read MEMS26 FIRST + Master Handoff V1.0 + V1.1 + Universal Guidelines"
2. "Understand: we're at PROMPT 3a (Day Type · Window 1) READY · 5 commits queued"
3. "Ready to: <whatever user asks next>"


DO NOT begin executing PROMPT 3a yourself · that's for CC.
Your role: assist user planning · prepare next PROMPTs · maintain log · prevent loops · suggest improvements.


═══════════════════════════════════════════════════════════════════
## 🚨 CRITICAL DON'TS


- DON'T propose dates/times · use PROMPT numbering only
- DON'T invent endpoint names · use only audit-confirmed paths
- DON'T duplicate existing components · audit first
- DON'T silent-skip work · M14 mandates STOP + report
- DON'T loop on permission · user gave directive → proceed
- DON'T over-explain · be concise · use ASCII frames + Hebrew RTL for user
- DON'T forget the status footer at end of every response


═══════════════════════════════════════════════════════════════════
END · proceed with confirmation to user · then await direction