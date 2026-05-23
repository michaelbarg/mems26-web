'use client';
import { Fragment } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId } from '../../types';
import { cellClass, contractHits, contractsPnlLine, excursionLine, pnlCell, systemsAgreementLine, tradePathLine } from './tradeRowFormat';
import { tradeWhen } from '../../lib/tradeTime';
import { TradeRowExpand } from './TradeRowExpand';
import { patternKey } from './PatternPerformanceStrip';

const TD = `${cellClass()} px-2 py-1.5 align-top`;
const COLS = 12;

export function TradesTable() {
  const { filteredTrades, expandedTradeId, toggleExpandedTradeId, filters, setFilters } = useTradeStore();
  const trades = filteredTrades();
  const activePattern = (filters.pattern ?? '').trim().toUpperCase();

  return (
    <div className="overflow-x-auto">
      <table className={`w-full min-w-[1280px] border-collapse ${cellClass()}`}>
        <thead>
          <tr
            className="sticky top-0 uppercase tracking-wide"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)', fontSize: '10px' }}
          >
            <th className="text-left px-2 py-2 font-medium w-6" />
            <th className="text-left px-2 py-2 font-medium">#</th>
            <th className="text-left px-2 py-2 font-medium">When</th>
            <th className="text-left px-2 py-2 font-medium">Sys</th>
            <th className="text-left px-2 py-2 font-medium">Dir</th>
            <th className="text-left px-2 py-2 font-medium min-w-[360px]">Path</th>
            <th className="text-left px-2 py-2 font-medium min-w-[200px]">Range / T1</th>
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
                    color: 'var(--text-primary)',
                    background: open
                      ? 'rgba(255,255,255,0.04)'
                      : t.stop_issue
                        ? 'rgba(234,179,8,0.06)'
                        : undefined,
                  }}
                  onClick={() => toggleExpandedTradeId(t.id)}
                >
                  <td className={`${TD} w-6 text-center`} style={{ color: 'var(--text-muted)' }}>
                    {open ? '\u25bc' : '\u25b6'}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-muted)' }}>{t.id}</td>
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
                  <td className={TD} title={t.stop_issue ?? undefined}>
                    {tradePathLine(t)}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-secondary)' }} title="5m bars: high/low, MFE/MAE, closest to T1">
                    {excursionLine(t) || '\u2014'}
                  </td>
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
                  <td className={TD} style={{ color: 'var(--text-secondary)' }}>{t.state ?? '\u2014'}</td>
                </tr>
                {open && (
                  <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <td colSpan={COLS} className="p-0">
                      <TradeRowExpand trade={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
          {trades.length === 0 && (
            <tr>
              <td colSpan={COLS} className={`${TD} text-center py-8`} style={{ color: 'var(--text-muted)' }}>
                No trades found matching filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
