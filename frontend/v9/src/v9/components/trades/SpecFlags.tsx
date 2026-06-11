'use client';
import type { Trade } from '../../types';

const badge = (bg: string, text: string) => (
  <span
    key={text}
    style={{
      display: 'inline-block',
      fontSize: 10,
      padding: '1px 6px',
      borderRadius: 4,
      backgroundColor: bg,
      color: '#fff',
      whiteSpace: 'nowrap',
    }}
  >
    {text}
  </span>
);

function sameDay(a: string | null, b: string | null): boolean {
  if (!a || !b) return false;
  return a.slice(0, 10) === b.slice(0, 10);
}

export default function SpecFlags({ trade, allTrades }: { trade: Trade; allTrades: Trade[] }) {
  const flags: JSX.Element[] = [];

  // 1. Shared anchor
  const stop0 = trade.stop_initial ?? trade.stop;
  if (stop0 != null) {
    const shared = allTrades.filter(
      (t) =>
        t.id !== trade.id &&
        sameDay(t.entry_ts, trade.entry_ts) &&
        Math.abs((t.stop_initial ?? t.stop ?? Infinity) - stop0) <= 0.5,
    );
    if (shared.length > 0) {
      flags.push(badge('#dc2626', `\uD83D\uDD17 Shared anchor (${shared.length + 1} trades)`));
    }
  }

  // 2. Risk bounds
  const ep = trade.entry_price;
  const sl = trade.stop_initial ?? trade.stop;
  if (ep != null && sl != null) {
    const risk = Math.abs(ep - sl);
    if (risk < 2) flags.push(badge('#ca8a04', '\u26A0 Risk < 2pt'));
    else if (risk > 60) flags.push(badge('#dc2626', '\uD83D\uDEAB Risk > 60pt'));
    else if (risk >= 25) flags.push(badge('#ea580c', `\u26A0 Risk ${risk.toFixed(1)}pt`));
  }

  // 3. Re-entry after stop-out
  if (trade.pattern_id && trade.direction) {
    const prior = allTrades.find(
      (t) =>
        t.id < trade.id &&
        t.pattern_id === trade.pattern_id &&
        t.direction === trade.direction &&
        t.exit_reason === 'STOP_HIT',
    );
    if (prior) flags.push(badge('#ca8a04', '\uD83D\uDD04 Re-entry after stop-out'));
  }

  if (flags.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {flags}
    </div>
  );
}
