# -*- coding: utf-8 -*-
"""Night-queue tree variants from the live 3.4.0 tree (text surgery, one branch each; the live file is never written):
  t567a — Variation day, phase C: counter-hint SHORT for REACTIVE_SHORT | INITIATIVE_SHORT | ZLR → TAKE
          (doctrine cells 08.10: 36 cands, 72%, +1,989$ holdout-10; the LONG side stays refused)
  t571a — auction_B_reversal: SKIP only OPENING_EXTREME_REJECT LONG (T-571: 1/7, −225$)
  t571b — auction_B_reversal: the whole leaf → SKIP (T-571: n=23, 39%, −124$, holdout −212$)
Usage: python3 harness_out/t567/make_variants.py   → config/decision_tree_v3.t567a.yaml, .t571a.yaml, .t571b.yaml"""
import re, sys, os
sys.path.insert(0, os.getcwd())
SRC = 'config/decision_tree_v3.yaml'
base = open(SRC, encoding='utf-8').read()
assert 'version: "3.4.0"' in base, 'live tree is not 3.4.0 — refuse to derive variants from an unruled tree'
def write(name, text, must_contain):
    out = f'config/decision_tree_v3.{name}.yaml'
    text = text.replace('version: "3.4.0"', f'version: "3.4.0-{name}"', 1)
    assert must_contain in text
    open(out, 'w', encoding='utf-8').write(text)
    from backend.v9.services.decision_tree import load_tree, leaves, walk
    tree = load_tree(out); n = len(leaves(tree))
    print(f'{out}: {n} leaves')
    return tree
# ── t567a ──────────────────────────────────────────────────────────────────────────────────────
old = ('      "*":\n        split: rel_bias\n        branches:\n          with: *take_with_hint\n'
       '          against: *against_fallback\n          "*": *kinds_variation\n')
assert base.count(old) == 1, base.count(old)
new = ('      "*":\n        split: rel_bias\n        branches:\n          with: *take_with_hint\n'
       '          against:\n            split: direction\n            branches:\n'
       '              SHORT:\n                split: pattern\n                branches:\n'
       '                  REACTIVE_SHORT|INITIATIVE_SHORT|ZLR:\n'
       '                    leaf: TAKE\n                    id: variation_c_against_short\n'
       '                    note: "T-567a: counter-hint SHORT on a Variation day (cell audit 08.10: REACTIVE_SHORT 71% · INITIATIVE_SHORT 60% · ZLR SHORT 57%; holdout-10 36 cands 72% +1,989$) — the LONG side stays refused"\n'
       '                  "*": *against_fallback\n'
       '              "*": *against_fallback\n'
       '          "*": *kinds_variation\n')
t = write('t567a', base.replace(old, new, 1), 'variation_c_against_short')
from backend.v9.services.decision_tree import walk
vec = dict(opening_type='OPEN_AUCTION_IN', phase='C', day_type='Variation', structure='up', pattern='REACTIVE_SHORT', kind='REVERSAL',
           direction='SHORT', rel_bias='against', zone='near_vah', edge='none', hour=18)
leaf, path = walk(t, vec); print('  t567a walk SHORT/against →', leaf.get('leaf'), leaf.get('id'))
leaf, path = walk(t, dict(vec, direction='LONG', pattern='REACTIVE_LONG')); print('  t567a walk LONG/against  →', leaf.get('leaf'), leaf.get('id'))
# ── t571b: whole leaf → SKIP ────────────────────────────────────────────────────────────────────
i = base.index('      REVERSAL:\n        leaf: TAKE\n        id: auction_B_reversal\n')
j = base.index('      "*": *kind_fallback\n', i)
old_leaf = base[i:j]
new_b = ('      REVERSAL:\n        leaf: SKIP\n        id: auction_B_reversal\n'
         '        note: "T-571b: phase B open-auction reversal at the opening extreme — refused (T-571: n=23 · 39% · −124$ · holdout-10 −212$)"\n')
t = write('t571b', base.replace(old_leaf, new_b, 1), 'T-571b')
vec_b = dict(opening_type='OPEN_AUCTION_IN', phase='B', day_type='FORMING', structure='forming', pattern='OPENING_EXTREME_REJECT', kind='REVERSAL',
             direction='LONG', rel_bias='none', zone='unknown', edge='none', hour=16)
leaf, path = walk(t, vec_b); print('  t571b walk ext-reject LONG →', leaf.get('leaf'), leaf.get('id'))
# ── t571a: SKIP only OPENING_EXTREME_REJECT LONG, the rest of the leaf unchanged ───────────────
inner = '\n'.join('    ' + l if l else l for l in old_leaf.split('\n')[1:])  # the original TAKE leaf body, indented 4 more
new_a = ('      REVERSAL:\n        split: pattern\n        branches:\n          OPENING_EXTREME_REJECT:\n'
         '            split: direction\n            branches:\n              LONG:\n                leaf: SKIP\n'
         '                id: auction_B_reversal_long_ext_reject\n'
         '                note: "T-571a: OPENING_EXTREME_REJECT LONG in the phase-B reversal leaf — 1/7, −225$ (T-571)"\n'
         '              "*":\n' + inner.replace('\n    ', '\n        ', 1).replace('\n        leaf: TAKE', '\n                leaf: TAKE') + '\n')
# simpler + safer: build the two TAKE copies explicitly
take_copy = lambda ind: (f'{ind}leaf: TAKE\n{ind}id: auction_B_reversal\n{ind}ruling: *ruling_pkg_2709\n'
                         f'{ind}note: "phase B open-auction: a reversal at the opening extreme is taken too"\n')
new_a = ('      REVERSAL:\n        split: pattern\n        branches:\n          OPENING_EXTREME_REJECT:\n'
         '            split: direction\n            branches:\n              LONG:\n                leaf: SKIP\n'
         '                id: auction_B_reversal_long_ext_reject\n'
         '                note: "T-571a: OPENING_EXTREME_REJECT LONG in the phase-B reversal leaf — 1/7, −225$ (T-571)"\n'
         '              "*":\n' + take_copy('                ') +
         '          "*":\n' + take_copy('            '))
t = write('t571a', base.replace(old_leaf, new_a, 1), 'auction_B_reversal_long_ext_reject')
leaf, path = walk(t, vec_b); print('  t571a walk ext-reject LONG  →', leaf.get('leaf'), leaf.get('id'))
leaf, path = walk(t, dict(vec_b, direction='SHORT')); print('  t571a walk ext-reject SHORT →', leaf.get('leaf'), leaf.get('id'))
leaf, path = walk(t, dict(vec_b, pattern='DALTON_EDGE_SHORT', direction='SHORT')); print('  t571a walk DALTON_EDGE_SHORT →', leaf.get('leaf'), leaf.get('id'))
