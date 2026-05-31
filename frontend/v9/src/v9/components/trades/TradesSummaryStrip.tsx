'use client';
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId, Trade } from '../../types';

function sumPnl(trades: Trade[]): number {
  return trades.reduce((acc, t) => acc + (t.pnl_usd ?? 0), 0);
}

function pnlColor(v: number): string {
  if (v > 0) return 'var(--green)';
  if (v < 0) return 'var(--red)';
  return 'var(--text-secondary)';
}

export function TradesSummaryStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const trades = filteredTrades();

  const stats = useMemo(() => {
    const closed = trades.filter((t) => t.state === 'CLOSED' || (t.pnl_usd != null && t.outcome !== 'OPEN'));
    const withPnl = trades.filter((t) => t.pnl_usd != null && t.pnl_usd !== 0);
    const partialCount = trades.filter((t) => t.pnl_mode === 'partial').length;
    const wins = withPnl.filter((t) => (t.pnl_usd ?? 0) > 0);
    const losses = withPnl.filter((t) => (t.pnl_usd ?? 0) < 0);
    const scratch = closed.filter((t) => (t.pnl_usd ?? 0) === 0);
    const open = trades.filter((t) => t.outcome === 'OPEN' || ['FILLED', 'PARTIAL', 'PENDING'].includes(t.state ?? ''));

    const bySystem: Record<number, { count: number; pnl: number; wins: number; losses: number }> = {};
    for (const t of trades) {
      const sid = (t.system as number) || 0;
      if (!bySystem[sid]) bySystem[sid] = { count: 0, pnl: 0, wins: 0, losses: 0 };
      bySystem[sid].count += 1;
      if (t.pnl_usd != null) {
        bySystem[sid].pnl += t.pnl_usd;
        if (t.pnl_usd > 0) bySystem[sid].wins += 1;
        else if (t.pnl_usd < 0) bySystem[sid].losses += 1;
      }
    }

    const systemRows = ([1, 2, 3, 4, 5, 6] as SystemId[])
      .map((id) => ({ id, ...bySystem[id] }))
      .filter((r) => r.count > 0)
      .sort((a, b) => b.count - a.count);

    const wCount = wins.length;
    const lCount = losses.length;
    const decided = wCount + lCount;
    const winRate = decided > 0 ? (wCount / decided) * 100 : null;
    const totalR = withPnl.reduce((acc, t) => acc + ((t as any).pnl_r ?? 0), 0);

    return {
      total: sumPnl(trades.filter((t) => t.pnl_usd != null)),
      partialCount,
      closedCount: closed.length,
      tradeCount: trades.length,
      wins: wCount,
      losses: lCount,
      scratch: scratch.length,
      open: open.length,
      winRate,
      totalR,
      systemRows,
    };
  }, [trades]);

  return (
    <div
      className="px-4 py-3 border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      <div className="flex flex-wrap items-end gap-6 mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Total P&L (filtered)
          </div>
          <div className="font-mono text-2xl font-bold" style={{ color: pnlColor(stats.total) }}>
            {stats.total >= 0 ? '+' : ''}${stats.total.toFixed(2)}
          </div>
          <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {stats.tradeCount} trades · {stats.closedCount} closed
            {stats.partialCount > 0 && ` · ${stats.partialCount} partial (realized)`}
          </div>
        </div>
        <div className="flex gap-4">
          <StatChip label="Wins" value={String(stats.wins)} color="var(--green)" />
          <StatChip label="Losses" value={String(stats.losses)} color="var(--red)" />
          <StatChip label="Scratch" value={String(stats.scratch)} color="var(--text-secondary)" />
          <StatChip label="Open" value={String(stats.open)} color="var(--sys1)" />
          <StatChip
            label="Win Rate"
            value={stats.winRate != null ? `${stats.winRate.toFixed(1)}%` : '—'}
            color={stats.winRate != null && stats.winRate >= 50 ? 'var(--green)' : 'var(--text-secondary)'}
          />
          <StatChip
            label="Total R"
            value={stats.totalR !== 0 ? `${stats.totalR >= 0 ? '+' : ''}${stats.totalR.toFixed(2)}` : '—'}
            color={pnlColor(stats.totalR)}
          />
        </div>
      </div>
      <div className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
        By system
      </div>
      <div className="flex flex-wrap gap-3">
        {stats.systemRows.map((row) => (
          <div
            key={row.id}
            className="rounded px-3 py-2 min-w-[140px]"
            style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}
          >
            <div className="text-xs font-semibold" style={{ color: SYSTEM_COLORS[row.id] }}>
              S{row.id} {SYSTEM_NAMES[row.id]}
            </div>
            <div className="font-mono text-lg font-bold" style={{ color: pnlColor(row.pnl) }}>
              {row.pnl >= 0 ? '+' : ''}${row.pnl.toFixed(2)}
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {row.count} tr · W{row.wins} L{row.losses}
            </div>
          </div>
        ))}
        {stats.systemRows.length === 0 && (
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>No trades in filter</span>
        )}
      </div>
    </div>
  );
}

function StatChip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div>
      <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{label}</div>
      <div className="font-mono text-xl font-bold" style={{ color }}>{value}</div>
    </div>
  );
}
