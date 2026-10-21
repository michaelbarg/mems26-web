# DAY_LESSONS — one day at a time, walk-forward (2026-10-06)

Michael 06.10 12:29 IL: not a pooled leaf score, not a YAML branch — each day opened on its own; the next day judged only with lessons already learned.

## Method (fixed before any day was looked at)

- Bars: `v9_bars_5min_woodies` MES, RTH 16:30–22:55 IL. IB = first 12 bars (16:30–17:25 IL = 09:30–10:29 ET).
- Value **as of the bar**: last `v9_tpo_history` row with `created_at ≤ bar close` (availability, not nominal `ts`; `ts` is −3h-shifted before 08-31 — T-100). The 16:30:05 row carries the prior session's final value, so the first bars are judged against prior value. `v9_tpo_sessions` CASH end-of-day VAH/VAL is shown in the table only for reference — it is what hid the 10-05 stairs.
- Swing = 3-bar fractal (strict), confirmed 3 bars after the pivot. Candidate signal bar = directional close that takes out the prior bar's high (long) / low (short), signal ts ≤ 19:50.
- Trade execution (same for best-causal and walk-forward): fill = **open of the bar after the signal bar closed**; stop = last confirmed swing on the invalidating side (else session extreme so far); exit = **close of the bar that confirms the next opposite swing**, or the 19:55 bar close (= 20:00), or the stop (checked first, gap → open). 1 contract × $5/pt, no fee, no slippage.
- Best causal trade = the max-$ candidate of the day (hindsight picks the bar; execution is causal).
- Took = `sum(trades[].pnl_usd)` from `harness_out/t466/t543ref_<day>.json` (live config reference); `t529b` shown alongside. Both are 1 contract × $5 (4/192 and 1/145 trades are 2 contracts — reported as written). 08-07 is missing in both. On 06-22 / 07-06 / 09-08 `daily_pnl_harness` differs from the trade sum; the trade sum is used.
- Lesson = tuple (direction, location vs IB, location vs value-as-of, signal-bar volume ≥ / < prior-5-bar median) of that day's best trade. Only day-D information.
- Walk-forward on day D: the first candidate bar whose tuple is in the lesson set from days < D is traded with the same execution; one trade per day; no retirement, no weighting. A lesson never sees its own day.

## Per-day lines

### 2026-06-15
1. IB 7598.25–7622.50 (24.25); drive up (+26.25 above IB, close above IB); value stepped up (7607.25–7620.75 → 7620.50–7648.50).
2. Best causal: **LONG** signal bar 17:45 (close 7615.75), fill 17:50 open 7616.00, stop 7606.50 (last confirmed swing, risk 9.50), exit 19:15 7643.00 [SWING] → **+27.00 pts = $+135.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +191.25 (2 trades) · t529b +191.25 (2 trades)
4. Gap: $+135.00 − (+191.25) = **$-56.25**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7598.25–7622.50) and **IN_VALUE** (value-as-of 7607.25–7620.75) with **VOL_LO** (signal vol 8907 = 0.85× prior-5 median) — new lesson.
6. Walk-forward: no prior lesson matched (0 lessons known) → $0.00 (cum $+0.00).

### 2026-06-16
1. IB 7612.00–7636.50 (24.50); drive down (−29.25 below IB, close below IB); value stepped down (7620.50–7635.50 → 7599.50–7620.25).
2. Best causal: **SHORT** signal bar 16:55 (close 7622.75), fill 17:00 open 7622.75, stop 7636.50 (last confirmed swing, risk 13.75), exit 17:45 7613.00 [SWING] → **+9.75 pts = $+48.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +68.75 (2 trades) · t529b +68.75 (2 trades)
4. Gap: $+48.75 − (+68.75) = **$-20.00**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7612.00–7636.50) and **BELOW_VAL** (value-as-of 7626.25–7634.75) with **VOL_HI** (signal vol 20730 = 1.12× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'INSIDE_IB', 'IN_VALUE', 'VOL_LO') (from 2026-06-15) matched signal bar 19:40 → LONG fill 7613.25, stop 7598.75, exit 19:55 7610.50 [20:00] → **$-13.75** (cum $-13.75).

### 2026-06-22
1. IB 7560.50–7599.25 (38.75); modest extension down (−33.25, close below IB); value stepped down (7551.75–7593.50 → 7528.50–7557.25).
2. Best causal: **SHORT** signal bar 17:10 (close 7589.75), fill 17:15 open 7590.00, stop 7599.25 (last confirmed swing, risk 9.25), exit 18:10 7540.75 [SWING] → **+49.25 pts = $+246.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -46.25 (1 trades) · t529b -46.25 (1 trades)
4. Gap: $+246.25 − (-46.25) = **$+292.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7560.50–7599.25) and **IN_VALUE** (value-as-of 7579.25–7596.75) with **VOL_HI** (signal vol 14359 = 1.02× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 17:20 → SHORT fill 7571.50, stop 7599.25, exit 18:10 7540.75 [SWING] → **$+153.75** (cum $+140.00).

### 2026-06-23
1. IB 7415.00–7491.25 (76.25); auction inside the IB; value held (7439.00–7491.25 → 7441.25–7475.50).
2. Best causal: **LONG** signal bar 16:35 (close 7436.75), fill 16:40 open 7437.00, stop 7415.00 (last confirmed swing, risk 22.00), exit 17:35 7470.50 [SWING] → **+33.50 pts = $+167.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +0.00 (0 trades)
4. Gap: $+167.50 − (+0.00) = **$+167.50**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7415.00–7491.25) and **BELOW_VAL** (value-as-of 7528.50–7557.25) with **VOL_LO** (signal vol 40320 = 0.81× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'INSIDE_IB', 'IN_VALUE', 'VOL_LO') (from 2026-06-15) matched signal bar 18:50 → LONG fill 7453.00, stop 7415.00, exit 19:25 7469.00 [SWING] → **$+80.00** (cum $+220.00).

### 2026-06-24
1. IB 7436.50–7472.50 (36.00); two-sided auction (+24.00/−32.50 around IB, close below IB); value stepped down (7443.00–7466.00 → 7408.25–7467.50).
2. Best causal: **LONG** signal bar 17:20 (close 7458.50), fill 17:25 open 7458.50, stop 7437.00 (last confirmed swing, risk 21.50), exit 18:15 7488.75 [SWING] → **+30.25 pts = $+151.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +0.00 (0 trades)
4. Gap: $+151.25 − (+0.00) = **$+151.25**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7436.50–7472.50) and **IN_VALUE** (value-as-of 7442.25–7467.25) with **VOL_HI** (signal vol 30284 = 1.24× prior-5 median) — new lesson.
6. Walk-forward: no prior lesson matched (4 lessons known) → $0.00 (cum $+220.00).

### 2026-06-25
1. IB 7390.00–7490.50 (100.50); auction inside the IB; value step unknown (v9_tpo_history has <2 post-IB rows).
2. Best causal: **LONG** signal bar 17:00 (close 7427.75), fill 17:05 open 7427.75, stop 7390.00 (last confirmed swing, risk 37.75), exit 17:45 7460.50 [SWING] → **+32.75 pts = $+163.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +0.00 (0 trades)
4. Gap: $+163.75 − (+0.00) = **$+163.75**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7390.00–7490.50) and **IN_VALUE** (value-as-of 7405.00–7475.50) with **VOL_LO** (signal vol 55376 = 0.99× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 16:40 → SHORT fill 7439.00, stop 7490.50, exit 17:10 7437.25 [SWING] → **$+8.75** (cum $+228.75).

### 2026-06-29
1. IB 7409.00–7489.75 (80.75); modest extension up (+15.25, close above IB); value held (7436.50–7480.50 → 7455.00–7500.50).
2. Best causal: **LONG** signal bar 17:20 (close 7430.50), fill 17:25 open 7430.25, stop 7409.00 (last confirmed swing, risk 21.25), exit 18:05 7461.25 [SWING] → **+31.00 pts = $+155.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +81.25 (2 trades) · t529b +81.25 (2 trades)
4. Gap: $+155.00 − (+81.25) = **$+73.75**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7409.00–7489.75) and **BELOW_VAL** (value-as-of 7444.50–7475.25) with **VOL_LO** (signal vol 30326 = 0.87× prior-5 median) — already learned 2026-06-23.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-22) matched signal bar 16:55 → SHORT fill 7458.50, stop 7489.75, exit 17:30 7463.00 [SWING] → **$-22.50** (cum $+206.25).

### 2026-06-30
1. IB 7495.75–7533.50 (37.75); modest extension up (+34.25, close above IB); value stepped up (7510.50–7533.25 → 7524.25–7566.00).
2. Best causal: **LONG** signal bar 18:00 (close 7529.25), fill 18:05 open 7529.25, stop 7495.75 (last confirmed swing, risk 33.50), exit 19:30 7549.75 [SWING] → **+20.50 pts = $+102.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +70.60 (2 trades) · t529b +108.10 (3 trades)
4. Gap: $+102.50 − (+70.60) = **$+31.90**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7495.75–7533.50) and **IN_VALUE** (value-as-of 7510.50–7533.25) with **VOL_HI** (signal vol 13509 = 1.01× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'INSIDE_IB', 'IN_VALUE', 'VOL_LO') (from 2026-06-15) matched signal bar 18:05 → LONG fill 7532.00, stop 7495.75, exit 19:30 7549.75 [SWING] → **$+88.75** (cum $+295.00).

### 2026-07-01
1. IB 7506.00–7553.75 (47.75); rejection of the upside extension (+25.25 then back to/under IB high); value stepped up (7518.75–7551.25 → 7548.50–7578.50).
2. Best causal: **LONG** signal bar 16:50 (close 7531.00), fill 16:55 open 7530.50, stop 7506.00 (last confirmed swing, risk 24.50), exit 17:55 7553.50 [SWING] → **+23.00 pts = $+115.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +85.00 (4 trades) · t529b +170.00 (7 trades)
4. Gap: $+115.00 − (+85.00) = **$+30.00**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7506.00–7553.75) and **IN_VALUE** (value-as-of 7524.25–7566.00) with **VOL_LO** (signal vol 18029 = 0.67× prior-5 median) — already learned 2026-06-25.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:50 → LONG fill 7530.50, stop 7506.00, exit 17:55 7553.50 [SWING] → **$+115.00** (cum $+410.00).

### 2026-07-02
1. IB 7551.75–7594.00 (42.25); drive down (−72.00 below IB, close below IB); value stepped down (7551.75–7581.25 → 7479.75–7556.75).
2. Best causal: **SHORT** signal bar 17:05 (close 7583.75), fill 17:10 open 7583.75, stop 7594.00 (last confirmed swing, risk 10.25), exit 18:20 7539.75 [SWING] → **+44.00 pts = $+220.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -38.75 (1 trades) · t529b -38.75 (1 trades)
4. Gap: $+220.00 − (-38.75) = **$+258.75**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7551.75–7594.00) and **IN_VALUE** (value-as-of 7565.00–7594.00) with **VOL_LO** (signal vol 14761 = 0.67× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-22) matched signal bar 17:20 → SHORT fill 7577.25, stop 7594.00, exit 18:20 7539.75 [SWING] → **$+187.50** (cum $+597.50).

### 2026-07-06
1. IB 7552.25–7579.00 (26.75); modest extension up (+23.25, close above IB); value stepped up (7557.75–7574.00 → 7571.00–7595.75).
2. Best causal: **LONG** signal bar 18:20 (close 7582.25), fill 18:25 open 7582.00, stop 7570.00 (last confirmed swing, risk 12.00), exit 18:45 7588.00 [SWING] → **+6.00 pts = $+30.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -51.25 (4 trades) · t529b -51.25 (4 trades)
4. Gap: $+30.00 − (-51.25) = **$+81.25**
5. Lesson: LONG when the signal bar closes **ABOVE_IB** (IB 7552.25–7579.00) and **ABOVE_VAH** (value-as-of 7560.25–7579.00) with **VOL_LO** (signal vol 7518 = 0.84× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:45 → LONG fill 7568.00, stop 7552.25, exit 17:05 7566.75 [SWING] → **$-6.25** (cum $+591.25).

### 2026-07-07
1. IB 7538.50–7587.75 (49.25); auction inside the IB; value held (7548.50–7582.00 → 7539.25–7570.25).
2. Best causal: **LONG** signal bar 18:40 (close 7541.50), fill 18:45 open 7541.25, stop 7534.50 (last confirmed swing, risk 6.75), exit 19:55 7567.25 [20:00] → **+26.00 pts = $+130.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +158.75 (2 trades) · t529b +158.75 (2 trades)
4. Gap: $+130.00 − (+158.75) = **$-28.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7538.50–7587.75) and **IN_VALUE** (value-as-of 7529.50–7567.00) with **VOL_HI** (signal vol 9781 = 1.38× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:40 → LONG fill 7580.00, stop 7569.25, exit 16:50 7569.25 [STOP] → **$-53.75** (cum $+537.50).

### 2026-07-08
1. IB 7501.75–7524.75 (23.00); two-sided auction (+11.75/−32.50 around IB, close above IB); value held (7501.75–7517.00 → 7496.25–7533.00).
2. Best causal: **LONG** signal bar 18:55 (close 7481.00), fill 19:00 open 7481.00, stop 7469.25 (last confirmed swing, risk 11.75), exit 19:55 7522.00 [20:00] → **+41.00 pts = $+205.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +66.25 (4 trades) · t529b +66.25 (4 trades)
4. Gap: $+205.00 − (+66.25) = **$+138.75**
5. Lesson: LONG when the signal bar closes **BELOW_IB** (IB 7501.75–7524.75) and **BELOW_VAL** (value-as-of 7486.00–7524.75) with **VOL_LO** (signal vol 8004 = 0.77× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 16:45 → SHORT fill 7511.50, stop 7524.75, exit 17:30 7508.00 [SWING] → **$+17.50** (cum $+555.00).

### 2026-07-09
1. IB 7529.50–7566.50 (37.00); modest extension up (+28.50, close above IB); value stepped up (7535.50–7560.50 → 7553.00–7595.00).
2. Best causal: **LONG** signal bar 17:25 (close 7552.75), fill 17:30 open 7552.75, stop 7529.50 (last confirmed swing, risk 23.25), exit 19:45 7580.00 [SWING] → **+27.25 pts = $+136.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -42.50 (1 trades) · t529b -42.50 (1 trades)
4. Gap: $+136.25 − (-42.50) = **$+178.75**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7529.50–7566.50) and **IN_VALUE** (value-as-of 7541.50–7566.50) with **VOL_HI** (signal vol 20637 = 1.08× prior-5 median) — already learned 2026-06-24.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 17:05 → SHORT fill 7553.50, stop 7566.50, exit 17:35 7558.00 [SWING] → **$-22.50** (cum $+532.50).

### 2026-07-13
1. IB 7573.00–7610.50 (37.50); modest extension down (−21.50, close below IB); value stepped down (7590.00–7610.00 → 7560.00–7593.50).
2. Best causal: **SHORT** signal bar 18:40 (close 7588.00), fill 18:45 open 7588.00, stop 7601.50 (last confirmed swing, risk 13.50), exit 19:50 7565.50 [SWING] → **+22.50 pts = $+112.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -40.00 (3 trades) · t529b -40.00 (3 trades)
4. Gap: $+112.50 − (-40.00) = **$+152.50**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7573.00–7610.50) and **IN_VALUE** (value-as-of 7587.00–7606.75) with **VOL_LO** (signal vol 4193 = 0.79× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 17:10 → LONG fill 7603.75, stop 7590.25, exit 17:15 7590.25 [STOP] → **$-67.50** (cum $+465.00).

### 2026-07-14
1. IB 7556.50–7588.25 (31.75); modest extension up (+16.00, close above IB); value stepped up (7567.00–7585.25 → 7576.50–7596.75).
2. Best causal: **LONG** signal bar 19:25 (close 7578.25), fill 19:30 open 7578.00, stop 7575.25 (last confirmed swing, risk 2.75), exit 19:55 7589.25 [20:00] → **+11.25 pts = $+56.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +2.50 (5 trades) · t529b -36.25 (6 trades)
4. Gap: $+56.25 − (+2.50) = **$+53.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7556.50–7588.25) and **IN_VALUE** (value-as-of 7575.00–7599.25) with **VOL_LO** (signal vol 6400 = 0.87× prior-5 median) — already learned 2026-06-15.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:35 → LONG fill 7582.00, stop 7564.25, exit 17:00 7574.75 [SWING] → **$-36.25** (cum $+428.75).

### 2026-07-15
1. IB 7591.75–7619.00 (27.25); rejection of the downside extension (−20.00 then back to/over IB low); value stepped down (7608.75–7624.75 → 7591.50–7619.00).
2. Best causal: **LONG** signal bar 18:45 (close 7583.25), fill 18:50 open 7583.25, stop 7571.75 (last confirmed swing, risk 11.50), exit 19:55 7612.50 [20:00] → **+29.25 pts = $+146.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +236.90 (3 trades) · t529b +185.65 (5 trades)
4. Gap: $+146.25 − (+236.90) = **$-90.65**
5. Lesson: LONG when the signal bar closes **BELOW_IB** (IB 7591.75–7619.00) and **BELOW_VAL** (value-as-of 7600.75–7618.25) with **VOL_HI** (signal vol 20421 = 2.43× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 17:05 → LONG fill 7610.00, stop 7597.00, exit 17:15 7597.00 [STOP] → **$-65.00** (cum $+363.75).

### 2026-07-16
1. IB 7598.50–7614.75 (16.25); drive down (−50.25 below IB, close below IB); value step unknown (v9_tpo_history has <2 post-IB rows).
2. Best causal: **SHORT** signal bar 17:40 (close 7605.50), fill 17:45 open 7605.75, stop 7613.75 (last confirmed swing, risk 8.00), exit 18:40 7588.75 [SWING] → **+17.00 pts = $+85.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -34.35 (4 trades) · t529b -40.60 (6 trades)
4. Gap: $+85.00 − (-34.35) = **$+119.35**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7598.50–7614.75) and **IN_VALUE** (value-as-of 7593.25–7619.00) with **VOL_LO** (signal vol 8245 = 0.93× prior-5 median) — already learned 2026-07-13.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 16:35 → SHORT fill 7608.25, stop 7614.00, exit 16:45 7614.00 [STOP] → **$-28.75** (cum $+335.00).

### 2026-07-17
1. IB 7504.75–7533.75 (29.00); modest extension down (−20.25, close below IB); value stepped up (7491.00–7536.50 → 7506.25–7536.50).
2. Best causal: **SHORT** signal bar 19:10 (close 7529.75), fill 19:15 open 7529.75, stop 7539.00 (last confirmed swing, risk 9.25), exit 19:55 7511.00 [20:00] → **+18.75 pts = $+93.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +80.60 (1 trades) · t529b +80.60 (1 trades)
4. Gap: $+93.75 − (+80.60) = **$+13.15**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7504.75–7533.75) and **IN_VALUE** (value-as-of 7503.00–7535.50) with **VOL_LO** (signal vol 5543 = 0.66× prior-5 median) — already learned 2026-07-13.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:35 → LONG fill 7532.75, stop 7521.75, exit 16:45 7521.75 [STOP] → **$-55.00** (cum $+280.00).

### 2026-07-20
1. IB 7506.00–7552.25 (46.25); modest extension down (−29.25, close below IB); value held (7505.25–7530.50 → 7501.25–7528.00).
2. Best causal: **SHORT** signal bar 16:45 (close 7539.75), fill 16:50 open 7539.75, stop 7552.25 (last confirmed swing, risk 12.50), exit 17:35 7517.50 [SWING] → **+22.25 pts = $+111.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -75.00 (1 trades) · t529b -75.00 (1 trades)
4. Gap: $+111.25 − (-75.00) = **$+186.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7506.00–7552.25) and **ABOVE_VAH** (value-as-of 7502.00–7536.50) with **VOL_LO** (signal vol 17237 = 0.88× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-22) matched signal bar 16:50 → SHORT fill 7528.75, stop 7552.25, exit 17:35 7517.50 [SWING] → **$+56.25** (cum $+336.25).

### 2026-07-21
1. IB 7521.00–7544.00 (23.00); rejection of the upside extension (+10.25 then back to/under IB high); value stepped up (7510.50–7527.75 → 7524.75–7553.25).
2. Best causal: **LONG** signal bar 16:45 (close 7532.75), fill 16:50 open 7532.75, stop 7521.00 (last confirmed swing, risk 11.75), exit 18:45 7548.25 [SWING] → **+15.50 pts = $+77.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -31.25 (1 trades) · t529b -13.75 (2 trades)
4. Gap: $+77.50 − (-31.25) = **$+108.75**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7521.00–7544.00) and **ABOVE_VAH** (value-as-of 7525.75–7527.25) with **VOL_HI** (signal vol 21073 = 1.31× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 16:35 → SHORT fill 7526.25, stop 7535.75, exit 16:45 7535.75 [STOP] → **$-47.50** (cum $+288.75).

### 2026-07-23
1. IB 7444.75–7486.50 (41.75); modest extension down (−26.25, close below IB); value stepped down (7447.50–7468.00 → 7426.75–7457.50).
2. Best causal: **SHORT** signal bar 16:45 (close 7464.25), fill 16:50 open 7464.00, stop 7486.50 (last confirmed swing, risk 22.50), exit 17:20 7454.00 [SWING] → **+10.00 pts = $+50.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -50.00 (3 trades) · t529b -50.00 (3 trades)
4. Gap: $+50.00 − (-50.00) = **$+100.00**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7444.75–7486.50) and **BELOW_VAL** (value-as-of 7536.00–7555.25) with **VOL_HI** (signal vol 28913 = 1.15× prior-5 median) — already learned 2026-06-16.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:35 → LONG fill 7474.75, stop 7444.75, exit 17:50 7444.75 [STOP] → **$-150.00** (cum $+138.75).

### 2026-07-27
1. IB 7439.50–7514.25 (74.75); rejection of the downside extension (−23.25 then back to/over IB low); value stepped down (7451.00–7502.00 → 7423.75–7455.50).
2. Best causal: **SHORT** signal bar 16:40 (close 7493.25), fill 16:45 open 7493.50, stop 7514.25 (last confirmed swing, risk 20.75), exit 17:55 7455.50 [SWING] → **+38.00 pts = $+190.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +160.00 (2 trades) · t529b +160.00 (2 trades)
4. Gap: $+190.00 − (+160.00) = **$+30.00**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7439.50–7514.25) and **BELOW_VAL** (value-as-of 7506.50–7509.00) with **VOL_HI** (signal vol 23521 = 1.01× prior-5 median) — already learned 2026-06-16.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 16:40 → SHORT fill 7493.50, stop 7514.25, exit 17:55 7455.50 [SWING] → **$+190.00** (cum $+328.75).

### 2026-07-30
1. IB 7399.75–7446.50 (46.75); modest extension up (+32.00, close above IB); value held (7418.50–7446.50 → 7405.25–7446.50).
2. Best causal: **LONG** signal bar 18:30 (close 7413.75), fill 18:35 open 7414.00, stop 7398.75 (last confirmed swing, risk 15.25), exit 19:30 7441.25 [SWING] → **+27.25 pts = $+136.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +112.50 (1 trades) · t529b +112.50 (1 trades)
4. Gap: $+136.25 − (+112.50) = **$+23.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7399.75–7446.50) and **IN_VALUE** (value-as-of 7404.25–7434.25) with **VOL_LO** (signal vol 15073 = 0.82× prior-5 median) — already learned 2026-06-15.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-24) matched signal bar 16:40 → LONG fill 7417.25, stop 7399.75, exit 17:15 7431.25 [SWING] → **$+70.00** (cum $+398.75).

### 2026-07-31
1. IB 7427.50–7515.25 (87.75); modest extension up (+25.75, close above IB); value held (7442.00–7500.50 → 7449.25–7506.75).
2. Best causal: **SHORT** signal bar 16:35 (close 7493.50), fill 16:40 open 7493.25, stop 7515.25 (last confirmed swing, risk 22.00), exit 17:30 7456.00 [SWING] → **+37.25 pts = $+186.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +0.00 (0 trades)
4. Gap: $+186.25 − (+0.00) = **$+186.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7427.50–7515.25) and **ABOVE_VAH** (value-as-of 7399.50–7455.75) with **VOL_LO** (signal vol 23109 = 0.83× prior-5 median) — already learned 2026-07-20.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-07-20) matched signal bar 16:35 → SHORT fill 7493.25, stop 7515.25, exit 17:30 7456.00 [SWING] → **$+186.25** (cum $+585.00).

### 2026-08-03
1. IB 7542.75–7600.00 (57.25); modest extension up (+38.50, close above IB); value stepped up (7562.00–7600.00 → 7585.50–7637.00).
2. Best causal: **LONG** signal bar 16:35 (close 7568.75), fill 16:40 open 7568.75, stop 7542.75 (last confirmed swing, risk 26.00), exit 18:15 7605.75 [SWING] → **+37.00 pts = $+185.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +90.00 (3 trades) · t529b +111.25 (5 trades)
4. Gap: $+185.00 − (+90.00) = **$+95.00**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7542.75–7600.00) and **ABOVE_VAH** (value-as-of 7469.25–7531.00) with **VOL_LO** (signal vol 24706 = 0.69× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'INSIDE_IB', 'IN_VALUE', 'VOL_LO') (from 2026-06-15) matched signal bar 17:35 → LONG fill 7600.00, stop 7542.75, exit 18:15 7605.75 [SWING] → **$+28.75** (cum $+613.75).

### 2026-08-05
1. IB 7794.75–7820.25 (25.50); drive down (−49.00 below IB, close below IB); value stepped down (7798.25–7814.25 → 7753.50–7791.25).
2. Best causal: **SHORT** signal bar 17:15 (close 7808.50), fill 17:20 open 7808.50, stop 7820.25 (last confirmed swing, risk 11.75), exit 18:05 7788.00 [SWING] → **+20.50 pts = $+102.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +168.75 (2 trades) · t529b +236.25 (3 trades)
4. Gap: $+102.50 − (+168.75) = **$-66.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7794.75–7820.25) and **IN_VALUE** (value-as-of 7805.00–7820.25) with **VOL_LO** (signal vol 9011 = 0.59× prior-5 median) — already learned 2026-07-02.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-07-20) matched signal bar 16:45 → SHORT fill 7805.75, stop 7820.25, exit 17:05 7812.50 [SWING] → **$-33.75** (cum $+580.00).

### 2026-08-06
1. IB 7740.25–7768.50 (28.25); modest extension down (−16.00, close below IB); value stepped down (7750.75–7765.75 → 7727.50–7751.25).
2. Best causal: **SHORT** signal bar 18:00 (close 7752.50), fill 18:05 open 7752.75, stop 7768.50 (last confirmed swing, risk 15.75), exit 19:30 7732.75 [SWING] → **+20.00 pts = $+100.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -162.50 (3 trades) · t529b -162.50 (3 trades)
4. Gap: $+100.00 − (-162.50) = **$+262.50**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7740.25–7768.50) and **IN_VALUE** (value-as-of 7748.00–7763.50) with **VOL_HI** (signal vol 15249 = 1.03× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:45 → LONG fill 7763.00, stop 7740.25, exit 17:05 7764.75 [SWING] → **$+8.75** (cum $+588.75).

### 2026-08-07
1. IB 7743.25–7780.50 (37.25); auction inside the IB; value stepped up (7750.50–7771.75 → 7761.75–7780.25).
2. Best causal: **LONG** signal bar 17:15 (close 7765.75), fill 17:20 open 7765.75, stop 7743.25 (last confirmed swing, risk 22.50), exit 17:45 7771.75 [SWING] → **+6.00 pts = $+30.00** (1 contract × $5/pt, no fee).
3. Took: t543ref missing · t529b missing → **missing**
4. Gap: $+30.00 − missing = n/a
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7743.25–7780.50) and **IN_VALUE** (value-as-of 7754.50–7768.00) with **VOL_HI** (signal vol 24256 = 1.08× prior-5 median) — already learned 2026-06-24.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:40 → LONG fill 7767.25, stop 7753.50, exit 16:55 7753.50 [STOP] → **$-68.75** (cum $+520.00).

### 2026-08-10
1. IB 7771.00–7791.25 (20.25); two-sided auction (+5.75/−7.25 around IB, close inside IB); value held (7775.50–7791.25 → 7771.50–7786.00).
2. Best causal: **SHORT** signal bar 19:05 (close 7786.50), fill 19:10 open 7786.50, stop 7788.75 (last confirmed swing, risk 2.25), exit 19:45 7772.75 [SWING] → **+13.75 pts = $+68.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +0.00 (0 trades)
4. Gap: $+68.75 − (+0.00) = **$+68.75**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7771.00–7791.25) and **IN_VALUE** (value-as-of 7779.50–7790.25) with **VOL_LO** (signal vol 5685 = 0.8× prior-5 median) — already learned 2026-07-13.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:45 → LONG fill 7777.75, stop 7771.25, exit 16:50 7771.25 [STOP] → **$-32.50** (cum $+487.50).

### 2026-08-11
1. IB 7771.75–7792.50 (20.75); drive down (−32.50 below IB, close below IB); value stepped down (7777.00–7788.75 → 7740.25–7776.50).
2. Best causal: **SHORT** signal bar 17:35 (close 7779.25), fill 17:40 open 7779.50, stop 7787.00 (last confirmed swing, risk 7.50), exit 18:50 7763.75 [SWING] → **+15.75 pts = $+78.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +112.50 (1 trades) · t529b +42.50 (3 trades)
4. Gap: $+78.75 − (+112.50) = **$-33.75**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7771.75–7792.50) and **IN_VALUE** (value-as-of 7777.00–7788.75) with **VOL_HI** (signal vol 10450 = 1.13× prior-5 median) — already learned 2026-08-06.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 16:45 → SHORT fill 7774.25, stop 7792.50, exit 17:50 7784.75 [SWING] → **$-52.50** (cum $+435.00).

### 2026-08-12
1. IB 7763.50–7794.00 (30.50); auction inside the IB; value held (7763.50–7780.75 → 7764.75–7777.75).
2. Best causal: **LONG** signal bar 18:45 (close 7766.50), fill 18:50 open 7766.50, stop 7756.25 (last confirmed swing, risk 10.25), exit 19:55 7773.50 [20:00] → **+7.00 pts = $+35.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -146.25 (4 trades) · t529b -146.25 (4 trades)
4. Gap: $+35.00 − (-146.25) = **$+181.25**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7763.50–7794.00) and **IN_VALUE** (value-as-of 7761.50–7778.00) with **VOL_LO** (signal vol 5307 = 0.8× prior-5 median) — already learned 2026-06-15.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 17:00 → SHORT fill 7764.00, stop 7794.00, exit 17:20 7774.00 [SWING] → **$-50.00** (cum $+385.00).

### 2026-08-13
1. IB 7785.25–7837.00 (51.75); auction inside the IB; value held (7811.00–7837.50 → 7798.50–7825.25).
2. Best causal: **SHORT** signal bar 17:40 (close 7830.25), fill 17:45 open 7830.25, stop 7838.50 (last confirmed swing, risk 8.25), exit 19:10 7801.25 [SWING] → **+29.00 pts = $+145.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +248.75 (4 trades) · t529b +237.50 (6 trades)
4. Gap: $+145.00 − (+248.75) = **$-103.75**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7785.25–7837.00) and **ABOVE_VAH** (value-as-of 7796.50–7821.50) with **VOL_LO** (signal vol 9445 = 0.92× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:35 → LONG fill 7809.00, stop 7785.25, exit 17:50 7823.00 [SWING] → **$+70.00** (cum $+455.00).

### 2026-08-14
1. IB 7813.75–7830.75 (17.00); drive down (−17.25 below IB, close below IB); value stepped down (7819.25–7828.50 → 7798.25–7814.00).
2. Best causal: **SHORT** signal bar 17:10 (close 7825.25), fill 17:15 open 7825.25, stop 7830.75 (last confirmed swing, risk 5.50), exit 17:45 7814.75 [SWING] → **+10.50 pts = $+52.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -31.25 (2 trades) · t529b -80.00 (4 trades)
4. Gap: $+52.50 − (-31.25) = **$+83.75**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7813.75–7830.75) and **IN_VALUE** (value-as-of 7822.00–7828.25) with **VOL_LO** (signal vol 10979 = 0.98× prior-5 median) — already learned 2026-07-02.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:40 → LONG fill 7826.50, stop 7819.25, exit 17:20 7819.25 [STOP] → **$-36.25** (cum $+418.75).

### 2026-08-17
1. IB 7789.25–7809.50 (20.25); drive down (−23.00 below IB, close below IB); value held (7789.75–7802.00 → 7780.00–7807.25).
2. Best causal: **SHORT** signal bar 19:25 (close 7794.25), fill 19:30 open 7794.25, stop 7800.00 (last confirmed swing, risk 5.75), exit 19:55 7788.00 [20:00] → **+6.25 pts = $+31.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -13.75 (2 trades) · t529b +21.25 (3 trades)
4. Gap: $+31.25 − (-13.75) = **$+45.00**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7789.25–7809.50) and **IN_VALUE** (value-as-of 7791.00–7799.50) with **VOL_HI** (signal vol 4691 = 1.01× prior-5 median) — already learned 2026-08-06.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 17:10 → LONG fill 7797.75, stop 7789.25, exit 18:35 7791.25 [SWING] → **$-32.50** (cum $+386.25).

### 2026-08-18
1. IB 7716.50–7735.25 (18.75); modest extension down (−6.25, close below IB); value held (7720.25–7732.00 → 7716.75–7726.25).
2. Best causal: **SHORT** signal bar 17:40 (close 7724.00), fill 17:45 open 7724.00, stop 7732.75 (last confirmed swing, risk 8.75), exit 18:15 7714.75 [SWING] → **+9.25 pts = $+46.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -55.00 (1 trades) · t529b -55.00 (1 trades)
4. Gap: $+46.25 − (-55.00) = **$+101.25**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7716.50–7735.25) and **IN_VALUE** (value-as-of 7720.25–7732.00) with **VOL_LO** (signal vol 11133 = 0.77× prior-5 median) — already learned 2026-07-13.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-24) matched signal bar 17:00 → LONG fill 7729.75, stop 7718.50, exit 17:10 7718.50 [STOP] → **$-56.25** (cum $+330.00).

### 2026-08-19
1. IB 7720.75–7746.25 (25.50); rejection of the upside extension (+18.50 then back to/under IB high); value held (7728.00–7742.25 → 7728.75–7749.00).
2. Best causal: **SHORT** signal bar 18:05 (close 7754.75), fill 18:10 open 7754.75, stop 7764.75 (last confirmed swing, risk 10.00), exit 19:55 7736.00 [20:00] → **+18.75 pts = $+93.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -65.00 (3 trades) · t529b -45.00 (4 trades)
4. Gap: $+93.75 − (-65.00) = **$+158.75**
5. Lesson: SHORT when the signal bar closes **ABOVE_IB** (IB 7720.75–7746.25) and **ABOVE_VAH** (value-as-of 7725.25–7747.75) with **VOL_LO** (signal vol 10059 = 0.85× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 16:45 → SHORT fill 7725.00, stop 7746.25, exit 17:05 7737.75 [SWING] → **$-63.75** (cum $+266.25).

### 2026-08-20
1. IB 7691.50–7716.25 (24.75); drive down (−32.50 below IB, close below IB); value held (7695.50–7709.50 → 7690.25–7714.50).
2. Best causal: **SHORT** signal bar 18:05 (close 7703.75), fill 18:10 open 7703.75, stop 7719.75 (last confirmed swing, risk 16.00), exit 19:00 7693.75 [SWING] → **+10.00 pts = $+50.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +118.75 (3 trades) · t529b +148.75 (5 trades)
4. Gap: $+50.00 − (+118.75) = **$-68.75**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7691.50–7716.25) and **IN_VALUE** (value-as-of 7697.00–7710.00) with **VOL_HI** (signal vol 19180 = 1.84× prior-5 median) — already learned 2026-08-06.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 17:00 → SHORT fill 7698.25, stop 7716.25, exit 17:35 7707.75 [SWING] → **$-47.50** (cum $+218.75).

### 2026-08-21
1. IB 7676.50–7696.25 (19.75); rejection of the upside extension (+13.75 then back to/under IB high); value stepped up (7679.75–7690.50 → 7685.00–7701.00).
2. Best causal: **LONG** signal bar 17:45 (close 7685.75), fill 17:50 open 7685.75, stop 7676.50 (last confirmed swing, risk 9.25), exit 18:20 7690.50 [SWING] → **+4.75 pts = $+23.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -40.00 (1 trades) · t529b -40.00 (1 trades)
4. Gap: $+23.75 − (-40.00) = **$+63.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7676.50–7696.25) and **IN_VALUE** (value-as-of 7679.75–7690.50) with **VOL_HI** (signal vol 10683 = 1.0× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-22) matched signal bar 16:50 → SHORT fill 7679.50, stop 7696.25, exit 17:55 7693.75 [SWING] → **$-71.25** (cum $+147.50).

### 2026-08-24
1. IB 7655.00–7682.75 (27.75); auction inside the IB; value stepped up (7659.25–7674.25 → 7666.75–7682.00).
2. Best causal: **LONG** signal bar 18:20 (close 7665.50), fill 18:25 open 7665.50, stop 7659.50 (last confirmed swing, risk 6.00), exit 19:35 7677.50 [SWING] → **+12.00 pts = $+60.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +22.50 (1 trades) · t529b +70.00 (3 trades)
4. Gap: $+60.00 − (+22.50) = **$+37.50**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7655.00–7682.75) and **IN_VALUE** (value-as-of 7661.25–7674.50) with **VOL_HI** (signal vol 11953 = 1.87× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-22) matched signal bar 17:00 → SHORT fill 7664.25, stop 7682.75, exit 17:25 7663.25 [SWING] → **$+5.00** (cum $+152.50).

### 2026-08-25
1. IB 7679.75–7701.25 (21.50); rejection of the downside extension (−17.00 then back to/over IB low); value held (7682.25–7697.00 → 7680.25–7691.50).
2. Best causal: **SHORT** signal bar 16:50 (close 7693.25), fill 16:55 open 7693.25, stop 7701.25 (last confirmed swing, risk 8.00), exit 17:45 7675.25 [SWING] → **+18.00 pts = $+90.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +77.50 (3 trades) · t529b +68.75 (5 trades)
4. Gap: $+90.00 − (+77.50) = **$+12.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7679.75–7701.25) and **ABOVE_VAH** (value-as-of 7666.50–7680.75) with **VOL_LO** (signal vol 12655 = 0.81× prior-5 median) — already learned 2026-07-20.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-07-20) matched signal bar 16:50 → SHORT fill 7693.25, stop 7701.25, exit 17:45 7675.25 [SWING] → **$+90.00** (cum $+242.50).

### 2026-08-26
1. IB 7678.75–7702.00 (23.25); rejection of the downside extension (−7.75 then back to/over IB low); value held (7680.25–7695.75 → 7680.25–7695.25).
2. Best causal: **SHORT** signal bar 17:10 (close 7694.00), fill 17:15 open 7694.25, stop 7702.00 (last confirmed swing, risk 7.75), exit 17:40 7685.75 [SWING] → **+8.50 pts = $+42.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +0.00 (0 trades) · t529b +65.60 (1 trades)
4. Gap: $+42.50 − (+0.00) = **$+42.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7678.75–7702.00) and **IN_VALUE** (value-as-of 7685.75–7701.50) with **VOL_LO** (signal vol 12488 = 0.91× prior-5 median) — already learned 2026-07-02.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:40 → LONG fill 7695.50, stop 7678.75, exit 17:15 7691.75 [SWING] → **$-18.75** (cum $+223.75).

### 2026-08-27
1. IB 7702.75–7730.50 (27.75); modest extension up (+25.25, close above IB); value stepped up (7711.75–7727.25 → 7721.25–7746.00).
2. Best causal: **LONG** signal bar 19:25 (close 7740.50), fill 19:30 open 7740.50, stop 7725.00 (last confirmed swing, risk 15.50), exit 19:55 7752.00 [20:00] → **+11.50 pts = $+57.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +27.50 (4 trades) · t529b +80.00 (5 trades)
4. Gap: $+57.50 − (+27.50) = **$+30.00**
5. Lesson: LONG when the signal bar closes **ABOVE_IB** (IB 7702.75–7730.50) and **ABOVE_VAH** (value-as-of 7717.00–7738.75) with **VOL_HI** (signal vol 5217 = 1.0× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_HI') (from 2026-07-21) matched signal bar 16:40 → LONG fill 7723.50, stop 7702.75, exit 17:00 7719.25 [SWING] → **$-21.25** (cum $+202.50).

### 2026-08-28
1. IB 7726.50–7760.50 (34.00); two-sided auction (+22.00/−14.75 around IB, close below IB); value stepped down (7740.75–7760.00 → 7712.75–7755.25).
2. Best causal: **SHORT** signal bar 18:30 (close 7773.50), fill 18:35 open 7773.75, stop 7782.50 (last confirmed swing, risk 8.75), exit 19:35 7732.25 [SWING] → **+41.50 pts = $+207.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -62.50 (1 trades) · t529b -62.50 (1 trades)
4. Gap: $+207.50 − (-62.50) = **$+270.00**
5. Lesson: SHORT when the signal bar closes **ABOVE_IB** (IB 7726.50–7760.50) and **ABOVE_VAH** (value-as-of 7731.50–7768.25) with **VOL_LO** (signal vol 9976 = 0.86× prior-5 median) — already learned 2026-08-19.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:35 → LONG fill 7751.50, stop 7743.75, exit 17:00 7743.75 [STOP] → **$-38.75** (cum $+163.75).

### 2026-08-31
1. IB 7674.75–7704.25 (29.50); auction inside the IB; value held (7677.50–7696.25 → 7680.75–7692.00).
2. Best causal: **SHORT** signal bar 16:35 (close 7690.50), fill 16:40 open 7690.50, stop 7704.25 (last confirmed swing, risk 13.75), exit 17:00 7686.00 [SWING] → **+4.50 pts = $+22.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -66.25 (2 trades) · t529b -66.25 (2 trades)
4. Gap: $+22.50 − (-66.25) = **$+88.75**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7674.75–7704.25) and **BELOW_VAL** (value-as-of 7712.75–7753.75) with **VOL_LO** (signal vol 20780 = 0.88× prior-5 median) — new lesson.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 17:00 → SHORT fill 7686.00, stop 7704.25, exit 17:40 7686.00 [SWING] → **$-0.00** (cum $+163.75).

### 2026-09-01
1. IB 7638.50–7667.25 (28.75); rejection of the downside extension (−17.00 then back to/over IB low); value held (7639.00–7657.50 → 7633.00–7662.00).
2. Best causal: **SHORT** signal bar 19:05 (close 7665.75), fill 19:10 open 7665.75, stop 7673.75 (last confirmed swing, risk 8.00), exit 19:45 7646.25 [SWING] → **+19.50 pts = $+97.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +176.20 (4 trades) · t529b +221.20 (5 trades)
4. Gap: $+97.50 − (+176.20) = **$-78.70**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7638.50–7667.25) and **IN_VALUE** (value-as-of 7652.50–7673.75) with **VOL_LO** (signal vol 8455 = 0.99× prior-5 median) — already learned 2026-07-13.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:45 → LONG fill 7649.00, stop 7638.50, exit 17:50 7663.00 [SWING] → **$+70.00** (cum $+233.75).

### 2026-09-02
1. IB 7643.25–7682.50 (39.25); auction inside the IB; value stepped up (7643.25–7671.00 → 7672.25–7687.00).
2. Best causal: **LONG** signal bar 16:40 (close 7654.25), fill 16:45 open 7654.00, stop 7643.25 (last confirmed swing, risk 10.75), exit 18:45 7676.50 [SWING] → **+22.50 pts = $+112.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +113.75 (3 trades) · t529b +101.25 (6 trades)
4. Gap: $+112.50 − (+113.75) = **$-1.25**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7643.25–7682.50) and **ABOVE_VAH** (value-as-of 7650.25–7651.25) with **VOL_LO** (signal vol 14111 = 0.73× prior-5 median) — already learned 2026-08-03.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:40 → LONG fill 7654.00, stop 7643.25, exit 18:45 7676.50 [SWING] → **$+112.50** (cum $+346.25).

### 2026-09-03
1. IB 7700.50–7726.50 (26.00); drive up (+39.75 above IB, close above IB); value stepped up (7704.25–7719.50 → 7718.25–7766.25).
2. Best causal: **LONG** signal bar 17:55 (close 7718.00), fill 18:00 open 7718.25, stop 7700.50 (last confirmed swing, risk 17.75), exit 18:45 7755.75 [SWING] → **+37.50 pts = $+187.50** (1 contract × $5/pt, no fee).
3. Took: t543ref -3.75 (2 trades) · t529b -3.75 (2 trades)
4. Gap: $+187.50 − (-3.75) = **$+191.25**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7700.50–7726.50) and **IN_VALUE** (value-as-of 7704.25–7719.50) with **VOL_HI** (signal vol 23118 = 2.11× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:35 → LONG fill 7723.00, stop 7704.25, exit 17:05 7704.25 [STOP] → **$-93.75** (cum $+252.50).

### 2026-09-04
1. IB 7729.50–7751.00 (21.50); modest extension down (−19.25, close below IB); value stepped down (7735.75–7749.75 → 7712.75–7731.00).
2. Best causal: **SHORT** signal bar 16:40 (close 7743.50), fill 16:45 open 7743.50, stop 7751.00 (last confirmed swing, risk 7.50), exit 18:15 7715.50 [SWING] → **+28.00 pts = $+140.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +142.50 (4 trades) · t529b +115.00 (6 trades)
4. Gap: $+140.00 − (+142.50) = **$-2.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7729.50–7751.00) and **ABOVE_VAH** (value-as-of 7742.25–7743.25) with **VOL_LO** (signal vol 21345 = 1.0× prior-5 median) — already learned 2026-07-20.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-07-20) matched signal bar 16:40 → SHORT fill 7743.50, stop 7751.00, exit 18:15 7715.50 [SWING] → **$+140.00** (cum $+392.50).

### 2026-09-08
1. IB 7680.00–7717.75 (37.75); auction inside the IB; value held (7680.75–7704.75 → 7686.25–7699.75).
2. Best causal: **SHORT** signal bar 16:35 (close 7702.00), fill 16:40 open 7702.00, stop 7717.75 (last confirmed swing, risk 15.75), exit 17:25 7687.50 [SWING] → **+14.50 pts = $+72.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +105.00 (5 trades) · t529b +47.50 (7 trades)
4. Gap: $+72.50 − (+105.00) = **$-32.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7680.00–7717.75) and **BELOW_VAL** (value-as-of 7712.75–7731.00) with **VOL_LO** (signal vol 23738 = 0.73× prior-5 median) — already learned 2026-08-31.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-08-31) matched signal bar 16:35 → SHORT fill 7702.00, stop 7717.75, exit 17:25 7687.50 [SWING] → **$+72.50** (cum $+465.00).

### 2026-09-09
1. IB 7644.25–7663.75 (19.50); rejection of the downside extension (−15.50 then back to/over IB low); value stepped down (7651.75–7662.25 → 7639.50–7657.50).
2. Best causal: **LONG** signal bar 19:20 (close 7637.00), fill 19:25 open 7637.00, stop 7628.75 (last confirmed swing, risk 8.25), exit 19:55 7645.75 [20:00] → **+8.75 pts = $+43.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -15.00 (3 trades) · t529b -15.00 (3 trades)
4. Gap: $+43.75 − (-15.00) = **$+58.75**
5. Lesson: LONG when the signal bar closes **BELOW_IB** (IB 7644.25–7663.75) and **BELOW_VAL** (value-as-of 7643.75–7663.50) with **VOL_LO** (signal vol 5595 = 0.75× prior-5 median) — already learned 2026-07-08.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:55 → LONG fill 7660.75, stop 7652.00, exit 17:15 7652.00 [STOP] → **$-43.75** (cum $+421.25).

### 2026-09-10
1. IB 7585.50–7620.00 (34.50); auction inside the IB; value held (7589.00–7609.25 → 7596.25–7613.75).
2. Best causal: **LONG** signal bar 17:15 (close 7599.25), fill 17:20 open 7599.25, stop 7585.50 (last confirmed swing, risk 13.75), exit 17:35 7612.50 [SWING] → **+13.25 pts = $+66.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +3.75 (2 trades) · t529b +3.75 (2 trades)
4. Gap: $+66.25 − (+3.75) = **$+62.50**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7585.50–7620.00) and **IN_VALUE** (value-as-of 7586.00–7602.00) with **VOL_LO** (signal vol 18488 = 0.8× prior-5 median) — already learned 2026-06-25.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:35 → LONG fill 7603.50, stop 7593.75, exit 16:50 7593.75 [STOP] → **$-48.75** (cum $+372.50).

### 2026-09-11
1. IB 7659.75–7682.00 (22.25); modest extension down (−6.50, close below IB); value held (7667.50–7681.25 → 7666.25–7679.25).
2. Best causal: **LONG** signal bar 18:00 (close 7664.00), fill 18:05 open 7664.00, stop 7653.25 (last confirmed swing, risk 10.75), exit 18:55 7675.00 [SWING] → **+11.00 pts = $+55.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -86.25 (2 trades) · t529b -86.25 (2 trades)
4. Gap: $+55.00 − (-86.25) = **$+141.25**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7659.75–7682.00) and **BELOW_VAL** (value-as-of 7667.50–7681.25) with **VOL_LO** (signal vol 12310 = 0.76× prior-5 median) — new lesson.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:55 → LONG fill 7681.00, stop 7659.75, exit 17:35 7659.75 [STOP] → **$-106.25** (cum $+266.25).

### 2026-09-14
1. IB 7665.25–7694.75 (29.50); rejection of the upside extension (+25.00 then back to/under IB high); value stepped up (7668.00–7686.00 → 7678.50–7715.50).
2. Best causal: **LONG** signal bar 18:05 (close 7674.50), fill 18:10 open 7674.50, stop 7662.50 (last confirmed swing, risk 12.00), exit 18:55 7702.00 [SWING] → **+27.50 pts = $+137.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +78.75 (5 trades) · t529b +148.75 (6 trades)
4. Gap: $+137.50 − (+78.75) = **$+58.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7665.25–7694.75) and **IN_VALUE** (value-as-of 7665.25–7684.25) with **VOL_HI** (signal vol 27239 = 4.49× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-06-23) matched signal bar 16:40 → LONG fill 7677.75, stop 7668.00, exit 17:20 7671.25 [SWING] → **$-32.50** (cum $+233.75).

### 2026-09-15
1. IB 7654.00–7687.00 (33.00); rejection of the downside extension (−10.50 then back to/over IB low); value stepped down (7664.00–7684.75 → 7647.75–7661.00).
2. Best causal: **SHORT** signal bar 16:45 (close 7676.50), fill 16:50 open 7676.50, stop 7687.00 (last confirmed swing, risk 10.50), exit 18:05 7650.75 [SWING] → **+25.75 pts = $+128.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -12.50 (2 trades) · t529b +17.50 (3 trades)
4. Gap: $+128.75 − (-12.50) = **$+141.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7654.00–7687.00) and **BELOW_VAL** (value-as-of 7679.25–7712.75) with **VOL_LO** (signal vol 13226 = 0.75× prior-5 median) — already learned 2026-08-31.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-06-25) matched signal bar 16:40 → LONG fill 7682.50, stop 7670.25, exit 17:05 7670.25 [STOP] → **$-61.25** (cum $+172.50).

### 2026-09-18
1. IB 7683.25–7714.50 (31.25); rejection of the downside extension (−8.25 then back to/over IB low); value held (7683.25–7703.50 → 7681.25–7701.75).
2. Best causal: **SHORT** signal bar 16:35 (close 7705.25), fill 16:40 open 7705.25, stop 7714.50 (last confirmed swing, risk 9.25), exit 17:30 7687.50 [SWING] → **+17.75 pts = $+88.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +82.50 (1 trades) · t529b +82.50 (1 trades)
4. Gap: $+88.75 − (+82.50) = **$+6.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7683.25–7714.50) and **IN_VALUE** (value-as-of 7694.50–7711.00) with **VOL_LO** (signal vol 16179 = 0.64× prior-5 median) — already learned 2026-07-02.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'IN_VALUE', 'VOL_LO') (from 2026-07-02) matched signal bar 16:35 → SHORT fill 7705.25, stop 7714.50, exit 17:30 7687.50 [SWING] → **$+88.75** (cum $+261.25).

### 2026-09-21
1. IB 7758.25–7791.00 (32.75); drive up (+56.25 above IB, close above IB); value stepped up (7761.00–7781.75 → 7767.50–7826.00).
2. Best causal: **LONG** signal bar 16:40 (close 7766.25), fill 16:45 open 7766.25, stop 7758.25 (last confirmed swing, risk 8.00), exit 19:45 7820.00 [SWING] → **+53.75 pts = $+268.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +211.25 (3 trades) · t529b +230.00 (5 trades)
4. Gap: $+268.75 − (+211.25) = **$+57.50**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7758.25–7791.00) and **ABOVE_VAH** (value-as-of 7681.25–7709.25) with **VOL_LO** (signal vol 9321 = 0.65× prior-5 median) — already learned 2026-08-03.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:40 → LONG fill 7766.25, stop 7758.25, exit 19:45 7820.00 [SWING] → **$+268.75** (cum $+530.00).

### 2026-09-22
1. IB 7831.50–7848.50 (17.00); modest extension down (−9.00, close below IB); value stepped down (7834.50–7845.50 → 7828.50–7840.50).
2. Best causal: **LONG** signal bar 18:55 (close 7826.75), fill 19:00 open 7826.75, stop 7822.50 (last confirmed swing, risk 4.25), exit 19:55 7832.00 [20:00] → **+5.25 pts = $+26.25** (1 contract × $5/pt, no fee).
3. Took: t543ref +141.85 (3 trades) · t529b +161.85 (4 trades)
4. Gap: $+26.25 − (+141.85) = **$-115.60**
5. Lesson: LONG when the signal bar closes **BELOW_IB** (IB 7831.50–7848.50) and **BELOW_VAL** (value-as-of 7829.50–7841.75) with **VOL_LO** (signal vol 5749 = 0.75× prior-5 median) — already learned 2026-07-08.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-07-20) matched signal bar 16:40 → SHORT fill 7842.75, stop 7848.50, exit 17:10 7840.00 [SWING] → **$+13.75** (cum $+543.75).

### 2026-09-23
1. IB 7778.25–7826.50 (48.25); modest extension down (−19.25, close below IB); value stepped down (7786.50–7818.25 → 7764.75–7793.75).
2. Best causal: **SHORT** signal bar 16:35 (close 7816.75), fill 16:40 open 7817.00, stop 7826.50 (last confirmed swing, risk 9.50), exit 17:40 7786.25 [SWING] → **+30.75 pts = $+153.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +151.90 (2 trades) · t529b +155.65 (3 trades)
4. Gap: $+153.75 − (+151.90) = **$+1.85**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7778.25–7826.50) and **BELOW_VAL** (value-as-of 7827.25–7839.25) with **VOL_HI** (signal vol 14530 = 1.0× prior-5 median) — already learned 2026-06-16.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 16:35 → SHORT fill 7817.00, stop 7826.50, exit 17:40 7786.25 [SWING] → **$+153.75** (cum $+697.50).

### 2026-09-24
1. IB 7730.00–7758.25 (28.25); modest extension up (+25.25, close above IB); value stepped up (7738.75–7757.50 → 7744.00–7778.00).
2. Best causal: **LONG** signal bar 19:10 (close 7739.50), fill 19:15 open 7739.50, stop 7725.25 (last confirmed swing, risk 14.25), exit 19:30 7762.25 [SWING] → **+22.75 pts = $+113.75** (1 contract × $5/pt, no fee).
3. Took: t543ref +61.25 (2 trades) · t529b +22.50 (3 trades)
4. Gap: $+113.75 − (+61.25) = **$+52.50**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7730.00–7758.25) and **IN_VALUE** (value-as-of 7726.75–7746.75) with **VOL_HI** (signal vol 8501 = 1.15× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:35 → LONG fill 7744.25, stop 7730.00, exit 17:20 7752.25 [SWING] → **$+40.00** (cum $+737.50).

### 2026-09-25
1. IB 7752.75–7793.75 (41.00); modest extension up (+21.00, close above IB); value stepped up (7766.50–7789.50 → 7775.75–7807.25).
2. Best causal: **LONG** signal bar 18:30 (close 7781.75), fill 18:35 open 7781.50, stop 7752.75 (last confirmed swing, risk 28.75), exit 19:45 7802.25 [SWING] → **+20.75 pts = $+103.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -35.00 (2 trades) · t529b -35.00 (2 trades)
4. Gap: $+103.75 − (-35.00) = **$+138.75**
5. Lesson: LONG when the signal bar closes **INSIDE_IB** (IB 7752.75–7793.75) and **IN_VALUE** (value-as-of 7767.50–7787.50) with **VOL_HI** (signal vol 27677 = 2.28× prior-5 median) — already learned 2026-06-30.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:35 → LONG fill 7787.75, stop 7767.50, exit 17:00 7767.50 [STOP] → **$-101.25** (cum $+636.25).

### 2026-09-28
1. IB 7758.75–7775.25 (16.50); two-sided auction (+10.75/−32.75 around IB, close below IB); value held (7761.50–7772.50 → 7747.75–7778.25).
2. Best causal: **SHORT** signal bar 17:10 (close 7762.00), fill 17:15 open 7762.25, stop 7774.75 (last confirmed swing, risk 12.50), exit 18:10 7741.00 [SWING] → **+21.25 pts = $+106.25** (1 contract × $5/pt, no fee).
3. Took: t543ref -41.25 (2 trades) · t529b -41.25 (2 trades)
4. Gap: $+106.25 − (-41.25) = **$+147.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7758.75–7775.25) and **BELOW_VAL** (value-as-of 7764.00–7775.25) with **VOL_HI** (signal vol 14216 = 1.05× prior-5 median) — already learned 2026-06-16.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_HI') (from 2026-06-16) matched signal bar 17:10 → SHORT fill 7762.25, stop 7774.75, exit 18:10 7741.00 [SWING] → **$+106.25** (cum $+742.50).

### 2026-09-29
1. IB 7731.75–7758.75 (27.00); rejection of the downside extension (−19.50 then back to/over IB low); value stepped down (7733.00–7747.75 → 7718.00–7741.75).
2. Best causal: **SHORT** signal bar 16:55 (close 7736.50), fill 17:00 open 7736.25, stop 7758.75 (last confirmed swing, risk 22.50), exit 18:40 7726.50 [SWING] → **+9.75 pts = $+48.75** (1 contract × $5/pt, no fee).
3. Took: t543ref -107.50 (2 trades) · t529b -53.15 (3 trades)
4. Gap: $+48.75 − (-107.50) = **$+156.25**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7731.75–7758.75) and **BELOW_VAL** (value-as-of 7757.75–7758.75) with **VOL_LO** (signal vol 15326 = 0.88× prior-5 median) — already learned 2026-08-31.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-08-31) matched signal bar 16:40 → SHORT fill 7740.75, stop 7758.75, exit 17:10 7741.00 [SWING] → **$-1.25** (cum $+741.25).

### 2026-09-30
1. IB 7747.75–7779.50 (31.75); drive down (−37.75 below IB, close below IB); value held (7754.75–7775.25 → 7758.00–7778.50).
2. Best causal: **LONG** signal bar 16:45 (close 7759.00), fill 16:50 open 7759.00, stop 7747.75 (last confirmed swing, risk 11.25), exit 17:20 7772.00 [SWING] → **+13.00 pts = $+65.00** (1 contract × $5/pt, no fee).
3. Took: t543ref -75.00 (1 trades) · t529b -147.50 (3 trades)
4. Gap: $+65.00 − (-75.00) = **$+140.00**
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7747.75–7779.50) and **ABOVE_VAH** (value-as-of 7718.75–7741.75) with **VOL_HI** (signal vol 18952 = 1.52× prior-5 median) — already learned 2026-07-21.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_HI') (from 2026-07-21) matched signal bar 16:45 → LONG fill 7759.00, stop 7747.75, exit 17:20 7772.00 [SWING] → **$+65.00** (cum $+806.25).

### 2026-10-01
1. IB 7682.25–7740.25 (58.00); auction inside the IB; value held (7683.00–7715.50 → 7682.25–7722.25).
2. Best causal: **SHORT** signal bar 16:40 (close 7720.25), fill 16:45 open 7720.00, stop 7740.25 (last confirmed swing, risk 20.25), exit 17:20 7689.00 [SWING] → **+31.00 pts = $+155.00** (1 contract × $5/pt, no fee).
3. Took: t543ref +182.50 (2 trades) · t529b +182.50 (2 trades)
4. Gap: $+155.00 − (+182.50) = **$-27.50**
5. Lesson: SHORT when the signal bar closes **IB_FORMING** (IB 7682.25–7740.25) and **BELOW_VAL** (value-as-of 7758.00–7778.50) with **VOL_LO** (signal vol 19636 = 0.75× prior-5 median) — already learned 2026-08-31.
6. Walk-forward: lesson ('SHORT', 'IB_FORMING', 'BELOW_VAL', 'VOL_LO') (from 2026-08-31) matched signal bar 16:40 → SHORT fill 7720.00, stop 7740.25, exit 17:20 7689.00 [SWING] → **$+155.00** (cum $+961.25).

### 2026-10-02
1. IB 7773.50–7808.75 (35.25); rejection of the downside extension (−19.50 then back to/over IB low); value stepped down (7784.50–7805.00 → 7765.75–7792.25).
2. Best causal: **SHORT** signal bar 17:50 (close 7793.00), fill 17:55 open 7792.75, stop 7805.00 (last confirmed swing, risk 12.25), exit 18:40 7773.25 [SWING] → **+19.50 pts = $+97.50** (1 contract × $5/pt, no fee).
3. Took: t543ref +21.25 (4 trades) · t529b +21.25 (4 trades)
4. Gap: $+97.50 − (+21.25) = **$+76.25**
5. Lesson: SHORT when the signal bar closes **INSIDE_IB** (IB 7773.50–7808.75) and **IN_VALUE** (value-as-of 7784.50–7805.00) with **VOL_HI** (signal vol 17740 = 1.53× prior-5 median) — already learned 2026-08-06.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'ABOVE_VAH', 'VOL_LO') (from 2026-08-03) matched signal bar 16:40 → LONG fill 7800.25, stop 7778.25, exit 16:55 7778.25 [STOP] → **$-110.00** (cum $+851.25).

## Final table

| day | best causal $ | took (t543ref) $ | walk-forward $ | cum WF $ | lesson learned | lesson applied | sessions VAH/VAL (EOD, ref only) |
|---|---:|---:|---:|---:|---|---|---|
| 2026-06-15 | +135.00 | +191.25 | — | +0.00 | LONG/INSIDE_IB/IN_VALUE/VOL_LO | — | 7577.00–7648.50 |
| 2026-06-16 | +48.75 | +68.75 | -13.75 | -13.75 | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | LONG/INSIDE_IB/IN_VALUE/VOL_LO | 7625.50–7636.50 |
| 2026-06-22 | +246.25 | -46.25 | +153.75 | +140.00 | SHORT/IB_FORMING/IN_VALUE/VOL_HI | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7543.25–7548.25 |
| 2026-06-23 | +167.50 | +0.00 | +80.00 | +220.00 | LONG/IB_FORMING/BELOW_VAL/VOL_LO | LONG/INSIDE_IB/IN_VALUE/VOL_LO | 7441.75–7450.50 |
| 2026-06-24 | +151.25 | +0.00 | — | +220.00 | LONG/IB_FORMING/IN_VALUE/VOL_HI | — | 7404.50–7410.75 |
| 2026-06-25 | +163.75 | +0.00 | +8.75 | +228.75 | LONG/IB_FORMING/IN_VALUE/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7420.00–7490.50 |
| 2026-06-29 | +155.00 | +81.25 | -22.50 | +206.25 | LONG/IB_FORMING/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_HI | 7460.75–7468.75 |
| 2026-06-30 | +102.50 | +70.60 | +88.75 | +295.00 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/INSIDE_IB/IN_VALUE/VOL_LO | 7563.50–7567.75 |
| 2026-07-01 | +115.00 | +85.00 | +115.00 | +410.00 | LONG/IB_FORMING/IN_VALUE/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7537.75–7544.00 |
| 2026-07-02 | +220.00 | -38.75 | +187.50 | +597.50 | SHORT/IB_FORMING/IN_VALUE/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_HI | 7513.75–7521.25 |
| 2026-07-06 | +30.00 | -51.25 | -6.25 | +591.25 | LONG/ABOVE_IB/ABOVE_VAH/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7581.75–7588.50 |
| 2026-07-07 | +130.00 | +158.75 | -53.75 | +537.50 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7564.50–7567.75 |
| 2026-07-08 | +205.00 | +66.25 | +17.50 | +555.00 | LONG/BELOW_IB/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7522.75–7527.75 |
| 2026-07-09 | +136.25 | -42.50 | -22.50 | +532.50 | LONG/IB_FORMING/IN_VALUE/VOL_HI | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7582.75–7588.25 |
| 2026-07-13 | +112.50 | -40.00 | -67.50 | +465.00 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7597.25–7604.25 |
| 2026-07-14 | +56.25 | +2.50 | -36.25 | +428.75 | LONG/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7575.00–7585.25 |
| 2026-07-15 | +146.25 | +236.90 | -65.00 | +363.75 | LONG/BELOW_IB/BELOW_VAL/VOL_HI | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7604.75–7609.00 |
| 2026-07-16 | +85.00 | -34.35 | -28.75 | +335.00 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_LO | — |
| 2026-07-17 | +93.75 | +80.60 | -55.00 | +280.00 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7494.75–7497.00 |
| 2026-07-20 | +111.25 | -75.00 | +56.25 | +336.25 | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_HI | 7482.50–7483.50 |
| 2026-07-21 | +77.50 | -31.25 | -47.50 | +288.75 | LONG/IB_FORMING/ABOVE_VAH/VOL_HI | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7540.75–7541.50 |
| 2026-07-23 | +50.00 | -50.00 | -150.00 | +138.75 | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7419.25–7427.50 |
| 2026-07-27 | +190.00 | +160.00 | +190.00 | +328.75 | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7450.75–7452.75 |
| 2026-07-30 | +136.25 | +112.50 | +70.00 | +398.75 | LONG/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_HI | 7410.50–7426.75 |
| 2026-07-31 | +186.25 | +0.00 | +186.25 | +585.00 | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 7491.50–7498.75 |
| 2026-08-03 | +185.00 | +90.00 | +28.75 | +613.75 | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | LONG/INSIDE_IB/IN_VALUE/VOL_LO | 7542.75–7604.75 |
| 2026-08-05 | +102.50 | +168.75 | -33.75 | +580.00 | SHORT/IB_FORMING/IN_VALUE/VOL_LO | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 7804.50–7818.75 |
| 2026-08-06 | +100.00 | -162.50 | +8.75 | +588.75 | SHORT/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7732.00–7736.50 |
| 2026-08-07 | +30.00 | missing | -68.75 | +520.00 | LONG/IB_FORMING/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7748.25–7786.75 |
| 2026-08-10 | +68.75 | +0.00 | -32.50 | +487.50 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7792.25–7797.00 |
| 2026-08-11 | +78.75 | +112.50 | -52.50 | +435.00 | SHORT/INSIDE_IB/IN_VALUE/VOL_HI | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7749.75–7752.00 |
| 2026-08-12 | +35.00 | -146.25 | -50.00 | +385.00 | LONG/INSIDE_IB/IN_VALUE/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7767.50–7794.00 |
| 2026-08-13 | +145.00 | +248.75 | +70.00 | +455.00 | SHORT/INSIDE_IB/ABOVE_VAH/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7808.25–7810.50 |
| 2026-08-14 | +52.50 | -31.25 | -36.25 | +418.75 | SHORT/IB_FORMING/IN_VALUE/VOL_LO | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7821.75–7828.00 |
| 2026-08-17 | +31.25 | -13.75 | -32.50 | +386.25 | SHORT/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7798.00–7809.50 |
| 2026-08-18 | +46.25 | -55.00 | -56.25 | +330.00 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_HI | 7717.75–7735.25 |
| 2026-08-19 | +93.75 | -65.00 | -63.75 | +266.25 | SHORT/ABOVE_IB/ABOVE_VAH/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7734.00–7764.75 |
| 2026-08-20 | +50.00 | +118.75 | -47.50 | +218.75 | SHORT/INSIDE_IB/IN_VALUE/VOL_HI | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7693.00–7703.50 |
| 2026-08-21 | +23.75 | -40.00 | -71.25 | +147.50 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | SHORT/IB_FORMING/IN_VALUE/VOL_HI | 7692.25–7695.00 |
| 2026-08-24 | +60.00 | +22.50 | +5.00 | +152.50 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | SHORT/IB_FORMING/IN_VALUE/VOL_HI | 7672.50–7682.75 |
| 2026-08-25 | +90.00 | +77.50 | +90.00 | +242.50 | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 7674.25–7701.25 |
| 2026-08-26 | +42.50 | +0.00 | -18.75 | +223.75 | SHORT/IB_FORMING/IN_VALUE/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7673.75–7679.50 |
| 2026-08-27 | +57.50 | +27.50 | -21.25 | +202.50 | LONG/ABOVE_IB/ABOVE_VAH/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_HI | 7736.75–7746.50 |
| 2026-08-28 | +207.50 | -62.50 | -38.75 | +163.75 | SHORT/ABOVE_IB/ABOVE_VAH/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7758.25–7781.50 |
| 2026-08-31 | +22.50 | -66.25 | -0.00 | +163.75 | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7692.00–7695.50 |
| 2026-09-01 | +97.50 | +176.20 | +70.00 | +233.75 | SHORT/INSIDE_IB/IN_VALUE/VOL_LO | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7637.25–7673.75 |
| 2026-09-02 | +112.50 | +113.75 | +112.50 | +346.25 | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7649.00–7682.75 |
| 2026-09-03 | +187.50 | -3.75 | -93.75 | +252.50 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7704.25–7752.00 |
| 2026-09-04 | +140.00 | +142.50 | +140.00 | +392.50 | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 7722.50–7751.00 |
| 2026-09-08 | +72.50 | +105.00 | +72.50 | +465.00 | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | 7695.50–7701.00 |
| 2026-09-09 | +43.75 | -15.00 | -43.75 | +421.25 | LONG/BELOW_IB/BELOW_VAL/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7636.25–7643.25 |
| 2026-09-10 | +66.25 | +3.75 | -48.75 | +372.50 | LONG/IB_FORMING/IN_VALUE/VOL_LO | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7595.75–7620.00 |
| 2026-09-11 | +55.00 | -86.25 | -106.25 | +266.25 | LONG/INSIDE_IB/BELOW_VAL/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7675.00–7679.00 |
| 2026-09-14 | +137.50 | +78.75 | -32.50 | +233.75 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/BELOW_VAL/VOL_LO | 7698.75–7706.00 |
| 2026-09-15 | +128.75 | -12.50 | -61.25 | +172.50 | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | LONG/IB_FORMING/IN_VALUE/VOL_LO | 7655.50–7659.75 |
| 2026-09-18 | +88.75 | +82.50 | +88.75 | +261.25 | SHORT/IB_FORMING/IN_VALUE/VOL_LO | SHORT/IB_FORMING/IN_VALUE/VOL_LO | 7688.00–7718.25 |
| 2026-09-21 | +268.75 | +211.25 | +268.75 | +530.00 | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7758.25–7793.25 |
| 2026-09-22 | +26.25 | +141.85 | +13.75 | +543.75 | LONG/BELOW_IB/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 7830.25–7848.50 |
| 2026-09-23 | +153.75 | +151.90 | +153.75 | +697.50 | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7779.25–7826.50 |
| 2026-09-24 | +113.75 | +61.25 | +40.00 | +737.50 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7733.00–7773.75 |
| 2026-09-25 | +103.75 | -35.00 | -101.25 | +636.25 | LONG/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7801.50–7809.75 |
| 2026-09-28 | +106.25 | -41.25 | +106.25 | +742.50 | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 7763.75–7773.50 |
| 2026-09-29 | +48.75 | -107.50 | -1.25 | +741.25 | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | 7726.25–7758.75 |
| 2026-09-30 | +65.00 | -75.00 | +65.00 | +806.25 | LONG/IB_FORMING/ABOVE_VAH/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_HI | 7731.75–7782.25 |
| 2026-10-01 | +155.00 | +182.50 | +155.00 | +961.25 | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | SHORT/IB_FORMING/BELOW_VAL/VOL_LO | 7727.75–7730.25 |
| 2026-10-02 | +97.50 | +21.25 | -110.00 | +851.25 | SHORT/INSIDE_IB/IN_VALUE/VOL_HI | LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 7771.00–7810.50 |

| **SUM** | **+7042.50** | **+2224.95** (65 days) | **+851.25** (64 trades) | | 21 distinct lessons | | |

## Lesson ledger (walk-forward record per lesson, in the order learned)

| lesson | learned | applied n | WF $ |
|---|---|---:|---:|
| LONG/INSIDE_IB/IN_VALUE/VOL_LO | 2026-06-15 | 4 | +183.75 |
| SHORT/IB_FORMING/BELOW_VAL/VOL_HI | 2026-06-16 | 8 | +446.25 |
| SHORT/IB_FORMING/IN_VALUE/VOL_HI | 2026-06-22 | 5 | +155.00 |
| LONG/IB_FORMING/BELOW_VAL/VOL_LO | 2026-06-23 | 6 | -252.50 |
| LONG/IB_FORMING/IN_VALUE/VOL_HI | 2026-06-24 | 2 | +13.75 |
| LONG/IB_FORMING/IN_VALUE/VOL_LO | 2026-06-25 | 9 | -251.25 |
| LONG/INSIDE_IB/IN_VALUE/VOL_HI | 2026-06-30 | 0 | +0.00 |
| SHORT/IB_FORMING/IN_VALUE/VOL_LO | 2026-07-02 | 7 | -40.00 |
| LONG/ABOVE_IB/ABOVE_VAH/VOL_LO | 2026-07-06 | 0 | +0.00 |
| LONG/BELOW_IB/BELOW_VAL/VOL_LO | 2026-07-08 | 0 | +0.00 |
| SHORT/INSIDE_IB/IN_VALUE/VOL_LO | 2026-07-13 | 0 | +0.00 |
| LONG/BELOW_IB/BELOW_VAL/VOL_HI | 2026-07-15 | 0 | +0.00 |
| SHORT/IB_FORMING/ABOVE_VAH/VOL_LO | 2026-07-20 | 5 | +396.25 |
| LONG/IB_FORMING/ABOVE_VAH/VOL_HI | 2026-07-21 | 2 | +43.75 |
| LONG/IB_FORMING/ABOVE_VAH/VOL_LO | 2026-08-03 | 13 | -70.00 |
| SHORT/INSIDE_IB/IN_VALUE/VOL_HI | 2026-08-06 | 0 | +0.00 |
| SHORT/INSIDE_IB/ABOVE_VAH/VOL_LO | 2026-08-13 | 0 | +0.00 |
| SHORT/ABOVE_IB/ABOVE_VAH/VOL_LO | 2026-08-19 | 0 | +0.00 |
| LONG/ABOVE_IB/ABOVE_VAH/VOL_HI | 2026-08-27 | 0 | +0.00 |
| SHORT/IB_FORMING/BELOW_VAL/VOL_LO | 2026-08-31 | 3 | +226.25 |
| LONG/INSIDE_IB/BELOW_VAL/VOL_LO | 2026-09-11 | 0 | +0.00 |

## Verdict
- Sum of best causal $: **+7042.50** over 66 sessions.
- Sum of what we took (t543ref): **+2224.95** over 65 sessions (08-07 missing).
- Sum of walk-forward lesson $: **+851.25** over 64 applied days.
- Walk-forward is positive but thin: 28W / 35L / 1 flat, avg $+13.30 per applied day; max drawdown $466.25 (peak→2026-08-21); cumulative was negative only on 2026-06-16.
- First day an applied lesson lost: **2026-06-16** (the 06-15 lesson LONG/INSIDE_IB/IN_VALUE/VOL_LO fired at 19:40 on a drive-down day). Cumulative first went negative: 2026-06-16.
- The walk-forward lessons (+851.25) earn **less than the tree took** (+2224.95) and ~12% of the best-causal ceiling (+7042.50). The day-lessons transfer weakly: the carry is in SHORT/IB_FORMING/BELOW_VAL/VOL_HI, SHORT/IB_FORMING/ABOVE_VAH/VOL_LO and SHORT/IB_FORMING/BELOW_VAL/VOL_LO; the two LONG/IB_FORMING/*/VOL_LO lessons give back ≈ $500 (see ledger).
- Nothing was tuned: one fixed method, one run. Changing the swing width, the first-match rule, or adding lesson retirement would be a second experiment, not this one.

## Appendix — 2026-10-05 (out of sample, NOT in the sums; the day the EOD VAH 7824.25 hid the stairs)

As-of VAH from `v9_tpo_history` that day: 18:00→7802.25 · 18:30→7811.25 · 19:00→7816.25 · 19:30→7818.25 · 20:00→7824.25. `v9_tpo_sessions` CASH EOD = 7824.25. The lines below use the as-of value and all 66 prior lessons.

### 2026-10-05
1. IB 7778.25–7811.25 (33.00); drive up (+36.50 above IB, close above IB); value stepped up (7778.25–7798.75 → 7796.25–7837.25).
2. Best causal: **LONG** signal bar 17:00 (close 7790.50), fill 17:05 open 7790.50, stop 7778.25 (last confirmed swing, risk 12.25), exit 17:40 7803.75 [SWING] → **+13.25 pts = $+66.25** (1 contract × $5/pt, no fee).
3. Took: t543ref missing · t529b missing → **missing**
4. Gap: $+66.25 − missing = n/a
5. Lesson: LONG when the signal bar closes **IB_FORMING** (IB 7778.25–7811.25) and **IN_VALUE** (value-as-of 7782.50–7792.00) with **VOL_HI** (signal vol 21657 = 2.09× prior-5 median) — already learned 2026-06-24.
6. Walk-forward: lesson ('LONG', 'IB_FORMING', 'IN_VALUE', 'VOL_HI') (from 2026-06-24) matched signal bar 17:00 → LONG fill 7790.50, stop 7778.25, exit 17:40 7803.75 [SWING] → **$+66.25** (cum $+851.25).

_Generated read-only by /tmp/day_lessons.py (not in repo); DB untouched; no tree/env/restart/commit._
