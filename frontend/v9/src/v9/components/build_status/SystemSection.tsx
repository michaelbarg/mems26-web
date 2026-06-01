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

function formatLastFireET(ts: string | null | undefined): string | null {
  if (!ts) return null;
  try {
    const d = new Date(ts);
    // ET wall-clock for the trader; matches the rest of the dashboard.
    return d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/New_York',
    });
  } catch {
    return null;
  }
}

function FireSummary({ system }: { system: SystemBlock }) {
  const count = system.fired_today_count ?? 0;
  if (count <= 0) {
    return (
      <span
        style={{
          fontSize: 9,
          fontFamily: 'ui-monospace, monospace',
          color: COLORS.textTertiary,
          padding: '1px 6px',
          borderRadius: 3,
          background: COLORS.bgSurface2,
        }}
      >
        0 fires today
      </span>
    );
  }
  const lastEt = formatLastFireET(system.last_fire_ts);
  return (
    <span
      title={system.last_fire_ts ?? undefined}
      style={{
        fontSize: 9,
        fontFamily: 'ui-monospace, monospace',
        color: COLORS.bull,
        padding: '1px 6px',
        borderRadius: 3,
        background: '#0e3a1f',
      }}
    >
      ✓ {count}× fired{lastEt ? ` · last ${lastEt} ET` : ''}
    </span>
  );
}

export function SystemSection({ system, showOnlyBlockers }: SystemSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  const visiblePatterns = showOnlyBlockers
    ? system.patterns.filter((p) => p.status === 'blocked' || p.status === 'vetoed' || (p.blockers && p.blockers.length > 0))
    : system.patterns;

  // Per-pattern roll-up (distinct patterns that fired) — separate from the
  // backend-supplied fired_today_count which sums multi-pattern fires.
  const firedPatternCount = system.patterns.filter((p) => p.fired_today).length;
  const armedCount = system.patterns.filter((p) => p.status === 'armed').length;
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
        <FireSummary system={system} />
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: COLORS.textTertiary, fontFamily: 'ui-monospace, monospace' }}>
          {system.patterns.length} patterns · {firedPatternCount} fired · {armedCount} armed · {blockedCount} blocked
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

      {/* D-OBS: Live Inputs + Interpretations */}
      {!collapsed && system.live_inputs && system.live_inputs.length > 0 && (
        <div style={{ display: 'flex', gap: 12, padding: '6px 12px', borderBottom: `1px solid ${COLORS.borderFaint}`, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 9, color: COLORS.textTertiary, fontWeight: 600, marginBottom: 3, textTransform: 'uppercase' }}>Live Inputs</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 8px' }}>
              {system.live_inputs.map((inp: any, i: number) => (
                <span key={i} style={{ fontSize: 10, fontFamily: 'ui-monospace, monospace', color: COLORS.textSecondary }}>
                  <span style={{ color: COLORS.textTertiary }}>{inp.field}=</span>
                  <span style={{ color: COLORS.textPrimary }}>{inp.value ?? '—'}</span>
                </span>
              ))}
            </div>
          </div>
          {system.interpretations && system.interpretations.length > 0 && (
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 9, color: COLORS.textTertiary, fontWeight: 600, marginBottom: 3, textTransform: 'uppercase' }}>Interpretation</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 8px' }}>
                {system.interpretations.map((interp: any, i: number) => (
                  <span key={i} style={{ fontSize: 10, fontFamily: 'ui-monospace, monospace', color: COLORS.textSecondary }}>
                    <span style={{ color: COLORS.bull }}>{interp.key}:</span>{' '}
                    <span style={{ color: COLORS.textPrimary }}>{interp.value ?? '—'}</span>
                    {interp.from_input && <span style={{ color: COLORS.textTertiary, fontSize: 8 }}> ←{interp.from_input}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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
