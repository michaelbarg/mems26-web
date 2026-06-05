'use client';
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { equityCurveByClose, formatUsdAccounting, type EquityPoint } from '../../lib/tradeMath';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload as EquityPoint;
  return (
    <div
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        padding: '6px 10px',
        fontSize: 11,
        fontFamily: 'ui-monospace, monospace',
        color: 'var(--text-primary)',
      }}
    >
      <div style={{ color: 'var(--text-muted)', fontSize: 9 }}>{d.label} · S{d.system} · #{d.id}</div>
      <div>
        Trade:{' '}
        <span style={{ color: d.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
          {formatUsdAccounting(d.pnl)}
        </span>
        {d.outcome ? ` (${d.outcome})` : ''}
      </div>
      <div>
        Cumulative:{' '}
        <span style={{ color: d.cum >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>
          {formatUsdAccounting(d.cum)}
        </span>
      </div>
    </div>
  );
}

export function EquityCurveStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const trades = filteredTrades();
  // Ordered by exit_ts (realised close cumulative) — NOT entry_ts.
  const { points, maxDd } = useMemo(() => equityCurveByClose(trades), [trades]);
  const [open, setOpen] = useState(true);

  if (points.length < 1) {
    return null; // no closed trades with P&L
  }

  // chart needs a baseline 0 point at the start
  const chartData = [{ id: 0, label: 'Start', cum: 0, pnl: 0, outcome: '', system: 0 }, ...points];
  const finalPnl = points[points.length - 1].cum;
  // colour by sign — a falling equity must read red, not green
  const curveColor = finalPnl >= 0 ? 'var(--green)' : 'var(--red)';

  return (
    <div
      className="border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Equity Curve (by close)
          </span>
          <span className="font-mono text-xs font-bold" style={{ color: finalPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
            {formatUsdAccounting(finalPnl)}
          </span>
          {maxDd > 0 && (
            <span className="font-mono text-[10px]" style={{ color: 'var(--red)' }}>
              max DD {formatUsdAccounting(-maxDd)}
            </span>
          )}
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-[10px] uppercase tracking-wide hover:underline"
          style={{ color: 'var(--text-secondary)' }}
        >
          {open ? '▾ Collapse' : '▸ Expand'}
        </button>
      </div>
      {open && (
        <div className="px-2 pb-2" style={{ height: 104 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 12, bottom: 4, left: 12 }}>
              <defs>
                <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={curveColor} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={curveColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.3} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}
                interval="preserveStartEnd"
                minTickGap={90}
                tickLine={false}
                axisLine={{ stroke: 'var(--border)' }}
              />
              <YAxis
                tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}
                tickFormatter={(v: number) => (v < 0 ? `($${Math.abs(v)})` : `$${v}`)}
                tickLine={false}
                axisLine={false}
                width={58}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="4 4" strokeOpacity={0.5} />
              <Area
                type="monotone"
                dataKey="cum"
                stroke={curveColor}
                strokeWidth={1.5}
                fill="url(#equityFill)"
                dot={false}
                activeDot={{ r: 3, fill: 'var(--text-primary)', stroke: curveColor, strokeWidth: 1.5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
