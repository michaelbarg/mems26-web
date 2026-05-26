'use client';
import { useState } from 'react';
import type { SystemBlock } from './types';
import { COLORS } from '../../design/tokens';
import { PatternRow } from './PatternRow';

interface SystemSectionProps {
  system: SystemBlock;
  showOnlyBlockers: boolean;
}

function FreshnessIndicator({ system }: { system: SystemBlock }) {
  const fresh = system.data_freshness?.fresh;
  const lag = system.data_freshness?.lag_seconds;
  const lagText = lag === null || lag === undefined ? 'unknown' : `${lag}s`;
  return (
    <span
      style={{
        fontSize: 9,
        fontFamily: 'ui-monospace, monospace',
        color: fresh ? COLORS.bull : COLORS.bear,
        padding: '1px 6px',
        borderRadius: 3,
        background: fresh ? '#0e3a1f' : '#3a1a1a',
      }}
    >
      lag {lagText}
    </span>
  );
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{ fontSize: 9, color: COLORS.textSecondary, fontFamily: 'ui-monospace, monospace' }}>
      <span style={{ color: ok ? COLORS.bull : COLORS.bear, marginRight: 3 }}>●</span>
      {label}
    </span>
  );
}

export function SystemSection({ system, showOnlyBlockers }: SystemSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  const visiblePatterns = showOnlyBlockers
    ? system.patterns.filter((p) => p.status === 'blocked' || p.status === 'vetoed' || (p.blockers && p.blockers.length > 0))
    : system.patterns;

  const firedCount = system.patterns.filter((p) => p.fired_today).length;
  const blockedCount = system.patterns.filter((p) => p.status === 'blocked' || p.status === 'vetoed').length;

  return (
    <div
      style={{
        background: COLORS.bgSurface1,
        border: `1px solid ${COLORS.borderFaint}`,
        borderRadius: 6,
        marginBottom: 12,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        onClick={() => setCollapsed((c) => !c)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          background: COLORS.bgSurface3,
          cursor: 'pointer',
          borderBottom: collapsed ? 'none' : `1px solid ${COLORS.borderFaint}`,
        }}
      >
        <span style={{ color: COLORS.textTertiary }}>{collapsed ? '▶' : '▼'}</span>
        <span
          style={{
            color: COLORS.textPrimary,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: 'ui-monospace, monospace',
          }}
        >
          {system.name}
        </span>
        <StatusDot ok={system.running} label={`run ${system.running ? 'on' : 'off'}`} />
        <StatusDot ok={system.hydrated} label={`hyd ${system.hydrated ? 'ok' : 'no'}`} />
        <FreshnessIndicator system={system} />
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: COLORS.textTertiary, fontFamily: 'ui-monospace, monospace' }}>
          {system.patterns.length} patterns · {firedCount} fired · {blockedCount} blocked
          {showOnlyBlockers && visiblePatterns.length !== system.patterns.length && (
            <span style={{ color: COLORS.warning, marginLeft: 6 }}>
              (filtered to {visiblePatterns.length})
            </span>
          )}
        </span>
        <span
          style={{
            fontSize: 10,
            color: COLORS.modeShadow,
            fontFamily: 'ui-monospace, monospace',
            padding: '1px 6px',
            borderRadius: 3,
            border: `1px solid ${COLORS.borderTertiary}`,
          }}
        >
          {system.mode || '—'}
        </span>
      </div>

      {/* Patterns table */}
      {!collapsed && (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontFamily: 'system-ui, -apple-system, sans-serif',
            }}
          >
            <thead>
              <tr
                style={{
                  color: COLORS.textTertiary,
                  fontSize: 9,
                  textAlign: 'left',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  background: COLORS.bgSurface2,
                }}
              >
                <th style={{ padding: '6px 8px', width: 18 }}></th>
                <th style={{ padding: '6px 8px', width: 200, fontWeight: 500 }}>Pattern</th>
                <th style={{ padding: '6px 8px', width: 110, fontWeight: 500 }}>Status</th>
                <th style={{ padding: '6px 8px', fontWeight: 500 }}>Reason</th>
                <th style={{ padding: '6px 8px', width: 70, fontWeight: 500, textAlign: 'right' }}>Fired</th>
              </tr>
            </thead>
            <tbody>
              {visiblePatterns.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    style={{
                      padding: '12px 8px',
                      textAlign: 'center',
                      color: COLORS.textTertiary,
                      fontStyle: 'italic',
                      fontSize: 11,
                    }}
                  >
                    {showOnlyBlockers
                      ? 'No blockers · all patterns clear.'
                      : 'No patterns reported.'}
                  </td>
                </tr>
              ) : (
                visiblePatterns.map((p) => <PatternRow key={p.id} pattern={p} />)
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
