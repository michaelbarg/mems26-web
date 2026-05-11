'use client';
import { useEffect, useRef, useCallback } from 'react';
import { useSystemStore } from '../stores/systemStore';
import { SYSTEM_META } from '../design/system_colors';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

/**
 * Subscribes to all 6 system event streams via WS.
 * Updates systemStore on each event.
 *
 * System events arrive on channels like /ws/v9/signals/{system_id}.
 * This hook manages one connection per system.
 */
export function useSystemEvents() {
  const addSignal = useSystemStore((s) => s.addSignal);
  const connectionsRef = useRef<Map<number, WebSocket>>(new Map());

  const connectSystem = useCallback((systemId: number) => {
    const url = `${WS_URL}/ws/v9/signals/${systemId}?token=${TOKEN}`;
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'heartbeat' || msg.type === 'pong') return;
        if (msg.type === 'update' && msg.data) {
          addSignal(msg.data);
        } else if (msg.type === 'snapshot' && Array.isArray(msg.data)) {
          // Initial snapshot already handled by store init
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      connectionsRef.current.delete(systemId);
      // Reconnect after 5s
      setTimeout(() => {
        if (connectionsRef.current.size < 6) {
          connectSystem(systemId);
        }
      }, 5000);
    };

    ws.onerror = () => ws.close();

    connectionsRef.current.set(systemId, ws);
  }, [addSignal]);

  useEffect(() => {
    // Connect to all 6 system signal streams
    for (const id of Object.keys(SYSTEM_META)) {
      connectSystem(Number(id));
    }

    return () => {
      for (const ws of connectionsRef.current.values()) {
        ws.onclose = null;
        ws.close();
      }
      connectionsRef.current.clear();
    };
  }, [connectSystem]);
}
