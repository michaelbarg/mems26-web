export const TOKENS = {
  colors: {
    bullGreen: '#16a34a', bearRed: '#dc2626', yellow: '#facc15',
    orange: '#f97316', cyan: '#06b6d4', grayNeutral: '#525252',
    bgPrimary: '#0a0a0a', bgCard: '#141414', textPrimary: '#ffffff',
  },
  heights: { topbar: 50, layer0: 22, tradeHistory: 18, shadowSoak: 22, volume: 28 },
};
export function rgbToHex(rgb: string): string {
  const m = rgb.match(/\d+/g);
  if (!m) return rgb;
  return '#' + m.slice(0,3).map(n => parseInt(n).toString(16).padStart(2,'0')).join('');
}
