/** Format MES price with comma separator: 7435.25 → "7,435.25" */
export function formatMESPrice(price: number | null | undefined): string {
  if (price == null || isNaN(price)) return '—.—';
  const [whole, frac] = price.toFixed(2).split('.');
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${withCommas}.${frac}`;
}

/** Format bid/ask spread: "0.25" */
export function formatSpread(bid: number | undefined | null, ask: number | undefined | null): string {
  if (bid == null || ask == null) return '—';
  return (ask - bid).toFixed(2);
}

/** Relative time from timestamp: "0.2s ago", "5s ago", "2m ago" */
export function relativeTime(tsMs: number | undefined | null): string {
  if (tsMs == null) return '—';
  const ageSec = (Date.now() - tsMs) / 1000;
  if (ageSec < 0) return 'now';
  if (ageSec < 1) return `${ageSec.toFixed(1)}s ago`;
  if (ageSec < 60) return `${Math.floor(ageSec)}s ago`;
  if (ageSec < 3600) return `${Math.floor(ageSec / 60)}m ago`;
  return `${Math.floor(ageSec / 3600)}h ago`;
}
