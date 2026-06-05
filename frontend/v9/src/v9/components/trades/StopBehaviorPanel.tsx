'use client';
/**
 * StopBehaviorPanel — dedicated stop management analysis panel.
 * Shows BE/static/T1_NO_BE distribution from tradeMath.stopMovement.
 * Existing fields only — no synthesis.
 */
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { stopMovement, type StopMovement } from '../../lib/tradeMath';

function fmtPct(n: number, total: number): string {
  return total > 0 ? `${((n / total) * 100).toFixed(1)}%` : '—';
}

export function StopBehaviorPanel() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);
  const [open, setOpen] = useState(false);

  const stats = useMemo(() => {
    const buckets: Record<StopMovement, { count: number; totalPnl: number; wins: number; losses: number }> = {
      moved: { count: 0, totalPnl: 0, wins: 0, losses: 0 },
      t1_no_be: { count: 0, totalPnl: 0, wins: 0, losses: 0 },
      static: { count: 0, totalPnl: 0, wins: 0, losses: 0 },
    };
    for (const t of trades) {
      const sm = stopMovement(t);
      const b = buckets[sm];
      b.count++;
      const pnl = t.pnl_usd ?? 0;
      b.totalPnl += pnl;
      if (pnl > 0) b.wins++;
      else if (pnl < 0) b.losses++;
    }
    return buckets;
  }, [trades]);

  if (trades.length === 0) return null;

  const total = trades.length;
  const labels: { key: StopMovement; label: string; desc: string; color: string }[] = [
    { key: 'moved', label: 'BE (moved)', desc: 'Stop moved to breakeven after T1', color: 'var(--green)' },
    { key: 'static', label: 'Static (-1R)', desc: 'Stop stayed at initial level', color: 'var(--text-secondary)' },
    { key: 't1_no_be', label: 'T1 no BE', desc: 'T1 hit but stop never moved — calibration issue', color: '#eab308' },
  ];

  return (
    <div className="border-b shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Stop Behavior · {total} trades
          </span>
          {labels.map(({ key, label, color }) => (
            <span key={key} className="font-mono text-[10px]" style={{ color }}>
              {label}: {stats[key].count} ({fmtPct(stats[key].count, total)})
            </span>
          ))}
        </div>
        <button onClick={() => setOpen((o) => !o)} className="text-[10px] uppercase tracking-wide hover:underline" style={{ color: 'var(--text-secondary)' }}>
          {open ? '▾ Collapse' : '▸ Expand'}
        </button>
      </div>
      {open && (
        <div className="px-4 pb-2">
          <div className="grid grid-cols-3 gap-3">
            {labels.map(({ key, label, desc, color }) => {
              const b = stats[key];
              const wr = b.wins + b.losses > 0 ? (b.wins / (b.wins + b.losses)) * 100 : null;
              return (
                <div key={key} className="p-2 rounded" style={{ border: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
                  <div className="text-[11px] font-semibold font-mono" style={{ color }}>{label}</div>
                  <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{desc}</div>
                  <div className="mt-2 grid grid-cols-2 gap-1 text-[10px] font-mono">
                    <span style={{ color: 'var(--text-muted)' }}>Count</span>
                    <span style={{ color: 'var(--text-primary)' }}>{b.count} ({fmtPct(b.count, total)})</span>
                    <span style={{ color: 'var(--text-muted)' }}>Win%</span>
                    <span style={{ color: wr != null && wr >= 50 ? 'var(--green)' : wr != null ? 'var(--red)' : 'var(--text-muted)' }}>
                      {wr != null ? `${wr.toFixed(1)}%` : '—'}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>Net $</span>
                    <span style={{ color: b.totalPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                      {b.totalPnl >= 0 ? '+' : '-'}${Math.abs(b.totalPnl).toFixed(2)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          {stats.t1_no_be.count > 0 && (
            <div className="mt-2 text-[10px] font-mono p-2 rounded" style={{ background: 'rgba(234,179,8,0.08)', color: '#eab308', border: '1px solid #eab30833' }}>
              Calibration insight: {stats.t1_no_be.count} trades hit T1 but stop was never moved to breakeven. This represents potential risk reduction if Smart BE was consistently applied.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
