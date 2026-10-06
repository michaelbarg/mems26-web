# STAIR_HOLD — walk-forward, exit = hold the stair · 2026-10-06

Michael 06.10 13:07 IL. Same 66 sessions and the same entries as DAY_LESSONS_2026-10-06.md (first bar closing beyond the prior bar's high/low, fill at the next bar's open, first candidate whose lesson tuple was learned on an earlier day). Only the exit changed: hold while each newly confirmed swing low is higher than the previous stair low and the bar closes above the as-of VAH (`v9_tpo_history`, created_at <= bar close); exit on the first of: stop (= the low that confirmed the stair, raised with every higher low), a close below the previous stair low, a close at/below the as-of VAH, 20:00. Shorts mirrored (VAL). Walk-forward only: day D uses lessons from days < D; the lesson learning itself is unchanged (best causal trade under the original exit), so no day's best trade enters the sum.

**$ = points x 5 · 1 contract · no fee · no slippage.** Read-only (SELECT); no YAML leaf, no .env, no restart.

```
$ python3 scripts/stair_hold.py
STAIR_HOLD walk-forward — 66 sessions · $ = points x 5 · 1 contract · no fee · read-only
self-check (ORIGINAL exit, must equal DAY_LESSONS): best-causal +7042.50 · walk-forward +851.25

day        | entry (lesson)                               | stair exit                          | WF stair $ | WF orig $ | took $   | cum $
2026-06-15 | no prior lesson matched (0 known)                 | -                                   |      0.00 |     0.00 |  +191.25 |    +0.00
2026-06-16 | L 19:40->19:45 @7613.25 LONG/INSIDE_IB/IN_VALUE/VOL_ | 19:45 @7610.50 VALUE       steps=0 |    -13.75 |   -13.75 |   +68.75 |   -13.75
2026-06-22 | S 17:20->17:25 @7571.50 SHORT/IB_FORMING/BELOW_VAL/V | 18:30 @7542.25 VALUE       steps=1 |   +146.25 |  +153.75 |   -46.25 |  +132.50
2026-06-23 | L 18:50->18:55 @7453.00 LONG/INSIDE_IB/IN_VALUE/VOL_ | 18:55 @7453.75 VALUE       steps=0 |     +3.75 |   +80.00 |    +0.00 |  +136.25
2026-06-24 | no prior lesson matched (4 known)                 | -                                   |      0.00 |     0.00 |    +0.00 |  +136.25
2026-06-25 | S 16:40->16:45 @7439.00 SHORT/IB_FORMING/BELOW_VAL/V | 17:00 @7427.75 VALUE       steps=0 |    +56.25 |    +8.75 |    +0.00 |  +192.50
2026-06-29 | S 16:55->17:00 @7458.50 SHORT/IB_FORMING/IN_VALUE/VO | 17:00 @7449.75 VALUE       steps=0 |    +43.75 |   -22.50 |   +81.25 |  +236.25
2026-06-30 | L 18:05->18:10 @7532.00 LONG/INSIDE_IB/IN_VALUE/VOL_ | 18:15 @7533.25 VALUE       steps=0 |     +6.25 |   +88.75 |   +70.60 |  +242.50
2026-07-01 | L 16:50->16:55 @7530.50 LONG/IB_FORMING/IN_VALUE/VOL | 17:10 @7549.75 VALUE       steps=0 |    +96.25 |  +115.00 |   +85.00 |  +338.75
2026-07-02 | S 17:20->17:25 @7577.25 SHORT/IB_FORMING/IN_VALUE/VO | 17:35 @7565.25 VALUE       steps=0 |    +60.00 |  +187.50 |   -38.75 |  +398.75
2026-07-06 | L 16:45->16:50 @7568.00 LONG/IB_FORMING/IN_VALUE/VOL | 16:50 @7567.25 VALUE       steps=0 |     -3.75 |    -6.25 |   -51.25 |  +395.00
2026-07-07 | L 16:40->16:45 @7580.00 LONG/IB_FORMING/IN_VALUE/VOL | 16:45 @7574.75 VALUE       steps=0 |    -26.25 |   -53.75 |  +158.75 |  +368.75
2026-07-08 | S 16:45->16:50 @7511.50 SHORT/IB_FORMING/IN_VALUE/VO | 16:50 @7511.75 VALUE       steps=0 |     -1.25 |   +17.50 |   +66.25 |  +367.50
2026-07-09 | S 17:05->17:10 @7553.50 SHORT/IB_FORMING/IN_VALUE/VO | 17:10 @7549.25 VALUE       steps=0 |    +21.25 |   -22.50 |   -42.50 |  +388.75
2026-07-13 | L 17:10->17:15 @7603.75 LONG/IB_FORMING/IN_VALUE/VOL | 17:15 @7590.25 STOP        steps=0 |    -67.50 |   -67.50 |   -40.00 |  +321.25
2026-07-14 | L 16:35->16:40 @7582.00 LONG/IB_FORMING/IN_VALUE/VOL | 16:40 @7583.25 VALUE       steps=0 |     +6.25 |   -36.25 |    +2.50 |  +327.50
2026-07-15 | L 17:05->17:10 @7610.00 LONG/IB_FORMING/IN_VALUE/VOL | 17:10 @7601.00 VALUE       steps=0 |    -45.00 |   -65.00 |  +236.90 |  +282.50
2026-07-16 | S 16:35->16:40 @7608.25 SHORT/IB_FORMING/IN_VALUE/VO | 16:40 @7612.75 VALUE       steps=0 |    -22.50 |   -28.75 |   -34.35 |  +260.00
2026-07-17 | L 16:35->16:40 @7532.75 LONG/IB_FORMING/BELOW_VAL/VO | 16:45 @7521.75 STOP        steps=0 |    -55.00 |   -55.00 |   +80.60 |  +205.00
2026-07-20 | S 16:50->16:55 @7528.75 SHORT/IB_FORMING/IN_VALUE/VO | 16:55 @7520.25 VALUE       steps=0 |    +42.50 |   +56.25 |   -75.00 |  +247.50
2026-07-21 | S 16:35->16:40 @7526.25 SHORT/IB_FORMING/IN_VALUE/VO | 16:40 @7529.50 VALUE       steps=0 |    -16.25 |   -47.50 |   -31.25 |  +231.25
2026-07-23 | L 16:35->16:40 @7474.75 LONG/IB_FORMING/BELOW_VAL/VO | 16:40 @7478.75 VALUE       steps=0 |    +20.00 |  -150.00 |   -50.00 |  +251.25
2026-07-27 | S 16:40->16:45 @7493.50 SHORT/IB_FORMING/BELOW_VAL/V | 17:55 @7455.50 VALUE       steps=0 |   +190.00 |  +190.00 |  +160.00 |  +441.25
2026-07-30 | L 16:40->16:45 @7417.25 LONG/IB_FORMING/IN_VALUE/VOL | 16:45 @7427.50 VALUE       steps=0 |    +51.25 |   +70.00 |  +112.50 |  +492.50
2026-07-31 | S 16:35->16:40 @7493.25 SHORT/IB_FORMING/ABOVE_VAH/V | 16:40 @7482.75 VALUE       steps=0 |    +52.50 |  +186.25 |    +0.00 |  +545.00
2026-08-03 | L 17:35->17:40 @7600.00 LONG/INSIDE_IB/IN_VALUE/VOL_ | 18:00 @7604.50 VALUE       steps=0 |    +22.50 |   +28.75 |   +90.00 |  +567.50
2026-08-05 | S 16:45->16:50 @7805.75 SHORT/IB_FORMING/ABOVE_VAH/V | 16:50 @7810.75 VALUE       steps=0 |    -25.00 |   -33.75 |  +168.75 |  +542.50
2026-08-06 | L 16:45->16:50 @7763.00 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7761.75 VALUE       steps=0 |     -6.25 |    +8.75 |  -162.50 |  +536.25
2026-08-07 | L 16:40->16:45 @7767.25 LONG/IB_FORMING/ABOVE_VAH/VO | 16:55 @7753.50 STOP        steps=0 |    -68.75 |   -68.75 |    miss  |  +467.50
2026-08-10 | L 16:45->16:50 @7777.75 LONG/IB_FORMING/ABOVE_VAH/VO | 16:50 @7771.25 STOP        steps=0 |    -32.50 |   -32.50 |    +0.00 |  +435.00
2026-08-11 | S 16:45->16:50 @7774.25 SHORT/IB_FORMING/BELOW_VAL/V | 17:00 @7785.00 VALUE       steps=0 |    -53.75 |   -52.50 |  +112.50 |  +381.25
2026-08-12 | S 17:00->17:05 @7764.00 SHORT/IB_FORMING/BELOW_VAL/V | 17:05 @7768.50 VALUE       steps=0 |    -22.50 |   -50.00 |  -146.25 |  +358.75
2026-08-13 | L 16:35->16:40 @7809.00 LONG/IB_FORMING/ABOVE_VAH/VO | 17:45 @7821.25 VALUE       steps=0 |    +61.25 |   +70.00 |  +248.75 |  +420.00
2026-08-14 | L 16:40->16:45 @7826.50 LONG/IB_FORMING/BELOW_VAL/VO | 16:45 @7822.00 VALUE       steps=0 |    -22.50 |   -36.25 |   -31.25 |  +397.50
2026-08-17 | L 17:10->17:15 @7797.75 LONG/IB_FORMING/IN_VALUE/VOL | 17:15 @7795.00 VALUE       steps=0 |    -13.75 |   -32.50 |   -13.75 |  +383.75
2026-08-18 | L 17:00->17:05 @7729.75 LONG/IB_FORMING/IN_VALUE/VOL | 17:05 @7725.25 VALUE       steps=0 |    -22.50 |   -56.25 |   -55.00 |  +361.25
2026-08-19 | S 16:45->16:50 @7725.00 SHORT/IB_FORMING/BELOW_VAL/V | 17:00 @7736.00 VALUE       steps=0 |    -55.00 |   -63.75 |   -65.00 |  +306.25
2026-08-20 | S 17:00->17:05 @7698.25 SHORT/IB_FORMING/IN_VALUE/VO | 17:05 @7705.00 VALUE       steps=0 |    -33.75 |   -47.50 |  +118.75 |  +272.50
2026-08-21 | S 16:50->16:55 @7679.50 SHORT/IB_FORMING/IN_VALUE/VO | 16:55 @7680.50 VALUE       steps=0 |     -5.00 |   -71.25 |   -40.00 |  +267.50
2026-08-24 | S 17:00->17:05 @7664.25 SHORT/IB_FORMING/IN_VALUE/VO | 17:05 @7663.50 VALUE       steps=0 |     +3.75 |    +5.00 |   +22.50 |  +271.25
2026-08-25 | S 16:50->16:55 @7693.25 SHORT/IB_FORMING/ABOVE_VAH/V | 16:55 @7690.00 VALUE       steps=0 |    +16.25 |   +90.00 |   +77.50 |  +287.50
2026-08-26 | L 16:40->16:45 @7695.50 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7700.75 VALUE       steps=0 |    +26.25 |   -18.75 |    +0.00 |  +313.75
2026-08-27 | L 16:40->16:45 @7723.50 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7719.25 VALUE       steps=0 |    -21.25 |   -21.25 |   +27.50 |  +292.50
2026-08-28 | L 16:35->16:40 @7751.50 LONG/IB_FORMING/ABOVE_VAH/VO | 16:50 @7746.25 VALUE       steps=0 |    -26.25 |   -38.75 |   -62.50 |  +266.25
2026-08-31 | S 17:00->17:05 @7686.00 SHORT/IB_FORMING/IN_VALUE/VO | 17:05 @7682.75 VALUE       steps=0 |    +16.25 |    -0.00 |   -66.25 |  +282.50
2026-09-01 | L 16:45->16:50 @7649.00 LONG/IB_FORMING/BELOW_VAL/VO | 16:50 @7645.25 VALUE       steps=0 |    -18.75 |   +70.00 |  +176.20 |  +263.75
2026-09-02 | L 16:40->16:45 @7654.00 LONG/IB_FORMING/ABOVE_VAH/VO | 16:45 @7647.00 VALUE       steps=0 |    -35.00 |  +112.50 |  +113.75 |  +228.75
2026-09-03 | L 16:35->16:40 @7723.00 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7706.75 VALUE       steps=0 |    -81.25 |   -93.75 |    -3.75 |  +147.50
2026-09-04 | S 16:40->16:45 @7743.50 SHORT/IB_FORMING/ABOVE_VAH/V | 16:45 @7747.25 VALUE       steps=0 |    -18.75 |  +140.00 |  +142.50 |  +128.75
2026-09-08 | S 16:35->16:40 @7702.00 SHORT/IB_FORMING/BELOW_VAL/V | 16:55 @7694.75 VALUE       steps=0 |    +36.25 |   +72.50 |  +105.00 |  +165.00
2026-09-09 | L 16:55->17:00 @7660.75 LONG/IB_FORMING/IN_VALUE/VOL | 17:00 @7658.25 VALUE       steps=0 |    -12.50 |   -43.75 |   -15.00 |  +152.50
2026-09-10 | L 16:35->16:40 @7603.50 LONG/IB_FORMING/BELOW_VAL/VO | 16:40 @7600.25 VALUE       steps=0 |    -16.25 |   -48.75 |    +3.75 |  +136.25
2026-09-11 | L 16:55->17:00 @7681.00 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7672.00 VALUE       steps=0 |    -45.00 |  -106.25 |   -86.25 |   +91.25
2026-09-14 | L 16:40->16:45 @7677.75 LONG/IB_FORMING/BELOW_VAL/VO | 16:45 @7686.50 VALUE       steps=0 |    +43.75 |   -32.50 |   +78.75 |  +135.00
2026-09-15 | L 16:40->16:45 @7682.50 LONG/IB_FORMING/IN_VALUE/VOL | 16:45 @7676.50 VALUE       steps=0 |    -30.00 |   -61.25 |   -12.50 |  +105.00
2026-09-18 | S 16:35->16:40 @7705.25 SHORT/IB_FORMING/IN_VALUE/VO | 16:40 @7705.00 VALUE       steps=0 |     +1.25 |   +88.75 |   +82.50 |  +106.25
2026-09-21 | L 16:40->16:45 @7766.25 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7772.25 VALUE       steps=0 |    +30.00 |  +268.75 |  +211.25 |  +136.25
2026-09-22 | S 16:40->16:45 @7842.75 SHORT/IB_FORMING/ABOVE_VAH/V | 16:45 @7839.75 VALUE       steps=0 |    +15.00 |   +13.75 |  +141.85 |  +151.25
2026-09-23 | S 16:35->16:40 @7817.00 SHORT/IB_FORMING/BELOW_VAL/V | 17:00 @7799.50 VALUE       steps=0 |    +87.50 |  +153.75 |  +151.90 |  +238.75
2026-09-24 | L 16:35->16:40 @7744.25 LONG/IB_FORMING/ABOVE_VAH/VO | 17:30 @7753.00 VALUE       steps=0 |    +43.75 |   +40.00 |   +61.25 |  +282.50
2026-09-25 | L 16:35->16:40 @7787.75 LONG/IB_FORMING/ABOVE_VAH/VO | 17:00 @7767.50 STOP        steps=0 |   -101.25 |  -101.25 |   -35.00 |  +181.25
2026-09-28 | S 17:10->17:15 @7762.25 SHORT/IB_FORMING/BELOW_VAL/V | 17:15 @7764.50 VALUE       steps=0 |    -11.25 |  +106.25 |   -41.25 |  +170.00
2026-09-29 | S 16:40->16:45 @7740.75 SHORT/IB_FORMING/BELOW_VAL/V | 17:00 @7738.25 VALUE       steps=0 |    +12.50 |    -1.25 |  -107.50 |  +182.50
2026-09-30 | L 16:45->16:50 @7759.00 LONG/IB_FORMING/ABOVE_VAH/VO | 17:25 @7766.25 VALUE       steps=0 |    +36.25 |   +65.00 |   -75.00 |  +218.75
2026-10-01 | S 16:40->16:45 @7720.00 SHORT/IB_FORMING/BELOW_VAL/V | 17:30 @7701.00 VALUE       steps=0 |    +95.00 |  +155.00 |  +182.50 |  +313.75
2026-10-02 | L 16:40->16:45 @7800.25 LONG/IB_FORMING/ABOVE_VAH/VO | 16:50 @7785.00 VALUE       steps=0 |    -76.25 |  -110.00 |   +21.25 |  +237.50

exit reasons (stair walk-forward): VALUE n=59 $+562.50 · STOP n=5 $-325.00
stairs climbed before exit: 0 steps: 63 trades · 1 steps: 1 trades
walk-forward stair: 64 trades · 30W / 34L / 0 flat · max drawdown $-476.25 · lessons known at end: 21
best-causal ceiling under the stair exit (hindsight picks the bar; NOT a walk-forward number): $+4355.00

THE THREE NUMBERS
  stair-hold walk-forward ........ $+237.50  (64 trades)
  the tree took (t543ref) ........ $+2224.95  (65 days)
  old lesson walk-forward ........ $+851.25  (DAY_LESSONS, same entries, swing exit)
  verdict: stair-hold does not pass the tree (לא עוברת את העץ); vs the old lesson: worse
```
