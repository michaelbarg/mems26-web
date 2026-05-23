'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { SYSTEM_META } from '../../design/system_colors';
import { exitTrade, fetchActiveTrade, getApiBase } from '../../lib/api';
import { fmtTimeET, fmtTimeIL } from '../../lib/tradeTime';

interface Contract {
  id: string;
  target_price: number;
  status: 'OPEN' | 'HIT_TARGET' | 'HIT_STOP' | 'BE';
  pnl: number;
  r: number;
  smart_be: boolean;
}

interface TradeSystemChip {
  id: number;
  name: string;
  role: string;
  involved: boolean;
  is_firing: boolean;
  hint?: string | null;
  entry_price?: number | null;
}

interface ActiveTrade {
  trade_id: number;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  entry_ts: string | null;
  stop_price: number;
  firing_system?: number;
  systems?: TradeSystemChip[];
  contracts: Contract[];
  hits: number;
  total_pnl: number;
  total_r: number;
  summary: string;
  pattern_id?: string | null;
  trigger?: string | null;
  classification?: string | null;
  day_type?: string | null;
}

export type ActiveTradeContext = {
  firingSystemId: number;
  entryPrice: number;
} | null;

interface ActiveTradeCardProps {
  onTradeContext?: (ctx: ActiveTradeContext) => void;
}

const STATUS_COLORS: Record<string, string> = {
  OPEN: '#737373',
  HIT_TARGET: '#16a34a',
  HIT_STOP: '#dc2626',
  BE: '#eab308',
};

export function ActiveTradeCard({ onTradeContext }: ActiveTradeCardProps) {
  const [trade, setTrade] = useState<ActiveTrade | null>(null);

  const refreshActiveTrade = () => {
    fetchActiveTrade().then((d) => {
      const t = d && d.trade_id ? (d as unknown as ActiveTrade) : null;
      setTrade(t);
      if (onTradeContext) {
        onTradeContext(
          t?.firing_system
            ? { firingSystemId: t.firing_system, entryPrice: t.entry_price }
            : null,
        );
      }
    });
  };

  useEffect(() => {
    refreshActiveTrade();
    const id = setInterval(refreshActiveTrade, 10000);
    return () => clearInterval(id);
  }, []);

  if (!trade) {
    return (
      <div style={{
        padding: 12,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        borderRadius: 6,
        margin: 6,
        background: COLORS.bgSurface4,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: COLORS.textTertiary, fontWeight: 500 }}>
          No Active Trade
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim, marginTop: 2 }}>
          Awaiting setup confirmation
        </div>
      </div>
    );
  }

  const dirColor = trade.direction === 'LONG' ? COLORS.bull : COLORS.bear;
  // §3.6 5-state: Idle(no card) / Armed(yellow) / Active(green/red) / JustClosed(gray)
  const cardState = trade.hits > 0 || trade.total_pnl !== 0 ? 'Active' : 'Armed';
  const borderColor = cardState === 'Armed' ? '#eab308'
    : trade.total_pnl > 0 ? COLORS.bull
    : trade.total_pnl < 0 ? COLORS.bear
    : '#eab308';
  const entryTimeEt = trade.entry_ts ? fmtTimeET(trade.entry_ts) : '';
  const entryTimeIl = trade.entry_ts ? fmtTimeIL(trade.entry_ts) : '';

  return (
    <div style={{
      padding: 8,
      borderRadius: 6,
      margin: 6,
      background: COLORS.bgSurface4,
      border: `0.5px solid ${borderColor}`,
    }}>
      {/* Header: direction + entry price + time */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 11, color: dirColor, fontWeight: 700 }}>
            {trade.direction === 'LONG' ? '\u25B2' : '\u25BC'} {trade.direction}
          </span>
          <span style={{ fontSize: 10, fontWeight: 600, color: COLORS.textPrimary, fontFamily: 'ui-monospace' }}>
            {trade.entry_price.toFixed(2)}
          </span>
        </div>
        <span
          style={{ fontSize: 8, color: COLORS.textTertiary, fontFamily: 'ui-monospace', textAlign: 'right' }}
          title="Trade entry — New York / Israel"
        >
          {entryTimeEt} ET
          {entryTimeIl && (
            <>
              {' · '}
              <span style={{ color: COLORS.textDim }}>{entryTimeIl} IL</span>
            </>
          )}
        </span>
      </div>

      {(trade.pattern_id || trade.trigger) && (
        <div style={{ fontSize: 8, color: COLORS.textTertiary, marginBottom: 4, lineHeight: 1.3 }}>
          {trade.pattern_id && <span style={{ fontFamily: 'ui-monospace' }}>{trade.pattern_id}</span>}
          {trade.pattern_id && trade.trigger && ' · '}
          {trade.trigger && <span>{trade.trigger}</span>}
          {trade.day_type && <span> · {trade.day_type}</span>}
        </div>
      )}

      {trade.systems && trade.systems.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 7, color: COLORS.textDim, marginBottom: 3, textTransform: 'uppercase' }}>
            Systems at entry
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {trade.systems.filter((s) => s.involved).map((s) => {
              const color = SYSTEM_META[s.id]?.color ?? '#888';
              return (
                <span
                  key={s.id}
                  title={s.hint ?? s.name}
                  style={{
                    fontSize: 7,
                    padding: '2px 4px',
                    borderRadius: 3,
                    border: `1px solid ${s.is_firing ? color : COLORS.borderFaint}`,
                    background: s.is_firing ? `${color}22` : 'transparent',
                    color: s.is_firing ? color : COLORS.textTertiary,
                    fontWeight: s.is_firing ? 700 : 500,
                    fontFamily: 'ui-monospace',
                  }}
                >
                  S{s.id}
                  {s.hint ? ` ${String(s.hint).slice(0, 8)}` : ''}
                  {s.is_firing && s.entry_price != null ? ` @${s.entry_price.toFixed(2)}` : ''}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* C1/C2/C3 rows */}
      {trade.contracts.map(c => {
        const sc = STATUS_COLORS[c.status] || '#737373';
        return (
          <div key={c.id} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: 9, padding: '2px 0',
            borderBottom: `1px solid ${COLORS.borderFaint}`,
          }}>
            <span style={{ fontWeight: 600, color: COLORS.textSecondary, width: 22 }}>{c.id}</span>
            <span style={{ color: COLORS.textTertiary, fontFamily: 'ui-monospace', fontSize: 8, width: 52 }}>
              {c.target_price?.toFixed(2) ?? '\u2014'}
            </span>
            <span style={{
              fontSize: 8, fontWeight: 500, padding: '0 4px', borderRadius: 2,
              color: sc, background: `${sc}15`,
            }}>
              {c.status.replace('_', ' ')}{c.smart_be ? ' \u21C4' : ''}
            </span>
            <span style={{ fontFamily: 'ui-monospace', fontSize: 9, width: 40, textAlign: 'right',
              color: c.pnl >= 0 ? COLORS.bull : COLORS.bear }}>
              ${c.pnl.toFixed(0)}
            </span>
            <span style={{ fontFamily: 'ui-monospace', fontSize: 8, width: 30, textAlign: 'right',
              color: COLORS.textTertiary }}>
              {c.r.toFixed(1)}R
            </span>
          </div>
        );
      })}

      {/* Summary footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', paddingTop: 4, marginTop: 2,
        fontSize: 9,
      }}>
        <span style={{ color: COLORS.textTertiary }}>
          Stop {trade.stop_price.toFixed(2)} | {trade.summary}
        </span>
        <span style={{
          fontWeight: 700, fontSize: 10, fontFamily: 'ui-monospace',
          color: trade.total_pnl >= 0 ? COLORS.bull : COLORS.bear,
        }}>
          ${trade.total_pnl.toFixed(0)} ({trade.total_r.toFixed(1)}R)
        </span>
      </div>

      {/* §3.5 Flow 5: Exit + Move Stop buttons */}
      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
        <button
          onClick={async () => {
            if (!confirm('Exit all contracts?')) return;
            const tid = trade.trade_id;
            if (tid == null || Number.isNaN(Number(tid))) {
              alert('Exit failed — missing trade_id');
              return;
            }
            const result = await exitTrade(Number(tid), { reason: 'manual' });
            if (!result.ok) {
              console.error('[ActiveTradeCard] exit failed', result.status, result.error);
              const hint =
                result.status === 0
                  ? `Cannot reach backend at ${getApiBase()} — is uvicorn on :8000?`
                  : `Exit failed (${result.status}): ${result.error ?? 'unknown'}`;
              alert(hint);
              return;
            }
            refreshActiveTrade();
          }}
          style={{
            flex: 1, fontSize: 9, padding: '3px 0', borderRadius: 3, cursor: 'pointer',
            border: '1px solid #dc2626', background: 'rgba(220,38,38,0.12)', color: '#dc2626',
          }}
        >Exit</button>
        <button
          onClick={() => {
            const ticks = prompt('Move stop by N ticks (positive=tighter):');
            if (ticks) {
              alert('Move Stop is not wired to the API yet — use Sierra or manual stop update.');
            }
          }}
          style={{
            flex: 1, fontSize: 9, padding: '3px 0', borderRadius: 3, cursor: 'pointer',
            border: `1px solid ${COLORS.borderFaint}`, background: 'transparent', color: COLORS.textTertiary,
          }}
        >Move Stop</button>
      </div>
    </div>
  );
}
