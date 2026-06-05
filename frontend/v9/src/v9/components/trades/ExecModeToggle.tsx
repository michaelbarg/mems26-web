'use client';
/**
 * Execution-mode toggle — "All" vs "Sequential (one-at-a-time)" comparison.
 *
 * Consumes existing auxStatus (isParallel/liveEligible) from tradeStore — no new gating logic.
 * Shows win% all vs sequential side-by-side.
 */
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

function winPct(trades: { pnl_usd: number | null }[]): number | null {
  let w = 0, l = 0;
  for (const t of trades) {
    if (t.pnl_usd == null) continue;
    if (t.pnl_usd > 0) w++;
    else if (t.pnl_usd < 0) l++;
  }
  const n = w + l;
  return n > 0 ? (w / n) * 100 : null;
}

function fmtPct(p: number | null): string { return p == null ? '—' : `${p.toFixed(1)}%`; }
function wrColor(p: number | null): string {
  if (p == null) return 'var(--text-muted)';
  return p >= 55 ? 'var(--green)' : p >= 45 ? 'var(--text-primary)' : p >= 30 ? '#eab308' : 'var(--red)';
}

export function ExecModeToggle() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const auxStatus = useTradeStore((s) => s.auxStatus);
  const filters = useTradeStore((s) => s.filters);
  const setFilters = useTradeStore((s) => s.setFilters);

  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic), [allTrades]);

  const seqTrades = useMemo(
    () => trades.filter((t) => auxStatus.get(t.id)?.liveEligible === true),
    [trades, auxStatus]
  );

  const allWr = useMemo(() => winPct(trades), [trades]);
  const seqWr = useMemo(() => winPct(seqTrades), [seqTrades]);

  const isSeqMode = filters.liveGated === 'eligible';

  if (trades.length === 0) return null;

  return (
    <div
      className="px-4 py-1.5 border-b shrink-0 flex items-center gap-3"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      <span className="text-[9px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Exec Mode</span>
      <button
        onClick={() => setFilters({ liveGated: isSeqMode ? 'all' : 'eligible' })}
        className="text-[10px] px-2.5 py-0.5 rounded font-semibold"
        style={{
          background: isSeqMode ? 'rgba(88,166,255,0.15)' : 'transparent',
          color: isSeqMode ? 'var(--sys1)' : 'var(--text-secondary)',
          border: `1px solid ${isSeqMode ? 'var(--sys1)' : 'var(--border)'}`,
        }}
      >
        {isSeqMode ? '1-at-a-time (Sequential)' : 'All trades'}
      </button>
      <div className="flex items-center gap-4 text-[10px] font-mono" style={{ color: 'var(--text-secondary)' }}>
        <span>
          All: <span style={{ color: wrColor(allWr), fontWeight: 700 }}>{fmtPct(allWr)}</span>
          <span style={{ color: 'var(--text-muted)' }}> ({trades.length})</span>
        </span>
        <span>
          Sequential: <span style={{ color: wrColor(seqWr), fontWeight: 700 }}>{fmtPct(seqWr)}</span>
          <span style={{ color: 'var(--text-muted)' }}> ({seqTrades.length})</span>
        </span>
      </div>
    </div>
  );
}
