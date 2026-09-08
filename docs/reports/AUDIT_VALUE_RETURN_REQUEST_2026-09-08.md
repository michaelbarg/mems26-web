# AUDIT — "the first move toward the belly" (A) and "price is searching for a new place" (B)

**Written:** 2026-09-08 · cowork · **READ-ONLY.** No code, service, `.env`, flag or position touched.
**Question (Michael, 08.09):** *"I have raised this subject many times — why was it not built? Or maybe it
exists and you don't know it? It cannot be that I write this so many times and discover on the day of
trading that it was not done."*

**Definitions used throughout, exactly as Michael frames them:**
- **A — first move toward the belly.** On a one-sided / Variation day, entering on the **first rotation back
  toward the developing POC**, with POC as the destination. **Not** a rejection at the value-area edge —
  the rotation itself, caught as it starts.
- **B — price is searching for a new place.** On a balance/bracket day, when price **leaves the balance
  area** in search of new value, being there to take **that departure** as an entry.

---

## 0. The short answer

Neither answer is "you never asked" and neither is "it lost money". The true answers are different for A and B:

| | What actually happened | Where it stopped |
|---|---|---|
| **A** | Raised **7 times** since 07-15. Two *adjacent* things were built and measured; **the producer Michael actually describes was never built.** The one closest measurement (08.09) came back **−$1,488.75 / 15 sessions** — but the report itself says the *read* is right and the *trade geometry* is wrong. | Tracked as **T-271, open**. Not a paperwork failure — a measurement that has not yet been re-run with the right target. |
| **B** | Raised **6 times** since 07-02. It **was** built as a replay, **measured POSITIVE — `+$5,973 / 34 sessions` (OOS `+$2,235`)** — entered in TASK_LOG as **T-105 `CONTEXT_ENTRY_V1`**, and then **frozen.** Verified today: **zero lines of code.** | **T-105, status 🟡, next-step reads literally `אל תתחיל` (do not start)** — blocked behind T-103 → T-100/T-104 since **2026-08-25, 14 days.** |

**The single most damning line in the repo** is our own, written 2026-08-22 and never actioned —
`docs/plans/SYSTEM_BRAIN.html:54`:

> `איזון מול גילוי-מחיר` · *"האם השוק מסתובב בערך או מחפש מקום חדש"* · **`✗ לא קיים בכלל — וזה המצב הבסיסי ביותר בדלתון`**

We diagnosed B as missing, called it the most basic state in Dalton, measured a positive fix, and then
parked it for 17 days.

---

## 1. Timeline — concept A ("first move toward the belly", POC as destination)

| # | Date | Source (file:line) | What Michael said | What happened next in the record |
|---|---|---|---|---|
| A1 | **2026-07-15** | `docs/handoff/EXECUTION_REPORT_2026-07-15.md:9` | On #372: *"בנקודה כזו הפעולה הנכונה היא שורט (רוטציה סביב VAH/VAL/POC)"* | Fed into `DAYTYPE_LOCATION_GATE` — a **gate**, not a producer |
| A2 | **2026-07-15** | `docs/handoff/GROUND_TRUTH_TRADES_2026-07-15.md:47` | Trade **D** = *"היפוך-שפל→POC ~33 נק'"*; *"**ניהול:** יעד-מבני = POC ואז VAH … זו עסקת-ה-POC שמייקל תיאר"* | Recorded as a **missed** trade (`MISSED_TRADES_2026-07-15.md:11` — 1 of 5 key trades executed, 4 missed). No producer opened |
| A3 | **2026-07-16 22:20** | `docs/handoff/CC_NIGHT_PROMPT_2026-07-16.md:14` | **פסיקת-מייקל:** *"זה יום נורמל-וריאציה, והמסחר היה יכול להיות מצוין **מכיוון-לכיוון ואז POC**"* | Converted into a **playbook permission** (allow fades at the edges with a POC target) — again a gate/table change, not an entry that triggers on the rotation |
| A4 | **2026-07-19** | `docs/handoff/DIRECTION_AUTHORITY_MAP_2026-07-19.md:36,57` | POC rule approved, **rotation days only**; *"✅ אושר 07-19"* | Became the POC-side **filter** in `reactive_location_gate.py` — a **gate** |
| A5 | **2026-07-21 22:18** | `docs/handoff/CC_T1_STRUCTURE_END_2026-07-21.md:71` | *"הייתי מעדיף שכניסה בסוג יום כזה תהיה כמו ההגדרה שנתנו — זה כניסה ב-VAH שורט לאחר בדיקה."* | Built as `DAYTYPE_LOCATION_GATE` v2 (RULED_FLAGS:183). **Gate.** |
| A6 | **2026-08-26 09:08:11Z** | `docs/handoff/PHONE_THREAD.jsonl` (line 7, his only message in the thread on this subject) | *"כניסה לאחר בדיקה **לא בקיצון** אלא כאשר מתגבשת לנו תבנית תקרה כפולה או רצפה כפולה מכיוון לכיוון … **אם יהיה יעד רווח של POC ולאו דווקא המשך לצד השני כי זה צריך להיות זיגזאג**"* | **This one WAS built.** `failed_break.py` with T1=POC (`9a4c47d6` — *"T2=2R (not opposite edge per Michael 'זיגזאג→POC'"*), measured `+$118 / 33 sessions / 56%` (`ddaa9479`), then found ≈ **zero after commissions**; live-wired to shadow 27.08 (`285b0a41`). **`FAILED_BREAK_VA_V1=shadow` today** (`.env:617`, RULED_FLAGS:334) |
| A7 | **2026-09-06 17:49** | `docs/handoff/CC_DAYTYPE_MGMT_2026-09-06.md:4` | **פסיקת-מייקל:** *"בשני הימים השוק עלה או ירד לכיוון מסוים **כדי לבנות את הבטן**, והמערכת לא ניצלה הזדמנות … אני לא מוכן להמשיך להפסיד סתם מדברים שהמערכת צריכה לדעת לבצע."* | 5 fixes specified. Fix #1 = `DAYTYPE_DIR_DISCIPLINE_V1`. **Verified today: `grep DAYTYPE_DIR_DISCIPLINE backend/ config/ ⇒ 0`** — not built |
| A8 | **2026-09-08** | `docs/reports/TERMINATION_REVERSAL_2026-09-08.md:4-6` | *"recognising that price has FINISHED extending in one direction, so that termination itself becomes the trigger for the other side"* | **Measured today.** See §3 |

**Count: 7 distinct occasions (A1/A2 are the same day) over 55 days.**

---

## 2. Timeline — concept B ("searching for a new place" / balance → discovery)

| # | Date | Source (file:line) | What Michael said | What happened next |
|---|---|---|---|---|
| B1 | **2026-07-02** | `docs/plans/MICHAEL_ISSUES_LEDGER.md` item **24** | *"יום טרנדי **שמחפש מקום** — עסקאות רק עם הכיוון עד עצירה מוכחת"* | Status `🌙 נפסק (פריט-18)` → `DAY_DIRECTION_DOCTRINE_V1`. **Built as a GATE** ("only with-expansion entries allowed"), and it is **OFF**: `docs/FLAG_INDEX.md:146` — `🔴 OFF · unset → "0" · code default "0"` |
| B2 | **2026-07-02** | `docs/handoff/CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md:206` | *"יום טרנדי שמחפש מקום חדש — העסקאות היו צריכות להיות עם כיוון המגמה, עד שיש עצירה"* | Same item-18 thread. Gate only |
| B3 | **2026-08-22/23** | `docs/handoff/CC_TASK_DALTON_SIM_FIRST.md:12` (+ ruling 23.08 at `:5`) | *"**דלתון בקצרה:** השוק תמיד באחד משניים — **איזון** … או **גילוי-מחיר** (**מחפש מקום חדש**)"* · and the architectural charge: *"המערכת היום **כולה חיסורית**: כל מנגנון הוא שער שחוסם. **אין היגיון חיובי**"* | Simulation ordered and run — see §4 |
| B4 | **2026-08-22** | `docs/plans/SYSTEM_BRAIN.html:54` | (our own record of it) | Marked **`✗ לא קיים בכלל — וזה המצב הבסיסי ביותר בדלתון`** |
| B5 | **2026-08-24** | `docs/handoff/CC_BUILD_2026-08-24.md:23-31` | **פסיקת-מייקל** on rotation policy: *"ב-BALANCE אין תקרת-כניסות — שורט בקצה-עליון, לונג בקצה-תחתון, חוזר כל עוד המבנה מחזיק"*; target = *"הקצה הנגדי של אזור-הערך ב-BALANCE · טרייל-מבני ב-DISCOVERY"* | Spec for `CONTEXT_ENTRY_V1`. **Never coded** |
| B6 | **2026-09-01** | `docs/handoff/CC_WORKORDER_2026-09-01_NO_CHASE.md:16-17` and **`:138`** | *"…**אלא אם כן** אנחנו רואים שהוא **מחפש מקום חדש**, או שנוצרות **מדרגות מעל VAH** או מדרגות מתחת ל-VAL"* | **Implemented as `תנאי 3 · הפטור` — the exemption.** The same file, §"מה שאסור לבנות", says explicitly: **`לא לייצר כניסות חדשות. זה שער-חסימה בלבד`** |

**Count: 6 distinct occasions over 68 days.**

**B6 is the sharpest single illustration of the failure mode.** The one time "מחפש מקום חדש" was turned
into code-adjacent spec, it became **the exemption clause of a blocking gate** — the thing that stops
`NO_CHASE` from over-blocking — and the work order forbids it from producing an entry. Michael's
positive signal was implemented as a negative one's escape hatch. (And `NO_CHASE_V1` itself: `grep
NO_CHASE backend/ config/ scripts/ .env ⇒ 0` — the gate was never built either.)

---

## 3. Concept A — code verdict

### Does a PRODUCER exist that triggers on the first rotation back toward the developing POC? **NO.**

Exhaustive grep across `backend/v9`, exact strings searched: **`poc_target`, `toward_poc`,
`revert_to_poc`, `mean_revert` ⇒ 0 files, all of `backend/v9`.**
`\brotation\b` ⇒ 16 files, all of them (a) day-type vocabulary, (b) stop-floor sizing
(`stop_anchors/stop_resolver.py:69-84`), (c) `release_gate.py`'s internal exit model, (d) docstring
narrative. **None is an entry trigger.**

**What exists instead** — every POC-touching producer is an *edge-rejection* pattern, which is the exact
family A's definition excludes:

| File | Class | Trigger | POC role | Flag / state |
|---|---|---|---|---|
| `va_fade.py:100-104` | PRODUCER | `lh >= vah - _ez and close_pos <= _cp and lc < vah` — probe the edge and close back **inside** | POC = target only | `VA_FADE_V1=shadow`; code default `"0"` (`five_min_system.py:2345`) |
| `edge_fade.py:124-127` | PRODUCER | session-hi/lo probe + reject | **no POC at all**; target = day mid | `EDGE_FADE_V1` code default `"0"` |
| `failed_break.py:82-86` | PRODUCER | `ph > edge_high and ch <= ph and cc < edge_high` — a **failed** breakout, then return | **T1 = POC**, per A6 ruling quoted in code at `:134` | `FAILED_BREAK_VA_V1=shadow` |
| `ceiling_flip.py:46-48,67` | PRODUCER | double-top/bottom **failure**, entry on neckline break | T1 = POC when supplied | `CEILING_FLIP_SHORT_V1=shadow`, code default `"0"` |
| `dalton_edge.py:119-121` | PRODUCER | N-bar extreme + rejection close + volume ≥ 2×SMA20 | **no POC**; T1/T2 = pure R-multiples | `DALTON_EDGE_V1=live` — **but n=1 in all history** |
| `reactive_location_gate.py:43-51` | **GATE** | `if entry > poc_f: return False` | POC = **boundary**, never destination | `REACTIVE_LOCATION_GATE` default `"0"` |
| `_detect_reactive` (`five_min_system.py:1012-1014`) | PRODUCER | 4-bar climax absorption | `poc_rising` is a **per-bar footprint** POC used only as a confidence bump (`0.80 if poc_rising else 0.75`, `:1039`) | core S2 |

**The one rule in the codebase that actually models "rotation to a value target" is dead code.**
`backend/v9/systems/day_type/day_context_extras.py:92-101` — `va_rule_read()`, Dalton's 80% rule:
*"opened ABOVE value and accepted back in → rotation target = prior VAL"*. Its consumer,
`classifier_core.py:227-230`, says in a comment: **`VA-rule read (emitted for briefing/UI; no gate yet)`.**
Computed on every bar since 07-13, consumed by nothing.

### The one measurement that bears on A — and it is negative on money, positive on the read

`docs/reports/TERMINATION_REVERSAL_2026-09-08.md` (today), 36 candidates / 15 sessions / 3 fixed rules,
targets = nearest of POC / opposite value edge / IB-mid, stop = session extreme + 6 ticks:

```
T1 (extension failed 2 periods)  n=15  47%  −$1,473.75
T2 (excess / tail)               n=11  27%    −$165.00
T3 (return through IB edge)      n=10  60%    +$150.00
                                        Σ    −$1,488.75  @2 contracts
```

Its own §6 finding 1: **"Termination is a real read. The trade specified on top of it is not."** R:R as
specified is **0.43 : 1** ⇒ needs 70 % to break even against 44 % actual. Five T1 candidates carrying
> 20 pt of risk account for **−$1,160 of the −$1,473.75**. And: *"MFE after end-of-extension 4.5-7.1 pts,
and T3 got ≥ 4 pts of room in 7/10 ⇒ **the market DOES rotate; we are risking to the extreme and aiming
at the nearest level.**"*

**So the honest sentence to Michael on A is:** *the reading you describe is measurably correct; the one
trade structure we wrapped around it loses money, and the report says the loss is geometry, not the
read.* That is **not** the same as "your idea was tested and failed."

**Tracked as:** `docs/plans/TASK_LOG.md:628` **T-271, 🟠 open.** Next step, verbatim: *"(3) **המדידה
היחידה שראויה להמשך: אותו טריגר T3 עם היעד לצד הרחוק של הערך** כדי שה-R:R יעבור 1:1 — פרמטר אחד
על כלל קיים, בצל, ≥40 סשנים לפני שמוצע דגל."*

---

## 4. Concept B — code verdict, and the drop point

### Does a PRODUCER exist that triggers on price leaving the balance area? **NO — but it was measured, and it was positive.**

Exact strings searched across `backend/v9`: **`balance_exit`, `va_exit`, `leaves_value`, `outside_va`,
`break_of_balance`, `range_expansion` ⇒ 1 hit, and it is a false positive** (the substring `outside_va`
inside the test name `test_low_outside_value` in `systems/five_min/tests/test_quality_tier.py`).
**No production trigger uses any of these terms.**

Three partial mechanisms exist, each scoped so narrowly it cannot be what Michael asked for:

| File | Class | Why it is not B |
|---|---|---|
| `opening_entry.py:166-172` (DRIVE) | PRODUCER | The "balance" is only the **first opening-range bar**, not the day's established balance; narrow-OR case only. `OPENING_ENTRY_V1=1` |
| `re_acceptance.py:126-133` | PRODUCER | Closes beyond IB/VA with delta+volume conviction — genuinely close — but **no balance-day gate**; `OPEN` crossings also qualify. `RE_ACCEPTANCE_V1=shadow` (default `"0"` at `re_acceptance.py:30`) |
| `five_min/patterns/pullback_retest.py:117-137` | PRODUCER | Requires the IB break, but the entry fires on the **retest**, not on the departure. `RE_PULLBACK_ENTRY_V1` default `"0"` |

And `balance_imbalance_toggle.py` — which computes `BALANCE`/`IMBALANCE`/`TRANSITIONAL` and whose
docstring claims it is *"consumable by S2 and S4 fire paths"* — **is dead relative to trading.**
`grep BALANCE_IMBALANCE_TOGGLE_V1` ⇒ the only hit is its own docstring; **no `os.getenv` for it exists
anywhere in the repo.** Its only production caller is `api/v9/context_radar.py`, a read-only dashboard route.

### The measurement — POSITIVE

`docs/plans/TASK_LOG.md:84` (dated 2026-08-24, from `CC_NEXT_2026-08-23C`):

> ✅ **דלתון V2 מעל גלאים:** `replay_dalton_over_detectors.py` — **L2 חיובי: +$5,973/34 סשנים** (OOS
> **+$2,235**). 18/34 ימים חיוביים, 1.6 עסקאות/יום. **INITIATIVE_LONG: −$2,310 → +$2,253 (+$4,563)**.
> דוח: `SIM_DALTON_OVER_DETECTORS.md`.

(The earlier, weaker run is honestly recorded next to it — `TASK_LOG.md:82`, Dalton V2 on swings:
convergence 30%→90%, L2 **−$478.50**; and `SIM_DALTON_CONTEXT_WEEK.md` totals `L2 −$868.50 / 10
sessions` with **convergence 30%** and the explicit self-criticism *"IB break ≠ DISCOVERY … the
definition IS wrong."* The definition was then fixed to require acceptance + value migration +
non-return, and the fixed version is the `+$5,973` run.)

### 🔴 THE DROP POINT

It **was** entered in the task log. `docs/plans/TASK_LOG.md:310`:

```
| T-105 | 🟡 CONTEXT_ENTRY_V1 pure function אחת ל-replay+shadow+live.
         BALANCE=B+REACTIVE confirmation; DISCOVERY=D+with-direction; stop_anchors authority.
       | 🟡 חסום עד T-103 GO ואז T-100/T-104
       | cc-macbook → cursor/cowork
       | אל תתחיל. אחרי התלויות: build default-OFF; … shadow 10 sessions.
         live enable = פסיקת מייקל |
```

**The next-step field literally reads `אל תתחיל` — "do not start".** The dependency chain:

- **T-103** (Candidate Ledger) — `TASK_LOG.md:312`, `🟠 IN-PROGRESS` since **2026-08-25** (`TASK_LOG.md:74`). Still in progress.
- **T-104** (`S1_STRUCTURAL_BINARY_V1` completion) — `:311`, `🟡 חסום עד T-103 GO`, next-step `אל תתחיל לפני T-103`.
- **T-100** (TPO lookahead 92.3 % + CVD conflict) — `:315`, `🔴 חסום עד T-103 GO`, next-step `אל תתחיל`.

**Confirmed zero code, twice, 15 days apart:**
- `docs/handoff/GAP_REGISTER.md:42` (**G-22**, 2026-08-24, `🟢 CONFIRMED`): *"`CONTEXT_ENTRY_V1` קיים
  **כמפרט בלבד** — אין דגל/מודול/חיווט בקוד … אפס backend/config."*
- **Verified today, 2026-09-08:** `grep -rn CONTEXT_ENTRY --include=*.py --include=*.yaml backend/ config/
  scripts/ frontend/` ⇒ **0**. `grep CONTEXT_ENTRY .env` ⇒ **0**.
  The only 30-odd occurrences in the repo are in `docs/` plus the two generated readiness HTML pages.

Commit `997f625d` (2026-08-23) is titled *"בנייה: שלב1 … שלב2 **CONTEXT_ENTRY_V1** — מיקום בוחר/REACTIVE
נכנס/מבנה יוצא · שלב3 אימות"*. Its `--stat`: 5 files — `news_calendar.yaml`, `CC_BUILD_2026-08-24.md`,
`TASK_LOG.md`, `EXTREME_DETECTION_AND_BIAS_AUDIT.md`, `extreme_detection_audit.py`. **A commit whose
subject says "build … CONTEXT_ENTRY_V1" contains no `CONTEXT_ENTRY_V1` code.**

### Nothing was built and reverted, and nothing is waiting on a branch

`git log --oneline --all | grep -iE "poc|belly|balance|rotation|discovery|context_entry|va_fade|failed_break"`
⇒ 22 commits, all on the current branch, all accounted for above (`VA_FADE` calibration, `FAILED_BREAK`
wiring, `T-242`, `T-161`, the 06.09 belly work order). `git log --all | grep -i revert` ⇒ the reverts are
`location_gate`, `G2/G3`, `G6`, the 8pt stop band-aid, chase-tip revocation — **none of them A or B.**
No branch holds an unmerged implementation.

---

## 5. Classification of the failure, stated precisely

The parent question offered three shapes of failure. The record shows **two different ones**, and neither
is the one that would be easiest to say:

**For B — "measured positive, entered as a task, then frozen behind a dependency chain."**
This is not "raised in chat, never entered in TASK_LOG" (it *was* entered, as T-105), and it is not
"built, measured, and shelved after a negative replay" (the replay was **+$5,973**). It is: a positive
measurement whose follow-through was made conditional on three other items — T-103, then T-100 and
T-104 — one of which has been in progress for 14 days and two of which are themselves blocked on it. The
instruction attached to the item is `אל תתחיל`. Nobody violated a rule; the rule was the problem. And
`SYSTEM_BRAIN.html:54` had already flagged this as the most basic missing state in Dalton, on 08-22,
before the freeze.

**For A — "repeatedly translated into a gate instead of a producer, then measured once with the wrong geometry."**
Across A1-A5 (07-15 → 07-21), every single time Michael described a POC-destination rotation entry, what
got built was a **permission** — `DAYTYPE_LOCATION_GATE`, `reactive_location_gate`, a playbook cell. At
A6 (08-26) a genuine producer with a POC target was finally built (`failed_break.py`), but it is an
edge-rejection pattern, it measured ≈ zero after commissions, and it sits at `shadow`. At A7 (09-06) the
fix specified for the belly, `DAYTYPE_DIR_DISCIPLINE_V1`, **⇒ grep 0, not built.** At A8 (today) the
closest measurement returned −$1,488.75 while its own text says the read is correct and the geometry is
wrong.

**The structural diagnosis is Michael's own, written 17 days ago and still true**
(`CC_TASK_DALTON_SIM_FIRST.md:9-11`):

> *"המערכת היום **כולה חיסורית**: כל מנגנון הוא שער שחוסם. **אין היגיון חיובי** שאומר 'המחיר ב-VAL,
> היום מתגבש כמאוזן ⇒ **זו** עסקת-הלונג של היום'. התבניות יורות איפה שנופל ואז מסננים."*

Every one of the 13 raisings above was absorbed by the subtractive half of the system. That is why he can
write it many times and still find it not done: each time, something *was* done — a gate was added — and
the item was closed.

---

## 6. Exact current flag state (read today, 2026-09-08)

| Flag | `.env` | RULED_FLAGS `expected` | Code default | Producer for A or B? |
|---|---|---|---|---|
| `CONTEXT_ENTRY_V1` | **absent** | — | **no code at all** | **would have been B — does not exist** |
| `DAYTYPE_DIR_DISCIPLINE_V1` | absent | — | **no code at all** | fix #1 for A7 — does not exist |
| `NO_CHASE_V1` | absent | — | **no code at all** | gate (B6 exemption) — does not exist |
| `DAY_DIRECTION_DOCTRINE_V1` | unset | — | `"0"` (`FLAG_INDEX.md:146`) | **gate**, OFF |
| `FAILED_BREAK_VA_V1` | `shadow` (`.env:617`) | `shadow` (`:334`) | `"0"` | producer, **POC target**, edge-rejection family |
| `VA_FADE_V1` | `shadow` (`.env:654`) | `shadow` (`:333`) | `"0"` | producer, edge fade; §D **−$1,316 / 26 sessions** |
| `RE_ACCEPTANCE_V1` | `shadow` (`.env:121`) | `shadow` (`:74`) | `"0"` | **closest thing to B**, no balance-day gate |
| `FAILED_RE_IB_V1` | — | `shadow` (`:75`) | `"0"` | failed-break at IB, t1 = IB-mid |
| `DALTON_EDGE_V1` | `live` (`.env:622`) | `live` (`:359`) | `"0"` | producer, **no POC**; **n=1 in all history** (T-271) |
| `CEILING_FLIP_SHORT_V1` | — | `shadow` (`:376`) | `"0"` | producer, POC target, double-top failure |

---

## 7. What is true, in one paragraph, if Michael asks for it plainly

*B was built as a replay, measured at **+$5,973 over 34 sessions** on 24.08, written into the task log as
T-105, and then marked "do not start" behind three other items — it has **zero lines of production code**
today, 15 days later. A was raised seven times; each of the first five times it became a blocking gate
rather than an entry; the sixth produced `failed_break.py` with a POC target which measured to roughly zero
after commissions and sits in shadow; the seventh's fix was never built; and the eighth was measured today
at −$1,488.75, with the report itself concluding that the read is right and only the stop/target geometry
is wrong. Nothing was built and reverted, nothing is hiding on a branch, and no measurement ever said the
idea was wrong.*

---

**Verification note (Rule 5):** every claim above carries a `file:line`, a commit hash, or the exact grep
string and its count. The greps that returned zero are quoted with the strings searched, per the standing
rule that `grep ⇒ 0` proves only that *the string I guessed* is absent.
