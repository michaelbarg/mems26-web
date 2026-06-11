'use client';

import { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  IChartApi,
  CandlestickSeries,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { Trade } from '../../types';

interface TradeChartProps {
  trade: Trade;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const THIRTY_MIN_S = 30 * 60;

export default function TradeChart({ trade }: TradeChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || !trade.entry_ts) return;

    let disposed = false;

    (async () => {
      try {
        const res = await fetch(`${API}/api/v9/chart/bars5min?limit=120`);
        if (!res.ok) return;
        const rawBars: { ts: string; o: number; h: number; l: number; c: number; v: number }[] =
          await res.json();

        if (disposed || !containerRef.current) return;

        // Compute trade window
        const entryEpoch = Math.floor(new Date(trade.entry_ts!).getTime() / 1000);
        const exitEpoch = trade.exit_ts
          ? Math.floor(new Date(trade.exit_ts).getTime() / 1000)
          : Math.floor(Date.now() / 1000);
        const windowStart = entryEpoch - THIRTY_MIN_S;
        const windowEnd = exitEpoch + THIRTY_MIN_S;

        // Filter bars to trade window
        const bars = rawBars
          .map((b) => {
            const time = Math.floor(new Date(b.ts).getTime() / 1000) as UTCTimestamp;
            return { time, open: b.o, high: b.h, low: b.l, close: b.c };
          })
          .filter((b) => b.time >= windowStart && b.time <= windowEnd)
          .sort((a, b) => a.time - b.time);

        if (bars.length === 0 || disposed || !containerRef.current) return;

        // Create chart
        const chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height: 200,
          layout: {
            background: { type: ColorType.Solid, color: '#0d1117' },
            textColor: '#c9d1d9',
          },
          grid: {
            vertLines: { color: '#21262d' },
            horzLines: { color: '#21262d' },
          },
          timeScale: { timeVisible: true, secondsVisible: false },
          rightPriceScale: { borderColor: '#21262d' },
        });
        chartRef.current = chart;

        const candleSeries = chart.addSeries(CandlestickSeries, {
          upColor: '#3fb950',
          downColor: '#f85149',
          borderUpColor: '#3fb950',
          borderDownColor: '#f85149',
          wickUpColor: '#3fb950',
          wickDownColor: '#f85149',
        });
        candleSeries.setData(bars);

        // Price lines helper
        const addLine = (
          price: number,
          color: string,
          title: string,
          style: number, // 0=solid, 1=dotted, 2=dashed
        ) => {
          candleSeries.createPriceLine({
            price,
            color,
            lineWidth: 1,
            lineStyle: style,
            axisLabelVisible: true,
            title,
          });
        };

        // Entry price
        if (trade.entry_price != null) {
          addLine(trade.entry_price, '#58a6ff', 'Entry', 2);
        }

        // Initial stop
        if (trade.stop_initial != null) {
          addLine(trade.stop_initial, '#f85149', 'Stop', 2);
        }

        // Current stop / BE (if different from initial)
        if (
          trade.stop != null &&
          trade.stop_initial != null &&
          trade.stop !== trade.stop_initial
        ) {
          addLine(trade.stop, '#d29922', 'BE', 1);
        }

        // T1
        if (trade.t1 != null) {
          addLine(trade.t1, '#3fb950', 'T1', 2);
        }

        // T2
        if (trade.t2 != null) {
          addLine(trade.t2, '#56d364', 'T2', 2);
        }

        // Exit marker
        if (trade.exit_price != null && trade.exit_ts) {
          const exitTime = Math.floor(new Date(trade.exit_ts).getTime() / 1000) as UTCTimestamp;
          candleSeries.setMarkers([
            {
              time: exitTime,
              position: trade.direction === 'LONG' ? 'aboveBar' : 'belowBar',
              color: '#a371f7',
              shape: 'circle',
              text: 'Exit',
            },
          ]);
        }

        // Fit content
        chart.timeScale().fitContent();

        // Resize observer
        const ro = new ResizeObserver(() => {
          if (containerRef.current && chartRef.current) {
            chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
          }
        });
        ro.observe(containerRef.current);

        // Store cleanup ref
        (containerRef.current as any).__ro = ro;
      } catch {
        // Network error — silently skip chart
      }
    })();

    return () => {
      disposed = true;
      if ((containerRef.current as any)?.__ro) {
        (containerRef.current as any).__ro.disconnect();
      }
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [trade.id, trade.entry_ts, trade.exit_ts]);

  if (!trade.entry_ts) return null;

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: 200, background: '#0d1117', borderRadius: 4 }}
    />
  );
}
