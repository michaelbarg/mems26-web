'use client';
import { useState, useCallback, useRef, useEffect } from 'react';
import { TopBar } from './TopBar';
import { Layer0Strip } from './Layer0Strip';
import { SidePanel } from './SidePanel';
import { ViewTabs, type DashboardView } from './ViewTabs';
import { PriceDebugConsole } from '../PriceDebugConsole';
// import { ChartV5a } from '../chart/ChartV5a';  // W5.13: kept as backup
import { ChartV5b } from '../chart/v5b/ChartV5b';
import { TradeHistoryStrip } from '../strips/TradeHistoryStrip';
import { ShadowSoakStrip } from '../strips/ShadowSoakStrip';
import { KeyLevelsStrip } from '../strips/KeyLevelsStrip';
import { BuildStatusTab } from '../build_status/BuildStatusTab';
import { useSystemEvents } from '../../hooks/useSystemEvents';
import { useSystemStatePolling } from '../../hooks/useSystemStatePolling';
import { usePriceStream } from '../../hooks/usePriceStream';
import { useLivePricePoll } from '../../hooks/useLivePricePoll';
import { BannerStack } from '../banners/BannerStack';
import { SystemControlPanel } from '../controls/SystemControlPanel';
import { COLORS } from '../../design/tokens';

const STORAGE_KEY = 'chart-height-v5c';
const MIN_H = 200, DEFAULT_H = 720, MAX_H = 800;
const PRESETS = { Min: 240, Md: 480, Max: 720 } as const;

function clamp(v: number) { return Math.max(MIN_H, Math.min(MAX_H, v)); }

export function V9Dashboard() {
  useSystemEvents();
  // P30 FORENSICS: 5s is the floor — fires/ZLR need <5s visibility.
  // Do NOT increase past 5000 without Michael's approval.
  useSystemStatePolling(5000);
  usePriceStream();
  useLivePricePoll(true);

  // Top-level view switcher · added 2026-05-26 for Build Status tab
  // SSR-stable default 'main'; deep-link (?view=) is applied on mount to avoid a
  // server/client hydration mismatch. Reading window in the useState initializer
  // made the server render 'main' and the client 'build_status' → mismatch.
  // Fixed 2026-06-15 (mirrors the chartH SSR-stable+useEffect pattern below).
  const [view, setView] = useState<DashboardView>('main');
  useEffect(() => {
    const v = new URLSearchParams(window.location.search).get('view');
    if (v === 'build_status' || v === 'trade_review') setView(v);
  }, []);

  // Chart height — SSR-stable default, hydrate from localStorage on mount
  const [chartH, setChartH] = useState(DEFAULT_H);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) setChartH(clamp(Number(saved)));
    setHydrated(true);
  }, []);
  const persistH = useCallback((h: number) => {
    const clamped = clamp(h);
    setChartH(clamped);
    localStorage.setItem(STORAGE_KEY, String(clamped));
  }, []);

  // Drag handle
  const dragging = useRef(false);
  const startY = useRef(0);
  const startH = useRef(DEFAULT_H);
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true;
    startY.current = e.clientY;
    startH.current = chartH;
    e.preventDefault();
  }, [chartH]);
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      persistH(startH.current + (e.clientY - startY.current));
    };
    const onUp = () => { dragging.current = false; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [persistH]);

  return (
    <div
      className="flex flex-col h-screen"
      style={{ background: COLORS.bgBase }}
    >
      <BannerStack />
      <ViewTabs active={view} onChange={setView} />

      {view === 'main' ? (
        <>
          <TopBar />
          <Layer0Strip />
          <KeyLevelsStrip />
          <div className="flex flex-1 min-h-0">
            <div className="flex-1 flex flex-col min-h-0">
              {/* Chart area — flex-1 fills vertical space, min-height from drag */}
              <div style={{ flex: 1, minHeight: MIN_H, height: chartH, overflow: 'hidden' }}>
                <ChartV5b />
              </div>

              {/* Drag handle + presets */}
              <div className="flex items-center" style={{ userSelect: 'none' }}>
                <div
                  onMouseDown={onMouseDown}
                  style={{
                    flex: 1, height: 5, cursor: 'ns-resize',
                    background: dragging.current ? COLORS.borderFaint : 'transparent',
                    borderTop: `1px solid ${COLORS.borderFaint}`,
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = COLORS.borderFaint)}
                  onMouseLeave={e => { if (!dragging.current) e.currentTarget.style.background = 'transparent'; }}
                />
                <div className="flex gap-1 px-2">
                  {(Object.entries(PRESETS) as [string, number][]).map(([label, h]) => (
                    <button key={label} onClick={() => persistH(h)}
                      style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3, cursor: 'pointer', border: 'none',
                        background: hydrated && chartH === h ? 'rgba(255,255,255,0.12)' : 'transparent',
                        color: hydrated && chartH === h ? '#e5e5e5' : '#525252',
                      }}
                    >{label}</button>
                  ))}
                </div>
              </div>

              {/* Strips below chart */}
              <TradeHistoryStrip />
              <ShadowSoakStrip />
            </div>
            <SidePanel />
          </div>
          <PriceDebugConsole />
          <SystemControlPanel />
        </>
      ) : view === 'build_status' ? (
        <div className="flex-1 min-h-0">
          <BuildStatusTab />
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          {/* The proven standalone marker tool, served live from /public and fed by
              the API (replay + trade_reviews). Reuses its exact render/marking. */}
          <iframe src="/marker.html" title="Trade Marker (live)" style={{ width: '100%', height: '100%', border: 'none', background: '#0d1117' }} />
        </div>
      )}
    </div>
  );
}
