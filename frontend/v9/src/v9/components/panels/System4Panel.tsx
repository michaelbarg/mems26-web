'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useMarketStore } from '../../stores/marketStore';
import { useSystemStore } from '../../stores/systemStore';
import { useTradeStore } from '../../stores/tradeStore';

export function System4Panel() {
  const woodiesBars = useMarketStore((s) => s.woodiesBars);
  const latest = woodiesBars[woodiesBars.length - 1];
  const allSignals = useSystemStore((s) => s.signals);
  const sys4Signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 4), [allSignals]);
  const trades = useTradeStore((s) => s.trades);
  const sys4Trades = useMemo(() => trades.filter((t) => t.system === 4), [trades]);
  const shadowTrades = useMemo(() => sys4Trades.filter((t) => t.mode === 'SHADOW'), [sys4Trades]);
  const shadowWins = shadowTrades.filter((t) => t.outcome === 'WIN').length;
  const shadowLosses = shadowTrades.filter((t) => t.outcome === 'LOSS').length;
  const shadowPnl = shadowTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);

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
        {latest && (
          <div className="border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
            <div className="flex justify-between">
              <span className="opacity-60">CCI-14:</span>
              <span style={{ color: (latest.cci_14 ?? 0) > 0 ? 'var(--green)' : 'var(--red)' }}>
                {latest.cci_14?.toFixed(1) ?? '\u2014'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-60">TCCI:</span>
              <span>{latest.cci_6_tcci?.toFixed(1) ?? '\u2014'}</span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-60">Trend:</span>
              <span>{latest.trend_state ?? '\u2014'}</span>
            </div>
            {latest.zlr_detected && (
              <div className="mt-1 px-1 rounded text-center" style={{
                background: 'rgba(251,149,11,0.15)',
                color: '#fb950b',
              }}>
                ZLR {latest.zlr_direction ?? ''}
              </div>
            )}
          </div>
        )}
      </div>
    </SystemPanelWrapper>
  );
}
