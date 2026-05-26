'use client';
import { useCallback, useEffect, useState } from 'react';
import type { BuildStatusResponse } from '../components/build_status/types';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UseBuildStatusReturn {
  data: BuildStatusResponse | null;
  error: string | null;
  loading: boolean;
  lastFetchedAt: Date | null;
  refresh: () => void;
}

/**
 * Per Michael's instruction (chat 2026-05-26 06:42 IL): "קצב עדכון כפתור רפרש"
 * — manual refresh only, no auto-poll. Initial fetch on mount, then user
 * controls re-fetches via the Refresh button in BuildStatusTab.
 */
export function useBuildStatus(): UseBuildStatusReturn {
  const [data, setData] = useState<BuildStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/api/v9/build/pattern-status`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: BuildStatusResponse) => {
        setData(d);
        setLastFetchedAt(new Date());
      })
      .catch((e: Error) => {
        setError(e.message || 'fetch failed');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, error, loading, lastFetchedAt, refresh };
}
