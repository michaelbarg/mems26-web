'use client';
/**
 * Heat MAE/MFE strip — SVG scatter plot matching the mockup.
 * x-axis = MAE (points), y-axis = exit R.
 * Green dots = winners, Red dots = losers, grey = scratch/BE.
 */
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

const panelStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 8,
  background: 'var(--bg-secondary)',
  padding: '13px 15px',
};

export function HeatMaeStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);

  const hasData = useMemo(() => trades.some((t) => t.mae_pts != null || t.mfe_pts != null), [trades]);

  if (trades.length === 0) {
    return (
      <div style={panelStyle}>
        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>No trades in filter</span>
      </div>
    );
  }

  // SVG dimensions
  const W = 360, H = 160, x0 = 44, x1 = 348, y0 = 14, y1 = 128;

  // Compute scales
  const maes = trades.map((t) => t.mae_pts ?? 0);
  const rs = trades.map((t) => t.pnl_r ?? 0);
  const maxMae = Math.max(...maes, 6);
  const maxR = Math.max(...rs, 3);
  const minR = Math.min(...rs, -2);

  const fx = (v: number) => x0 + (v / maxMae) * (x1 - x0);
  const fy = (v: number) => y1 - ((v - minR) / (maxR - minR)) * (y1 - y0);

  return (
    <div style={panelStyle}>
      <h4 style={{ fontSize: 12.5, color: 'var(--text-primary)', marginBottom: 3 }}>
        Heat -- MAE on winners, MFE on losers
      </h4>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 11 }}>
        {hasData ? 'mfe_pts/mae_pts per trade' : 'pending G4 -- mfe_pts/mae_pts not populated'}
      </div>

      {hasData && (
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', direction: 'ltr' }} fontFamily="ui-monospace,monospace">
          {/* zero line */}
          <line x1={x0} y1={fy(0)} x2={x1} y2={fy(0)} stroke="var(--border)" strokeDasharray="3 3" />
          {/* axis labels */}
          <text x={x1} y={H - 4} fill="var(--text-muted)" fontSize={9} textAnchor="end">MAE pts</text>
          <text x={6} y={20} fill="var(--text-muted)" fontSize={9}>exit-R</text>
          {/* dots */}
          {trades.map((t) => {
            const c = (t.pnl_usd ?? 0) > 0 ? 'var(--green)' : (t.pnl_usd ?? 0) < 0 ? 'var(--red)' : 'var(--text-muted)';
            const cx = fx(t.mae_pts ?? 0);
            const cy = fy(t.pnl_r ?? 0);
            return (
              <circle
                key={t.id}
                cx={cx.toFixed(1)}
                cy={cy.toFixed(1)}
                r={4}
                fill={c}
                opacity={0.85}
              >
                <title>{`MAE ${t.mae_pts ?? 0} / ${(t.pnl_r ?? 0).toFixed(2)}R`}</title>
              </circle>
            );
          })}
        </svg>
      )}

      {!hasData && (
        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)', lineHeight: 1.7, padding: '20px 0', textAlign: 'center' }}>
          No MAE/MFE data available
        </div>
      )}
    </div>
  );
}
