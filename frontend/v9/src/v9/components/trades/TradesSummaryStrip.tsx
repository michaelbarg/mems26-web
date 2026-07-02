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

/** ET (America/New_York) date, DST-safe — same convention as tradeStore.toETDate. */
const _etFmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
function etDate(ts: string): string {
  try { return _etFmt.format(new Date(ts)); } catch { return ts.slice(0, 10); }
}

/** Mode badge colors — same palette as TopBar.MODE_STYLES / design tokens. */
const MODE_META: Record<string, { label: string; color: string }> = {
  SHADOW: { label: 'SHADOW', color: '#facc15' },
  SIM: { label: 'DEMO', color: '#06b6d4' },
  LIVE: { label: 'LIVE', color: '#dc2626' },
};

interface ModeAgg {
  mode: string;
  count: number;
  wins: number;
  losses: number;
  net: number;
}

/** Today's (ET) per-mode aggregation — from ALL loaded trades, independent of
 *  the filter bar, so "מה קרה היום" is always answered. W/L/net accumulation
 *  adapted from TradeReviewPanel.summary (orphan). */
function aggregateToday(trades: Trade[]): { modes: ModeAgg[]; total: ModeAgg } {
  const today = _etFmt.format(new Date());
  const byMode = new Map<string, ModeAgg>();
  const total: ModeAgg = { mode: 'ALL', count: 0, wins: 0, losses: 0, net: 0 };
  for (const t of trades) {
    if (t.is_synthetic) continue;
    if (!t.entry_ts || etDate(t.entry_ts) !== today) continue;
    const key = t.mode || '?';
    let agg = byMode.get(key);
    if (!agg) {
      agg = { mode: key, count: 0, wins: 0, losses: 0, net: 0 };
      byMode.set(key, agg);
    }
    agg.count += 1;
    total.count += 1;
    if (t.pnl_usd != null) {
      agg.net += t.pnl_usd;
      total.net += t.pnl_usd;
      if (t.pnl_usd > 0) { agg.wins += 1; total.wins += 1; }
      else if (t.pnl_usd < 0) { agg.losses += 1; total.losses += 1; }
    }
  }
  const order = ['LIVE', 'SIM', 'SHADOW'];
  const modes = [...byMode.values()].sort(
    (a, b) => (order.indexOf(a.mode) === -1 ? 99 : order.indexOf(a.mode)) - (order.indexOf(b.mode) === -1 ? 99 : order.indexOf(b.mode)),
  );
  return { modes, total };
}

function TodayModeChip({ agg, accent }: { agg: ModeAgg; accent?: string }) {
  const meta = MODE_META[agg.mode];
  const color = accent ?? meta?.color ?? 'var(--text-secondary)';
  return (
    <div
      className="rounded px-3 py-1.5 min-w-[132px]"
      style={{ background: 'var(--bg-primary)', border: `1px solid ${color}55` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-semibold" style={{ color }}>
          {meta?.label ?? agg.mode}
        </span>
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{agg.count} tr</span>
      </div>
      <div className="flex items-baseline gap-2 font-mono">
        <span className="text-sm font-bold" style={{ color: pnlColor(agg.net) }}>
          {agg.net >= 0 ? '+' : ''}${agg.net.toFixed(2)}
        </span>
        <span className="text-[10px]">
          <span style={{ color: 'var(--green)' }}>{agg.wins}W</span>
          <span style={{ color: 'var(--text-muted)' }}> / </span>
          <span style={{ color: 'var(--red)' }}>{agg.losses}L</span>
        </span>
      </div>
    </div>
  );
}

export function TradesSummaryStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = useTradeStore((s) => s.trades);
  const trades = filteredTrades();

  const today = useMemo(() => aggregateToday(allTrades), [allTrades]);

  const stats = useMemo(() => {
    // Exclude synthetic from all aggregates (shown with badge but not counted in stats)
    const real = trades.filter((t) => !t.is_synthetic);
    const closed = real.filter((t) => t.state === 'CLOSED' || (t.pnl_usd != null && t.outcome !== 'OPEN'));
    const withPnl = real.filter((t) => t.pnl_usd != null && t.pnl_usd !== 0);
    const partialCount = real.filter((t) => t.pnl_mode === 'partial').length;
    const wins = withPnl.filter((t) => (t.pnl_usd ?? 0) > 0);
    const losses = withPnl.filter((t) => (t.pnl_usd ?? 0) < 0);
    const scratch = closed.filter((t) => (t.pnl_usd ?? 0) === 0);
    const open = real.filter((t) => t.outcome === 'OPEN' || ['FILLED', 'PARTIAL', 'PENDING'].includes(t.state ?? ''));

    const bySystem: Record<number, { count: number; pnl: number; wins: number; losses: number }> = {};
    for (const t of real) {
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

    const grossWins = wins.reduce((acc, t) => acc + (t.pnl_usd ?? 0), 0);
    const grossLosses = Math.abs(losses.reduce((acc, t) => acc + (t.pnl_usd ?? 0), 0));
    const profitFactor = grossLosses > 0 ? grossWins / grossLosses : grossWins > 0 ? Infinity : 0;

    const riskPts = real
      .map((t) => {
        const init = (t as any).stop_initial ?? t.stop;
        return init != null && t.entry_price != null ? Math.abs(t.entry_price - init) : null;
      })
      .filter((r): r is number => r != null && r > 0);
    const avgRisk = riskPts.length > 0 ? riskPts.reduce((a, b) => a + b, 0) / riskPts.length : null;

    const biggestLoss = losses.length > 0 ? Math.min(...losses.map((t) => t.pnl_usd ?? 0)) : null;

    return {
      total: sumPnl(real.filter((t) => t.pnl_usd != null)),
      partialCount,
      closedCount: closed.length,
      tradeCount: real.length,
      syntheticCount: trades.length - real.length,
      wins: wCount,
      losses: lCount,
      scratch: scratch.length,
      open: open.length,
      winRate,
      totalR,
      profitFactor,
      avgRisk,
      biggestLoss,
      systemRows,
    };
  }, [trades]);

  return (
    <div
      className="px-4 py-3 border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Today (ET) per mode — from all loaded trades, independent of the filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-3 pb-3 border-b" style={{ borderColor: 'var(--border)' }}>
        <div>
          <div className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            היום (ET)
          </div>
          <div className="font-mono text-2xl font-bold" style={{ color: pnlColor(today.total.net) }}>
            {today.total.net >= 0 ? '+' : ''}${today.total.net.toFixed(2)}
          </div>
          <div className="text-[11px] mt-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>
            {today.total.count} עסקאות ·{' '}
            <span style={{ color: 'var(--green)' }}>{today.total.wins}W</span>
            {' / '}
            <span style={{ color: 'var(--red)' }}>{today.total.losses}L</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {today.modes.map((m) => (
            <TodayModeChip key={m.mode} agg={m} />
          ))}
          {today.modes.length === 0 && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>אין עסקאות היום (עדיין)</span>
          )}
        </div>
      </div>

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
          <StatChip
            label="PF"
            value={stats.profitFactor === Infinity ? '∞' : stats.profitFactor > 0 ? stats.profitFactor.toFixed(2) : '—'}
            color={stats.profitFactor >= 1.5 ? 'var(--green)' : stats.profitFactor >= 1.0 ? 'var(--text-secondary)' : 'var(--red)'}
          />
          <StatChip
            label="Avg Risk"
            value={stats.avgRisk != null ? `${stats.avgRisk.toFixed(1)}pt` : '—'}
            color={stats.avgRisk != null && stats.avgRisk > 25 ? 'var(--red)' : stats.avgRisk != null && stats.avgRisk > 10 ? '#eab308' : 'var(--green)'}
          />
          <StatChip
            label="Max Loss"
            value={stats.biggestLoss != null ? `$${Math.abs(stats.biggestLoss).toFixed(0)}` : '—'}
            color="var(--red)"
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
