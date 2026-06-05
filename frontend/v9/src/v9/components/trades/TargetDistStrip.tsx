'use client';
/**
 * Target distribution — client-side from existing trade fields.
 * Shows T1/T2/T3 hit rates as horizontal bars per day-type (matching mockup .panel + .hbar/.track).
 */
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

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

export function TargetDistStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);

  // Group by day_type and compute T2+ hit rates
  const dayGroups = useMemo(() => {
    const map = new Map<string, { total: number; t2Plus: number }>();
    for (const t of trades) {
      const day = t.day_type ?? '(unknown)';
      let g = map.get(day);
      if (!g) { g = { total: 0, t2Plus: 0 }; map.set(day, g); }
      g.total++;
      if (t.t2_hit || t.t3_hit) g.t2Plus++;
    }
    return Array.from(map.entries()).sort((a, b) => b[1].total - a[1].total);
  }, [trades]);

  // Also compute overall stats for the header
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

  if (stats.total === 0) return <div style={panelStyle}><span style={{ color: 'var(--text-muted)', fontSize: 10 }}>No trades in filter</span></div>;

  return (
    <div style={panelStyle}>
      <h4 style={{ fontSize: 12.5, color: 'var(--text-primary)', marginBottom: 3 }}>Target Distribution</h4>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 11 }}>
        t1_hit/t2_hit/t3_hit per day_type
      </div>

      {dayGroups.length > 0 ? dayGroups.map(([day, g]) => {
        const pct = g.total > 0 ? (g.t2Plus / g.total) * 100 : 0;
        const barColor = pct < 30 ? 'var(--red)' : pct > 60 ? 'var(--green)' : 'var(--sys1)';
        return (
          <div key={day}>
            <div style={hbarStyle}>
              <span style={{ color: 'var(--text-secondary)' }}>{day}</span>
              <div style={trackStyle}>
                <i style={{ display: 'block', height: '100%', width: `${pct}%`, background: barColor }} />
              </div>
              <span style={{ textAlign: 'left', color: 'var(--text-primary)' }}>{pct.toFixed(0)}% T2+</span>
            </div>
          </div>
        );
      }) : (
        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)', lineHeight: 1.7 }}>No data in filter</div>
      )}

      {/* Overall stacked bar */}
      <div style={{ marginTop: 8, display: 'flex', width: '100%', height: 18, borderRadius: 3, overflow: 'hidden', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
        {stats.t3Hit > 0 && <div style={{ width: `${(stats.t3Hit / stats.total) * 100}%`, background: 'var(--green)', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#fff', whiteSpace: 'nowrap' }}>T3 {stats.t3Hit}</span>
        </div>}
        {(stats.t2Hit - stats.t3Hit) > 0 && <div style={{ width: `${((stats.t2Hit - stats.t3Hit) / stats.total) * 100}%`, background: 'var(--sys5)', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#fff', whiteSpace: 'nowrap' }}>T2 {stats.t2Hit - stats.t3Hit}</span>
        </div>}
        {(stats.t1Hit - stats.t2Hit) > 0 && <div style={{ width: `${((stats.t1Hit - stats.t2Hit) / stats.total) * 100}%`, background: 'var(--sys1)', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#fff', whiteSpace: 'nowrap' }}>T1 {stats.t1Hit - stats.t2Hit}</span>
        </div>}
        {stats.scratch > 0 && <div style={{ width: `${(stats.scratch / stats.total) * 100}%`, background: '#64748b', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#fff', whiteSpace: 'nowrap' }}>BE {stats.scratch}</span>
        </div>}
        {stats.stopHit > 0 && <div style={{ width: `${(stats.stopHit / stats.total) * 100}%`, background: 'var(--red)', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#fff', whiteSpace: 'nowrap' }}>Stop {stats.stopHit}</span>
        </div>}
      </div>
    </div>
  );
}
