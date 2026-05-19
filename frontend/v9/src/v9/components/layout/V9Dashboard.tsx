'use client';
import { useState, useCallback, useRef, useEffect } from 'react';
import { TopBar } from './TopBar';
import { Layer0Strip } from './Layer0Strip';
import { SidePanel } from './SidePanel';
import { PriceDebugConsole } from '../PriceDebugConsole';
// import { ChartV5a } from '../chart/ChartV5a';  // W5.13: kept as backup
import { ChartV5b } from '../chart/v5b/ChartV5b';
import { TradeHistoryStrip } from '../strips/TradeHistoryStrip';
import { ShadowSoakStrip } from '../strips/ShadowSoakStrip';
import { useSystemEvents } from '../../hooks/useSystemEvents';
import { useSystemStatePolling } from '../../hooks/useSystemStatePolling';
import { usePriceStream } from '../../hooks/usePriceStream';
import { useLivePricePoll } from '../../hooks/useLivePricePoll';
import { BannerStack } from '../banners/BannerStack';
import { SoundProvider } from '../sounds/SoundProvider';
import { COLORS } from '../../design/tokens';

const STORAGE_KEY = 'chart-height-v5c';
const MIN_H = 200, DEFAULT_H = 720, MAX_H = 800;
const PRESETS = { Min: 240, Md: 480, Max: 720 } as const;

function clamp(v: number) { return Math.max(MIN_H, Math.min(MAX_H, v)); }

export function V9Dashboard() {
  useSystemEvents();
  useSystemStatePolling(2000);
  usePriceStream();
  useLivePricePoll(true);

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
      <SoundProvider />
      <TopBar />
      <Layer0Strip />
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
    </div>
  );
}
