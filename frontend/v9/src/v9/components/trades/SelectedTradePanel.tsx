'use client';
import { useMemo, type ReactNode } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_NAMES } from '../../types';
import type { SystemId, Trade } from '../../types';
import {
  rLevels,
  riskReward,
  stopMovement,
  formatUsdAccounting,
  durationMinutes,
  formatDuration,
  cumulativeByClose,
  cumulativeByOpen,
} from '../../lib/tradeMath';
import { tradeWhen } from '../../lib/tradeTime';

function Row({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '3px 0', fontSize: 11 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      {/* bdi isolates LTR numbers/R so they don't scramble the RTL layout */}
      <bdi style={{ color: color ?? 'var(--text-primary)' }}>{value}</bdi>
    </div>
  );
}

function StopVerdict({ trade }: { trade: Trade }) {
  const sm = stopMovement(trade);
  if (sm === 'moved')
    return (
      <span style={{ color: 'var(--green)' }}>
        ✓ זז ל-<bdi>BE</bdi> לפי אפיון<br />
        <bdi style={{ fontSize: 9, color: 'var(--text-muted)' }}>
          SMART_BE: {trade.stop_initial?.toFixed(2)} → {trade.stop?.toFixed(2)}
        </bdi>
      </span>
    );
  if (sm === 't1_no_be') return <span style={{ color: '#eab308' }}>⚠ <bdi>T1</bdi> נגע אך הסטופ לא זז</span>;
  return <span style={{ color: 'var(--text-secondary)' }}>סטופ ב-<bdi>−1R</bdi> — לא זז</span>;
}

export function SelectedTradePanel() {
  const trades = useTradeStore((s) => s.trades);
  const filtered = useTradeStore((s) => s.filteredTrades)();
  const expandedTradeId = useTradeStore((s) => s.expandedTradeId);

  const trade = useMemo(() => {
    return trades.find((t) => t.id === expandedTradeId) ?? filtered[0] ?? null;
  }, [trades, filtered, expandedTradeId]);

  const cumClose = useMemo(() => (trade ? cumulativeByClose(trades).get(trade.id) : undefined), [trades, trade]);
  const cumOpen = useMemo(() => (trade ? cumulativeByOpen(trades).get(trade.id) : undefined), [trades, trade]);

  if (!trade) {
    return (
      <div style={{ padding: 12, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
        בחר עסקה כדי לראות פרטים.
      </div>
    );
  }

  const L = rLevels(trade);
  const rr = riskReward(trade);
  const w = tradeWhen(trade.entry_ts);
  const col = SYSTEM_COLORS[(trade.system as SystemId) || 1] || 'var(--text-secondary)';
  const f = (v: number | null | undefined) => (v != null ? v.toFixed(2) : '—');
  const rtxt = (v: number | null) => (v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}R` : '—');
  const pnlColor = trade.pnl_usd == null ? 'var(--text-muted)' : trade.pnl_usd > 0 ? 'var(--green)' : trade.pnl_usd < 0 ? 'var(--red)' : 'var(--text-secondary)';
  const long = trade.direction === 'LONG';
  const divider = <div style={{ height: 1, background: 'var(--border)', margin: '6px 0' }} />;

  // Per-target "price · R" cell. T3 may be a real price (Trend_Normal/Trend_DD)
  // or trail/no-T3 (Variation/Normal) → show the label instead of a fake 0.00.
  const tgt = (price: number | null | undefined, r: number | null) =>
    price != null && price > 0 ? `${f(price)} · ${rtxt(r)}` : '—';
  const t3HasPrice = trade.t3 != null && trade.t3 > 0;
  const t3Display = t3HasPrice
    ? `${f(trade.t3)} · ${rtxt(L.t3R)}`
    : trade.t3_label
      ? `trail · ${trade.t3_label}`
      : trade.trail_after_t2
        ? 'trail'
        : '—';

  return (
    <div style={{ padding: 12, fontFamily: 'ui-monospace, monospace' }}>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 7 }}>
        עסקה נבחרת
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>#{trade.id}</span>
        <span style={{ fontSize: 10, color: long ? 'var(--green)' : 'var(--red)' }}>{trade.direction}</span>
        {trade.mode && <span style={{ fontSize: 8, color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 3, padding: '0 4px', textTransform: 'uppercase' }}>{trade.mode}</span>}
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: col, marginBottom: 8 }}>
        S{trade.system} {SYSTEM_NAMES[(trade.system as SystemId) || 1]}{trade.pattern_id ? ` · ${trade.pattern_id}` : ''}
      </div>

      <Row label="שעת כניסה" value={w ? `${w.date} ${w.etTime} ET` : '—'} color="var(--text-secondary)" />
      <Row label="משך" value={formatDuration(durationMinutes(trade))} />

      {divider}
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>מחיר · יחסי (R)</div>
      <Row label="כניסה" value={`${f(trade.entry_price)} · 0`} />
      <Row label="סטופ" value={`${f(trade.stop_initial ?? trade.stop)} · −1R`} color="var(--red)" />
      <Row label="T1 (C1)" value={tgt(trade.t1, L.t1R)} color="var(--sys1)" />
      <Row label="T2 (C2)" value={tgt(trade.t2, L.t2R)} color="var(--sys1)" />
      <Row label="T3 (C3)" value={t3Display} color="var(--sys2)" />
      <Row label="יציאה" value={`${f(trade.exit_price)} · ${rtxt(L.exitR)}`} color="var(--sys4)" />
      <Row label="P&L" value={formatUsdAccounting(trade.pnl_usd)} color={pnlColor} />

      {divider}
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>סיכון / סיכוי</div>
      <Row label="יחס R:R" value={rr && rr.t2 != null ? `1:${rr.t1?.toFixed(1) ?? '—'} (T1) · 1:${rr.t2.toFixed(1)} (T2)` : '—'} />
      <Row label="מומש" value={rtxt(L.exitR)} color={pnlColor} />

      {divider}
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>ניהול סטופ</div>
      <div style={{ fontSize: 11, lineHeight: 1.5 }}><StopVerdict trade={trade} /></div>

      {divider}
      <Row label="קומ׳ פתיחה" value={cumOpen != null ? formatUsdAccounting(cumOpen) : '—'} color={cumOpen != null && cumOpen < 0 ? 'var(--red)' : 'var(--green)'} />
      <Row label="קומ׳ סגירה" value={cumClose != null ? formatUsdAccounting(cumClose) : '—'} color={cumClose != null && cumClose < 0 ? 'var(--red)' : 'var(--green)'} />
    </div>
  );
}
