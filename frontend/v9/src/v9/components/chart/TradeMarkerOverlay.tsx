'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_COLORS, SYSTEM_BORDER_STYLE } from '../../types';
import type { SystemId, TradeMode } from '../../types';

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

interface BarRect {
  trade: any;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export function TradeMarkerOverlay({ chart, candleSeries }: Props) {
  const trades = useTradeStore((s) => s.trades);
  const setSelectedTradeId = useTradeStore((s) => s.setSelectedTradeId);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [bars, setBars] = useState<BarRect[]>([]);

  const computeBars = useCallback(() => {
    if (!chart || !candleSeries || !overlayRef.current) return;

    const timeScale = chart.timeScale();
    const newBars: BarRect[] = [];

    for (const trade of trades) {
      if (!trade.entry_ts) continue;
      const entryTime = new Date(trade.entry_ts).getTime() / 1000;
      const exitTime = trade.exit_ts
        ? new Date(trade.exit_ts).getTime() / 1000
        : Date.now() / 1000;

      const x1 = timeScale.timeToCoordinate(entryTime as any);
      const x2 = timeScale.timeToCoordinate(exitTime as any);
      if (x1 === null || x2 === null) continue;

      // Use entry/exit prices for vertical range
      const entryPrice = trade.entry_price ?? 0;
      const exitPrice = trade.exit_price ?? entryPrice;
      const highPrice = Math.max(entryPrice, exitPrice);
      const lowPrice = Math.min(entryPrice, exitPrice);

      const yHigh = candleSeries.priceToCoordinate(highPrice);
      const yLow = candleSeries.priceToCoordinate(lowPrice);
      if (yHigh === null || yLow === null) continue;

      newBars.push({
        trade,
        left: Math.min(x1, x2),
        right: Math.max(x1, x2),
        top: Math.min(yHigh, yLow),
        bottom: Math.max(yHigh, yLow),
      });
    }
    setBars(newBars);
  }, [chart, candleSeries, trades]);

  // Recompute on scroll/zoom and trade changes
  useEffect(() => {
    if (!chart) return;
    const ts = chart.timeScale();
    ts.subscribeVisibleLogicalRangeChange(computeBars);
    computeBars();
    return () => ts.unsubscribeVisibleLogicalRangeChange(computeBars);
  }, [chart, computeBars]);

  // Also recompute when the chart crosshair moves (ensures Y updates on pan)
  useEffect(() => {
    if (!chart) return;
    chart.subscribeCrosshairMove(computeBars);
    return () => chart.unsubscribeCrosshairMove(computeBars);
  }, [chart, computeBars]);

  if (bars.length === 0) return null;

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 pointer-events-none z-[5]"
    >
      {bars.map((b) => {
        const color = SYSTEM_COLORS[(b.trade.system as SystemId) || 1];
        const mode = (b.trade.mode || 'SHADOW') as TradeMode;
        const borderStyle = SYSTEM_BORDER_STYLE[mode];
        const minWidth = Math.max(b.right - b.left, 6);
        const minHeight = Math.max(b.bottom - b.top, 10);

        // Border: solid=LIVE, none=SIM, dashed=SHADOW
        const borderCss =
          borderStyle === 'none'
            ? 'none'
            : `1px ${borderStyle} ${color}`;

        return (
          <div
            key={b.trade.id}
            className="absolute pointer-events-auto cursor-pointer"
            style={{
              left: b.left,
              top: b.top,
              width: minWidth,
              height: minHeight,
              background: `${color}22`,
              border: borderCss,
              borderRadius: 1,
            }}
            title={`S${b.trade.system} ${b.trade.direction} @ ${b.trade.entry_price?.toFixed(2) ?? '—'}\n${b.trade.mode} | ${b.trade.outcome ?? 'OPEN'}\nP&L: ${b.trade.pnl_usd != null ? '$' + b.trade.pnl_usd.toFixed(0) : '—'}`}
            onClick={() => setSelectedTradeId(b.trade.id)}
          >
            {/* Entry arrow */}
            <span
              className="absolute text-[8px] leading-none"
              style={{
                left: 1,
                top: '50%',
                transform: 'translateY(-50%)',
                color,
                opacity: 0.9,
              }}
            >
              {b.trade.direction === 'LONG' ? '\u25B2' : '\u25BC'}
            </span>
            {/* Exit icon (right edge) */}
            {b.trade.exit_ts && (
              <span
                className="absolute text-[8px] leading-none"
                style={{
                  right: 1,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color,
                  opacity: 0.9,
                }}
              >
                {b.trade.outcome === 'WIN' ? '\u2713' : '\u2717'}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
