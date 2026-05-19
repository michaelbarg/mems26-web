'use client';

import { useEffect } from 'react';
import { usePriceStore } from '../stores/priceStore';
import type { PriceTickEvent } from '../types/events';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Fallback when WS price stream is down: poll Sierra live_price.json via backend.
 * Keeps priceStore fresh so chart + ConnectionIndicator show LIVE/STALE not DISCONNECTED.
 */
export function useLivePricePoll(enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    let inFlight = false;
    const poll = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`${API}/api/v9/live_price`);
        const d = await res.json();
        const price = d.price ?? d.last;
        if (price == null) return;
        usePriceStore.getState().onTick({
          event_type: 'price.tick',
          correlation_id: 'live_price_poll',
          source: 'sierra_live_price',
          version: '1',
          price: Number(price),
          ts_ms: Date.now(),
          bid: d.bid ?? undefined,
          ask: d.ask ?? undefined,
        } as PriceTickEvent);
        usePriceStore.getState().setConnected(true);
      } catch {
        /* backend down */
      } finally {
        inFlight = false;
      }
    };
    poll();
    const id = setInterval(poll, 1000);
    return () => clearInterval(id);
  }, [enabled]);
}
