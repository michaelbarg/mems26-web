'use client';
import { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

const LEVEL_CONFIGS = [
  { key: 'pdh', label: 'PDH', color: '#f85149', style: 2 },
  { key: 'pdl', label: 'PDL', color: '#f85149', style: 2 },
  { key: 'onh', label: 'ONH', color: '#d2a8ff', style: 1 },
  { key: 'onl', label: 'ONL', color: '#d2a8ff', style: 1 },
  { key: 'openPrice', label: 'OPEN', color: '#fb950b', style: 0 },
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
