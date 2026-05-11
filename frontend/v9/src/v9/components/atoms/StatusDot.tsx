'use client';

export type DotState = 'healthy' | 'armed' | 'fired' | 'error' | 'paused';

interface StatusDotProps {
  state: DotState;
  size?: number;
}

const DOT_MAP: Record<DotState, { symbol: string; color: string }> = {
  healthy: { symbol: '\uD83D\uDFE2', color: '#16a34a' },
  armed:   { symbol: '\uD83D\uDFE1', color: '#facc15' },
  fired:   { symbol: '\uD83D\uDD34', color: '#dc2626' },
  error:   { symbol: '\u2717',        color: '#dc2626' },
  paused:  { symbol: '\u23F8',        color: '#737373' },
};

export function StatusDot({ state, size = 10 }: StatusDotProps) {
  const cfg = DOT_MAP[state] ?? DOT_MAP.healthy;
  return (
    <span style={{ fontSize: size, color: cfg.color, lineHeight: 1 }}>
      {cfg.symbol}
    </span>
  );
}
