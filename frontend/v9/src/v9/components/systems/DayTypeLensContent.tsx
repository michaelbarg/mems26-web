'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DayTypeCurrent {
  day_type: string;
  status: string;
  confidence: number;
  ib_width: string;
  opening_type: string;
  stage: string;
}

interface LensContentProps {
  activeTab: string;
}

export function DayTypeLensContent({ activeTab }: LensContentProps) {
  const [current, setCurrent] = useState<DayTypeCurrent | null>(null);
  const color = systemColor(1);

  useEffect(() => {
    fetch(`${API_BASE}/api/v9/day_type/current`)
      .then((r) => r.json())
      .then(setCurrent)
      .catch(() => {});
  }, [activeTab]);

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color }}>
            {current?.day_type?.replace('_', ' ') ?? 'Loading...'}
          </span>
          <span style={{ fontSize: 9, color: COLORS.textTertiary }}>
            {current?.status ?? ''}
          </span>
        </div>
        {current && (
          <>
            <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
              Confidence: {(current.confidence * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
              IB: {current.ib_width} | Opening: {current.opening_type} | Stage: {current.stage}
            </div>
          </>
        )}
      </div>
    );
  }

  if (activeTab === 'Plan') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
        Locks at 10:30 ET based on IB Width + Opening Type
      </div>
    );
  }

  if (activeTab === 'Hist') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
        Last 30 days — will populate from /api/v9/day_type/history
      </div>
    );
  }

  // Shadow, Chart — placeholders
  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
