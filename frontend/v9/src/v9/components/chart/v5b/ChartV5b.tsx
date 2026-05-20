'use client';
import {
  createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi,
  CandlestickSeries,
} from 'lightweight-charts';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { usePriceStore } from '../../../stores/priceStore';
import { registerMainChart, unregisterMainChart, syncVolumeFromMain } from '../../../stores/chartSyncStore';
import { SierraLevelsOverlay, type TpoOverlayData } from './SierraLevelsOverlay';
import { CvdChartPane, loadCvdPanelDefaultPct, saveCvdPanelPct } from './CvdChartPane';
import { WoodiesCciPanel } from '../woodies/WoodiesCciPanel';
import { WoodiesPanelTab } from '../woodies/WoodiesPanelTab';

const LS_WOODIES_OPEN = 'mems26-woodies-panel-open';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const INITIAL_BAR_LIMIT = 600;

const TF_ENDPOINTS: Record<string, string> = {
  '3m': 'bars3m', '5m': 'bars5min', '15m': 'bars15m', '30m': 'bars30m', '1h': 'bars1h',
};

const TF_SECONDS: Record<string, number> = { '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600 };

/**
 * DB / Sierra bar timestamps are wall-clock ET with no timezone suffix
 * ("2026-05-19 16:55:00.000000"). `new Date(...)` in the browser would
 * otherwise parse them as local time (IST = UTC+3 for Michael), placing
 * each bar ~7 hours away from the CVD points whose `t` is already epoch
 * UTC. Anchoring the parse at -04:00 (EDT) keeps the two panes on the
 * same UTC line — the only contract `lightweight-charts` relies on.
 *
 * Trade-off: this falls back to EDT and is wrong by 1 hour during EST
 * (winter Nov-Mar). Acceptable until the API ships `ts_unix` directly.
 */
function tsToUnix(ts: string): number {
  return Math.floor(new Date(ts.replace(' ', 'T') + '-04:00').getTime() / 1000);
}

function latestBarUnix(bars: Array<{ ts?: string }>): number | null {
  const last = bars[bars.length - 1];
  return last?.ts ? tsToUnix(last.ts) : null;
}

export function ChartV5b() {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [overlaySize, setOverlaySize] = useState({ width: 0, height: 0 });
  const [barsForOverlay, setBarsForOverlay] = useState<Array<{ ts: string }>>([]);
  const [tpoOverlay, setTpoOverlay] = useState<TpoOverlayData | null>(null);
  const earliestTsRef = useRef<string | null>(null);
  const latestTsRef = useRef<number | null>(null);
  const loadingHistoryRef = useRef(false);
  const skipRangeEventsRef = useRef(2);
  const allBarsRef = useRef<any[]>([]);
  const [activeTf, setActiveTf] = useState('5m');
  const [kzLabel, setKzLabel] = useState('MKT');
  const [woodiesOpen, setWoodiesOpen] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(LS_WOODIES_OPEN) === '1';
  });
  // P30 (2026-05-20): live CVD pane height %. Drives which pane owns the
  // shared time axis: below `CVD_AXIS_OWN_MIN_PCT` the CVD pane is too
  // short to show its own labels usefully, so we restore the price pane's
  // bottom axis. At or above the threshold the CVD pane keeps the axis.
  // Initialized SSR-stable via loadCvdPanelDefaultPct (localStorage).
  const [cvdPanelPct, setCvdPanelPct] = useState<number>(() => loadCvdPanelDefaultPct());
  const CVD_AXIS_OWN_MIN_PCT = 14;
  const cvdOwnsAxis = cvdPanelPct >= CVD_AXIS_OWN_MIN_PCT;

  const toggleWoodiesPanel = useCallback(() => {
    setWoodiesOpen((open) => {
      const next = !open;
      localStorage.setItem(LS_WOODIES_OPEN, next ? '1' : '0');
      return next;
    });
  }, []);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0a0a0a' },
        textColor: '#a3a3a3',
        fontSize: 10,
        fontFamily: 'ui-monospace, monospace',
      },
      grid: {
        vertLines: { color: '#1a1a1a', style: 1 },
        horzLines: { color: '#1a1a1a', style: 1 },
      },
      rightPriceScale: {
        borderColor: '#262626',
        // Breathing room top & bottom so candles don't get smashed against
        // the pane edges when the time axis is hidden. Without the bottom
        // padding the last candle scrapes the bottom of the pane and
        // distorts visually.
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      timeScale: {
        // P30 (2026-05-20): default ON so the time axis is ALWAYS visible —
        // including when the CVD pane is collapsed or dragged to a height
        // too small to render its own labels. The CVD pane's mount effect
        // (and ChartV5b's cvdPanelPct watcher) hides this axis when the
        // CVD pane is large enough to own the cockpit's shared time axis.
        visible: true,
        borderColor: '#262626',
        timeVisible: true,
        secondsVisible: false,
        // P30 alignment guarantee: lightweight-charts defaults rightOffset
        // to 0, but pin it explicitly so a future global default change
        // can't drift the two panes' candle positions apart.
        rightOffset: 0,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
        horzLine: { color: '#525252', style: 3, width: 1, labelBackgroundColor: '#06b6d4' },
      },
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#dc2626',
      borderUpColor: '#16a34a',
      borderDownColor: '#dc2626',
      wickUpColor: '#16a34a',
      wickDownColor: '#dc2626',
    });

    chartRef.current = chart;
    candleRef.current = candles;
    registerMainChart(chart);

    const ro = new ResizeObserver(([entry]) => {
      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      unregisterMainChart();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!wrapperRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setOverlaySize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    ro.observe(wrapperRef.current);
    return () => ro.disconnect();
  }, []);

  // P30 (2026-05-20): keep the time axis visible in every CVD pane state.
  // Apply price-chart axis visibility = !cvdOwnsAxis so exactly one axis is
  // visible at any moment (avoids the duplicate-axis seam between the two
  // panes when both are normal-height, and restores the price-pane axis
  // when the CVD pane is dragged below the useful-height threshold).
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    try {
      chart.timeScale().applyOptions({ visible: !cvdOwnsAxis });
    } catch {
      /* chart not ready */
    }
  }, [cvdOwnsAxis]);

  const cvdDefaultPct = loadCvdPanelDefaultPct();
  const priceDefaultPct = 100 - cvdDefaultPct;

  // Fetch bars on TF change
  const loadBars = useCallback(async (tf: string) => {
    if (!candleRef.current) return;
    const ep = TF_ENDPOINTS[tf] || 'bars5min';
    try {
      const res = await fetch(`${API}/api/v9/chart/${ep}?limit=${INITIAL_BAR_LIMIT}`);
      const raw = await res.json();
      const bars = Array.isArray(raw) ? raw : [];
      if (!bars.length) return;

      const cDataRaw = bars.map((b: any) => ({
        time: tsToUnix(b.ts) as any,
        open: b.open ?? b.o,
        high: b.high ?? b.h,
        low: b.low ?? b.l,
        close: b.close ?? b.c,
      }));
      // Dedup by `time` (DB sometimes ships two rows for the same minute when
      // a bar is rewritten mid-poll). Last value wins because the bridge POSTs
      // the rewrite after the first version. lightweight-charts throws
      // "data must be asc ordered by time" on a duplicate and aborts the
      // whole setData call — that was producing the "only 3 bars visible"
      // symptom. Also enforce strictly ascending time after dedup.
      const dedupMap = new Map<number, (typeof cDataRaw)[number]>();
      for (const c of cDataRaw) {
        if (Number.isFinite(c.time)) dedupMap.set(Number(c.time), c);
      }
      const cData = Array.from(dedupMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time),
      );
      if (cData.length !== cDataRaw.length) {
        console.warn(
          `[ChartV5b] dedup removed ${cDataRaw.length - cData.length} duplicate bar(s)`,
        );
      }
      // Mirror dedup back into the overlay bars list so SierraLevelsOverlay
      // and CvdChartPane don't compute against duplicate ts values either.
      const tsToBar = new Map<string, { ts: string }>();
      for (const b of bars) tsToBar.set(b.ts, { ts: b.ts });
      const dedupedBars = Array.from(tsToBar.values()).sort(
        (a, b) => tsToUnix(a.ts) - tsToUnix(b.ts),
      );

      allBarsRef.current = dedupedBars;
      setBarsForOverlay(dedupedBars);
      latestTsRef.current = latestBarUnix(dedupedBars);
      formingBarRef.current = null;
      candleRef.current.setData(cData);
      earliestTsRef.current = dedupedBars[0]?.ts || null;
      // Default view shows the most recent 60 bars (5 h of 5 m, 3 h of 3 m, 15 h of 15 m).
      // fitContent on 600 bars produced a sub-1-px-per-candle view that the
      // CVD sync then mirrored onto a 17 h window — user saw 10 price candles
      // and only 2 CVD candles. Lazy-load handler in this file still fetches
      // older data when the user pans left.
      const DEFAULT_VISIBLE = 60;
      const last = cData.length - 1;
      if (last >= 0) {
        const from = Math.max(0, last - DEFAULT_VISIBLE + 1);
        chartRef.current?.timeScale().setVisibleLogicalRange({ from, to: last });
        syncVolumeFromMain();
      } else {
        chartRef.current?.timeScale().fitContent();
        syncVolumeFromMain();
      }
    } catch (e) {
      console.error('ChartV5b load error:', e);
    }
  }, []);

  useEffect(() => { loadBars(activeTf); }, [activeTf, loadBars]);

  // Real-time: live_price tick every 1s → update forming bar
  const formingBarRef = useRef<{ time: number; open: number; high: number; low: number; close: number; vol: number } | null>(null);

  useEffect(() => {
    if (!candleRef.current) return;

    const bucketSize = TF_SECONDS[activeTf] || 300;

    // Subscribe to priceStore (fed by WebSocket) instead of polling /api/v9/live_price
    const unsubPrice = usePriceStore.subscribe((state) => {
      const price = state.price;
      if (!price || !candleRef.current) return;

      const nowSec = Math.floor(Date.now() / 1000);
      const bucket = Math.floor(nowSec / bucketSize) * bucketSize;
      const latestTs = latestTsRef.current;
      if (!latestTs || bucket - latestTs > bucketSize * 3) {
        // Do not draw a detached "now" candle when historical DB bars are stale.
        formingBarRef.current = null;
        return;
      }

      const fb = formingBarRef.current;
      if (fb && fb.time === bucket) {
        fb.high = Math.max(fb.high, price);
        fb.low = Math.min(fb.low, price);
        fb.close = price;
        fb.vol += 1;
      } else {
        formingBarRef.current = { time: bucket, open: price, high: price, low: price, close: price, vol: 1 };
      }

      const bar = formingBarRef.current!;
      candleRef.current?.update({ time: bar.time as any, open: bar.open, high: bar.high, low: bar.low, close: bar.close });
    });

    // Finalized bars poll every 5s — replaces historical bars with DB truth.
    // P30 2026-05-20: lightweight-charts `update()` requires strictly
    // monotonic time (>= last bar). Sort ASC and skip duplicates/older
    // times to avoid `Cannot update oldest data` crashes; previously the
    // CVD pane stayed empty because every update call threw.
    const barsPoll = setInterval(async () => {
      const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
      try {
        const res = await fetch(`${API}/api/v9/chart/${ep}?limit=3`);
        const raw = await res.json();
        const bars = Array.isArray(raw) ? raw : [];
        const latest = latestBarUnix(bars);
        if (latest) latestTsRef.current = Math.max(latestTsRef.current ?? latest, latest);
        const sorted = bars
          .map((b: any) => {
            const t = tsToUnix(b.ts);
            return Number.isFinite(t) ? { ...b, _t: t } : null;
          })
          .filter(Boolean)
          .sort((a: any, b: any) => a._t - b._t);
        for (const b of sorted) {
          candleRef.current?.update({
            time: b._t as any,
            open: b.open ?? b.o,
            high: b.high ?? b.h,
            low: b.low ?? b.l,
            close: b.close ?? b.c,
          });
        }
      } catch {}
    }, 5000);

    return () => { unsubPrice(); clearInterval(barsPoll); };
  }, [activeTf]);

  // Historical scroll-back: load older bars when user pans left
  useEffect(() => {
    if (!chartRef.current) return;
    const onRangeChange = (range: any) => {
      if (skipRangeEventsRef.current > 0) {
        skipRangeEventsRef.current -= 1;
        return;
      }
      if (!range || loadingHistoryRef.current || !earliestTsRef.current) return;
      if (allBarsRef.current.length >= 2000) return; // cap memory
      // User panned near left edge → fetch older bars (not on initial fitContent)
      if (range.from < 20 && range.from >= 0 && allBarsRef.current.length < 2000) {
        loadingHistoryRef.current = true;
        const ep = TF_ENDPOINTS[activeTf] || 'bars5min';
        fetch(`${API}/api/v9/chart/${ep}?limit=240&before=${encodeURIComponent(earliestTsRef.current!)}`)
          .then(r => r.json())
          .then(raw => {
            const older = Array.isArray(raw) ? raw : [];
            if (!older.length) { loadingHistoryRef.current = false; return; }
            // Prepend + dedup by timestamp
            const existing = new Set(allBarsRef.current.map((b: any) => b.ts));
            const fresh = older.filter((b: any) => !existing.has(b.ts));
            const merged = [...fresh, ...allBarsRef.current];
            allBarsRef.current = merged;
            setBarsForOverlay(merged.map((b: { ts: string }) => ({ ts: b.ts })));
            earliestTsRef.current = merged[0]?.ts || earliestTsRef.current;
            // Re-set full data (sorted time-ascending)
            candleRef.current?.setData(merged.map((b: any) => ({
              time: tsToUnix(b.ts) as any,
              open: b.open ?? b.o, high: b.high ?? b.h,
              low: b.low ?? b.l, close: b.close ?? b.c,
            })));
            loadingHistoryRef.current = false;
          })
          .catch(() => { loadingHistoryRef.current = false; });
      }
    };
    chartRef.current.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);
    return () => { try { chartRef.current?.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange); } catch {} };
  }, [activeTf]);

  // Sierra TPO overlay: stepped POC, cyan IB, white prior-day (not full-width price lines)
  useEffect(() => {
    const loadLevels = async () => {
      try {
        const curRes = await fetch(`${API}/api/v9/tpo/current`);
        const d = await curRes.json();
        const prev = d.previous_session;
        setTpoOverlay({
          poc: d.poc,
          vah: d.vah,
          val: d.val,
          session_va_ok: d.session_va_ok,
          periods: d.periods,
          ib_high: d.ib_high,
          ib_mid: d.ib_mid,
          ib_low: d.ib_low,
          ib_locked: d.ib_locked,
          ib_found: d.ib_locked ?? Boolean(d.ib_high),
          stale: d.stale,
          prior_day: d.prior_day,
          previous_session: prev?.found
            ? {
                found: true,
                poc: prev.poc,
                vah: prev.vah,
                val: prev.val,
                opened_ts: prev.opened_ts ?? null,
                closed_ts: prev.closed_ts ?? null,
              }
            : { found: false },
        });
      } catch {
        /* keep last overlay on transient errors */
      }
    };
    loadLevels();
    const id = setInterval(loadLevels, 10000);
    return () => clearInterval(id);
  }, []);

  // Killzone label
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json())
      .then(d => setKzLabel(d?.current_zone?.name || 'MKT')).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // TR countdown
  const [trText, setTrText] = useState('0:00');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const min5 = Math.floor(now.getMinutes() / 5) * 5 + 5;
      const nb = new Date(now); nb.setMinutes(min5, 0, 0);
      if (nb <= now) nb.setMinutes(nb.getMinutes() + 5);
      const s = Math.max(0, Math.floor((nb.getTime() - now.getTime()) / 1000));
      setTrText(`${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`);
    };
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, []);

  /**
   * Q2 fix — snap-to-latest: lazy-load left edge keeps old bars in memory
   * (working as intended, cap 2000), but there was no way to jump back to
   * the rightmost bar once the user scrolled into history. lightweight-charts
   * `scrollToRealTime()` pans the visible window to the latest bar without
   * resetting `allBarsRef` — older bars stay loaded for re-scroll left.
   */
  const goToLatest = useCallback(() => {
    try {
      chartRef.current?.timeScale().scrollToRealTime();
    } catch {
      /* chart not ready */
    }
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%' }}>
      {/* TF selector row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2px 0',
        background: '#0d0d0d', borderBottom: '1px solid #1a1a1a', flexShrink: 0, gap: 4 }}>
        <span suppressHydrationWarning style={{
          fontSize: 9, padding: '2px 8px', borderRadius: 3, fontFamily: 'ui-monospace, monospace',
          background: '#141414', border: '1px solid #f97316', color: '#f97316', fontWeight: 600,
        }}>{kzLabel} · {trText}</span>
        <span style={{ color: '#333', fontSize: 9 }}>|</span>
        {['3m','5m','15m','30m','1h'].map(tf => (
          <button key={tf} data-testid={`tf-btn-${tf}`} suppressHydrationWarning
            onClick={() => setActiveTf(tf)}
            style={{ fontSize: 9, padding: '2px 8px',
              border: tf === activeTf ? '1px solid #06b6d4' : '1px solid transparent',
              borderRadius: 3, cursor: 'pointer',
              background: tf === activeTf ? 'rgba(6,180,212,0.15)' : 'transparent',
              color: tf === activeTf ? '#06b6d4' : '#525252',
              fontWeight: tf === activeTf ? 600 : 400,
            }}>{tf}</button>
        ))}
        <span style={{ color: '#333', fontSize: 9 }}>|</span>
        <button
          data-testid="go-to-latest"
          suppressHydrationWarning
          onClick={goToLatest}
          title="Snap to latest bar"
          style={{
            fontSize: 9,
            padding: '2px 8px',
            border: '1px solid transparent',
            borderRadius: 3,
            cursor: 'pointer',
            background: 'transparent',
            color: '#525252',
            fontWeight: 600,
          }}
        >
          ▶|
        </button>
      </div>
      <Group orientation="vertical" style={{ flex: 1, minHeight: 200 }}>
        <Panel id="price-pane" defaultSize={priceDefaultPct} minSize={35}>
          <div
            ref={wrapperRef}
            data-testid="chart-v5b-price"
            style={{ position: 'relative', width: '100%', height: '100%' }}
          >
            <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
            <SierraLevelsOverlay
              chartRef={chartRef}
              candleRef={candleRef}
              bars={barsForOverlay}
              tpo={tpoOverlay}
              width={overlaySize.width}
              height={overlaySize.height}
            />
            {activeTf === '5m' && (
              <WoodiesPanelTab open={woodiesOpen} onToggle={toggleWoodiesPanel} />
            )}
            <WoodiesCciPanel
              visible={activeTf === '5m' && woodiesOpen}
              onVisibilityChange={(open) => {
                setWoodiesOpen(open);
                localStorage.setItem(LS_WOODIES_OPEN, open ? '1' : '0');
              }}
            />
          </div>
        </Panel>
        <Separator className="h-[4px] cursor-row-resize bg-[#1a1a1a] hover:bg-[#fb950b]" />
        <Panel
          id="cvd-pane"
          defaultSize={cvdDefaultPct}
          minSize={12}
          maxSize={55}
          onResize={(size) => {
            const pct = size.asPercentage;
            if (!Number.isFinite(pct)) return;
            setCvdPanelPct(pct);
            saveCvdPanelPct(pct);
          }}
        >
          <CvdChartPane
            bars={barsForOverlay}
            priceChartRef={chartRef}
            activeTf={activeTf}
            axisVisible={cvdOwnsAxis}
          />
        </Panel>
      </Group>
    </div>
  );
}
