import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface LayoutState {
  chartPercent: number;
  panelsCollapsed: boolean;
  settingsOpen: boolean;
  settingsSystemId: number | null;
  activeChartType: '5min' | 'tick_reversal';
  showBidAskSplit: boolean;

  setChartPercent: (pct: number) => void;
  togglePanels: () => void;
  openSettings: (systemId: number) => void;
  closeSettings: () => void;
  setActiveChartType: (type: '5min' | 'tick_reversal') => void;
  toggleBidAskSplit: () => void;
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

      setChartPercent: (pct) => set({ chartPercent: pct }),
      togglePanels: () => set((s) => ({ panelsCollapsed: !s.panelsCollapsed })),
      openSettings: (systemId) => set({ settingsOpen: true, settingsSystemId: systemId }),
      closeSettings: () => set({ settingsOpen: false, settingsSystemId: null }),
      setActiveChartType: (type) => set({ activeChartType: type }),
      toggleBidAskSplit: () => set((s) => ({ showBidAskSplit: !s.showBidAskSplit })),
    }),
    { name: 'mems26-v9-layout' }
  )
);
