'use client';
import { useEffect, useRef } from 'react';
import { wsManager } from '../lib/websocket';

export function useWebSocket(channel: string, callback: (data: any) => void) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    const unsub = wsManager.subscribe(channel, (data) => {
      callbackRef.current(data);
    });
    return unsub;
  }, [channel]);
}
