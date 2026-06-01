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
        <td style={{ padding: '6px 8px', fontSize: 11 }}>
          <div style={{ color: COLORS.textSecondary }}>{pattern.reason}</div>
          {/* Quick summary: show live values of key components inline */}
          {pattern.components && pattern.components.length > 0 && (
            <div style={{ marginTop: 3, display: 'flex', flexWrap: 'wrap', gap: '3px 8px' }}>
              {pattern.components
                .filter((c: any) => c.stage === 'detection' || !c.present)
                .slice(0, 4)
                .map((c: any, i: number) => (
                  <span
                    key={i}
                    style={{
                      fontSize: 9,
                      fontFamily: 'ui-monospace, monospace',
                      padding: '1px 4px',
                      borderRadius: 2,
                      background: c.present ? 'rgba(86,211,100,0.1)' : 'rgba(248,81,73,0.1)',
                      color: c.present ? COLORS.bull : COLORS.bearLight,
                    }}
                  >
                    {c.present ? '✓' : '✕'} {c.key}: {(c.live || c.value || '').toString().slice(0, 40)}
                  </span>
                ))}
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
