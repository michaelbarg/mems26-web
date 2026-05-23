import {
  LineSeries,
  LineStyle,
  type IChartApi,
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

// Sierra periods arrive as naive UTC wall-clock ("2026-05-22 13:30:00") or
// occasionally with a TZ suffix (`+00:00`, `Z`, or legacy `-04:00`). Detect
// existing TZ before appending `Z`. Without this guard, `+00:00`-tagged
// strings became `...T17:20:00+00:00Z` → Date.parse=NaN → silently dropped
// period (P31-FE-TPO-1). Treat naive as UTC to match the post-§9 DB ts
// convention and the matching `tsToUnix` fix in ChartV5b.tsx (P31-FE-TZ-2).
const TZ_SUFFIX_RE = /([Zz]|[+-]\d{2}:?\d{2})$/;

export function parseSierraTsToMs(ts: string | null | undefined): number {
  if (!ts) return 0;
  const normalized = String(ts).replace(' ', 'T');
  const final = TZ_SUFFIX_RE.test(normalized) ? normalized : normalized + 'Z';
  const parsed = Date.parse(final);
  return Number.isFinite(parsed) ? parsed : 0;
}

function periodOpenedMs(p: TpoPeriod): number {
  return parseSierraTsToMs(p.opened_ts);
}

function sessionOpenedMs(ts: string | null | undefined): number {
  return parseSierraTsToMs(ts);
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

const lineStore2 = new WeakMap<IChartApi, ISeriesApi<'Line'>[]>();
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

/**
 * Today (pink) lines.
 *
 * Per Sierra Study ID:3 spec (`docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md`)
 * developing POC/VAH/VAL should be **stepped** every 30 min from RTH open
 * to RTH close — rendered by `TpoContinuityOverlay` (LineType.WithSteps).
 *
 * This function provides a **horizontal-fallback** for the case where Sierra
 * has not yet exposed per-period developing values in `tpo.json::periods[]`
 * (see `PROMPT30_10b_TPO_LEVELS_FIX.md` §"Still needed — DLL / Agent 2").
 *
 * If `tpo.periods[]` contains at least one period for today's session, the
 * stepped overlay is responsible and this function renders nothing (and
 * cleans up any prior flat series). Otherwise the flat line is kept so the
 * user always sees a current developing-POC reference during RTH.
 */
export function syncTpoPriceLines(
  chart: IChartApi | null,
  tpo: TpoOverlayData | null,
  paneIndex: number,
): number {
  if (!chart) return 0;

  // Remove previous today series
  const prev = lineStore2.get(chart) ?? [];
  for (const s of prev) {
    try { chart.removeSeries(s); } catch { /* noop */ }
  }

  // Defer to TpoContinuityOverlay (stepped) when Sierra has per-period data
  // for today. Falls back to flat lines only when periods[] is empty for
  // today — keeps a visible reference until the DLL ships periods[] (D-???).
  const todayDay = sessionDay(tpo?.session_opened_ts);
  const todayPeriods = (tpo?.periods ?? []).filter(
    (p) => sessionDay(p.opened_ts) === todayDay,
  );
  if (todayDay && todayPeriods.length >= 1) {
    lineStore2.set(chart, []);
    return 0;
  }

  const plan = buildTpoPlan(tpo);
  const todayLevels = plan.filter((lv) => lv.session === 'today');
  if (!todayLevels.length) { lineStore2.set(chart, []); return 0; }

  // RTH open: today 09:30 ET
  const nowSec = Math.floor(Date.now() / 1000);
  let rthOpen: number;
  try {
    const et = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const etMidnight = new Date(et);
    etMidnight.setHours(0, 0, 0, 0);
    const midnightUnix = Math.floor(etMidnight.getTime() / 1000);
    rthOpen = midnightUnix + 9 * 3600 + 30 * 60; // 09:30 ET today
  } catch {
    rthOpen = nowSec - 7 * 3600; // fallback
  }

  const t0 = rthOpen as Time;
  const t1 = (nowSec + 300) as Time;

  const next: ISeriesApi<'Line'>[] = [];
  for (const lv of todayLevels) {
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
      console.error('[TPO] today line series failed', lv, e);
    }
  }
  lineStore2.set(chart, next);
  return next.length;
}

// HMR-resilient store for yesterday's white LineSeries. A plain WeakMap is
// reset whenever Next.js HMR replaces the module — leaving orphan series on
// the live chart that the new module instance can't reach. Stick the store
// on `globalThis` so it survives HMR cycles. The series refs themselves are
// per-chart in a WeakMap inside the global, so chart disposal still GCs them.
type YdayStore = WeakMap<IChartApi, ISeriesApi<'Line'>[]>;
const G: { __mems26YdayTpoStore?: YdayStore } = globalThis as never;
if (!G.__mems26YdayTpoStore) {
  G.__mems26YdayTpoStore = new WeakMap();
}
const yesterdayLineSeriesStore: YdayStore = G.__mems26YdayTpoStore;

/** Compute today's RTH window in unix seconds (UTC).
 *
 *  Note: lightweight-charts internal time axis is real UTC after the
 *  P31-FE-TZ-2 fix, so we compute RTH open/close as UTC unix directly
 *  from today's date in ET. Handles EDT (UTC-4) and EST (UTC-5)
 *  automatically by probing the actual ET offset for the target date.
 *
 *  History — the earlier implementation built a "wall-clock string + Z"
 *  and back-shifted by `guess - etOnGuess`, which silently used the
 *  **local** TZ offset (IL +3h) instead of ET. On a Mac in IL the lines
 *  ended up at 12:30 ET instead of 09:30 ET — a 3-hour drift that
 *  Michael spotted in the 2026-05-22 17:58 IL screenshot ("they're not
 *  in the right time area"). Switched to Intl.DateTimeFormat probing,
 *  which round-trips through the actual tz database.
 *
 *  The `close` field tracks **now + 1 bar bucket** during the live
 *  session so the line "follows the price" instead of dangling 8h past
 *  the latest candle (Michael 2026-05-22 18:05 IL "they need to follow
 *  along with the price"). Post-16:00 ET it stays pinned at the RTH
 *  close so the daily horizontal stays whole.
 */
function todayRthWindowUnix(): { open: number; close: number } {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date());
    const y = Number(parts.find((p) => p.type === 'year')?.value);
    const mo1 = Number(parts.find((p) => p.type === 'month')?.value);
    const d = Number(parts.find((p) => p.type === 'day')?.value);
    if (!y || !mo1 || !d) throw new Error('bad ET parts');

    // Detect EDT (UTC-4) vs EST (UTC-5) for that ET date by probing the
    // ET wall-clock at 12:00 UTC. 12 - etHour = offsetHours (4 or 5).
    const probeMs = Date.UTC(y, mo1 - 1, d, 12, 0, 0);
    const etHourStr = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour12: false,
      hour: '2-digit',
    }).format(new Date(probeMs));
    const etHour = parseInt(etHourStr, 10);
    const offsetHours = 12 - etHour; // 4=EDT, 5=EST

    const open = Date.UTC(y, mo1 - 1, d, 9 + offsetHours, 30, 0) / 1000;
    const rthClose = Date.UTC(y, mo1 - 1, d, 16 + offsetHours, 0, 0) / 1000;
    // "Follow the price": cap the right edge at one 5-min bucket past
    // current real-UTC unix; never overshoot the RTH close.
    const nowSec = Math.floor(Date.now() / 1000);
    const close = Math.min(rthClose, nowSec + 300);
    return { open, close };
  } catch {
    // Fallback if Intl APIs are unavailable — anchor a 6.5h window
    // around now so the line is at least visible during live RTH.
    const now = Math.floor(Date.now() / 1000);
    return { open: now - 4 * 3600, close: now + 300 };
  }
}

/** Yesterday (white) lines — RTH-bounded horizontal LineSeries.
 *
 *  Per Michael's 2026-05-22 spec ("The line starts at today's market open
 *  and goes until end of trading day. Tomorrow, updated lines of the new
 *  day with yesterday's lines of it"): render yesterday's POC/VAH/VAL as
 *  horizontal references ONLY across today's RTH window (09:30 → 16:00 ET).
 *
 *  Earlier attempts:
 *    1. `LineSeries` with 2 points (open, close) → truncated mid-chart when
 *       bars didn't cover the full range. lightweight-charts won't draw
 *       across a "bar gap."
 *    2. `createPriceLine` (infinite horizontal) → too wide; user explicitly
 *       said "still infinite" (2026-05-22 17:32 IL).
 *
 *  Idempotent reuse: when the level count and current series count match,
 *  this function **reuses the existing series** via `setData` instead of
 *  removing and recreating them. That makes it safe to call at sub-second
 *  cadence (the 10 s bars-poll hooks it for "follow the price" — Michael
 *  2026-05-22 18:24 IL "they have a 2-bar delay"). Recreating LineSeries
 *  every tick would either flicker or thrash memory; setData on the same
 *  series is a no-op render when the data is unchanged.
 */
export function syncYesterdayTpoLines(
  chart: IChartApi | null,
  candleSeries: ISeriesApi<'Candlestick'> | null,
  tpo: TpoOverlayData | null,
  paneIndex: number,
): number {
  if (!chart) return 0;
  // Suppress unused-var lint on candleSeries — kept in the signature so the
  // ChartV5b caller's contract is unchanged and future updates that need to
  // anchor to candle priceScale won't require a new prop.
  void candleSeries;

  const plan = buildTpoPlan(tpo);
  const ydayLevels = plan.filter((lv) => lv.session === 'yesterday');
  const existing = yesterdayLineSeriesStore.get(chart) ?? [];

  // Off-RTH / no levels — clean up any leftover series and exit.
  if (!ydayLevels.length) {
    for (const s of existing) {
      try { chart.removeSeries(s); } catch { /* noop */ }
    }
    yesterdayLineSeriesStore.set(chart, []);
    return 0;
  }

  const { open, close } = todayRthWindowUnix();
  // Dense points every 5 min (matches 5m bar bucket) — single 2-point line
  // is silently clipped by lightweight-charts when bars don't cover the
  // tail of the window. Building 78+ points across 09:30→16:00 ET keeps
  // the horizontal line visible end-to-end.
  const STEP_SEC = 300;
  const pointsPerLevel: Array<{ time: Time; value: number }>[] = ydayLevels.map((lv) => {
    const series: Array<{ time: Time; value: number }> = [];
    for (let t = open; t <= close; t += STEP_SEC) {
      series.push({ time: t as Time, value: lv.price });
    }
    return series;
  });

  // Fast path: reuse existing series when the count matches. setData
  // replaces the data without recreating the underlying canvas object
  // — no flicker, no memory churn, safe to call at 10 s cadence.
  if (existing.length === ydayLevels.length) {
    ydayLevels.forEach((lv, idx) => {
      try {
        existing[idx].applyOptions({
          color: lv.color,
          lineWidth: (lv.width >= 2 ? 2 : 1) as LineWidth,
          lineStyle: lv.dashed ? LineStyle.Dashed : LineStyle.Solid,
        });
        existing[idx].setData(pointsPerLevel[idx]);
      } catch (e) {
        console.error('[TPO] yesterday LineSeries reuse-update failed', lv, e);
      }
    });
    return existing.length;
  }

  // Slow path: level count changed (mount, HMR, or session rotation).
  // Tear down the prior series and recreate fresh.
  for (const s of existing) {
    try { chart.removeSeries(s); } catch { /* noop */ }
  }
  const next: ISeriesApi<'Line'>[] = [];
  ydayLevels.forEach((lv, idx) => {
    try {
      const s = chart.addSeries(
        LineSeries,
        {
          color: lv.color,
          lineWidth: (lv.width >= 2 ? 2 : 1) as LineWidth,
          lineStyle: lv.dashed ? LineStyle.Dashed : LineStyle.Solid,
          crosshairMarkerVisible: false,
          // `lastValueVisible: false` + empty `title` is critical — the
          // SierraLevelsOverlay (SVG-based TpoAxisBadge) is the SINGLE
          // source of truth for the right-axis VAH/POC/VAL labels.
          // If we leave the LineSeries' native label on, the user sees
          // doubled badges (regression spotted in screenshot at
          // 2026-05-22 ~17:55 IL: bold + regular "VAH 7436.75" stacked).
          lastValueVisible: false,
          priceLineVisible: false,
          title: '',
        },
        paneIndex,
      );
      s.setData(pointsPerLevel[idx]);
      next.push(s);
    } catch (e) {
      console.error('[TPO] yesterday LineSeries create failed', lv, e);
    }
  });
  yesterdayLineSeriesStore.set(chart, next);
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
    autoscaleInfoProvider: (original: any) => {
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
