'use client';
import { useMemo } from 'react';
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

const panelStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 8,
  background: 'var(--bg-secondary)',
  padding: '13px 15px',
  marginTop: 14,
};

export function EquityCurveStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const trades = filteredTrades();
  // Ordered by exit_ts (realised close cumulative) — NOT entry_ts.
  const { points, maxDd } = useMemo(() => equityCurveByClose(trades), [trades]);

  if (points.length < 1) {
    return null; // no closed trades with P&L
  }

  // chart needs a baseline 0 point at the start
  const chartData = [{ id: 0, label: 'Start', cum: 0, pnl: 0, outcome: '', system: 0 }, ...points];
  const finalPnl = points[points.length - 1].cum;
  // colour by sign — a falling equity must read red, not green
  const curveColor = finalPnl >= 0 ? 'var(--green)' : 'var(--red)';

  return (
    <div style={panelStyle}>
      <h4 style={{ fontSize: 12.5, color: 'var(--text-primary)', marginBottom: 3 }}>
        Equity by-close + Max DD{' '}
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: finalPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
          {formatUsdAccounting(finalPnl)}
        </span>
      </h4>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 11 }}>
        equityCurveByClose (exit_ts order){maxDd > 0 ? ` -- max DD ${formatUsdAccounting(-maxDd)}` : ''}
      </div>

      <div style={{ height: 150 }}>
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
    </div>
  );
}
