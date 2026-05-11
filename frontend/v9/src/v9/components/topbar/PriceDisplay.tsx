'use client';
import { useEffect, useRef, useState } from 'react';
import { usePriceStore, type PriceDirection } from '../../stores/priceStore';
import { formatMESPrice } from '../../lib/formatPrice';

const DIR_ARROW: Record<PriceDirection, string> = {
  up: '\u25B2',
  down: '\u25BC',
  unchanged: '',
};

const DIR_COLOR: Record<PriceDirection, string> = {
  up: 'var(--green, #56d364)',
  down: 'var(--red, #f85149)',
  unchanged: 'var(--text-primary, #e6edf3)',
};

export function PriceDisplay() {
  const price = usePriceStore((s) => s.price);
  const direction = usePriceStore((s) => s.direction);
  const connected = usePriceStore((s) => s.connected);
  const lastUpdateMs = usePriceStore((s) => s.lastUpdateMs);

  const [flash, setFlash] = useState(false);
  const prevPriceRef = useRef(price);

  // Flash on price change
  useEffect(() => {
    if (price !== prevPriceRef.current && price != null) {
      prevPriceRef.current = price;
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 120);
      return () => clearTimeout(t);
    }
  }, [price]);

  // Stale detection
  const isStale = connected && lastUpdateMs != null && (Date.now() - lastUpdateMs) > 10000;
  const opacity = price == null ? 0.4 : isStale ? 0.5 : 1;

  return (
    <div
      id="topbar-price"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 4,
        background: flash
          ? direction === 'up'
            ? 'rgba(86, 211, 100, 0.15)'
            : direction === 'down'
              ? 'rgba(248, 81, 73, 0.15)'
              : 'transparent'
          : 'transparent',
        transition: 'background 100ms ease-out',
        opacity,
      }}
    >
      {direction !== 'unchanged' && (
        <span
          style={{
            color: DIR_COLOR[direction],
            fontSize: 10,
            lineHeight: 1,
          }}
        >
          {DIR_ARROW[direction]}
        </span>
      )}
      <span
        data-testid="topbar-price-value"
        style={{
          fontFamily: 'monospace',
          fontSize: 18,
          fontWeight: 700,
          color: DIR_COLOR[direction],
          letterSpacing: '-0.5px',
        }}
      >
        {formatMESPrice(price)}
      </span>
    </div>
  );
}
