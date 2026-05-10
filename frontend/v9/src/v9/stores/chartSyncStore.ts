import type { IChartApi } from 'lightweight-charts';

// Lightweight registry for syncing chart time scales.
// Not a Zustand store — uses plain refs to avoid re-renders.

let mainChart: IChartApi | null = null;
let volumeChart: IChartApi | null = null;
let syncing = false;

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
  syncing = false;
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
