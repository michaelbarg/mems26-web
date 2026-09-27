T-493/T-494/T-496/T-498/T-500 — replay variants, 27.09 (harness only; NONE of these files is the live tree)

Reference: live0927 = the live configuration loaded 25.09 19:15 (DECISION_TREE_V3=1, config/decision_tree_v3.yaml),
replayed on harness_out/t493/sessions.txt (61 clean sessions; 07.08 crashes in the harness itself → 60 measured).
Evidence for every variant: harness_out/t494/gate_audit_live0927.txt (unique candidates, independent 1.5R sim).
Day-total vs live0927: python3 harness_out/t494/cmp_vs_live.py <tag> [--days]

tag       tree file              change vs the live tree                                          evidence (candidate-level)
t494s1    tree_s1.yaml           phase D: Variation with the extension → TAKE; Normal up|down with → TAKE    stand_down (D,Variation,none,with) 21 · 90% · +1,298$ (3 days)
t494s2    tree_s2.yaml           Variation, against the extension, price back in value → TAKE              bias refusals (C,Variation,mid_value,up,SHORT) 81 · 53% · +1,700$ ; near_val 32 · 69% · +1,007$
t494s3    tree_s3.yaml           take_with_hint skips ELQ                                                  ELQ on take_with_hint 167 · 41% · −1,735$ (expected negative)
t494s4    tree_s4.yaml           S3 + exit ladder 1.5R/2.5R on take_with_hint and take_with_extension     ELQ −1,735$ · RR 44 · 41% · −599$ (expected negative)
t494t2    —                      DROPPED: "TOUCH2_V1=1" is read by no code (the flag is CEILING_FLIP_TOUCH2_V1) ⇒ identical to live0927
t494t2e   tree_t2e.yaml          phase-B open-auction EDGE_FADE leaf: promote CEILING_FLIP_TOUCH2 + ladder 1.5R/2.5R (T-496)   TOUCH2 at that leaf 113 · 51% · +706$ (34 days); TOUCH2 overall 714 · 40% · −1,479$
t494s5    tree_s5.yaml           phase-B open-auction kinds: REVERSAL also taken                          kind refusals FORMING/REVERSAL 19 · +529$ ; Trend_Normal/REVERSAL 13 · +419$
t498ec0   (live tree)            S4_ENTRY_CONFIRM_V1=0 — the entry-confirm gate itself (T-498 live race)   entry_not_confirmed after TAKE 114 · 47% · +1,013$
t494s6    tree_s6.yaml           auction_B_trend_break skips extreme_chase_guard (T-500)                  10 · 80% · +498$ (7 days)
t494s7    tree_s7.yaml           exit ladder 1.5R/2.5R on take_failed_ext + the BREAK kinds leaves        RR refusals there: 9 · 78% · +510$ ; 7 · 86% · +450$

t494pkg   tree_pkg.yaml          S1 + S5 + S7 composed (compose_pkg.py) — the combination is what would go live

Queues: run_queue.sh (s4,s1,s3,s2,t2) → run_queue2.sh (t2e,s5) → run_queue3.sh (ec0) → run_queue4.sh (s6,s7) → run_queue5.sh (pkg). ≤2 parallel, outside RTH.

RESULTS (cmp_vs_live.py, 60 sessions vs live0927 Σ+1,373.75$; net = gross − 2.60$ × Δround-trips):
  t494s1   Δ +160.00$  ≈ +110.60$ net · +19 trades (12 wins) · removed 0 · better 9 / worse 7        PASS
  t494s5   Δ +105.55$  ≈  +69.15$ net · +25 / −11 · better 9 / worse 9                           PASS (thin)
  t494s7   Δ +166.25$  ≈ +163.65$ net · +7 / −6 · better 11 / worse 8                             PASS
  t494s2   Δ  +52.50$  ≈  −41.10$ net · better 15 / worse 13                                      FAIL
  t494s3   Δ  −90.00$  ≈ −183.60$ net · better 13 / worse 13                                      FAIL
  t494s4   Δ −373.75$  ≈ −469.95$ net · better 21 / worse 23                                      FAIL
  t494t2e  Δ −363.05$  ≈ −441.05$ net · 34 TOUCH2 trades, 10 wins                                 FAIL
  t498ec0  Δ −197.50$  ≈ −218.30$ net (entry-confirm OFF) ⇒ the gate earns money                  FAIL
  t494s6   Δ  −95.00$  ≈ −100.20$ net · +2 trades, both stops                                     FAIL
  t494pkg  Δ +470.55$  ≈ +387.35$ net · +46 / −14 · better 24 / worse 12 · maxDD −277.50$ (live −212.50$)   PASS — awaiting Michael
  (live0927 vs the pre-tree baseline: Δ +192.50$ ≈ +166.50$ net · better 9 / worse 3; pkg vs baseline Δ +663.05$ ≈ +553.85$ net)
