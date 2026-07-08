// Node-runnable unit test for the board logic (no framework).
// Run: node tests/board_logic.test.mjs   (from frontend/v9)
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  sortTasks, groupByLane, priorityCounts, priorityRank, LANE_META,
} from '../src/v9/components/board/boardLogic.mjs';

let passed = 0;
const check = (name, fn) => { fn(); passed += 1; console.log('  ok -', name); };

check('priority ranks order P0<P1<P2', () => {
  assert.ok(priorityRank('P0') < priorityRank('P1'));
  assert.ok(priorityRank('P1') < priorityRank('P2'));
  assert.equal(priorityRank('junk'), 99);
});

check('sortTasks orders by priority then id', () => {
  const out = sortTasks([
    { id: 'B', priority: 'P2' },
    { id: 'A', priority: 'P0' },
    { id: 'C', priority: 'P0' },
  ]);
  assert.deepEqual(out.map((t) => t.id), ['A', 'C', 'B']);
});

check('groupByLane buckets by status, unknown->open, hides empty lanes', () => {
  const lanes = groupByLane([
    { id: '1', priority: 'P0', status: 'blocked' },
    { id: '2', priority: 'P1', status: 'weird' },
    { id: '3', priority: 'P0', status: 'open' },
  ]);
  const byKey = Object.fromEntries(lanes.map((l) => [l.key, l.tasks.map((t) => t.id)]));
  assert.deepEqual(byKey.blocked, ['1']);
  assert.deepEqual(byKey.open, ['3', '2']); // both land in open, P0 before P1
  assert.ok(!('done' in byKey)); // empty lane omitted
});

check('lanes come back in LANE_META display order', () => {
  const lanes = groupByLane([
    { id: 'x', priority: 'P0', status: 'done' },
    { id: 'y', priority: 'P0', status: 'blocked' },
  ]);
  assert.deepEqual(lanes.map((l) => l.key), ['blocked', 'done']);
});

check('priorityCounts tallies', () => {
  const c = priorityCounts([
    { priority: 'P0' }, { priority: 'P0' }, { priority: 'P2' },
  ]);
  assert.deepEqual(c, { P0: 2, P1: 0, P2: 1, total: 3 });
});

// Contract check against the real seed data file.
check('task_board.json parses and every task has required fields + valid lane', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const data = JSON.parse(readFileSync(join(here, '..', 'public', 'task_board.json'), 'utf8'));
  assert.ok(Array.isArray(data.tasks) && data.tasks.length > 0);
  const laneKeys = new Set(LANE_META.map((l) => l.key));
  for (const t of data.tasks) {
    for (const f of ['id', 'title', 'priority', 'status', 'owner', 'where']) {
      assert.ok(t[f] !== undefined && t[f] !== '', `task ${t.id} missing ${f}`);
    }
    assert.ok(['P0', 'P1', 'P2'].includes(t.priority), `task ${t.id} bad priority`);
    assert.ok(laneKeys.has(t.status), `task ${t.id} bad status ${t.status}`);
  }
  // At least one real-money blocker exists and is P0.
  assert.ok(data.tasks.some((t) => t.priority === 'P0'));
});

console.log(`\nboard_logic.test.mjs: ${passed} checks passed`);
