'use client';
import { Fragment, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId } from '../../types';
import { cellClass, contractHits, contractsPnlLine, excursionLine, pnlCell, systemsAgreementLine, tradePathLine } from './tradeRowFormat';
import { tradeWhen } from '../../lib/tradeTime';
import { TradeRowExpand } from './TradeRowExpand';
import { patternKey } from './PatternPerformanceStrip';
import { TradePathVisual } from './TradePathVisual';
import { riskReward } from '../../lib/tradeMath';

type RowView = 'visual' | 'classic';

const TD = `${cellClass()} px-2 py-1.5 align-top`;
const COLS_CLASSIC = 12;
const COLS_VISUAL = 11; // Path + Range merge into one visual column

export function TradesTable() {
  const { filteredTrades, expandedTradeId, toggleExpandedTradeId, filters, setFilters } = useTradeStore();
  const trades = filteredTrades();
  const activePattern = (filters.pattern ?? '').trim().toUpperCase();
  const [rowView, setRowView] = useState<RowView>('visual');

  const cols = rowView === 'visual' ? COLS_VISUAL : COLS_CLASSIC;

  return (
    <div className="overflow-x-auto">
      {/* View toggle */}
      <div
        className="sticky top-0 z-10 flex items-center justify-end px-3 py-1"
        style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-1" style={{ fontSize: 10, fontFamily: 'ui-monospace, monospace' }}>
          <button
            onClick={() => setRowView('visual')}
            className="px-2 py-0.5 rounded"
            style={{
              background: rowView === 'visual' ? 'rgba(59,130,246,0.15)' : 'transparent',
              color: rowView === 'visual' ? 'var(--sys1)' : 'var(--text-muted)',
              border: rowView === 'visual' ? '1px solid var(--sys1)' : '1px solid transparent',
            }}
          >
            Visual
          </button>
          <button
            onClick={() => setRowView('classic')}
            className="px-2 py-0.5 rounded"
            style={{
              background: rowView === 'classic' ? 'rgba(59,130,246,0.15)' : 'transparent',
              color: rowView === 'classic' ? 'var(--sys1)' : 'var(--text-muted)',
              border: rowView === 'classic' ? '1px solid var(--sys1)' : '1px solid transparent',
            }}
          >
            Classic
          </button>
        </div>
      </div>
      <table className={`w-full ${rowView === 'classic' ? 'min-w-[1280px]' : 'min-w-[1100px]'} border-collapse ${cellClass()}`}>
        <thead>
          <tr
            className="sticky top-[29px] uppercase tracking-wide"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)', fontSize: '10px' }}
          >
            <th className="text-left px-2 py-2 font-medium w-6" />
            <th className="text-left px-2 py-2 font-medium">#</th>
            <th className="text-left px-2 py-2 font-medium">When</th>
            <th className="text-left px-2 py-2 font-medium">Sys</th>
            <th className="text-left px-2 py-2 font-medium">Dir</th>
            {rowView === 'classic' ? (
              <>
                <th className="text-left px-2 py-2 font-medium min-w-[360px]">Path</th>
                <th className="text-left px-2 py-2 font-medium min-w-[200px]">Range / T1</th>
              </>
            ) : (
              <th className="text-left px-2 py-2 font-medium min-w-[520px]">Price Track</th>
            )}
            <th className="text-left px-2 py-2 font-medium min-w-[200px]" title="S*=firing ✓=agree ✗=against ·=neutral">
              Systems S1–S6
            </th>
            <th className="text-left px-2 py-2 font-medium">C1-C3</th>
            <th className="text-left px-2 py-2 font-medium">Pattern</th>
            <th className="text-right px-2 py-2 font-medium">P&L (realized)</th>
            <th className="text-left px-2 py-2 font-medium">St</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const open = expandedTradeId === t.id;
            return (
              <Fragment key={t.id}>
                <tr
                  className="border-b cursor-pointer hover:bg-[var(--bg-secondary)]"
                  style={{
                    borderColor: 'var(--border)',
                    color: t.is_synthetic ? 'var(--text-muted)' : 'var(--text-primary)',
                    background: open
                      ? 'rgba(255,255,255,0.04)'
                      : t.is_synthetic
                        ? 'rgba(234,179,8,0.03)'
                        : t.stop_issue
                          ? 'rgba(234,179,8,0.06)'
                          : undefined,
                    opacity: t.is_synthetic ? 0.6 : 1,
                  }}
                  onClick={() => toggleExpandedTradeId(t.id)}
                >
                  <td className={`${TD} w-6 text-center`} style={{ color: 'var(--text-muted)' }}>
                    {open ? '\u25bc' : '\u25b6'}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-muted)' }}>
                    {t.id}
                    {t.is_synthetic && (
                      <span
                        style={{
                          display: 'inline-block',
                          marginLeft: 4,
                          padding: '0 3px',
                          fontSize: 8,
                          fontWeight: 700,
                          borderRadius: 2,
                          background: 'rgba(234,179,8,0.2)',
                          color: '#d97706',
                          border: '1px solid rgba(234,179,8,0.3)',
                          verticalAlign: 'middle',
                        }}
                      >
                        TEST
                      </span>
                    )}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-secondary)' }}>
                    {(() => {
                      const w = tradeWhen(t.entry_ts);
                      if (!w) return '\u2014';
                      return (
                        <>
                          <span className="block">{w.date} {w.etTime} <span style={{ color: 'var(--text-muted)' }}>ET</span></span>
                          <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>{w.ilTime} IL</span>
                        </>
                      );
                    })()}
                  </td>
                  <td className={TD}>
                    <span style={{ color: SYSTEM_COLORS[(t.system as SystemId) || 1] }}>
                      S{t.system} {SYSTEM_NAMES[(t.system as SystemId) || 1]}
                    </span>
                  </td>
                  <td className={TD}>
                    <span style={{ color: t.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>
                      {t.direction}
                    </span>
                  </td>
                  {rowView === 'classic' ? (
                    <>
                      <td className={TD} title={t.stop_issue ?? undefined}>
                        {tradePathLine(t)}
                      </td>
                      <td className={TD} style={{ color: 'var(--text-secondary)' }} title="5m bars: high/low, MFE/MAE, closest to T1">
                        {excursionLine(t) || '\u2014'}
                      </td>
                    </>
                  ) : (
                    <td className={`${TD} py-1`}>
                      <TradePathVisual trade={t} width={500} />
                    </td>
                  )}
                  <td className={TD} title={t.systems_agreement?.map((s) => `${s.name}:${s.hint ?? ''}`).join(' | ')}>
                    {systemsAgreementLine(t.systems_agreement)}
                  </td>
                  <td className={TD}>{contractHits(t)}</td>
                  <td className={TD}>
                    {(() => {
                      const key = patternKey(t);
                      if (key === '(none)') {
                        return <span style={{ color: 'var(--text-muted)' }}>\u2014</span>;
                      }
                      const isActive = activePattern === key;
                      return (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setFilters({ pattern: isActive ? null : key });
                          }}
                          className="px-1.5 py-0.5 rounded text-[10px] font-semibold hover:opacity-80"
                          style={{
                            background: isActive ? 'rgba(59,130,246,0.18)' : 'rgba(255,255,255,0.06)',
                            color: isActive ? 'var(--sys1)' : 'var(--text-primary)',
                            border: isActive ? '1px solid var(--sys1)' : '1px solid transparent',
                          }}
                          title={
                            isActive
                              ? `Clear filter (currently: ${key})`
                              : `Filter to ${key} only · ${t.trigger ?? ''}`.trim()
                          }
                        >
                          {key}
                        </button>
                      );
                    })()}
                    {t.trigger && t.trigger.toUpperCase() !== patternKey(t) && (
                      <span className="block text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {t.trigger}
                      </span>
                    )}
                    {(() => {
                      const rr = riskReward(t);
                      return rr && rr.t2 != null ? (
                        <span
                          className="block text-[10px] mt-0.5"
                          style={{ color: 'var(--text-secondary)' }}
                          title="סיכון : סיכוי עד T2 (R)"
                        >
                          R:R 1:{rr.t2.toFixed(1)}
                        </span>
                      ) : null;
                    })()}
                  </td>
                  <td className={`${TD} text-right`}>
                    {(() => {
                      const p = pnlCell(t);
                      const color =
                        t.pnl_usd != null
                          ? t.pnl_usd > 0
                            ? 'var(--green)'
                            : t.pnl_usd < 0
                              ? 'var(--red)'
                              : 'var(--text-secondary)'
                          : 'var(--text-muted)';
                      return (
                        <>
                          <span className="font-semibold block" style={{ color }}>{p.value}</span>
                          <span
                            className="block text-[10px]"
                            style={{ color: t.pnl_mode === 'partial' ? '#eab308' : 'var(--text-muted)' }}
                          >
                            {p.sub}
                          </span>
                          {t.pnl_mode === 'partial' && contractsPnlLine(t) && (
                            <span className="block text-[10px] opacity-80" style={{ color: 'var(--text-muted)' }}>
                              {contractsPnlLine(t)}
                            </span>
                          )}
                        </>
                      );
                    })()}
                  </td>
                  <td className={TD}>
                    {(() => {
                      const s = t.state ?? '';
                      const o = t.outcome;
                      const stateColor = o === 'WIN' ? 'var(--green)'
                        : o === 'LOSS' ? 'var(--red)'
                        : s === 'OPEN' || s === 'FILLED' || s === 'PARTIAL' ? '#3b82f6'
                        : 'var(--text-secondary)';
                      return (
                        <span style={{ color: stateColor, fontWeight: 600, fontSize: 10 }}>
                          {s || '\u2014'}
                          {t.stop_issue === 'T1_NO_BE' && (
                            <span style={{ marginLeft: 3, color: '#eab308', fontSize: 8, fontWeight: 700 }} title="T1 hit without breakeven stop">
                              T1_NO_BE
                            </span>
                          )}
                        </span>
                      );
                    })()}
                  </td>
                </tr>
                {open && (
                  <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <td colSpan={cols} className="p-0">
                      <TradeRowExpand trade={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
          {trades.length === 0 && (
            <tr>
              <td colSpan={cols} className={`${TD} text-center py-8`} style={{ color: 'var(--text-muted)' }}>
                No trades found matching filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
