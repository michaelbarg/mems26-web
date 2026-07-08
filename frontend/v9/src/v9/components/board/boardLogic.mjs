// Pure, framework-agnostic board logic. Imported by StatusBoardPanel.tsx AND
// unit-tested directly by Node (board_logic.test.mjs) — no TS runner needed.

export const PRIORITY_RANK = { P0: 0, P1: 1, P2: 2 };

// Display order of the status lanes + their presentation metadata.
export const LANE_META = [
  { key: 'blocked',          label: 'Blocked',           color: 'var(--red, #f85149)',    emoji: '⛔' },
  { key: 'open',             label: 'Open',              color: 'var(--orange, #d29922)', emoji: '🔴' },
  { key: 'in_progress',      label: 'In progress',       color: 'var(--blue, #58a6ff)',   emoji: '🔵' },
  { key: 'fixed_unverified', label: 'Fixed — verify live', color: 'var(--purple, #bc8cff)', emoji: '🟣' },
  { key: 'done',             label: 'Done',              color: 'var(--green, #3fb950)',  emoji: '✅' },
];

const LANE_INDEX = Object.fromEntries(LANE_META.map((l, i) => [l.key, i]));

export function priorityRank(p) {
  const r = PRIORITY_RANK[p];
  return r === undefined ? 99 : r;
}

// Sort: priority first (P0>P1>P2), then id for stability.
export function sortTasks(tasks) {
  return [...(tasks || [])].sort((a, b) => {
    const pr = priorityRank(a.priority) - priorityRank(b.priority);
    if (pr !== 0) return pr;
    return String(a.id).localeCompare(String(b.id));
  });
}

// Group tasks into lanes (unknown status -> 'open'), each lane priority-sorted,
// returned in LANE_META display order.
export function groupByLane(tasks) {
  const buckets = {};
  for (const l of LANE_META) buckets[l.key] = [];
  for (const t of tasks || []) {
    const key = buckets[t.status] ? t.status : 'open';
    buckets[key].push(t);
  }
  return LANE_META
    .map((l) => ({ ...l, tasks: sortTasks(buckets[l.key]) }))
    .filter((l) => l.tasks.length > 0);
}

// Counts for the header, e.g. { P0: 3, P1: 4, P2: 3, total: 10 }.
export function priorityCounts(tasks) {
  const c = { P0: 0, P1: 0, P2: 0, total: 0 };
  for (const t of tasks || []) {
    if (c[t.priority] !== undefined) c[t.priority] += 1;
    c.total += 1;
  }
  return c;
}

export function laneOrderIndex(status) {
  return LANE_INDEX[status] === undefined ? LANE_INDEX.open : LANE_INDEX[status];
}
