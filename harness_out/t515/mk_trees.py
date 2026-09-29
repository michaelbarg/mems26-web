#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): harness-only tree variants built from the LIVE tree — the turn is asked FIRST, the live tree is the
"*" branch (root renamed root_legacy + anchor). NOT the live tree. usage: python3 harness_out/t515/mk_trees.py
  wp   with the turn: CEILING_FLIP_TOUCH2|ZLR ⇒ TAKE + promote (the shadow producers at the defended extreme) · rest live
  awp  against ⇒ SKIP + wp
  aw   against ⇒ SKIP · with ⇒ TAKE + promote (every with-turn candidate) · rest live
  awg  against ⇒ SKIP · with ⇒ TAKE + promote + exit {1.5R, 2.5R} + skip_gates [entry_location_quality,
       extreme_chase_guard] (28.09 16:55 TOUCH2 SHORT at the double top died on ELQ beyond_value; 17:14 on the chase guard)"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = open(os.path.join(ROOT, "config", "decision_tree_v3.yaml"), encoding="utf-8").read()
assert LIVE.count("\nroot:\n") == 1, "live tree: expected exactly one top-level root:"
BASE = LIVE.replace("\nroot:\n", "\nroot_legacy: &root_legacy\n")
AG = '    against: {leaf: SKIP, id: against_turn, note: "T-515: the market turned against this direction (double top/bottom at the session extreme, closed bars)"}\n'
PR = "promote: [CEILING_FLIP_TOUCH2, ZLR]"
WP = ('    with:\n      split: pattern\n      branches:\n'
      f'        CEILING_FLIP_TOUCH2|ZLR: {{leaf: TAKE, id: with_turn_promote, {PR}, note: "T-515: with the turn — the shadow producers at the defended extreme go live"}}\n'
      '        "*": *root_legacy\n')
W = f'    with: {{leaf: TAKE, id: with_turn, {PR}, note: "T-515: with the turn — every with-turn candidate"}}\n'
WG = (f'    with: {{leaf: TAKE, id: with_turn_g, {PR}, exit: {{t1_r: 1.5, t2_r: 2.5}}, '
      'skip_gates: [entry_location_quality, extreme_chase_guard], note: "T-515: with the turn — ladder from the own stop, location gates off"}\n')
# 29.09 10:10 — amw measured: with-turn SHORT 76 trades +389.90$ net (3 of 4 months +), with-turn LONG 42 trades
# −426.70$ net (every month −) ⇒ the double TOP is the signal, the double bottom is not. Short-only variants:
WS = ('    with:\n      split: direction\n      branches:\n'
      f'        SHORT: {{leaf: TAKE, id: with_turn_short, {PR}, note: "T-515: short after the double top"}}\n'
      '        "*": *root_legacy\n')
WSG = ('    with:\n      split: direction\n      branches:\n'
       f'        SHORT: {{leaf: TAKE, id: with_turn_short_g, {PR}, exit: {{t1_r: 1.5, t2_r: 2.5}}, '
       'skip_gates: [entry_location_quality, extreme_chase_guard], note: "T-515: short after the double top — ladder, location gates off"}\n'
       '        "*": *root_legacy\n')
AGL = ('    against:\n      split: direction\n      branches:\n'
       '        LONG: {leaf: SKIP, id: against_turn_long, note: "T-515: no long after the double top"}\n'
       '        "*": *root_legacy\n')
# 10:26 — t515x (exit on the turn, both directions) measured −1,044.35$ net ⇒ exits dropped; the producer read was
# strongest for the FIRST-HOUR short (16:30-17:30 IL: n=30, 57%, +559.50$) ⇒ with & SHORT & phase A|B only:
WSAB = ('    with:\n      split: direction\n      branches:\n'
        '        SHORT:\n          split: phase\n          branches:\n'
        f'            "A|B": {{leaf: TAKE, id: with_turn_short_ab, {PR}, note: "T-515: first-hour short after the double top"}}\n'
        '            "*": *root_legacy\n'
        '        "*": *root_legacy\n')
# 11:01 — wsab (+16.50$ net) is the only non-negative one; 28.09 16:55 TOUCH2 SHORT at the double top died on ELQ
# beyond_value ⇒ the same first-hour leaf with the R-ladder and the two location gates skipped:
WSABG = ('    with:\n      split: direction\n      branches:\n'
         '        SHORT:\n          split: phase\n          branches:\n'
         f'            "A|B": {{leaf: TAKE, id: with_turn_short_abg, {PR}, exit: {{t1_r: 1.5, t2_r: 2.5}}, '
         'skip_gates: [entry_location_quality, extreme_chase_guard], note: "T-515: first-hour short after the double top — ladder, location gates off"}\n'
         '            "*": *root_legacy\n'
         '        "*": *root_legacy\n')
VARIANTS = {"wp": WP, "awp": AG + WP, "aw": AG + W, "awg": AG + WG,
            "ws": WS, "wsg": WSG, "aLws": AGL + WS, "aLwsg": AGL + WSG, "aL": AGL, "wsab": WSAB, "wsabg": WSABG}
for tag, body in VARIANTS.items():
    head = f"# VARIANT (harness only, 29.09 T-515 {tag}) — NOT the live tree\n"
    tail = ("\n# T-515: the turn is asked FIRST — what the market shows right now\nroot:\n  split: turn_rel\n  branches:\n"
            + body + '    "*": *root_legacy\n')
    p = os.path.join(ROOT, "harness_out", "t515", f"tree_{tag}.yaml")
    open(p, "w", encoding="utf-8").write(head + BASE + tail)
    print("wrote", p)
