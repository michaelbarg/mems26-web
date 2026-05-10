'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';
import { useTradeStore } from '../../stores/tradeStore';

export function System1Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 1), [allSignals]);
  const latest = signals[signals.length - 1];
  const trades = useTradeStore((s) => s.trades);
  const sys1Trades = useMemo(() => trades.filter((t) => t.system === 1), [trades]);
  const shadowTrades = useMemo(() => sys1Trades.filter((t) => t.mode === 'SHADOW'), [sys1Trades]);
  const demoTrades = useMemo(() => sys1Trades.filter((t) => t.mode === 'SIM'), [sys1Trades]);
  const shadowWins = shadowTrades.filter((t) => t.outcome === 'WIN').length;
  const shadowLosses = shadowTrades.filter((t) => t.outcome === 'LOSS').length;
  const shadowPnl = shadowTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
  const demoPnl = demoTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);

  return (
    <SystemPanelWrapper systemId={1}>
      <div className="space-y-1 mt-1" style={{ color: 'var(--text-secondary)' }}>
        {latest && (
          <>
            <div>
              <span className="opacity-60">Type: </span>
              <span>{(latest.payload?.day_type as string) || '\u2014'}</span>
            </div>
            <div>
              <span className="opacity-60">IB Range: </span>
              <span>{(latest.payload?.ib_range as string) || '\u2014'}</span>
            </div>
          </>
        )}
        <div>
          <span className="opacity-60">Setups: </span>
          <span>{signals.length}</span>
        </div>
        <div>
          <span className="opacity-60">SHADOW: </span>
          <span>{shadowTrades.length} ({shadowWins}W {shadowLosses}L)</span>
        </div>
        {demoTrades.length > 0 && (
          <div>
            <span className="opacity-60">DEMO: </span>
            <span>{demoTrades.length}</span>
          </div>
        )}
        <div>
          <span className="opacity-60">PnL: </span>
          <span style={{ color: shadowPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
            ${shadowPnl.toFixed(0)}
          </span>
          {demoTrades.length > 0 && (
            <span style={{ color: 'var(--text-muted)' }}> / ${demoPnl.toFixed(0)}</span>
          )}
        </div>
      </div>
    </SystemPanelWrapper>
  );
}
