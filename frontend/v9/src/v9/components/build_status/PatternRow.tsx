'use client';
import { useState } from 'react';
import type { Pattern } from './types';
import { COLORS } from '../../design/tokens';
import { StatusPill } from './StatusPill';
import { ComponentTable } from './ComponentTable';

interface PatternRowProps {
  pattern: Pattern;
  initiallyExpanded?: boolean;
}

function formatFireTime(ts: string | null): string {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
}

export function PatternRow({ pattern, initiallyExpanded = false }: PatternRowProps) {
  const [expanded, setExpanded] = useState(initiallyExpanded);
  const hasBlockers = pattern.blockers && pattern.blockers.length > 0;
  return (
    <>
      <tr
        onClick={() => setExpanded((e) => !e)}
        style={{
          cursor: 'pointer',
          background: expanded ? COLORS.bgSurface2 : 'transparent',
          borderTop: `1px solid ${COLORS.borderFaint}`,
        }}
      >
        <td style={{ padding: '6px 8px', width: 18, color: COLORS.textTertiary }}>
          {expanded ? '▼' : '▶'}
        </td>
        <td
          style={{
            padding: '6px 8px',
            color: COLORS.textPrimary,
            fontFamily: 'ui-monospace, monospace',
            fontSize: 11,
            fontWeight: 600,
            width: 200,
          }}
        >
          {pattern.name}
          <div style={{ color: COLORS.textTertiary, fontSize: 9, fontWeight: 400 }}>{pattern.id}</div>
        </td>
        <td style={{ padding: '6px 8px', width: 110 }}>
          <StatusPill status={pattern.status} label={pattern.label} />
        </td>
        <td style={{ padding: '6px 8px', color: COLORS.textSecondary, fontSize: 11 }}>
          {pattern.reason}
          {hasBlockers && (
            <div style={{ marginTop: 2, fontSize: 9, color: COLORS.bearLight, fontFamily: 'ui-monospace, monospace' }}>
              blockers: {pattern.blockers.join(' · ')}
            </div>
          )}
        </td>
        <td
          style={{
            padding: '6px 8px',
            width: 70,
            color: pattern.fired_today ? COLORS.bull : COLORS.textTertiary,
            fontFamily: 'ui-monospace, monospace',
            fontSize: 11,
            textAlign: 'right',
          }}
        >
          {formatFireTime(pattern.last_fire_ts)}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5} style={{ padding: 0 }}>
            <ComponentTable components={pattern.components} />
          </td>
        </tr>
      )}
    </>
  );
}
