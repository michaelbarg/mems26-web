import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatUsdAccounting,
  cumulativeByClose,
  cumulativeByOpen,
  equityCurveByClose,
  riskReward,
  stopMovement,
  rLevels,
} from '../tradeMath.ts';

// Minimal Trade-shaped fixtures (cast to any — type-only in production).
const mk = (o: any): any => ({
  is_synthetic: false,
  direction: 'LONG',
  system: 4,
  ...o,
});

test('formatUsdAccounting: loss in parentheses, no leading minus', () => {
  assert.equal(formatUsdAccounting(-33.75), '($33.75)');
  assert.equal(formatUsdAccounting(5), '+$5.00');
  assert.equal(formatUsdAccounting(0), '$0.00');
  assert.equal(formatUsdAccounting(null), '—');
});

test('cumulativeByClose orders by exit_ts, NOT entry_ts (the bug)', () => {
  // A entered first (09:00) but closed last (12:00); B entered later, closed first.
  const A = mk({ id: 1, entry_ts: '2026-06-02 09:00', exit_ts: '2026-06-02 12:00', pnl_usd: 100 });
  const B = mk({ id: 2, entry_ts: '2026-06-02 10:00', exit_ts: '2026-06-02 10:30', pnl_usd: -50 });
  const close = cumulativeByClose([A, B]);
  // close order = B(-50) then A(+50)
  assert.equal(close.get(2), -50); // if reverted to entry_ts ordering -> this becomes 50 -> RED
  assert.equal(close.get(1), 50);
  const open = cumulativeByOpen([A, B]);
  // open order = A(+100) then B(+50)
  assert.equal(open.get(1), 100);
  assert.equal(open.get(2), 50);
});

test('equityCurveByClose maxDd from close order', () => {
  const A = mk({ id: 1, entry_ts: '2026-06-02 09:00', exit_ts: '2026-06-02 12:00', pnl_usd: 100 });
  const B = mk({ id: 2, entry_ts: '2026-06-02 10:00', exit_ts: '2026-06-02 10:30', pnl_usd: -50 });
  const { points, maxDd } = equityCurveByClose([A, B]);
  assert.equal(points[0].id, 2); // B closes first
  assert.equal(points[1].id, 1);
  assert.equal(maxDd, 50);
});

test('riskReward null when no T1', () => {
  assert.equal(riskReward(mk({ id: 1, entry_price: 100, stop_initial: 99, t1: null })), null);
  const rr = riskReward(mk({ id: 2, entry_price: 100, stop_initial: 99, t1: 102, t2: 103 }));
  assert.ok(rr && Math.abs((rr.t1 as number) - 2) < 1e-9);
});

test('stopMovement: moved / static / t1_no_be', () => {
  assert.equal(stopMovement(mk({ stop_initial: 7616.25, stop: 7615.75 })), 'moved');
  assert.equal(stopMovement(mk({ stop_initial: 7610.5, stop: 7610.5 })), 'static');
  assert.equal(stopMovement(mk({ stop_initial: 99, stop: 99, stop_issue: 'T1_NO_BE' })), 't1_no_be');
});

test('rLevels: SHORT favorable direction, stop = -1R', () => {
  const l = rLevels(mk({ direction: 'SHORT', entry_price: 7616, stop_initial: 7616.25, t1: 7615.75, pnl_r: -1 }));
  assert.equal(l.stopR, -1);
  assert.ok(Math.abs((l.t1R as number) - 1) < 1e-9); // (7616-7615.75)/0.25 = 1
});
