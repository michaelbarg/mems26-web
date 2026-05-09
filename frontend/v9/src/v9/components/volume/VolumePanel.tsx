'use client';
import { useEffect, useRef } from 'react';
import { createChart, HistogramSeries, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';
import { useLayoutStore } from '../../stores/layoutStore';

export function VolumePanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const deltaSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const bars = useMarketStore((s) => s.bars5min);
  const tickBars = useMarketStore((s) => s.tickReversalBars);
  const { activeChartType, showBidAskSplit, toggleBidAskSplit } = useLayoutStore();

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#0d1117' },
        textColor: '#8b949e',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      rightPriceScale: { borderColor: '#30363d' },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
        visible: false,
      },
      crosshair: { mode: 0 },
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    const deltaSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'delta',
    });

    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0, bottom: 0.5 } });
    chart.priceScale('delta').applyOptions({ scaleMargins: { top: 0.5, bottom: 0 } });

    chartRef.current = chart;
    volumeSeriesRef.current = volumeSeries;
    deltaSeriesRef.current = deltaSeries;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => { resizeObserver.disconnect(); chart.remove(); };
  }, []);

  useEffect(() => {
    const data = activeChartType === '5min' ? bars : tickBars;
    if (!volumeSeriesRef.current || !deltaSeriesRef.current || data.length === 0) return;

    volumeSeriesRef.current.setData(
      data.map((b: any) => ({
        time: (new Date(b.timestamp).getTime() / 1000) as Time,
        value: b.volume,
        color: b.close >= b.open ? 'rgba(86,211,100,0.5)' : 'rgba(248,81,73,0.5)',
      }))
    );

    let cumDelta = 0;
    deltaSeriesRef.current.setData(
      data.map((b: any) => {
        cumDelta += b.delta || 0;
        return {
          time: (new Date(b.timestamp).getTime() / 1000) as Time,
          value: cumDelta,
          color: cumDelta >= 0 ? 'rgba(86,211,100,0.7)' : 'rgba(248,81,73,0.7)',
        };
      })
    );
  }, [bars, tickBars, activeChartType]);

  return (
    <div className="relative w-full h-full" style={{ background: 'var(--bg-primary)' }}>
      {activeChartType === 'tick_reversal' && (
        <button
          onClick={toggleBidAskSplit}
          className="absolute top-1 left-2 z-10 text-[10px] px-1.5 py-0.5 rounded"
          style={{
            background: showBidAskSplit ? 'var(--bg-tertiary)' : 'transparent',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
          }}
        >
          Bid/Ask
        </button>
      )}
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
}
