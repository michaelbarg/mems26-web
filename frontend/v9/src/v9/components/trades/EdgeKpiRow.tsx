'use client';
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import type { Trade } from '../../types';
import { equityCurveByClose, formatUsdAccounting, rLevels } from '../../lib/tradeMath';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';

function pnlColor(v: number): string {
  if (v > 0) return 'var(--green)';
  if (v < 0) return 'var(--red)';
  return 'var(--text-secondary)';
}

interface EdgeKpis {
  net: number;
  winPct: number | null;
  pf: number | null;
  expectancy: number | null;
  maxDd: number;
  bestStreak: number;
  totalR: number;
  avgRR: number | null;
}

const tsKey = (s: string | null | undefined): string => s ?? '';

function computeEdge(trades: Trade[]): EdgeKpis {
  const real = trades.filter((t) => !t.is_synthetic);
  const withPnl = real.filter((t) => t.pnl_usd != null);
  const decided = withPnl.filter((t) => t.pnl_usd !== 0);

  const wins = decided.filter((t) => (t.pnl_usd ?? 0) > 0);
  const losses = decided.filter((t) => (t.pnl_usd ?? 0) < 0);
  const grossWin = wins.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);
  const grossLoss = losses.reduce((s, t) => s + Math.abs(t.pnl_usd ?? 0), 0);
  const net = withPnl.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);

  const winPct =
    wins.length + losses.length > 0 ? (wins.length / (wins.length + losses.length)) * 100 : null;
  const pf = grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : null;
  const closedCount = withPnl.length;
  const expectancy = closedCount > 0 ? net / closedCount : null;

  // Max drawdown — realised, ordered by exit_ts (shared helper, NOT entry_ts).
  const { maxDd } = equityCurveByClose(real);

  // Best win streak in realised (close) order.
  const byClose = withPnl
    .filter((t) => t.exit_ts)
    .slice()
    .sort((a, b) => {
      const ka = tsKey(a.exit_ts), kb = tsKey(b.exit_ts);
      return ka < kb ? -1 : ka > kb ? 1 : a.id - b.id;
    });
  let bestStreak = 0;
  let cur = 0;
  for (const t of byClose) {
    if ((t.pnl_usd ?? 0) > 0) {
      cur += 1;
      if (cur > bestStreak) bestStreak = cur;
    } else if ((t.pnl_usd ?? 0) < 0) {
      cur = 0;
    }
  }

  const totalR = withPnl.reduce((s, t) => s + (t.pnl_r ?? 0), 0);

  // Average planned R:R to T2 across trades that have a T1.
  const rr = real.map((t) => rLevels(t).t2R).filter((v): v is number => v != null);
  const avgRR = rr.length ? rr.reduce((s, v) => s + v, 0) / rr.length : null;

  return { net, winPct, pf, expectancy, maxDd, bestStreak, totalR, avgRR };
}

function fmtPF(v: number | null): string {
  if (v == null) return '---';
  if (!Number.isFinite(v)) return '\u221e';
  return v.toFixed(2);
}

export function EdgeKpiRow() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const trades = filteredTrades();
  const kpis = useMemo(() => computeEdge(trades), [trades]);
  const { points } = useMemo(() => equityCurveByClose(trades), [trades]);
  const curveColor = kpis.net >= 0 ? 'var(--green)' : 'var(--red)';
  const chartData = [{ cum: 0 }, ...points.map((p) => ({ cum: p.cum }))];

  const kvp = (label: string, value: string, color: string) => (
    <span style={{ fontFamily: 'var(--mono)' }}>
      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{label} </span>
      <b style={{ color, fontWeight: 700 }}>{value}</b>
    </span>
  );

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '7px 20px',
        padding: '9px 14px',
        marginTop: 9,
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        fontFamily: 'var(--mono)',
        fontSize: 12,
      }}
    >
      {kvp('Net', formatUsdAccounting(kpis.net), pnlColor(kpis.net))}
      {kvp('Win%', kpis.winPct != null ? `${kpis.winPct.toFixed(1)}%` : '---', kpis.winPct != null && kpis.winPct >= 50 ? 'var(--green)' : 'var(--text-primary)')}
      {kvp('PF', fmtPF(kpis.pf), 'var(--text-primary)')}
      {kvp('Exp', kpis.expectancy != null ? formatUsdAccounting(kpis.expectancy) : '---', kpis.expectancy != null ? pnlColor(kpis.expectancy) : 'var(--text-muted)')}
      {kvp('Max DD', kpis.maxDd > 0 ? formatUsdAccounting(-kpis.maxDd) : '$0.00', kpis.maxDd > 0 ? 'var(--red)' : 'var(--text-secondary)')}
      {kvp('R:R~', kpis.avgRR != null ? `1:${kpis.avgRR.toFixed(1)}` : '---', 'var(--text-primary)')}
      {kvp('Streak', String(kpis.bestStreak), kpis.bestStreak >= 3 ? 'var(--green)' : 'var(--text-secondary)')}
      {kvp('\u03A3R', kpis.totalR !== 0 ? `${kpis.totalR >= 0 ? '+' : ''}${kpis.totalR.toFixed(2)}` : '---', pnlColor(kpis.totalR))}
      <span style={{ flex: 1 }} />
      {chartData.length > 1 && (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>equity</span>
          <span style={{ position: 'relative', width: 150, height: 30, display: 'inline-block' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
                <defs>
                  <linearGradient id="edgeEq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={curveColor} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={curveColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="cum" stroke={curveColor} strokeWidth={1.5} fill="url(#edgeEq)" dot={false} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </span>
        </span>
      )}
    </div>
  );
}
