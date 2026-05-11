/** MEMS26 Design Tokens — Master Visual Reference V5 */

export const COLORS = {
  // Backgrounds
  bgBase: '#0a0a0a',
  bgSurface1: '#0d0d0d',
  bgSurface2: '#0f0f0f',
  bgSurface3: '#101010',
  bgSurface4: '#141414',
  bgSurface5: '#1a1a1a',
  bgSurface6: '#1f1f1f',

  // Borders
  borderFaint: '#1a1a1a',
  borderTertiary: '#262626',
  borderSecondary: '#333333',
  borderPrimary: '#404040',
  borderStrong: '#525252',

  // Text
  textPrimary: '#e5e5e5',
  textSecondary: '#a3a3a3',
  textTertiary: '#737373',
  textDisabled: '#525252',
  textDim: '#404040',

  // Semantic
  bull: '#16a34a',
  bullLight: '#86efac',
  bullFill: '#dcfce7',
  bear: '#dc2626',
  bearLight: '#fca5a5',
  warning: '#f59e0b',
  caution: '#facc15',

  // Modes
  modeShadow: '#facc15',
  modeDemo: '#06b6d4',
  modeLive: '#dc2626',

  // Chart
  tpoPoc: '#ec4899',
  ibLine: '#4ade80',
  currentPriceLine: '#facc15',
} as const;

export const TYPOGRAPHY = {
  fontSans: 'system-ui, -apple-system, sans-serif',
  fontMono: 'ui-monospace, monospace',

  textXs: '8px',
  textSm: '10px',
  textMd: '11px',
  textLg: '13px',
  textXl: '14px',

  weightRegular: 400,
  weightMedium: 500,
  weightSemibold: 600,
  weightBold: 700,

  letterSpacingLabel: '0.5px',
} as const;

export const SIZES = {
  topBarHeight: 36,
  layer0Height: 22,
  chartToolbarHeight: 28,
  volumeStripHeight: 28,
  sidePanelWidth: 248,

  pillFiring: { w: 36, h: 32 },
  pillObserving: { w: 36, h: 28 },
  pillBorderRadius: 5,
  pillBorderSelected: 1.5,

  lensCardRadius: 6,
  lensCardBorder: 0.5,
  lensPadding: 8,
  lensTabBorderActive: 1.5,
} as const;

export const ANIMATIONS = {
  pulseFire: {
    duration: '1.6s',
    easing: 'ease-in-out',
    keyframes: { from: 1, mid: 0.72, to: 1 },
  },
  stateTransition: '200ms',
  tradeEntryFlash: '800ms',
  tradeTintExpand: '400ms',
  justClosedFade: '30s',
} as const;
