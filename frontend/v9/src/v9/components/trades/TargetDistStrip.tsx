'use client';
/**
 * Target distribution — client-side from existing trade fields.
 * Shows T1/T2/T3 hit rates as a horizontal bar.
 */
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

export function TargetDistStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);
  const [open, setOpen] = useState(false);

  const stats = useMemo(() => {
    let total = 0, t1Hit = 0, t2Hit = 0, t3Hit = 0, stopHit = 0, scratch = 0;
    for (const t of trades) {
      total++;
      if (t.t1_hit) t1Hit++;
      if (t.t2_hit) t2Hit++;
      if (t.t3_hit) t3Hit++;
      if (t.pnl_usd != null && t.pnl_usd < 0) stopHit++;
      if (t.pnl_usd != null && t.pnl_usd === 0) scratch++;
    }
    return { total, t1Hit, t2Hit, t3Hit, stopHit, scratch };
  }, [trades]);

  if (stats.total === 0) return null;

  const pct = (n: number) => stats.total > 0 ? ((n / stats.total) * 100).toFixed(1) : '0';
  const bar = (n: number, color: string, label: string) => {
    const w = stats.total > 0 ? (n / stats.total) * 100 : 0;
    if (w === 0) return null;
    return (
      <div key={label} style={{ width: `${w}%`, background: color, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 9, fontFamily: 'ui-monospace, monospace', color: '#fff', whiteSpace: 'nowrap' }}>
          {label} {n}
        </span>
      </div>
    );
  };

  return (
    <div className="border-b shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Target Distribution · {stats.total} closed
          </span>
          <span className="font-mono text-[10px]" style={{ color: 'var(--green)' }}>
            T1 {pct(stats.t1Hit)}% · T2 {pct(stats.t2Hit)}% · T3 {pct(stats.t3Hit)}%
          </span>
          <span className="font-mono text-[10px]" style={{ color: 'var(--red)' }}>
            Stop {pct(stats.stopHit)}%
          </span>
        </div>
        <button onClick={() => setOpen((o) => !o)} className="text-[10px] uppercase tracking-wide hover:underline" style={{ color: 'var(--text-secondary)' }}>
          {open ? '▾ Collapse' : '▸ Expand'}
        </button>
      </div>
      {open && (
        <div className="px-4 pb-2">
          <div style={{ display: 'flex', width: '100%', borderRadius: 4, overflow: 'hidden', border: '1px solid var(--border)' }}>
            {bar(stats.t3Hit, '#22c55e', 'T3')}
            {bar(stats.t2Hit - stats.t3Hit, '#4ade80', 'T2')}
            {bar(stats.t1Hit - stats.t2Hit, '#86efac', 'T1')}
            {bar(stats.scratch, '#64748b', 'BE')}
            {bar(stats.stopHit, '#ef4444', 'Stop')}
          </div>
          <div className="flex gap-4 mt-2 text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
            <span>T1 reached: {stats.t1Hit}/{stats.total} ({pct(stats.t1Hit)}%)</span>
            <span>T2: {stats.t2Hit}/{stats.total}</span>
            <span>T3: {stats.t3Hit}/{stats.total}</span>
            <span>Stop: {stats.stopHit}/{stats.total}</span>
          </div>
        </div>
      )}
    </div>
  );
}
