'use client';
/**
 * StopBehaviorPanel — dedicated stop management analysis panel.
 * Shows BE/static/T1_NO_BE distribution from tradeMath.stopMovement.
 * Existing fields only — no synthesis.
 * Layout: two-column .panel cards matching mockup.
 */
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { stopMovement, type StopMovement } from '../../lib/tradeMath';

function fmtPct(n: number, total: number): string {
  return total > 0 ? `${((n / total) * 100).toFixed(1)}%` : '---';
}
function fmtUsd(v: number): string {
  return v >= 0 ? `+$${v.toFixed(2)}` : `($${Math.abs(v).toFixed(2)})`;
}

const panelStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 8,
  background: 'var(--bg-secondary)',
  padding: '13px 15px',
};

const hbarStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '96px 1fr 64px',
  alignItems: 'center',
  gap: 9,
  marginBottom: 8,
  fontFamily: 'var(--mono)',
  fontSize: 11,
};

const trackStyle: React.CSSProperties = {
  height: 14,
  background: 'var(--bg-tertiary)',
  borderRadius: 3,
  overflow: 'hidden',
  boxShadow: 'inset 0 0 0 1px var(--border)',
};

export function StopBehaviorPanel() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);

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
  const noBeLosses = trades.filter((t) => stopMovement(t) === 't1_no_be' && (t.pnl_usd ?? 0) < 0);
  const noBeLost = noBeLosses.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);

  return (
    <div style={{ marginTop: 14 }}>
      {/* Section label */}
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.7, fontFamily: 'var(--mono)', margin: '20px 2px 8px', display: 'flex', alignItems: 'center', gap: 8 }}>
        Stop Behavior
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignItems: 'start' }}>
        {/* Left panel: distribution bars */}
        <div style={panelStyle}>
          <h4 style={{ fontSize: 12.5, color: 'var(--text-primary)', marginBottom: 3 }}>Stop Management Distribution</h4>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 11 }}>
            stop_initial vs stop / stop_issue
          </div>

          <div style={hbarStyle}>
            <span style={{ color: 'var(--text-secondary)' }}>BE (moved)</span>
            <div style={trackStyle}>
              <i style={{ display: 'block', height: '100%', width: `${(stats.moved.count / total) * 100}%`, background: 'var(--green)' }} />
            </div>
            <span style={{ textAlign: 'left', color: 'var(--text-primary)' }}>{stats.moved.count}</span>
          </div>

          <div style={hbarStyle}>
            <span style={{ color: 'var(--text-secondary)' }}>static -1R</span>
            <div style={trackStyle}>
              <i style={{ display: 'block', height: '100%', width: `${(stats.static.count / total) * 100}%`, background: 'var(--text-secondary)' }} />
            </div>
            <span style={{ textAlign: 'left', color: 'var(--text-primary)' }}>{stats.static.count}</span>
          </div>

          <div style={hbarStyle}>
            <span style={{ color: 'var(--amber)' }}>T1_NO_BE</span>
            <div style={trackStyle}>
              <i style={{ display: 'block', height: '100%', width: `${(stats.t1_no_be.count / total) * 100}%`, background: 'var(--amber)' }} />
            </div>
            <span style={{ textAlign: 'left', color: 'var(--amber)' }}>{stats.t1_no_be.count}</span>
          </div>
        </div>

        {/* Right panel: insight */}
        <div style={panelStyle}>
          <h4 style={{ fontSize: 12.5, color: 'var(--text-primary)', marginBottom: 3 }}>Calibration Insight</h4>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 11 }}>
            T1 hit but stop never moved to BE
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)', lineHeight: 1.7 }}>
            <b style={{ color: 'var(--amber)' }}>{stats.t1_no_be.count}</b> trades hit T1 but stop stayed at -1R.
            {noBeLosses.length > 0 && (
              <>
                {' '}Of those, <b style={{ color: 'var(--red)' }}>{noBeLosses.length} became losses</b> = <b style={{ color: 'var(--red)' }}>{fmtUsd(noBeLost)}</b> that
                could have been prevented with consistent Smart-BE.
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
