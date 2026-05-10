'use client';
import { useLayoutStore, type TabId } from '../../stores/layoutStore';
import { TradeTab } from './tabs/TradeTab';
import { SignalTab } from './tabs/SignalTab';
import { SetupsTab } from './tabs/SetupsTab';
import { PatternsTab } from './tabs/PatternsTab';
import { DataTab } from './tabs/DataTab';
import { OrdersTab } from './tabs/OrdersTab';
import { DayTab } from './tabs/DayTab';
import { StatsTab } from './tabs/StatsTab';
import { PredActualTab } from './tabs/PredActualTab';

interface TabDef {
  id: TabId;
  label: string;
  shortcut: number; // 1-9
}

const TABS: TabDef[] = [
  { id: 'trade',       label: '\u05DE\u05E1\u05D7\u05E8',       shortcut: 1 },
  { id: 'signal',      label: '\u05E1\u05D9\u05D2\u05E0\u05DC',      shortcut: 2 },
  { id: 'setups',      label: '\u05E1\u05D8\u05D0\u05E4\u05D9\u05DD',      shortcut: 3 },
  { id: 'patterns',    label: '\u05EA\u05D1\u05E0\u05D9\u05D5\u05EA',    shortcut: 4 },
  { id: 'data',        label: '\u05E0\u05EA\u05D5\u05E0\u05D9\u05DD',        shortcut: 5 },
  { id: 'orders',      label: '\u05E4\u05E7\u05D5\u05D3\u05D5\u05EA',      shortcut: 6 },
  { id: 'day',         label: '\u05D9\u05D5\u05DD',         shortcut: 7 },
  { id: 'stats',       label: '\u05E1\u05D8\u05D8\u05D9\u05E1\u05D8\u05D9\u05E7\u05D4',       shortcut: 8 },
  { id: 'pred_actual', label: 'Pred/Actual', shortcut: 9 },
];

const TAB_COMPONENTS: Record<TabId, React.FC> = {
  trade: TradeTab,
  signal: SignalTab,
  setups: SetupsTab,
  patterns: PatternsTab,
  data: DataTab,
  orders: OrdersTab,
  day: DayTab,
  stats: StatsTab,
  pred_actual: PredActualTab,
};

export function LeftTabs() {
  const activeTab = useLayoutStore((s) => s.activeTab);
  const setActiveTab = useLayoutStore((s) => s.setActiveTab);

  const ActiveComponent = TAB_COMPONENTS[activeTab];

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
        <ActiveComponent />
      </div>
    </div>
  );
}
