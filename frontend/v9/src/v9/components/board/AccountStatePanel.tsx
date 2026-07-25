'use client';
/**
 * AccountStatePanel — W1b (2026-07-25): account truth from sierra_state.json.
 * Shows position, avg, Open P/L, Daily P/L, High/Low During, working orders,
 * is_sim, armed, open trade, reconciler verdict. Polling 15000ms (P30 floor).
 */
import { useCallback, useEffect, useState } from 'react';

type SierraState = {
  ok: boolean;
  stale: boolean;
  age_s: number | null;
  position_qty: number | null;
  avg_price: number | null;
  working_orders: number | null;
  is_sim: number | null;
  order_placement_armed: number | null;
  open_pnl: number | null;
  daily_pnl: number | null;
  high_during_pos: number | null;
  low_during_pos: number | null;
  trade_account: string | null;
  symbol: string | null;
  daily_total_qty_filled: number | null;
  last_price: number | null;
};

type OpenTrade = {
  id: number;
  direction: string;
  entry_price: number;
  stop: number;
  t1: number | null;
  t2: number | null;
  t3: number | null;
  state: string;
  mode: string;
  pattern: string;
  contracts: number | null;
};

type AccountRes = {
  sierra_state: SierraState;
  open_trade: OpenTrade | null;
  verdict: string;
  source: string;
};

const VERDICT_COLOR: Record<string, string> = {
  flat: 'var(--text-secondary, #8b949e)',
  system: 'var(--green, #3fb950)',
  manual: 'var(--orange, #d29922)',
  divergence: 'var(--red, #f85149)',
  unknown: 'var(--red, #f85149)',
};

function V({ label, value }: { label: string; value: string | number | null | undefined }) {
  const display = value === null || value === undefined ? '\u2014' : String(value);
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
      <span style={{ color: 'var(--text-secondary, #8b949e)', fontSize: 12 }}>{label}</span>
      <span style={{ fontFamily: 'monospace', fontSize: 13 }}>{display}</span>
    </div>
  );
}

function Pnl({ label, value }: { label: string; value: number | null | undefined }) {
  if (value === null || value === undefined) return <V label={label} value={null} />;
  const color = value > 0 ? 'var(--green, #3fb950)' : value < 0 ? 'var(--red, #f85149)' : 'var(--text, #e6edf3)';
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
      <span style={{ color: 'var(--text-secondary, #8b949e)', fontSize: 12 }}>{label}</span>
      <span style={{ fontFamily: 'monospace', fontSize: 13, color }}>${value.toFixed(2)}</span>
    </div>
  );
}

export function AccountStatePanel() {
  const [data, setData] = useState<AccountRes | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v9/account/state', { cache: 'no-store' });
      if (res.ok) setData(await res.json());
    } catch { /* backend down */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  if (!data) return null;

  const s = data.sierra_state;
  const t = data.open_trade;
  const vColor = VERDICT_COLOR[data.verdict] || 'var(--text, #e6edf3)';
  const posQty = s.position_qty ?? 0;
  const isSim = s.is_sim === 1;
  const isArmed = s.order_placement_armed === 1;

  return (
    <div dir="rtl" style={{
      background: 'var(--bg-panel, #0d1117)',
      border: `1px solid ${posQty !== 0 ? 'var(--green, #238636)' : 'var(--border, #30363d)'}`,
      borderRadius: 8, padding: 14, color: 'var(--text, #e6edf3)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>
          {'\u{1F4CA}'} {s.symbol || 'Account'} {s.trade_account ? `(${s.trade_account})` : ''}
        </span>
        <span style={{ fontSize: 11, display: 'flex', gap: 6 }}>
          <span style={{
            background: isSim ? 'var(--orange, #d29922)' : 'var(--green, #238636)',
            borderRadius: 4, padding: '1px 6px', color: '#fff', fontWeight: 600,
          }}>{isSim ? 'SIM' : 'LIVE'}</span>
          <span style={{
            background: isArmed ? 'var(--green, #238636)' : 'var(--red, #da3633)',
            borderRadius: 4, padding: '1px 6px', color: '#fff', fontWeight: 600,
          }}>{isArmed ? 'ARMED' : 'OFF'}</span>
          <span style={{
            color: vColor, fontWeight: 600, fontSize: 12,
          }}>{data.verdict.toUpperCase()}</span>
        </span>
      </div>

      {/* Position */}
      <V label="Position" value={posQty !== 0 ? `${posQty} @ ${s.avg_price?.toFixed(2) ?? '\u2014'}` : 'Flat'} />
      <V label="Last Price" value={s.last_price?.toFixed(2)} />
      <V label="Working Orders" value={s.working_orders} />

      {/* P&L */}
      <div style={{ borderTop: '1px solid var(--border, #21262d)', margin: '6px 0', paddingTop: 4 }}>
        <Pnl label="Open P/L" value={s.open_pnl} />
        <Pnl label="Daily P/L" value={s.daily_pnl} />
      </div>

      {/* Position extremes (only when in position) */}
      {posQty !== 0 && (
        <div style={{ borderTop: '1px solid var(--border, #21262d)', margin: '6px 0', paddingTop: 4 }}>
          <V label="High During Pos" value={s.high_during_pos?.toFixed(2)} />
          <V label="Low During Pos" value={s.low_during_pos?.toFixed(2)} />
        </div>
      )}

      <V label="Daily Qty Filled" value={s.daily_total_qty_filled} />

      {/* Open system trade */}
      {t && (
        <div style={{
          borderTop: '1px solid var(--border, #21262d)', margin: '6px 0', paddingTop: 4,
          fontSize: 12,
        }}>
          <div style={{ fontWeight: 600, marginBottom: 2 }}>
            System Trade #{t.id} {t.direction} {t.contracts ?? '?'}c
            <span style={{ color: 'var(--text-secondary, #8b949e)', fontWeight: 400, marginRight: 4 }}>
              {t.pattern} ({t.state})
            </span>
          </div>
          <V label="Entry" value={t.entry_price?.toFixed(2)} />
          <V label="Stop" value={t.stop?.toFixed(2)} />
          {t.t1 && <V label="T1" value={t.t1.toFixed(2)} />}
          {t.t2 && <V label="T2" value={t.t2.toFixed(2)} />}
          {t.t3 && <V label="T3" value={t.t3.toFixed(2)} />}
        </div>
      )}

      {/* Footer */}
      <div style={{ fontSize: 10, color: 'var(--text-secondary, #8b949e)', marginTop: 6, textAlign: 'left' }}>
        {data.source} {s.stale ? '(STALE)' : ''} {s.age_s != null ? `${s.age_s}s ago` : ''}
      </div>
    </div>
  );
}
