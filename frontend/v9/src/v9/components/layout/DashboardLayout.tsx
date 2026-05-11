'use client';
import { Panel, Group, Separator } from 'react-resizable-panels';
import { TopBar } from './TopBar';
import { ChartArea } from '../chart/ChartArea';
import { VolumePanel } from '../volume/VolumePanel';
import { SystemPanelsBar } from '../panels/SystemPanelsBar';
import { SettingsDrawer } from '../settings/SettingsDrawer';
import { LeftTabs } from '../sidebar/LeftTabs';
import { PriceDebugConsole } from '../PriceDebugConsole';
import { useLayoutStore } from '../../stores/layoutStore';

export function DashboardLayout() {
  const { panelsCollapsed, settingsOpen } = useLayoutStore();

  return (
    <div className="h-screen w-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      <TopBar />
      <div className="flex-1 flex min-h-0">
        {/* Left Tabs Sidebar — 240px fixed */}
        <LeftTabs />

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
      </div>
      {settingsOpen && <SettingsDrawer />}
      <PriceDebugConsole />
    </div>
  );
}
