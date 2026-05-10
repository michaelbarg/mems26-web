'use client';
import { useEffect, useRef, useCallback } from 'react';
import { createChart, CandlestickSeries, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';
import { useSystemStore } from '../../stores/systemStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { WS_CHANNELS } from '../../lib/websocket';
import { fetchBars5min, fetchTickReversalBars, fetchMarkers, fetchSignals, fetchTrades } from '../../lib/api';
import { useTradeStore } from '../../stores/tradeStore';
import { TPOLines } from './TPOLines';
import { StaticLevels } from './StaticLevels';
import { RightSideLabels } from './RightSideLabels';
import { TradeMarkerOverlay } from './TradeMarkerOverlay';
import { VegasEMAs } from './VegasEMAs';
import { SYSTEM_COLORS, type SystemId } from '../../types';

export function ChartArea() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const activeChartType = useLayoutStore((s) => s.activeChartType);
  const { setBars5min, addBar5min, setLevels } = useMarketStore();
  const { setMarkers, addMarker, setSignals } = useSystemStore();
  const setTrades = useTradeStore((s) => s.setTrades);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0d1117' },
        textColor: '#8b949e',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: '#58a6ff', width: 1, style: 2, labelBackgroundColor: '#161b22' },
        horzLine: { color: '#58a6ff', width: 1, style: 2, labelBackgroundColor: '#161b22' },
      },
      rightPriceScale: {
        borderColor: '#30363d',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#56d364',
      downColor: '#f85149',
      borderUpColor: '#56d364',
      borderDownColor: '#f85149',
      wickUpColor: '#56d364',
      wickDownColor: '#f85149',
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, []);

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        const bars = activeChartType === '5min'
          ? await fetchBars5min(300)
          : await fetchTickReversalBars(15, 300);

        if (activeChartType === '5min') setBars5min(bars);

        const chartData: CandlestickData[] = bars.map((b: any) => ({
          time: (new Date(b.ts).getTime() / 1000) as Time,
          open: b.o,
          high: b.h,
          low: b.l,
          close: b.c,
        }));
        candleSeriesRef.current?.setData(chartData);

        const [allMarkers, allSignals, allTrades] = await Promise.all([
          fetchMarkers(), fetchSignals(), fetchTrades(),
        ]);
        setMarkers(allMarkers);
        setSignals(allSignals);
        setTrades(allTrades);
      } catch (err) {
        console.error('Failed to load chart data:', err);
      }
    }
    loadData();
  }, [activeChartType, setBars5min, setMarkers, setSignals, setTrades]);

  // WebSocket for real-time bars
  const wsChannel = activeChartType === '5min' ? WS_CHANNELS.BARS_5MIN : WS_CHANNELS.BARS_TICK_REVERSAL;
  useWebSocket(wsChannel, useCallback((data: any) => {
    if (activeChartType === '5min') addBar5min(data);
    candleSeriesRef.current?.update({
      time: (new Date(data.ts).getTime() / 1000) as Time,
      open: data.o,
      high: data.h,
      low: data.l,
      close: data.c,
    });
  }, [activeChartType, addBar5min]));

  // WebSocket for levels
  useWebSocket(WS_CHANNELS.LEVELS, useCallback((data: any) => {
    setLevels(data);
  }, [setLevels]));

  // WebSocket for markers (system 1-6)
  const handleMarker = useCallback((data: any) => { addMarker(data); }, [addMarker]);
  useWebSocket(WS_CHANNELS.MARKERS(1), handleMarker);
  useWebSocket(WS_CHANNELS.MARKERS(2), handleMarker);
  useWebSocket(WS_CHANNELS.MARKERS(3), handleMarker);
  useWebSocket(WS_CHANNELS.MARKERS(4), handleMarker);
  useWebSocket(WS_CHANNELS.MARKERS(5), handleMarker);
  useWebSocket(WS_CHANNELS.MARKERS(6), handleMarker);

  return (
    <div className="relative w-full h-full" style={{ background: 'var(--bg-primary)' }}>
      <div ref={chartContainerRef} className="w-full h-full" />
      <StaticLevels chart={chartRef.current} candleSeries={candleSeriesRef.current} />
      <TPOLines chart={chartRef.current} candleSeries={candleSeriesRef.current} />
      <VegasEMAs chart={chartRef.current} />
      <RightSideLabels />
      <TradeMarkerOverlay chart={chartRef.current} candleSeries={candleSeriesRef.current} />
    </div>
  );
}
