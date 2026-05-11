'use client';
import { useLayoutStore, type TabId } from '../../stores/layoutStore';
import { TraderTab } from './tabs/TraderTab';
import { MarketTab } from './tabs/MarketTab';
import { SetupsTab } from './tabs/SetupsTab';
import { SystemsTab } from './tabs/SystemsTab';
import { DayTab } from './tabs/DayTab';
import { DecisionsTab } from './tabs/DecisionsTab';
import { PatternsTab } from './tabs/PatternsTab';
import { PerformanceTab } from './tabs/PerformanceTab';
import { PredictionsTab } from './tabs/PredictionsTab';

interface TabDef {
  id: TabId;
  label: string;
  shortcut: number;
}

const TABS: TabDef[] = [
  { id: 'trader',      label: '\u05E1\u05D5\u05D7\u05E8',       shortcut: 1 },
  { id: 'market',      label: '\u05E9\u05D5\u05E7',        shortcut: 2 },
  { id: 'setups',      label: '\u05E1\u05D8\u05D0\u05E4\u05D9\u05DD',      shortcut: 3 },
  { id: 'systems',     label: '\u05DE\u05E2\u05E8\u05DB\u05D5\u05EA',     shortcut: 4 },
  { id: 'day',         label: '\u05D9\u05D5\u05DD',         shortcut: 5 },
  { id: 'decisions',   label: '\u05D4\u05D7\u05DC\u05D8\u05D5\u05EA',   shortcut: 6 },
  { id: 'patterns',    label: '\u05EA\u05D1\u05E0\u05D9\u05D5\u05EA',    shortcut: 7 },
  { id: 'performance', label: '\u05D1\u05D9\u05E6\u05D5\u05E2\u05D9\u05DD',  shortcut: 8 },
  { id: 'predictions', label: '\u05EA\u05D7\u05D6\u05D9\u05D5\u05EA',  shortcut: 9 },
];

const TAB_COMPONENTS: Record<TabId, React.FC> = {
  trader: TraderTab,
  market: MarketTab,
  setups: SetupsTab,
  systems: SystemsTab,
  day: DayTab,
  decisions: DecisionsTab,
  patterns: PatternsTab,
  performance: PerformanceTab,
  predictions: PredictionsTab,
};

export function LeftTabs() {
  const activeTab = useLayoutStore((s) => s.activeTab);
  const setActiveTab = useLayoutStore((s) => s.setActiveTab);

  const ActiveComponent = TAB_COMPONENTS[activeTab] ?? TAB_COMPONENTS.trader;

  return (
    <div
      className="flex flex-col h-full shrink-0"
      style={{ width: 240, background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)' }}
      dir="rtl"
    >
      {/* Tab buttons */}
      <div className="flex flex-col shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="text-right px-3 py-1.5 text-xs transition-colors"
            style={{
              background: activeTab === tab.id ? 'var(--bg-tertiary)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderRight: activeTab === tab.id ? '2px solid #58a6ff' : '2px solid transparent',
              fontWeight: activeTab === tab.id ? 700 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-2" dir="ltr">
        {ActiveComponent ? <ActiveComponent /> : null}
      </div>
    </div>
  );
}
