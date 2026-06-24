'use client';
import { useEffect, useRef, useState } from 'react';
import { IChartApi, ISeriesApi, LineSeries, LineData, Time } from 'lightweight-charts';
import { barTimestampsUnix, type WoodiesChartBar } from './woodies/woodiesDesignerSpec';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Props {
  chart: IChartApi | null;
}

// LSMA (Least-Squares MA) overlay on the PRICE pane. The /chart/bars5min endpoint does not
// carry lsma_value, so we read it from the Woodies stream (/api/v9/woodies/chart) which does,
// and resolve per-bar timestamps the same way the CCI panel does (the export repeats ts on the
// live tick). Display-only — no engine/trading effect. 5s poll = the WoodiesCciPanel floor.
export function LsmaLine({ chart }: Props) {
  const [bars, setBars] = useState<WoodiesChartBar[]>([]);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    let cancel = false;
    const load = () =>
      fetch(`${API}/api/v9/woodies/chart?limit=200`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (cancel || !d) return;
          const list = Array.isArray(d) ? d : (d.bars ?? d.data ?? []);
          setBars(list);
        })
        .catch(() => { /* offline → keep last */ });
    load();
    const id = setInterval(load, 5000);
    return () => { cancel = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (!chart || bars.length === 0) return;
    if (seriesRef.current) {
      try { chart.removeSeries(seriesRef.current); } catch {}
      seriesRef.current = null;
    }
    const series = chart.addSeries(LineSeries, {
      color: '#22d3ee',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: 'LSMA',
      crosshairMarkerVisible: false,
      autoscaleInfoProvider: () => null, // overlay only — never drive the price-pane scale
    });
    const tsList = barTimestampsUnix(bars);
    const seen = new Set<number>();
    const data: LineData[] = [];
    for (let i = 0; i < bars.length; i++) {
      const v = bars[i].lsma_value;
      const t = tsList[i];
      if (v == null || t == null || seen.has(t)) continue;
      seen.add(t);
      data.push({ time: t as Time, value: v });
    }
    data.sort((a, b) => (a.time as number) - (b.time as number));
    try { series.setData(data); } catch { /* ignore transient ordering on first paint */ }
    seriesRef.current = series;
    return () => {
      if (seriesRef.current) {
        try { chart.removeSeries(seriesRef.current); } catch {}
        seriesRef.current = null;
      }
    };
  }, [chart, bars]);

  return null;
}
