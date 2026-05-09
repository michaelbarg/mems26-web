'use client';
import { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi, createSeriesMarkers } from 'lightweight-charts';
import { useSystemStore } from '../../stores/systemStore';
import { SYSTEM_COLORS } from '../../types';
import type { SystemId } from '../../types';

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

const MARKER_ICONS: Record<string, string> = {
  ENTRY: '\u25B6',
  EXIT_WIN: '\u2713',
  EXIT_STOP: '\u2717',
  ALERT: '\u26A1',
  LEVEL: '\u2500',
};

export function TradeMarkerOverlay({ chart, candleSeries }: Props) {
  const markers = useSystemStore((s) => s.markers);
  const markersPluginRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(null);

  useEffect(() => {
    if (!candleSeries) return;

    const chartMarkers = markers
      .sort((a, b) => new Date(a.bar_timestamp).getTime() - new Date(b.bar_timestamp).getTime())
      .map((m) => ({
        time: (new Date(m.bar_timestamp).getTime() / 1000) as any,
        position: m.direction === 'LONG' ? 'belowBar' as const : 'aboveBar' as const,
        color: SYSTEM_COLORS[m.system_id as SystemId],
        shape: m.marker_type === 'ENTRY' ? 'arrowUp' as const :
               m.marker_type === 'EXIT_WIN' ? 'circle' as const :
               m.marker_type === 'EXIT_STOP' ? 'square' as const : 'circle' as const,
        text: MARKER_ICONS[m.marker_type] || '',
      }));

    if (!markersPluginRef.current) {
      markersPluginRef.current = createSeriesMarkers(candleSeries, chartMarkers);
    } else {
      markersPluginRef.current.setMarkers(chartMarkers);
    }
  }, [candleSeries, markers]);

  return null;
}
