'use client';
import { useState, useCallback, useRef, useEffect } from 'react';
import { TopBar } from './TopBar';
import { Layer0Strip } from './Layer0Strip';
import { SierraTruthStrip } from './SierraTruthStrip';
import { ContextRadar } from './ContextRadar';
import { MultidayProfilePanel } from './MultidayProfilePanel';
import { SidePanel } from './SidePanel';
import { DemoMonitor } from './DemoMonitor';
import { ViewTabs, type DashboardView } from './ViewTabs';
import { PriceDebugConsole } from '../PriceDebugConsole';
// import { ChartV5a } from '../chart/ChartV5a';  // W5.13: kept as backup
import { ChartV5b } from '../chart/v5b/ChartV5b';
import { TradeHistoryStrip } from '../strips/TradeHistoryStrip';
import { ShadowSoakStrip } from '../strips/ShadowSoakStrip';
import { KeyLevelsStrip } from '../strips/KeyLevelsStrip';
import { OpeningTypePanel } from '../strips/OpeningTypePanel';
import { DirectionStrip } from '../strips/DirectionStrip';
import { BuildStatusTab } from '../build_status/BuildStatusTab';
import { TradeReviewTab } from '../trades/TradeReviewTab';
import { TradeDetailsModal } from '../trades/TradeDetailsModal';
import { DayTypeLabelTab } from '../day-type/DayTypeLabelTab';
import { useLayoutStore } from '../../stores/layoutStore';
import { useSystemEvents } from '../../hooks/useSystemEvents';
import { useSystemStatePolling } from '../../hooks/useSystemStatePolling';
import { usePriceStream } from '../../hooks/usePriceStream';
import { useLivePricePoll } from '../../hooks/useLivePricePoll';
import { BannerStack } from '../banners/BannerStack';
import { SystemControlPanel } from '../controls/SystemControlPanel';
import { COLORS } from '../../design/tokens';

const STORAGE_KEY = 'chart-height-v5c';
// מייקל 05.08: "הטבלה גדולה יותר" — תקרת-הגובה הוגדלה; השורות שהוסרו פינו מקום
const MIN_H = 200, DEFAULT_H = 780, MAX_H = 1000;
const PRESETS = { Min: 240, Md: 560, Max: 900 } as const;

function clamp(v: number) { return Math.max(MIN_H, Math.min(MAX_H, v)); }

export function V9Dashboard() {
  // 07-09: the panels button toggled the store but the REAL dashboard (this
  // component, not the unused DashboardLayout) never listened → "nothing
  // happens". Now the right SidePanel collapses → full-width chart.
  const { panelsCollapsed } = useLayoutStore();
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
    if (v === 'build_status' || v === 'trade_review' || v === 'day_type_labeler') setView(v);
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
      <DemoMonitor />
      <ViewTabs active={view} onChange={setView} />

      {view === 'main' ? (
        <>
          <TopBar />
          {/* מייקל 07-27: אמת-סיירה על המסך — פוזיציה/P&L/סטופים ישירות מהחשבון,
              והאזהרה על פוזיציה-ללא-הגנה כבאנר במקום חלון-קופץ */}
          {/* מייקל 05.08: אמת-סיירה + רדאר = שורה אחת שמתאימה גם ל-MacBook 13":
              בלי wrap; במסך צר גוללים אופקית בתוך השורה במקום לשבור לשתיים */}
          <div style={{
            display: 'flex', alignItems: 'stretch', minWidth: 0,
            overflowX: 'auto', whiteSpace: 'nowrap', maxHeight: 64,
          }}>
            <div style={{ flexShrink: 0, minWidth: 'max-content' }}><SierraTruthStrip /></div>
            <div style={{ flexShrink: 0, minWidth: 'max-content' }}><ContextRadar /></div>
          </div>
          {/* מייקל 04.08: המאזן-7-ימים = כפתור-צף בקצה כמו WOODY, אפס-שורות מהטבלה */}
          <MultidayProfilePanel />
          <Layer0Strip />
          {/* מייקל 04.08: שורת-הרמות הועברה מהכותרת אל הפאנל-הצדדי (SidePanel) */}
          {/* מייקל 07-21: פאנל סוג-פתיחה — סוג הפתיחה + מה הוא מבשר + התבניות הרלוונטיות */}
          <OpeningTypePanel />
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
              <DirectionStrip />
              <TradeHistoryStrip />
              <ShadowSoakStrip />
            </div>
            {!panelsCollapsed && <SidePanel />}
          </div>
          <PriceDebugConsole />
          <SystemControlPanel />
        </>
      ) : view === 'build_status' ? (
        <div className="flex-1 min-h-0">
          <BuildStatusTab />
        </div>
      ) : view === 'day_type_labeler' ? (
        <div className="flex-1 min-h-0">
          <DayTypeLabelTab />
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          {/* Collapsible/resizable trade list + the proven live marker tool (iframe). */}
          <TradeReviewTab />
        </div>
      )}

      {/* מייקל 07-10: drawer פירוט-עסקה — מותקן top-level (V9Dashboard הוא הדשבורד האמיתי;
          DashboardLayout לא בשימוש) כדי שכל כרטיס/שורת-עסקה בכל התצוגות יפתח אותו. */}
      <TradeDetailsModal />
    </div>
  );
}
