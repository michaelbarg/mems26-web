'use client';
import { useEffect, useRef, useState } from 'react';
import type { IChartApi, ISeriesApi, IPriceLine } from 'lightweight-charts';
import { LineStyle } from 'lightweight-charts';
import { fetchActiveTrade } from '../../../lib/api';
import { parseActiveTrade, type ActiveTrade } from '../../../lib/activeTrade';

// §7 (PROMPT_SYSTEMS_TRADE_UX_2026-07-10) — the LIVE trade on the price chart.
// Draws entry / stop / T1-T3 as lightweight-charts price lines on the candle series (the
// stop line MOVES in real-time as stop_price changes on the 5s /trades/active poll — the
// point of the section), plus a mini-banner (#ID · pattern · live P&L · contracts).
// Shadow trades are NEVER drawn — the chart is reality (live/sim/demo only).
//
// Not a duplicate of chart/TradeMarkerOverlay (audited): that draws historical entry→exit
// rectangles for ALL trades and is mounted on the dead DashboardLayout/ChartArea; this is
// the single live trade with a moving stop + targets, on the live ChartV5b.

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

const COLOR = {
  entry: '#16a34a',
  stop: '#dc2626',
  target: ['#3b82f6', '#2563eb', '#1d4ed8'],
  long: '#16a34a',
  short: '#dc2626',
};
const POLL_MS = 5000; // useLivePricePoll floor (CLAUDE.md) — do not lower

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function LiveTradeOverlay({ candleSeries }: Props) {
  const [trade, setTrade] = useState<ActiveTrade | null>(null);
  const [mode, setMode] = useState<string>('shadow');
  const linesRef = useRef<IPriceLine[]>([]);

  // active trade — 5s (stop moves here)
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetchActiveTrade().then((d) => { if (alive) setTrade(parseActiveTrade(d)); }).catch(() => {});
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // system mode — 15s (skip drawing in shadow mode)
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`${API}/api/v9/cockpit/heartbeat`).then((r) => r.json())
        .then((d) => { if (alive) setMode(String(d.mode || 'shadow').toLowerCase()); })
        .catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // draw / update price lines
  useEffect(() => {
    const series = candleSeries;
    if (!series) return;

    const clear = () => {
      for (const l of linesRef.current) { try { series.removePriceLine(l); } catch { /* gone */ } }
      linesRef.current = [];
    };
    clear();

    const drawable = trade && mode !== 'shadow' && Number.isFinite(trade.entry_price);
    if (!drawable || !trade) return clear;

    const isLong = trade.direction === 'LONG';
    const arrow = isLong ? '▲' : '▼';
    const pat = trade.pattern_id || trade.trigger || '';
    type PriceLineOpts = Parameters<typeof series.createPriceLine>[0];
    const add = (o: PriceLineOpts) => { linesRef.current.push(series.createPriceLine(o)); };

    // entry — green dashed, at the real fill price
    add({ price: trade.entry_price, color: COLOR.entry, lineWidth: 1, lineStyle: LineStyle.Dashed,
      axisLabelVisible: true, title: `${arrow} #${trade.trade_id} ${pat}`.trim() });

    // stop — red solid; recreated at the new price each poll ⇒ visibly moves on every MODIFY
    if (Number.isFinite(trade.stop_price)) {
      add({ price: trade.stop_price, color: COLOR.stop, lineWidth: 2, lineStyle: LineStyle.Solid,
        axisLabelVisible: true, title: 'Stop' });
    }

    // targets — from contracts (C1→T1…); dotted until hit, then solid + ✓ at the fill price
    (trade.contracts || []).forEach((c, i) => {
      if (c.target_price == null) return;
      const hit = c.status === 'HIT_TARGET';
      add({ price: c.target_price, color: COLOR.target[i] || COLOR.target[2], lineWidth: 1,
        lineStyle: hit ? LineStyle.Solid : LineStyle.Dotted, axisLabelVisible: true,
        title: `T${i + 1}${hit ? ' ✓' : ''}` });
    });

    return clear;
  }, [trade, mode, candleSeries]);

  // mini-banner (top-left of the pane) — reuses the same reality gate
  if (!trade || mode === 'shadow' || !Number.isFinite(trade.entry_price)) return null;
  const isLong = trade.direction === 'LONG';
  const pnl = trade.total_pnl ?? 0;
  const modeLabel = mode === 'live' ? 'LIVE' : 'DEMO';
  return (
    <div
      data-testid="live-trade-banner"
      style={{
        position: 'absolute', left: 8, top: 8, zIndex: 12, pointerEvents: 'none',
        display: 'flex', alignItems: 'center', gap: 6, padding: '2px 8px', borderRadius: 6,
        background: 'rgba(13,17,23,0.85)', border: `1px solid ${isLong ? COLOR.long : COLOR.short}`,
        fontFamily: 'ui-monospace, monospace', fontSize: 10, whiteSpace: 'nowrap',
      }}
    >
      <span style={{ color: isLong ? COLOR.long : COLOR.short, fontWeight: 700 }}>
        {isLong ? '▲' : '▼'} #{trade.trade_id}
      </span>
      <span style={{ color: '#e5e5e5' }}>{trade.pattern_id || trade.trigger || ''}</span>
      <span style={{ color: pnl >= 0 ? '#56d364' : '#f85149' }}>{pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}</span>
      <span style={{ color: '#8b949e' }}>{trade.contracts?.length ?? 0}c · {modeLabel}</span>
    </div>
  );
}
