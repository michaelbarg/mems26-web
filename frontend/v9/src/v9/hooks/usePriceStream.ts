'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import type { PriceTickEvent } from '../types/events';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

interface PriceStreamState {
  connected: boolean;
  lastTick: PriceTickEvent | null;
  tickCount: number;
}

/**
 * Hook that connects to /ws/v9/price and streams price.tick events.
 * Reconnects with exponential backoff on disconnect.
 * Logs each event to DevTools console.
 */
export function usePriceStream(): PriceStreamState {
  const [state, setState] = useState<PriceStreamState>({
    connected: false,
    lastTick: null,
    tickCount: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectAttempt = useRef(0);
  const tickCountRef = useRef(0);

  const connect = useCallback(() => {
    const url = `${WS_URL}/ws/v9/price?token=${TOKEN}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttempt.current = 0;
      setState((prev) => ({ ...prev, connected: true }));
      console.log('[MEMS26] Price stream connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'heartbeat') return;
        if (msg.type === 'pong') return;

        if (msg.type === 'price.tick' && msg.data) {
          const tick = msg.data as PriceTickEvent;
          tickCountRef.current += 1;

          // Log to DevTools console
          console.log(
            `📍 EVENT: price.tick {price: ${tick.price}, ts_ms: ${tick.ts_ms}, bid: ${tick.bid}, ask: ${tick.ask}}`
          );

          setState({
            connected: true,
            lastTick: tick,
            tickCount: tickCountRef.current,
          });
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setState((prev) => ({ ...prev, connected: false }));
      wsRef.current = null;

      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), 30000);
      reconnectAttempt.current += 1;
      console.log(`[MEMS26] Price stream disconnected, reconnecting in ${delay}ms...`);
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on cleanup
        wsRef.current.close();
      }
    };
  }, [connect]);

  return state;
}
