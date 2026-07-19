'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStateStore } from '../../store/systemStateStore';
import { useSystemStore } from '../../stores/systemStore';
import { useTradeStore } from '../../stores/tradeStore';

/** T14: CCI/Trend from /woodies/current via systemStateStore (not dead woodiesBars). */
export function System4Panel() {
  const s4raw = useSystemStateStore((s) => s.systems[4]?.raw) as {
    cci_14?: number | null;
    cci_6_tcci?: number | null;
    trend_state?: string | null;
    active_patterns?: Array<{ pattern_id?: string; direction?: string; zlr_detected?: boolean }>;
    zlr_detected?: boolean;
    zlr_direction?: string | null;
  } | undefined;
  const allSignals = useSystemStore((s) => s.signals);
  const sys4Signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 4), [allSignals]);
  const trades = useTradeStore((s) => s.trades);
  const sys4Trades = useMemo(() => trades.filter((t) => t.system === 4), [trades]);
  const shadowTrades = useMemo(() => sys4Trades.filter((t) => t.mode === 'SHADOW'), [sys4Trades]);
  const shadowWins = shadowTrades.filter((t) => t.outcome === 'WIN').length;
  const shadowLosses = shadowTrades.filter((t) => t.outcome === 'LOSS').length;
  const shadowPnl = shadowTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);

  const cci = s4raw?.cci_14;
  const tcci = s4raw?.cci_6_tcci;
  const trend = s4raw?.trend_state;
  const zlr = s4raw?.zlr_detected || s4raw?.active_patterns?.some((p) => p.pattern_id === 'ZLR');
  const zlrDir = s4raw?.zlr_direction || s4raw?.active_patterns?.find((p) => p.pattern_id === 'ZLR')?.direction;

  return (
    <SystemPanelWrapper systemId={4}>
      <div className="space-y-0.5 mt-1 font-mono" style={{ color: 'var(--text-secondary)' }}>
        <div>
          <span className="opacity-60">Setups: </span>
          <span>{sys4Signals.length}</span>
        </div>
        <div>
          <span className="opacity-60">SHADOW: </span>
          <span>{shadowTrades.length} ({shadowWins}W {shadowLosses}L)</span>
        </div>
        <div>
          <span className="opacity-60">PnL: </span>
          <span style={{ color: shadowPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
            ${shadowPnl.toFixed(0)}
          </span>
        </div>
        <div className="border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
          <div className="flex justify-between">
            <span className="opacity-60">CCI-14:</span>
            <span style={{ color: (cci ?? 0) > 0 ? 'var(--green)' : 'var(--red)' }}>
              {cci != null ? cci.toFixed(1) : '\u2014'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-60">TCCI:</span>
            <span>{tcci != null ? tcci.toFixed(1) : '\u2014'}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-60">Trend:</span>
            <span>{trend ?? '\u2014'}</span>
          </div>
          {zlr && (
            <div className="mt-1 px-1 rounded text-center" style={{
              background: 'rgba(251,149,11,0.15)',
              color: '#fb950b',
            }}>
              ZLR {zlrDir ?? ''}
            </div>
          )}
        </div>
      </div>
    </SystemPanelWrapper>
  );
}
