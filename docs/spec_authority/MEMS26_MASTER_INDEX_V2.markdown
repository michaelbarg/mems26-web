# MEMS26 — MASTER INDEX V2

## Single source of truth · per-system specs · authoritative

**Version:** V2.0 (supersedes V1.0)
**Updated:** 16 May 2026
**Status:** 🟢 LOCKED · authoritative
**Replaces:** V1.0 (1CUhjvwvlGz5umpH_wRxH4Jz8txzX2xig — kept in Drive history)

---

## 📌 Quick Stats

```
═══════════════════════════════════════════════════════════════════
   Project:    MEMS26 V9 · autonomous MES Futures trading
   Stack:      Sierra DLL → Python bridge → Redis → FastAPI → Next.js
   Repo:       /Users/michael/Downloads/mems26_web_git
   Branch:     feature/v9_architecture_rebuild (86 commits ahead)
   
   Architecture: V9 (LOCKED 10/5) — 4 Layers · 6 Independent Systems
   Decision Trees: Each system has dedicated Drive spec
   Status:       Per-system audits + Day Type V9 architecture exists
═══════════════════════════════════════════════════════════════════
```

---

## 📚 SPEC AUTHORITY · TOP-LEVEL

| Doc | Drive ID | Role |
|-----|----------|------|
| **Spec Registry** | `1_gQCaMTq-3D3Fe34_ddV54-9eQvOAW9Mfx4zAyPMSwk` | 🆕 Master index of all per-system specs |
| **Constitution V3 FINAL** | `1K9Dsx_ydIDtPonXXF6MXF-OrUsWG0OuD4pn3bElPDcM` | Strategic foundation · 4 Layers · Zohar |
| **3-Mode V3 LOCKED** | `1F9KWXpSplBsPHhLu2erlMbHDQp4EmqmV4T00U9NYHyM` | SHADOW/DEMO/LIVE behavior |
| **Cockpit V5 LOCKED** | `1pxIkOJvKmTBv9MzehI-boFTiWZfTwjcoBV67LvOuvAE` | UI/UX active mode |
| **Cockpit V6 UPDATE** | `1qxNDriXvnWmChP-VNjy_TUj1J2V2NwoTDPkfVYVBuoQ` | Extension |
| **Sierra V9 Inputs LOCKED** | `1goLTVMAe3yqBp7lmvEHXIqXrjQjTgwCZXaJusopq5qY` | Sierra Chart Inputs |
| **Master Visual Reference V5** | `1q0gvhPwdn-PXhxX3qXypadYidpng5SNt` | 🆕 Visual reference |

---

## 📚 PER-SYSTEM DECISION TREES + SPECS

### 🟢 S1 — Day Type (Observer · Context Filter)

| Doc | Drive ID |
|-----|----------|
| **Day Type Tree V2** | `1Tx1sfVdebnTNS2Cv8MQpnBOXwCbVutmFyIZ-tJtYGuU` |
| **System 1 Data Reqs V1.0** | `1KhbyAWIDswqHp6M3JiQmuKifw5cUopBYLmwuAKQ2UyI` |
| Constitution V3 §Layer 2 | (see top) |

Audit: 15 files · 2152 LOC · 9 V9 endpoints · 58 tests · 🟢 V9 architecture
Critical gaps: Previous Day Loader · Dead wiring fix · V1 fallback removal

---

### 🟡 S2 — 5-min Patterns T1 (Firing)

| Doc | Drive ID |
|-----|----------|
| **5-min Tree V3.3** | `1dP8x4vaat49BAw0L1DgOBTBqQ4Ci1YllUoWTwoy1DSQ` |
| Constitution V3 §Layer 1 §T1 | (see top) |
| Cockpit V5 §3.4 | (see top) |

Audit: 2 files · 416 LOC · 4 endpoints · 0 tests · 🟡 PARTIAL
Critical gaps: pre_fire_validator · tests · V9 enhancement layer

---

### 🟡 S3 — Footprint T3 (Firing · Observer)

| Doc | Drive ID |
|-----|----------|
| **Footprint Spec V3** | `1iPndwDKwYn70pXCwkHNJVyAwLeU8WislDGAQX3HXvT4` |
| Constitution V3 §Layer 1 §T3 | (see top) |

Architecture per Spec V3: STANDALONE observer · 7-stage processing per bar (A-G) · 5 patterns + 10 signals + 3 classifications (NO_SETUP / TACTICAL / STRATEGIC)

Audit: 8 files · 823 LOC · 3 endpoints · 1 test · 🟡 PARTIAL

---

### 🟡 S4 — Woodies CCI T2 (Firing)

| Doc | Drive ID |
|-----|----------|
| **Woodies CCI Spec V1** | `1NtKDNZNVwWi8Dio_C-42Yj0c6DPFGEfnFSo3Vx4rp0k` |
| **Woodies Decision Tree V1** | repo: `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` |
| Constitution V3 §Layer 1 §T2 | (see top) |

Architecture per Decision Tree V1: STANDALONE · 21 stages (A1-A7 entry + B1-B14 active) · 9 patterns (8 built + HFE missing) · 6 advisory touch-points (NO veto) · 18 terminal states · YAML config-driven modular

Audit: 18 files · 1737 LOC · 3 endpoints · 3 tests · 🔴 39 FAILS
Spec components: 82 total · 25 built · 57 missing
Critical gaps: HFE pattern · B1-B14 14 stages · Priority Dispatcher · 17 terminal states · 6 touch-points · YAML loader · 39 ZLR test failures

---

### 🟡 S5 — TPO (Observer · Macro Context)

| Doc | Drive ID |
|-----|----------|
| **TPO Tree V2** | `1DrjQOphmG3Edn0QaniSRf7Ijr50i-7TWrNqRWK2xn_0` |
| Constitution V3 §Layer 2 §Location | (see top) |
| Cockpit V5 §4.5 | (see top) |

Audit: 8 files · 1154 LOC · 4 endpoints · 2 tests · 🟡 PARTIAL

---

### 🟡 S6 — Killzone (Observer + Gate)

| Doc | Drive ID |
|-----|----------|
| **Killzone Spec V1** | `1s6GpXv2zXy8KzQASkzIgdxRYDDG8KYWkyokdq-3iSzY` |
| Constitution V3 §Layer 0 | (see top) |
| Cockpit V5 §3.3 (OVERRIDDEN by D-061) | (see top) |

Audit: 9 files · 586 LOC · 1 endpoint · 2 tests · 🟡 PARTIAL
Active Conflict: Cockpit V5 §3.3 (BLOCK in IB Building) vs D-061 (TRADE ALL THE TIME) → D-061 wins

---

## 🏛️ V9 ARCHITECTURE (LOCKED 10/5)

```
L0 — Market State Gate · chop_score 0-100 + 4 states
                ↓
L1 — Setup Identification · Firing systems detect (T1/T2/T3)
                ↓
L2 — Quality · per-system internal sizing · Day Type · Location
                ↓
L3 — Entry Execution · 15-tick reversal bar + cluster + empty zone
                ↓
L4 — Trade Management · 10 don't-give-back rules · Smart BE on C2 fill
```

---

## 🛡️ M-PROTECTIONS (M1 — M18 · all binding)

M1-M16 per Master Handoff V1.0 §8
M13 🔒 IRON: NEVER INVENT · Sierra > Spec > Computed · ASK if unclear
M17 Self-control before each PROMPT (6 questions)
M18 Self-validation per fire (pre_fire_validator · D-063)

---

## ⚙️ ACTIVE D-DECISIONS (Drive numbering · D-001 → D-073)

Critical to honor:
- D-051: Constitution V3 §Part 6 setup classification wins
- D-052: T1 tactical priority
- D-061: Trade all the time · user defines exceptions
- D-062: Time Tagging Enforcement
- D-063: Self-Validation Mandate (pre_fire_validator)
- D-064: Bar Accumulation Defaults (200 init · 2000 cap)
- D-067: Local-First · NO push to main until LIVE-ready
- D-068: Market Clock authoritative
- D-069: IB Class thresholds (33/67 percentiles · 10-day rolling)
- D-070: Previous Day source (α-first → β fallback)
- D-071: V1 classifier → fallback only · State machine primary
- D-072: Open Type trigger at 10:00 ET
- D-073: 2026 NYSE holidays · CME-verified

Decision Reset (LOCKED 15/5): All pre-10/5 D-XXX ARCHIVED.
See `MEMS26_DECISIONS_ARCHIVE_V1` (1Q4OyNT3cRlzW-A5lj3I76vxP5jXs5H4v).

---

## 🛠️ PROMPT SEQUENCE TO LIVE

```
NOW → PROMPT 3a (Day Type · Window 1) READY in Drive
      ID: 1lfi5N7Y5kXr8DCOfIeLUtI399uBrC1l_r-xjNCv5_ZY
      (May need update to FIX MODE based on audit findings)

Then → PROMPTs 3b-3f (Systems 2-6 audits + builds · parallel after 3a c1-c2)

Then → PROMPT 4 — E2E Integration tests (6 tests)
Then → SHADOW PHASE (5-30 days · autonomous · per D-067 promotion gates)
Then → PROMPT 5 — SHADOW Analyst Agent + Stepped POC
Then → PROMPT 6 — LIVE Pre-flight (Risk widget + Emergency Kill + checklist)
Then → PROMPT 7 — LIVE Activation · push to main → blasttt.com
```

---

## 📦 Quality Tools

| Doc | Drive ID | Purpose |
|-----|----------|---------|
| **Guardian Agent v2** | `1_Aaqa-0crpkgmR6EHWpYW24Sv7WPN6y-` | 🆕 QA agent |
| **PROMPT Template V2** | `1XObzjr_q-WIGFilcqYxUUbX1xMjh3DmI` | 🆕 Embedded Self-QA template |
| **V9 Ops Quick Reference** | `1syRXsK_-OfCtzUAw0OYG9LY6JeUmcuCv` | 🆕 Quick ref |

---

## 📎 Related Documents

- **MEMS26_DECISIONS_ARCHIVE_V1** (`1Q4OyNT3cRlzW-A5lj3I76vxP5jXs5H4v`) — pre-10/5 D-XXX (ARCHIVED)
- **MEMS26 FIRST.md** (`1QJZF0gKYlnjJgjACShe9dZX44GA2Crup0KX9k049Yec`) — start here for new chat
- **Master Handoff V1.0/V1.1** — see top
- **Universal Guidelines** — see top

---

## 🚨 Critical Don'ts

- DON'T propose dates/times · use PROMPT numbering
- DON'T invent endpoint names · use only audit-confirmed paths (M13)
- DON'T duplicate existing components · audit first
- DON'T silent-skip work · M14 mandates STOP + report
- DON'T over-explain · be concise · ASCII frames + Hebrew RTL
- DON'T forget the status footer at end of every response

---

**End of MEMS26_MASTER_INDEX_V2**

🟢 ACTIVE · authoritative
📅 Last updated: 16 May 2026
🔗 Replaces V1.0 (kept in Drive history)
