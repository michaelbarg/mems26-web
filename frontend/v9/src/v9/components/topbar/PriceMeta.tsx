'use client';
import { useEffect, useState } from 'react';
import { usePriceStore } from '../../stores/priceStore';
import { formatSpread, relativeTime } from '../../lib/formatPrice';

export function PriceMeta() {
  const bid = usePriceStore((s) => s.bid);
  const ask = usePriceStore((s) => s.ask);
  const lastSize = usePriceStore((s) => s.lastSize);
  const lastUpdateMs = usePriceStore((s) => s.lastUpdateMs);

  // Re-render every 500ms to keep relative time fresh
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 500);
    return () => clearInterval(id);
  }, []);

  const meta = `${relativeTime(lastUpdateMs)}`;
  const spread = formatSpread(bid, ask);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 10,
        color: 'var(--text-secondary, #8b949e)',
        fontFamily: 'monospace',
      }}
    >
      <span>B:{bid?.toFixed(2) ?? '—'}</span>
      <span>A:{ask?.toFixed(2) ?? '—'}</span>
      <span>S:{spread}</span>
      {lastSize != null && <span>Sz:{lastSize}</span>}
      <span style={{ color: 'var(--text-muted, #484f58)' }}>{meta}</span>
    </div>
  );
}
