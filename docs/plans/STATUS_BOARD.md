
# Status Board · Pre-LIVE Pipeline V2

## 2026-06-12 EOD (Cowork — היום הראשון שה-runner שילם: 5×T2, נטו −$351)

**[2026-06-12 15:12 CT — EOD]** **יום-תצפית-העוגנים** (אומת ב-.env: `RUNNER_TARGETS_V1=1`+`PATTERN_RISK_CAPS=1`+`PATTERN_LOSS_BREAKER` של `720f464`) — root=הכשל של 06-11 היה **תיאום-מגמה, לא mechanism**: ביום V-reversal (7423.5→LOW 7366.5→בר-טיל +43.5pt@09:50 CT→HIGH 7461.5→סגירה 7433.5) נורו 23 (15×S4+8×S2), 15W/6L (71%), נטו **−$350.75** (מול −$2,187 אתמול) + 2 PARTIAL פתוחים +$145 — **5 פגיעות-T2 אמיתיות 2.6–3.15R (Σ≈+14.65R), כולן עם-המגמה** ⇒ **I-29 ממוסגר-מחדש 🔴→🟡** (אין revert ל-`319e303`; הכיול=veto-מגמה+טבלת stop/target). כמעט-כל-הנזק: ZLR-SHORT×2 לתוך בר-הטיל (id69/70, stop-משותף 7429.75, **−$1,069** — **I-28 יום-3-ברציפות + I-30 נמשך**) + REACTIVE_LONG×2 בראש-רנג' (−$480, חשוד-כיול חדש §D4). **חשודים חדשים: I-31** (ספירת-ירי שקרית ב-pattern-status: FaMir count=5/HFE=4 עם אפס עסקאות — display שמרעיל כיול) · **I-32** (gap-ids 64/72/76 ב-v9_trades) · **I-22 חודד** (שבור רק בנתיב-T1/BE; נתיב-T2 מחזיר R נכון ⇒ תיקון=branch אחד) → verified: `/trades/recent` 23 עסקאות + 78 ברי-RTH מלאים + `pattern-status` post-close (raw ב-`PATTERN_EOD_2026-06-12.md`) → solutions designed: `DESIGNS_2026-06-12.md` D1–D9 (עדיפות: D8 stop/target → **D3 veto-מגמה** → D5 cluster-guard → D2 I-31). **בונוס:** `PATTERN_LOSS_BREAKER` ככל-הנראה עבד חי — ZLR נעצר אחרי בדיוק 2 הפסדים, REACTIVE_LONG אחרי בדיוק 2 (CC לאמת בלוג). **OPEN:** סוכן-DIAG לא רץ **יום שני ברציפות** (0 snapshots — לתקן trigger לפני יום-המסחר הבא, §D6); id86/88 TLB PARTIALs פתוחים (stop-משותף 7417.75) — לעקוב בפתיחה; `data.mode_context` blocker חדש-בשם על 6 תבניות-S2 — CC לאמת שאינו re-enable מוסווה של chop-gate; opening_type=OPEN_REJECTION_REVERSE סווג נכון ביום-V (S1-opening ✓) אך I-1 residual (`session_min=0`) נמשך.

**[2026-06-12 15:20 CT — missed-trades EOD]** root=ה-unfired היה רווחי היום: 5 ZLR-flags ברנג'-אחה"צ + cluster 50×ZLR-LONG `ready_to_route=False` — כולם מפסידים ⇒ **חיסכון ≈+6R**; פוספסו ≈+2R בלבד: **ZLR-DOWN 14:15 (T1 ✓, MFE ~7.9R — נחסם I-3 fire_setup)** + continuation-LONG אחרי בר-הטיל 09:50 (**אין detector — יום-3**, I-28/D3) → fix מוצע: D8 stop/target (משחרר גם winners) + D3 + חיווט reject_reason ל-flags לא-מנותבים → verified: 23 עסקאות `/trades/recent` (R מ-pnl_usd, לא pnl_r/I-22) + 78 ברי-RTH + woodies 11:15→15:20 + replay על OHLC חי. **🎯 benchmark: 4/5 סלוטים (3 מדויק) — ולראשונה סלוטים 1–2 שילמו (id65/id66 = 2×T2)**. 🆕 ממצא: יום **R-חיובי (סגורות ≈+0.7R) שהפך $-שלילי (−$495)** — sizing קבוע (3 חוזים) על stops 2.75–48.5נק' ⇒ $-risk לא-מנורמל $41–$727/עסקה (→I-13/D8). חריג id74: MFE 2.81R, t1_hit=0, −1R (→I-3, CC). דוח: `docs/reports/MISSED_TRADES_2026-06-12.md`; register עודכן (I-3 + סעיף EOD 15:20).

## 2026-06-11 EOD (Cowork — אימות-חי של 319e303: מכנית ✅ כלכלית ❌)

**[2026-06-11 15:12 CT — EOD]** root=`expected_t2_r_mult=2.0` לא מתממש (runner נעצר BE אחרי T1; רק 2/21 wins=TIME_STOP אמיתי) → 34 ירי (32×S4+2×S2), 21W/12L (64%), **נטו −$2,187 shadow**; 2 חשודים חדשים: **I-29** (כיול runner/BE-policy) · **I-30** (cluster-stacking: 5×HFE על stop-זהה, −$1,372 בבר-אחד; CF-guard ≈+$1,665) · **I-22 הוכח סופית** (`pnl_usd÷pnl_r=1.25` בדיוק בכל 13 WINs ⇒ מחלק=tick $1.25) · **I-28 אומת סימטרית** (SHORT-נגד-ראלי −$1,559 אחרי בר-הטיל 12:25 CT) · **I-9 נסגר** (EOD רץ 15:12 CT אחרי-סגירה) → verified: `/trades/recent` 34 עסקאות + 78 ברי-RTH, פירוט-raw ב-`PATTERN_EOD_2026-06-11.md` §1/§4 → solutions designed: `DESIGNS_2026-06-11.md` D1–D7 (עדיפות: D5 טבלת stop/target → D2 כיול runner). **OPEN:** סוכן-DIAG-30דק' לא רץ היום (0 snapshots — לתקן trigger לפני מחר, §D6); id60 ZLR PARTIAL פתוח, runner +25pt בסגירה — לעקוב בפתיחה.

**[2026-06-11 15:20 CT — missed-trades EOD]** root=ה-gates כבר לא הבעיה — ירי עובד אבל היד-על-העסקה לא: ΣR אמיתי **−5.81R** מול ΣMFE זמין **+39.1R** (19/34 גורדו +0.01R; counterfactual exit-at-T1 עדיין −1.88R כי T1 ממוצע=0.46R ⇒ השורש=target מנוון, I-3/D5) → fix מוצע: D5 טבלת stop/target קודם, אח"כ D2 BE-policy → verified: 34 עסקאות `/trades/recent` (R מחושב מ-stop_initial, לא pnl_r המנופח I-22) + replay על OHLC חי. **setups שזוהו-ולא-ירו: 6 בלבד, ΣR-נגד ≈ −2R (ה-gates חסכו)**; חריג: ZLR-UP 14:10 (+1R) לא ירה ובאותו בר ירה TLB-SHORT (−1R) — I-26 הורחב לדו-כיווני. **🎯 benchmark: 4/5 סלוטים אותרו עם ירי** (מול 0/5 ב-06-05/06-10). דוח: `docs/reports/MISSED_TRADES_2026-06-11.md`; register עודכן (I-22/I-26/I-29 + סעיף EOD).

## 2026-06-11 (CC+Cowork — S2+S4 fire fixes deployed to SHADOW)

**[2026-06-11 — 🟢 S2+S4 fire blockers resolved + deployed (`319e303`)]**
- **finding (Cowork diagnosis, CC log verification):** A7 `pre_fire_validator` measured R:R against T1 (scalp, 0.4-0.8R by design) instead of T2 (runner ~2R). **Result: EVERY valid trade blocked for the past week.** Logs show 7 S2 detections + 13 S4 detections on 06-10, ALL rejected by A7. Additionally, B-13 stale bar filter's shared `_latest_known_price` blocked 18,567 woodies_5min bars from routing (woodies CCI bars carry different prices from different chart periods).
- **fix (3 changes, commit `319e303`, all flag-gated default-OFF):**
  1. `pre_fire_validator.py`: R:R computed on T2/runner. When T2=None (CCI-cross deferred §1.6), uses `expected_t2_r_mult` (default 2.0). + `MEMS_MIN_RISK_POINTS`/`MEMS_MAX_RISK_POINTS` stop-sanity gates.
  2. `bars.py _route_bar`: price-band stale check only for 5min stream (woodies/tpo/footprint exempt).
  3. `state_machine.py`: provisional day_type at 30min from developing IB (`S1_PROVISIONAL_DAYTYPE` flag).
- **verified (Rule 5 raw):**
  - Tests: `18 passed` (4 provisional + 3+4 risk gates + 7 R:R runner). Full suite: `237 passed, 1 pre-existing failure`.
  - RED-on-revert: OLD R:R=0.40 BLOCK → NEW R:R=2.0 PASS (9/9 Cowork simulation ZLR setups).
  - Post-restart: `/health` OK, 0 woodies BLOCKED in new log, bridge 0 errors.
- **flags set in .env:** `S1_PROVISIONAL_DAYTYPE=1`, `MEMS_MIN_RISK_POINTS=2`, `MEMS_MAX_RISK_POINTS=60`, `STOP_ANCHORS_V2=1` (was already set).
- **OPEN (awaiting RTH 09:30 ET for live verification):** day_type≠UNKNOWN@30min, S4 fire in v9_trades, stop-gate rejections in log, no regression.

## 2026-06-10 (Cowork — S4 target/stop spec ננעל פר-תבנית)

**[2026-06-10 15:24 CT — סוכן-EOD דיאגנוסטי (Cowork) · 9 snapshots + API חי]** (ראיה: `docs/reports/PATTERN_EOD_2026-06-10.md` · `DESIGNS_2026-06-10.md` · `MEMS26_ISSUES_REGISTER.md` §EOD)
- **finding (3 fires):** S4 HFE LONG ×3 (id24/26/27) נגד trend RED, **3/3 STOP_HIT −1R** (ΣR −3R / −$71.25 shadow). stop צמוד 1–2pt; id27 MFE **+16.75pt** = מנצח-שאבד.
- **finding (counterfactual · raw `bars5min` 78 ברי-RTH, ירידה 7355→7276):** כל ה-SHORTים עם-המגמה (ZLR/TLB/GB100/GHOST/HTLB) נחסמו A7 R:R<1.0 (target מנוון 3pt); ב-CF (targets שפויים 1R/2R) **4W/0L, ΣR ≈ +3R**. ⇒ ה-bottleneck עלה על רווח עקבי עם-המגמה (≠06-09 שבו CF ≈ +1R).
- **🔴 verification (Rule 5 — committed-but-not-effective):** PHASE1 (`6c58d05`+סבבי-תיקון) של טבלת stop/target **לא אפקטיבי ב-stack הרץ היום** — 3 ה-fires יצאו `t2=null` + stop מנוון 1–2pt (התנהגות-ישנה), ו-9 תבניות-S4 עדיין `targets_stop.r_t1_gate` block. **לאמת מול CC** (restart/flag/wiring) לפני סימון I-3/I-13 כסגור.
- **חשודים חדשים:** I-26 (A7 reward↔target inconsistency) · I-27 (flicker-detection per-bar על trend יציב) · I-28 (reversal HFE יורה נגד-מגמה — D2, **טעון-החלטת-Michael**).
- **OPEN (read-only · designs מוכנים):** I-22 win-path מנופח (אין WIN טרי לאימות) · I-23 4-ספירות-ירי סותרות · I-10 `pre_fire_validator`/`risk_checks` absent ב-payload · I-18/I-20 freshness TZ+ts-עתידי+stale-עובר-READY · I-1 day_type split.

**[2026-06-10 — S4 אפיון-יעדים מלא (9 תבניות) ננעל ויזואלית מול Michael + טבלת-בחינה]** (ראיה: `docs/plans/MEMS26_S4_REVIEW_TABLE_2026-06-10.xlsx`)
- **finding:** עד היום ל-S4 ננעלו רק עוגני-סטופ + T1 + sizing (06-07); ה-**יעדים פר-תבנית (T1/T2/T3)** היו placeholder — הדיטקטורים פולטים T1/T2 בטיקים-קבועים (ZLR 12/24 וכו'), בלי T3, day-type-blind. שורש I-3 (ZLR ב-A7: target מנוון 1pt → R:R≈0.06 → אין fire_setup).
- **solution (ננעל, Cowork+Michael · walkthrough ויזואלי פר-9-תבניות):** T1 = **סולם-סיכון 0-25** (לא נוסחת-Flag 15-25; REV ×0.8; HFE מדרגה−1) · VEGAS T1=Measure×0.75 / T2=Measure×1.0 · GHOST T1=Measure×0.5 / T2=חציית−100 / T3=חציית+100 · HTLB T2=חציית-ZL / T3=חציית+100 · FAMIR T2=חציית−100 (נגדי) · CONT (ZLR/TLB/TT/GB100) T2=חציית+200 · **סטופ = 3T מעבר-לקצה-הבר (לא עליו)** · ATR=שער-גודל (סטופ מבני גובר).
- **verified (Cowork):** טבלת-בחינה xlsx הופקה ואושרה פר-תבנית מול Michael; 9 הדגמות-נרות ויזואליות (כניסה/סטופ/T1/T2 על נרות + פאנל CCI).
- **OPEN (מימוש — trading-logic, flag-gated SHADOW · אופציה 1 אושרה Michael 06-10):** Phase 1 = (1) `t1_ladder_continuation` ל-**כל 9** (כיום רק HTLB+FAMIR) + (2) **T1 (כל 9) + VEGAS T2 בלבד** → `fire_setup` (סוגר I-3; T1+סטופ פותחים A7) + (3) `config/stop_anchors.yaml` ערכי-06-10. **יעדי-T2/T3 שהם חציות-CCI = None ביושר** (Rule 1). **משימה-2 נדחית:** מוניטור-חציית-CCI ל-T2/T3 — תוספת מוכלת ל-`b11/b12` (Woodies רואה CCI פר-בר; **לא** rebuild של trade-manager הגנרי, אומת בקוד). + (4) רובריקת-detection ב-SHADOW (S1/S2/S4 · needed-מול-actual · אחוזי-בנייה). פרומפט: `docs/handoff/CC_MEGA_S4_TARGETS_DAYOPEN_DASHBOARD_2026-06-10.md`.

**[2026-06-10 — אימות‑Cowork ל‑PHASE1 של CC (`6c58d05`): 4 בעיות → פרומפט‑תיקון]** (ראיה: grep + קריאת‑קוד חי)
- **finding:** (1) 🔴 Rule‑1 — measure של VEGAS/GHOST **מסונתז** (`woodies_system.py` proxy `risk×2`/`×1.5`; הדיטקטורים לא חושפים `measure_pts`) → T1/T2 לא מהגאומטריה. (2) 🔴 B1 — טסטי‑VEGAS/GHOST/CCI‑None בודקים **ערכי‑YAML בלבד** (עוברים גם עם ה‑measure המזויף); `test_s4_fire_setup_routable` (I‑3) **חסר**. (3) 🟡 Phase 2 (formula needed‑מול‑actual + build%) **לא בוצעה** (grep=0; DetectionPanel הוחזר). (4) 🟡 דוח‑חובה חסר + ראיה=replay סינתטי, לא ירי חי.
- **תקין:** T1‑סולם CONT/FAMIR/HTLB/HFE (קורא `SA.t1_price`) · CCI‑cross=None · שריד‑option‑A (`targets_table`) הוסר · VEGAS cap=0.75 · flag‑gated.
- **solution:** פרומפט‑תיקון `docs/handoff/CC_FIX_S4_MEASURE_TESTS_PHASE2_2026-06-10.md` — measure אמיתי (head−neckline ÷25 / עומק‑כוס, או None) · טסטים על קוד‑הירי + `test_s4_fire_setup_routable` · השלמת Phase 2 · דוח+ראיה חיה.
- **verified (Cowork, raw · סבב‑1):** `grep targets_table`=0 · `measure_pts` נעדר מ‑details · `grep formula|build_pct`=0 · אין דוח.

**[2026-06-10 ערב — סבבי‑תיקון 2‑4 + אימות‑Cowork חוזר]**
- **סבב‑2 (`11425c2`+`814c684`):** FIX A תוקן (measure אמיתי מהגאומטריה, proxy נמחק — Cowork raw: grep=0). אבל טסטים עדיין ריקים (GHOST `detected=False` → assert לא רץ; fire_setup רק `bar_buffer`); C/D דולגו בשקט (B3).
- **סבב‑3 (`3106c5f`+`88aa189`):** GHOST‑test אמיתי (Cowork raw: `detected=True · measure=4.4`) · FIX C בוצע (`woodies_inspector._build_s4_formula`+`build_pct`+PatternsTab `formula`) · דוח `MEGA_S4_TARGETS_2026-06-10.txt` עם NOT‑DONE (B3 תוקן; live‑fire נדחה — RTH סגור, לגיטימי). 10 טסטי‑spec עוברים.
- **פרצה שנותרה → סבב‑4:** `test_s4_fire_setup_routable` בודק `stop≠None` (תיקון ישן 06‑08), **לא** R:R/fire_setup → I‑3 לא מוכח בטסט (אומת ע"י קריאת‑האסרטים). פרומפט: `docs/handoff/CC_FIX_S4_ROUND4_I3_TEST_2026-06-10.md` (assert על R:R אמיתי + RED‑on‑revert של לוגיקת‑ה‑T1; Cowork יהפוך T1 בעצמו ויוודא FAIL).
- **OPEN:** סבב‑4/5 (טסט‑I‑3 — נכשל בריצה נקייה כי harness בלי day_type → fire_setup=None; אומת ע"י Cowork) · אימות‑חי ב‑RTH (ירי‑SHADOW עם stop/T1 ב‑`v9_trades`) · S1/S2 formula (רק S4 בוצע) · §1.6 CCI‑monitor (נדחה בכוונה).

**[2026-06-10 — סוכן ביקורת‑EOD (בקשת‑Michael) — ספציפיקציה הוכנה]**
- **goal:** סוכן רב‑פעמי ב‑EOD: (1) לסיים בדיקות · (2) סריקת‑SHADOW (עבד‑לפי‑האפיון? מידע‑נכון?) · (3) counterfactual פר S1/S2/S4 — אילו תבניות היו צריכות לירות, האם נכנסה, וכמה $ צריך היה להרוויח/להפסיד.
- **design (audit‑before‑build):** מתזמר קיים — `missed_trade_detector` (ADAPT: +S1, +full‑session replay, +$) · `daily_quality_agent` (KEEP) · `historical_replay` (KEEP) · `eod_archiver`/scheduler 15:55 ET (KEEP, נקודת‑הפעלה). שכבה חדשה: P&L counterfactual פר‑מערכת מהאפיון‑הנעול. observability בלבד.
- **deliverable:** `docs/handoff/CC_AGENT_EOD_SHADOW_AUDIT_2026-06-10.md` → סוכן `backend/v9/services/eod_shadow_audit.py` → דוח `EOD_AUDIT_<date>.md`. **ריצה‑1: סוף יום‑1.** OPEN: מימוש ע"י CC + ריצה ראשונה ב‑RTH close.

**[2026-06-10 10:05 ET — 🔴 day_type@30דק' לא סוּוַּג (תקלה חוזרת · Michael flag · אומת חי ע"י Cowork)]**
- **finding (raw, `v9_day_type_state`):** ב‑10:05 ET (RTH+35דק') `day_type=UNKNOWN`, `opening_type=OPEN_DRIVE`. ספירת‑היום: UNKNOWN×~109 (NA×93, OPEN_DRIVE×12, ORR×4), ורק **1** שורה `Variation` (לא נדבקה). opening_type כן מחושב (אך לא‑יציב בפתיחה: ORR→NA→OPEN_DRIVE), אבל **day_type נתקע UNKNOWN** הרבה אחרי 30דק' → חוסם auth/sizing של S2/S4 (אותו שורש של `fire_setup=None` בטסט‑I‑3).
- **השערה (לא‑מאומת · diagnose‑first):** שלב‑סיווג‑day_type@30דק' (`app.state.day_type_machine` / `main.py:_day_type_on_bar`) לא מייצר/מתמיד `day_type≠UNKNOWN` למרות opening_type≠NA; ה‑Variation היחיד מרמז שהלוגיקה יכולה לרוץ אך לא נדבקת. FIX 1 תיקן opening_type=NA — לא את הסיווג‑בפועל.
- **OPEN (קריטי · גוזר את כל הירי היום):** diagnose חי בעוד RTH פתוח — למה day_type=UNKNOWN ב‑30דק' עם opening_type=OPEN_DRIVE; לבדוק `app.state.day_type_machine` (לא ה‑wrapper המת), זמינות‑IB@30דק', ונתיב‑הפרסיסט ב‑`main.py`.

**[2026-06-10 ~10:1x ET — 🔴 חוסמי‑ניתוב חיים (build‑status TLB) · I‑3 לא סגור חי + רגרסיות]** (ראיה: snapshot מ‑Michael)
- **finding:** TLB Armed עם `detection✓` + `day_type=Variation✓` + stop=7381.75/target=7400✓, אבל **`r_t1_gate=null`** (= I‑3 **חי, לא סגור!**) ו‑**`day_type_matrix="lookup error"`** → `ready_to_route=False` → **לא יורה.** ה‑unit‑tests של CC עברו (10 ירוקים) אך ה‑inspector‑החי מראה r_t1=null → **הטסטים לא תפסו את הרגרסיה** (מאשר את ה‑NO‑GO של I‑3).
- **השערות (diagnose‑first):** (1) matrix‑lookup‑error = key‑mismatch `Variation` מול `NV`/`Normal Variation` ב‑`day_type_matrix.yaml`. (2) r_t1=null = ה‑T1‑החדש (Phase‑1 סולם) לא מחווט לשדה‑r_t1 ב‑inspector. שתיהן כנראה **רגרסיה מ‑`6c58d05`/`88aa189`**.
- **solution:** `docs/handoff/CC_DIAGNOSE_LIVE_S4_ROUTE_BLOCKERS_2026-06-10.md` — **diagnose‑only**, strategic‑stop + אישור Michael לפני תיקון.
- **OPEN (קריטי):** אבחון‑שורש + הצלבת‑רגרסיה · future‑ts (I‑18) · ZLR לא‑זוהה · day_type שהחל UNKNOWN.

## 2026-06-09 (RTH · Cowork verify + CC fixes)

**[2026-06-09 15:12 CT — EOD מאוחד (Cowork): 2 fires, ΣR-נגד +1R, 3 בעיות חמורות]** (ראיה: `docs/reports/PATTERN_EOD_2026-06-09.md` + `DESIGNS_2026-06-09.md` + register EOD)
- **finding:** 2 עסקאות-shadow היום — S4 HTLB id=20 **WIN** (runner +106pt, R-אמיתי ≈+42R) · S2 BEAR_FLAG_SHORT id=22 **BE** (יציאה ידנית קטעה ~+1R). תחזית-נגד ZLR (3 signals, targets שפויים): **2W/1L, ΣR ≈ +1R** — חסימות לא קטעו רווח משמעותי. **3 חמורות:** I-22 (pnl_r ×10, שורש מאומת raw: `÷$1.25` טיק ולא `÷risk_$`) · I-3 (ZLR ב-A7 חסום, target מנוון 1pt → היעדר טבלת stop/target) · I-18 (ts עתידי 06-10 **אומת ברמת DATA** ב-`/chart/bars5min`, לא רק gate).
- **proposed solution (DESIGNS §D1–D6, לא בוצע — read-only):** D1 pnl_r `÷risk_$` (🟢 safe) · D2 טבלת stop/target→fire_setup (🔴 trading-logic, אישור Michael) · D3 נרמול-ts UTC+guard עתידי (🟢) · D4 freshness predicate `|lag|≤thr` (🟢) · D5 gateway counters→shadow (🟢) · D6 doc-fix limit≤100 (I-25 חדש).
- **verified (Cowork, raw API חי):** id=20 `contracts_pnl` C1 `$17.5÷14R=$1.25`=טיק (שורש I-22); bars5min bar אחרון ts=`2026-06-10 22:40:00+03:00` (I-18); counterfactual שוחזר מ-99 ברי-5דק'. **אל-תיגע-בקוד — קריאה/תיעוד בלבד.**
- **OPEN:** D2 ממתין טבלת stop/target + אישור Michael (trading-logic). הצלבות-Sierra (CCI/woodies_5min-ts/footprint/pnl_r) → CC.

**[2026-06-09 — opening_type=NA → S1 day_type=UNKNOWN כל הסשן (S2 auth-SKIP) — FIX מיושם]**
- **finding:** S1 לא סיווגה כל הסשן (`day_type=UNKNOWN`, `opening_type=NA`) → S2 SKIP → 0 ירי מוקדם. **לא תקלת Sierra/TPO** — TPO פעיל ונכון (POC 7435 · VAH 7456 · VAL 7397.75 · IB `found:true high:7417 mid:7403.88 low:7390.75`, תואם `key_levels` בול). שורש: `state_machine._stage_a2` *כן* מחשב opening_type (`detect_opening_type_cvd`), אבל `main.py` שמר ל-DB את הערך מ-TPO-normalization שמקודד-קשיח `"NA"` (`tpo_routes.py:383`) → דרס את הערך הנכון בנתיב-הפרסיסט.
- **fix (CC, מאושר Michael):** `main.py:237` קורא opening_type **מהמכונה** (`day_type_machine.opening.opening_type`, `.value`), TPO רק fallback. תיקון-מקור, לא שינוי בלוגיקת-סיווג.
- **verified (Cowork, raw):** קוד נוכח ומאומת (`main.py:233-242`). **live-verify ממתין restart** — DB היום עדיין `opening_type: NA×73, OPEN_DRIVE×2` כי ה-backend החי טרם אותחל עם התיקון. CC לאתחל → להראות `opening_type≠NA` עקבי + `day_type≠UNKNOWN` בחלון.
- **OPEN (anti-partial-wiring):** ה-auth/`setup_emitter` עדיין מאשר רק לפי `day_type` → צריך נתיב `opening_type→אישור` בחלון 15–30דק' כדי ש-S2/S4 *יורו* (החלטת-Michael: opening_type@15דק' מאפשר ירי · day_type@30דק' + reclass רציף · IB-lock@60דק'). בלי זה opening_type נכתב נכון אך הירי נחסם.
- **תיקון-Cowork:** אזעקת-שווא קודמת על "IB מזויף" הייתה קריאה-שגויה מ-grep שטוח (ייחס `previous_session.ib_found=false` להיום) — תוקנה; ה-IB תקין. כלל-מניעה נשמר.

**[2026-06-09 11:13 CT — PATTERN_DIAG snapshot #6: I-3 ZLR הגיע ל-A7 לראשונה (ממצא חדש)]** (ראיה: `docs/reports/PATTERN_DIAG_2026-06-09.md` §11:13 · Build Status `ss_8495tn5t4`)
- **finding:** ZLR נדרך ו-`active_patterns=[ZLR SHORT conf 0.65]`, dtree A1–A6 PASS אך **A7 FAIL "missing fire_setup for routable pattern"**. חוסם מדויק (`build/pattern-status`): `targets_stop.r_t1_gate / stop_price / targets` + `exit_rules.ready_to_route`. ה-target מנוון (1pt מול stop 17.75pt ⇒ R:R≈0.06) — שער R:R צודק שחוסם, אבל **סימפטום של היעדר טבלת stop/target** (בלי T1/stop אמיתי לא נבנה `fire_setup`).
- **proposed solution (CC, לא בוצע — read-only snapshot):** לחווט `targets_stop`/`exit_rules` ל-`fire_setup` + להזין טבלת stop/target פר-תבנית×day-type (חופף project stop/target table). זהו ה-reject_reason הקונקרטי ל-I-3.
- **verified (Cowork, raw):** `woodies/current` dtree A7=FAIL + `build/pattern-status` S4 blockers — מצוטטים מלא בדוח. **אל-תיגע-בקוד נשמר.**
- **נלוות:** S2+S4 **ירו היום** (id=22 BEAR_FLAG_SHORT פתוח · id=20 S4 TIME_STOP WIN). I-22 (pnl_r ×~5.5 ניפוח, id=20=233R) + I-23 (gateway counters=0 מול 2 עסקאות) **חוסמים ΣR-counterfactual**. I-11 (אישור #27, footprint 0 ברים) · I-18 (woodies_5min ts עתידי 2026-06-10) — נמשכים. verdict=READY.

## ✅ 2026-06-08 (RTH-prep, Cowork+CC) — GO + צ'קליסט-מצב

> מקור: `docs/reports/SYSTEM_START_2026-06-07.txt` (CC, raw) + בדיקות-Cowork חיות (Chrome).

**הערכת-GO לקראת RTH: 🟢 ירוק.** ה-pipeline שלם: Sierra→גשר→backend(Postgres)→frontend.

| # | קריטריון | מצב | ראיה |
|---|---|---|---|
| 1 | backend uvicorn יחיד · health ok | ✅ | health 200, uptime |
| 2 | **DATABASE_URL=postgresql://localhost/mems26** (סוגר חשד-SQLite) | ✅ | `ps eww` בתהליך הרץ |
| 3 | אין שגיאות sqlite/malformed בלוג | ✅ | `clean` |
| 4 | דגלי-כיול ON | 🟢 6/7 | S1×3·S2_ATR·S3_RELATIVE·S2_VSA = ON · ⚠️ `S3_MUTE` לא הופיע (משתיק S3-החשוך; לא-חוסם, לאמת) |
| 5 | גשר דוחף ל-localhost | ✅ | log `push #780` כל הזרמים (status-probe `timeout` = I-19 קוסמטי, לא הגשר) |
| 6 | frontend :3000 | ✅ | 200 |
| 7 | Sierra כותבת | ✅ | `active`, fresh<1s |

**נסגר היום:** ✅ חשד-SQLite (DATABASE_URL ב-`.env`) · ✅ באג-דגלי-שישי (`bcdf43e`, אומת חי) · ✅ SPEC-סטופים נעול (14 תבניות, `c2cfd40`) · ✅ T3 חי (restart).
**פתוח (RTH היום):** I-21 stall (פרומפט-אבחון מוכן) · אימות-ירי-חי S2/S4 · S3_MUTE · I-20/C-6 (דגימת-ts).
**משימות-בפועל מוכנות (פרומפטים):** `CC_START_SYSTEM` · `CC_PROMPT_I21_I20_RTH_DIAGNOSE` · `CC_PROMPT_P5_0_GATEWAY_AUDIT` · `CC_MASTER_OFFLINE_SWEEP` · מעבר-מחשב: `MIGRATION_TO_NEW_MACHINE` (+ חבילה בהכנה).

**[2026-06-08 08:42 CT — snapshot-דיאגנוסטיקה חי סותר את ה-GO בשתי נקודות]** (ראיה: `docs/reports/PATTERN_DIAG_2026-06-08.md` §08:42):
- **root: ערוץ-היצוא 5דק'/study לא עלה הסשן** (I-21 כ-session-non-start). `build/pattern-status` verdict=**BLOCKED** (`dead: tick_reversal,5min_bars`); gates `woodies_5min`/`5min_bars`/`tick_reversal` DEAD מ-שישי 06-05, בעוד `footprint`/`cumulative_delta`/`volume_profile`/`imbalance` FRESH 0s. ⇒ הקריטריון #7 ("Sierra כותבת fresh<1s") נכון רק לערוץ tick/footprint; ערוץ ה-5דק'/study **מת**. S1/S2/S4 רצים על ברי-שישי קפואים (woodies `cci_14=-139.56` קפוא, day_type=UNKNOWN). **fix מוצע (ל-CC):** לאבחן למה study/5min export ב-Sierra לא התחיל ב-08:30 CT. **verified:** gates+systems raw בדוח.
- **#6 frontend :3000 ירד** מאז ה-GO (`fetch localhost:3000` = Failed to fetch) — אין לוח לצלם.
- אישור: I-11 (footprint 0 ברים, ingest-break) עצמאי מ-I-21 · I-20 (freshness predicate משקר fresh=true על lag 2.7 ימים) · I-19/I-16 לא משחזרים.

**[2026-06-08 09:40 CT — snapshot #3, 70דק' לתוך RTH]** (ראיה: `docs/reports/PATTERN_DIAG_2026-06-08.md` §09:40 + snapshot `docs/reports/snapshots/build_status_2026-06-08_0940CT.html`):
- **🟢 התקדמות:** ערוץ 5דק'/study **חי** (woodies_5min/5min_bars/footprint-file FRESH 09:40). **day_type סוּוַּג=Trend_Normal** עקבי על 3 משטחים (state+readiness+S2-gate) ⇒ I-1 פיצול-3-כיווני לא משחזר, day_type כבר לא חוסם S2 → ירד 🔴→🟡. השוק התהפך: woodies `cci_14` חצה אפס −154→**+121.6**, trend נכנס ל-**GRAY** (מנוע+לוח מסכימים ⇒ I-15/C-1 לא משחזר, GRAY אמיתי).
- **🔴 חוסמים נותרים:** verdict=**BLOCKED** root=`tick_reversal` DEAD מ-שישי (session-non-start, I-21 מבודד ל-ערוץ זה). I-11 (footprint file FRESH אך 0 ברים, ingest-break) אישור 15 — עצמאי מוכח שוב. I-16 (choppiness_ok מסומן Missing על 6 תבניות-S2 בעוד chop_state=EXPANDING; score≠gate-flag) — מבודד כעת לחוסם-יחיד. I-22 (pnl_r ~50× inflation) גלוי בערכי-שישי. I-20/I-18 (TZ-mix, fresh=true על lag שלילי -3h) נמשך.
- **fix מוצע (ל-CC):** (1) tick_reversal — למה לבדו לא עלה ב-08:30 CT; (2) footprint ingest file→bridge→buffer; (3) choppiness_ok — לחווט הדגל הבוליאני מ-chop_state; (4) TZ-normalize גייטים ל-UTC + אכיפת-סף על lag. **verified:** gates+systems+readiness raw בדוח; 8/8 endpoints <200ms (I-19 נקי).
- **0 fires היום** (trend GRAY חוסם S4, choppiness_ok חוסם S2-מומנטום, feed-dead חוסם S3, auth-skip לגיטימי חוסם S2-day-patterns) ⇒ אין signal שעבר detection-ונחסם → אין counterfactual לחשב.

**[2026-06-08 — I-16 choppiness_ok root-fix אומת (CC `4a073c6`, Cowork-verified Rule 5)]**
- **root:** `compute_choppiness` קרא `bars[:max_bars]` (6 הברים הכי **ישנים** מתוך חלון-14) → הציון נתקע ~75-93 ממבנה-פתיחה ישן ולא התעדכן ⇒ `choppiness_ok=score<70` נכשל על כל 10 תבניות-S2. ההשערה הקודמת בלוח (09:40 "score≠gate-flag / לחווט מ-chop_state") **שגויה** — הציון *כן* היה קלט-הגייט, רק חושב על ברים בייתים.
- **fix:** שורה אחת `window = bars[-max_bars:]` (חלון מתגלגל אמיתי) + docstring מעודכן (תואם-קוד). 5 טסטים חדשים `tests/v9/regression/test_choppiness_rolling.py`.
- **verified (raw, Cowork):** הרצתי את `compute_choppiness` ישירות — 5/5 ההנחות עוברות; live-sim: באפר-14 (פתיחה-choppy, מגמתי-עכשיו) → OLD `[:6]`=**75.0** (≥70 חוסם) · NEW `[-6:]`=**35.0** (<70 פותח). (189-regression המלא = על ה-Mac; ה-sandbox חסר sqlalchemy.)
- **🔴 שאריות פתוחות (anti-partial-wiring):** (1) **גייט-chop #2 לא נגע** — `trading_gateway.py:111` `chop_state=="SEARCHING"→BLOCKED` הוא מטריקה אחרת (Layer0 `chop_score`, לא `choppiness_score`); תיקון CC לא משחרר ירי-SHADOW אם Layer0=SEARCHING. (2) **restart נדרש** — שינוי-קוד; backend חי לא קולט עד אתחול; ב-hydrate הציון נטען מ-DB (`five_min_system:263/280`) עד הבר הבא שמחשב מחדש. (3) **לא disable** — אם הזנב באמת choppy, הגייט עדיין יחסום (נכון/כנה).

**[2026-06-08 — שני שערי-chop כובו (Michael directive, "גם וגם", default-off + CLAUDE.md)]**
- **directive:** Michael — לכבות את `choppiness_ok` של S2 *וגם* את שער-Layer0 ב-gateway, ולהשאיר כבוי עד אישור מפורש; לתעד ב-CLAUDE.md. **בוצע (Cowork).**
- **fix:** (a) `s2_inspector.py` — `choppiness_ok` flag-gated `S2_CHOPPINESS_GATE` (default-off ⇒ `chop_ok=True`, הציון עדיין מוצג). (b) `trading_gateway.py:111` — veto `chop_state==SEARCHING` flag-gated `LAYER0_CHOP_GATE` (default-bypass, עדיין מחושב+לוג). שניהם `os.getenv` ב-runtime → דורש **restart**. CLAUDE.md §"Chop Gates (DISABLED)" + טסט `tests/v9/regression/test_chop_gates_disabled.py`.
- **finding שאומת תוך כדי:** `choppiness_ok` הוא **inspector-only** — `s2_inspector.inspect` מיובא רק ב-`build_status/aggregator.py`; מסלול-הירי האמיתי (five_min emit→trade_manager→gateway) **לא** חוסם על `choppiness_score` כלל. כלומר הוא חסם רק את **תצוגת-הדריכה**, לא ירי-S2 אמיתי. שער-הירי-האמיתי היחיד ל-chop הוא Layer0 ב-gateway (#2).
- **verified (raw, Cowork; ה-suite המלא = Mac, sandbox חסר sqlalchemy):** `route_setup` עם `_get_chop_state→SEARCHING`: default-off → `blocked_by=None` · `LAYER0_CHOP_GATE=1` → `blocked_by=chop_searching`. לוגיקת-S2: score=93 default-off→pass, flag-on→block.
- **⚠️ re-enable = שינוי risk-surface** → strategic-stop + אישור-Michael (CLAUDE.md).

**[2026-06-08 — verdict=BLOCKED מדומה מזרם-מושתק תוקן (Michael catch)]**
- **Michael:** "tick_reversal זה מערכת 3 והוא בכלל לא צריך לעבוד" — נכון. **תיקון טענת-Cowork שגויה:** קודם נטען ש-tick_reversal_15 המת "חוסם ירי" — **לא נכון**.
- **finding (אומת):** `tick_reversal_15`=System 3 (footprint/tick-reversal, **מושתק** `S3_MUTE=1`); `tpo`=S5 (לא-מחווט, I-24). **אף מערכת-ירי לא צריכה אותם:** S2 נרשם רק `["5min"]`, S4 רק `["woodies_5min"]`. ה-fire-path (`gateway.route_setup` + `PreFireValidator._check_bridge_health`→`live_price.json` בלבד) **לא** בודק אותם. ⇒ המוות שלהם חוסם רק את **verdict-התצוגה**, לא ירי אמיתי.
- **root:** `aggregator.py:_compute_readiness` `_NON_CRITICAL_STREAMS` הוציא `footprint` (S3) אך **השאיר** `tick_reversal_15` (אותה S3 מושתקת) ו-`tpo` (S5) כקריטיים ⇒ זרם-מושתק גרר את הלוח ל-BLOCKED. חוסר-עקביות.
- **fix:** הוספתי `tick_reversal_15`+`tpo` ל-`_NON_CRITICAL_STREAMS` (+הערה: re-add רק אם S3 מוסר-השתקה). טסט `tests/v9/regression/test_readiness_noncritical_s3_streams.py`.
- **verified (raw, Cowork):** `_compute_readiness` אמיתי — dead `tick_reversal_15/tpo/footprint` + fire-path fresh → `bridge_streams_fresh.passed=True` (detail=None) · `bars_5min` מת → `passed=False, detail="dead: bars_5min"` (עדיין חוסם נכון, ו-S3/S5 לא ב-detail). **restart נדרש.**
- **משמעות:** verdict=BLOCKED של היום היה חלקית **מדומה** (זרם-מושתק). החוסמים האמיתיים לירי = שערי-chop (כובו היום) + trend-gate ל-S4 + detection + כיול. ⇒ המערכת קרובה-לירי יותר ממה ש-BLOCKED הראה. **קשור I-21/I-24.**


## 📍 2026-06-05 (eve, Cowork) — עסקאות SHADOW: תצוגת stop/targets + S2 T3 wiring

> מקור: `/api/v9/trades/recent` חי (Chrome) + קריאת-קוד. 2 עסקאות נוצרו (#12 S4 HTLB · #10 S2 BEAR_FLAG), שתיהן day_type=Variation.

- **[2026-06-08 RTH] ⚠️ מוכנות-ירי: BLOCKED · 0 armed (Cowork+CC, handoff `HANDOFF_RTH_READINESS_2026-06-08.md`):** ✅ STOP_ANCHORS_V2 + S4_EXTREME_TREND_RELABEL מודלקים ב-SHADOW · backend בריא · גשר חי (push #5843). **❌ אבל verdict=BLOCKED, 0/10+0/9 תבניות armed:** (1) 🔴 **אין ברי-RTH** — `v9_bars_5min` תקוע שישי 23:55; Sierra `5min.json` last=08:50 UTC (Globex), ברי-RTH של היום לא ביצוא ⇒ **Chart 5 לא מייצר** (פעולת-Michael: focus/Recalculate). (2) day_type=UNKNOWN (נגזר). (3) 🟡 **באג-שמות build inspector** — `STREAM_CHECKS` בודק `5min_bars`/`tpo_bars`/`tick_reversal` במקום `bars_5min`/`tpo`/`tick_reversal_15` ⇒ "dead: tick_reversal" שקרי (CC לתקן). **לא יורים עד ש-Sierra מזין RTH.**
- **[2026-06-08] ✅ מימוש Stop-Anchor V2 הושלם ואומת (Cowork יסוד + CC חיווט + Cowork verifier):** היסוד (Cowork): `config/stop_anchors.yaml` + loader + resolver + מנועי-V2 (S4/S2). חיווט (CC, 6 phases): 14 תבניות + sizing(min(סולם,auth,מצב)) + T1-ladder + מסווג-מצב, כולן flag-gated עם fallback ל-legacy. **אימות עצמאי (Cowork, Rule 5):** הרצתי 63 טסטי-V2 ירוקים + הצלבתי קוד מול SPEC. **תפסתי באג שטסטי-CC פספסו:** 3 משפחות-S2 מעוגנות-מבנה (Flag/Double_BT/HnS) **כפלו את ה-offset** — הפטרן מכניס −1T ו-V2 הוסיף 3T = 4T במקום 3T (ה-e2e בדקו רק `stop<=entry`, לא מרחק). **תוקן** (`0a82128`): un-bake ה-1T + טסטי-מרחק-מדויק. **מצב:** הכל ירוק, **דגל `STOP_ANCHORS_V2` OFF** = התנהגות-היום בדיוק. **נותר לפני הדלקה:** pytest מלא על ה-Mac (עם conftest/DB) + הדלקה ב-SHADOW בלבד + כיול-MFE ב-soak. commits: `00aa717`→`0a82128`.
- **[2026-06-07 ערב] 🏛️ SPEC סטופים/יעדים/גדלים ננעל לכל 14 התבניות (Michael+מחקר, יום-עבודה מלא):** עוגנים פר-תבנית (ZLR=אשכול-4 · TLB=מאז-פסגת-טרנדליין 3-8 · TT=אקסקורסיה 4-9 · GB100=חלון-6 · REV=קיצון/כתף · S2=Bulkowski: Initiative הדוק!, Flag=שפל-הדגל) · הסטופ-המבני תמיד גובר, ATR=שער-גודל, רצפה 4T · תקרת-סיכון 25 נק' · סולם-חוזים ≤15→3·15-25→2·>25→1 · סולם-T1 ‏1R→0.4R (REV ×0.8, רצפה 3 נק') · נר-ענק: חוזה-1, יעד=קו-קרוב, BE+15 · אחרי-T1 BE+1T (קאנון נשמר) · טקטית≤2/אסטרטגית≤3 (סיווג: כיוון-יום; ימי-ערך: VAH↔VAL=אסטרטגית, POC→קצה=טקטית) · **כלל-מאוחד: חוזים=min(סולם, auth/TableB, מצב)**. מסמכי-מקור: `STOP_ANCHOR_DECISIONS_DRAFT` + `MEMS26_MASTER_TRADE_SPEC_ONE_TABLE.xlsx` + ‏2 דוחות-מחקר (‏T1_LADDER + ‏ANCHOR_ALL, ‏~40 מקורות, ‏3+4 צוותים+סוכן-אימות שתפס 7 אי-התאמות). **מימוש: פתוח** — `stop_anchors.yaml`+resolver+17 נקודות-חיווט+טסטים, flag-gated, SHADOW-בלבד עד אישור-LIVE. כיול-אמת: עקומות-MFE ב-soak.
- **[2026-06-07 PM] ✅ restart בוצע + דגלים אומתו חיים · 🔴 חשד DATABASE_URL/SQLite (פתוח):** CC ביצע restart (uptime ~9דק', uvicorn יחיד pid 8310, health ok) → תיקוני T3+דגלים **חיים**. **verified by (raw):** `docs/reports/FLAG_CHECK_2026-06-07.txt` — כל 7 הדגלים בתהליך הרץ (`ps eww`): S1_CVD_OPENING/S1_DAYTYPE_STAGING/S1_IB_WIDTH_ATR/S2_ATR_RELATIVE/S3_RELATIVE=true · S2_VSA_VOLUME/S3_MUTE=1. **באג-שישי (דגלים) סגור.** 🔴 **אבל** זנב-הלוג הראה `sqlite3.DatabaseError: database disk image is malformed` על `v9_bars_5min` → חשד שה-restart עלה **בלי `DATABASE_URL`** (היה רק ב-start_all.sh, לא ב-`.env` — אותה משפחת-באג כמו הדגלים) ונפל ל-SQLite המושחת. **תוקן בשורש:** `DATABASE_URL=postgresql://localhost/mems26` נוסף ל-`.env`. **ממתין:** CC מריץ `CC_CHECK_DB_URL_RESTART_2026-06-07.md` (בודק `ps eww | grep DATABASE_URL`, restart אם חסר, פלט ל-`DB_URL_CHECK_2026-06-07.txt`). חלופה: ייתכן שזה רק ה-hydration-fallback הישן (residual מתועד) — CC יבחין.
- **[2026-06-07 PM] ✅ אכיפת-דגלים תוקנה מהשורש (Cowork) — commit `bcdf43e`:** **שורש ה-0-עסקאות-בשישי (חשד ראשי):** ה-backend קורא דגלים מ-`os.environ` ב-import-time אבל **לא טען `.env` בקוד** — רק `start_all.sh` עשה `source .env`. אתחול דרך ה-LaunchAgent (auto-restart) או uvicorn ידני → כל דגלי-SHADOW נפלו ל-default OFF. **תיקון:** `backend/env_loader.py` (parser stdlib, לא דורס env מפורש, missing-file=no-op כך ש-Render לא מושפע) + `main.py` טוען `.env` **לפני** כל import של `backend.v9` (לפני ש-`atr.py` קורא את הדגלים). `.env` (gitignored) הושלם ב-`S2_VSA_VOLUME=1`+`S3_MUTE=1` = מקור-יחיד לכל דרכי-האתחול. **verified by (raw):** `pytest test_env_loader_flags.py` → `5 passed` (כולל אימות ש-.env האמיתי מדליק את 5 הדגלים). ⚠️ דורש restart כדי להיכנס לתוקף; עדיין לאמת חי ב-RTH שני שהדגלים אכן ON + לשלול את I-21 כשורש-משני ל-0-עסקאות.
- **[2026-06-07 AM] 🧹 שני פריטי-בורד התבררו stale (Cowork, אומת):** (1) `test_bear_flag_skipped_on_first_hour_mode` **ירוק** (עבר ב-isolation + בקובץ; הערת ה"נכשל" התיישנה). (2) **S1 trigger#1 (move_30) = dead code:** `_check_reeval`/`check_reeval_triggers` **לא נקראים מאף מקום** (grep: 0 call-sites) — הוחלפו ב-**continuous re-eval**: C1+C3 תמיד חוזרים ל-B2 כל בר (גם כשנעול, `state_machine.py:713-722,768-770`), כך שמהלך-קיצון נתפס ב-B2 של הבר הבא. תיקון ה-deque ל-`_check_reeval` היה **inert** (תיקון-קוד-מת, P27.5-class). פעולה: לתעד; הסרת `_check_reeval`+`check_reeval_triggers` כ-cleanup לפני LIVE (לא שינוי-התנהגות), לא דחוף.
- **[2026-06-07 AM] 🔬 I-20/C-6 אובחן לעומק (Cowork, read-only — לא תוקן בכוונה):** המסכה היא `bridge_inspector.py:99-102` (`age<0 → status=FRESH, age_display=0.0`) אבל היא **load-bearing**: השורש האמיתי הוא `bridge_inspector._parse_ts:40-75` שמחיל **America/New_York** על ts נאיבי **ומטפל שגוי ב-`+00:00`** (ה-literal-in-format משאיר `tzinfo=None` → גם UTC-מפורש מקבל ET) → כל בר *עדכני* נראה ~4ש' בעתיד, והמסכה "מצילה" אותו. **ראיה חיה (now=11:02:08Z):** `volume_profile` (stream **קריטי**) age אמיתי 4.6s (row_helpers) אבל `_check_stream` מחזיר `live:"0s"` = ענף-המסכה → אם מסירים את המסכה עיוור, volume_profile הופך not-present → **`bridge_streams_fresh` חוסם את הלוח ב-RTH (רגרסיה)**. `footprint` (לא-קריטי) ts=13:27 IL-as-UTC = ~35דק' stale אמיתי, מוצג FRESH 0s = נזק-C-6 האמיתי. **שורש מערכתי:** קונבנציות-ts לא-עקביות פר-stream (footprint=IL-as-UTC · volume_profile=UTC · v9_bars_5min=ET-naive) → חוק-parser אחד לא משרת את שלושתם. **מסקנה:** תיקון דורש דגימת ts גולמי פר-טבלה ב-RTH ואז תיקון `_parse_ts` פר-קונבנציה + הסרת המסכה + טסט. **לא לתקן עיוור** (P27.5-class). נשאר OPEN עם פתרון מוצע.
- **[2026-06-07 AM] ✅ אימות-T3 end-to-end בלי Sierra/RTH (Cowork) — commit `56a6a9c`:** טסט-אינטגרציה `test_t3_monitor_integration.py` מזרים setup-Trend (T3 קבוע) ו-setup-trail (None) דרך `build_s2_gateway_setup` האמיתי → trade → ה-`ActiveTradeMonitor` האמיתי (monitor.py:104). מוכיח: Trend=T3 מנוהל כיעד-חי · trail=0 יעדי-פנטום · ליטמוס: t3=0.0 מחזיר את הפנטום. **verified by (raw):** `pytest test_t3_monitor_integration.py` → `4 passed`. סוגר את פער-האימות-החי בלי לחכות ל-RTH של שני (אימות-Sierra-חי עדיין רצוי ביום-Trend אמיתי, אך לא חוסם).
- **[2026-06-07 AM] ✅ תיקון-T3 (I-22+I-23) נכנס ל-git (Cowork) — 2 commits:** `4d79a2d` fix(T3) backend (4 קבצים + טסט-regression) · `0be56ab` feat(trades) frontend (T3 display + השלמת רכיבי Trades-Phase1 שכבר יובאו ע"י HEAD: `TradeCardList`/`TradePathVisual` — HEAD היה לא-בונה בלעדיהם). **verified by (raw, Rule 5):** `pytest test_s2_gateway_t3_passthrough.py` → `3 passed`; `node --test tradeMath.test.ts` → `pass 6 / fail 0`; `tsc --noEmit` → רק 2 שגיאות pre-existing (PriceDebugConsole.tsx, api.ts), **0 שגיאות module-resolution** = גרף-Trades בונה שוב. **נותר 🔴 מיידי:** restart SHADOW כדי שה-`None` ייכנס לתוקף + אישור-LIVE (B5) אחרי soak.
- **[2026-06-05 eve] ✅ I-22 + I-23 תוקנו מהשורש (Cowork — אישור Michael "ללא פלסתרים"; committed 2026-06-07 `4d79a2d`+`0be56ab`):**
  - **שורש שהתגלה (מעבר לתצוגה):** אחסון `t3=0.0` במקום `None` גרם ל-`active_trade_manager/monitor.py:104` (`if trade.t3 is not None`) לטפל ב-T3 לא-קיים כיעד-פנטום (בלתי-ניתן-להשגה) על רגל C3. התיקון הנכון = `None` end-to-end.
  - **Backend:** S2 `five_min_system.py` — הדיקט-inline חולץ ל-`build_s2_gateway_setup(t1_setup, info)` (testable) שמעביר `t1_setup.t3_price` (None ל-trail/no-T3, מחיר אמיתי ל-TN/TDD). S4 `woodies_system.py:504` + S3 `footprint_system.py:565`: `0.0`→`None`. API `trades.py` חושף `t3_label`/`trail_after_t2` מ-`quality`.
  - **Frontend:** `tradeMath.ts` `rLevels` הוסיף `t3R` + guard `lvl<=0→null`. `SelectedTradePanel` מציג price·R פר-יעד + שורת T3 ("trail"/price/—). `TradeDetailsModal/PriceTimeAxis` guard `t3>0` (מונע ש-0.0 ישבור את סקאלת-המחיר).
  - **טסט אנטי-טאוטולוגי:** `tests/v9/regression/test_s2_gateway_t3_passthrough.py` קורא ל-`build_s2_gateway_setup` האמיתי. ליטמוס: revert ל-`"t3":0.0`→`test_fixed_t3_passes_through` RED.
  - **verified by (raw):** sandbox `build_s2_gateway_setup(mk(7392.0))['t3']==7392.0`, `mk(None)['t3'] is None`. tsc: 0 שגיאות חדשות (רק 2 pre-existing: PriceDebugConsole/api.ts). UI חי (Chrome): פאנל #13 מציג `T1 7410.50·+1.0R · T2 7404.88·+2.5R · T3 —` (תאם spec Variation 1R/2.5R). console נקי.
  - **⚠️ LIVE-gate (B5):** שינוי `0.0→None` ל-T3 משנה את ניהול C3 בימי-Trend (יעד-קבוע מול trail). אומת ב-SHADOW; LIVE דורש אישור Michael אחרי soak. **Backend דורש restart כדי להיכנס לתוקף** (עסקאות קיימות נשארות t3=0.0; ה-frontend מטפל ב-0.0 כ-"—").
  - **OPEN החלטה:** ב-Variation T3=trail (אפיון) — נשאר trail אלא אם Michael ירצה T3 קבוע (שינוי-אפיון).

### (היסטוריה — איך התגלה)

- **[2026-06-05 eve] 🟡 I-23 חדש — עמוד Trades לא מציג מחירי-מכירה T1/T2/T3:** finding=`SelectedTradePanel.tsx:94` מציג שורת "T1 · T2" כ-R-multiples בלבד (`rLevels()` ב-`tradeMath.ts:40-54` ממיר את מחירי `t.t1/t.t2` ל-R), מחירי המכירה עצמם לא מרונדרים, ו-T3 חסר לגמרי (אין `t3R` ב-`rLevels`). הנתונים קיימים ב-API. proposed=fix-frontend (hot-reload): להציג מחיר לצד R + שורת T3 שמראה "trail" כשאין מחיר קבוע. verified by: raw `/trades/recent` → `#12 {stop:7443.5, t1:7440.25, t2:7436.75, t3:0.0}`, `#10 {stop:7457.03, t1:7428.75, t2:7413.5, t3:0.0}` (stop/t1/t2 present, t3=0) מול `SelectedTradePanel.tsx:91-95` (אין רינדור-מחיר ל-T1/T2, אין שורת-T3).
- **[2026-06-05 eve] 🟡 I-22 חדש — S2 T3 מחושב-אך-נזרק (partial wiring):** finding=`five_min_system.py:1083` מחשב `t3_price = _targets.get("t3_price")` אבל `:1108` שולח `"t3": 0.0` קשיח ל-`gateway_setup` → בימים עם T3 קבוע (Trend_Normal=4R · Trend_DD=4R-cap לפי `targets_table.py`) ה-T3 אובד. ב-Variation T3=trail (t3_r=None) → 0 לגיטימי שם. proposed=smallest-fix: להעביר את `t3_price` המחושב במקום `0.0` (exposure-only של ערך שכבר מחושב). verified by: שתי העסקאות Variation t3=0.0 + grep `five_min_system.py:1108 "t3": 0.0`. ⚠️ נוגע ל-trading-logic surface → תיקון + אישור Michael לפני LIVE.
- **החלטה פתוחה ל-Michael:** ב-Variation, האם T3 צריך להישאר "trail" (לפי האפיון `targets_table.py:66`) או להפוך ל-T3 קבוע — זה שינוי-אפיון, לא באג.

## 📍 2026-06-05 (EOD-agent, 09:25 CT) — pattern-EOD מאוחד + 2 חשודים חדשים

> דוחות: `docs/reports/PATTERN_EOD_2026-06-05.md` · `DESIGNS_2026-06-05.md` · register עודכן.

- **[2026-06-05] 🔴 I-9 cron-TZ נפתח-מחדש:** root=ה-EOD-agent נורה ב-**09:25 CT** (54 דק' לתוך RTH) ולא אחרי 15:00 CT → gating-פנימי מוודא RTH אך לא after-close → הדוח כיסה רק שעה-ראשונה (11 ברים), counterfactual נחתך ל-3 ברים. proposed=trigger→23:05 IL **או** guard `now_ct>=15:00` (D-1). verified by: `TZ=America/Chicago date` → `09:25 CDT` בזמן-ריצה + bars5min last ts=`17:20+03` (09:20 CT).
- **[2026-06-05] 🔴 I-11 חדש — S3 footprint 0 ברים:** finding=`running+hydrated` אבל `bars_processed_today=0`, buffer=0, flow=null בשני snapshots (09:12+09:24 CT) → אף תבנית-S3 לא דורכת. proposed=CC לאבחן export→bridge→DB (D-2, diagnose-first). verified by: `/api/v9/footprint/current` raw `bars_processed_today:0` ×2.
- **[2026-06-05] 🟡 I-12 חדש — A5 sizing reject אטום:** finding=`calculate_size=reject` עם `details{}` ריק; הסבר רק ב-`last_reasoning_notes` (`HFE LONG size=reject: CCI=-192.9, trend=RED, group=REVERSAL`); פעל בזמן A4 `context degraded` (day_type missing, I-1). proposed=§1 למלא `details{}` (display/safe) · §2 defer כש-day_type חסר (trading-logic→אישור) (D-4). counterfactual: ה-reject **חסך ≈1R** (HFE LONG מולא 7519.25→stop 7516.75 באותו בר; T1 7522.25 פוספס ב-0.25) → מוצדק. verified by: bars5min replay (17:15/17:20/17:25 IL).
- **[2026-06-05] I-1 אומת-חי:** A4 ב-HFE dtree=`context degraded: day_type/tpo/killzone/layer0 missing` ב-09:24 CT (נשאר 🔴, CC להצליב atr_daily ב-v9_export).
- **חלון:** נדרכה=1 (S4 HFE) · נורתה=0 · trades_today=0. S2 detector חי 0-patterns (לגיטימי) · S3 dark (I-11). **דוח חלקי — להריץ שוב אחרי-סגירה.**
- **[2026-06-05 11:08 CT] 🔴 C-5 חדש (I-19) — `/api/v9/build/pattern-status` נתקע:** finding=3 קריאות עם AbortController 5–6s, כולן הגיעו לתקרת 45s של CDP בלי לחזור (abort לא נורה); כל שאר ה-endpoints ענו <1s. proposed=CC לפרופל את ה-route + לאמת אי-חסימת event-loop (single-worker uvicorn). verified by: 3× CDP timeout על fetch('/api/v9/build/pattern-status') מול תגובות <1s מ-woodies/footprint/five_min/gateway/day_type. **חוסם אימות I-16 בסנאפ-שוט זה.** דוח: `PATTERN_DIAG_2026-06-05.md §11:08`.
- **[2026-06-05 11:08 CT] snapshot — סטטוסים:** I-11 footprint **אישור 6** (0 ברים, buffer 0) · I-15/C-1 trend RED **durable** (3 סנאפ-שוטים) · I-1 day_type=**Variation 0.48/B2 מסווג** (לא UNKNOWN) אך opening_type=UNKNOWN בעוד five_min/UI=OPEN_REJECTION_REVERSE (פער-instance שייר) · B-11 **לא משחזר** (לוח 🟢 LIVE) · S2 DOUBLE_TOP_AA conf=88 **size=reject** (location=far) — אנלוג-S2 ל-I-13 · Y IB `dll_missing` (פער Sierra).
- **[2026-06-05 11:38 CT] 🟡 C-6 חדש (I-20) — bridge `lag_seconds=-10467s` + `fresh=true`:** finding=`systems[0].data_freshness` של `/build/pattern-status` מחזיק `last_bar_ts=null`, `lag_seconds=-10467.4` (~−2.9h שלילי), `fresh=true`, `threshold=90`; lag שלילי ~3h = חתימת TZ-mix (IL UTC+3 מול UTC now, משפחת I-18/C-4, מפר Rule 4) וה-predicate לא אוכף סף על lag שלילי. proposed=CC ל-TZ-normalize את last_bar_ts ל-UTC בגבול + לאכוף `|lag|≤threshold` לפני fresh=true. verified by: raw `{last_bar_ts:null, lag_seconds:-10467.4, fresh:true, threshold_seconds:90}`.
- **[2026-06-05 11:38 CT] 🔴 I-11 escalation — footprint מת חוסם את כל הלוח:** finding=readiness `bridge_streams_fresh`=**passed:false/severity:block/"dead: tick_reversal"** ⇒ board verdict=**BLOCKED**, בעוד ב-10:44 אותו footprint-מת נתן READY. ⇒ I-11 עלה מ"S3 לא דורכת" ל-חסם-לוח. proposed=CC לאבחן מדוע tick_reversal הופך dead-severity (אישור 7 ל-0 ברים). verified by: readiness.checks raw + footprint `bars_processed_today:0`.
- **[2026-06-05 11:38 CT] snapshot — סטטוסים:** S2 **כל 10 armed** (choppiness_ok present=true chop=69 ⇒ **I-16 לא משחזר**; auth=FULL 3/2/2 ⇒ **I-14 auth-block נוקה**) · S4 **כל 9 armed** trend RED **durable snap-4** (I-15/C-1) · C-5 **לא משחזר** (pattern-status 138ms/60ms) · I-1 day_type פיצול-3-כיווני (Variation ב-state/UI/S2 מול readiness="Normal") + `opening_type=UNKNOWN`+`session_min=0` תקוע ⇒ state-instance stale · B-11 לא משחזר (LIVE) · trades_today=0. דוח: `PATTERN_DIAG_2026-06-05.md §11:38`.
- **[2026-06-05 12:14 CT] 🔴 I-21 חדש — stall של יצוא Sierra בערוץ 5-דק'/study (~39 דק'):** root/finding=ערוץ `woodies_5min`/`5min_bars`(min-patterns)/`footprint`/`day_type` תקוע מ-~11:35 CT, בעוד ערוץ tick/price+CVD+volume_profile חי (`fresh <1s`). הלוח אומר במפורש S2 source "**תקוע · lag 39m · last_bar 12:35 PM**" + "יצוא Sierra תקוע". ראיה: engine `cci_14=-126.44` **זהה ל-11:38** (קפוא); כל S2/S4 armed-אך-לא-detecting על בר קפוא; chain BLOCKED. proposed=CC לאבחן Sierra-export→bridge→DB לערוץ 5דק'/study (file mtimes + last-bar ts ב-`~/SierraChart_Data/v9_export/` + /tmp/bridge.err.log). זהו השורש מאחורי I-11+I-15. verified by: raw `woodies.cci_14=-126.44` (=snap 11:38) + board DATA_FRESHNESS `Woodies CCI stale 39m / Min Patterns stale 39m` + global_gates `woodies_5min ts=19:35 IL-as-UTC`.
- **[2026-06-05 12:14 CT] 🟡 I-20/C-6 — נזק מוכח:** המסכה (negative-lag `fresh=true`, `lag_seconds=-8685.6`) מסתירה את ה-stall של I-21 — global_gates מציג `woodies_5min`/`footprint`="FRESH 0s" בעוד אותו payload + הלוח אומרים `stale 39m`. ⇒ C-6 אינו cosmetic; הוא מסתיר חסם-נתונים אמיתי. proposed=TZ-normalize + אכיפת `|lag|≤threshold`.
- **[2026-06-05 12:14 CT] snapshot — סטטוסים:** I-11 **אישור 8** (footprint 0 ברים; tick_reversal DEAD 78דק' חוסם לוח) · I-15/C-1 trend RED **snap-5** אך על בר-קפוא (I-21) · I-16 **לא משחזר** (10 armed, choppiness_ok present) · C-5 **לא משחזר** (pattern-status 477ms) · B-11 לא משחזר (LIVE) · I-1 פיצול-3-כיווני + session_min=0 נמשך · trades_today=0. דוח: `PATTERN_DIAG_2026-06-05.md §12:14`.

## 📍 2026-06-05 — B-13 remediation + G1 columns + clean shadow reset

> 🧭 בּאג-לוג מלא: `docs/reports/BUG_LOG_2026-06-04_05.md`.

**✅ B-13 תוקן (CC, 2026-06-05).** S2 ירה 2× phantom trades (7341/7365) — ברים שאריתיים מ-PG migration May 6, לא ברים פנטומיים.
- **שורש מאומת (CC psql):** entry_price 7341.00 = exact match close של 2026-05-06 16:30+03; 7365.75 = close של 2026-05-06 20:20+03. 8 ברים ישנים (May 6-12) שרדו migration.
- **D2 (root fix) — staleness guard:** `_route_bar` blocks bars with stale ts (>24h) or off-market price (>50pts from latest). Old bars still written to DB for chart, but NOT routed to pattern engines. `MAX_STALE_HOURS=24`, `STALE_PRICE_BAND=50` (Michael approved). 6/6 tests GREEN, RED proven.
- **D3 — session gate 08:30–15:00 CT:** `session_gate.py` canonical firing window. Gateway blocks ALL modes (incl SHADOW) outside window. S2 transitions DAY_TYPE→OVERNIGHT at 15:00 CT. All 3 firing systems (S2/S3/S4) blocked via single choke point. 9/9 tests GREEN, RED proven.
- **D1 — S3_MUTE=1:** added to `start_all.sh`. Footprint observability stays, no firing.
- **D4 (price-sanity in pre_fire):** deferred per Michael.
- **D5 — clean reset:** TRUNCATE v9_trades + v9_bars_5min + _continuous + _woodies + v9_five_min_state. 0 bars below 7450. Soak ≥10min: 0 errors, 0 deadlocks, 0 phantom trades.

**✅ G1 columns (CC, 2026-06-05).** `day_type_at_entry`, `pattern_id_at_entry`, `session_at_entry` — nullable, indexed. Migration 020 applied. Populated at entry from same cross_context snapshot (extract_g1_entry_context). Litmus: missing killzone → NULL (not synthesized). 7/7 tests GREEN. No backfill (trades wiped).

**🔴 פתוחים:** B-11 bridge_inspector rowid (ready) · SQLite-isms scan · Build-cull · S1-POC · chart display (RTH per-session).

**החלטות שהתקבלו בסשן:**
- **Build-Status cull = אופציה A** (אושר Michael) — Build חי ב-`/build` בלבד. פרומפט: `CC_PROMPT_BUILD_STATUS_CULL_2026-06-04.md`. **טרם בוצע.**
- **S1 day-type re-eval = "הדבר האמיתי"** (POC/value-area דינמי). נתיב-נתונים = **Sierra** דרך `/api/v9/tpo/current` (Rule 1: found=false→no-reeval). פרומפט: `CC_PROMPT_S1_POC_REEVAL_2026-06-04.md` (flag-gated default OFF). **טרם בוצע.** סף-נדידה = לכייל מ-soak.
- **D-096 S1=OBSERVER נעול** (אין החלטה פתוחה; firing=פרויקט עתידי). drift נסגר: **S3=firing · Killzone=11**.
- **D-RVX** — knob נשלח (`e72883c`, ברירת-מחדל A_VSA). בחירת-וריאציה → מ-soak.
- **הגדרת סטופים** — נדחתה ע"י Michael. טבלה לעריכה מוכנה: `MEMS26_STOP_TARGET_PLACEMENT_TABLE_2026-06-04.xlsx` (+Drive). חסר: `stop_anchors.yaml` + 2 עוגנים חדשים + loader. ([[project-stop-target-placement-table]])
- **#6 residuals קטנים + #5 post-soak → לפני LIVE** (נדחו).

**✅ commits שאומתו בסשן:** `e41ac5d` S4-ticks · `182862b` config-YAML · `e72883c` S2-variant · `66bd45c` targets_stop · `3820f3b` PG-datetime · `1896a97` continuous-5min · `355a54b` dedup-bars · `a4b1fac`/`5b06899`/`f36e184` index.

**🔴 פתוחים (לפי עדיפות):** B-13 (S2 guardrails+מקור-בר) · **B-11 bridge_inspector `ORDER BY rowid` → `ORDER BY ts`** (פרומפט מוכן בעל-פה; SQLite-ism שובר PG → כל הזרמים no_data/Bridge-OFFLINE שקרי) · **סריקת SQLite-isms** (datetime↔str · rowid · str(ts)-dedup) לפני LIVE · Build-cull · S1-POC · צ'ארט-תצוגה (RTH פר-סשן כמו Sierra chart#5).
**מצב חי:** גשר רץ ודוחף (PID חי, `/tmp/bridge.err.log` push#50 errors≈0). day_type מסווג (PG-fix עבד). S2 10-armed.


- **[2026-06-04] ✅ PG datetime↔str regression fix (CC):** root=PG returns `datetime` for timestamp columns, `DataFreshness.last_bar_ts: Optional[str]` rejected it → `day_type_inspector` crashed → `day_type=None` → S1 unclassified → S2/S4 day-gate fell. fix=central `field_validator(mode="before")` coercion on `DataFreshness.last_bar_ts`, `PatternStatus.last_fire_ts`, `SystemStatus.last_fire_ts`, `Freshness.ts` in `types.py`. Sibling audit: woodies/s2/bridge inspectors safe (`latest_valid_db_ts` already does `str(raw)`, `fires_today` does `.isoformat()`). Verified: 9/9 pytest green + litmus revert→RED (pydantic `ValidationError: Input should be a valid string`).
- **[2026-06-04 eve] ✅ אינדקס-קוד חי (CC `a4b1fac`, אומת Cowork):** `scripts/gen_index.py` + 107 `_INDEX.md` פר-ספרייה + `SYSTEM_INDEX.md`. import-graph (py+ts) מסמן שימוש פר-קובץ; orphans 137→**53** אחרי הקשחה (entrypoints/dynamic/streams/Next.js). verification (Cowork): 107 קבצים נמצאו · litmus `adaptive_stop.py ✅2`/`s2_inspector.py ✅1` (לא-orphan, graph תופס) · idempotent (CC: 0-diff בריצה שנייה). **2 orphans-אמת בולטים לבדיקה:** `services/trail_engine.py` (0 refs — dead או missing-wire?) · `archive/confluence.py`. residual: 53 כוללים false-positives של class-instantiation (דורש AST על constructor-calls). להריץ `python3 scripts/gen_index.py` לרענון.

> 🟡 **OPEN (נגיש להמשך) — הגדרת סטופים פר-תבנית×סוג-יום:** טבלת-עבודה לעריכה ב-`docs/plans/MEMS26_STOP_TARGET_PLACEMENT_TABLE_2026-06-04.xlsx` (+ Drive `1IW5SQytZ6iFGcLSVgeE9tKo7BmEqDyFk`). distances/targets/verdict כבר YAML-tunable; ה-**עוגן** קשיח → דורש `stop_anchors.yaml` + loader + 2 עוגנים חדשים (candle-cluster low, extreme-candle edge). כש-Michael יבקש "להגדיר סטופים" — לפתוח את הטבלה. ([[project-stop-target-placement-table]])

## 📋 2026-06-04 eve — ✅ D-RVX: בורר וריאציית S2 → YAML-tunable (CC `e72883c`, אומת Cowork, litmus revert→RED הוכח)

- **✅ knob נחשף — exposure-only, 0 שינוי-התנהגות בברירת-מחדל (אומת בלתי-תלוי, Cowork code+pytest):** commit `e72883c` (4 קבצים) הופך את שער-הירי של S2 ל-YAML.
  verification (raw): (1) **diff כירורגי** — ב-`five_min_system.py` רק `:513-514` (`b2_drop=_vsa_pass`→selector); `:504-511`(compute)/`:546`/`:570`(fire)/`:516`(legacy) **לא נגעו** (numstat `8/1`). (2) `config_loader.load_s2_firing()` מאמת מול 5 ערכים מותרים, חסר/לא-חוקי→`A_VSA`+warning (No silent failure). (3) הטסט מייבא את **`FiveMinSystem._detect_reactive` האמיתי** (anti-tautological) — בָּרים עם `_rvol_pass=True,_vsa_pass=False`. (4) **6/6 ב-sandbox**. (5) **litmus revert→RED הוכח ע"י Cowork:** כפיית `b2_drop=_vsa_pass` קשיח → `test_variant_b_rvol_fires`+`test_variant_union_fires` **נכשלו** (`None==LONG`); שחזור → 6/6 ירוק. (6) `test_default_a_vsa_zero_change` ירוק = ברירת-מחדל bit-identical.
- **🟢 5 ערכים זמינים בקונפיג** (`config/s2_firing.yaml` `variant:`): `A_VSA`(ברירת-מחדל, 22.1%) · `B_RVOL`(20.9%) · `C_STRICT`(11.0%) · `UNION`(OR) · `INTERSECTION`(AND).
- **⏳ ההכרעה עצמה פתוחה ל-Michael (D-RVX):** איזו וריאציה להדליק — **תיבחר מדאטת ה-soak**. שינוי מ-`A_VSA` = trading-logic → strategic-stop + אישור לפני live. עד אז A_VSA פעילה (= ההתנהגות הקיימת, ללא שינוי).

## 📋 2026-06-04 eve — ✅ BuildTreeView מרנדר TARGETS/STOP חי + הוסר de-trust מיושן (CC `66bd45c`, אומת Cowork)

- **✅ רינדור + ניקוי אומתו בלתי-תלוי (Cowork, code+tsc):** commit `66bd45c` (frontend-only, 1 קובץ) סוגר את ה-staleness של P0-2.
  verification (raw): (1) `TargetsStopLive` (`:605`) קורא `components[stage=="targets_stop"]` מהתגובה החיה, מציג stop/r_t1/targets/sizing/matrix, וחסר/`null`→`⧗ ממתין` — **0 סינתזה** (אין חישוב-מחיר ב-frontend; Rule 1 נשמר). (2) משובץ ב-§6 עם guard `isFiring` בלבד (`:799-801`). (3) **de-trust הוסר:** 0 קריאות חיות ל-`isProxyGate` (נמחק); ⧗-branch ב-ComponentTable/global_gates הוחלף ב-✓/✕ אמיתי; title "⧗ ממתין ל-backend (P0-2)" ירד. (4) **tsc שוחזר ע"י Cowork** (`node_modules` קיים): **0 שגיאות ב-BuildTreeView**; 2 pre-existing בלבד (`PriceDebugConsole.tsx:90`, `api.ts:47`) לא-קשורות.
- **✅ סתירת-framing מהסשן נסגרה:** BuildTreeView היה **untracked** עד כה (ה-numstat `1362/0` = commit ראשון). כעת committed → מימוש ה-Build-Status redesign מגובה ב-git.
- **🟡 3 residuals (לא-חוסמי-SHADOW):** (1) CC NOT-DONE#1 — **price-scale ויזואלי** (entry→stop→T1-T3 כפס) נדחה (דורש כל השדות present בו-זמנית → מבחן RTH). (2) CC NOT-DONE#2 — **אין render-test אנטי-טאוטולוגי** (אין jest/testing-library מוגדר); לוגיקת ה-render אומתה ע"י Cowork בקריאת-קוד אך **לא מוגנת בטסט**. (3) **ממצא Cowork — staleness ב-`:1176`:** הערת טבלאות-האפיון עדיין אומרת שהקרנת-$ "⧗ ממתין ל-backend · ה-1R החי חייב להגיע מ-inspector" — אבל ה-1R **כבר הגיע** (P0-2) ו-TargetsStopLive מציג אותו. טקסט מטעה (קוסמטי) → לנסח מחדש: 1R זמין; ה-overlay על הטבלאות הסטטיות הוא enhancement דחוי (#1).

## 📋 2026-06-04 eve — ✅ S4 ticks חוּוטו ל-YAML (CC `e41ac5d`, אומת Cowork) — wiring אמיתי, טסט-litmus חלש

- **✅ wiring אמיתי — אומת בלתי-תלוי (Cowork, reload-proof):** commit `e41ac5d` יצר `woodies/patterns/_pattern_ticks.py` (helper מרכזי, cache + `_DEFAULTS` fallback) ו-9 ה-detectors קוראים ממנו. **0 drift + wiring חי הוכחו ע"י Cowork:**
  - (A) bind ברירת-מחדל: כל 9 ה-detectors → `STOP_TICKS/TARGET1/2_TICKS` == ערכי-המקור המקוריים (raw: `drift: NONE`).
  - (B) **litmus אמיתי ש-Cowork הריץ** (מה שהטסט היה צריך לעשות): override YAML `ZLR stop=9` → `reset_cache()` → `importlib.reload(zlr)` → `zlr.STOP_TICKS == 9` (ושוחזר ל-8). **המנוע באמת קורא מה-YAML.** `_T1_TICKS=4` לא נגוע.
  - pytest `test_config_yaml_roundtrip.py` = **8/8**; regression 33/33 (CC raw).
- **🟡 residual (B1 anti-tautological) — `test_s4_detector_reads_from_yaml` מטרתו שגויה:** ה-docstring טוען "verifies the detector's STOP_TICKS == 9", אבל הקוד עושה assert על ה-**helper** (`_pattern_ticks.get_ticks("ZLR")==9`) בלבד — **לא** מייבא/reload את `zlr` ולא בודק `zlr.STOP_TICKS`. תוצאה: אם יחזירו (revert) את החיווט בתוך detector לקבוע קשיח — **הטסט עדיין ירוק** → נכשל ב-litmus `revert→RED` ברמת ה-detector. (`test_s4_ticks_yaml_matches_detector_constants` כן קורא `mod.STOP_TICKS` ל-9/9, אבל מכיוון ש-YAML==defaults הוא תופס drift, לא היעדר-wiring.) **✅ תוקן ע"י Cowork (working-tree, טרם committed):** ב-litmus נוסף `importlib.reload(zlr)` + `assert zlr.STOP_TICKS == 9` (+guard `_T1_TICKS==4`) + cleanup-reload ב-finally + docstring עודכן. **revert→RED הוכח (raw):** סימולציה של החזרת `STOP_TICKS=8` קשיח ב-zlr → הטסט **נכשל** (`assert 8 == 9`); לאחר שחזור → 8/8 ירוק. כעת הטסט מגן על החיווט ברמת ה-detector, לא רק ה-helper. (CC/Michael ל-commit.)
- **סטטוס config-tunable:** S2-stop + auth + targets + min_r_t1 + **S4-ticks** = כעת YAML-authoritative. נותר ל-[[project-config-tunable-stop-exits-contracts]]: לוודא ש**contracts-count** מניע sizing בפועל + exits מלאים + reload-endpoint (NOT-DONE#2) + איחוד `build_status/auth_table_lookup.py` הכפול (NOT-DONE#4).

## 📋 2026-06-04 eve — ✅ config→YAML round-trip הוצלב (CC `182862b`, אומת Cowork בלתי-תלוי)

- **✅ Round-trip equality אומת — 0 שינוי-ערכים (Cowork, code+pytest):** commit `182862b` (HEAD) externalize auth/targets/stop ל-`config/*.yaml` עם fallback ל-const קשיחים.
  verification (raw): (1) `git diff 8eb5747 182862b` על `auth_table_v1.py`/`targets_table.py` — ה-const-dicts הקשיחים `_AUTH_TABLE_V1`/`_TARGETS` **לא שונו** (רק נוספו loader + `AUTH_TABLE`/`TARGETS` = YAML-או-fallback). (2) deep-equal עצמאי: `load_auth_matrix()` vs `_AUTH_TABLE_V1` = **70/70 cells, 0 mismatch, 0 yaml-extra**; `load_targets()` vs `_TARGETS` = **7/7 day_types, 0 mismatch**. (3) S2 stop ידני מול מקור: `MES_TICK=0.25·FLOOR_TICKS=4·backstop=4·_FLOOR_ATR_K=1.75·ATR_MULTIPLIERS{Reactive1.0/OFA1.5/Flag1.5/Double_BT2.0/HnS2.0}` = זהים ל-YAML. (4) S4: **כל 9 התבניות** (ZLR 8/12/24·TLB 10/15/30·TT 8/12/20·GB100 8/12/24·VEGAS 12/16/32·GHOST 12/16/32·FAMIR 10/14/28·HTLB 10/14/28·HFE 8/12/24) זהות מול קבועי ה-detectors. (5) pytest `test_config_yaml_roundtrip.py` = **6/6** ב-sandbox.
- **🟡 wiring — מה באמת YAML-authoritative מול mirror-בלבד (ממצא Cowork):**
  - **חי (YAML מוביל):** S2 `adaptive_stop` (`_try_load_yaml_stop()` נקרא ב-:58) · `auth_table_v1.AUTH_TABLE` · `targets_table.TARGETS` · `pattern_dispatcher min_r_t1_threshold` (:55-63). עריכת ה-YAML **כן** משנה התנהגות.
  - **❗ אינרטי (mirror-בלבד) — S4 per-pattern ticks:** אף קובץ ב-`woodies/patterns/` לא מייבא `config_loader` (אומת: 0 hits). 9 ה-detectors עדיין קוראים `STOP_TICKS`/`TARGET1/2_TICKS` הקשיחים שלהם. **משמעות:** עריכת `config/stop_params.yaml`→`s4_patterns` **לא תשנה כלום** ב-S4 עד שחיווט 9 הקבצים (NOT-DONE#1). זה הפער מול [[project-config-tunable-stop-exits-contracts]] — stop/exits של S4 **טרם** ניתנים-לכיול-ללא-קוד.
- **🟡 residual (test-hardening):** `test_stop_params_roundtrip` משווה S4 מול **ליטרלים בטסט** (רק 3/9: ZLR/TLB/VEGAS), לא מול קבועי-המקור. כל drift עתידי ב-YAML-S4 (האינרטי) יעבור ירוק בלי להיתפס. תיקון מוצע: לחזק את הטסט להשוות מול קבועי 9 ה-detectors בפועל (ואז לחווט אותם → YAML authoritative). אומת Cowork שהיום 0 drift, אבל ההגנה חלשה.

## 📋 2026-06-04 eve — ✅ הצלבת 2 תוצרי המעצבים (Trades + Build-Status) מול source-of-truth (Cowork, code+git)

- **✅ Trades redesign — עבר הצלבה (Rule 1 נקי), אומת מול קוד:** `TRADES_PAGE_REDESIGN_2026-06-03.md` לא מסנתז שום שדה.
  verification (raw): כל השדות הנשענים = עמודות אמיתיות ב-`db/models/trades.py` (`stop,t1,t2,t3,t1-t3_hit_ts,exit_reason,pnl_usd/r,outcome,firing_system`); `killzone`/`day_type` **אינם** עמודות → מסומנים נכון ⛔ "ממתין ל-backend". D-A `tradeStore.ts:57 mode:'ALL'` ✅ (תוקן כפי שנטען); באג-תאריך לקסיקלי D-D `tradeStore.ts:114-118` `entry_ts.slice(0,10)` השוואת-מחרוזת `<`/`>` ✅ פתוח כמתואר; `api/v9/trades.py` routes = exit/active/POST/GET/recent/{id}/log → **אין endpoint אגרגציה** → gap-list G2-G4/G7 אכן נדרשים.
  **verify-item (לא-חוסם):** G5 "`v9_trade_management_log` לעולם לא נכתב" — קיימת התייחסות ב-`services/trade_manager/manager.py`; לאמת אם זה כותב-שבור לפני סיווג כ-gap קשיח.
- **✅ Build-Status redesign — עבר הצלבה (Rule 1 נקי) + cull מאומת בטוח:** field-schema מסונכרן verbatim בין CC_PROMPT_P0_2 ↔ gap-list P0-2 ↔ `BuildTreeView.tsx:578`.
  **cull מאומת (raw — נמנע מ-grep-false-positive בכוונה):** `BuildStatusTab` מותקן **רק** ב-`V9Dashboard.tsx:138` (else-branch); `/build`=`app/build/page.tsx`→`<BuildTreeView/>`; 6 קבצי-DELETE (BuildStatusTab/SystemSection/PatternRow/ComponentTable/StatusPill/ReadinessHeader) reachable רק דרך BuildStatusTab; `BuildTreeView` **מממש inline** `ComponentTable`(:359)/`PatternRow`(:415) ומייבא רק `types.ts` (KEEP) → **cull בטוח**. ההמלצה תקפה, עדיין ממתינה go של Michael.
- **🟡 ממצא-מפתח (staleness — דורש re-mark):** שני המסמכים (08:37) קודמים ל-P0-2 (`8eb5747`, 11:44 commit). הם מסמנים TARGETS/STOP/r_t1 כ-`⧗ ממתין ל-backend`, אבל ה-backend **כבר פולט** זאת — אומת: `s2_inspector.py:317-426` (preview דרך `compute_stop`+`compute_targets_for_day_type`, `r_t1_gate`) + `woodies_inspector.py:329-364` (`r_t1` מ-`PatternResult`). הפער שנותר = **frontend-render בלבד** (`BuildTreeView.tsx:386` עדיין ⧗ proxy; residual §5 "frontend טרם מרנדר stage targets_stop"). solution: למרק מחדש gap-list P0-2 + spec §4/§6 → **backend=DONE (`8eb5747`), frontend-render=OPEN**.
- **🟡 סתירת-framing להכרעת Michael:** ה-handoff §1 מתאר את שני המעצבים כ-"read-only, לא מימוש", אך Build-Status **מומש בפועל** כקוד-frontend (`build_tree/BuildTreeView.tsx`, mounted `/build`, **untracked** = טרם committed — `git ls-files build_tree/` ריק). Trades אכן design-only. לא-חוסם, ראוי-ידיעה.

## 📋 2026-06-04 (P0-2) — חשיפת TARGETS/STOP→r_t1 ל-build-status (CC `8eb5747`, אומת Cowork)

- **✅ P0-2 בוצע ואומת בלתי-תלוי (Cowork, code+git) — exposure-only:** commit `8eb5747` = רק `s2_inspector.py`+`woodies_inspector.py` (+119/+100), **0 שינוי מנוע/risk**.
  s2_inspector **משתמש-מחדש** ב-`compute_stop`+`compute_targets_for_day_type` (לא reimplement/synth). פרוקסי `confidence≥0.5` → `r_t1≥1.0` (סף pre_fire); חסר → "awaiting backend". S4 prospective כבר ב-`PatternResult`; S2 קיבל preview read-only (היה fire-time בלבד). + Day-Type Matrix verdict ל-S4.
  verification (Cowork): `git show --stat 8eb5747` 2 קבצים; `compute_stop`/`compute_targets` מיובאים ונקראים (s2_inspector:346/354); woodies_inspector `_min_r_t1=1.0`.
  **3 residuals (אומתו, NOT-DONE):** (1) **consistency חי טרם אומת** — displayed stop/r_t1 == עסקה שנורתה (תלוי-RTH; נוסף לצ'ק-ליסט bring-up). (2) **תבניות-chart S2** (Flag/H&S/Double-BT) משתמשות ב-pattern-measure בזמן-ירי, ה-preview מציג R-based → תצוגה≠מנוע לאותן תבניות (תיקון: למשוך pattern_measure). (3) **`pattern_dispatcher.py:47 min_r_t1_threshold=0.0`** no-op (pre_fire R:R≥1.0 הוא הגייט הקובע) → dead-threshold לחווט/להוציא ל-config (מתחבר ל-[[project-config-tunable-stop-exits-contracts]]).

> 🧭 **המשך-צ'אט מתחיל כאן:** `docs/handoff/HANDOFF_NEXT_CHAT_2026-06-04_LATE.md`. מצב: DB+firing+watchdog+P0-2(backend+frontend)+config→YAML(auth/targets/stop/S4-ticks/S2-knob)+הצלבת 2 המעצבים — **הכל אומת**. **הצעד המיידי = P1 bring-up ב-RTH** (הגייט לפתיחת SHADOW; אימות ירי-S2 חי + P0-2 consistency). החלטות מאושרות (אומת מול docs/decisions): D-RVX✅ · cull✅(אופ' A `/build`) · S3=Firing✅(D-089) · Killzone=Observer-no-change(D-093). **פתוח באמת: stop-anchor בלבד** (+ post-soak תלוי-דאטה).

## 📋 2026-06-04 — אבחון S1/S2 firing (rerun על PG, אומת Cowork)

- **✅ אבחון S1/S2 מחדש על PG (CC) — אומת בלתי-תלוי (Cowork, code).** (ריצה ראשונה רצה על SQLite + טעתה לגבי S2 → נדחתה; ריצה זו על PG, ספירות טריות.)
  **S1:** אין עמודת `atr` ב-`v9_bars_5min` (אומת) → `_check_reeval:784` `atr=bar.atr`=None → re-eval trigger#1+#3 **מתים**; אבל סיווג **חי** דרך `_last_atr_daily` (rolling ranges, `state_machine.py:257,320-324`).
  **תיקון מינימלי שאומת ע"י Cowork:** `atr = bar.atr or self._last_atr_daily` ב-:784 → מחייה triggers בלי schema/Sierra/bridge. signal-leak אומת: `wrappers.py:91` מחזיר `Signal(system_id=1)` ב-LOCKED_LOW_CONF למרות S1=OBSERVER → **החלטת D-090**. lock_state ב-PG: LOCKED_LOW_CONF=22/PENDING=1, LOCKED(high-conf)=0 (conf max 0.68<0.85).
  **S2:** הדגל `S2_VSA_VOLUME` **כבוי** → legacy gate (90% drop) פעיל = **0.5% pass** → S2 de-facto מושתק (0 fires/setups/signals ב-PG). 3 וריאציות קיימות ונמדדו על 417 חלונות PG: **A_VSA 22.1% · B_RVOL 20.9% · C_STRICT 11.0% · legacy 0.5%** → **החלטת D-RVX** (להדליק + איזו וריאציה).
  verification (Cowork): `_last_atr_daily`+`_check_reeval:784` (code) · `wrappers.py:91` Signal · המקור PG (information_schema, ספירות טריות). pass-rates = CC raw על ברי-PG (לא ניתן לחישוב-מחדש מ-sandbox).
  **החלטות פתוחות ל-Michael:** D-090 (S1 observer/firing) · one-liner re-eval · D-RVX (S2 variant). אלה תנאי-firing ל-SHADOW משמעותי (לא-DB).
- **✅ 3 תיקוני-firing בוצעו (CC `9cac12f`/`d785b2c`/`5343755`) ואומתו בלתי-תלוי (Cowork, code+git):**
  S1 (`9cac12f`): fallback `_last_atr_daily` בכל 4 אתרי `bar.atr` (427/590/619/786 — **חיווט מלא**) · D-090 (`d785b2c`): `return None` ב-`wrappers.py` (S1 observer נאכף, classification ממשיך, Signal נחסם) ·
  S2 (`5343755`): `export S2_VSA_VOLUME=1` (start_all.sh + plist), gate=VSA, תיקון import שבור (היה 0 setups), persist `variant_tag`/`variants_passed` (943-958, + ALTER ב-PG).
  verification (Cowork): grep 4 אתרי bar.atr עם fallback · `wrappers.py` return None · `start_all.sh:21` export · persist wired. CC: 53/53 + 13/13 + 6/6 tests.
  **2 הסתייגויות (אומתו, NOT-DONE):** (1) trigger#1 (extreme move) **עדיין חלקי** — `move_30=None` קשיח (`:783`, צריך bar-history window); ה-fallback החייה trigger#3 + סיווגי-ATR בלבד. (2) S2 0 fires ב-PG — **ירי-חי טרם הוכח**; מבחן-אמת = RTH הבא.
  **3 תנאי-ה-firing שאינם-DB סגורים** (עם ההסתייגויות). נותר ל-P1: bring-up שירותים+feed ב-RTH + אימות ירי-S2 ב-RTH הבא.
- **✅ חוב-תיעוד נסגר (CC):** `docs/decisions/D-096_S1_OBSERVER_ENFORCED.md` — מתעד את ההחלטה שמומשה ב-`d785b2c` (S1=OBSERVER, `return None` ב-`wrappers.py:88`, classification נשמר, הוראות reversibility). Reference שגויה ל-D-090 תוקנה → D-096 (D-090 תפוס ל-Path A Canonical).
- **⚠️ OPEN — S1 re-eval trigger#1 (extreme move >3×ATR) חלקי:** `state_machine.py:783` `move_30 = None` hardcoded → trigger#1 לעולם לא יורה גם אחרי תיקון ה-ATR fallback (`9cac12f`). root=`_check_reeval` לא מחזיק bar-history window ולכן לא יכול לחשב move-in-30-min. פתרון מוצע: הוסף `_recent_closes: deque(maxlen=6)` ל-state machine (6 ברי 5-דק' = 30 דק'), חשב `move_30 = abs(bar.close - _recent_closes[0])` ב-`_check_reeval`. **לא לתקן עכשיו** — trigger#2 (failed extension) ו-trigger#3 (range exceeded) **חיים** אחרי `9cac12f`; trigger#1 הוא edge-case (FOMC/NFP-scale moves). **לפני LIVE.**

## 📋 2026-06-04 — 🔴 split-brain: כתיבות עם db_path → SQLite לא PG (Cowork, מבטל SHADOW GO)

- **✅ ציר 4 + 6b תוקנו (CC `d635b1c`/`20f9df7`) ואומת (Cowork, git+code):** axis4 `_is_within_rth_iso` ב-history_loader → `MAX(vol) WHERE is_synthetic=0 = 83,033` (היה 840,016); axis6b woodies ts unix→ISO + `zlr_detected` 0 + **הסרת `db_path`** → woodies נשמר ל-PG.
- **🔴 ממצא רחב שאומת (Cowork, code-level) — split-brain כתיבה/קריאה:** `safe_writer._get_engine(db_path)` יוצר **SQLite engine לכל `db_path` לא-None**. מחלקות שמאתחלות `self.db_path` לנתיב-SQLite ומעבירות אותו כותבות ל-**SQLite, לא PG**:
  `trading_gateway.py:426,442` (עסקאות) · `tpo_system.py:449,479,556,564` + `tpo_history_snapshotter:286` · `reversal_handler:91` · `footprint_system:326,340,523` · `session_boundary/manager.py:60,83,175,180,193,199,206` (`v9_day_type_state`/S1).
  finding=קריאות מ-PG אך כתיבות S1/S3/S4/TPO/gateway ל-SQLite → נתונים נעלמים מ-PG בשקט. ה-soak לא תפס (SQLite קיבל→"0 errors"); audit קרא מ-PG. הטענה ש-session_boundary "works via engine fallback" הופרכה.
  verification (raw): `_get_engine` `return create_engine(f"sqlite:///{db_path}")`; `grep db_path=self.db_path` → 7 מודולים; ברירות-מחדל = נתיבי-SQLite.
  fix/solution = `CC_PROMPT_FIX_DBPATH_SPLITBRAIN_2026-06-04.md`: להסיר `db_path` מכל כותבי-הפרודקשן + להקשיח `_get_engine` (PG → התעלם מ-db_path + warning) + lint-guard + אימות פר-מערכת ש-COUNT עולה **ב-PG**.
  **❌ SHADOW חסום** עד שכל הכתיבות מאומתות ל-PG (לא רק 4+6b).
- **✅ split-brain נסגר (CC `69744bb`) ואומת בלתי-תלוי (Cowork, code+git) → DB-side GO:**
  verification (Cowork, raw): `git show --stat 69744bb` = 7 קבצים (19 קריאות safe_execute, הסרת db_path);
  `grep db_path=self.db_path` בפרודקשן = **0**; `_get_engine` מקשיח — `if _is_postgres(engine): logger.warning(...); return engine`
  (מתעלם מ-db_path על PG); `bridge_inspector.inspect` קורא דרך `read_one` (PG), ה-db_path שריד לא-בשימוש.
  CC raw פר-מערכת: TPO 0→1, day_type_state 22→23, reversal 0→1, tpo_history 0→1, **SQLite mtime לא זז**; 488 passed (3 pre-existing woodies).
  **ממצא Cowork = כל מחלקת ה-DB סגורה ומאומתת: reads+writes על PG, constraints, tests, axis4/6b, split-brain.** נותרו תנאי-מקדים שאינם-DB (ראה למטה).
  **תנאים שאינם-DB לפתיחת SHADOW משמעותי:** (a) שירותים על PG ב-RTH + feed זורם (frozen-tail watch) · (b) flags ON · (c) S2 יורה (D-RVX variant=Michael) · (d) S1 day-type inputs (bar.atr). S3=MUTE✓ S4=יורה✓.

## 📋 2026-06-04 — ✅ עיצוב-מחדש עמוד Trades לכיול (Cowork, read-only design-research)

- **[2026-06-04] Trades redesign — scope הוכרע (Michael):** decision = **Frontend‑שלב‑1 עכשיו + G1 במקביל**.
  finding = "מלא כמו prototype" אי‑אפשר ב‑frontend לבד (killzone‑at‑entry לא נשמר → צריך G1; אגרגציה
  client‑side רק ≤500 שורות → סיכון Cardinality). solution = שלב‑1 frontend ללא נגיעה ב‑DB/risk/polling
  + G1 (write‑at‑entry — לא סובל דחייה, אחרת היסטוריה מאבדת killzone/day_type לתמיד). **בעלות (אנטי‑כפילות):**
  Frontend‑1=סוכן‑Frontend (ADAPT מ‑`PatternPerformanceStrip.tsx`, לא רכיב חדש) · G1=CC · **G2–G7=DEFERRED,
  ⛔ לא לבנות עד ש‑G1+Frontend‑1 ינחתו.** **חוזה‑ממשק G1** (נקודת‑חיבור מוסכמת מראש → אפס rework):
  עמודות `day_type_at_entry`/`pattern_id_at_entry`/`session_at_entry`; מקור שותק→NULL; frontend מרנדר
  "missing — pending G1" ב‑runtime (Rule 1) + ציר killzone אפור מנוטרל עד G1. מקור‑מלא + טבלת‑בעלות:
  `docs/handoff/HANDOFF_TRADES_PAGE_REDESIGN_NEXT_2026-06-04.md` §5/§5a/§5b. ההכרעה תיעוד‑בלבד, **טרם מומש קוד.**
- **[2026-06-04] G1 prompt נכתב + תיקון‑דיוק (Cowork, code‑verified, Rule 2):** הטענה "killzone‑at‑entry
  לא נשמר" **הופרכה** — `trading_gateway._capture_cross_context()` (`:399‑410`) מצלם את כל 6 המערכות
  (כולל `killzone_system`) ל‑`cross_context` JSON בכניסה ושומר ב‑INSERT (`:414`); `trade_context.py`
  חולץ משם ב‑runtime → קבור ב‑JSON, לא queryable. ⇒ G1 = **promote JSON→עמודה אינדקסבילית**, ברובו
  **backfillable** (לא write‑at‑entry "נאבד לתמיד" כפי שנטען קודם). פרומפט עם **verify‑first** (לאמת מול PG
  מה מאוכלס ב‑cross_context לפני הוספת עמודות) + seam‑map + טסטים anti‑tautological:
  `docs/handoff/CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md`. verification (raw, Cowork):
  `trades.py:53‑54` cross_context JSON · `trading_gateway.py:399‑410` snapshot כל 6 · `:414‑426` INSERT ·
  `trade_context.py:38‑45` registry keys (killzone→killzone_system). טרם מומש קוד.
- **[2026-06-04] ערכת‑מימוש מסודרת נוצרה (Cowork):** מסמך‑אב `docs/handoff/TRADES_REDESIGN_KIT_2026-06-04.md`
  (START HERE — החלטה/סדר/בעלות/חוזה/invariants + קישור לכל הקבצים) + פרומפט Frontend שלב‑1
  `docs/handoff/CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md` (8 פריטים מסודרים, ADAPT מ‑
  `PatternPerformanceStrip`, ET‑date fix `tradeStore.ts:114‑118`, ציר killzone/day_type gated "pending G1").
  G1+Frontend רצים במקביל דרך חוזה §5b. verification (raw, Cowork): `tradeStore.ts:114‑118` slice(0,10) לקסיקלי
  (אומת באג TZ) · `TradesView.tsx:16` fetchTrades() ללא args · `PatternPerformanceStrip.tsx:30,43` patternKey/aggregateByPattern.
- **[2026-06-04] Trades redesign (design-only, לא מומש):** root finding = כל חתכי-הכיול
  שהטריידר ביקש (pattern/day_type/killzone/confluence) **נגזרים מ-JSON ב-runtime**
  (`trade_context.py`) או לא קיימים → אי-אפשר GROUP_BY ב-SQL; ובנוסף כל האגרגציה
  (WR/Exp/equity) מחושבת **צד-לקוח מעל 500 שורות בלבד** (`fetchTrades()` default, ללא mode)
  → סיכון Cardinality כמו P27.5a. תוצרים: `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md`
  (מסמך+gap-list) · `TRADES_PAGE_REDESIGN_MOCKUP_2026-06-03.html` (mockup סטטי) ·
  **`TRADES_PAGE_PROTOTYPE_2026-06-03.html` (prototype אינטראקטיבי, tokens אמיתיים מ-globals.css,
  אגרגציה client-side חיה, drill-down + ציר price/time מדויק — אומת: render ללא שגיאות, BE/Scratch מאוכלסים,
  השוואת exec-mode הכל מול ירי-אחד 68%→75% win)**. תוספות שביקש Michael שולבו: date-presets (היום-RTH/אתמול/7/30/MTD),
  Execution-mode (סימולטני מול ירי-אחד = computeAuxStatus קיים), ציר price/time פר-עסקה (עמודות ממשיות),
  התנהגות-סטופים בתחתית. gap-list ל-backend: G1(root) קיבוע day_type/pattern/killzone כעמודות,
  G2 `/trades/stats?group_by`, G3 `/trades/equity` (rolling+maxDD שרת-צד), G4 excursion_stats,
  G5 אכלוס `v9_trade_management_log` (Audit-06-01 F3), G6 TZ למסנן-תאריך. חוב-ידוע:
  mode=SHADOW ✅כבר ALL, WR%+R ✅נוסף ל-EdgeKpiRow, Scratch⚠️פתוח (ב-TradesSummaryStrip הלא-mounted),
  מסנן-תאריך לקסיקלי⚠️פתוח. verification (raw, Cowork): `tradeStore.ts:57 mode:'ALL'`;
  `TradesView` imports ללא EquityCurveStrip/Summary/Table (לא-mounted); `api.ts:165 fetchTrades(limit=500)`;
  mockup tag-balanced. **read-only — Michael מאשר לפני מימוש.**

## 📋 2026-06-03 (eve) — ✅ הגירת Postgres בוצעה (CC) · ⚠️ אימות-Cowork מצא silent-write באג חוסם-SHADOW

- **שערי-קדם-SHADOW שנפתחו (החלטת Michael, prompts מוכנים):** (1) ירוק 9 טסטים + verify clean —
  `CC_PROMPT_PG_GREEN_TESTS_2026-06-03.md`. (2) **audit דאשבורד+נתונים, 6 צירים** — `CC_PROMPT_PRE_SHADOW_DASHBOARD_DATA_AUDIT_2026-06-03.md`:
  wiring כל הפאנלים · עמוד trades מסודר · עמוד build-status · טבלת-נרות (4 צירי UAT) · auth-matrix · חישוב stop+T1–T5.
  verification-first; כל אי-דיוק בלוגיקת-trading/risk (T1–T5/stop/auth) = strategic-stop ל-Michael, לא תיקון בשקט.
  SHADOW נפתח רק אחרי שני השערים.
- **✅ שער-1 (ירוק טסטים) בוצע (CC `f6fabac`) ואומת בלתי-תלוי (Cowork, git):**
  finding/PASS = הירוק בא מ-fixtures בלבד, **0 שינויי קוד-פרודקשן**. verification (Cowork, raw): `git show --stat f6fabac`
  → רק 3 קבצי-טסט (`test_bars_safe_writer`/`test_day_type_api_v9`/`test_historical_replay`, 45+/32-); `grep` non-test .py = none.
  CC: 488 passed, 0 errors. **caveat (לא-חוסם):** נותרו 3 כשלים "pre-existing woodies HFE/B3" — אומת ע"י Cowork שהם **לא רגרסיית-הגירה**:
  קבצי-הטסט (`test_hfe_pattern`/`test_b3_b7_b8_b13`) נגעו לאחרונה ע"י commits **לפני** ההגירה (`aafb699`/`372cef4`),
  לא ע"י אף commit הגירה → חוב-טסטים של S4/woodies, למעקב (לא חוסם SHADOW מצד ה-DB). נותר שער-2 (audit 6-צירים).

- **✅ הגירה הושלמה (CC, 6 phases) — אומת בלתי-תלוי ע"י Cowork (code+git):**
  finding/PASS = corruption class חוסל. PG MVCC, soak 10-דק' = **21,055 דחיפות, 0 שגיאות, 0 deadlocks** (מחליף `integrity backend-כבוי=ok`).
  verification (Cowork, raw): 5 commits קיימים ב-`git log` (`3fbb71f`/`f97eef6`/`2d22b29`/`04e1eb6`/`28dda30`) · `grep sqlite3.connect backend/v9` = 0 אמיתי
  (2 hits = הערות) · `bridge/` 0 `.connect` (נותר `import sqlite3` מת) · `__tablename__` 22→40 · `safe_writer` engine-based, lock רק ב-SQLite (`nullcontext` ב-PG) · `db/read.py` קיים.
  ⚠️ הערה: נתוני-ה-PG החיים (41 טבלאות, ספירות-שורות) **לא** ניתנים לאימות מ-sandbox (PG על ה-Mac) → נשענים על raw של CC; מומלץ 2 שאילתות psql של Michael/CC.
- **⚠️ 🔴 באג latent שה-soak פספס (Cowork code-level, חוסם-SHADOW):**
  finding = ה-shim `_sqlite_to_pg_upsert()` (`safe_writer.py:62-114`) **מנחש** conflict-col מרשימת-העמודות. ל-`v9_bars_5min_woodies` (S4!)
  הוא פולט `ON CONFLICT (ts, symbol)`, אך המודל `V9Bar5MinWoodies` מכיל **רק `__tablename__`** — אין `UniqueConstraint(ts,symbol)` →
  Postgres זורק "no matching constraint" → `safe_writer` בולע ל-warning → **כל כתיבת בר-woodies 5-דק' נופלת בשקט** (מפר Rule 1).
  זהה ל-`v9_reversal_enrichment` (`ON CONFLICT (bar_ts)`, אין unique). ה-soak פספס כי ברי woodies_5min נדחו ב-גייט-RTH (0 שורות) → הנתיב לא הורץ.
  verification (raw): `awk class V9Bar5MinWoodies` → רק `__tablename__`+`ts index`+`symbol non-unique`, אין `__table_args__`; `woodies_system.py:543` כותב `(ts,symbol,...)`.
  fix/solution = `docs/handoff/CC_PROMPT_PG_UPSERT_CONSTRAINT_FIX_2026-06-03.md`: הוסף UNIQUE תואם לכל יעד-ON-CONFLICT + אודיט כל ~32 האתרים +
  העדף ON CONFLICT מפורש (פרישת ה-shim) + soak שמריץ woodies_5min RTH-valid (COUNT עולה) + green 9 טסטים. **SHADOW חסום עד שזה עובר.**
- **✅ תיקון ה-upsert בוצע (CC `2742e4c`) ואומת בלתי-תלוי (Cowork, code-level) → PG GO:**
  finding/PASS = כל יעדי ה-ON-CONFLICT של ה-shim תואמים כעת constraint אמיתי. verification (Cowork, raw):
  `awk class V9Bar5MinWoodies` → `__table_args__ = (UniqueConstraint("ts","symbol", name="uq_woodies5_ts_symbol"),)` + `zlr_detected Integer` ✓;
  `v9_reversal_enrichment.bar_ts = Column(String, primary_key=True)` ✓; אודיט-מלא של כל אתרי ה-shim (5 distinct): 2 REPLACE
  (woodies→ts,symbol · reversal→bar_ts) **שניהם תואמים**, ו-3 IGNORE (`v9_session_meta`/`v9_footprint_journal`/`v9_tpo_sessions`)
  → `ON CONFLICT DO NOTHING` bare (תקף תמיד). **0 יעדים לא-תואמים.** CC: direct-write 6 rows + soak 21,807 דחיפות/0 שגיאות
  (woodies soak count=1 = stale-detection בכוונה, לא constraint). dead `import sqlite3` הוסר מהגשר.
  **ממצא Cowork = GO ל-SHADOW מצד ה-DB.** residual לא-חוסם (למעקב לפני LIVE): 9 טסטים שדווחו fixture-only (טרם אומת ירוק בלתי-תלוי),
  fallback ל-SQLite ב-`main.py` hydration (מזהיר malformed, לא-פטאלי), וה-shim עדיין runtime (עובד; להעדיף ON CONFLICT מפורש לפני LIVE).
  לא ניתן לאמת מ-sandbox: ספירות-שורות PG החיות (PG על ה-Mac) → נשען על raw של CC.

## 📋 2026-06-03 (PM) — 🔴 DB corruption חזר שוב → הכרעת Michael: הגירה ל-Postgres מקומי (root fix)

- **🔴 corruption חזר (P0) — אומת read-only ע"י Cowork, table אותר:**
  root/finding = `quick_check` (mode=ro) → `Page 76860 btreeInitPage error 11` + `Rowid out of order` (76856–76859);
  `dbstat` ממפה את העמודים ל-**`v9_bars_footprint`**. הכותב היחיד (לא-טסט) של הטבלה = `POST /api/v9/bars/footprint`
  (`bars.py:415`) `db.add`+`db.commit()` — **כתיבת-ORM לא-מסורלת העוקפת safe_writer**, על endpoint סינכרוני ב-threadpool.
  ה-endpoint **לא** מגודר ב-`FOOTPRINT_DISABLED`, וה-flag **לא מיוצא** ב-`start_all.sh`/LaunchAgent/`.env` → footprint
  **לא באמת מושבת** (סותר את CLAUDE.md). WAL **אחיד** (engine+safe_writer WAL+busy_timeout=5000) → השורש מקביליות-ORM, לא WAL.
  ⚠️ ה-prompt הקודם (`CC_PROMPT_DB_CORRUPTION_RECURRED`) כיוון לכותבים אחרים (woodies/day_type/five_min) שכותבים טבלאות
  **אחרות** — היה מפספס את הכותב של הטבלה המושחתת. **הופרך/הוחלף.**
  verification (raw, Cowork mode=ro): `quick_check` → page 76860 ב-`v9_bars_footprint`; קריאת `v9_bars_5min` → `malformed`
  (= "אין נרות"); grep: הכותב היחיד הלא-טסט הוא `bars.py:415`; `grep FOOTPRINT_DISABLED scripts/start_all.sh` = ריק.
  fix/solution = **הכרעת Michael: לא עוד המרת-כותב — הגירה ל-Postgres מקומי כפתרון-שורש.** נתוני-עבר מתכלים → מתחילים נקי.
  plan: `docs/plans/POSTGRES_MIGRATION_PLAN_2026-06-03.md`; prompt: `docs/handoff/CC_PROMPT_POSTGRES_MIGRATION_2026-06-03.md`
  (Phase 0→5, שערים פר-שלב). היקף audit: ~22 קריאות raw `mode=ro` + 13 קוראי-safe_writer + `INSERT OR REPLACE`→`ON CONFLICT`
  + 2 נגיעות-SQLite בגשר; `psycopg2-binary` כבר ב-requirements. גבול: **localhost בלבד, ❌ לא Render/Upstash/prod-PG**.
  **❌ לא לאסוף SHADOW** עד Phase-5 soak-מקביליות נקי (מחליף את `integrity backend-כבוי=ok` של SQLite).

## 📋 2026-06-03 (RTH) — B4 fix אומת בלתי-תלוי (Cowork) + אבחון feed תקוע

- **✅ B4 (RTH time-gate + is_synthetic) — CC `0ece0fa`, אומת בלתי-תלוי ע"י Cowork (Rule 5, raw output):**
  finding=RTH chart + continuous chart שניהם כתבו ל-`v9_bars_5min` ב-INSERT OR REPLACE; אחרי 16:00 ET ה-RTH chart ייצא נפח-סשן מצטבר (עד 1M) ודרס נתוני per-bar → זיהם rolling_avg/VSA.
  fix=time-gate `_is_within_rth` (09:30–16:00 `America/New_York`, DST-safe ZoneInfo) על `/5min` **וגם** `/cumulative_delta`, עם `continue` לפני ה-INSERT (לא רק טסט — מחווט בנתיב ה-ingestion החי, `bars.py:315-317,646-647`); `/5min_continuous`+`/cvd_continuous` מושבתים; FiveMin hydration מסנן `is_synthetic==0` (`five_min_system.py:202`).
  verification (Cowork, DB read-only mode=ro): `MAX(volume) WHERE is_synthetic=0 = 71832` (תאם טענת CC) · `is_synthetic=1 count = 19`, `NULL=0` · **litmus: 0 שורות is_synthetic=0 עם volume≥500000** (אין דליפה) · טווח-נפח synthetic 126045–1,000,000 (הפרדה נקייה מ-71832 הלגיטימי, אין חפיפה) · גייט DST-safe (`ZoneInfo("America/New_York")` + astimezone) · קוד מאומת `bars.py:36-40` + call-sites · commit קיים ונוגע ב-4 קבצים נכונים. **PASS.**
  הערה ל-Michael: הגייט הופך את `v9_bars_5min` ל-RTH-only — ברי Globex לילה לא ייקלטו יותר (החלטה נעולה §3 handoff). ברי-לילה קיימים = שאריות pre-gate.
- **🔴 feed תקוע (#10) — אבחון Cowork (DB-side; Sierra/bridge/backend = Mac-side, מחוץ ל-sandbox):**
  finding=שתי שכבות. (1) **backend מושבת כרגע** (דוח CC: "Backend restart | Michael — currently stopped") → שום נתון לא יזרום עד restart. (2) עוד **לפני** שהושבת, הברים נעצרו ב-07:15 UTC/03:15 ET בעוד `v9_woodies_signals` (08:16) ו-`v9_day_type_state` (08:08) המשיכו → ה-backend היה חי עד ~08:16 אך **לא קיבל ברים חדשים אחרי 07:15** → השבר **upstream** ל-ingestion (Sierra export או bridge push), לא ב-backend. הגייט החדש (0ece0fa, נוצר 13:45 UTC) **אינו** הסיבה — לא היה קיים ב-07:15.
  verification (raw): `MAX(ts) v9_bars_5min = 2026-06-03T07:15:00Z` · `cumulative_delta=06:55` · `woodies_signals=08:16:53` · `day_type_state=08:08`. כעת RTH פתוח (≈09:5x ET) → אחרי restart הברים גם יעברו את גייט ה-RTH.
  **חוסם-SHADOW. צריך אישור Mac-side (Michael/CC):** (a) restart backend · (b) Sierra רץ+מחובר לפיד (export JSONs ב-`~/SierraChart_Data/v9_export/` מתקדמים?) · (c) bridge רץ+דוחף ל-localhost:8000 (`/tmp/bridge.err.log` — אין "API push FAILED"?) · (d) אחרי restart, `v9_bars_5min` MAX(ts) מתקדם תוך דקות ועובר גייט RTH.
- **🎯 שורש #10 אותר (CC, Mac-side, ~10:15 ET) — frozen-tail ב-Sierra study:** prompt `CC_PROMPT_FEED_BRINGUP_VERIFY_2026-06-03.md`. ראיה: `live_price.json` **חי** (7593.50 @10:11 ET) → פיד-הנתונים עובד · `5min.json` mtime מתקדם **כל 3 ש'** אבל **מערך הברים תקוע ב-05:10 ET** → ה-DLL כותב את הקובץ אך לא מקדם את הברים · bridge רץ+localhost+בריא · backend עלה health=ok · DB MAX(ts)=07:15Z לא מתקדם כי אין ברים חדשים מ-Sierra. **השבר ב-Sierra study, לא ב-bridge/backend** (תואם מסקנת Cowork: upstream ל-ingestion). **fix=Michael:** Sierra UI → Chart #3 → Study Settings → **Reload Study**. ⚠️ frozen-tail חזר למרות תיקון v9.4.5 (`bars-from-chart12`, `816dd1a`) → **למעקב**: אם חוזר תכופות = רגרסיה, לא reload חד-פעמי. verification (post-reload, חוסם-SHADOW): `MAX(ts) v9_bars_5min` מתקדם ב-2 קריאות + בר אחרון בתוך RTH (עובר גייט B4) → task #3.
- **✅ #10 נסגר — feed חי ואומת בלתי-תלוי (Cowork, 10:42 ET):** אחרי reload (Michael) הברים זרמו (בפיגור קצר — בדיקות 10:24 עדיין ריקות, 10:35 CC ראה זרימה, 10:42 Cowork אישר). raw: `MAX(ts)=2026-06-03T13:40:00Z` (09:40 ET, **מתקדם**) · ברי-RTH 09:30/09:35/09:40 ET vol 12419/11115/3631 **syn=0** (שפוי, לא מנופח) · woodies(14:30)/day_type(14:40)/cvd(13:40) טריים → backend מעבד · גייט B4 עובד על הנתיב החי (0 ברים מנופחים נכתבו). **caveat low-risk:** בר 03:15 ET יחיד (07:15Z) נכתב-מחדש post-cleanup ל-syn=0/vol=879 → re-push/backfill של reload **כנראה לא עובר דרך גייט ה-RTH** (רק הנתיב-החי כן). לא מזיק (vol שפוי, מחוץ ל-RTH, מסונן ע"י לוגיקת-סשן). follow-up אופציונלי: לוודא שהגייט מכסה גם hydration/backfill, לא רק live-tail. **SHADOW: feed=GO; נשאר integrity backend-כבוי בסוף סשן.**

## 📋 2026-06-02 (PM) — Desktop Worklist מגה-פרומפט (Phases 0–3) + ממצא doc-drift ב-DB (Cowork)

CC CLI שלח Worklist לתיקונים למחר; Cowork אימת מול קוד וקיבע הכרעות Michael → **מגה-פרומפט אוטונומי יחיד**
`docs/handoff/CC_PROMPT_DESKTOP_WORKLIST_FIXES_2026-06-03.md` (Phases 0–3 **+ תיקון נרות frontend**, לפי CC_HANDOFF_CONTRACT).
**אישור Michael 2/6: ריצה אוטונומית מלאה ללא שערי-אישור** (B5 strategic-stop מבוטל לריצה זו; שאר החוזה + Invariants קשיחים בתוקף).
פרוטוקול-שער-אוטונומי: שער שנכשל → רכיב OFF + מצב בטוח + תיעוד + המשך לשלבים עצמאיים (לא דוחפים לתוך data מושחת). הקשר: כולו SHADOW (אין נתיב ברוקר). **טרם הורץ.**

- **🔴 ממצא קוד קריטי (root + doc-drift):** `get_db()` (`session.py:71-81`) **אינו** לוקח את `_write_lock` —
  גישת `_LockedSession` **בוטלה** (deadlock ב-uvicorn single-thread). ה-docstring מפורש: "ORM writes rely on
  WAL ... busy_timeout waits rather than corrupts". **שורש ה-corruption החוזר של tick_reversal:** כתיבת ORM
  בתדר-גבוה (`bars.py:375` `db.commit()`) **לא מסורלת** — רק קוראי raw sqlite3 עוברים ב-`safe_writer`.
  **CLAUDE.md §DB Write-Safety מיושן** (מתאר lock `ec9fe97` שכבר אינו קיים) → צריך תיקון.
  verification: `session.py:71-81` (קוד) + `safe_writer.py:21` (`_write_lock` רק ל-raw). **אסור להחזיר lock ל-get_db** (deadlock).
- **פתרון (במגה-פרומפט, queued):** A1 = השבתת tick_reversal (דגל call-time + early-return `bars.py:354` + DROP+VACUUM) →
  שער `integrity_check` **backend-כבוי**; residual root (כותבי-ORM אחרים לא-מסורלים) מתועד כ-Open, **לא** נפתר ע"י lock.
  A3/D1 = כל הדגלים (`atr.py:83-93`, `trend_relabel.py:12`) → call-time. B1 = bypass `lookback_quiet`
  (`five_min_system.py:531-533,622-624`) כש-`S2_VSA_VOLUME`. **B2/B3 ללא שינוי (הכרעת Michael).** B4 = אבחון-בלבד.
- **הכרעות Michael (2026-06-02):** S2 firing — אשר B1 בלבד; **B2** (`b4>b3.high`) ו-**B3** (`_EXPANSION_MIN_ATR_K=1.5`)
  נשארים מחמירים. tick_reversal — השבתה + אבחון שורש. ⚠️ B4 עלול לזהם בקטסטי B1/B3 (נפחים 540K-980K) — מעקב אחרי RTH.
- **✅ Phase 0 הורץ (CC `9a5ed5d`) — אך אימות Cowork בלתי-תלוי מצא over-claim (לא DONE):**
  **תקין:** A1 tick_reversal early-return call-time (`bars.py`) ✓ · אף צרכן לא מייבא קבועי S2_VSA/S4 קפואים ✓ · integrity backend-כבוי=ok (CC) · 87/87.
  **🔴 פערים (round-2):** (1) **B1 partial-wiring** — bypass נוסף רק באתר אחד (`five_min_system.py:536-537`); האתר השני (`625`, gates `631/645`) **ללא** bypass → נתיב-תבנית שני של S2 עדיין חסום. (2) **D1 לא הושלם** — רק `trend_relabel` הומר ל-`flag()`; ~9 דגלים (`S2_ATR_RELATIVE`×8, `S3_RELATIVE`, `S3_MUTE`, `FOOTPRINT_DISABLED`, `S1_IB_WIDTH_ATR`, `S1_DAYTYPE_STAGING`, `S1_CVD_OPENING`) עדיין קפואים ב-import; הטענה "✓" שגויה (latent — plist מציל). (3) **B1 ללא טסט** (diff נגע רק ב-3 טסטי S4). solution: `CC_PROMPT_PHASE0_FIXES_ROUND2_2026-06-03.md`. verification: grep `lookback_quiet = True`=1 (צ"ל 2); `from ...atr import S2_ATR_RELATIVE` ×8 קיים.
- **תיקון אי-דיוק קודם:** frontend **כן** בריפו (`frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`); Phase 3 (נרות C1/C2) מפנה אליו ישירות.
- **✅ דוח Phase 0-3 מלא (CC `1bad5c0`+`7583546`) — אימות Cowork round-3 (לא DONE):**
  **תוקן בפועל מאז round-2:** B1 מחווט עכשיו ב**שני** האתרים (`five_min_system.py` 537+631, `grep lookback_quiet=True`=2) + טסט אנטי-טאוטולוגי `test_b1_lookback_bypass.py` (litmus "if reverted→RED", flag ON/OFF) — **אבל שניהם UNCOMMITTED** (M+untracked, לא בקומיט `9a5ed5d` שהדוח טען "DONE"). S2_VSA/S1_LIVE_RECLASS call-time (`173c8d6`). A1+integrity+87/87 ✓.
  **🔴 פערים round-3:** (1) **drift לא-מקומיט** — תיקון B1+טסט ייאבדו אם לא יקומטו. (2) **`sc_study/` שונה על ה-risk-surface** (uncommitted, **לא** מ-Phase 0-3): `MES_AI_DataExport.cpp` SWI SG5→SG0 · `v9_types.h` `v9.4.5-wc-fix` · `v9_woodies_export.h` ~165 שורות → סכנת source≠running-DLL + bundling ב-`git add -A`. (3) **D1 over-claimed** — רק 2 דגלים call-time, ~9 קפואים. (4) **Phase 3 נרות לא מאומת** — filter=היוריסטיקת ">2h gap" ב-`bars_5min_history.py`, אך הפסקת MES ~1h → בימי חול לא מסיר ברי-סשן-קודם; C2 CVD לא בוצע; **אין screenshot**. (5) **B4=artifact מאומת** (DB 930K vs Sierra 72K) → מאשר זיהום כיול VSA/בקטסט.
  solution: `CC_PROMPT_PHASE0_3_FIXES_ROUND3_2026-06-03.md` (commit B1; sc_study=אבחון-בלבד+החלטת Michael; D1 honest-downgrade; Phase3 session-filter אמיתי+screenshot@RTH).
- **תיקון אי-דיוק קודם:** frontend **כן** בריפו; CLAUDE.md §DB Write-Safety (uncommitted) טוען get_db נועל — **סותר `session.py:71-81`** (אין lock) → doc-drift, החלטת Michael.
- **Open:** round-3 (CC) · **החלטת Michael: `sc_study` v9.4.5 — לקמט/לבנות/לזרוק?** · CLAUDE.md doc-drift · re-verify S2 firing + נרות ב-RTH · residual ORM-write root.
- **🔴 בדיקת מערכת ליום SHADOW (Cowork 2026-06-03 ~03:00 ET) — שער DB לא עבר:** quick_check מהצד (mount, **לא-אוטוריטטיבי**) מראה `Rowid out of order` **למרות** tick_reversal מושבת → ה-residual ORM-write root עדיין משחית. חשד: `cumulative_delta` (CVD, 51,803 שורות, כותב עד 06:55) / `imbalance` — לא-מסורלים (תועד ב-NOT-DONE של CC). + `v9_bars_5min_woodies` תקוע 06-02 08:34 · נפח מקס' 5min=1,000,000 (B4 חי). CC רץ באותו רגע (index.lock; commits `825972f` B1 both-sites+4 tests, `361e5bd` ET session-filter). **go/no-go ליום SHADOW = ❌ עד `integrity_check` backend-כבוי=ok.** solution: `CC_PROMPT_SHADOW_DAY_OPS_2026-06-03.md` (אישור Michael) — שער DB אוטוריטטיבי + טיפול ב-cumulative_delta → pre-trade → איסוף → EOD integrity. נרות-מערכת חיים (readiness/bridge/Sierra) = Mac-side בלבד.
- **✅ B4 תוקן ואומת (CC `0ece0fa` + Cowork בלתי-תלוי):** טבלה אחת=RTH, time-gate 09:30-16:00 ET (DST-safe zoneinfo) על `/5min`+`/cumulative_delta` · `/5min_continuous`+`/cvd_continuous` disabled · CVD מ-RTH (מיושר, פותר C2) · ניקוי is_synthetic=1 ל-19 ברים → `max vol WHERE is_synthetic=0 = 71,832` (היה 1M) · **VSA מוגן** `five_min_system.py:202 .filter(is_synthetic==0)` · 488 passed · טסטים litmus אמיתיים. אימות per-system S1/S2/S3/S4 — כל השדות מחוברים+מאוכלסים שפוי. קוסמטי: שם study "v9.4.3" (V9_VERSION=v9.4.5 רץ) + In:17/In:19 code-default מול chart. **Open:** טבלה רציפה 24h (#11) · backend restart · `/5min_continuous` disabled עד הטבלה החדשה.
- **🔴 feed עדיין תקוע** (#10): 5min latest=07:15 UTC (03:15 ET) — לא התקדם → backend/bridge לא קולט. תנאי מקדים ליום SHADOW.
- **🛠️ החלטת Michael 2026-06-03: תיקון-שורש מלא, ❌ לא אוספים SHADOW היום.** audit Cowork חשף שטענת 2/6 "ALL writes through safe_writer" **שגויה**: ~15 אתרי כתיבת-ORM ב-`bars.py` (כל ה-ingestion: cumulative_delta/imbalance/woodies/tpo/...) + עשרות `sqlite3.connect` גולמיים (`woodies_system:141`, `footprint_system:84`, `tpo_system:88`, `session_boundary:66`) **לא הומרו** → ORM ו-raw מתחרים = `Rowid out of order` נמשך. **root-fix אמיתי:** המרת כל כותב חם ל-`safe_writer` (מנעול יחיד, **לא** lock על get_db=deadlock) + בידוד journals תדר-גבוה ל-`mems26_journals.db` נפרד + rebuild + soak תחת עומס → integrity backend-כבוי=ok. prompt: `CC_PROMPT_DB_ROOT_FIX_FULL_2026-06-03.md` (4 phases, per-phase gate). verification אומתה: אותו עמוד מושחת 96566/rowid 325707 ב-2 בדיקות = השחתה אמיתית, לא mount false-positive.
- **✅ תיקון-שורש DB — בוצע ואומת (CC `d38444d`/`edab3c0`/`9255bfa`; Cowork בלתי-תלוי):** Phase 1 (כל ה-ingestion ב-`bars.py`→safe_writer, 23 קריאות, 0 ORM-write פעיל) · Phase 2 (0 raw-write connect, קריאות→mode=ro) · Phase 4 (rebuild + **soak 600ש'/21,726 דחיפות/0 שגיאות** → `integrity_check` backend-כבוי=**ok לפני ואחרי**). **Cowork אימת:** ההשחתה 325707/376946 **נעלמה**, quick_check=ok, journals-DB נפרד לא נוצר (Phase 3 deferred=צפוי). **Open:** (1) **~5 כתיבות-ORM בתדר-נמוך** נשארו (`woodies_system:651`, `five_min:957`, `day_type/consumer:147`, 2 APIs) — ה-soak לא בהכרח הפעיל את נתיב עיבוד-הברים → סיכון נמוך, למעקב. (2) Phase 3 journal-isolation דחוי (תוכנית מתועדת, ~2-3ש'). (3) CLAUDE.md §DB Write-Safety — CC מעדכן עכשיו (Cowork יצליב דיוק). (4) `v9_bars_5min_woodies` latest ts=2025-01-01 חריג (תוצר rebuild/backfill?) — לבדוק.
- **✅ החלטה #1 (sc_study v9.4.5-wc-fix) — אומת, מומלץ COMMIT (CC `CC_DB_ROOT_FIX_AND_SCSTUDY_DIAGNOSE` + Cowork בלתי-תלוי):** v9.4.5 **כבר חי מאז 2/6** (כל 13 ה-export JSONs + DLL built 2/6 11:14). מתקן באגי-נתונים אמיתיים של S4: SWI היה זבל (SG5 לא קיים) → עכשיו **מחושב מקומית** (`v9_woodies_export.h:542-544` `v9_calc_sidewinder`, אומת ע"י Cowork); trend קרא CCI → עכשיו SG4 נכון; bars-from-chart12-direct (`:427`) מבטל frozen-tail. הסתירה SG0/SG4 נפתרה (ההערה ב-`v9_types.h` "SWI SG4" מטעה → לתקן ל-"local-computed"). ⚠️ נתוני S4 מ**לפני** 2/6 = מיפוי שגוי, לא לסמוך. **✅ COMMITTED `816dd1a`** (scoped — רק 3 קבצי sc_study, הערה תוקנה ל-"SWI local-computed", אומת Cowork). החלטה #1 סגורה. revert היה מחזיר את הבאגים → נדחה.
- **✅ CLAUDE.md §DB Write-Safety — תוקן doc-drift (Cowork):** הוסר "get_db acquires the lock" (שגוי); מתאר עכשיו safe_writer-only + get_db לא נועל (לא להחזיר=deadlock) + residual ORM תדר-נמוך + journals deferred + אימות soak 3/6.

## 📋 2026-06-02 CC Master Run — 3 phases DONE, 2 strategic-stop, 1 frontend-pending

**CC Master Run** ביצע 3 phases מתוך 6 (85/85 regression tests green):
- **✅ D-S3MUTE** (`1c28df7`): `S3_MUTE` flag ב-`_fire()` → 0 fires כש-ON. 2/2 tests.
- **✅ S4 dispatcher fix** (`401d526`): trend source = `studies` (current bar), לא stale `current_state`. + `bar_count` ב-Build Status. 3/3 tests.
- **✅ D-RDY readiness** (`3e2f785`): `READY/DEGRADED/BLOCKED` verdict ב-`BuildStatusResponse`. 4 checks (bridge, day_type, trend, RTH). RTH-aware. 5/5 tests.
- **🛑 S2/D-RVX + S1 Day-Type** = strategic stop (trading logic — ממתין אישור Michael).
- **⏳ Frontend** (Build-Status UI + Trades UX) = דורש dev server.
דוח מלא: `docs/reports/CC_MASTER_RUN_REPORT_2026-06-02.md`.

## 📋 2026-06-02 — 5 סוכני אבחון read-only + 2 פרומפטי החלטה (Cowork)

5 סוכני אבחון מקבילים, **אפס שינוי קוד**. כל ממצא = file:line + ראיה גולמית (DB/grep).
7 פרומפטי CC נוצרו ב-`docs/handoff/*_2026-06-02.md` — **ממתינים לאישור Michael פר-פרומפט לפני מימוש**.
שני ממצאים **הפריכו** השערות קודמות (verify-before-trust עבד).

- **S2 (D-RVX) — שורש מתוקן + השערה הופרכה.** השערת "channel-mismatch" (ב-2 הפרומפטים מ-1/6)
  **הופרכה** — ה-wiring תקין (`main.py:88` `bar_router.subscribe("5min", process_bar)`; הדיטקטור רץ).
  שורש אמיתי: **גייט volume בלתי-אפשרי מתמטית** — `_detect_reactive` (`five_min_system.py:469-543`)
  דורש בו-זמנית `b2_vol<=b1_vol*0.10` AND `max(prev3)<b1_vol*0.6`; על 1085 זוגות ברים אמיתיים שני
  הגייטים נפגשים **0 פעמים**. fix מוצע: לחלץ את גייט bar-2 ל-callable מוזרק + 3 וריאציות יחסיות כצופים.
  verification: `v9_five_min_setups=0 · v9_five_min_state=0 · v9_trades firing_system=2 → 0` all-time (raw).
  prompt: `CC_PROMPT_S2_REACTIVE_CANFIRE_2026-06-02.md` (מתקן Phase 0 של הפרומפטים הקודמים, שומר Phases 2-5).
  **[2026-06-02 PM] חידוד funnel + ממצא data-quality (Cowork, raw):** funnel היסטורי 1293 חלונות →
  terminated_at b2_drop:1227 (~95%) · reached_lookback:**0** (lookback_quiet מעולם לא הורץ — אישוש ש-b2_drop
  הוא ה-blocker, לא lookback). + **חוסם-נתונים חדש:** נפחי close מנופחים 15:15–16:15 (980001/960000/950000…,
  `is_synthetic=0`, ×50–100 מנורמלי; all-time MAX=980001) מעוותים b2_drop+lookback — לאמת מקור מול Sierra
  export לפני כיול (strategic-stop §Source-of-Truth). נוסף כ-§D2 לפרומפט. **לא לכייל b2_drop לפני אימות מקור.**
- **S4 (Woodies) — תקין; "A1 חוסם הכל" הופרך.** S4 **יורה** (`v9_trades firing_system=4`=10, אחרון
  היום `id=384` 07:46); trend מתקדם (BLUE 67/GRAY 34/RED 3/YELLOW 5 ב-109 ברים); bar_count עולה.
  פער אמיתי: **single-source violation** — ה-dispatcher (`woodies_system.py:359,374`) קורא `current_state`
  שמתעדכן רק ב-:425 (אחרי decision_tree :422) → trend של הבר הקודם; ה-relabel ב-:279 מגיע ל-A1 אך לא
  ל-dispatcher. fix: `studies.get("trend_state")` ב-:359 + bar_count ל-:425 + per-pattern blocked_reason.
  prompt: `CC_PROMPT_S4_WOODIES_CANFIRE_2026-06-02.md`.
- **S1 (Day-Type) — inputs מתים.** subscriber תקין + bar_count עולה (הפריך "subscriber broke").
  שורש: **`bar.atr` תמיד None** (`main.py:230-244`; אין עמודת atr ב-`v9_bars_5min`) → B3 range_ratio
  קבוע 1.0, re-eval מת, C3=hard-lock דה-פקטו (סותר "day-type רציף"); IB-width משתמש בממוצע 5-דק'
  כ-daily-ATR → EXTREME מזויף; `day_type_inspector.py:76` AttributeError (`ib_class.width` במקום
  `ib_width`) נבלע ב-`except:pass:78` → כל ה-interpretations נופלים בשקט. verification: `v9_day_type_history`=2
  שורות תקועות `Normal/LOCKED_LOW_CONF/p=0.68/C3`; `lock_state` distinct={LOCKED_LOW_CONF:104,PENDING:364}
  — אף פעם LOCKED אמיתי. prompt: `CC_PROMPT_S1_PIPELINE_AUDIT_2026-06-02.md`.
- **Trades — `TradeDetailsModal` = dead code.** הרכיב העשיר (timeline ניהול ENTRY→STOP_MOVE→T1-3→EXIT,
  confidence, day_type, MAE/MFE) **לא מיובא בשום מקום** (grep) — ה-timeline "ששודרג" קיים רק שם ולא מוצג;
  `v9_trade_management_log`=804 שורות אמיתיות אך נעלמות. + `outcome=BE` (2) חסר ב-enum/filter; `total/truncated`
  נזרקים ב-normalize → אין "showing N of M"; אין מסנני Direction/Synthetic. prompt: `CC_PROMPT_TRADES_UX_UPGRADE_2026-06-02.md`.
- **Build Status — `global_gates` לא מרונדרים.** `bridge_inspector.py:137-145` מפיק 8 שערי freshness אך
  אין `global_gates.map` בפרונט (grep) → פאנל "האם מידע זורם" של ה-Bridge בלתי-נראה; שדות הגשר מוסתרים
  מאחורי pill "FRESH" יחיד (15 שדות woodies + opening_type/day_type/POC/VAH/VAL/IB). **D-RDY readiness=לא מומש**
  (אין `readiness` ב-`BuildStatusResponse`). prompt-על: `CC_PROMPT_BUILD_STATUS_MEGA_2026-06-02.md`
  (קופלו לתוכו המלצות observability מ-S1/S2/S4).
- **2 פרומפטי החלטה מאושרים:** D-S3MUTE → `CC_PROMPT_D_S3MUTE_2026-06-02.md` (אומת: אין `S3_MUTE` בקוד) ·
  D-WDIAG `trend_original` → `CC_PROMPT_D_WDIAG_TREND_ORIGINAL_2026-06-02.md` (**2 נגיעות** מאומתות —
  הכרעת סתירה מול דוח CC: CC "שורה אחת" שגוי, "4 נגיעות" הגזמה. אמת: `trend_relabel.py` +
  המילון המפורש `woodies_system.py:425-432`; **לא** schema; `trade_context.py:342` אופציונלי).

- **✅ מומש היום (commits, backend נטען מחדש PID 76066 — הכל live):** S3MUTE `1c28df7` · S4 dispatcher+bar_count `401d526` · D-RDY backend `3e2f785` · trend_original `1e077fa` · **frontend** global_gates+readiness banner+BE/Direction filters `0240cab`.
- **🔴 חוסם DB corruption — חוזר תחת עומס (task #18, פתוח 2026-06-02):** הסימפטום הראשוני: קריאת `bars5min` נכשלה ו-`except Exception: return []` (`bars_5min_history.py:96`) **בלעה בשקט** → 0 נרות → צ'ארט ריק (הפרת "אין כשלים שקטים"). תוקן בקוד (`ea33c2f`: תפיסת `DatabaseError` בנפרד + דילוג OHLC לא-מספרי + warning) + שוקם ה-DB (`.recover`+swap; **סבב שיקום ראשון עדיין היה פגום — נתפס ע"י הצלבת Cowork** `Rowid out of order`; סבב שני יצא נקי, `integrity_check=ok`). **אבל ה-corruption חזר תוך דקות** — אומת: `integrity_check` עם backend **כבוי** עדיין corrupt (Tree 18/35/11 `2nd reference to page`, tick_reversal TEXT-in-ts/NULL-close, 30min_woodies חסר שורות אינדקס). **שורש אמיתי (Cowork אימת בקוד):** כתיבות SQLite מקביליות לא-בטוחות — חיבור **משותף** בין threads (`footprint_system.py:80` `check_same_thread=False`, כתיבה בתדירות גבוהה) + סחף `sqlite3.connect` גולמיים (`woodies_system.py:141/549/573`, `reversal_handler.py:75`, routes) בלי `WAL`/`busy_timeout` עקביים. גודל ה-DB **אינו** הגורם — מקביליות היא. **trades לא נפגעו** (טבלה נפרדת). **פתרון-שורש בתהליך:** `CC_PROMPT_DB_WRITE_SAFETY_ROOT_FIX_2026-06-02.md` — writer יחיד מסודר (queue/lock, אף חיבור משותף) + WAL/busy_timeout עקבי + בידוד tick/footprint ל-store נפרד FIFO-capped + checkpoint ב-SIGTERM (LaunchAgent ל-SIGTERM לא SIGKILL). **שער GO/NO-GO לפני 16:30:** soak תחת עומס + `integrity_check` נשאר `ok` → אוספים היום; אחרת — לא אוספים (נתונים מושחתים גרועים מאין). backend כבוי בינתיים.
- **🟡 פתוח עקב השיקום (task #17):** היסטוריית 4 טבלאות בר (woodies 5/30, footprint, tick) אבדה → מתמלאת live, צ'ארט דליל. לשחזר מ-Sierra backfill (מקור-אמת), לא מהגיבוי הפגום `.corrupt.bak`.

### CC MEGA FIX — צ'ק-ליסט (`CC_MEGA_FIX_ALL_2026-06-02.md`)
**החלטה נעולה (Michael):** footprint **מושבת זמנית** (`v9_footprint_journal` = מקור ה-corruption; 1/2/4 לא תלויים בו) עד כמה ימים נקיים של 1/2/4.

- [x] **Phase 1 · יציבות DB — ✅ נסגר 2026-06-02.** **שורש אמיתי: כתיבות SQLAlchemy ORM עקפו את ה-write-lock** (לא רק חיבורים גולמיים). fix: `get_db()` מקבל את ה-lock (`f5568a2`) → צומצם ל-commit-only + RLock (`ec9fe97`, פתר deadlock/חניקה). + footprint מושבת + safe_writer + VACUUM (ניקה carried-over B-tree corruption מהגיבוי). **אומת:** integrity backend-כבוי=ok (CC) + הצלבת Cowork נקייה תחת כתיבה חיה ב-16:57/17:03/17:05 + latency health 45-55ms. (הדוח `CC_DB_WRITE_SAFETY_REPORT` היה מיושן — commit 0afe147/soak-89ש'; המציאות עברה אותו.)
- [ ] **Phase 2 · streams** — cumulative_delta + imbalance לא נכתבים (~8ש') · tpo_bars ריק (wiring ל-journal במקום לטבלה). (woodies overnight=תקין)
- [ ] **Phase 3 · S2 Reactive חי** (D-RVX VSA) — וריאציה חיה + observers. 🛑 בחירת וריאציה = Michael.
- [ ] **Phase 4 · S1 day-type חי** — קידום shadow_reclass ל-live לפי האפיון. ⛔ Auth Table = אישור Michael, default-OFF.
- [ ] **Phase 5 · S4** — אימות יורה נקי + trend_original על בר ±200.
- [ ] **Phase 6 · Backfill היסטוריה** מ-Sierra (אחרי DB יציב).
- [ ] **Phase 7 · מוכנות** — readiness→READY + Pre-Trade.

**Open (לפי עדיפות):** 🔴 **Phase 1 (DB יציב) — שער חוסם להיום** · Phase 2 streams · Phase 3/4 (strategic-stops) · Phase 5-7 · מוניטור RTH מתוזמן. *הצ'ק-ליסט מסומן ✅ אחרי הצלבת Cowork פר-phase.*

---

## 📋 2026-06-01 (session 3) — Fire-Audit חזותי + 3 החלטות פתוחות (Cowork)

מקור: צילומי Sierra (Woodies chart 12 + chart 5/TPO+CVD) + 2 מחקרים חיצוניים. **אפס שינוי קוד — אנליזה + החלטות.** תוויות החלטה מלאות ב-`docs/plans/DECISION_LEDGER.md`.

| תווית | פריט | סטטוס | root/finding | נקודת החלטה / verification |
|-------|------|-------|--------------|----------------------------|
| — | Fire-Audit חזותי (S1/S2/S4, חלון נראה) | ✅ DONE | 7 מועמדים שהיו צריכים לירות; ZLR UP=conviction גבוה שפוספס | `docs/reports/AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` |
| **D-RVX** | Reactive volume threshold | ✅ APPROVED 1/6 (Stage 1 shadow A/B/C + verify) | `DROP_THRESHOLD_PCT=0.10` בלתי-אפשרי (0/54 עברו, קרוב 88%); ספרות=יחסי/RVOL לא בר-מול-בר | brief: `DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`; מימוש: מגה-פרומפט Reactive |
| **D-S1DYN** | S1 dynamic re-classification | ✅ APPROVED + 🟢 IMPLEMENTED-SHADOW 1/6 (CC Phase 0-2 · `caeb984`/`df16d03`/`9d8ff30` · Stage 3 נפרד) | reeval קיים אך **ATR-relative+conf-gated**, לא IB-relative → לא תפס extension (E_up=1.77, R=2.77); הקפאה ב-Normal חסמה Initiative של S2 | brief: `DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`; מימוש: מגה-פרומפט S1 |
| **D-RDY** | Pre-Fire Readiness Gate | ✅ APPROVED 1/6 (הרחבת build_status בדאשבורד) | אוטומציה read-only של PRE_TRADE_PROTOCOL מעל BuildStatusAggregator | `CC_PROMPT_FIRE_AUDIT_DIAGNOSIS_AND_READINESS_GATE_2026-06-01.md` §B |
| **D-WDIAG** | Woodies missed-fire diagnosis | ✅ APPROVED 1/6 (ZLR confirmed-bounce+DLL · HFE low-tier/exit · audit gray) · מימוש אחרי D-RVX+D-S1DYN | ZLR Impl-B נאמן אך override DLL (58d6538) סותר; HFE כבר low-tier; 17 HFE ב-GRAY=חשד באג תיוג | brief: `DECISION_BRIEF_WOODIES_ZLR_HFE_TREND_2026-06-01.md` |

**✅ D-WDIAG relabel — מומש ומאומת בקוד/טסט (Cowork 2026-06-02):** root: ה-override המקורי (`1c0397a`) היה partial-wired (לא הגיע ל-decision_tree). fix: relabel חולץ ל-`trend_relabel.py` (מקור יחיד), נקרא ב-`woodies_system.py:279`, מאחורי דגל `S4_EXTREME_TREND_RELABEL` (OFF); טסט אינטגרציה אמיתי דרך `decision_tree.evaluate_bar` (commit `c43acc6`, CC 6/6 green + litmus 2 RED). **verified (Cowork):** הרצה ישירה של פונקציית הייצור — flag ON: YELLOW+331→BLUE / −257→RED / GRAY+80→GRAY · flag OFF: YELLOW→YELLOW (לא טאוטולוגי; הטסט הקודם `c9f3883` שהיה טאוטולוגי הוחלף). הערה: לא הורצה pytest מלאה ב-sandbox Cowork (חסר sqlalchemy). **נותר:** shadow על בר ±200 ב-RTH + אישור Michael להדלקת הדגל קבוע. דגל OFF (בטוח).

**✅ D-WDIAG `trend_original` — מומש (CC 2026-06-02):** [2026-06-02] שדה `trend_original` לשוואת A/B relabel. root=ה-relabel mutation in-place מחק את ה-trend המקורי, אין דרך להבחין trend טבעי מ-relabeled ב-trade record. fix=2 נגיעות: (1) `trend_relabel.py:22` שומר `studies["trend_original"]` **תמיד** (גם no-op/flag-OFF). (2) `woodies_system.py:433` מוסיף ל-explicit `current_state.update()` → זורם ל-`get_current()`→`cross_context`→`v9_trades`. +P3 nice-to-have: `trade_context.py:342` → תצוגת סיכום. verified: 10/10 pytest green (4 חדשים + 6 קיימים). litmus: revert P2 only → 4 RED (מוכיח שהנתיב מלא). דוח: `docs/reports/D_WDIAG_RELABEL_FLAG_AUDIT_2026-06-02.md`.

**🔎 בקרה בלתי-תלויה (CC, `INDEPENDENT_VERIFICATION_2026-06-02.md`, commit `638072b`):** 16 MATCH · 1 MISMATCH · 0 cannot-verify. **MISMATCH יחיד = ה-override `1c0397a` (D-WDIAG) partial-wired** — אומת: כותב `_ts`+`current_state` אך לא `studies["trend_state"]`; decision_tree A1 קורא `studies` → ה-override **לא מגיע ל-`ready_to_route`**. מצב: inert ל-routing (אין fires שגויים), אך לא עקבי. כל שאר טענות Cowork (עיגון briefs, IB/E_up/R, 73/73 bounce, D-OBS read-only, D-S1DYN shadow-only, 27/27 נתיבי קבצים) = MATCH. D-RVX = לא בוצע (MATCH).

**✅ סטטוס מימוש EOD 2026-06-01 (אחרי שליחת 4 הפרומפטים ל-CC):**
- **D-S1DYN — 🟢 IMPLEMENTED-SHADOW (CC, Phase 0-2).** root: 4 ממצאי האבחון אומתו (lock conf≥0.85; `move_30=None` מת :783; אין עמודת atr → range-trigger מת; rescore=behavior לא IB-relative). fix: `shadow_reclass.py` + דגל `S1_DYNAMIC_RECLASS` + טבלה `v9_day_type_shadow_transitions` + תצוגת shadow chain ב-Build Status (commits `caeb984`/`df16d03`/`9d8ff30`). **verified (Cowork, code-level):** commits+file+flag(atr.py,main.py)+table(day_type_inspector.py) קיימים. **runtime:** היום נרשם shadow `Normal→Variation` (@min387 E↑0.74 · @min397 E↑0.95) — לא הגיע ל-Trend (נתונים חלקיים) → **אימות יום-trend מלא ב-RTH הבא**. Stage 3 (live gating) = אישור נפרד.
- **D-RVX / D-OBS+D-RDY / D-WDIAG — ⏳ נשלחו ל-CC, אין דוח עדיין** (טרם הורצו/הושלמו). להמשיך מחר.

**רצף מימוש (Michael 2026-06-01):** (1) roadmap/ledger ✅ · (2) מגה-פרומפט Reactive (בדיקה+תיקון+3 וריאציות בתצוגת build_status עם אור ירוק למי שירה + תצוגה בטריידר) · (3) מגה-פרומפט S1 (אבחון מלא + דינמי) · (4) Woodies. **כל פריט במלואו לפני הבא. כל קוד שנוגעים = נושא תווית D-XXX + סיבה.** פילוסופיה: shadow-first (צופים) → אישור → חיווט live.

---

**Version:** V2 (full restructure 23/5 17:30) · **Updated:** 2026-06-01 EOD (Cowork — 🟢 SHADOW יום 1 פתוח · backend+LaunchAgent · chart #5 רציף · POC=chart3 תקין · IB RTH-only · management-log+synthetic-badge · flags ON=A(always-on) · day-type=continuous · 🟡 2 באגי wiring (S2 opening_type `2124411` + build-status armed/blocked `f493126`) → **code-level אומת ע"י Cowork; S4 trend=לא-באג (bar_count תקין); runtime עדיין assertion → לאמת חי ב-RTH הבא** · המרת ספי-זיהוי ליחסי (audit) · Bridge inventory · Pipeline 5=חוסם-LIVE · 🆕 Fire-Audit חזותי + 3 החלטות פתוחות D-RVX/D-S1DYN/D-RDY → `docs/plans/DECISION_LEDGER.md`) ·

---

## 📋 2026-06-01 (session 2) — Bar Continuity + Live Price

| # | Item | Root Cause | Fix | Verification |
|---|------|-----------|-----|-------------|
| S0 | Live price stuck 7590.50 | `sc.Close[idx]` = RTH bar close, frozen overnight; bid/ask = live L1 | `_best_price()` uses bid/ask midpoint when >2pt divergence | price=7612.12 (was 7590.50) |
| S1a | Flat stale bars in v9_bars_5min | FiveMinAggregator builds from stale sc.Close → O=H=L=C=7590.5 | Filter: reject bars where O=H=L=C AND volume>10k | 8 flat bars deleted |
| S1b | WoodiesSystem persist duplication | `_persist_bar` used `datetime.now()` as ts → unique row every 3s push | Use bars actual DLL ts + INSERT OR REPLACE | 1247 dupes deleted; 301 unique, 0 dupes |
| S2 | Chart endpoint gaps | Only read v9_bars_5min (sparse); ignored v9_bars_5min_woodies (dense) | Merge both tables in `_fetch_bars_5min()` | 5 bars returned with real prices |

---

## 📋 2026-06-01 — Connectivity + OOH + Hydration (CC diagnostic fix session)

| # | Item | Root Cause | Fix | Verification |
|---|------|-----------|-----|-------------|
| P0.1 | Backend dead (DISCONNECTED) | No LaunchAgent for backend — screen session died silently | Created `com.mems26.backend.plist` with KeepAlive | `curl health` → alive, PID 1289 |
| P0.2 | v9_bars_5min only 7 rows | `timedelta` not imported in `bar_ingestion.py:8` | Added `timedelta` to import | 7 → 609 rows, zero NameError |
| P0.3 | History gap-fill 1h drift | `v9_history.py:43` used `America/Chicago` | Changed to `America/New_York` | Matches `base_stream.py:74` |
| P1.4 | Y IB dll_missing | `v9_tpo_sessions_archive` 19 cols vs 27 → `SELECT *` failed | Explicit column list in `_archive_yesterday` | 30 sessions archived, zero error |
| P1.5 | Woodies 5min 26k dupes | No UNIQUE constraint, no UPSERT, no symbol | UNIQUE(ts), INSERT OR REPLACE, symbol='MES' | 26,250 → 970 unique rows |
| OOH.6 | No candles overnight | Sierra exports RTH-only bar history | Option C: DB fallback in woodies_chart_routes.py | endpoint serves from DB when export empty |
| P2.7 | State lost on restart | No hydration inventory | Startup log: CVD/CCI/bars/archive counts | session-bounded CVD, archive populated |

---

## 📋 סיכום יום שישי 2026-05-29 — מה הושלם היום

| # | משימה | סטטוס | commit |
|---|-------|--------|--------|
| P31 | Daily Reset/Archive backend (8 tasks A-H) | ✅ CC DONE | multiple |
| P31.1 | Fix-up 9 gaps (T1-T6 · 101 tests) | ✅ CC+Cursor DONE | multiple |
| DLL Frozen-Tail | mapIdx clamp-detect patch · DLL rebuilt v9.4.3-p31.1 | 🔴 FIX SHIPPED · NOT verified (see blocker ↓) | ada6c88 |
| Backend routing | current_bar override S4 gets live SWI/CCI | ✅ DONE | in ada6c88 |
| Bug E | stop_hit_ts < entry_ts — entry guard in BarLevelDetector | ✅ DONE | e3b986c |
| S2 None warn | current_day_type=None logged (rate-limited 1/min) | ✅ DONE | e3b986c |
| Readiness Check | CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md | ✅ WRITTEN | — |
| Backend recovery | backend was down — restarted screen session | ✅ DONE | — |

**Test count (end of day):** 7/7 trade_manager · 4/4 DLL regression · 2/2 bar routing · 101/101 P31.1 · 17/17 day_type · all green.

---

## ⚙️ החלטות תפעוליות (משפיעות על מה שהמערכת מבצעת · Michael 31/5)

1. **תקרת סיכון — אין כרגע.** ⚠️ שער חובה לפני LIVE (P-L0a) — להגדיר לפני כסף אמיתי. SHADOW=בסדר.
   **MAX_CONTRACTS=5 (Michael 31/5)** — לקבוע + **לאכוף** (GAP-4: כרגע לא נאכף). ⚠️ Auth Table מקס' 3/setup → עסקה לא תעבור 3 אלא אם משנים גם אותו. לאמת אם MAX_CONTRACTS = per-trade או מצטבר/מקבילי.
   **GAP-3 (מי יורה) — Michael החליט: לבנות חישוב R:R בדולרים** (רווח פוטנציאלי מול הפסד) ולבחור לפיו את היורה. פיצ'ר חדש שמשנה first-wins → **מפרט (D) קודם, אישור, ואז מימוש.** דורש מנגנון buffering (חלון לאיסוף setups מתחרים).
2. **גודל פוזיציה — באפיון.** לאמת קוד מול אפיון (טבלת-על).
3. **מי יורה — ⚠️ GAP-3 (HIGH, אומת בטבלת-העל):** "יחס רווח הגבוה" **לא קיים באף מסמך אפיון** — מופיע רק ב-STATUS_BOARD. כל המפרטים הנעולים + הקוד = **first-wins**. הפער = בין הכוונה (יחס-רווח) למה שתועד/נבנה (first-wins). **החלטה דרושה:** להשאיר first-wins או לבנות בחירת יחס-רווח (D חדש + scoring + buffering ב-gateway — פיתוח חדש). מקור: `docs/reports/FULL_PATH_MEGA_TABLE_2026-05-31.md`.
4. **קידום מצב (SHADOW→DEMO→LIVE) — Michael מחליט ידנית.**
5. **פילטרי זמן/חדשות (lunch/FOMC) — דחוי, לא עכשיו.**
6. **k-values — נעולים על priors, כיול אחרי סוף ה-SHADOW.**

## 🧩 Pipeline 5 — צעדים בטוחים בוצעו (2026-05-31)

- **1.12 pytest** — root: `setup_db` חסר ב-`tests/v9/api/conftest.py` → תוקן (import אחד, `f84d631`). +7 (44→37 failed). **37 כשלים → **37→11** (`PYTEST_CLOSE_2026-05-31.md`, `1fc6ae4`): 26 תוקנו. כל 3 החלטות Michael יושמו: #1 cross_context טסטים עודכנו · #2 PENDING הוסף ל-`_ACTIVE_TRADE_STATES` (slot לא נפגע, gateway-level) · #3 NT counter=אותו בר (dedup תקין)→טסט תוקן. **11 נותרים → תוקנו 10 (37→1)** (`PYTEST_GREEN_FINAL_2026-05-31.md`, `457cd1c`): event-loop fixture + temp DB + find-by-trigger (בידוד אמיתי, לא skip). **נשאר 1 — באג לוגיקת-מסחר אמיתי:** `bar_level_detector._parse_ts` משווה naive מול aware → entry guard מדלג → **T1 לא נתפס** (עסקאות לא נסגרות ב-target!). מתחבר ל-1.6 (תיקון 30/5 לא כיסה tz-mismatch). ⚠️ **אבחון הושלם** (`DIAGNOSE_T1_TZ_2026-05-31.md`): שורש = naive-vs-aware ב-`bar_level_detector.py:91` + SQLite מפשיט tzinfo; ה-TypeError **נבלע ב-except שקט** (שורה 127) → T1/T2/stop **לא נתפסים**. **SHADOW חי מושפע — 334 עסקאות פעילות ירו TypeError → ה-detector no-op.** קשר ל-1.6: התיקון מ-30/5 פתר "ברים לא מגיעים", לא את ה-TZ. ⚠️ **משמעות: נתוני SHADOW לסגירת target פגומים → תנאי מקדים לכיול.** המלצת Cowork: Option B (UTC aware, Rule 4) + תיקון ה-except השקט + רגרסיה. **✅ Michael אישר 31/5** (תיקון תקינות, לא שינוי אסטרטגיה) → פרומפט `CC_PROMPT_FIX_T1_TZ_2026-05-31.md` נשלח. היקף מצומצם: נרמול TZ + un-swallow + רגרסיה בלבד; יסגור pytest ל-0 ויפעיל מחדש זיהוי target/stop ב-SHADOW (לתעד backlog סגירות). **audit מערכתי (`TZ_SYSTEMIC_AUDIT_2026-05-31.md`) אישר: הבאג לא systemic — רק האתר הזה; שאר הקוד מוגן (Pattern A/B/C, 20+ מודלים נסרקו). Option 2 (TypeDecorator boundary fix) דחוי ל-P6 כהקשחה עתידית — לא נחוץ עכשיו.** **✅ בוצע 31/5: pytest ירוק לחלוטין (2535 passed, 0 failed)** — fix שורה 89 (Pattern A: `tzinfo is None`→UTC); BarLevelDetector מזהה שוב targets/stops. **✅ אומת 31/5:** (a) ה-except רושם `logger.error(exc_info=True)` — לא שקט, עומד בדרישה; (b) **DB ריק (0 trades)** → אין backlog burst. ה-334 היו מ-session חי קודם. ⚠️ **משמעות: כרגע לא נאספים נתוני SHADOW — השרת לא רץ.** כיול הדגלים מחייב הרצת SHADOW (ברים→עסקאות). בירור: ייתכן DB אופס (`mems26_pre_shadow_reset_*`) — לאשר אם מכוון.
- **#4 CVD חי — בוצע** (`S1_CVD_LIVE_2026-05-31.md`, `216520d`): ה-CVD מחליף את opening_type החי כשהדגל ON + footprint deltas, fallback למחיר אם חסר, golden regression 71/71, אומת אין נתיב ל-order. ⚠️ הערת "shadow" בפרומפט הדגלים מיושנת — CVD חי עכשיו.
- **P5-0 Gateway audit** (read-only) → `P5_0_GATEWAY_AUDIT.md`. **המלצה: MERGE** (בסיס Legacy + 5 שערי סיכון + חילוץ RiskValidator מ-New) · confidence HIGH. אישר ממצאי Cowork (New חסר cooldown/SSV/cluster/chop; cutover=רגרסיית סיכון). חשבון parameterized ב-`sierra_command.py` (swap אחד→37138283). dead-code: 5 קבצים (לא למחוק עד P5-2). Apex: `PA-APEX-125218-01` ב-2 מקומות + `APEX-125218-13` (LIVE, מת — אין Apex).
- **🔒 כל 4 החלטות P5 נעולות (Michael 31/5):** **Q1=MERGE** (Legacy base + חילוץ RiskValidator מ-New) · **Re-lock 1=BuyEntry+Attached** (dev) · **Re-lock 2=ModifyOrder** (dev, P5-4/5) · **Heartbeat=ALERT-ONLY** (אין auto-KILL — נתיב DLL יחיד + false-positive; flatten ידני). **APEX מת** (שני המחרוזות), חשבון יחיד 37138283 (sim/live=toggle). **חוסם 1.2 נסגר בהחלטה.** → P5-1 משוחרר לכתיבה.

## 🚀 בביצוע — 2 מגה-פרומפטים E2E נשלחו (2026-05-31)

הפרומפטים נשלחו לסוכן הקוד לביצוע (סדר תלות: 1 לפני 2):
- **E2E 1/2** (`docs/handoff/MEGA_E2E_1of2_PIPELINE_TRADES_2026-05-31.md`) — הבסיס:
  (A) audit סנכרון bridge→backend→DB→build_status→dashboard→trades · (B) אבחון
  נתיב הטרייד · (C) תיקון באגי עמוד הטריידס (Scratch תמיד 0 / mode=SHADOW default
  / מסנן תאריך לקסיקלי / חסר WR%+R / truncation 200) · (D) סדרת בדיקות נראות+טריות.
  מכסה משימות #18 (אבחון טרייד) + #19 (sync audit) + צ'ק-ליסט הטריידס.
  **✅ חזר GREEN 31/5** (`docs/reports/PIPELINE_TRADES_E2E_2026-05-31.md`): audit סנכרון
  ללא שברים · אבחון = הצינור תקין, הבאגים בשכבת התצוגה · 5 תיקוני UI עם diffs
  (scratch, mode→ALL, date filter, WR%+R, limit 200→500/1000+truncated) · 7 טסטי
  e2e PASSED (פלט גולמי) · 4 כשלים אומתו כ-pre-existing ב-`git stash`. **הסתייגויות:**
  אימות ברמת endpoint/חוזה, **לא** UI חי (D1/D2 visibility/freshness בפועל) → לאמת
  ב-SHADOW; C2 (mode→ALL) שינוי UX מכוון; uncommitted (ממתין ל-commit approval).
- **E2E 2/2** (`docs/handoff/MEGA_E2E_2of2_S1_S2_S3_IMPL_2026-05-31.md`) — מימוש
  S1/S2/S3 (relative ATR + CVD/PE + day_type מדורג) מאחורי flags כבויים +
  golden regression + shadow-scoring. **שער:** מתחיל רק אחרי ש-1/2 ירוק.
  **✅ E2E 1/2 committed (`a3afe49`). ✅ E2E 2/2 הושלם במלואו GREEN 31/5 — כל 4 השלבים.**
  תשתית ATR Wilder + 5 flags default OFF + golden baseline לכל שלב + מימוש relative.
  **71/71 טסטים PASSED** (flag OFF=identical / ON / ATR-none+median fallback).
  שלבים+דוחות+commits: ATR (`1df766b`,6) · S2 (`ebc7f6a`,22, `S1_S2_S3_IMPL`) ·
  S3 (`87f7553`,11, `S3_IMPL`) · S1-opening (`0c47bb9`,13, `S1_OPENING_IMPL`,
  shadow-dict original=live) · S1-daytype (`7a64361`,19, `S1_DAYTYPE_IMPL`,
  IBWidth.EXTREME + staging 60%→IB lock + C-period re-diagnose). אפס נגיעה
  order/risk/sizing/polling. Cowork אימת — אין תיקונים. **הערות כיול (priors):**
  gap tiers 0.25/0.50/1.0 מול R01 0.3/0.7/1.2; EXTREME matrix = WIDE placeholder.
  **החלטות Michael 31/5 (pytest triage):** #1 cross_context=עדכן טסטים ✅ · #2 PENDING=active ✅
  (בטיחות slot) · #3 NT counter=לוודא distinct-bars ואז להחליט · 8 ordering=תקן infra → נשלח ל-CC.
  **החלטה 31/5: `S1_CVD_OPENING` → חי (לא shadow)** — ה-CVD/PE יחליף את סיווג הפתיחה החי מקצה-לקצה
  (→ matrix → day_type → playbook), מאחורי הדגל + fallback למסווג מחיר אם CVD/footprint חסר +
  golden regression. דורש שינוי מימוש (CC). משנה התנהגות SHADOW → לצפות.
  **k נעולים על ה-priors מעכשיו** (Michael 31/5 — gap/expansion/PE/EXTREME). אין המתנה ל-soak.
  התאמה תגובתית: אם סף מתנהג רע ב-SHADOW → לבקש מ-CC המלצה מבוססת-נתונים ולעדכן (re-lock). רשת ביטחון = מעקב + החזרה per-flag.
  **החלטת Michael 31/5: להדליק את 5 הדגלים מעכשיו ב-SHADOW** (לא להמתין 60 יום) —
  כיול חי + החזרה per-flag אם מתנהג רע (`docs/handoff/CC_PROMPT_ENABLE_FLAGS_SHADOW_2026-05-31.md`).
  הערה: `S1_CVD_OPENING`=shadow-scoring (לא משנה סיווג חי, רק רושם להשוואה). k נשארים
  priors, נעילה לפי הנתונים החיים. **אסור** DEMO/LIVE/order — SHADOW בלבד.
- כללי בקרה: flags default OFF (כבוי=קוד קיים), גיבוי רגרסיה לפני כל שינוי, שינוי
  אחד בכל פעם, אפס נגיעה ב-order/risk/sizing/polling, נעילת ערכים אחרי soak+אישור.
- מקורות מחקר: `RESEARCH_01/02/03_*`, `S1_S2_ATR_NORMALIZATION`, `CALIBRATION_MATRIX_*`.

## ✅ Michael approvals — 2026-05-31 (עקרוני, ממתין לכיול+backtest)

- **S2 (five_min) המרת ספים → ATR יחסי** — ✅ מאושר עקרונית (EXPANSION/POC/PROXIMITY/SR/STOP/POLE/HEAD/double_bt). priors מ-RESEARCH 02; נעילת ערכים אחרי backtest (dollar vs ATR per Davey) + soak.
- **S3 (footprint) MIN_LEVEL_VOL→נפח, range_ticks→ATR** — ✅ מאושר עקרונית.
- **סיווג הרצת פתיחה (opening) — PE/CVD + gap קטגוריות + 15→30** — ✅ מאושר עקרונית.
- **סוג היום (day_type)** — ⏳ ממתין לאישור סופי של המודל (ראה דיון 31/5): 30דק'=סיווג ראשוני, 60דק'=חיזוק+נעילת IB, re-diagnosis מתמשך. הערת Cowork: לפי R03 חלון C-period (10:30–11:00 ≈ "90 דק'") הוא gate האישור החזק ביותר — מוצע שה-"90" יהפוך לשלב ולידציה/אישור (לא סיווג שלישי), שזה בדיוק ה-re-diagnosis שמיכאל ביקש.

## 🧪 Verification Log — Cowork 2026-05-31 (finding → evidence)

- `[2026-06-01]` **🔴 חקירת RTH (Michael + צילומי Sierra chart 12+5) — 2 ממצאים מאומתים מול ה-DB החי (`data/mems26_local.db`):** **(1) S2 Five-Min מת — אפס פלט אי-פעם.** `v9_five_min_setups` all-time=**0** · `v9_five_min_state` **0 שורות אי-פעם** · `v9_trades firing_system=2` all-time=**0** · `v9_system_signals` היום=רק system_id=3 (footprint, 60). רק S3 (142 trades) ו-S4 (4 trades + 79 signals: HTLB33/TLB28/ZLR10/FAMIR6/HFE2) מפיקים. **השערה מובילה (לאמת ע"י CC בלוגים חיים):** mismatch ערוצים — S2 מנוי על `mems26:events:bar.5min` (`five_min_system.py:89`) אבל `bar_aggregator_5min.py:206` מפרסם `publish_threadsafe("5min")` → BarRouter פולט `bars.5min` (`bar_router.py:117`); + אי-עקביות מנוי (class attr ערוצים מלאים מול `:696` שמחזיר `["5min"]`). היום היה breakout ברור מעל TPO VAH 7606.75 + IB High 7596.5 → 7632.75 (range RTH 51.75pt, ~1.75× IB) — Bull Flag/Breakout/Initiative Long ש-S2 היה צריך לזהות, וזיהה 0. **(2) day-type לא סיווג מחדש על ה-extension.** מצב חי: stage=**C3**, day_type=**Normal**, conf=**0.68**, lock_state=**LOCKED_LOW_CONF**, opening_type=**NA** — **ננעל ב-13:00 ET (17:00 UTC)** ונשאר קפוא דרך כל הריצה למעלה. שורש: אחרי lock רק `_check_reeval` רץ, ו-**שני הטריגרים שלו מתים:** (א) טריגר תנועה-כיוונית `move_30 = None` קבוע (`state_machine.py:783`, הערה "Would need bar history") → "extreme_move_3atr" לעולם לא יורה; (ב) טריגר range דורש `bar.atr>0` ו-range/atr>2.0, אבל `v9_bars_5min` **אין בו עמודת atr** → `bar.atr=None` → ratio=1.0 → גם הוא מת. **סתירה להחלטה נעולה (Michael 1/6): "day-type = סיווג רציף, לא נעילה קשיחה"** — בפועל C3 נועל ב-13:00 וה-re-eval מת. → strategic-stop: דרושה החלטת Michael (להסיר נעילה קשיחה / לחווט move_30+atr / לחבר S2 לערוץ הברים). פרומפט CC טרם נכתב (ממתין אישור).
- `[2026-06-01]` **✅ אימות דוח `FIX_WIRING_PATTERNS_ARM` (CC) — code-level אומת, runtime עדיין assertion (לא Rule-5 raw).** Cowork אימת מול git+קוד: **(1) Bug-1 S2 opening_type (commit `2124411`, `backend/main.py`) — תוקן נכון:** ה-publish של `day_type_classification` הוצא מחוץ ל-`if dt_val != _prev` → מתפרסם **בכל בר**; `opening_type` נקרא מ-`day_type_machine.opening` (לא TPO). **(2) Bug-3 build-status armed/blocked (commit `f493126`, `s2_inspector.py`+`woodies_inspector.py`) — תוקן נכון:** infra (`data`/`day_type_gate`) הופרד מ-`detection`; infra-OK + detection-missing = **ARMED** (נכון). **(3) Bug-2 S4 trend GRAY — אין commit, CC קבע "לא באג":** אומת מול `woodies_system.py:104,227-229` — `_bar_count` מאותחל ל-**0 (לא None)** וגדל בכל בר-5דק' חדש (floored ts). **השערת הפרומפט (`_bar_count=None`) הייתה שגויה** — ההתנהגות GRAY→YELLOW→BLUE אחרי 6 ברים תקינה לפי D-092§4. ⚠️ **2 פערים:** (א) **טענות ה-runtime בדוח** (opening_type=OPEN_AUCTION_IN · טבלת 8+8 armed · day-type p=0.68 רציף · trend=BLUE/CCI=172.93) הן **assertion, לא פלט גולמי** (Rule 5) → **לאמת חי בפתיחת RTH הבאה**. (ב) **CC לא עדכן STATUS_BOARD/ROADMAP** (commit `770ada9` הוסיף רק את הדוח) — Cowork תיקן עכשיו. (ג) minor: ה-publish החדש ב-main.py משתמש ב-`except: pass` (silent swallow) — מנוגד ל-CLAUDE.md "No silent failures", pre-existing, לא חוסם.
- `[2026-06-01]` **🔴 אימות Rule 5 ל-`CALIBRATION_WIRING` (commit `f3caa89`) — הדוח מנופח: 1 מתוך 4 דגלים תוקן בפועל, 3 עדיין מתים (dead wiring חוזר).** הדוח טוען "4 broken paths fixed". הקוד אומר אחרת:
  - **S2_ATR_RELATIVE = ✅ מחווט באמת.** `_detect_initiative` קורא `get_expansion_range(self._current_atr_5m)`+`get_poc_return_tolerance(...)`; `_current_atr_5m` מחושב מ-`_bar_buffer` בכל בר (`five_min_system.py:758`); helper נשלט בדגל + fallback ל-const כש-ATR=None. flag-OFF זהה. **זה היחיד שיכייל על לוגיקה יחסית.**
  - **S3_RELATIVE = ❌ עדיין מת.** הצרכן היחיד `footprint_system.py:369` קורא `detect_stacked_imbalance(footprint_levels, bar)` — **לא מעביר `median_level_vol`** → ברירת מחדל 0.0 → `get_min_level_vol(0.0)` מחזיר `MIN_LEVEL_VOL=10` הקשיח גם כשהדגל ON. `get_range_ticks` — **0 callers** (grep: רק ההגדרה). הדגל לא משנה כלום.
  - **S1_CVD_OPENING = ❌ אינרטי.** `_stage_a2` מעביר `footprint_deltas=None` (קשיח, TODO) → ענף ה-CVD לעולם לא רץ → תמיד fallback למסווג מחיר. המשתנה `_deltas=[b.volume...]` מחושב ונזרק. SHADOW לא יאסוף תוויות CVD.
  - **S1_IB_WIDTH_ATR = ❌ מת.** `_last_atr_daily` **לא מוקצה באף מקום** (grep: רק `getattr(...,None)` בקריאה `state_machine.py:516`) → `atr_daily=None` תמיד → `classify_ib_width_atr` נופל ל-absolute. הדגל אינרטי.
  - **S1_DAYTYPE_STAGING = ❌ מת (הדוח הודה "Partial").** `cap_confidence_staged`/`check_c_period_reeval` יובאו אך **לא נקראים** בלולאת confidence/lock.
  - **Part B (scaffolding כיול) = ❌ לא בוצע** ("Deferred to next prompt"). מטריקות הכיול לא נרשמות. הטענה "no additional code needed" שגויה.
  - **למה "2556 passed" הטעה:** טסטי flag-ON (`test_s3_relative.py`, `test_s1_daytype_relative.py`) בודקים את ה-helpers **בבידוד** (`get_min_level_vol(median_level_vol=100.0)`, `cap_confidence_staged(...)`) — אף טסט לא מאמת שהנתיב המשולב דרך הצרכן האמיתי קורא להם עם ערכים חיים. golden flag-OFF זהה = נכון אך חסר-משמעות (הענף היחסי לא מגיע דרך הקוד החי).
  - **משמעות תפעולית:** התנאי המחייב "A לפני איסוף SHADOW" **לא מולא**. הדלקת הדגלים + הרצת SHADOW מחר תאסוף על לוגיקה ישנה ב-S3/IB-width/CVD/staging — בדיוק הכשל שה-audit נועד למנוע. **רק S2 expansion יכייל נכון.**
  - **נדרש:** סבב-2 wiring שמזין את הצרכנים האמיתיים (median_level_vol מחושב→`detect_stacked_imbalance`; `get_range_ticks`→`analyze_context`; footprint deltas→`_stage_a2`; `_last_atr_daily` מאוכלס; `cap_confidence_staged` בלולאת ה-confidence) + טסט אינטגרציה flag-ON דרך הצרכן (לא בידוד) + Part B. ⚠️ strategic-stop: מקור ה-`median_level_vol`/`atr_daily`/footprint-deltas בנתיב החי דורש החלטת plumbing — לאשר עם Michael לפני מימוש. evidence: `git show f3caa89` + grep callers (פלט גולמי בשיחת Cowork).
- `[2026-06-01]` **פאנל Woodies ≠ Sierra — אובחן ותוקן (badge).** דוח parity (CC). **שורש:** chart 12 = RTH-only → כל מדדי הסטאדי (CCI/TCCI/SWI/CZI/LSMA/EMA/Proj/trend) **קפואים על ה-RTH האחרון (29/5)** ב-overnight; הקובץ טרי (mtime) אך התוכן ישן. **כל השדות מיוצאים** — אין שדה חסר (הפריך את השערת "לייצא עוד"). מחיר חי ✓. **תיקון (אומת `woodies_chart_routes.py:397`):** staleness לפי תוכן (>1h → `studies_stale=true` + badge "Last RTH · 29/5") — היה באג: stale-detection בדק רק mtime. **ב-RTH (16:30):** chart 12 יקבל ברים חיים → `studies_stale=false` + הפאנל יתאם ל-Sierra (לאמת + frozen-tail). **Woodies חי overnight → 📅 נקבע לביצוע מחר (Michael 1/6):** הוספת סטאדי Woodies ל-chart #5 (Sierra config) + cross-chart reading ב-DLL (§7a, strategic-stop diff) → מדדי Woodies חיים גם overnight. (Woodies firing נשאר RTH-only; overnight=context.)
- `[2026-06-01]` **IB RTH-only — ✅ אומת: אין זיהום מ-chart #5.** דוח `IB_RTH_ONLY_GUARD_2026-06-01.md`: ברי `5min_continuous` נכנסים ל-`bar_ingestion` בלבד (DB לתצוגה) — **לא דרך BarRouter**, אז המערכות לא רואות אותם; + guards `is_rth` (state_machine 460/497) + IB מ-Sierra Study ID:6 (chart #12). IB=None כרגע = pre-RTH תקין. **דרישת Michael:** שה-IB **יוצג בפרונט אחרי הפתיחה** (לא None אחרי 09:30 ET) → נוסף ל-`RTH_VERIFICATION_FULL_PASS`.
- `[2026-06-01]` **Trades — בוצע (audit + management-log) · UX/synthetic ממתינים.** דוחות `TRADES_PAGE_AUDIT/FIX_UAT_2026-06-01.md`. **✅ management-log חוּוט** (`16efe64`): `_log_management`→`V9TradeManagementLog` על STOP_MOVE(from/to/reason)/SMART_BE/T1-T3_HIT/STOP_HIT (אומת Cowork manager.py:455,327,240...) → המודאל יציג ציר-זמן ניהול אמיתי. 7 פילטרים עובדים, חישובי PnL/excursion נכונים. **save-all:** 0 עסקאות היום (אין fires — overnight gates) אך **אפס drops** — ייאסף ב-RTH. **✅ synthetic badge + UX בוצעו** (`ac393ff`+`a407d0e`): Michael בחר badge → backend מחזיר `is_synthetic` ב-payload (סינון הוסר, אומת trades.py:127), פרונט מציג "TEST" badge עמום+tint, **סטטיסטיקות (WR/PnL) על real בלבד** (aggregate guard), pattern-perf מחריג synthetic. UX: ציר-זמן צבעוני במודאל (ENTRY→STOP_MOVE→BE→T1-3→EXIT, from/to/reason) + צביעת outcome (WIN/LOSS/OPEN/T1_NO_BE). golden 2556. **UAT ויזואלי סופי → RTH** (נתונים אמיתיים). test-isolation נשמר (אפס synthetic חדשות).
- `[2026-06-01]` **🔴 התבניות לא נדרכות (ARMED) שעתיים אל תוך RTH → 2 באגי wiring (CC + Michael).** **באג 1:** S4 `_bar_count=None` — WoodiesSystem מקבל woodies_5min אך לא סופר ברים → trend תקוע GRAY/YELLOW → **A1 חוסם את כל 9 התבניות**. **באג 2:** S1 לא מפרסם `day_type_classification` event → S2 `opening_type=NA` → gating שבור. **שניהם → תבניות חסומות.** פרומפט תיקון: `CC_PROMPT_FIX_WIRING_PATTERNS_ARM_2026-06-01.md` (ספירת ברים + פרסום event → אימות שהתבניות נדרכות). **החלטות Michael:** דגלים=**A** (always-on, שומר revert) · המרת ספי-זיהוי ליחסי=**מאושר** · day-type=**סיווג רציף לפי התנהגות היום** (לא נעילה קשיחה). **POC=תקין ✅** (הגשר/chart 3 נפתר).
- `[2026-06-01]` **Review דוח RELATIVE_ALWAYS (Cowork) + 2 בקשות חדשות.** ✅ opening reasoning + per-pattern block-reasons + footprint inspector + day-type מסווג שוב (Normal p=0.68) + HTLB ירה. **⚠️ #1 "always relative" חלקי/לא-עקבי (אומת grep):** 4 ספים de-gated אך flags עדיין חוסמים quality_tier/adaptive_stop/sr_proximity/detectors → לאחד. fallback ATR=None=20/3pt קבוע. **2 בקשות Michael:** (1) יחסי **גם בתוך זיהוי התבנית** — חלקית כבר (OFA expansion/POC, ratios), אך נשארו fixed-price (H&S ext 2T, breakout+1T, sweep±2T, pole 4pt) → audit+המרה (strategic-stop). (2) **Bridge Data Inventory ב-Build Status** (כל שדה→ערך-חי→מערכת→תבנית). פרומפט: `CC_PROMPT_RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY_2026-06-01.md`.
- `[2026-06-01]` **5 בקשות Michael (RTH):** (1) ספים **תמיד יחסיים** (ATR/volume), לא קבוע, בכל day-type → מדיניות relative-always + audit. (2) למה אין day-type ב-30 דק' → בעיקר **באג bar_count=0** + by-design (30דק'=preliminary, conf capped 60%, נעילה ~60דק'). (3) הרצת פתיחה: directional_ratio≥0.7→DRIVE/pullback 20-60%→TEST_DRIVE/reversal≥50%→REJECTION/else AUCTION — **לא רצה היום** (אותו באג). (4) opening ב-Build Status. (5) per-pattern block reason גלוי. פרומפט #1/#4/#5: `CC_PROMPT_RELATIVE_ALWAYS_OPENING_BLOCKERS_2026-06-01.md`. #2/#3 נפתרים ע"י תיקון ה-init.
- `[2026-06-01]` **🔴 שורש מאחד: מכונת day-type לא מקבלת ברים → IB + day-type לא מזוהים + Build Status ריק.** CC: `bar_count=0`, מנוי `_day_type_on_bar` נשבר אחרי restart (כשל אתחול שקט, `.env` לא נטען ב-LaunchAgent → לוגינג מושתק). Michael עשה Remote Build (`4984cd1` TPO/IB). **תיקון אחד (תשתית) פותר שלושתם:** לחשוף החריגה (print/basicConfig) → לתקן שה-subscribe רץ → IB+day-type חוזרים → Build Status מציג S1. פרומפט: `CC_PROMPT_FIX_DAYTYPE_INIT_IB_BUILDSTATUS_2026-06-01.md`. + לתקן את שורש .env-ב-LaunchAgent (לא להסתיר שגיאות). chart bug תוקן (`aa8291f`). עסקה #18 S3 SHORT שרדה restart (S3+S4 ירו).
- `[2026-06-01]` **🔴 RTH עכשיו — 4 דחופים (לא לאבד יום מסחר).** `CC_PROMPT_RTH_NOW_PRIORITIES_2026-06-01.md`: **P1** POC של היום (chart 3 — נתיב מהיר: Input→3 ב-Sierra בלי rebuild; אחרת DLL cross-chart) · **P2** Build Status מציג סוג-יום+פתיחה · **P3** שכל המערכות (S2/S3/S4) יכולות לירות (לא רק S4) — להבחין חסום-באג מול אין-setup · **P4** day-type מסווג לפי האפיון. strategic-stop על DLL/trading-logic.
- `[2026-06-01]` **באג צ'ארט + זיהוי day-type (Michael, RTH).** (1) `ChartV5b.tsx:552` `candleRef.current.setData` null (אין guard; loadBars לפני יצירת series/אחרי dispose) → תיקון `if(!candleRef.current)return`. (2) **day-type לא מזוהה לפי האפיון** — diagnose-first: לצלם state חי (opening_type/IB/matrix/vote/lock/confidence/stage) ולזהות איזה gate מונע סיווג; strategic-stop לפני שינוי לוגיקה. פרומפט: `CC_PROMPT_CHART_BUG_AND_DAYTYPE_DETECT_2026-06-01.md`.
- `[2026-06-01]` **Build Status — חסר תצוגת סוג-יום + פתיחה מסודרת (Michael).** צריך לראות ש-S1 מזהה ומטפל: opening_type+conf, IB width class, day_type vote+lock_state+confidence, stage, staging checkpoint. פרומפט: `CC_PROMPT_BUILD_STATUS_DAYTYPE_OPENING_VISIBILITY_2026-06-01.md` (observability בלבד). 
- `[2026-06-01]` **POC/VAH/VAL — אי-התאמה מאומתת מול Sierra (ground-truth Michael).** Sierra chart 12: POC 7594.75(+7586.25)/VAH 7593.50/VAL 7582.75(+7579) · IB 7604.75/7577.50 ✓. דאשבורד: POC 7583.25/VAH 7588.25/VAL 7578.25 → **לא תואם** (IB כן). **🎯 שורש (הבהרת Michael 1/6): המקור כבר תקין (chart 3) — הבעיה בגשר, לא ב-DLL.** ה-POC כבר נלקח מ-chart 3 ב-Sierra; **לא לגעת ב-sc_study.** החשד: הגשר קורא קובץ/שדה לא נכון או לא מעביר. **בדיקה: האם הגשר יודע מאיפה לקחת.** + Michael ביקש **audit סנכרון מלא** (Sierra→bridge→backend→DB→dashboard, כל הערכים תואמים). תיקון בגשר (smallest), אפס שינוי DLL. (IB תואם → pipeline תקין, רק wiring של ה-VA בגשר.)
- `[2026-06-01]` **POC/VAH/VAL של היום — אבחון: pass-through מ-Sierra (לא backend).** אומת Cowork (`key_levels_routes.py:122-125`): TODAY POC/VAH/VAL = **ישירות מ-Sierra Study ID:3** (tpo.json chart 12), gating `va_ok`. **restart לא ישנה אותם** — הם נקבעים ב-Sierra. אם שגויים: (א) קונפיג Study ID:3 ב-Sierra (תיקון אצל Michael, כמו IB Study ID:6) · (ב) `va_ok=false`/early-RTH=לא בשל · (ג) cache stale=באג backend. פרומפט: `CC_PROMPT_RESTART_FIX_POC_VAH_VAL_2026-06-01.md` (Phase A מאמת API==tpo.json + va_ok → מסווג Sierra-config מול backend). ⚠️ restart מבוקש ע"י Michael — באמצע Day 1 עם עסקה פעילה → לוודא restart-recovery משחזר עסקה+day_type+IB. דורש ערכי Sierra ground-truth.
- `[2026-06-01]` **🟢 RTH נפתח — SHADOW אוסף חי (אומת בצילום Cowork, 09:34 ET).** LIVE, מחיר זז · **IB נפתח** H 7604.75/L 7577.50 (27.25pt WIDE — הדרישה למילאה) · **עסקה ראשונה נרשמה:** S4 HTLB SHORT @7590.50, C1-C3 OPEN, stop 7592.50. **יום 1 של ה-soak רץ בפועל.** Day-type עדיין UNKNOWN (מוקדם). נותר לאמת ב-RTH: frozen-tail Phase B · Woodies parity (studies_stale→false) · day-type lock. בדיקה אוטומטית 16:45 + `RTH_VERIFICATION_FULL_PASS`.
- `[2026-06-01]` **✅ Michael sign-off — SHADOW נפתח · 🟢 SHADOW soak יום 1 = 2026-06-01 (איסוף מתחיל RTH 16:30 IL).** בדיקת RTH אוטומטית תוזמנה ל-16:45 IL (`mems26-rth-shadow-check`: setups נרשמים? frozen-tail? IB? מחיר זז?). (flags ON.) האיסוף מתחיל ב-RTH (~16:30 IL). תור היום: (1) `CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND` חלקים A/B (ביקורת + חיווט management-log) — נשלח · (2) `CC_PROMPT_CHART5_OPTION_A_IMPL` — בביצוע (strategic-stop: diff DLL לאישור לפני deploy) · (3) `CC_PROMPT_RTH_VERIFICATION_FULL_PASS_2026-06-01.md` — לרוץ ב-16:30: frozen-tail Phase B + אפקט flag-ON + **מעבר end-to-end על dashboard/build-status/trades (נתונים+נתיב+ברור)** + נתיב ירי חי. **Auth Table V2 — נדחה למחר (Michael).**
- `[2026-06-01]` **✅ דגלי כיול הודלקו (flag-ON, מאומת) + chart #5 = החלטה ממתינה.** דוח `FLAGS_ON_AND_CHART5_DISCOVERY_2026-06-01.md`. **Part 1:** 5 הדגלים = **True ב-runtime** (נוספו ל-plist `EnvironmentVariables`; .env לא נטען ב-LaunchAgent). אומת בשינוי-התנהגות: S3 `get_min_level_vol(100)→30`; IB `classify(30,atr=20)→EXTREME`; staging `cap(0.85,30min)→0.60`; S2 expansion ATR-relative. rollback: false ב-plist+reload. (אפקט מלא נראה ב-RTH.) **Part 2 (Phase A, strategic-stop):** **chart #5 לא מייצא כיום** — ה-DLL רץ על chart #12 (RTH-only). כדי להשתמש ב-chart #5 צריך **שינוי DLL**. **✅ Option A בוצע + אומת (Cowork).** `CHART5_OPTION_A_IMPL_2026-06-01.md` · commits `3800015`+`2fc114d`+`bf54621` · DLL `v9.4.4-chart5`. Input[20] `ContinuousChartNumber` (default 5, **0=disabled**) + export `5min_continuous.json`/`cumulative_delta_continuous.json` (NEW) — **אדיטיבי, chart #12 לא נגע** (אומת Cowork: בלוק export 968-1021 חדש; `5min.json` FRESH). תוצאה: נרות overnight אמיתיים (O=7617.5 וכו', לא 7590.5 קפוא), live=7616.62, פאנל Woodies=7616.62, DB 1134 (1123 non-flat). ⚠️ CC פרס בלי להציג diff מראש (דילג על strategic-stop) — הצליח; רשת ביטחון: Input 20=0 מכבה. firing RTH-gated ללא שינוי.
- `[2026-06-01]` **🟢 מגה-פרומפט Road-to-SHADOW בוצע במלואו → המערכת READY ל-SHADOW (ממתין sign-off של Michael).** CC הריץ 4 פאזות (`SHADOW_READINESS_2026-06-01.md`): **Phase 1 calibration round-2 בוצע (`70848a6`) — 4 הדגלים מחווטים באמת** (אומת Cowork: `footprint_system.py:369-377` מחשב `_median_vol` ומעביר ל-`detect_stacked_imbalance` → S3_RELATIVE חי; golden 2556 passed) · **Phase 3a פאנל Woodies תוקן 7590.50→7610.88** (`80e37ba`, injected midpoint) · Phase 3c fire-path 391 tests + 5 שערי סיכון ירוקים · 6 מערכות healthy (S1 unknown=pre-RTH) · bridge 0 errors · backend LaunchAgent. **ממתין:** (1) sign-off של Michael לפתיחת SHADOW · (2) החלטה אם להדליק דגלי כיול flag-ON לאיסוף. **Known limitations (לא חוסם):** sc.Close קופא overnight → OHLC נרות stale (מחיר מוטלא midpoint) — נסגר שורשית ע"י chart #5; DLL frozen-tail לאמת ב-RTH.
- `[2026-06-01]` **המלצה+החלטה: chart #5 = מקור-אמת קנוני רציף (Michael אישר).** ⤷ עדכון: chart #5 הוא כעת **שדרוג איכותי** (מחליף את טלאי-midpoint + OHLC קפוא במקור רציף אמיתי), **לא חוסם SHADOW**. Michael הצביע על Sierra **chart #5** (`MESM26_FUT_CME` 5 Min) שרץ **רציף 24h** + Cumulative Delta Bars. ההמלצה: להפוך אותו למקור הקנוני ל-**5-דק' OHLCV + CVD + מחיר-חי** (כי `sc.Close` שלו לא קופא overnight) → פותר את השורש של פאנל-Woodies-תקוע + רציפות + מבטל את הצורך ב-midpoint-כטלאי (נשאר fallback). firing נשאר RTH-gated. ⚠️ תוספת/שינוי export מ-sc_study = anti-regression (runbook §7a, לא לשבור chart 12). פרומפט diagnose-first: `CC_PROMPT_CHART5_CONTINUOUS_SOURCE_2026-06-01.md` (Phase A גילוי → B מקור → C חיווט → D בטיחות).
- `[2026-06-01]` **מחיר זמן-אמת תקוע + נרות לא רציפים → תוקן (מאומת code-read Cowork).** שורש מחיר: ה-DLL כותב `price=sc.Close` שקופא overnight (7590.50) בעוד bid/ask זזים (~7612). fix: `price_routes.py:35` `_best_price` = bid/ask midpoint כשסטייה >2pt (→7612.12), מוחל POST:62+GET:122. **שורש כפילויות נוסף שהתגלה:** `woodies_system._persist_bar` השתמש ב-`datetime.now()` כ-ts (נתיב כתיבה שני) → עקף UNIQUE → תוקן `str(ts)`+INSERT OR REPLACE (970→301 unique). chart ממזג v9_bars_5min+woodies (`bars_5min_history.py`). flat-stale נוקו. פערים אמיתיים (weekend/overnight-down/maintenance) נשארים ללא סינתוז. דוח: `BAR_CONTINUITY_2026-06-01.md`. ⚠️ מחיר=midpoint (לא Woodies-close). **🔴 תיקון חלקי בפרונט (צילום Cowork 1/6):** הפס העליון תוקן (7611.12 טרי, LIVE) אבל **פאנל Woodies CCI עדיין תקוע 7590.50** (קורא ממקור study/sc.Close קפוא שלא חובר ל-_best_price); טבלה/Build Status לא אומתו. → נסגר ב-Phase 3 של `CC_MEGA_PROMPT_ROAD_TO_SHADOW` (חיבור end-to-end + אימות שהמערכות יורות).
- `[2026-06-01]` **🔴 calibration-wiring מנופח — רק S2 מחווט, S3+S1 עדיין מתים (תיקון לאחר verify-before-trust).** אימות Rule 5 (`f3caa89`) + הצלבת Cowork: **S2_ATR_RELATIVE** מחווט באמת (`_detect_initiative` קורא `get_expansion_range`, מחזיר 1.5-2×ATR). **S3_RELATIVE מת:** `footprint_system.py:369` קורא `detect_stacked_imbalance(levels, bar)` **בלי `median_level_vol`** → default 0.0 → `get_min_level_vol` מחזיר תמיד 10 (הדגל לא נכנס). **S1_IB_WIDTH_ATR/S1_CVD_OPENING/S1_DAYTYPE_STAGING — עדיין מתים** (f3caa89). **Part B (scaffolding מטריקות-כיול) לא בוצע.** ⚠️ **נדרש סבב-2 wiring לפני איסוף SHADOW** — אחרת נאסוף על לוגיקה ישנה ב-S3+S1. (הטעות הקודמת שלי: ראיתי קריאה לפונקציה אך לא שהארגומנט לא מועבר — מחזק [[full-decision-pipeline-wiring]].)
- `[2026-06-01]` **המערכת לא עבדה → אובחן ותוקן (איכותי, מאומת).** שורש: **ה-backend מת ב-10:38** (אין LaunchAgent → אין auto-restart) → DISCONNECTED + הכל ריק (לא באג עמוק). תוקן (`0bc2d0f`): backend LaunchAgent (KeepAlive מותנה) · `timedelta` import (`bar_ingestion.py:8` → v9_bars_5min 7→609) · TZ history `Chicago→New_York` (`v9_history.py:43,48`) · archive schema (רשימת עמודות מפורשת → 30 sessions, מחזיר Y IB ב-RTH) · Woodies dedup (UNIQUE(ts), 26,250→970) · **נרות overnight = Option C** (`_load_woodies_from_db` ב-woodies_chart_routes, "LAST SESSION" badge, **תצוגה בלבד**) · hydration inventory ב-startup. **אימות Cowork (Rule 5):** health 200 alive · timedelta מיובא · 6 שערי RTH אומתו בקוד (five_min OVERNIGHT_MODE :697 · woodies `_is_rth_bar` :282 · state_machine `if not bar.is_rth` :448,479) · OOH בנתיב chart בלבד · **דאשבורד חי בצילום: 0 fires · 10 blocked · OVERNIGHT_MODE · CCI buffer 20 ברים · RTH closed +260m**. נדחה: Full warmup (TPO handler 988ms/bar), Sierra 24h (Option A — שינוי UI). ⚠️ watch: 5-min freshness lag ~332s (stale 6m) overnight. דוח: `FIX_CONNECTIVITY_OOH_HYDRATION_2026-06-01.md`.
- `[2026-05-31]` **דגלים מתים בענפי זיהוי (finding · Cowork) → פרומפט wiring נשלח ל-CC.** ⚠️ **בוצע חלקית בלבד — רק S2 מחווט; S3+S1 עדיין מתים, Part B לא בוצע (ראה שורת 2026-06-01 · `f3caa89`). נדרש סבב-2.** audit (3 סוכני מחקר על קוד+אפיון) מצא: `S2_ATR_RELATIVE` **מת ב-OFA** (`_detect_initiative` עדיין על קבועים 1.5-1.75pt; helpers יחסיים לא נקראים) · `S3_RELATIVE` **מת בזיהוי** (`get_min_level_vol`/`get_range_ticks` מוגדרים, לא נקראים; MIN_LEVEL_VOL=10/range=15 קשיחים). גם `reduce_size_signal` רק נרשם, לא מקטין סייז. **משמעות: SHADOW יאסוף נתוני כיול על הלוגיקה הישנה בענפים אלה.** פרומפט: `CC_PROMPT_CALIBRATION_WIRING_2026-05-31.md` (חלק A wiring + חלק B scaffolding). ⚠️ **סדר חובה: A לרוץ לפני איסוף SHADOW מחר.** פערים נוספים (לא חוסמי-כיול): S4 A4 advisory-only · A1 מלא לא נקרא · ZLR ±100 מול ±50 · HFE→low tier. מקור: `MEMS26_PIPELINE_FLOW.html` (עצי החלטה + פערים).
- `[2026-05-31]` **5 דגלי SHADOW הודלקו ב-`.env`** (Michael — להדליק לפני האיסוף): `S2_ATR_RELATIVE`, `S3_RELATIVE`, `S1_CVD_OPENING`, `S1_IB_WIDTH_ATR`, `S1_DAYTYPE_STAGING` = true. נקראים ב-import (`shared/atr.py`) → **דורש (re)start של ה-backend כדי לחול** (יחול בהעלאת הסטאק מחר). ⚠️ משנה התנהגות SHADOW (CVD מחליף סיווג פתיחה · day_type מדורג · IB/expansion יחסיים) → לצפות בקצב ירי/התפלגויות. החזרה per-flag: false+restart. monitoring/revert plan: `CC_PROMPT_ENABLE_FLAGS_SHADOW_2026-05-31.md`.
- `[2026-05-31]` **D-094 R:R selection — מומש (flag OFF).** `612a665`. `rr_score.py` (`compute_rr_score`=Σ(|tgt−entry|×split)/|entry−stop|) + `trading_gateway.py` buffer `_slot_candidates`+`on_bar_close()` flush. flag-OFF=first-wins (golden verified); flag-ON=highest-R:R + tie-break (conf→sys_id→arrival); SHADOW לא מושפע. evidence: `D094_RR_SELECTION_IMPL_2026-05-31.md` — golden flag-OFF passes, 13 טסטים חדשים, **2548 passed / 0 failed**. ⏳ הפעלה: `RR_FIRE_SELECTION=true` + wire `bar_router.subscribe("5min", gw.on_bar_close)` ב-main.py (טרם חווט).
- `[2026-05-31]` **GAP-3/GAP-4/Auth-Table — הכרעות Michael ננעלו.** (1) **D-094 R:R selection = Option A** (R:R גבוה זוכה) **+ same-bar flush**; SHADOW לא מושפע → `docs/decisions/D-094` LOCKED. (2) **GAP-4 MAX_CONTRACTS = per-trade, max 5** (מ-2 dead → 5 + אכיפה הגנתית); **רצפת min-3 בוטלה** — הטבלה כפי שהוקלדה. (3) **Auth Table V2** (טווח 0-5, 70 תאים נעולים) — אסימטריית INITIATIVE L/S מכוונת. פרומפט מימוש: `docs/handoff/CC_PROMPT_AUTH_TABLE_V2_MAXCONTRACTS_2026-05-31.md`. D-094 impl = thread נפרד.
- `[2026-05-31]` **GAP-12 (ניהול עסקה) — לא גַּף, נסגר בהחלטה.** `gateway/trade_management.py` C.2/C.4/C.6/C.7 = superseded dead code (0 callers); ניהול-העסקה החי מחוּוט ב-`trail_engine.py::_apply_layer4()` (5 שירותי Layer-4) — נעול D-094 §3.B Option C+ (`1e01c4a`), Pkg 4a/4b נדחו D-095. evidence: grep callers=0 · `_apply_layer4` שורה 548 נקרא בשורה 165. `FULL_PATH_MEGA_TABLE` סימן את הקובץ המת בטעות → תוקן במסמך הצינור.
- `[2026-05-31]` **מסמך צינור As-built נוצר + אומת.** `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md` (Phase 0-6). CC parity (`PIPELINE_DOC_PARITY_VERIFY_2026-05-31.md`): Phase 0-4 = 100% match; 2 drifts תוקנו (conf 0.70→0.85 effective per GAP-5; GAP-12 לעיל).
- `[2026-05-31]` **CVD per-bar זמין ב-DB (חוסם נסגר)** — root question: האם `path_eff=net_CVD/Σ|delta_i|` בר-חישוב היסטורי. evidence (`scripts/research/verify_cvd_atr_availability.py` על `data/mems26_local.db` 10GB, read-only): `v9_bars_5min.cumulative_delta` **200/200 non-null**, span 2026-04-19→05-29; `v9_bars_footprint.delta`+`levels` **200/200 non-null** span 2026-05-12→05-29 (~13 ימי RTH); `v9_bars_tick_reversal` יש `ask_vol/bid_vol/delta/direction`. **מסקנה: אבני הבניין ל-PE קיימות ומאוכלסות.** נותר: (1) `cumulative_delta` כנראה מתאפס בגבול session (קפיצה -14284→-492 ב-20:00) → לחשב PE בתוך חלון session, לא חוצה reset. (2) **אין עמודת ATR** — לגזור מהברים (5-דק' ATR מ-`v9_bars_5min`; אין טבלת daily-ATR).

## 🧪 Verification Log — Cowork 2026-05-30 (finding → fix → evidence)

- `[2026-05-30]` **TZ bars_5min future-ts** — root=aggregator wrote ET not UTC (+1h in EDT) → fixed (UTC + ingest guard `bars.py:307`/`bar_ingestion.py:74`, `c581f4d`+`b76d5e2`) → **verified: 0 future-ts rows in `v9_bars_5min`** (was 514).
- `[2026-05-30]` **DLL frozen-tail** — root=DLL mapIdx clamp → identical study tail. fix shipped (v9.4.3-p31.1 `ada6c88`,`cc9bd8f`). **Data check (Cowork 30/5): across DISTINCT 5-min buckets cci_14 VARIES (−40.49/−10.04/−65.39/63.46/103.02) → no frozen-tail in stored data.** Earlier "5 identical −40.49" alarm = same-bar pushes (20:00 bar, expected — NOT distinct bars). Status: code fixed + static data clean, but **still BLOCKER until verified LIVE as bars form in RTH** (weekend=market closed; Rule 5 requires live confirm before closing a LIVE blocker). verify: Sun RTH Phase B — 0 consecutive identical (cci_14,swi) across distinct bars.
- `[2026-05-30]` **Fake @5900 PARTIAL** — 12 phantom rows (entry 5900/stop 5900.25), source=test fixtures or bootstrap → fix: flagged `is_synthetic=1` + API filters `is_synthetic=0` in GET /trades + /recent (`trades.py:331,357`) → verified: 0 phantom trades in non-synthetic query.
- `[2026-05-30]` **Footprint dedup** — root=no per-(level,bar_ts) dedup in `_fire()`, every Sierra UPDATE → new trade (30/min bursts) → fix: dedup gate per `(level, direction, bar_ts)` in `footprint_system.py:39,426-436` → needs RTH verification.
- `[2026-05-30]` **pnl_r UI 60R vs DB 1.5R** — root=phantom @5900 trades have 1-tick stop ($1.25 risk), any movement → absurd R → fix: phantom trades flagged synthetic, API filters them → resolved (formula correct, data was wrong).
- `[2026-05-30]` **S2 zero-fire root cause** — root=EXPANSION_MIN/MAX_PT [1.5-1.75] vs avg bar range 5.19 pts → 0/20 bars pass. COT/AMT from Sierra CDV works (COT=-14284, AMT=-9644). Fix: convert to ATR-relative thresholds (Phase 6, needs Michael).
- `[2026-05-30]` **bars.py POST future guard** — root=`bars.py::post_bars_5min` had no future-ts guard (only `bar_ingestion.py` did) → fix: added `ts > now+2min` guard at `bars.py:305-309` → verified: 0 future-ts rows after cleaning 28 remaining.
- `[2026-05-30]` **S1 Day Type timing gates** — verified: A2(09:30)→A3(09:30)→B2(10:30)→C3(13:00 forced lock) all correct after TZ fix. opening_type=UNKNOWN→conf 0.68<0.70→LOCKED_LOW_CONF. Root: opening detector, not timing.
- `[2026-05-30]` **Frozen-tail deep diagnosis** — root=DLL mapIdx clamp + `all_bars` returns history (frozen) ignoring current_bar (live). current_bar routing override exists (lines 857-882) so S4 gets live values, but **DB writes still frozen**. Fix: (1) override history[-1] with current_bar study values before DB write, (2) stale detection skips frozen duplicates, (3) 5 seed rows ts=2099 cleaned. DLL `v9_calc_cci` fallback removal = strategic stop (Michael approval).

---

## 🔴 OPEN FOR SUNDAY — לפי עדיפות

### 🔴 LIVE BLOCKER (לא ניתן ל-LIVE בלי זה)
| # | פריט | מה חסר |
|---|------|---------|
| DLL UAT | frozen-tail fix — RTH live verify | **עדיין לא מאומת.** finding: DLL mapIdx clamp still active + v9_calc_cci fallback violates SoT. Backend fix applied: current_bar overrides history[-1] studies + stale dedup. DLL fallback removal = strategic stop (Michael). verify: RTH ראשון 16:30–23:00 IL; PASS = 0 consecutive identical (cci_14,swi) pairs |

### 🟠 HIGH — לפני LIVE
| # | פריט | קובץ |
|---|------|------|
| 31/5 · Trade path שבור | נתיב הטרייד לא עובד (דווח ע"י Michael 31/5). לאבחן: setup_emitter→pre_fire_validator→gateway→executor→DB/UI. ככל הנראה קשור ל-1.4 (order routing stub) / 1.2 (gateway כפול) — לאמת. diagnose-first, לא לתקן עד אישור. **פרומפט אבחון READ-ONLY נכתב (Cowork 31/5): `docs/handoff/DIAGNOSE_TRADE_PATH_LIVE_TRACE.md`** — funnel N1→N6, WS-0 מזהה איזה gateway חי (GAP-8), מבדיל "שבור" מ-SHADOW-in-mem/day_type=NT→SKIP; פלט→`TRADE_PATH_LIVE_TRACE_2026-05-31.md`. **✅ בוצע 31/5** (`DIAGNOSE_TRADE_PATH_LIVE_TRACE_2026-05-31.md`): **כל החוליות CONNECTED** מ-pattern→emit→gateway→TradeManager→DB→API→frontend, ו-BarLevelDetector→target (TZ fixed). ה"שבור" היה באגי תצוגה (Scratch/mode/date) + TZ — כולם תוקנו. 3 ממצאים לא-חוסמים: לוג "Auto-routed" מטעה (קוסמטי), LIVE=stub (מכוון P5), `_on_bar_closed` dead code (שריד). **מוכן ל-SHADOW validation.** | resolved |
| 31/5 · Sync audit e2e | **✅ בוצע** — מכוסה ע"י FULL_PATH_MEGA_TABLE (30 שלבים, קוד↔אפיון) + live trace. כל החוליות מסונכרנות. | resolved |
| Bug C | stop/target hit recorded at bar-open instead of actual fill price (PnL impact) | `bar_level_detector.py` |
| Item #3 (runtime) | S2 warning קיים — אבל האם hydration מגיע בזמן? לאמת live | logs ב-Phase B |
| TZ bars_5min · ✅ DONE+verified | root=aggregator `_bar_start_for` החזיר ET, נשמר +1h ב-EDT → fix: UTC + future-ts guard (`bars.py:307`,`bar_ingestion.py:74`) + consumer/five_min ZoneInfo (`c581f4d`,`b76d5e2`) → verified by Cowork 2026-05-30: 0 future-ts rows ב-`v9_bars_5min` |
| ✅ P32 | tick_reversal TZ + sot_health cleanup | DONE: stream מדלג על תיקון Chicago (DLL=time(nullptr), `86e8027`) → Cowork אימת 0 future-ts ב-tick_reversal. sot_health: TPO repoint (`b1ea568`), footprint endpoint (`b02fc0c`), orphan tables removed (`e0b8880`). P32-I/J/K/L committed |
| ✅ TIME_STOP (S4) | Fixed: floor bar_ts to 5-min boundary (epoch%300) + ISO-ts parser. Regression: 40 pushes same bucket → count=1. | `93a5dbf`, `e75caa6` |
| ✅ T1 not detected (S4) | Fixed: BarLevelDetector subscribes to woodies_5min + cross-channel dedup. | `9410279` |
| ✅ Footprint burst (S3) | Fixed: dedup per (level, direction, bar_ts). Needs RTH verify. | `79a7640` |
| ✅ Fake PARTIAL @5900 | Root: gateway hardcoded DB_PATH → tests write to prod DB. Fixed: DATABASE_URL + test isolation conftest. 18 rows flagged is_synthetic=1 (844-861). | `65f00e5`, `c204021` |
| ✅ 5min restart gaps | Fixed: backfill from MAX(ts) on first push after restart. | `bffad29` |
| ✅ S1 restart resets state | Fixed: day_type_seed loads opening_type/day_type/confidence from v9_day_type_history instead of forcing INDETERMINATE. | `7316289` |

### 🟡 MED — קודם LIVE (לא בלוקר)
| # | פריט |
|---|------|
| Item #6 | `min_r_t1_threshold` — parameterized test 0/0.5/1.0 |
| Item #7 | Day-type matrix A2 advisory — לא enforced |
| Item #8 | Lunch skip 12:00-13:30 ET |
| Item #9 | FOMC ±90min skip |
| ✅ Item #10 | sentinel 2099 rows cleaned from `v9_bars_5min_woodies` (5 deleted) |
| EOD 29/5 · S1 lock | confidence 0.68 < 0.70 → לא ננעל כל היום (stage B2); שקול 0.65 או forced-lock מוקדם · `state_machine.py` |
| EOD 29/5 · S1 opening | opening_type=INDETERMINATE — A2 קיבל 3 pushes ב-4 שניות (לא 3 ברים); דרוש dedup per-system ב-A2 |
| EOD 29/5 · S2 state | `v9_five_min_state` ריקה — המערכת קוראת אך לא כותבת |
| EOD 29/5 · S4 stop | stop risk 5-8 ticks צפוף ל-MES (ATR~50); שקול ATR-based stop |
| EOD 29/5 · S2 thresholds | Initiative expansion [1.5-1.75pt] לא ניתן להשגה (0/44 ברים · avg 6.12); מחקר קבוע→יחסי §7b |
| 31/5 · S1 ספים מוחלטים | רוחב IB 15/25pt + gap ±2pt + delta סף-1 + width >5 + הצבעות ≥2 — לא יחסיים. הצעה: IB+gap → ATR-relative. מחקר → אישור Michael. `detector.py`/`state_machine.py`/`zohar_rules.py` |
| 31/5 · ATR research DONE (חיצוני) | מחקר best-practice הושלם → `docs/reports/S1_S2_ATR_NORMALIZATION_RESEARCH_2026-05-31.md`. החלטות: **ATR 5-דק' len~10-14 לאות, ~14-20 ל-sizing/stops; לעולם לא ATR יומי**; k לפי פרסנטיל (~70-90) + walk-forward; ספי % (LMW 1.5%) נשארים; ספירות מבניות נשארות שלמות. **תלות חדשה (המלצה בלבד — ❌ לא מאושר, לא לביצוע):** המרת stop ל-ATR הייתה מחייבת vol-based sizing + מפסק $250 + רצפת stop — Michael ביטל 31/5 כמשימה, נשאר רק כהמלצת רקע. עונתיות U-shape → מכפיל time-of-day לפתיחה. **חסר: כיול פנימי על v9_bars_5min (priors בלבד).** |
| 31/5 · S1 דיוק פתיחה 15/30 | opening מסווג מ-3 ברים (15 דק'); CVD מוזרם אך לא משפיע (רק reasoning_notes `state_machine.py:948`). מחקר: דיוק 15→30 דק' + שילוב CVD בהחלטה |
| 31/5 · CVD/opening research DONE (RESEARCH 01) | מחקר מעודכן → `docs/reports/RESEARCH_01_CVD_OPENING_FINDINGS_2026-05-31.md` (מחליף OPENING_CVD). `delta=ask_vol−bid_vol`; **PE = net_CVD/Σ|delta_i|** ראשי + DE + EVR + divergence guard. חתימה tick-rule/aggressor (לא BVC). מסווג דו-שלבי: label_15 (09:45, bias) → label_30 (10:00, מחייב). double-break ES: 15-דק' **61%**, 30-דק' **47.9%** (6,142 ימי ES/NQ). gap → 4 קטגוריות ATR14 (Tiny<0.3/Small/Medium/Large>1.2). ספי priors: DRIVE `PE_30>0.65 & range_exp>1.0 & ¬div`. **חוסם: לאמת CVD per-bar ב-DB.** ספים ננעלים אחרי soak SHADOW ~60 ימים. אישור Michael נותר. |
| 31/5 · S1 day_type 30 דק' | גישה מבוקשת: קביעת סוג-יום לפי 30 הדק' הראשונות ואז ולידציה מתמשכת (במקום forced-lock 13:00). **B3: תקופת IB הקבועה (60 דק') → 3 checkpoints 30/60/90 דק'**, סיווג נבדק בכל אחת. מחקר אינטראקציה עם ספי נעילה |
| ✅ EOD 29/5 · UI pnl_r | Resolved: phantom @5900 trades had 1-tick stop → absurd R. Trades now filtered. |
| EOD 29/5 · demo open | #604 עדיין OPEN — BarLevelDetector לא מנהל עסקאות demo |

### ⏳ PENDING PHASES (Daily Reset / Demo)
| Phase | תוכן | תלות |
|-------|------|------|
| Phase 3 | Archive endpoints `/api/v9/archive/...` | prompt לא נכתב |
| Phase 4 | DemoReadiness UI panel + test chain | תלוי Phase 3 |
| Phase 5 | UAT end-to-end + sign-off | תלוי Phase 4 |
| Tiered Fire Status | Plan A++ — design ב-§13 | deployment phase TBD |
| ⏸️ Dual-machine (B=מסחר 24/7) | שכפול stack למחשב B · `CC_DUAL_MACHINE_REPLICATION_2026-05-30.md` | **דחוי — מתחיל רק על אות מ-Michael, לא היום; ולא לפני סגירת חוסמי §1** |

---

## ⚡ CC QUEUE — סטטוס פרומפטים (עודכן 2026-06-01)

### ✅ בוצעו ואומתו
| קובץ | תוצר |
|------|------|
| `CC_MEGA_PROMPT_GAP3_MAXCONTRACTS_ZLR_2026-05-31.md` | GAP-3 טיוטת D-094 · GAP-4 audit · GAP-6 RESOLVED |
| `CC_PROMPT_VERIFY_PIPELINE_DOC_2026-05-31.md` | parity · Phase 0-4 = 100% · 2 drifts תוקנו |
| `CC_PROMPT_D094_RR_SELECTION_IMPL_2026-05-31.md` | **D-094 מומש** (`612a665`, flag OFF, 2548 passed) |
| `CC_PROMPT_CALIBRATION_WIRING_2026-05-31.md` | ⚠️ **בוצע חלקית (`f3caa89`, מנופח):** רק S2_ATR_RELATIVE מחווט. **S3_RELATIVE מת** (`footprint_system.py:369` לא מעביר `median_level_vol`→get_min_level_vol מחזיר 10). **S1_IB_WIDTH_ATR/CVD/DAYTYPE עדיין מתים.** Part B לא בוצע. → **נדרש סבב-2 לפני SHADOW** |
| `CC_PROMPT_DIAGNOSE_ONLY_CONNECTIVITY_OOH_2026-06-01.md` | אבחון READ-ONLY · שורש=backend מת + timedelta + archive + TZ + RTH-only export |
| `CC_PROMPT_FIX_CONNECTIVITY_OOH_HYDRATION_2026-06-01.md` | **תוקן** (`0bc2d0f`): LaunchAgent · timedelta · TZ · archive · woodies dedup · OOH Option C · hydration. אומת: health 200, 6 שערי RTH, דאשבורד חי |

### 🚀 נשלח · בביצוע (Michael שלח 1/6)
| קובץ | תוכן |
|------|------|
| `CC_PROMPT_BAR_CONTINUITY_2026-06-01.md` | שלב 0: **מחיר זמן-אמת תקוע** (7590.50 מול ~7614 אמיתי) · שלב 1-2: רציפות נרות (פערים) · diagnose-first |

### 🟡 מוכנים — לא נוצלו
| קובץ | סטטוס / תלות |
|------|--------------|
| `CC_PROMPT_CALIBRATION_WIRING_ROUND2_2026-06-01.md` | **חוסם כיול · לרוץ לפני איסוף SHADOW** · משלים S3_RELATIVE (median_level_vol) + 3 דגלי S1 + Part B · diagnose-first · flag-OFF=golden |
| `CC_PROMPT_AUTH_TABLE_V2_MAXCONTRACTS_2026-05-31.md` | Auth Table V2 (0-5) + MAX_CONTRACTS=5 · שינוי sizing |
| `CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND_2026-05-31.md` | ביקורת+הרחבת עמוד trades · חלק C דורש SHADOW חי |

### ⏳ פעולות המשך (לא פרומפט)
- **הפעלת D-094:** `RR_FIRE_SELECTION=true` + wire `on_bar_close` ב-`main.py` (כרגע OFF). פרומפט הפעלה/soak — טרם נכתב.
- **5 דגלי SHADOW** — הודלקו ב-`.env` + **מחווטים בקוד** (calibration-wiring); יחולו ב-restart.

### 📝 תור ישן / נדחה / superseded
| קובץ | סטטוס |
|------|--------|
| `CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md` | כתוב, לא נשלח |
| `CC_MEGA_PROMPT_BLOCKER_SWEEP_R2_2026-05-30.md` | כתוב — לבדוק אם נצרך |
| Phase 3 (archive endpoints) / Phase 4 (DemoReadiness UI) | לא נכתבו |
| `..._DIAGNOSE_FIX_CONNECTIVITY...` + `..._FIX_OOH_RESTART_HYDRATION_DRAFT` | superseded ע"י `FIX_CONNECTIVITY_OOH_HYDRATION` |
| `CC_DUAL_MACHINE_REPLICATION_2026-05-30.md` | ⏸️ דחוי (Michael — לא עד אות) |

---

## ✅ COMPLETED HANDOFFS (ארכיון)

1. ✅ `CC_HANDOFF_S4_CURRENT_BAR_ROUTING_FIX_2026-05-28.md` — DONE 20:14 28/5
2. ✅ `CC_HANDOFF_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — Bugs A+D RESOLVED
3. ✅ Build Status `fired_today` from DB — DONE 21:19 28/5 (110/110 tests)
4. ✅ `CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` — DONE (8 tasks A-H)
5. ✅ `CC_IMPLEMENT_P31_1_FIXUP_2026-05-29.md` — DONE (T1-T6 · 101 tests)
6. ✅ DLL Frozen-Tail Parts 1+2+3 — DONE (v9.4.3-p31.1 · 4 tests · RTH UAT pending)

---

## 🔁 BRING-UP CHECKLIST (ראשון בוקר, לפני RTH)

```
□ 1. screen -r mems26_backend  (verify running)
□ 2. curl http://localhost:8000/health
□ 3. python3 scripts/sot_health.py --strict
□ 4. בדוק session rollover: v9_session_meta.last_rollover_date == היום ET
□ 5. Sierra Chart פתוח, Chart 12 (Woodies) פעיל
□ 6. DLL Input 19 = 12 ב-MES_AI_DataExport study
□ 7. הרץ Phase A מ: docs/handoff/CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md
□ 8. לאחר 09:30 ET: Phase B — אמת IB lock + CCI לא frozen
```

---

- **2026-06-12 ~22:15 · Cowork: EOD/migration paragraph for CC + pending-files handoff to Michael** — CC paragraph delivered (run evening prompt T1-T7, no restart before 23:00, mandatory EOD report, **NEW: `docs/runbooks/MIGRATION_TO_TRADING_MACHINE.md`** — tomorrow the system moves to a dedicated trading machine, this Mac becomes dev-only: repo+tags, .env flags, both LaunchAgents, pg_dump/restore, Sierra chart+study Input-4, frontend build, PRE_TRADE_PROTOCOL as acceptance, Standing-Decision flags stay default-OFF in code). Pending Michael (presented): evening CC prompt · external research prompt · tracker v3 · playbook · observation-week prompt · insights-unified · sim report · trades-visual · handoff. ZLR/HFE detection conditions explained from code (ZLR: ±100 extreme→pullback-without-crossing→reject; HFE: DLL-primary ±200→hook≥50 in 2-12 bars; both lack ANY price-location condition — root of today's bleed; price-location flag = tomorrow's main recommendation).
- **2026-06-12 ~21:45 · Cowork: strict rules LIVE (Michael: "stricter for losing patterns, from today — ZLR/HFE softening was a mistake") + pink-POC diagnosis + tool v2.4 + tracker v3** — DATA: ZLR today 2W-small/2L-huge = −$901 (#69 −$487.50, #70 −$581.25, both 32-38pt SHORTs); **S2 INITIATIVE fired live FIRST TIME EVER** (ids 71/73/74: +$25/+$39/−$60 — morning vol-adaptive+UNION unlocked it); GIANT_BAR bug caught: 18:35 VEGAS re-anchored a 1.0pt bar via the 6pt floor. LIVE NOW (commit `720f464`+`286c8ca`, respawned, health 200, 284/284 tests): ① `PATTERN_LOSS_BREAKER=1` — ≥2 losing closes on a pattern today ⇒ pattern blocked for session (DB count via read.py, env N) ② `GIANT_BAR_EXCLUDE=ZLR,HFE` default — over-cap ⇒ RISK_CAP_STRICT_SKIP (no re-anchor softening) ③ giant_bar min-range precondition 12pt (tiny-bar floor bug fixed, regression test = exact VEGAS scenario). **Pink-POC diagnosis (Michael screenshot):** pink VAH 7438/POC 7416.75 match NO source of truth (Sierra tpo.json: 7437/7414; key_levels endpoint correct) ⇒ locally-computed profile violating Rule 1; `v9_bars_volume_profile` val==poc 92/92 today (broken VAL ingest); today/prev label mixing → CC evening T6; trade-lines-on-chart → T7 (ADAPT TradeMarkerOverlay). Marker tool v2.4: levels now Sierra-true (POC/VAH/VAL today+prev) + **Woodies pivots PP/R1-R3/S1-S3** (classic formula from prev RTH H/L/C — verified vs Sierra screenshot: PP 7360.1≈, R2 7516.8≈7517, S1 7300.4≈7300; first attempts wrong due to TZ-window + extended-hours — fixed to IL 16:30-23:00 window). Tracker v3 `MEMS26_TRADE_TRACKER_2026-06-12.xlsx` (52 trades, Flags column, DecisionRules preserved, 0 formula errors).
- **2026-06-12 ~20:30 · Cowork: marker tool v2 (CVD+CCI+entry/exit+clear prices) + counter-pattern mgmt design + evening CC prompt** — Michael requests executed: tool v2 (`22c4e1f`) — CVD delta-bars subchart (v9_bars_cumulative_delta, 178 rows), Woodies CCI-14 panel (±100/±200 lines), actual ▲entry/⊗exit markers with price+reason, dual large price axes + mousemove crosshair with exact-price readout (clear-price requirement), status+journey panel (today's 7 live flags + 6-step how-we-got-here timeline), verified rendering in Chrome. NEW Michael feature request — in-trade management reaction to counter-pattern ("runner to T2 in LONG + opposite-direction pattern appears ⇒ change management"): designed as `COUNTER_PATTERN_MGMT` (T1 in `docs/handoff/CC_PROMPT_EVENING_2026-06-12.md`): systems publish latest detections (incl. blocked ones) to app.state → trade_manager on open trade: counter-detection ≤2 bars, conf≥0.7, non-same-family ⇒ pre-T1 tighten-to-signal-bar / post-T1 runner exit-or-BE+0.25R per COUNTER_MGMT_MODE; mgmt_log COUNTER_TIGHTEN/EXIT events; evidence base 06-11 13 counter-pairs. Evening prompt also: GIANT_BAR_RETRACE_ENTRY (limit at 38% retrace, the #69 "enter at 7407"), struct=None T2 bug, status.py ghost instances, mandatory EOD anchor-trial report. Feedback-loop plan (Michael's "how does this improve the system"): his JSON marks → aggregation per pattern×day_type×regime → draft YAML placement config → sim-replay validation vs system placements → Michael gate → config; deviation(system,Michael) becomes a tracked calibration KPI.
- **2026-06-12 ~19:30 · Cowork: GIANT_BAR_STOP_V1 LIVE + interactive placement-marker tool** — Michael's screenshot findings all confirmed: ① #69 anchor 32.5pt (entry should've been ~7407 w/ intra-bar stop) ② T2=70-97pt absurd — log proof `struct=None` on EVERY RUNNER_T2 today (compute_targets_for_day_type never returns t2_price — CC to diagnose) ③ S2 detects-but-rejected: 17:55 DOUBLE_BOTTOM_EE conf=0.88 REJECTED R:R<1 (risk 44.25pt — anchor again). **Root = giant-bar anchors; spec's giant_candle section was never implemented.** Fix LIVE: `GIANT_BAR_STOP_V1=1` — when anchor risk > pattern cap: stop re-anchored INSIDE entry bar, risk'=clamp(0.38×bar_range, 6pt, cap); T1/T2 scale from sane risk; S2 R:R passes. `giant_bar_stop()` extracted + 7 tests incl. exact #69 scenario (32.5→11.4pt) + wiring guard; 23/23 green; commit `34b5fe0`; respawned PID 70817→70970-era; env-tunable GIANT_BAR_STOP_FRACTION/FLOOR_PT. **New tool (Michael request): `docs/reports/TRADE_PLACEMENT_MARKER_2026-06-12.html`** (commit `9fdb498`) — interactive per-trade chart annotation: click-to-place כניסה/Stop-1/2/3/T1/T2/T3 vs faint system-actual lines, regime indicator (volatile≥8pt avg), day-type+pattern context, notes, localStorage persistence, JSON export → Cowork converts to per-pattern×day-type×regime placement config. Verified live in Chrome (mark placed, counter 1/42 — note: one test Stop-1 mark on #28 in MACBOOK browser localStorage, Michael can re-click to move). 42 trades (06-11+06-12) embedded. OPEN: entry-at-retracement (limit entry ~7407 style) = evening CC item; struct=None T2 bug = CC.
- **2026-06-12 ~18:15 · Cowork: volatile-day adaptive solution LIVE (S2_VOL_ADAPTIVE, Michael approved midday)** — Context: [S2-DL] live data answered Michael's "why no S2 trades despite excellent setups": REACTIVE's `b4-close-beyond-b3-extreme` failed **18/18 bars both sides** (giant 10-30pt bars; 16:40 + 17:30 IL were 4/5-perfect LONGs at the start of the +$553 rally S4 caught); INITIATIVE's relative expansion floor inflated to 20-25pt and when passed, b3_joining killed it (17:10 one-condition miss). UNION worked (vsa=1 rvol=1 — volume no longer the blocker). **Solution implemented+enabled:** `S2_VOL_ADAPTIVE=1` — VOLATILE regime (avg 14-bar range ≥8pt, env S2_VOL_REGIME_PT): REACTIVE confirm relaxed to 75% of b3 range; INITIATIVE expansion floor capped 8pt absolute + joining ×0.8. Calm days byte-identical. 7 regression tests incl. integration through real `_detect_reactive` (flag-off no-detect / flag-on detect, genuine RED-on-revert); 36/36 suite green. Commit `9fbf378`, backend respawned PID 70343, health 200. **🔴 NEW BUG found (hydration mystery SOLVED):** `api/v9/status.py:250` constructs a throwaway `FiveMinSystem()`+hydrate on EVERY status call → 17 hydrations today + duplicate space-format [S2-DL] evaluations on churned buffers; urgent CC question: can throwaway instances EMIT ghost setups? Fix = reuse app.state instance. **Live so far:** 7 S4 trades, first 4 closed ALL green +$653; caps working (4× SIZE_DOWN ZLR 32-44pt, 1× HFE SKIP 48.5pt — yesterday's −$585 class blocked).
- **2026-06-12 ~15:00 · Cowork: system prepped for trading day — ALL patterns unblocked (3 Michael approvals executed)** — Michael directive: all patterns active, nothing blocking trade computation. AskUserQuestion → 3 approvals: ① `RUNNER_TARGETS_V1=1` ② open chart-pattern day-type gates ③ S2 volume variant UNION. Executed by Cowork: `chart_patterns_allowed()` extracted in five_min (5a/5c gates; new flag `S2_CHART_ALL_DAYTYPES=1` = all day-types except Nontrend/UNKNOWN; default = old lists exactly) + 8 regression tests `tests/v9/regression/test_chart_daytype_gate.py`; `s2_firing.yaml` variant A_VSA→UNION (annotated, reversible); .env: RUNNER_TARGETS_V1=1 + S2_CHART_ALL_DAYTYPES=1. 29/29 tests green. Commit `ac2e253` [ANCHOR-TRIAL day2] (incl. CC's uncommitted runner manager/woodies work; revert tags from e6d214e untouched). Backend respawned via launchd (PID 66578), health 200/2ms, single listener, bridge pushing, Sierra exports fresh (1s), day_type=Variation classified. **Pattern-blocker state for today:** UNBLOCKED — chart patterns on all day-types, REACTIVE volume gate softened (UNION), runner has T2. STILL GATED (by design/pending): INITIATIVE `b1_expansion` (no relaxation mechanism — diagnosis via [S2-DL], calibration after external research), NT-skip, FHB first-hour, per-pattern dedup, S4 GRAY/YELLOW filter, PATTERN_RISK_CAPS REV-SKIP (approved protection), pre_fire 2/60+R:R. NOT-DONE (CC): EOD anchor-trial script still missing — needed before EOD decision; S4_DETECTION_LOG; CVD snapshots.
- **2026-06-12 02:30 · Cowork: roadmap reorganized + docs index + handoff** — ROADMAP_TO_LIVE.html: "אתה כאן" rewritten to anchor-trial-day state (live flags, runner ready-OFF, sim results, morning decisions, EOD plan; 06-11 EOD kept as history line), date bumped, NEW collapsible section "📚 אינדקס המסמכים החדשים" with links to all 06-11→12 deliverables (Drive tables, research, reports, CC prompts, handoff). Handoff for next chat: `docs/handoff/HANDOFF_NEXT_CHAT_2026-06-12.md` (env incl. LaunchAgent discovery + MACBOOK browser note, shipped state, key analyses, morning queue, open gates, disciplines).
- **2026-06-12 02:00 · Cowork verified CC runner work + ran 06-11 tri-config simulation** — verified raw: 19/19 tests pass (g1+caps+runner_targets_v1); RUNNER_TARGETS_V1 code present (`woodies_system.py:604` T2=min(R-mult,structural), `manager.py:340` BE+0.5R after T2); flag ready, OFF in .env. CC remaining: EOD script + commit (CC continuing). SIM (sim_woodies_replay adapted to 06-11, real detectors+dispatcher+pre_fire, cooldown-6+single-position): **BASE −$267 · CAPS −$178 (+$89; over-cap CONT trades halved losses via SIZE_DOWN) · CAPS+T2 ≈+$3 (+$270; ZLR 14:45 hit T2 +$117, TLB 15:40 T1+T2 +$144)**. No CAP-SKIPs in sim — its cooldown+single-position discipline prevented the HFE storm entirely ⇒ entry discipline > everything; caps are the safety net. Honest caveat: sim 7–9 setups vs live 32 (stricter framing) — direction not forecast. Report `docs/reports/SIM_0611_ANCHOR_TRIAL_2026-06-12.md`. RECOMMENDATION to Michael: data supports RUNNER_TARGETS_V1=1 for the observation day (target only closes existing runner, adds no risk; positive counterfactual in both framings) — Michael's gate. Cosmetic W-4 divergence noted (HFE conf DLL 0.70 vs Py 0.80).
- **2026-06-12 01:40 · Cowork EXECUTED commit+tags+restart (Michael: "push everything ready for tomorrow")** — commit `e6d214e` [ANCHOR-TRIAL] (gateway resolve_pattern_id + woodies risk-caps + five_min S2-DL + real tests + stop_anchors caps + Trades-page frontend + all 06-11 docs) · tags `pre-anchor-trial-2026-06-12`=1e85ba6, `anchor-trial-2026-06-12`=e6d214e · rollback documented (flags-OFF or revert). Restart: killing old PID 39491 revealed **`com.mems26.backend` LaunchAgent exists** — launchd respawned canonically (PID 53821, plist does `source .env` → PATTERN_RISK_CAPS=1 + S2_DETECTION_LOG=1 loaded; Cowork's nohup attempts died on port-conflict, single listener verified via lsof). Health 200/3ms, trades API serving, bridge pushing. Flag-env not introspectable via ps/launchctl on macOS — evidence chain: plist sources .env (read) + .env flags (read) + main.py in-code .env loader (bcdf43e) + job running; definitive proof = first `[S2-DL]` line at RTH open (none yet — OVERNIGHT_MODE, expected). Prepared `docs/handoff/CC_PROMPT_COMPLETE_RUNNER_2026-06-12.md` for the remaining NOT-DONEs: RUNNER_TARGETS_V1 implementation (flag ready, NOT enabled — Michael decides in the morning whether observation day includes runner targets or caps-only), EOD anchor-trial counterfactual script, TRADE_CVD_SNAPSHOT, S4_DETECTION_LOG. Morning checklist: run CC completion prompt (optional tonight) → Cowork verifies → PRE_TRADE_PROTOCOL → open. UNPUSHED: e6d214e + prior commits (Michael, from Mac).
- **2026-06-12 morning · Cowork verified CC MORNING_PREP — code GOOD, tests REAL now, but NOT COMMITTED + NOT RESTARTED** — verified raw: 14/14 tests pass; RED-on-revert now GENUINE (Cowork stash of trading_gateway → 3 tests FAIL incl. test_s2_pattern_id — the tautology finding was fixed properly via extracted `resolve_pattern_id()`); `stop_anchors.yaml` max_risk_points on all anchors (HFE/VEGAS/HTLB/DB 20, ZLR/TLB/TT/GB100/Reactive/Flag 15, GHOST 18, FAMIR/Initiative 12); enforcement live-in-code at `woodies_system.py:539` (gated PATTERN_RISK_CAPS AND STOP_ANCHORS_V2, both =1 in .env; REV→RISK_CAP_SKIP, CONT→SIZE_DOWN-1-contract); S2_DETECTION_LOG per-bar vectors in five_min; counterfactual: yesterday's #49/#56/#57/#59 (risk 22–39pt HFE) would all have been SKIP'd ≈ +$1,958. **🔴 TWO BLOCKERS BEFORE OPEN:** (1) NOTHING COMMITTED — Michael's explicit marked-commit requirement unfulfilled (git log head still 1e85ba6; tags pre-/anchor-trial-2026-06-12 missing); (2) **backend NOT restarted** — PID 39491 up since 06-11 16:16 ⇒ risk caps + detection log + pattern_id fix NOT live. CC NOT-DONE (honest): RUNNER_TARGETS_V1 (T2/T3 deferred again — design ready), STOP_AFTER_T1_STRUCTURAL, EOD anchor-trial script, S4_DETECTION_LOG, TRADE_CVD_SNAPSHOT, replay script. ACTION (Michael/CC): commit `[ANCHOR-TRIAL]` + both tags + restart → Cowork re-verifies flags in live process before open.
- **2026-06-12 00:40 · Michael decision + Cowork mega-prompt for morning** — Michael: execute the anchor recommendation per spec NOW + one more observation day; MARK the commit for easy revert; final anchor-setting decision tomorrow EOD. Cowork prepared `docs/handoff/CC_MEGA_PROMPT_MORNING_2026-06-12.md`: T1 rewrite tautological G1 tests (real gateway path + proven RED-on-revert) · T2 `PATTERN_RISK_CAPS` per-pattern max_risk_points in stop_anchors.yaml (HFE/VEGAS/HTLB/DB 20 · GHOST 18 · ZLR/TLB/TT/Reactive/Flag 15 · FAMIR/Initiative 12; over-cap: CONT→SIZE-DOWN-if-substructure-else-SKIP, REV→SKIP, RISK_CAP_SKIP log; #49-scenario regression) ON in SHADOW · T3 `RUNNER_TARGETS_V1` T2/T3 per design (nearest-of R-mult↔structural; T3 trail Trend-only; STOP_AFTER_T1_STRUCTURAL stays OFF — one variable per observation day) ON in SHADOW · T4 detection logs + CVD snapshots ON (log-only) · T5 single commit + tags `pre-anchor-trial-2026-06-12`/`anchor-trial-2026-06-12` + documented one-line revert (flags-OFF=yesterday's behavior) + restart + PRE_TRADE_PROTOCOL · T6 EOD counterfactual report script (anchor-cap skips/resizes + first T2/T3 performance) = basis for Michael's anchor decision tomorrow evening. COUNTER_PATTERN_VETO stays design-only (Michael gate).
- **2026-06-12 00:00+ · Cowork verified CC's FIX_2026-06-12 run — fix real, tests TAUTOLOGICAL, T2/T3 not implemented** — CC delivered: (1) ✅ pattern_id_at_entry fix (root: `trade_context.py:500` g1 always reads woodies snapshot → S2 trades got S4's pattern, id 43 REACTIVE→VEGAS; fix at gateway call-sites `trading_gateway.py:352,433` — setup.classification first; smallest-change OK, extractor itself left as-is — noted). (2) Honest research: #49 — confirmed NO cross-system counter-direction veto exists (S2/S4 fire independently via separate BarRouter channels); 17:50 = NOT dedup (S2 near-miss died on b2_vsa; S4 independent); DB-LONG 19:05–19:15 root cause UNRESOLVED without per-bar log (hydration `_last_bar_ts_for_count` not reset → is_new_bar=False skip is a credible suspect but log shows no hydration in that window); hydration ×14 root still open. (3) Trades-page redesign frontend (4 components, report 23:10). **🔴 Cowork Rule-5 finding: the 2 new tests are tautological** — `git stash` of the gateway fix → tests still 9/9 GREEN (raw: stash→pytest→9 passed→pop). Tests re-implement the fix expression inline instead of exercising the gateway path → contract violation (RED-on-revert), CC must rewrite. **NOT implemented (design-only):** RUNNER_TARGETS_V1 (T2/T3 — Michael's main ask), PATTERN_RISK_CAPS, COUNTER_PATTERN_VETO (Michael gate), S2_DETECTION_LOG, STOP_AFTER_T1_STRUCTURAL. **Also: everything UNCOMMITTED + backend NOT restarted** — pattern_id fix not live yet. Morning queue: CC rewrites tests (real gateway-path call) → commit → restart → then T2/T3 implementation per design + Michael gates on veto/caps.
- **2026-06-11 EOD(5) · Cowork night close: #49 spec-deviation confirmed + unified insights + tomorrow's prompts** — Michael (screenshot #49): double-bottom + upper flag geometry present at #49's HFE SHORT entry — "deviation from spec, should never have been SHORT there". Replay corroborates: detect_double_bottom_ee returned LONG 19:05–19:15 + 20:25–20:55 (counter-pattern active at fire), detections never surfaced live. Deliverables: `docs/handoff/CC_PROMPT_FIX_2026-06-12.md` (Part 1 research: why DB-LONG detections lost + no cross-system counter-pattern check + 17:50 dedup + id43 pattern_id=VEGAS mix; Part 2 fixes flag-gated: pipeline detection-loss fix, COUNTER_PATTERN_VETO, **RUNNER_TARGETS_V1 — activate T2/T3 realization** (nearest-of R-mult↔structural per day_type) + STOP_AFTER_T1_STRUCTURAL (D-002) + PATTERN_RISK_CAPS per stop_anchors.yaml; NOT-DONE: no b2_vsa/b1_expansion calibration yet), `docs/research/EXTERNAL_CHAT_RESEARCH_PROMPT_2026-06-12.md` (paste-ready: 17 patterns × 7 day-types, stop-1/realization-1-2-3/stop-after-each, BE-stop-hunt, CVD oversight, counter-fire question), `docs/reports/INSIGHTS_UNIFIED_2026-06-11.md` (10 unified insights + full doc/link map + tomorrow plan). PLAN 06-12: Michael runs CC fix prompt + external research → joint fix review (Rule 5) → Cowork merges CC results + external research into final recommendations doc for Michael's gates.
- **2026-06-11 EOD(4) · Cowork: S2 why-not-fired REPLAY (read-only, zero code changes) + counter-signal analysis + pattern×day-type playbook** — Michael directives: no code changes, understand only. Replay of 79 RTH bars through exact detector conditions + real `detect_*` imports answered the S2 question definitively: (1) **25 near-misses where ONE condition killed a complete pattern** — REACTIVE blocked 9× solely by `b2_vsa` volume-drop filter; INITIATIVE blocked 13× solely by `b1_expansion` (≥1.3×avg) — these are THE two S2 calibration knobs, not bugs. (2) **DOUBLE_BOTTOM_EE detector found LONGs 19:05–19:15 + 20:25–20:55 but live pipeline only surfaced 20:30+22:15** (both pre_fire-rejected) — pipeline loses detections (suspects: per-kind dedup / chain order / post-hydration buffer; CC to explain, no fix yet). (3) **17:50 REACTIVE_SHORT detected in replay, not traded live** (S4 ZLR id 37 fired same minute) — dedup/exclusion suspect. (4) HnS/iHnS/DT_AA/Flags: 0 detections in 79 bars — geometry genuinely absent today. Counter-signal analysis (`systems_agreement` + 15-min windows): at-fire disagreement NOT predictive (10/13 wins with disagree vs 12/21 without); **opposite-direction fires within 15 min = real red flag** — 13 pairs today, nearly every pair had one big loser (#35→#36 whipsaw −$255; #56/57 vs #58; #49+#50 both lost). Candidate future rule (Michael gate): counter-fire within N bars ⇒ early-exit flag/entry veto. Deliverables: `docs/reports/S2_WHY_NOT_FIRED_REPLAY_2026-06-11.md`, `docs/research/PATTERN_DAYTYPE_PLAYBOOK_RESEARCH_2026-06-11.md` (17 patterns × 7 day-types: entry/stop-1/T1/T2/T3 + stop-after-each, master ENTER/SKIP/SIZE-DOWN matrix, unified stop-movement ladder, source-tagged [W][B][D][VSA][E]), CC prompt updated with T0 silent-pattern fixes (ON HOLD — Michael said no code changes for now).
- **2026-06-11 EOD(3) · Cowork: pattern-observation-week setup + S2 inventory + research brief + CVD-per-trade** — Michael directives: week of observations with EOD per-pattern analysis, verify ALL patterns can actually fire; research brief for external chat (per-pattern stop + profit anchor, day-type conditioned); CVD oversight on every trade. Deliverables: `docs/reports/S2_PATTERNS_INVENTORY_2026-06-11.md` (8 S2 patterns × conditions × gates × today's evidence; INITIATIVE 0-detections persists despite S2_ATR_RELATIVE relative-expansion; HnS/DoubleTop-AA/Flags unproven live today; Pkg 5a Trend_Normal mute confirmed in code), `docs/handoff/CC_PROMPT_PATTERN_OBSERVATION_WEEK_2026-06-11.md` (T1 per-pattern silence + DB ever-fired counts · T2 anti-tautological fixtures per detector · T3 S2/S4_DETECTION_LOG per-bar condition vectors · T4 TRADE_CVD_SNAPSHOT cvd_at_entry/t1/exit, Rule-1 None-propagation · T5 daily eod_pattern_report — audit overlap with #16 first), `docs/research/RESEARCH_BRIEF_STOPS_TARGETS_S1_S2_2026-06-11.md` (6 questions → YAML-ready thresholds). Tracker v2 (+DecisionRules sheet) in Drive `1ydisW_4JJipSs5YQ4oS7L3sSPr_CCdb9`. T2-never-hit explained: S4 t2=None by design (Option 1); S2 T2=2R unreached (max MFE 1.04R); historic T2_HITs ids 10/13/20 prove mechanism works. OPEN: Michael runs CC prompt + pastes research brief; calibration gate after the week.
- **2026-06-11 EOD(2) · Cowork: per-trade visual report + S2 deep checklist + Trades-page redesign prompt; CC audit received** — CC audit (`TRADE_AUDIT_S2_S4_2026-06-11`) confirmed: S2 silence = geometry scarcity (4-bar AND-chain ≈1–3% of bars ⇒ 2 fires/75 bars is per-code behavior), NOT a gate bug; recommends flag-gated `S2_DETECTION_LOG` per-bar condition vector (needs Michael OK to deploy). pnl_r bug root = `_initial_stop()` falls back to current stop (=BE+1T) when `quality.initial_stop` unset → fix: persist initial_stop at trade creation. HFE clusters confirmed: stop=`extreme_bar` anchor reused while CCI stays in extreme zone; existing cooldowns (ζ.A4 global 2-stop, ζ.A5 cluster) never triggered → proposal `S4_PATTERN_COOLDOWN` (same pattern+dir N bars after stop-out) = Michael gate. Today PF 0.35 (winners +$1,232 / losers −$3,477) — winner-cap structural problem (runner = BE only). New finds: id 43 S2 fired REACTIVE_LONG but DB pattern_id=VEGAS (mismatch, CC tracing); repeated hydration ×14 (16:35–16:56, wasted work, root TBD); ids 58/60 = OPEN (not close-failure); S4 time_stop hardcoded 90min, `targets.yaml` per-day_type values not consumed (FIX 5 known). Cowork deliverables: `docs/reports/TRADES_VISUAL_2026-06-11.html` (39/42 trades with per-trade price chart: entry/stop/T1/exit/BE markers), `docs/reports/S2_DEEP_CHECKLIST_2026-06-11.md` (10-stage pipeline checklist + per-stage verification + today's evidence; stages 5–7 = blind spot, no per-bar log), `docs/handoff/CC_PROMPT_TRADES_PAGE_REDESIGN_2026-06-11.md`, tracker uploaded to Google Drive (id `13m5UhNi6c8AQODmiAxNbnBhiw2ZgH4ja`). OPEN gates for Michael: S2_DETECTION_LOG deploy · S4_PATTERN_COOLDOWN · runner mechanism (a/b/c/d) · Pkg 5a Trend_Normal gap intentional?
- **2026-06-11 EOD · Cowork trade audit (42 trades, ids 10–62) + S2-silence diagnosis + tracker workbook** — finding 1: Trades page NOT broken — code/CORS/env/route all verified clean (curl preflight 200 + GET 70KB; page renders full on MACBOOK Chrome; Home MAC can't reach localhost:3000 — likely what Michael saw). finding 2: **S2 produced only 4 events all day** (2 fires ids 33/43 + 2 pre_fire rejections 20:30 risk-73>60, 22:15 R:R<1) — block is UPSTREAM of pre_fire, in detector; day_type/NT-skip/FHB/VSA-flag all verified open (logs); residual suspects: 4-bar geometry strictness + dedup + **Pkg 5a day_type gate excludes Trend_Normal** (17:30–18:00 window HnS/DT/DB muted). finding 3: **pnl_r for winners = ticks not R** (`pnl_r == pnl_usd/1.25`, e.g. id 20 → 233.0; losers correctly −1.0). finding 4: **HFE re-fire storm** — 6 trades shared stop anchor 7323.25 (ids 44–49), 6 shared 7387.25 (52–57,59); risk grew 17.75→39pt; 4 stop-outs ≈ −$1,957; no re-entry cooldown/breaker exists. finding 5: runner has no T2/T3/trail → winners avg ≈+$60 vs full losers −1R (−$330…−$585); the 2 big winners (20, 31) exited via TIME_STOP (luck, not mechanism). Deliverables: `docs/reports/MEMS26_TRADE_TRACKER_2026-06-11.xlsx` (per-trade: entry/stop/anchors/risk-pts/MFE/captured/BE-moves/spec-check; 0 formula errors), `docs/reports/TRADE_ANALYSIS_RECOMMENDATIONS_2026-06-11.md` (per-pattern + per-system recommendations: TLB keep, ZLR suspend-or-trend-filter, HFE cooldown+risk-cap), CC prompt `docs/handoff/CC_PROMPT_TRADE_AUDIT_S2_S4_2026-06-11.md` (Q1 S2 per-bar audit, Q2 pnl_r fix, Q3 anchor source, Q4 spec-conformance, Q5 runner-mechanism data). OPEN: ids 58/60 exit_reason=None; id 22 manual pnl=0; Michael gate on cooldown/breaker/runner mechanism.
- **2026-05-30 · Cowork verified R2-8(p2)+R2-9 DONE** — @5900: gateway test isolation added (`tests/v9/gateway/conftest.py` autouse temp DB, `c204021`); all 30 @5900 rows `is_synthetic=1` (verified `COUNT WHERE is_synthetic=0` = 0); CC verified 2 runs → 0 new. §1.8 CLOSED. R2-9: `day_type_seed.py` loads opening_type/day_type/confidence from today's row (`date=et_today()`, `status!='ROLLED_OVER'`, ORDER BY last_updated_at), falls back to INDETERMINATE only if no row (`7316289`); `bars_5min_stream.py` backfill from MAX(ts) first push (`bffad29`). §1.15 CLOSED. **Minor follow-ups (non-blocking):** (a) gateway test isolation is dir-scoped — confirm `tests/v9/api/` (also uses entry=5900) doesn't leak; (b) seed restores `ib_locked=True` but not the full `lock_state` enum from DB. **All approved §1 work now done.** Remaining: §1.2 (gateway canonical decision), §1.16 (S2 thresholds decision), TPO-TZ confirm, RTH-live verifications; NEWS parked.
- **2026-05-30 · Michael: NEWS handling PARKED** — do not work on news (calendar/feed/options) now; finish all approved items first. Resume later. Remaining APPROVED-but-unfinished for CC: (1) **R2-8 part 2** — test-DB isolation in `tests/conftest.py` (currently missing → @5900 recurs; mark rows 847-861 `is_synthetic=1`); (2) **R2-9** — restart recovery (`day_type_seed.py` load opening_type from DB + `bars_5min_stream.py` backfill). Everything else in R2/P32 committed & verified.
- **2026-05-30 · Cowork verified CC's R2+P32 commits — 2 issues surfaced** — CC committed (git lock cleared): R2-3 ISO-ts floor (`e75caa6`), R2-4 day_type fixtures (`0ee2657`), R2-5 api conftest (`19d6456`), R2-6 TPO test (`7e80626`), R2-8 gateway DB_PATH→DATABASE_URL (`65f00e5`), + P32-I/J/K/L. **Verified:** tick_reversal future-ts = **0** (§1.10 DONE). 844-846 marked `is_synthetic=1` (§1.8 approval executed ✓). **🔴 ISSUE 1 — @5900 RECURS:** 15 NEW rows 847-861 `is_synthetic=0`. Gateway DB_PATH fix alone does NOT isolate tests — `DATABASE_URL` defaults to the live DB (`db/session.py:14`), so tests still write to it. **R2-8 part-2 (conftest temp-DB isolation) was NOT done** → still bleeding. **⚠️ ISSUE 2 — TPO TZ:** `7e80626` changed the TEST to expect UTC (not ET) for `slot_start_ts_str`, classifying as fixture-drift — needs confirm that UTC is the intended TZ (Pre-LIVE Rule 4) or it masks a regression. **R2-9 (restart recovery) NOT started.**
- **2026-05-30 · Michael APPROVED §1.15 (restart recovery — simplified)** — root: `day_type_seed.py:111` hardcodes `opening_type=INDETERMINATE` on seed instead of loading the persisted value (proof: 27/5 saved OPEN_DRIVE but seed would flip to INDETERMINATE). Approved design (no replay, no 13:00 rule): (1) MANDATORY 5min bar backfill on restart (`bars_5min_stream.py` `_first_push`); (2) S1 loads `opening_type`/`day_type`/`lock_state` from today's `v9_day_type_history` row (`date==et_today()`, not ROLLED_OVER), IB/range stay from Sierra; only if no row → real INDETERMINATE (degrades to Normal). Replay + 13:00-skip dropped as over-engineering. → mega-prompt R2-9. Plan: `RESTART_RECOVERY_PLAN_2026-05-30.md` v2.
- **2026-05-30 · Michael APPROVED §1.8** — mark rows 844-846 `is_synthetic=1` (backup first, NOT delete). CC to execute `UPDATE v9_trades SET is_synthetic=1 WHERE id IN (844,845,846)` after `cp data/mems26_local.db data/...bak`, paired with R2-8 gateway DB-path fix so it stops recurring. Verify: `COUNT(*) WHERE entry_price=5900 AND is_synthetic=0` = 0.
- **2026-05-30 · Cowork read-only diagnoses (no-decision): §1.3 + §1.14 largely resolved** — §1.3 pre_fire: verified `validate_fire` IS called in all 3 fire paths (S3 `footprint_system.py:462`, S4 `woodies/decision_tree.py` A7, S2 `five_min/setup_emitter.py:110`) before gateway route — SYSTEM_REVIEW #3 ("standalone route only") is outdated; only cosmetic docstring/dup-route cleanup left. §1.14 status enum: `status.py:_check_day_type` returns live `lock_state`; DB shows `LOCKED_LOW_CONF` (not PENDING) — mapping in place; residual stale-PENDING is a restart/hydration artifact (→ §1.15), verify live after restart-seed.
- **2026-05-30 · Cowork: @5900 root cause = TEST POLLUTION via hardcoded gateway DB path** — `gateway/trading_gateway.py:25` hardcodes `mems26_local.db`, bypassing `DATABASE_URL`; gateway tests (`test_d088`/`test_gw02`, entry=5900) write SHADOW to the LIVE DB. Evidence: 0 hits for 5900 in prod code (tests only); 12 old rows (390-401, 29/5) now `is_synthetic=1`; **3 NEW rows 844-846 created today 14:19:50 — exactly during CC's pytest run — `is_synthetic=0`**; only 3 trades created today, all 5900. Report: `FAKE_5900_SOURCE_2026-05-30.md`. Fix added to R2 (T R2-8): gateway DB path from session + test DB isolation. **Decision (Michael):** mark/delete 844-846 (backup+approval). Also confirms SYSTEM_REVIEW §4 #15 (hardcoded DB paths bypass DATABASE_URL) — gateway doesn't honor DATABASE_URL → LIVE/DEMO risk.
- **2026-05-30 · Cowork: IB-lock "regression" = FIXTURE DRIFT (not a bug) + fixed one test** — root: A4 (`state_machine.py:495-502`) deliberately refuses to lock without Sierra IB (source-of-truth cleanup 28/5); failing tests feed `bar.high/low` with no `ib_high/ib_low`. **Verified empirically in sandbox:** no Sierra IB → `ib_locked=False stage=A3`; with Sierra IB → `ib_locked=True stage=B2`. **Do NOT change the state machine** (would re-introduce the 28/5 bug). Fix = fixtures. ✅ Cowork fixed `tests/v9/systems/test_day_type_ib_live.py` (`_bar()` now defaults `ib_high/ib_low`→high/low; all 3 edge behaviors re-verified). Pending CC (needs pytest/commit): `test_day_type.py::make_bar` same fix, ISO-ts floor, api/ conftest, TPO TZ (group 5), CST test, **commit all (git lock)** → `CC_MEGA_PROMPT_BLOCKER_SWEEP_R2_2026-05-30.md`.
- **2026-05-30 · CC executed Blocker Sweep (T1–T8) — Cowork verified diffs (UNCOMMITTED)** — ⚠️ all code changes in working tree, **not committed** (`.git/index.lock` perms). (T1·§1.5) `woodies_system.py:206` floors ts to 5-min (`ts%300`) → TIME_STOP count fixed; caveat: ISO-ts fallback floors to minute not 5-min — needs regression on closed-bar count. (T2·§1.6) `bar_level_detector.py:38` now subscribes `5min`+`woodies_5min` + minute-dedup → S4 T1/Smart-BE should work; verify live. (T6·§1.7) footprint dedup `(level+dir+bar_ts)` added (`:430,489`); **RTH gate NOT added (Michael decision)**. (T3·§1.13 + @5900) added `is_synthetic` to ORM (`db/models/trades.py`) + API filter (`trades.py`) — but 12 @5900 rows still `is_synthetic=0`, not hidden; no source report → **decision: mark/delete**. (T4·§1.11) verified ALREADY FIXED (`_chicago_to_utc`, `et_today()`). (T5·§1.12) triage → `PYTEST_TRIAGE_2026-05-30.md`: 38 failed/1994 passed; **NEW regression surfaced — day_type IB-lock not firing after A4 (`session_min≥60`), vote_history not populated (groups 9-10)**. (T8·§1.14) `RESTART_RECOVERY_PLAN_2026-05-30.md` (proposal, impl pending approval). **Next:** CC must commit (resolve git lock) + write regression tests; new IB-lock regression added to ROADMAP §1.
- **2026-05-30 · Blocker-sweep mega-prompt prepared (ROADMAP §1.5–§1.14)** — `docs/handoff/CC_MEGA_PROMPT_BLOCKER_SWEEP_2026-05-30.md`. Diagnose-first (code moved — verify before fixing). No-decision tasks T1–T8: TIME_STOP dedup floor-to-5min (`woodies_system.py:206`), T1 detection (`bar_level_detector.py:38` subscribes only `5min`), status-enum verify, **TZ/DST §1.11 appears ALREADY FIXED** (verified: `key_levels` uses `et_today()` :74, `woodies_chart_routes` uses `_chicago_to_utc` — no `+5*3600`), pytest triage, footprint dedup commit, @5900 root-cause (no delete), restart-recovery plan. **Decisions flagged (not executed):** §1.2 gateway canonical (D-093.Q1), §1.4 P5-1 (Q1/Q2/re-lock), §1.7 S3 RTH gate, §1.8 trade deletion, §1.3 pre_fire wiring.
- **2026-05-30 · Cowork verification of CC work (read-only DB + git)** — verified what CC shipped against live DB. (1) **bars_5min future-ts**: root=aggregator wrote ET → fix UTC+ingest-guard (`c581f4d`,`b76d5e2`) → **verified 0 future rows** (`SELECT COUNT(*) … ts>now+2min` = 0). (2) **DLL frozen-tail**: deep-fix shipped (`ada6c88`,`cc9bd8f`) → distinct 5-min buckets show **varying** cci_14 (−40.49/−10.04/−65.39/63.46/103.02) → no frozen-tail in data; earlier "5 identical" was same-bar pushes → still OPEN pending live RTH Phase B (market closed). (3) **fake @5900**: still **12 PARTIAL** in `v9_trades`, `is_synthetic=0` → filter in `trades.py` (uncommitted) doesn't hide them → OPEN. (4) **footprint burst**: 291 firing_system=3 trades last window; `footprint_system.py` dedup **uncommitted, no RTH gate** → OPEN. ROADMAP_TO_LIVE.html updated: 1.1 note corrected, TZ item split (bars_5min done / tick_reversal open), agent-marks seeded on verified items.
- **2026-05-29 EOD · Trading-day report folded into OPEN FOR SUNDAY** — `docs/reports/END_OF_DAY_TRADING_REPORT_2026-05-29.md`. Real P&L +$137.50 (S4 12 trades). New open items moved into triage: 🟠HIGH — TIME_STOP dedup early-fire (#603/#652), T1-not-detected (BarLevelDetector wrong stream), footprint burst 550/day, fake @5900 PARTIAL, 5min restart gaps, S1 restart state-loss · 🟡MED — S1 never-locks (0.68<0.70), opening INDETERMINATE, empty `v9_five_min_state`, tight S4 stop, S2 Initiative threshold research (§7b), pnl_r UI bug, demo #604 open.
- **2026-05-29 14:00 IL · P31 + P31.1 Daily Reset / Archive backend complete** — Bug B RESOLVED. 101/101 tests. Backend recovered. See `docs/reports/P31_1_FIXUP_FINAL_2026-05-29.md`. Phase 3/4/5 pending.
- 2026-05-28 21:50 IL · W-10 TimeStopEnforcer DISABLED (Option B · Michael) — Layer 4 sole TIME_STOP authority. Commit `dispatcher_config.yaml`. 6 tests pass.

## ⚡ ACTIVE HANDOFFS (CC queue)

7. ⏳ **`docs/handoff/CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md`** — written, NOT sent (Bridge tick_reversal TZ + sot_health 4 tasks)
8. ⏳ **Phase 3 prompt** — archive endpoints (`/api/v9/archive/...`) — not yet drafted
9. ⏳ **Phase 4 prompt** — DemoReadiness UI panel + test chain — depends on Phase 3
10. ⏳ **Tiered Fire Status (Plan A++)** — design done in `DAILY_RESET_AND_ARCHIVE_DESIGN.md` §13; deployment phase TBD



---

## 2026-05-29 · P31 + P31.1 Daily Reset / Archive Backend (14:00 IL)

**Bug being closed:** Bug B — frontend dashboard showed yesterday's `day_type` (`Normal · LOCKED_LOW_CONF · 0.68`) pre-market on 29/5 because:
1. Consumer wrote `UNKNOWN/PENDING` rows for 29/5 at 22:00 ET on 28/5 (TZ-naive `date.today()` in IL evening).
2. No filter on `lock_state='ROLLED_OVER'` in `/api/v9/day_type/v9/current` + `/api/v9/key_levels` + V1 compat.
3. `SessionBoundaryManager` did not exist — no daily reset/archive cycle.

| # | Action | Result |
|---|--------|--------|
| 1 | **Cursor pending fix (T1.4)** | ✅ Reset row 11 to `UNKNOWN/PENDING/conf=0` with explicit `reasoning_notes` audit trail; design doc + 5 open questions sent to Michael |
| 2 | **Michael decisions** | ✅ globex_open boundary · plus_replay archiving · all_three test chain · rely_on_existing isolation · diagnose_plus_pending_fix today |
| 3 | **Cursor design (P-T1.5)** | ✅ `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (17 sections incl. consumer write gate · 570f10d overlap · Bug 04 hydrate · CC consult acceptance) |
| 4 | **CC audit (P31a)** | ✅ `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` confirmed 9 design points + flagged 4 boundary semantics + 3 split decisions |
| 5 | **CC consult (P31b)** | ✅ `docs/reports/CC_CONSULT_P31_2026-05-29.md` advisory on §13 boundaries → adopted into §17 of design |
| 6 | **P31 implementation prompt** | ✅ `docs/handoff/CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` — 8 tasks A-H · CC executed + reported in `P31_DAILY_RESET_FINAL_2026-05-29.md` |
| 7 | **Cursor inquiry — 9 gaps surfaced** | ✅ `docs/handoff/CC_INQUIRY_P31_GAPS_2026-05-29.md` → CC self-assessment: working from memory, didn't run migration on live DB, prioritised shipping over verification (CLAUDE.md violations) |
| 8 | **P31.1 fix-up prompt** | ✅ `docs/handoff/CC_IMPLEMENT_P31_1_FIXUP_2026-05-29.md` — 6 tasks T1-T6 · raw UAT mandatory in commit messages |
| 9 | **CC P31.1 execution** | ✅ 6 commits (T1: ground-state-safe rollover · T2: migration on `mems26_local.db` + missing items · T3: SBM first-bar fallback + archive + truncate · T4: 2 SQLite `date('now')` + main.py path · T5: 4 missing test files · T6: final report) · `P31_1_FIXUP_FINAL_2026-05-29.md` |
| 10 | **Cursor verification (14:00 IL)** | ✅ **101/101 tests pass** (41 new P31/P31.1 + 60 regression in `day_type/`+`woodies/`+`test_time_stop`) · M19 schema applied · all 6 endpoints 200 OK · consumer write gate verified live (row 11 `last_updated_at=06:59:21` unchanged after backend ran 7h) |
| 11 | **Backend recovery** | ✅ `screen mems26_backend` started 13:40 IL · port 8000 listening · `BRIDGE_TOKEN` loaded from `.env` (was down since 28/5 19:59 — operator gap, not P31 regression) |
| 12 | **UAT 4-axis** | ✅ Quality (no UNKNOWN written by consumer) · Recency (session_date=29/5 ET) · Cardinality (no row leakage) · Latency (`/v9/current`=3ms · `/key_levels`=9ms · `/tpo/current`=5ms · `/status`=825ms) |

**Schema delta (Migration 019):**
- 4 archive tables: `v9_day_type_archive` · `v9_tpo_sessions_archive` · `v9_woodies_signals_archive` · `v9_build_status_archive`
- `v9_session_meta(last_rollover_date, ...)` — seeded with today, no reset on first run (P31.1-T1)
- 5 `is_synthetic INTEGER NOT NULL DEFAULT 0` columns: `v9_bars_5min` · `v9_woodies_signals` · `v9_trades` · `v9_audit_events` · `v9_five_min_setups`

**Code delta highlights:**
- `backend/v9/common/trading_date.py` — new `et_today()` utility (TZ-aware America/New_York)
- `backend/v9/services/session_boundary/manager.py` — new `SessionBoundaryManager` (idempotent, ground-state-safe, first-bar subscriber, archive on rollover, truncate stale state)
- `backend/v9/systems/day_type/consumer.py` — `_should_gate_write()` blocks `UNKNOWN/PENDING` writes
- `backend/v9/api/v9/day_type_v9_routes.py` + `key_levels_routes.py` + `day_type/api.py` — `lock_state != 'ROLLED_OVER'` filter
- `backend/v9/systems/five_min/five_min_system.py` — day_type hydrate moved before overnight early-return

**Open follow-ups (not blockers):**
- `backend/main.py:22` `DEFAULT_LOCAL_DB_PATH` still hardcoded (renamed but value unchanged — out of P31.1 scope)
- `backend/v9/systems/day_type/api.py:55,88` hardcoded paths remain (out of P31.1 scope)
- Pre-existing `pytest_plugins = ["tests.v9.db.conftest"]` in `tests/v9/api/conftest.py:3` — blocks running `tests/v9/api/` + `tests/v9/db/` together; workaround: run in 4 isolated groups
- CC's P31.1 final report did not paste raw UAT (CLAUDE.md Rule 5 violation, discipline-only)

**Phase plan progress:**
- ✅ **Phase 1** Diagnose + Design + Pending fix
- ✅ **Phase 2** Backend reset + archive (P31 + P31.1)
- ⏳ **Phase 3** Archive endpoints (`/api/v9/archive/sessions/{date}` etc.) — not started
- ⏳ **Phase 4** DemoReadiness UI panel + test chain — depends on Phase 3
- ⏳ **Phase 5** End-to-end UAT + sign-off

---

## 2026-05-28 · S2 VOLUME KEY MISMATCH — CRITICAL ROOT CAUSE (19:23 IL · CC report)

**Bug**: Bridge sends bars with field `"vol"`. S2 detectors read `b.get("v", 0)`. Since wiring, S2 detectors have **always seen volume=0**, silently blocking Reactive (90% vol drop) + Initiative (COT/AMT) patterns. This invalidates CC's earlier "no patterns today" conclusion.

| # | Action | Result |
|---|--------|--------|
| 1 | **CC fix (3 lines, 2 files)** | ✅ `five_min_system.py:698` adds `bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))` · `s2_inspector.py:112` adds `DAY_TYPE_MODE` to trading modes · `s2_inspector.py:103` bypasses FHB gate post-first-hour |
| 2 | **Code-level verification (Cursor)** | ✅ All 3 changes confirmed in source (Read tool, lines 698 / 112 / 103) |
| 3 | **DB integrity** | ✅ 200 bars today · 0 zero-volume rows |
| 4 | **DLL export field name** | ✅ `5min.json` keys = `['ts','o','h','l','c','vol','poc_vol','vah','val','cumulative_delta']` — confirms `"vol"` is canonical |
| 5 | **Running backend = OLD CODE** | ⚠️ Backend PID 49483 started **18:34:51** · CC fix applied **~19:20** · running process has the broken in-memory module · **restart required to activate fix** |
| 6 | **UAT axes (post-restart)** | ⬜ Quality (detectors see volume>0) · ⬜ Recency (next bar feeds patterns) · ⬜ Cardinality (S2 inspector reports correct mode/FHB) · ⬜ Latency (<100ms) |
| 7 | **CC regression report** | 962 pass / 1 skip / 0 NEW failures · 11 pre-existing failures from earlier day_type + IB work (separate cleanup) |

**ACTION required from Michael / Claude Code (sandbox cannot restart services):**
1. `kill -9 49483 && cd ... && nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &`
2. Wait 10s · then probe `/api/v9/cockpit/systems-snapshot` for S2 → expect Reactive/Initiative detectors to start seeing non-zero `b1.volume` next 5-min bar.
3. Watch `/tmp/backend.log` for 5 min for any new exception.

**11 pre-existing test failures (separate ticket):** day_type state machine + IB persistence changes from today's earlier work. Not introduced by CC's fix — but blocks the "全部 green" gate. To be triaged after volume fix confirmed live.

---

## 2026-05-28 · CONVERGENCE — Woodies Data-Integrity Triangle (19:34 IL)

Three independent investigations completed within ~30 minutes; all three point at the same defective Woodies data path:

| # | Source | Bug | Layer | Status |
|---|--------|-----|-------|--------|
| 1 | CC | S2 volume key mismatch (`vol` vs `v`) → detectors saw vol=0 | S2 ingestion | ✅ Code patched (`five_min_system.py:698`) · ⚠️ needs backend restart |
| 2 | Cursor forensic subagent | DLL frozen-tail: last ~13 5-min bars share identical `cci_14 / tcci / lsma / ema_34 / swi / czi / trend_state` (confirmed on 5/26, 5/27, 5/28) | DLL → bridge | ⬜ Open · root cause in `sc_study/v9_woodies_export.h:460-475` · S4 A5 sizing rejects with frozen SWI/TCCI |
| 3 | Cursor Build Status subagent | Sentinel rows `ts='2099-01-02 0X:00:00'` poisoning `v9_bars_5min_woodies` MAX(ts) → lag=-2.29×10⁹s in inspector | Stalled stream writes | ✅ Inspector hardened (`row_helpers.latest_valid_db_ts`) · ⚠️ underlying stream still writes sentinels |

**Synthesis:** findings #2 and #3 are two views of the same illness — the Woodies stream stalls / loops, the DLL clamps to one chart index for many bars, and the bridge writes placeholder `2099-…` rows when it has nothing fresh. S4 receives frozen Sierra study values via `history[-1]` (`bars.py:223-231` prefers history over `current_bar`), A5 sizing rejects, no fire — and the build status used to show fake `Present=✓` because lex-sorted `MAX(ts)` picked the 2099 sentinel.

**Side benefit:** Build Status now exposes `Live · Required · Freshness` per row across S1/S2/S4 (`Stage | Key | Spec | Live | Required | Present | Value`); the recency pill turns red on stale data so the next time the Woodies stream stalls we'll see it immediately. +765/-35 LOC across 10 files · 81/82 tests pass (1 pre-existing failure on `bridge_inspector threshold_seconds=90 ≠ 360`).

**Deliverables produced today:**
- `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` (CC — first pass · "no patterns" verdict — **superseded**)
- `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` (Cursor — falsified CC's verdict · ranked root cause)
- `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md` (independent critical-review prompt)

**Pending decision from Michael:**
1. Restart backend to activate CC's S2 volume fix → run UAT 4 axes.
2. Decide DLL frozen-tail fix path (DLL patch vs bridge-side workaround vs Sierra study reconfiguration).
3. Triage the 11 pre-existing test failures from earlier day_type/IB work.
4. Confirm bridge sentinel-row source (`2099-01-02 0X:00:00` writes — which stream and which code path).

---

## 2026-05-28 · INDEPENDENT CC REVIEW — Forensic Audit Confirmed (19:47 IL)

CC ran an independent READ-ONLY critical review of `AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` against source code + spec. **All 7 claims confirmed.** CC explicitly retracted his earlier "no patterns matched today" diagnosis ("I concluded 'no patterns detected' without querying `v9_woodies_signals`").

**3 NEW gaps surfaced by CC review (not in forensic audit):**

| # | Gap | Severity | File:Line | Status |
|---|-----|----------|-----------|--------|
| 1 | S2 `current_day_type=None` on mid-session restart → chart-pattern day-type gating silently skips because `None ∉ {"Neutral_Extreme","Neutral_Center","Normal","Variation"}` | MED | `five_min_system.py:728-749` | ⬜ Open |
| 2 | `woodies_chart_routes.py:43` hardcoded `ts_unix += 5*3600` is DST-unaware → under-corrects by 1h during CST (Nov-Mar) — winter-time bomb | LOW (today) / HIGH (Nov) | `woodies_chart_routes.py:43` | ⬜ Open |
| 3 | `min_r_t1_threshold >= 1.0` has no test coverage; switching to 1.0 for LIVE without regression risks silent breakage | MED | `test_pattern_dispatcher.py` (missing) | ⬜ Open |

**CC's ranked pre-LIVE blockers (independent):**

| Rank | Blocker | Status |
|------|---------|--------|
| **1 — CRITICAL** | DLL frozen-tail (`GetContainingIndexForDateTimeIndex` clamping in `v9_woodies_export.h:460-475`) — confirmed mechanically: `MES_AI_DataExport.cpp:587` uses direct `arr[idx]` (live) while history loop uses mapped index (frozen) | ⬜ Open · requires DLL patch + rebuild + Sierra study reload |
| **2 — CRITICAL** | Backend `all_bars` property (`bars.py:223-231`) prefers `history[-1]` (frozen) over `current_bar` (live) — compounds #1; CC says "no comment or docstring explains the priority… likely unintended" | ⬜ Open · ~2-line fix |
| **3 — HIGH** | S2 `"v"` vs `"vol"` key mismatch (`five_min_system.py:698`) — S2 Reactive/Initiative have NEVER seen volume since wiring | ✅ Code patched · ⚠️ needs backend restart |

**Worth quoting from CC's review (Q3):** even if S4 sizing read `studies` directly instead of `current_state`, **it would still get frozen inputs** because the routed bar itself is frozen. → Fix #1 (DLL) and Fix #2 (backend routing) are both needed; #2 alone won't help if the live `current_bar` itself doesn't carry the proper Sierra study values, but the audit confirms `current_bar` IS live (cci_14=47.21).

**Resulting strategy (recommendation for Michael's decision):**

1. **NOW** — restart backend → activates CC's S2 vol fix. 0 risk. ~30s.
2. **NEXT** — backend `all_bars` priority swap (`current_bar` first, `history` fallback) — 2-line change + 1 regression test. If `current_bar` carries live Sierra studies, this single change unblocks S4 fires immediately. Verifiable today, no DLL touch.
3. **STRATEGIC** — DLL frozen-tail fix. Architectural decision: patch DLL `mapIdx` to use `bi` directly when chart is in-progress / clamped, OR add bridge-side staleness detector that drops mapped values when they match prior bar's values. Requires DLL rebuild + Sierra study reload.
4. **DEFER** — gaps #1-3 above + 11 pre-existing test failures, after the critical-path two are clean.

CC's review also caught one item worth confirming: **`current_bar`'s study fields are live (`cci_14=47.21`)** — meaning option 2 (the backend `all_bars` swap) is the **cheapest, fastest, lowest-risk** route to actually firing S4 today. The DLL bug stays open but its blast radius is contained.

---

## 2026-05-28 · S2/S4 Live Forensics (19:00 IL · CLOSED — see Convergence + CC Review sections above)

| # | Action | Result |
|---|--------|--------|
| 1 | **CC diagnosis prompts (2)** | ✅ `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` — single combined report. CC conclusion: "no bug, no patterns today; all gates open." |
| 2 | **Cursor caveat on CC report** | ⚠️ CC claimed inspector vs live state divergence is closed — **STILL OPEN.** `/api/v9/status.day_type=PENDING/UNKNOWN/A1` while `v9_day_type_history` row IS classified (`day_type=Normal · prob=0.68 · IB=7574.0/7525.5 · WIDE · INDETERMINATE`). Root cause: legacy `status` column stuck at `PENDING` although classification fields filled — consumer.py never flips the enum. Cosmetic-but-misleading for top-bar; real bug for LIVE. |
| 3 | **Michael challenge** | ⛔ Rejected CC "no patterns" finding. Sierra Woodies UI values appear to disagree with frontend WoodiesLensContent; suspects DLL subgraph / stream-freshness / detector-drift. Requests: spec re-review · frontend↔Sierra parity · push cadence audit · 09:30→now replay through S2+S4 · Claude Desktop mega-prompt for independent critical review. |
| 4 | **Forensic audit subagent (read-only)** | ⏳ IN-FLIGHT. WS-A spec re-review · WS-B FE↔Sierra parity table · WS-C push freshness · WS-D 09:30→now replay (per-bar verdict for each detector) · WS-E ranked root-cause hypothesis. Deliverables: `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` + `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md`. |
| 5 | **No code changes yet** | ✋ Strategic stop — diagnose-first per pre-LIVE protocol. Fix plan deferred until audit report + Michael go/no-go. |

**Known follow-ups queued (no work started):**
- Fix legacy `status` column rollover in `consumer.py` so `/api/v9/status.day_type` matches live machine.
- Pipe `opening_type` through S1→S2 event payload (cosmetic NA vs INDETERMINATE).
- 6-bars replay on mid-session restart in `day_type_seed.py` (so `OPEN_AUCTION_IN` recovers instead of falling back to `INDETERMINATE`).

---

## EOD 2026-05-28 · Key Levels Sierra Source-of-Truth Cleanup (17:35 IL)

| # | Action | Result |
|---|--------|--------|
| 1 | **Sierra Inputs corrected (user UI)** | ✅ In:14=1 (TPO Yest), In:16=6 (IB) — `tpo.json` now valid |
| 2 | **Step 5: `_ib_from_bars` plaster removed** | ✅ `tpo_routes.py` — Sierra is the only IB source |
| 3 | **Step 6: `/api/v9/key_levels` rewritten** | ✅ Reads `_load_sierra_tpo()`, 12/12 fields match Sierra (36ms latency) |
| 4 | **Step 7a: `tpo_system.py` IB sourced from Sierra** | ✅ Removed bar-based `_update_ib` AND second hidden accumulator in `process_bar` |
| 5 | **Step 7b: `main.py` inline IB plaster removed** | ✅ S1 BarInput.ib_h now from Sierra — `v9_day_type_history` matches Sierra |
| 6 | **Step 7c: `state_machine.py` `_stage_a3` cleaned** | ✅ No more `bar.high/low` fallback |
| 6.5 | **Step 7d: `state_machine.py` `_stage_a4` bar.low fallback removed** | ✅ A4 now drops back to A3 if Sierra IB incomplete (loud failure over silent garbage) |
| 7 | **Step 8: Future-bars bug not present** | ✅ `count(*) WHERE ts > now()` = 0; risk also closed by Steps 5-7 |
| 8 | **Step 9: Yesterday IB DLL extension** | DEFERRED · UI shows `Y IB: dll_missing` honestly |
| 9 | **Step 10: UI re-ordered to Michael's spec** | ✅ Today POC / Yest POC / IB Today / Y IB / Yest Range / Today Range |
| 10 | **Tests** | ✅ 117/117 relevant pass; 1 pre-existing unrelated failure (build_status threshold 90 vs 360) |
| 11 | **Report** | ✅ `docs/reports/PROMPT_KEY_LEVELS_SIERRA_TRUTH_2026-05-28.md` |

**Watch item:** Sierra Initial Balance Study (ID:6) reports `ib.found=false`
post-lock at ~10:34 ET. Backend correctly preserves last-known IB and does
not synthesise replacements. Sierra-side investigation needed before next
session — likely a `Number of Days to Calculate` setting on the IB study.

---

## EOD 2026-05-27 · RTH Forensic + Pipeline Fix (21:25 IL)

| # | Action | Result |
|---|--------|--------|
| 0 | **RTH Forensic Audit** | ✅ Zero signals fired — 2 structural bugs identified · full report `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-27.md` |
| 0a | **Bug B1: S2 mode stuck FIRST_HOUR_TACTICAL** | ❌ `process_bar()` missing FIRST_HOUR→DAY_TYPE transition · ALL chart patterns (HNS/flags/doubles) never ran · Fix in mega-prompt |
| 0b | **Bug B2: Woodies demo disabled + shadow not persisted** | ❌ `demo_enabled_systems=[]` · shadow trades in-memory only · Fix in mega-prompt |
| 0c | **Bridge Live Feed Inspector** | ✅ `bridge_inspector.py` added to Build Status · per-stream FRESH/STALE/DEAD indicators · wired to aggregator |
| 0d | **Monitoring Script** | ✅ `scripts/bridge_monitor.py` · snapshots every 15 min · `/tmp/bridge_monitor_YYYYMMDD.log` |
| 0e | **Mega-Prompt: RTH Pipeline Fix** | ✅ `docs/handoff/MEGA_PROMPT_RTH_PIPELINE_FIX_2026-05-27.md` · 3 passes · Claude Desktop + Claude Code · Cursor verifies |
| 0f | **Table cleaned (v9_trades)** | ✅ 1 residual record deleted · fresh start for tomorrow |
| 1 | **G3 Review — Pipeline 2 S4 Woodies** | ✅ 9/10 PASS · W-9 deferred Pipeline 3 · W-10 Time Stop added · F-16 YELLOW guard fixed |
| 2 | **W-10 Time Stop Enforcer** | ✅ `TimeStopEnforcer` + 35 tests · `time_stop.py` · wired `woodies_system.py` |
| 3 | **F-16 YELLOW guard** | ✅ explicit guard instead of exception-for-control-flow |
| 4 | **F-17 RTH gate S4** | ✅ `_is_rth_bar()` + `rth_only` constructor arg · 17 tests |
| 5 | **DB cleanup** | ✅ cleared all backtest/fake trades · shadow day starts from 0 |
| 6 | **4 spec-audit meta-prompts** | ✅ S1/S2/S4/Bridge · `docs/handoff/META_PROMPT_SPEC_AUDIT_*.md` |
| 7 | **Trade filter audit S4** | ✅ AP1-9 · RTH gate · dedup · YELLOW gate · sizing · W-8 dispatcher · W-10 all verified |
| 8 | **S2 First Hour Buffer wired** | ✅ bars 1-3 ACCUMULATING (no patterns) · 4-6 EARLY (reactive only) · 7-9 DEVELOPING · 10+ MATURE |
| 9 | **S2 Choppiness wired** | ✅ `self.choppiness_score` computed live each bar in FIRST_HOUR_TACTICAL |
| 10 | **Archive S2 dead modules** | ✅ `confluence.py` · `q0_dispatcher.py` · `first_hour_matrix.py` → `five_min/archive/` |
| 11 | **Footprint SCID rollover** | ✅ `MESH26` → `MESM26` · 12/12 bridge streams healthy |
| 12 | **Tests** | ✅ 226 pass · 0 new failures |
| 13 | **S1 IB contamination bug (root cause)** | ✅ `is_rth: bool = True` added to `BarInput` · `main.py` computes `_is_rth_bar` from wall-clock ET · A2 guard + A3 guard: Globex bars skip both stages entirely |
| 14 | **S1 Globex / RTH range tracking** | ✅ `globex_h/l` + `rth_session_h/l` tracked separately in state machine · exposed via `/api/v9/day_type/state` meta · displayed in DayType lens (Now tab) |
| 15 | **DB IB cleanup** | ✅ `v9_day_type_history` row reset: `ib_h=NULL · ib_l=NULL · ib_width_class=DEVELOPING · day_type=UNKNOWN` · IB will re-lock correctly at 10:30 ET from RTH bars only |
| 16 | **Build Status enrichment — all 3 systems** | ✅ S1 +2 (ib_range_pts · trading_confidence) = 10 components · S2 +3 (mode_context · fhb_eligible · choppiness_ok) = 9/pattern · S4 +2 (rth_gate · day_type_gate) + last_fire_ts fix = 9/pattern · 71/71 tests |
| 17 | **S1 opening_run_detected** | ✅ new component distinguishes OPEN_DRIVE/OPEN_TEST_DRIVE from AUCTION types |
| 18 | **Diagnostic: systems verified ungated** | ✅ S4 CCI=50 · TCCI=45 · trend=GRAY (correct pre-RTH) · S2 buffer=0 mode=OVERNIGHT (correct pre-RTH) · both unblocked at RTH open |

**Live stack (21:25 IL):** Backend ✅ · Bridge ~10/12 streams live (woodies_5min ✅ footprint ✅ vol_profile ✅ · imbalance DEAD · tpo_bars DEAD) · Frontend ✅ · Build Status ✅ + Bridge Inspector NEW ·

**CRITICAL for next trading day:** 3 fixes pending (S2 mode transition + demo enable + shadow persist) — see `docs/handoff/MEGA_PROMPT_RTH_PIPELINE_FIX_2026-05-27.md`

---

## System Reference — Code · Spec · Decision Tree

| System | Code Path | Spec Authority | Decision Tree |
|--------|-----------|----------------|---------------|
| **S1 · Day Type** | `backend/v9/systems/day_type/` | `docs/decisions/D-091_S2_LIVE_SCOPE.md` §Day Type | `state_machine.py` stages A1→A7 · 7 Dalton types |
| **S2 · Five-Minute Patterns** | `backend/v9/systems/five_min/` | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | `five_min_system.py` → FHB gate → detectors → `setup_emitter.py` |
| **S4 · Woodies CCI** | `backend/v9/systems/woodies/` | `docs/spec_authority/S4_WOODIES_TABLE_*.csv` + `D-092_S4_WOODIES_UPDATE.md` | `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · 21 stages) |
| **S3 · Footprint** | `bridge/v9_streams/footprint_stream.py` | `docs/ENVIRONMENT.md` + DLL ops | `vap_recompute.py` SCID→VAP · file: `MESM26_FUT_CME.scid` |
| **Bridge** | `bridge/v9_streams/` | `CLAUDE.md` §Bridge Local-Only | `base_stream.py` → CLOUD_URL guard → 12 streams → `/api/v9/bars/*` |
| **TradeManager** | `backend/v9/systems/trade_manager/` | `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` | `trade_manager.py` → hooks → gateway |
| **Gateway / Order Routing** | `backend/v9/services/trading_gateway/` | `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` | SHADOW: log-only · LIVE: Sierra DLL API |
| **Quality V2** | `backend/v9/systems/five_min/auth_table_v1.py` | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | pattern × day_type × tier → sizing |

**Plan:** `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` V2

מעודכן רק כש-state ממש משתנה.

---

## Pre-flight checklist


| #    | Item                                                                                                       | Owner                          | Status                                                                           |
| ---- | ---------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------- |
| 1    | D-090 + D-091 → `docs/decisions/`                                                                          | Michael+Cursor                 | ✅ 23/5 17:40                                                                     |
| 2    | Spec lock 1 · Zohar thresholds                                                                             | Michael                        | ✅ 23/5 17:43                                                                     |
| 3    | ~~Spec lock 2 multipliers~~ — already in Master Sheet 4                                                    | —                              | ✅ N/A                                                                            |
| 4    | Spec lock 3 · Bulkowski edge tolerances                                                                    | Michael                        | ✅ 23/5 17:43                                                                     |
| 5    | D-092 Woodies update doc                                                                                   | Michael                        | ✅ 23/5 18:00                                                                     |
| 6    | S1 Day Type verify report                                                                                  | Michael                        | ⬜                                                                                |
| 7    | S3 Footprint verify report (incl. O-4)                                                                     | Michael                        | ⬜                                                                                |
| 8    | Hybrid C model approved (chat explicit)                                                                    | Michael                        | ✅ 23/5 16:48                                                                     |
| 9    | V2 restructure approved (chat explicit)                                                                    | Michael                        | ✅ 23/5 17:30                                                                     |
| 10   | MEGA_PROMPT_TEMPLATE.md                                                                                    | Cursor                         | ✅ 23/5 16:30                                                                     |
| 11   | SPEC_LOCK_TEMPLATE.md V2 (simplified · no multipliers)                                                     | Cursor                         | ⏳ in progress                                                                    |
| 12a  | EXIT_V6 fix Stream 1 · Neutral enum split + targets_table + 6/7 state_machine hits + api.py classification | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 21:00 (chain `dd9c34f` → `a58ee61` → `689ac41`)                   |
| 12a' | Stream 1.5 · prev_day hydration wiring + state_machine.py line 547 rewrite                                 | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 21:18 (commit `548f1f6` · first-try clean)                        |
| 12b  | EXIT_V6 fix Stream 2 · Pkg 3a proper (day_type_targets module + wiring + NT gate)                          | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 22:15 (commit `cf6383e` · first-try clean · zero new regressions) |
| 13   | STATUS_BOARD V2 (this)                                                                                     | Cursor                         | ✅ 23/5 19:05 · 23/5 20:15                                                        |
| 14   | Paste handoff to Claude Desktop · Pkg 0 mega prompt                                                        | Michael + Desktop              | ✅ pasted 23/5 17:43 · Desktop reading                                            |
| 15   | D-093 Sierra Order Routing doc                                                                             | Cursor                         | ✅ 23/5 19:00                                                                     |
| 16   | Pkg 1 handoff finalized (4 Claude Desktop fixes applied)                                                   | Cursor                         | ✅ 23/5 19:05                                                                     |
| 17   | D-093.Q1 · Gateway canonical lock                                                                          | Michael (after CC P5-0a audit) | 🟡 research recommends `backend/v9/services/trading_gateway/` (W11+W14) per `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §3.3 · awaiting Michael lock |
| 18   | D-093.Q2 · Sierra DEMO account                                                                             | Michael                        | ⬜                                                                                |
| 19   | D-091.Q1 · NeuE vs NeuC classification                                                                     | Michael                        | ✅ 23/5 20:10 · LOCKED A (VAH/VAL vs VA-interior · fallback NeuC)                 |
| 20   | D-091.Q2 · NT NO_TRADE gate location                                                                       | Michael                        | ✅ 23/5 20:10 · LOCKED early-skip in `_check_setup` + shadow counter              |
| 21   | D-091.Q4 · Pkg 3a TradeManager wiring scope                                                                | Michael                        | ✅ 23/5 20:10 · LOCKED Emit-only · enforcement in Pkg 6                           |


---

## SHADOW gate (P-S0) — Phase A → SHADOW activation


| Criterion                                                     | Status |
| ------------------------------------------------------------- | ------ |
| Phase A all packages SHADOW-soak completed (0-3, 5, 8, 6 = 13 pkgs + Consolidation = 14 · 4a+4b deferred per D-095) | ⏳ build done · G4 UAT pending RTH 16:30 IL · meta-prompt sent to Desktop |
| pytest tests/v9/ green                                        | ✅ **WAIVER GRANTED 26/5 12:25 IL** · 1694 pass · 21 pre-existing failures in legacy/non-trading code · 4 groups: (A) 7× tpo_history_snapshotter TZ bug · (B) 8× W11 snapshot schema drift · (C) 2× legacy trade_manager DBPersistence · (D) 3× woodies_dedup isolation + 1× frontend journal file missing · none affect S2 trading path · Pkg 0–8+6 Phase A code all green |
| Pkg 5a Axis 2 (Recency)                                       | ✅ **FIXED 26/5 12:02 IL** · commit `7433d52` · setup.ts = bar timestamp · mini-G3 PASS 932/932 |
| Pkg 0 Redis decision                                          | ✅ **CLOSED 26/5 12:15 IL** · no blocking action · legacy keys dead · cleanup deferred to post-SHADOW |
| UAT 4 axes on /cockpit/systems-snapshot                       | ⬜ pending RTH 16:30 IL |
| L4-2 Recency (TPO)                                            | ⬜ pending RTH 16:30 IL |
| L4-3 Cardinality (Five-Min bars)                              | ⬜ pending RTH 16:30 IL |
| L4-4 Latency (all endpoints)                                  | ⬜ pending RTH 16:30 IL |
| G4 smoke trades (Pkgs 1, 2a, 2bc, 3a, 3b, 5a, 5b, 5c, 8, 6) | ⬜ pending RTH · CC scaffolding via Desktop meta-prompt |
| 60min ירוק · zero open warnings                               | ⬜ pending post-UAT soak |
| Michael sign-off                                              | ⬜ pending all above |


---

## Pipeline 1 · S2 D-091 · Phase A (Pre-SHADOW Build)

### Build queue (14 packages · 4a+4b DEFERRED per D-095 25/5 11:18) · **15/15 ✅ COMPLETE 25/5 15:22**


| Pkg             | Name                                                                                                                           | G0 spec                                           | G1 prompt                         | G2 CC                                                      | G3 review                                             | G4 UAT                            | G5 soak                       | G6 promote |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | --------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- | --------------------------------- | ----------------------------- | ---------- |
| 0               | Path B deletion + Path X rewire                                                                                                | ✅                                                 | ✅ 23/5 18:25                      | ✅ 23/5 18:42                                               | ✅ 23/5 18:47 G3 PASS                                  | ⚠️ pending Michael redis decision | n/a                           | ⬜          |
| 1               | Adaptive Stop Engine                                                                                                           | ✅ multipliers (Master Sheet 4)                    | ✅ 23/5 19:00                      | ✅ 23/5 19:27 commit `dd5e2f2`                              | ✅ 23/5 19:30 G3 PASS 12/12                            | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 2a              | OFA Entry signal fix                                                                                                           | ✅ Master Sheet 2 verbatim                         | ✅ handoff 23/5 19:35              | ✅ 23/5 19:51 commit `847bb40`                              | ✅ 23/5 19:55 G3 PASS 12/12                            | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 2bc             | OFA Config + Validators (merged 2b+2c)                                                                                         | ✅ spec locked · arch Option X (S3 forces_history) | ✅ handoff 23/5 20:30              | ✅ 23/5 20:46 commit `dfdf91f`                              | ✅ 23/5 20:50 G3 PASS 10/10                            | ⬜ G4 pending Michael smoke        | ⬜                             | ⬜          |
| 3a · Stream 1   | EXIT_V6 fix · Neutral enum split (NeuE+NeuC) + targets_table NT NO_TRADE + state_machine 6/7 hits + api.py classification      | ✅ D-091.Q1 locked + Option B 23/5 20:34           | ✅ Cursor handoff ready 23/5 20:34 | ✅ chain `dd9c34f` → `a58ee61` → `689ac41` 23/5 20:38-20:55 | ✅ 23/5 21:00 G3 PASS 14/14 (Cursor)                   | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3a · Stream 1.5 | prev_day wiring · `DayTypeStateMachine.__init__` + `_stage_a1` capture + line 547 `_rescore_from_behavior` rewrite             | ✅ D-091 Option B locked                           | ✅ Cursor handoff ready 23/5 21:05 | ✅ 23/5 21:14 commit `548f1f6`                              | ✅ 23/5 21:18 G3 PASS 10/10 (Cursor · first-try clean) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3a · Stream 2   | Day-type targets (7 schemas) · `day_type_targets.py` + T1Setup t3_price + fix opening_type→current_day_type + D-091.Q2 NT gate | ✅ D-091.Q1+Q2+Q4 locked                           | ✅ Cursor handoff ready 23/5 21:42 | ✅ 23/5 22:14 commit `cf6383e`                              | ✅ 23/5 22:15 G3 PASS (Cursor · first-try clean · zero new regressions) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3b · Stream 1   | Trail infrastructure · `atr_caps.py` + BE+1T fix + Pkg 3a override hook                                                        | ✅ D-094 LOCKED 23/5 23:50 + handoff §4            | ✅ Cursor handoff ready 23/5 23:50 (`DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md` §4) | ✅ 24/5 18:53 commit `6dfce93` (+463 / 7 files / 34 tests) | ✅ 24/5 18:57 G3 PASS 8/8 (Cursor · first-try clean · zero new regressions) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3b · Stream 2   | TrailEngine + persistence (Layer 4 wiring deferred to 3b-3 · D-094 retrofit deferred per Michael directive)                    | ✅ D-094 LOCKED 23/5 23:50 + handoff §5 + 3 Cursor-Michael LOCKS 24/5 19:30 + 6 Claude review fixes v2 24/5 20:00 | ✅ Cursor mega-prompt v2 ready 24/5 20:00 (`MEGA_PROMPT_PKG3B_STREAM2.md`) | ✅ 24/5 20:07 commit `23c8456` (+1146 / 3 files / 29 tests) | 🔴 G3 STRATEGIC STOP 24/5 20:15 · CC wrote from scratch · 4 D-094 gap violations (Gap 2/5/11/14) · 29 tests PASS but spec-divergent · resolution: retrofit ב-3b-3 v3 per Michael directive 20:35 | ⬜ G4 pending 3b-3 | superseded by 3b-3 retrofit | ⬜ |
| 3b · Stream 3   | **D-094 retrofit + Layer 4 wiring** · 4 gap fixes from 3b-2 (LOCK 6-9) + 5 Layer 4 services (LOCK 1-5)                          | ✅ D-094 LOCKED + handoff §6 + 5 LOCKS 24/5 20:15 + 6 Claude fixes 24/5 20:30 + 4 D-094 retrofits (LOCK 6-9) per Michael directive 20:35 | ✅ Cursor mega-prompt v3 ready 24/5 20:50 (`MEGA_PROMPT_PKG3B_STREAM3.md` · ~5-6h CC · 58 tests · 28 migrated + 30 new) | ✅ 24/5 21:23 commit `6b2b7cc` → amended 21:42 to `1e01c4a` (3b-3.1 hotfix folded in via `git commit --amend`) | ✅ 24/5 21:45 G3 PASS 14/14 (Cursor · post-amend re-verify · 59/59 tests · baseline 42 failed/1114 passed identical to pre-3b-3 · zero regressions) · LOCK 1-9 + v4 Patch A + D-094 §3.B.3 order all verified | ⬜ G4 pending | ⬜ | ⬜ |
| 3c              | Contract split per pattern (emit-only · feeds Pkg 6)                                                                           | ✅ D-091 §Contract Distribution verbatim (all 10 PatternName values mapped) | ✅ Cursor handoff ready 24/5 19:45 (`DESKTOP_PKG3C_CONTRACT_SPLIT_HANDOFF.md`) | ✅ 24/5 19:45 commit `c917d42` (+163 / 6 files / 16 tests) | ✅ 24/5 19:50 G3 PASS 10/10 (Cursor · first-try clean · zero new regressions) | n/a (emit-only · implicit in Pkg 6 G4) | n/a (no LIVE behavior) | ⬜          |
| 3b · Stream 3.1 | **HOTFIX** · Layer 4 wiring order per D-094 §3.B.3 line 468 · reorder `_apply_layer4` evaluate calls to MFE→CCI→TCCI→SWI→DayType + update docstring lines 552-557 | ✅ D-094 §3.B.3 spec already locked | ✅ ad-hoc CC prompt (Michael 21:35) | ✅ 24/5 21:42 amended into `1e01c4a` (CC chose `git commit --amend` · same parent `31e493e` · +204/-119 trail_engine.py + 95/-119 tests · scope expansion beyond reorder: candidates→Dict + audit-on-move + preconditions + day_type WARN-only routing with no_trade reclass escalation gate · all legitimate improvements matching LOCK 5 part B intent) | ✅ 24/5 21:45 G3 PASS folded into 3b-3 G3 PASS | n/a (no LIVE behavior change) | n/a | ✅ folded |
| 4a              | ~~Risk Rules Critical (2 EXIT)~~ **DEFERRED · D-095 25/5 11:18** · scope absorbed by 3b-3 (TCCI cross live + NO_TRADE reclass live) | ❌ DEFERRED                                       | n/a                               | n/a                                                        | n/a                                                   | n/a                               | n/a                           | n/a        |
| 4b              | ~~Risk Rules Tightening (3)~~ **DEFERRED · D-095 25/5 11:18** · scope absorbed by 3b-3 (mfe/cci_flat/swi all live in _apply_layer4) | ❌ DEFERRED                                       | n/a                               | n/a                                                        | n/a                                                   | n/a                               | n/a                           | n/a        |
| 5a              | Inv H&S + H&S Top                                                                                                              | ✅ lock 3 + Master Sheet 2 trading spec (24/5 16:27) | ✅ Cursor handoff ready 24/5 16:35 | ✅ 24/5 17:22 commit `7ffab50`                              | ✅ 24/5 17:45 G3 PASS 10/10 (Cursor · first-try clean) | ⏳ Scaffolding G3 PASS 24/5 21:00 commit `31e493e` · Axes 1+3+4 GREEN · **Axis 2 FIXED 26/5 commit `7433d52`** · setup.ts now uses bar timestamp · mini-G3 PASS 932/932 · ready for smoke trade | ⬜                             | ⬜          |
| 5b              | Double Bottom + Top                                                                                                            | ✅ lock 3 + Master Sheet 2 trading spec (24/5 17:57) | ✅ Cursor handoff ready 24/5 18:00 (`DESKTOP_PKG5B_DBDT_HANDOFF.md`) | ✅ 24/5 18:35 commit `2c001a2`                              | ✅ 24/5 18:50 G3 PASS 10/10 (Cursor · first-try clean) | ⏳ Scaffolding G3 PASS 24/5 21:00 (shared with 5a · commit `31e493e`) | ⬜                             | ⬜          |
| 5c              | Bull Flag + Bear Flag                                                                                                          | ✅ lock 3 + D-091.Q5 Path C (24/5 18:45) + Master Sheet 2 (24/5 16:27) | ✅ Cursor v2 handoff ready 24/5 19:00 (`DESKTOP_PKG5C_FLAGS_HANDOFF.md`) | ✅ 24/5 19:19 commit `427d687`                              | ✅ 24/5 19:30 G3 PASS 12/12 (Cursor · first-try clean · Q5 Path C verbatim) | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 8               | Quality V2 · Auth Table V1 (pattern × day_type × tier sizing)                                                                    | ✅ 25/5 12:22 · `S2_AUTH_TABLE_V1.md` LOCKED      | ✅ 25/5 12:25 · Cursor handoff ready (`DESKTOP_PKG8_QUALITY_V2_HANDOFF.md`) | ✅ 25/5 13:00 commits `9bc3925` + `773f056` (+341/-58 · 7 files) | ✅ 25/5 13:20 G3 PASS (Cursor · 41 tests · 70 cells verified · Lock #1-8 all PASS) | ⬜ G4 pending post-RTH              | ⬜                             | ⬜          |
| **6**           | **TradeManager extensible**                                                                                                    | ✅ 25/5 13:57 · `S2_TRADEMGR_HOOKS_V1.md` LOCKED (Q9.1-Q9.4 all approved) | ✅ 25/5 14:05 · Cursor handoff ready (`DESKTOP_PKG6_TRADEMGR_HANDOFF.md`) | ✅ 25/5 14:28 commit `77dd4cf` (+887/-54 · 13 files · 39 tests) + `ed76e78` (rename fix · name collision with existing `test_trade_manager.py`) | ✅ 25/5 14:35 G3 PASS (Cursor verified · 10/10 acceptance · 39/39 new tests · D-095 zero-diff · `docs/reports/PKG6_G3_PASS_2026-05-25.md` commit `da4804b`) | ⬜ G4 pending post-RTH              | ⬜                             | ⬜          |
| **Consolidation** | **Phase A Consolidation · stale-fixture repair (LAST · 15th)**                                                              | ✅ 25/5 14:55 · `DESKTOP_PHASE_A_CONSOLIDATION_STALE_FIXTURES_HANDOFF.md` (Cursor verify-first) | ✅ 25/5 14:55 · Cursor handoff ready | ✅ 25/5 15:11 commit `799e00c` (+30/-5 · 3 test files · 18 tests · zero production diff) | ✅ 25/5 15:15 G3 PASS (Cursor verified · 7/7 acceptance · 6 originally-failing tests now PASS · regression sweep identical 30/1562) · `docs/reports/PHASE_A_CONSOLIDATION_G3_PASS_2026-05-25.md` commit `8e98010` | n/a (test-only fix · no LIVE behavior change) | n/a                           | ⬜          |


---

## Pipeline 1 · Phase C (DEMO add-ons)


| Pkg    | Name                                            | Trigger         | Status |
| ------ | ----------------------------------------------- | --------------- | ------ |
| DEMO-1 | News pause + news_countdown                     | DEMO start      | ⬜      |
| DEMO-2 | Filters (lunch skip + FOMC window)              | DEMO start      | ⬜      |
| Pkg 7  | STC/BTC time-of-day (optional · SHADOW-decided) | SHADOW analysis | ⬜      |


---

## Pipeline 2 · S4 D-092 Woodies


| Status       | Item                                                                              |
| ------------ | --------------------------------------------------------------------------------- |
| ✅ 23/5 18:00 | D-092 LOCKED · 9 patterns · ATR-14 stop arch · day-type matrix · 9 anti-patterns                                                                                                                                                                                                                  |
| ✅ 23/5 18:00 | `S4_WOODIES_PATTERN_TABLES_V1.xlsx` + 3 CSV exports in `docs/spec_authority/`                                                                                                                                                                                                                     |
| ✅ 23/5 18:00 | `D-092_S4_WOODIES_UPDATE.md` in `docs/decisions/`                                                                                                                                                                                                                                                 |
| ✅ 25/5 16:30 | **All 10 P-W locks closed** — `docs/handoff/MEGA_PROMPT_PW_DECISIONS_INTAKE.md` §Locked Decisions · audit passed (formulas direction-agnostic · no circular deps · pre-LIVE protocol compliant)                                                                                                   |
| ✅ 25/5 16:50 | **v2 FINAL · all 3 gaps resolved** — Gap 1 DTV1 saved to `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · MD5-verified · matches Michael upload) · Gap 2 P-W6 typo fix `RED → CONT wins` (was `REV wins` · unreachable branch · D-092 unchanged) · Gap 3 confidence formulas code-as-truth KEEP (Registry §5 verified) · Cursor follow-ups #1+#6 ✅ DONE |
| ✅ 25/5 16:50 | Registry §5 row 9 (HFE) updated · "להחליט: DLL only או keep Python fallback" → "🔒 P-W2 lock 25/5 · B · DLL primary · Python audit-only · DLL down → no HFE"                                                                                                                                       |
| ✅ 27/5 08:58 | **G3 PASS (Cursor)** · commit `2e14400` · W-0..W-8 LOCKED (9/10) · W-9 LEGIT BLOCK (S2 Pkg 6 RiskRule + Liran doctrine missing) · 210 new tests + 912 regression · 0 new failures · PatternDispatcher wired `woodies_system.py:242` · AP8 universal wired · atr_stop wired all patterns · raw_confidence UNCHANGED |
| ✅ 27/5 09:00 | **Michael decisions locked:** W-9→defer Pipeline 3 · W-10 Time stop→add to Pipeline 2 (~1.5d CC) · W-11 Partial exit→defer Pipeline 3 · Finding #15 YELLOW edge→Phase B |
| 🟡 SHADOW     | **SHADOW: APPROVED** · paper-trading ready · 9 patterns firing via R_t1 dispatcher |
| ✅ LIVE BLOCK CLEARED | **W-10 Time stop ENFORCED** (Registry #11) · `TimeStopEnforcer` fires per-bar · WARNING log · gateway close |
| ✅ 27/5 10:18 | **W-10 DONE** · commit `210e1ca` · `time_stop.py` + wiring + 35 tests · G3 PASS · 947/947 regression |
| ⏳ pending    | **CC verification batch** (`CC_FINAL_VERIFICATION_BATCH_2026-05-26.md` · §9.2 ❓ items · WIRED layer) |
| ⏳ pending    | **SHADOW data review** ≥200 trades · Phase B R_t1 + raw_confidence distribution check |


---

## Pipeline 3 · S1 Day Type verify


| Status    | Item                       |
| --------- | -------------------------- |
| ⏳ pending | Verify report from Michael |


---

## Pipeline 4 · S3 Footprint verify


| Status    | Item                                                         |
| --------- | ------------------------------------------------------------ |
| ⏳ pending | Verify report from Michael (incl. O-4 entry/stop spec audit) |


---

## Pipeline 5 · Sierra Order Routing (D-093)

**Authority:** `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` (🔒 LOCKED 23/5 19:00)
**Discovery:** No trade has ever reached Sierra — DLL TODO + 2 unwired layers + 3 dead executor stubs.

### Sub-decisions deferred (verify-first)


| Q        | Decision                                                                | Trigger                     | Status |
| -------- | ----------------------------------------------------------------------- | --------------------------- | ------ |
| D-093.Q1 | Gateway canonical: `backend/v9/gateway/` OR `services/trading_gateway/` | After CC P5-0a audit report | ⏳ P5-0 audit in progress (Desktop meta-prompt sent) |
| D-093.Q2 | Sierra DEMO account identifier                                           | Before P5-1 execution       | ✅ **LOCKED 26/5 12:44 IL** · IronBeam · Teton CME Routing [simulation] · verify exact label before P5-1 |


### Build queue (9 packages · ~9.5 CC days)


| Pkg  | Name                                          | G0 spec       | G1 prompt | G2 CC | G3 review | G4 UAT | G5 soak | G6 promote |
| ---- | --------------------------------------------- | ------------- | --------- | ----- | --------- | ------ | ------- | ---------- |
| P5-0 | Gateway reconciliation (verify-first)         | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-1 | DLL `sc.BuyEntry/SellEntry` + Attached Orders (DEMO) | ✅ D-093 · Q2 LOCKED 26/5 | ⏳ meta-prompt sent to Desktop 26/5 · pending Q1 lock | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-2 | DLL result mapping                            | ⬜ (deps P5-1) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-3 | Backend LIVE wiring                           | ⬜ (deps P5-1) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-4 | Position reconciliation                       | ⬜ (deps P5-2) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-5 | Order modification                            | ⬜ (deps P5-2) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-6 | Heartbeat + watchdog                          | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-7 | Bridge integration                            | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-8 | End-to-end UAT (SHADOW + DEMO + LIVE-on-demo) | ⬜ (deps all)  | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |


**Blocks:** SHADOW gate (P-S0) + DEMO gate · because without P5-1 no trade reaches a Sierra account.
**Does NOT block:** Pipeline 1 (S2) · Pipeline 2 (S4) · Pipelines 3/4 verify — those can proceed in parallel.

---

## Pipeline 2 · Shadow Data Quality Gate

**Audit 27/5 10:20 IL** — before LIVE or DEMO enable, shadow data must pass quality review.

| Date | Trades | W/L | PnL | Status |
| ---- | ------ | --- | --- | ------ |
| 2026-05-21 | 633 | 260/373 | -$6,534 | ⚠️ **SUSPECT BACKTEST** · 100 trades/hr uniform · avg_stop=1.5pts |
| 2026-05-22 | 1,830 | 736/1,094 | -$21,670 | ⚠️ **SUSPECT BACKTEST** · 100 trades/hr 24h straight · 736 zero-stop entries |
| 2026-05-23 | 9 | 9/0 | +$375 | ✅ looks real · avg_stop=0 (pre-ATR-stop code) |
| 2026-05-25 | 145 | 64/81 | -$303 | 🟡 real but high fire-rate (145/day = 12/hr) · avg_stop=1.55pts |
| 2026-05-26 | 74 | 32/42 | -$224 | 🟡 real but 74/day = 6/hr · avg_stop=1.54pts |
| 2026-05-27 | 1 | 0/1 | -$15 | ✅ · cleaned · table reset to 0 for fresh shadow start |

**Status after cleanup:** v9_trades = 0 rows. Shadow will repopulate when pipeline fixes deployed.

**Pending (Michael decision):**
- (b) 25/5-26/5 high fire-rate investigation (145/74 trades/day) — after pipeline fixes confirmed working
- (c) Minimum 200 clean post-fix SHADOW trades before LIVE quality assessment

## DEMO gate


| Criterion                                 | Status |
| ----------------------------------------- | ------ |
| All Phase A packages SHADOW passed        | ⬜      |
| D-092 (S4) done                           | ✅ Pipeline 2 complete · W-10 LIVE block cleared |
| S1 + S3 verify closed                     | ⬜      |
| ≥40 SHADOW trades on firing pattern combo | 🟡 data audit required first (see above) |
| Zero open warnings 24h                    | ⬜      |


---

## LIVE micro gate (P-L0)


| Criterion                   | Status |
| --------------------------- | ------ |
| DEMO 7 days on Sierra Sim   | ⬜      |
| Zero bugs surfaced in DEMO  | ⬜      |
| 4 pipelines fully promoted  | ⬜      |
| DEMO-1 + DEMO-2 done + soak | ⬜      |
| P-L0 Preflight 100%         | ⬜      |
| Michael sign-off explicit   | ⬜      |


---

## Risk tracker


| #   | Risk                                                     | Severity | Mitigation status                                     |
| --- | -------------------------------------------------------- | -------- | ----------------------------------------------------- |
| 1   | Spec drift mid-dev                                       | HIGH     | spec lock-once · D-XXX only                           |
| 2   | CC hallucinated APIs                                     | MED      | mega prompt whitelist enforces                        |
| 3   | Silent excepts                                           | HIGH     | mega prompt forbids · G3 adversarial scan             |
| 4   | Parallel streams stomp on shared files (manager.py)      | MED      | Pkg 3a/3b/3c sequential · scope paths whitelist       |
| 5   | Soak finds critical bug                                  | HIGH     | bug-fix budget 30-50%                                 |
| 6   | Michael overload                                         | MED      | spec locks 1+3 first                                  |
| 7   | Master Summary drift from chat                           | MED      | chat = source of truth                                |
| 8   | Pkg 6 hooks insufficient — future rule needs core change | MED      | G3 of Pkg 6 must include "future-rule" unit-test stub |


---

## Amendments log

Full log moved to [](../reports/AMENDMENTS_LOG.md) (148 KB · renderer-friendly separation).
