export type CvdPoint = { i: number; d: number; cum: number; p: number };

export function tsToUnix(ts: string): number {
  return Math.floor(new Date(ts.replace(' ', 'T')).getTime() / 1000);
}

/** Align Sierra CVD points to loaded chart bars by tail count (same time axis). */
export function mapCvdToBarTimes(
  bars: Array<{ ts: string }>,
  points: CvdPoint[],
): {
  hist: Array<{ time: number; value: number; color: string }>;
  line: Array<{ time: number; value: number }>;
} {
  if (!bars.length || !points.length) return { hist: [], line: [] };
  const n = Math.min(points.length, bars.length);
  const bSlice = bars.slice(-n);
  const pSlice = points.slice(-n);
  const hist = pSlice.map((pt, idx) => ({
    time: tsToUnix(bSlice[idx].ts),
    value: Math.abs(pt.d),
    color: pt.d >= 0 ? 'rgba(22,163,74,0.65)' : 'rgba(220,38,38,0.65)',
  }));
  const line = pSlice.map((pt, idx) => ({
    time: tsToUnix(bSlice[idx].ts),
    value: pt.cum,
  }));
  return { hist, line };
}
