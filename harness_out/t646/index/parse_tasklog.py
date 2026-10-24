#!/usr/bin/env python3
# T-646 (read-only audit helper): parse docs/plans/TASK_LOG.md table rows into JSON, print compact listing.
import re, json, sys
ROOT = '/Users/michael/Downloads/mems26_web_git'
lines = open(ROOT + '/docs/plans/TASK_LOG.md', encoding='utf-8').read().split('\n')
rows = []
for i, l in enumerate(lines):
    if not l.startswith('|'):
        continue
    m = re.match(r'^\|\s*(T-[0-9]+[A-Za-z0-9\-]*)\s*\|(.*)$', l)
    if not m:
        continue
    rid = m.group(1)
    rest = m.group(2)
    cols = rest.split('|')
    rows.append({'id': rid, 'line': i + 1, 'len': len(l), 'cols': [c.strip() for c in cols]})
json.dump(rows, open(ROOT + '/harness_out/t646/index/tasklog_rows.json', 'w'), ensure_ascii=False)
print('rows', len(rows))


def num(r):
    m = re.match(r'T-([0-9]+)', r['id'])
    return int(m.group(1)) if m else -1


lo = int(sys.argv[1]) if len(sys.argv) > 1 else 400
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 700
width = int(sys.argv[3]) if len(sys.argv) > 3 else 260
for r in rows:
    n = num(r)
    if lo <= n <= hi:
        c0 = r['cols'][0] if r['cols'] else ''
        print('%s L%d (%d) %s' % (r['id'], r['line'], r['len'], c0[:width].replace('\n', ' ')))
