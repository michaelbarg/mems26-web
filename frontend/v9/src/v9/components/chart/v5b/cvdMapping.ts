export type CvdPoint = {
  i: number;
  d: number;
  cum: number;
  p: number;
  /** Unix epoch seconds (added by backend when Sierra DLL omits it). */
  t?: number;
};

/** ET wall-clock bar times use -04:00 (see ChartV5b tsToUnix). */
export function barUnixFromTs(ts: string): number {
  return tsToUnix(ts);
}

/**
 * Sierra DLL `t` is often ET wall-clock stored as a UTC epoch (4h behind
 * chart bars in EDT, 5h in EST). Shift points so the last CVD bucket lines
 * up with the last price bar on the shared chart timeScale.
 */
export function alignCvdPointTimesToPriceBars(
  points: CvdPoint[],
  bars: Array<{ ts: string; t?: number }>,
): CvdPoint[] {
  if (!points.length || !bars.length) return points;
  if (!points.every((p) => typeof p.t === 'number')) return points;
  const lastBar = bars[bars.length - 1];
  const lastBarT =
    typeof lastBar.t === 'number' ? lastBar.t : barUnixFromTs(lastBar.ts);
  const lastPtT = points[points.length - 1].t!;
  if (!Number.isFinite(lastBarT) || !Number.isFinite(lastPtT)) return points;
  const diff = lastBarT - lastPtT;
  const EDT_SHIFT = 4 * 3600;
  const EST_SHIFT = 5 * 3600;
  let shift = 0;
  if (Math.abs(diff - EDT_SHIFT) < 600) shift = EDT_SHIFT;
  else if (Math.abs(diff - EST_SHIFT) < 600) shift = EST_SHIFT;
  else if (Math.abs(diff) <= 60) shift = 0;
  else return points;
  if (shift === 0) return points;
  return points.map((p) =>
    typeof p.t === 'number' ? { ...p, t: p.t + shift } : p,
  );
}

/**
 * Densify CVD points to match the active timeframe's bucket cadence.
 *
 * When `bucketSeconds` is **smaller** than the actual point spacing (e.g.
 * DLL ships 25-min points but the cockpit is on 5-min TF), interpolate
 * intermediate buckets linearly between consecutive points so every
 * candle on the CVD pane is exactly one TF wide — matching the price
 * candle width. Each interpolated candle gets:
 *   cum = lerp(prevCum, nextCum, fraction)
 *   d   = even share of (nextCum - prevCum) across the gap
 *
 * The result is **visually** parity with the price chart. The numbers
 * are approximations of the per-bar delta but `cum` lands on the real
 * value at the original point boundaries. Once the DLL emits one point
 * per host bar (post-`%5`-filter removal), this codepath becomes a
 * no-op because the gaps are already 5-min.
 */
export function densifyCvdPoints(points: CvdPoint[], bucketSeconds: number): CvdPoint[] {
  if (points.length < 2 || bucketSeconds <= 0) return points;
  const out: CvdPoint[] = [];
  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    if (typeof pt.t !== 'number') {
      out.push(pt);
      continue;
    }
    out.push(pt);
    const next = points[i + 1];
    if (!next || typeof next.t !== 'number') continue;
    const gap = next.t - pt.t;
    if (gap <= bucketSeconds) continue;
    const steps = Math.floor(gap / bucketSeconds);
    if (steps < 2) continue;
    const cumDelta = next.cum - pt.cum;
    for (let s = 1; s < steps; s++) {
      const frac = s / steps;
      const t = pt.t + s * bucketSeconds;
      const cum = pt.cum + cumDelta * frac;
      out.push({
        i: pt.i,
        t,
        d: cumDelta / steps,
        cum,
        p: pt.p,
      });
    }
  }
  return out;
}

/**
 * Aggregate raw CVD points (5-min host bars) into wider buckets so the CVD
 * pane matches the price chart's active timeframe. 3 m and 5 m use the
 * native series; 15 m / 30 m / 1 h collapse multiple 5-min points into one
 * candle by snapping `t` to the bucket start.
 *
 * Open = cum of the first source point in the bucket (= prevCum before it).
 * Close = cum of the last source point in the bucket.
 * High / Low = max / min of `cum` across the bucket.
 *
 * Skips points missing `t` defensively.
 */
export function aggregateCvdPoints(points: CvdPoint[], bucketSeconds: number): CvdPoint[] {
  if (!points.length || bucketSeconds <= 0) return points;
  const buckets = new Map<
    number,
    { first: CvdPoint; last: CvdPoint; sumD: number; minCum: number; maxCum: number }
  >();
  for (const pt of points) {
    if (typeof pt.t !== 'number') continue;
    const bucketStart = Math.floor(pt.t / bucketSeconds) * bucketSeconds;
    const existing = buckets.get(bucketStart);
    if (!existing) {
      buckets.set(bucketStart, {
        first: pt,
        last: pt,
        sumD: pt.d,
        minCum: pt.cum,
        maxCum: pt.cum,
      });
    } else {
      existing.last = pt;
      existing.sumD += pt.d;
      existing.minCum = Math.min(existing.minCum, pt.cum);
      existing.maxCum = Math.max(existing.maxCum, pt.cum);
    }
  }
  return Array.from(buckets.entries())
    .sort(([a], [b]) => a - b)
    .map(([bucketStart, agg]) => ({
      i: agg.first.i,
      t: bucketStart,
      d: agg.sumD,
      cum: agg.last.cum,
      p: agg.last.p,
    }));
}

/**
 * Post-§9 DB / Sierra bar timestamps are naive **real UTC** wall-clock.
 * Parse as `Z` so the resulting unix matches CVD points' `t` (already
 * epoch UTC) — keeps price chart and CVD pane on a single shared time
 * axis. The legacy `-04:00` shim was for pre-§9 Chicago-encoded ts and
 * was confirmed to mis-align the panes by 4 h during 2026-05-22 RTH UAT.
 * See ChartV5b.tsx::tsToUnix for the matching fix (P31-FE-TZ-2).
 */
export function tsToUnix(ts: string): number {
  const s = ts.replace(' ', 'T');
  const hasOffset = /[+-]\d{2}:\d{2}$/.test(s) || s.endsWith('Z');
  return Math.floor(new Date(hasOffset ? s : s + 'Z').getTime() / 1000);
}

/**
 * Build chart series from CVD points using each point's own timestamp.
 * Falls back to bar timestamps only when neither `t` nor bars are missing —
 * keeps CVD pane and price chart on a shared X axis.
 */
export function mapCvdToBarTimes(
  bars: Array<{ ts: string }>,
  points: CvdPoint[],
): {
  hist: Array<{ time: number; value: number; color: string }>;
  line: Array<{ time: number; value: number }>;
} {
  if (!points.length) return { hist: [], line: [] };
  const usePointTs = points.every((p) => typeof p.t === 'number');
  const n = usePointTs ? points.length : Math.min(points.length, bars.length);
  if (n === 0) return { hist: [], line: [] };
  const pSlice = usePointTs ? points : points.slice(-n);
  const bSlice = usePointTs ? [] : bars.slice(-n);
  const timeAt = (pt: CvdPoint, idx: number): number =>
    typeof pt.t === 'number' ? pt.t : tsToUnix(bSlice[idx].ts);
  const hist = pSlice.map((pt, idx) => ({
    time: timeAt(pt, idx),
    value: Math.abs(pt.d),
    color: pt.d >= 0 ? 'rgba(22,163,74,0.65)' : 'rgba(220,38,38,0.65)',
  }));
  const line = pSlice.map((pt, idx) => ({
    time: timeAt(pt, idx),
    value: pt.cum,
  }));
  return { hist, line };
}
