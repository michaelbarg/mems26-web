import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type TabId = 'trader' | 'market' | 'setups' | 'systems' | 'day' | 'decisions' | 'patterns' | 'performance' | 'predictions';

interface LayoutState {
  chartPercent: number;
  panelsCollapsed: boolean;
  settingsOpen: boolean;
  settingsSystemId: number | null;
  activeChartType: '5min' | 'tick_reversal';
  showBidAskSplit: boolean;
  activeTab: TabId;

  setChartPercent: (pct: number) => void;
  togglePanels: () => void;
  openSettings: (systemId: number) => void;
  closeSettings: () => void;
  setActiveChartType: (type: '5min' | 'tick_reversal') => void;
  toggleBidAskSplit: () => void;
  setActiveTab: (tab: TabId) => void;
}

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set) => ({
      chartPercent: 70,
      panelsCollapsed: false,
      settingsOpen: false,
      settingsSystemId: null,
      activeChartType: '5min',
      showBidAskSplit: false,
      activeTab: 'trader' as TabId,

      setChartPercent: (pct) => set({ chartPercent: pct }),
      togglePanels: () => set((s) => ({ panelsCollapsed: !s.panelsCollapsed })),
      openSettings: (systemId) => set({ settingsOpen: true, settingsSystemId: systemId }),
      closeSettings: () => set({ settingsOpen: false, settingsSystemId: null }),
      setActiveChartType: (type) => set({ activeChartType: type }),
      toggleBidAskSplit: () => set((s) => ({ showBidAskSplit: !s.showBidAskSplit })),
      setActiveTab: (tab) => set({ activeTab: tab }),
    }),
    { name: 'mems26-v9-layout' }
  )
);
