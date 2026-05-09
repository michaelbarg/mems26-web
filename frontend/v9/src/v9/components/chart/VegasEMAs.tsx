'use client';
import { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi, LineSeries, LineData, Time } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';

interface Props {
  chart: IChartApi | null;
}

export function VegasEMAs({ chart }: Props) {
  const bars = useMarketStore((s) => s.bars5min);
  const seriesRefs = useRef<ISeriesApi<'Line'>[]>([]);

  useEffect(() => {
    if (!chart || bars.length === 0) return;

    seriesRefs.current.forEach((s) => {
      try { chart.removeSeries(s); } catch {}
    });
    seriesRefs.current = [];

    const emaConfigs = [
      { period: 12, color: '#58a6ff', width: 1 },
      { period: 34, color: '#58a6ff', width: 1 },
      { period: 144, color: '#d2a8ff', width: 2 },
      { period: 169, color: '#d2a8ff', width: 2 },
      { period: 576, color: '#fb950b', width: 1 },
      { period: 676, color: '#fb950b', width: 1 },
    ];

    for (const cfg of emaConfigs) {
      const series = chart.addSeries(LineSeries, {
        color: cfg.color,
        lineWidth: cfg.width as 1 | 2 | 3 | 4,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });

      const emaData = calculateEMA(bars, cfg.period);
      series.setData(emaData);
      seriesRefs.current.push(series);
    }
  }, [chart, bars]);

  return null;
}

function calculateEMA(bars: any[], period: number): LineData[] {
  if (bars.length === 0) return [];
  const k = 2 / (period + 1);
  const result: LineData[] = [];
  let ema = bars[0].close;

  for (const bar of bars) {
    ema = bar.close * k + ema * (1 - k);
    result.push({
      time: (new Date(bar.timestamp).getTime() / 1000) as Time,
      value: ema,
    });
  }
  return result;
}
