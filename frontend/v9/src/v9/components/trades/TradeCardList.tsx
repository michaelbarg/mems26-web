'use client';
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId, Trade } from '../../types';
import { TradePathVisual } from './TradePathVisual';
import {
  formatUsdAccounting,
  riskReward,
  stopMovement,
  durationMinutes,
  formatDuration,
  cumulativeByClose,
} from '../../lib/tradeMath';
import { tradeWhen } from '../../lib/tradeTime';
import { patternKey } from './PatternPerformanceStrip';

function Sticker({ dir }: { dir: string }) {
  const long = dir === 'LONG';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 3,
        fontSize: 9,
        fontWeight: 600,
        padding: '2px 7px',
        borderRadius: 5,
        background: long ? 'rgba(86,211,100,0.15)' : 'rgba(248,81,73,0.15)',
        color: long ? 'var(--green)' : 'var(--red)',
        border: `1px solid ${long ? 'rgba(86,211,100,0.4)' : 'rgba(248,81,73,0.4)'}`,
      }}
    >
      <span style={{ fontSize: 8 }}>{long ? '▲' : '▼'}</span>
      {dir}
    </span>
  );
}

function StopTag({ trade }: { trade: Trade }) {
  const sm = stopMovement(trade);
  if (sm === 'moved')
    return <span style={{ fontSize: 8, color: 'var(--green)', border: '1px solid rgba(86,211,100,0.4)', borderRadius: 3, padding: '0 4px' }}>BE ✓</span>;
  if (sm === 't1_no_be')
    return <span style={{ fontSize: 8, color: '#eab308', border: '1px solid rgba(234,179,8,0.4)', borderRadius: 3, padding: '0 4px' }}>T1_NO_BE</span>;
  return <span style={{ fontSize: 8, color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 3, padding: '0 4px' }}>סטטי</span>;
}

function pnlColor(v: number | null | undefined): string {
  if (v == null) return 'var(--text-muted)';
  if (v > 0) return 'var(--green)';
  if (v < 0) return 'var(--red)';
  return 'var(--text-secondary)';
}

export function TradeCardList() {
  const { filteredTrades, expandedTradeId, setSelectedTradeId, filters, setFilters, auxFor } = useTradeStore();
  const trades = filteredTrades();
  const cum = useMemo(() => cumulativeByClose(trades), [trades]);
  const activePattern = (filters.pattern ?? '').trim().toUpperCase();

  if (trades.length === 0) {
    return (
      <div className="text-center py-10" style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'ui-monospace, monospace' }}>
        No trades found matching filters.
      </div>
    );
  }

  return (
    <div className="p-2" style={{ fontFamily: 'ui-monospace, monospace' }}>
      {trades.map((t) => {
        const col = SYSTEM_COLORS[(t.system as SystemId) || 1] || 'var(--text-secondary)';
        const sel = expandedTradeId === t.id;
        const rr = riskReward(t);
        const w = tradeWhen(t.entry_ts);
        const dur = formatDuration(durationMinutes(t));
        const c = cum.get(t.id);
        const key = patternKey(t);
        const isOpen = !!t.state && t.state !== 'CLOSED';
        const isParallel = auxFor(t.id)?.isParallel ?? false;
        return (
          <div
            key={t.id}
            onClick={() => setSelectedTradeId(t.id)}
            className="cursor-pointer"
            style={{
              position: 'relative',
              overflow: 'hidden',
              borderRadius: 7,
              marginBottom: 5,
              background: t.is_synthetic ? 'rgba(234,179,8,0.04)' : `${col}0d`,
              border: `1px solid ${sel ? col : `${col}2e`}`,
              boxShadow: sel ? `0 0 0 1px ${col}66` : undefined,
              opacity: t.is_synthetic ? 0.65 : 1,
              padding: '5px 11px 6px 8px',
            }}
          >
            <div style={{ position: 'absolute', top: 0, bottom: 0, right: 0, width: 3, background: col }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 34 }}>#{t.id}</span>
              <Sticker dir={t.direction} />
              <span style={{ fontSize: 12, fontWeight: 600, color: col }}>S{t.system} {SYSTEM_NAMES[(t.system as SystemId) || 1]}</span>
              {key !== '(none)' && (
                <button
                  onClick={(e) => { e.stopPropagation(); setFilters({ pattern: activePattern === key ? null : key }); }}
                  style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    background: activePattern === key ? 'rgba(88,166,255,0.18)' : 'rgba(255,255,255,0.06)',
                    color: activePattern === key ? 'var(--sys1)' : 'var(--text-secondary)',
                    border: activePattern === key ? '1px solid var(--sys1)' : '1px solid transparent',
                  }}
                >
                  {key}
                </button>
              )}
              {rr && rr.t2 != null && (
                <span style={{ fontSize: 8, color: 'var(--text-primary)', background: 'rgba(255,255,255,0.05)', borderRadius: 3, padding: '0 5px' }} title="סיכון : סיכוי עד T2">
                  R:R 1:{rr.t2.toFixed(1)}
                </span>
              )}
              <StopTag trade={t} />
              {isOpen && (
                <span style={{ fontSize: 8, color: '#eab308', border: '1px solid rgba(234,179,8,0.4)', borderRadius: 3, padding: '0 4px' }}>open</span>
              )}
              {isParallel && (
                <span title="מוצלבת — חופפת בזמן עם עסקה אחרת" style={{ fontSize: 9, color: 'var(--text-muted)' }}>⧓</span>
              )}
              <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>
                {w ? `${w.etTime} ET · ${dur}` : '—'}
              </span>
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: 15, fontWeight: 700, color: pnlColor(t.pnl_usd) }}>{formatUsdAccounting(t.pnl_usd)}</span>
              {c != null && (
                <span style={{ fontSize: 9, color: pnlColor(c), opacity: 0.85, minWidth: 56, textAlign: 'left' }} title="קומולטיב בסגירה">Σ {formatUsdAccounting(c)}</span>
              )}
            </div>
            <div style={{ marginTop: 3 }}>
              <TradePathVisual trade={t} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
