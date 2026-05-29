'use client';
import type { Component, Freshness } from './types';
import { COLORS } from '../../design/tokens';

interface ComponentTableProps {
  components: Component[];
}

const STALE_LAG_S = 60;

function FreshnessPill({ freshness }: { freshness?: Freshness | null }) {
  if (!freshness) return null;
  const lag = freshness.lag_s;
  let label: string;
  let color = COLORS.textTertiary;
  let bg: string | undefined;

  if (lag === null || lag === undefined) {
    label = 'lag ?';
    color = COLORS.warning;
    bg = '#3a280a';
  } else if (lag < STALE_LAG_S) {
    label = `fresh ${formatLag(lag)}`;
    color = COLORS.bull;
    bg = '#0e3a1f';
  } else {
    label = `stale ${formatLag(lag)}`;
    color = COLORS.bear;
    bg = '#3a1a1a';
  }

  const tooltip = `source=${freshness.source ?? '?'}${
    freshness.ts ? ` · ts=${freshness.ts}` : ''
  }`;

  return (
    <span
      title={tooltip}
      style={{
        fontSize: 9,
        marginLeft: 6,
        padding: '0 5px',
        borderRadius: 3,
        color,
        background: bg,
        fontFamily: 'ui-monospace, monospace',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

function formatLag(lag: number): string {
  if (lag < 1) return '<1s';
  if (lag < 60) return `${Math.round(lag)}s`;
  if (lag < 3600) return `${Math.round(lag / 60)}m`;
  return `${Math.round(lag / 3600)}h`;
}

export function ComponentTable({ components }: ComponentTableProps) {
  if (components.length === 0) {
    return (
      <div style={{ padding: 8, fontSize: 10, color: COLORS.textTertiary, fontStyle: 'italic' }}>
        No component data available.
      </div>
    );
  }

  return (
    <div
      style={{
        background: COLORS.bgSurface1,
        borderTop: `1px solid ${COLORS.borderFaint}`,
        padding: '6px 12px 8px 28px',
      }}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontFamily: 'ui-monospace, monospace',
          fontSize: 10,
        }}
      >
        <thead>
          <tr style={{ color: COLORS.textTertiary, textAlign: 'left' }}>
            <th style={{ padding: '4px 8px 4px 0', fontWeight: 500, width: 110 }}>Stage</th>
            <th style={{ padding: '4px 8px', fontWeight: 500, width: 170 }}>Key</th>
            <th style={{ padding: '4px 8px', fontWeight: 500 }}>Spec</th>
            <th style={{ padding: '4px 8px', fontWeight: 500, width: 180 }}>Live</th>
            <th style={{ padding: '4px 8px', fontWeight: 500, width: 140 }}>Required</th>
            <th style={{ padding: '4px 8px', fontWeight: 500, width: 60, textAlign: 'center' }}>Present</th>
            <th style={{ padding: '4px 8px', fontWeight: 500 }}>Value</th>
          </tr>
        </thead>
        <tbody>
          {components.map((c, i) => (
            <tr
              key={`${c.stage}-${c.key}-${i}`}
              style={{
                color: c.present ? COLORS.textPrimary : COLORS.bearLight,
                borderTop: i > 0 ? `1px solid ${COLORS.borderFaint}` : 'none',
              }}
            >
              <td style={{ padding: '3px 8px 3px 0', color: COLORS.textSecondary }}>{c.stage}</td>
              <td style={{ padding: '3px 8px', color: COLORS.textSecondary }}>{c.key}</td>
              <td style={{ padding: '3px 8px', color: COLORS.textTertiary }}>{c.spec}</td>
              <td style={{ padding: '3px 8px' }}>
                <span style={{ color: COLORS.textPrimary }}>{c.live ?? '—'}</span>
                <FreshnessPill freshness={c.freshness} />
              </td>
              <td style={{ padding: '3px 8px', color: COLORS.textSecondary }}>{c.required ?? '—'}</td>
              <td style={{ padding: '3px 8px', textAlign: 'center' }}>
                {c.present ? (
                  <span style={{ color: COLORS.bull }}>✓</span>
                ) : (
                  <span style={{ color: COLORS.bear }}>✕</span>
                )}
              </td>
              <td style={{ padding: '3px 8px' }}>{c.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
