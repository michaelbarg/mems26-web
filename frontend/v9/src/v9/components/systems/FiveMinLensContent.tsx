'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FiveMinState {
  mode: string;
  buffer_size: number;
  opening_type: string | null;
  last_pattern: string | null;
  last_confluence: number;
  last_classification: string | null;
}

interface LensContentProps {
  activeTab: string;
}

export function FiveMinLensContent({ activeTab }: LensContentProps) {
  const [state, setState] = useState<FiveMinState | null>(null);
  const color = systemColor(2);

  useEffect(() => {
    fetch(`${API_BASE}/api/v9/five_min/current`)
      .then((r) => r.json())
      .then(setState)
      .catch(() => {});
  }, [activeTab]);

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color }}>
            {state?.mode?.replace('_', ' ') ?? 'Loading...'}
          </span>
          <span style={{ fontSize: 9, color: COLORS.textTertiary }}>
            buf: {state?.buffer_size ?? 0}
          </span>
        </div>
        {state && (
          <>
            <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
              Pattern: {state.last_pattern ?? 'none'} | Confl: {state.last_confluence}
            </div>
            <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
              Opening: {state.opening_type ?? '--'} | Class: {state.last_classification ?? '--'}
            </div>
          </>
        )}
      </div>
    );
  }

  if (activeTab === 'Plan') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, padding: 8 }}>
        Setup classification, targets, sizing — populates on pattern detection
      </div>
    );
  }

  if (activeTab === 'Hist') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, padding: 8 }}>
        Recent setups — from /api/v9/five_min/setups
      </div>
    );
  }

  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
