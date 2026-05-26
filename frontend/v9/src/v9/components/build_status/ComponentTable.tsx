'use client';
import type { Component } from './types';
import { COLORS } from '../../design/tokens';

interface ComponentTableProps {
  components: Component[];
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
