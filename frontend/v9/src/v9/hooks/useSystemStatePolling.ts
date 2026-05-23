'use client';
import { useEffect } from 'react';
import { useSystemStateStore } from '../store/systemStateStore';

export function useSystemStatePolling(intervalMs = 5000) {
  const fetchAllStates = useSystemStateStore((s) => s.fetchAllStates);

  useEffect(() => {
    fetchAllStates();
    const id = setInterval(fetchAllStates, intervalMs);
    return () => clearInterval(id);
  }, [fetchAllStates, intervalMs]);
}
