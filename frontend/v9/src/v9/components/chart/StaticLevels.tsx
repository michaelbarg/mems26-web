'use client';
import { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

// Colors per spec Section 3.4:
// PDH/PDL = gray dashed, ONH/ONL = light blue dashed, Open = white dashed
const LEVEL_CONFIGS = [
  { key: 'pdh', label: 'PDH', color: '#8b949e', style: 2 },
  { key: 'pdl', label: 'PDL', color: '#8b949e', style: 2 },
  { key: 'onh', label: 'ONH', color: '#79c0ff', style: 2 },
  { key: 'onl', label: 'ONL', color: '#79c0ff', style: 2 },
  { key: 'openPrice', label: 'OPEN', color: '#e6edf3', style: 2 },
] as const;

export function StaticLevels({ chart, candleSeries }: Props) {
  const { pdh, pdl, onh, onl, openPrice } = useMarketStore();
  const linesRef = useRef<any[]>([]);

  useEffect(() => {
    if (!candleSeries) return;

    linesRef.current.forEach((line) => {
      try { candleSeries.removePriceLine(line); } catch {}
    });
    linesRef.current = [];

    const levels: Record<string, number | null> = { pdh, pdl, onh, onl, openPrice };

    for (const cfg of LEVEL_CONFIGS) {
      const value = levels[cfg.key];
      if (value === null) continue;

      const line = candleSeries.createPriceLine({
        price: value,
        color: cfg.color,
        lineWidth: 1,
        lineStyle: cfg.style,
        axisLabelVisible: true,
        title: cfg.label,
      });
      linesRef.current.push(line);
    }
  }, [candleSeries, pdh, pdl, onh, onl, openPrice]);

  return null;
}
