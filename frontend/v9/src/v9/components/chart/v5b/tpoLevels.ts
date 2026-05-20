import {
  LineSeries,
  LineStyle,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type LineWidth,
  type Time,
} from 'lightweight-charts';

export type TpoPeriod = {
  opened_ts: string | null;
  closed_ts: string | null;
  poc_price: number | null;
  vah_price?: number | null;
  val_price?: number | null;
};

export type TpoOverlayData = {
  poc?: number | null;
  vah?: number | null;
  val?: number | null;
  periods?: TpoPeriod[];
  session_opened_ts?: string | null;
  previous_session?: {
    found?: boolean;
    poc?: number | null;
    vah?: number | null;
    val?: number | null;
    opened_ts?: string | null;
    closed_ts?: string | null;
  };
};

export type TpoLevelName = 'VAH' | 'POC' | 'VAL';

export type TpoLevelPlan = {
  name: TpoLevelName;
  price: number;
  color: string;
  width: number;
  dashed: boolean;
  session: 'today' | 'yesterday';
};

export const PINK_RTH = '#FF4DD8';
export const WHITE_YDAY = '#FFFFFF';

const LEVEL_STYLE: Record<TpoLevelName, { dashed: boolean; width: number }> = {
  VAH: { dashed: false, width: 1 },
  POC: { dashed: true, width: 2 },
  VAL: { dashed: false, width: 1 },
};

const RTH_LEVEL_STYLE: Record<TpoLevelName, { dashed: boolean; width: number }> = {
  VAH: { dashed: false, width: 1 },
  POC: { dashed: true, width: 2 },
  VAL: { dashed: false, width: 1 },
};

/** RTH check: 09:30–16:00 ET. Pink (today) lines only visible during RTH. */
function isRthNow(): boolean {
  try {
    const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const mins = et.getHours() * 60 + et.getMinutes();
    return mins >= 9 * 60 + 30 && mins < 16 * 60;
  } catch {
    return false;
  }
}

/** Globex session: 18:00 ET Sunday–Friday. White (yesterday) lines from Globex open. */
function isGlobexOpen(): boolean {
  try {
    const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const hrs = et.getHours();
    // Globex: 18:00 ET → next day 17:00 ET (Sun–Fri)
    return hrs >= 18 || hrs < 17;
  } catch {
    return true; // fail-open: show lines
  }
}

export function coerceMesPrice(p: unknown): number | null {
  const n = typeof p === 'number' ? p : typeof p === 'string' ? Number(p) : NaN;
  if (!Number.isFinite(n)) return null;
  return n >= 3000 && n <= 10000 ? n : null;
}

export function isValidMesTpoPrice(p: number | null | undefined): p is number {
  return coerceMesPrice(p) != null;
}

function levelsTriple(
  poc: unknown,
  vah: unknown,
  val: unknown,
): { poc: number | null; vah: number | null; val: number | null } {
  return {
    poc: coerceMesPrice(poc),
    vah: coerceMesPrice(vah),
    val: coerceMesPrice(val),
  };
}

function periodOpenedMs(p: TpoPeriod): number {
  if (!p.opened_ts) return 0;
  return Date.parse(String(p.opened_ts).replace(' ', 'T') + '-04:00');
}

function sessionOpenedMs(ts: string | null | undefined): number {
  if (!ts) return 0;
  return Date.parse(String(ts).replace(' ', 'T') + '-04:00');
}

function sessionDay(ts: string | null | undefined): string | null {
  if (!ts) return null;
  const m = String(ts).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}

/** Prefer periods for the active session — never the oldest array tail (P27.5a-style stale pick). */
export function pickTodayPeriod(
  periods: TpoPeriod[],
  sessionOpenedTs?: string | null,
): TpoPeriod | null {
  if (!periods.length) return null;
  const sorted = [...periods].sort((a, b) => periodOpenedMs(b) - periodOpenedMs(a));
  const sessMs = sessionOpenedMs(sessionOpenedTs);
  const sessDay = sessionDay(sessionOpenedTs);

  const afterSession = sessMs
    ? sorted.filter((p) => periodOpenedMs(p) >= sessMs)
    : [];
  const sameDay = sessDay
    ? sorted.filter((p) => sessionDay(p.opened_ts) === sessDay)
    : [];
  const latestDay =
    sorted.map((p) => sessionDay(p.opened_ts)).find((d) => d != null) ?? null;
  const latestDayPeriods = latestDay
    ? sorted.filter((p) => sessionDay(p.opened_ts) === latestDay)
    : sorted;

  for (const bucket of [afterSession, sameDay, latestDayPeriods, sorted]) {
    if (!bucket.length) continue;
    for (const p of bucket) {
      const t = levelsTriple(p.poc_price, p.vah_price, p.val_price);
      if (t.poc != null && t.vah != null && t.val != null) return p;
    }
    const merged = { poc: null as number | null, vah: null as number | null, val: null as number | null };
    for (const p of bucket) {
      const t = levelsTriple(p.poc_price, p.vah_price, p.val_price);
      if (merged.poc == null && t.poc != null) merged.poc = t.poc;
      if (merged.vah == null && t.vah != null) merged.vah = t.vah;
      if (merged.val == null && t.val != null) merged.val = t.val;
    }
    if (merged.poc != null || merged.vah != null || merged.val != null) {
      return {
        opened_ts: bucket[0].opened_ts,
        closed_ts: bucket[0].closed_ts,
        poc_price: merged.poc,
        vah_price: merged.vah,
        val_price: merged.val,
      };
    }
  }
  return null;
}

export function resolveTodayLevels(tpo: TpoOverlayData): {
  poc: number | null;
  vah: number | null;
  val: number | null;
} {
  let { poc, vah, val } = levelsTriple(tpo.poc, tpo.vah, tpo.val);
  if (poc != null && vah != null && val != null) return { poc, vah, val };

  const picked = pickTodayPeriod(tpo.periods ?? [], tpo.session_opened_ts);
  if (picked) {
    const fromPeriod = levelsTriple(picked.poc_price, picked.vah_price, picked.val_price);
    if (fromPeriod.poc != null && fromPeriod.vah != null && fromPeriod.val != null) {
      return fromPeriod;
    }
    if (poc == null && fromPeriod.poc != null) poc = fromPeriod.poc;
    if (vah == null && fromPeriod.vah != null) vah = fromPeriod.vah;
    if (val == null && fromPeriod.val != null) val = fromPeriod.val;
  }
  return { poc, vah, val };
}

function resolvePrevLevels(prev: TpoOverlayData['previous_session']): {
  poc: number | null;
  vah: number | null;
  val: number | null;
} {
  if (!prev) return { poc: null, vah: null, val: null };
  return levelsTriple(prev.poc, prev.vah, prev.val);
}

export function buildTpoPlan(tpo: TpoOverlayData | null, rthOnly = true): TpoLevelPlan[] {
  if (!tpo) return [];
  const out: TpoLevelPlan[] = [];

  const push = (
    name: TpoLevelName,
    price: number | null,
    session: 'today' | 'yesterday',
  ) => {
    if (price == null) return;
    const style = session === 'today' ? RTH_LEVEL_STYLE[name] : LEVEL_STYLE[name];
    out.push({
      name,
      price,
      color: session === 'today' ? PINK_RTH : WHITE_YDAY,
      width: style.width,
      dashed: style.dashed,
      session,
    });
  };

  // Pink lines (today) only during RTH when rthOnly=true
  const showToday = !rthOnly || isRthNow();
  if (showToday) {
    const today = resolveTodayLevels(tpo);
    push('VAH', today.vah, 'today');
    push('POC', today.poc, 'today');
    push('VAL', today.val, 'today');
  }

  // White lines (yesterday) from Globex open (18:00 ET)
  if (isGlobexOpen()) {
    const prev = resolvePrevLevels(tpo.previous_session);
    push('VAH', prev.vah, 'yesterday');
    push('POC', prev.poc, 'yesterday');
    push('VAL', prev.val, 'yesterday');
  }
  return out;
}

export function collectTpoPrices(tpo: TpoOverlayData | null): number[] {
  return buildTpoPlan(tpo).map((p) => p.price);
}

const lineStore = new WeakMap<ISeriesApi<'Candlestick'>, IPriceLine[]>();
const horizStore = new WeakMap<IChartApi, ISeriesApi<'Line'>[]>();

/** Full-width TPO rules on the price pane (survives candle setData better than price lines alone). */
export function syncTpoHorizontals(
  chart: IChartApi | null,
  paneIndex: number,
  tpo: TpoOverlayData | null,
  timeFrom: number,
  timeTo: number,
): number {
  if (!chart) return 0;
  const prev = horizStore.get(chart) ?? [];
  for (const s of prev) {
    try {
      chart.removeSeries(s);
    } catch {
      /* noop */
    }
  }
  const plan = buildTpoPlan(tpo);
  const next: ISeriesApi<'Line'>[] = [];
  let t0 = Math.min(timeFrom, timeTo) as Time;
  let t1 = Math.max(timeFrom, timeTo) as Time;
  if (Number(t1) <= Number(t0)) {
    t1 = (Number(t0) + 300) as Time;
  }
  for (const lv of plan) {
    try {
      const s = chart.addSeries(
        LineSeries,
        {
          color: lv.color,
          lineWidth: (lv.width >= 2 ? 2 : 1) as LineWidth,
          lineStyle: lv.dashed ? LineStyle.Dashed : LineStyle.Solid,
          crosshairMarkerVisible: false,
          lastValueVisible: true,
          priceLineVisible: false,
          title: lv.name,
        },
        paneIndex,
      );
      s.setData([
        { time: t0, value: lv.price },
        { time: t1, value: lv.price },
      ]);
      next.push(s);
    } catch (e) {
      console.error('[TPO] horizontal line series failed', lv, e);
    }
  }
  horizStore.set(chart, next);
  console.info('[TPO] syncTpoHorizontals', {
    count: plan.length,
    prices: plan.map((p) => p.price),
    from: timeFrom,
    to: timeTo,
  });
  return plan.length;
}

/** Today (pink) price lines only — full width, locked to price by chart engine. */
export function syncTpoPriceLines(
  series: ISeriesApi<'Candlestick'> | null,
  tpo: TpoOverlayData | null,
): number {
  if (!series) return 0;
  const prev = lineStore.get(series) ?? [];
  for (const line of prev) {
    try {
      series.removePriceLine(line);
    } catch {
      /* noop */
    }
  }
  const next: IPriceLine[] = [];
  const plan = buildTpoPlan(tpo);
  // Only today (pink) — yesterday uses time-bounded LineSeries
  for (const lv of plan) {
    if (lv.session !== 'today') continue;
    try {
      next.push(
        series.createPriceLine({
          price: lv.price,
          color: lv.color,
          lineWidth: (lv.width >= 2 ? 2 : 1) as LineWidth,
          lineStyle: lv.dashed ? LineStyle.Dashed : LineStyle.Solid,
          axisLabelVisible: false,
          title: '',
        }),
      );
    } catch (e) {
      console.error('[TPO] createPriceLine failed', lv, e);
    }
  }
  lineStore.set(series, next);
  console.info('[TPO] syncTpoPriceLines', { count: next.length, prices: plan.map((p) => p.price) });
  return next.length;
}

/** Yesterday (white) lines — time-bounded from Globex open (18:00 ET) to now. */
export function syncYesterdayTpoLines(
  chart: IChartApi | null,
  tpo: TpoOverlayData | null,
  paneIndex: number,
): number {
  if (!chart) return 0;

  // Remove previous yesterday series
  const prev = horizStore.get(chart) ?? [];
  for (const s of prev) {
    try { chart.removeSeries(s); } catch { /* noop */ }
  }

  const plan = buildTpoPlan(tpo);
  const ydayLevels = plan.filter((lv) => lv.session === 'yesterday');
  if (!ydayLevels.length) { horizStore.set(chart, []); return 0; }

  // Globex open: today 18:00 ET (previous calendar day for overnight)
  // Approximate: find the nearest 18:00 ET in unix seconds
  const nowSec = Math.floor(Date.now() / 1000);
  let globexOpen: number;
  try {
    const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const h = et.getHours();
    // If before 18:00 ET, Globex started yesterday 18:00
    // If after 18:00 ET, Globex started today 18:00
    const etMidnight = new Date(et);
    etMidnight.setHours(0, 0, 0, 0);
    const midnightUnix = Math.floor(etMidnight.getTime() / 1000);
    if (h >= 18) {
      globexOpen = midnightUnix + 18 * 3600; // today 18:00
    } else {
      globexOpen = midnightUnix - 6 * 3600; // yesterday 18:00
    }
  } catch {
    globexOpen = nowSec - 24 * 3600; // fallback: 24h ago
  }

  const t0 = globexOpen as Time;
  const t1 = (nowSec + 300) as Time;

  const next: ISeriesApi<'Line'>[] = [];
  for (const lv of ydayLevels) {
    try {
      const s = chart.addSeries(
        LineSeries,
        {
          color: lv.color,
          lineWidth: (lv.width >= 2 ? 2 : 1) as LineWidth,
          lineStyle: lv.dashed ? LineStyle.Dashed : LineStyle.Solid,
          crosshairMarkerVisible: false,
          lastValueVisible: false,
          priceLineVisible: false,
          title: '',
        },
        paneIndex,
      );
      s.setData([
        { time: t0, value: lv.price },
        { time: t1, value: lv.price },
      ]);
      next.push(s);
    } catch (e) {
      console.error('[TPO] yesterday line series failed', lv, e);
    }
  }
  horizStore.set(chart, next);
  return next.length;
}

export function extendAutoscaleForTpo(
  series: ISeriesApi<'Candlestick'>,
  tpo: TpoOverlayData | null,
): void {
  const tpoPrices = collectTpoPrices(tpo);
  if (!tpoPrices.length) {
    series.applyOptions({ autoscaleInfoProvider: undefined });
    return;
  }
  series.applyOptions({
    autoscaleInfoProvider: (original) => {
      const base = original();
      const mn = Math.min(...tpoPrices);
      const mx = Math.max(...tpoPrices);
      if (base == null) {
        return { priceRange: { minValue: mn, maxValue: mx } };
      }
      return {
        priceRange: {
          minValue: Math.min(base.priceRange.minValue, mn),
          maxValue: Math.max(base.priceRange.maxValue, mx),
        },
        margins: base.margins,
      };
    },
  });
  series.priceScale().applyOptions({ autoScale: true });
}

export function refitPriceScaleForTpo(series: ISeriesApi<'Candlestick'> | null): void {
  if (!series) return;
  try {
    series.priceScale().applyOptions({ autoScale: true });
  } catch {
    /* noop */
  }
}
