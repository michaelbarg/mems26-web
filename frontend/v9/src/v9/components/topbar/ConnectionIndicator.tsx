'use client';
import { useEffect, useState } from 'react';
import { usePriceStore, getConnectionStatus, type ConnectionStatus } from '../../stores/priceStore';

const STATUS_CONFIG: Record<ConnectionStatus, { dot: string; label: string; color: string }> = {
  live:         { dot: '\uD83D\uDFE2', label: 'LIVE',         color: '#56d364' },
  stale:        { dot: '\uD83D\uDFE1', label: 'STALE',        color: '#d29922' },
  disconnected: { dot: '\uD83D\uDD34', label: 'DISCONNECTED', color: '#f85149' },
};

export function ConnectionIndicator() {
  const connected = usePriceStore((s) => s.connected);
  const lastUpdateMs = usePriceStore((s) => s.lastUpdateMs);

  // Re-evaluate status every second
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  useEffect(() => {
    const update = () => setStatus(getConnectionStatus(connected, lastUpdateMs));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [connected, lastUpdateMs]);

  const cfg = STATUS_CONFIG[status];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 10,
        fontWeight: 600,
        color: cfg.color,
      }}
    >
      <span style={{ fontSize: 8 }}>{cfg.dot}</span>
      <span>{cfg.label}</span>
    </div>
  );
}
