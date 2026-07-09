'use client';
import { Panel, Group, Separator } from 'react-resizable-panels';
import { TopBar } from './TopBar';
import { ChartArea } from '../chart/ChartArea';
import { VolumePanel } from '../volume/VolumePanel';
import { SystemPanelsBar } from '../panels/SystemPanelsBar';
import { SettingsDrawer } from '../settings/SettingsDrawer';
import { LeftTabs } from '../sidebar/LeftTabs';
import { SidePanel } from './SidePanel';
import { Layer0Strip } from './Layer0Strip';
import { PriceDebugConsole } from '../PriceDebugConsole';
import { useLayoutStore } from '../../stores/layoutStore';

export function DashboardLayout() {
  const { panelsCollapsed, settingsOpen } = useLayoutStore();

  return (
    <div className="h-screen w-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      <TopBar />
      <Layer0Strip />
      <div className="flex-1 flex min-h-0">
        {/* מייקל 07-09: כפתור-הפאנלים "לא עשה כלום" — הוא הסתיר רק את הפס התחתון.
            עכשיו הוא מקפל את שלושת הפאנלים (שמאל, תחתון, ימין) → צ'ארט על כל המסך. */}
        {!panelsCollapsed && <LeftTabs />}

        {/* Center: Chart + Volume + Bottom Panels */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          <Group orientation="vertical" className="flex-1">
            <Panel defaultSize={70} minSize={30} id="chart">
              <ChartArea />
            </Panel>
            <Separator className="h-[3px] cursor-row-resize" />
            <Panel defaultSize={30} minSize={10} id="volume">
              <VolumePanel />
            </Panel>
          </Group>
          {!panelsCollapsed && <SystemPanelsBar />}
        </div>

        {/* Right: Side Panel — Switcher + Lens */}
        {!panelsCollapsed && <SidePanel />}
      </div>
      {settingsOpen && <SettingsDrawer />}
      <PriceDebugConsole />
    </div>
  );
}
