import type { IChartApi } from 'lightweight-charts';

// Lightweight registry for syncing chart time scales.
// Not a Zustand store — uses plain refs to avoid re-renders.

let mainChart: IChartApi | null = null;
let volumeChart: IChartApi | null = null;
let syncing = false;
let syncUnlockRaf: number | null = null;

function syncTimeScales(source: IChartApi, target: IChartApi) {
  if (syncing) return;
  syncing = true;
  try {
    const range = source.timeScale().getVisibleLogicalRange();
    if (range) {
      target.timeScale().setVisibleLogicalRange(range);
    }
  } catch {
    // ignore sync errors during init
  }
  if (syncUnlockRaf != null) cancelAnimationFrame(syncUnlockRaf);
  syncUnlockRaf = requestAnimationFrame(() => {
    syncing = false;
    syncUnlockRaf = null;
  });
}

/** Push main chart's visible window to the volume/CVD chart (e.g. after setData). */
export function syncVolumeFromMain() {
  if (mainChart && volumeChart) syncTimeScales(mainChart, volumeChart);
}

export function registerMainChart(chart: IChartApi) {
  mainChart = chart;
  chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    if (volumeChart) syncTimeScales(chart, volumeChart);
  });
  // Initial sync if volume already registered
  if (volumeChart) {
    syncTimeScales(chart, volumeChart);
  }
}

export function registerVolumeChart(chart: IChartApi) {
  volumeChart = chart;
  chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    if (mainChart) syncTimeScales(chart, mainChart);
  });
  // Initial sync from main
  if (mainChart) {
    syncTimeScales(mainChart, chart);
  }
}

export function unregisterMainChart() {
  mainChart = null;
}

export function unregisterVolumeChart() {
  volumeChart = null;
}
