'use client';
import { TopBar } from './TopBar';
import { Layer0Strip } from './Layer0Strip';
import { SidePanel } from './SidePanel';
import { PriceDebugConsole } from '../PriceDebugConsole';
import { ChartV5a } from '../chart/ChartV5a';
import { useSystemEvents } from '../../hooks/useSystemEvents';
import { useSystemStatePolling } from '../../hooks/useSystemStatePolling';
import { COLORS } from '../../design/tokens';

export function V9Dashboard() {
  useSystemEvents();
  useSystemStatePolling(2000);

  return (
    <div
      className="flex flex-col h-screen"
      style={{ background: COLORS.bgBase }}
    >
      <TopBar />
      <Layer0Strip />
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 min-h-0" style={{ minHeight: 280 }}>
          <ChartV5a />
        </div>
        <SidePanel />
      </div>
      <PriceDebugConsole />
    </div>
  );
}
