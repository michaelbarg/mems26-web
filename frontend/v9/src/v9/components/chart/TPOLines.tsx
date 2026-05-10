'use client';
import { useEffect, useRef } from 'react';
import { IChartApi, ISeriesApi } from 'lightweight-charts';
import { useMarketStore } from '../../stores/marketStore';

interface Props {
  chart: IChartApi | null;
  candleSeries: ISeriesApi<'Candlestick'> | null;
}

export function TPOLines({ chart, candleSeries }: Props) {
  const { currentPOC, currentVAH, currentVAL } = useMarketStore();
  const linesRef = useRef<any[]>([]);

  useEffect(() => {
    if (!candleSeries) return;

    // Remove old lines
    linesRef.current.forEach((line) => {
      try { candleSeries.removePriceLine(line); } catch {}
    });
    linesRef.current = [];

    // POC line — dynamic, yellow per spec Section 3.2
    if (currentPOC !== null) {
      const pocLine = candleSeries.createPriceLine({
        price: currentPOC,
        color: '#F97316',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: 'POC',
      });
      linesRef.current.push(pocLine);
    }

    // VAH line — dynamic, green dashed per spec Section 3.2
    if (currentVAH !== null) {
      const vahLine = candleSeries.createPriceLine({
        price: currentVAH,
        color: '#56d364',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'VAH',
      });
      linesRef.current.push(vahLine);
    }

    // VAL line — dynamic, red dashed per spec Section 3.2
    if (currentVAL !== null) {
      const valLine = candleSeries.createPriceLine({
        price: currentVAL,
        color: '#f85149',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'VAL',
      });
      linesRef.current.push(valLine);
    }
  }, [candleSeries, currentPOC, currentVAH, currentVAL]);

  return null;
}
