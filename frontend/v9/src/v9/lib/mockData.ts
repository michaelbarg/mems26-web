/**
 * Mock data for V9 dashboard — used when market is closed or backend unavailable.
 * Generates realistic MES futures bars around a base price.
 */

const BASE_PRICE = 5820;
const TICK = 0.25;

function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function roundTick(p: number) {
  return Math.round(p / TICK) * TICK;
}

export function generateMockBars(count = 100): any[] {
  const bars: any[] = [];
  const now = Date.now();
  let price = BASE_PRICE;

  for (let i = count; i > 0; i--) {
    const ts = new Date(now - i * 5 * 60 * 1000).toISOString();
    const move = rand(-3, 3);
    const o = roundTick(price);
    const c = roundTick(price + move);
    const h = roundTick(Math.max(o, c) + rand(0.5, 2));
    const l = roundTick(Math.min(o, c) - rand(0.5, 2));
    const vol = Math.round(rand(200, 1500));
    const delta = Math.round(rand(-300, 300));

    bars.push({ ts, o, h, l, c, vol, delta });
    price = c;
  }

  return bars;
}

export function generateMockSignals(): any[] {
  const now = Date.now();
  return [
    {
      id: 1, system_id: 1, ts: new Date(now - 3600000).toISOString(),
      classification: 'TREND_DAY', direction: 'LONG', confidence: 0.82,
      payload: { day_type: 'Trend', ib_range: '8.5', mode: 'SHADOW' },
    },
    {
      id: 2, system_id: 2, ts: new Date(now - 1800000).toISOString(),
      classification: 'BREAKOUT', direction: 'LONG', confidence: 0.75,
      payload: { pattern: 'A1_Breakout' },
    },
    {
      id: 3, system_id: 3, ts: new Date(now - 900000).toISOString(),
      classification: 'IMBALANCE_CLUSTER', direction: 'UP', confidence: 0.68,
      payload: { imbalance_count: 4, stacked_count: 2, delta: 156 },
    },
    {
      id: 4, system_id: 6, ts: new Date(now - 600000).toISOString(),
      classification: 'KILLZONE_ACTIVE', direction: null, confidence: null,
      payload: { gate_open: true, session_volume: '12.4K', session_phase: 'New York', quality: 'HIGH' },
    },
  ];
}

export function generateMockLevels() {
  return {
    currentPOC: roundTick(BASE_PRICE + 1.5),
    currentVAH: roundTick(BASE_PRICE + 6),
    currentVAL: roundTick(BASE_PRICE - 4),
    pdh: roundTick(BASE_PRICE + 12),
    pdl: roundTick(BASE_PRICE - 10),
    onh: roundTick(BASE_PRICE + 8),
    onl: roundTick(BASE_PRICE - 6),
    openPrice: roundTick(BASE_PRICE - 1),
    ibh: roundTick(BASE_PRICE + 4),
    ibl: roundTick(BASE_PRICE - 3),
  };
}

export function generateMockWoodiesBars(): any[] {
  const now = Date.now();
  return [{
    ts: new Date(now - 300000).toISOString(),
    cci_14: 42.3, cci_6_tcci: 28.1, ema_34: BASE_PRICE - 0.5,
    trend_state: 'WITH_TREND', zlr_detected: false, zlr_direction: null,
  }];
}
