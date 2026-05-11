'use client';
import { TopBar } from './TopBar';
import { Layer0Strip } from './Layer0Strip';
import { SidePanel } from './SidePanel';
import { PriceDebugConsole } from '../PriceDebugConsole';
import { useSystemEvents } from '../../hooks/useSystemEvents';
import { COLORS } from '../../design/tokens';

export function V9Dashboard() {
  useSystemEvents();

  return (
    <div
      className="flex flex-col h-screen"
      style={{ background: COLORS.bgBase }}
    >
      <TopBar />
      <Layer0Strip />
      <div className="flex flex-1 min-h-0">
        <div
          className="flex-1 flex items-center justify-center text-sm"
          style={{ color: COLORS.textTertiary }}
        >
          Chart V5a — coming in PROMPT 10
        </div>
        <SidePanel />
      </div>
      <PriceDebugConsole />
    </div>
  );
}
