T-515 (29.09) — the real-time TURN (backend/v9/services/turn_state.py). Harness-only variants; NOT the live tree.
Every comparison is vs the SAME-DAY reference t515ref (history tables drift between days).

  python3 harness_out/t515/report.py   <tag> [<tag> ...]      day-total, exits, leaves, 28.09 in full
  python3 harness_out/t515/diff_dir.py <tag> [ref]            added / removed / exit-changed, by direction
  python3 harness_out/t494/cmp_vs_live.py <tag> t515ref [--days --trades]
  python3 harness_out/t515/turn_as_producer.py [k] [maxR]     the detector's own opinion quality (no gates/slot)
  python3 harness_out/t515/cmp_latch.py                       v1 vs the latched turn (rejected: +54$ vs +345$)
  python3 harness_out/t515/into_extreme.py [tag] [k]          entries near the session extreme needing a break
  python3 harness_out/t515/mk_trees.py                        rebuilds every tree_*.yaml from the live tree

tag        tree / env                                              net vs t515ref
t515a      tree_a       against ⇒ SKIP                              −82.80$
t515am     tree_am      + mid ⇒ SKIP                                −287.70$
t515amw    tree_amw     + with ⇒ TAKE (promote TOUCH2/ZLR)          −561.95$
t515x      live + TURN_EXIT_V1=1 (out at the open, both sides)      −1,044.35$
t515xLr    live + TURN_EXIT_V1=longr (ruled 11.09 realize, early)   −83.30$
t515ws     tree_ws      with & SHORT ⇒ TAKE + promote               −75.35$
t515wsab   tree_wsab    with & SHORT & phase A|B ⇒ TAKE + promote   +16.50$  (4 better / 6 worse — noise)
t515wsg    tree_wsg     ws + ladder 1.5R/2.5R + skip ELQ/chase      −445.05$
t515wsabg  tree_wsabg   wsab + ladder + skip ELQ/chase              −166.65$
T-514 re-measured vs t515ref: t514tbr −76.80 · t514xs −628.15 · t514zlr −334.60 · t514p17 (no S5) −21.25

Queues: run_queue.sh (ref×3, a, am, amw) → run_queue1b.sh (closed queue 1 after amw; amwe dropped) → run_queue2.sh
(t515ref full, t515x) → run_queue3b.sh (adaptive: reads queue3b.list before every run). ≤2 sessions in parallel,
outside RTH only.
