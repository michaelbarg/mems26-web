'use client';
import { useState } from 'react';
import { useBuildStatus } from '../../hooks/useBuildStatus';
import { COLORS } from '../../design/tokens';
import { SystemSection } from './SystemSection';

/**
 * Build Status tab — live debug view of why patterns fire / don't fire.
 *
 * Authority: docs/reports/BUILD_STATUS_ENDPOINT_DESIGN.md §7
 * Backend: GET /api/v9/build/pattern-status (CC HO-2 deliverable)
 *
 * Per Michael's 2026-05-26 06:42 IL chat:
 *  - LIVE (debug "למה לא נכנס / כן נכנס לעסקה")
 *  - Refresh button (no auto-poll)
 *  - 3 systems only in this iteration: 5-min (S2) · Woodies · Day Type
 */
export function BuildStatusTab() {
  const { data, error, loading, lastFetchedAt, refresh } = useBuildStatus();
  const [showOnlyBlockers, setShowOnlyBlockers] = useState(true);

  const renderHeader = () => (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 14px',
        background: COLORS.bgSurface2,
        borderBottom: `1px solid ${COLORS.borderTertiary}`,
      }}
    >
      <span
        style={{
          color: COLORS.textPrimary,
          fontSize: 14,
          fontWeight: 700,
          fontFamily: 'ui-monospace, monospace',
          letterSpacing: '0.5px',
        }}
      >
        Build Status · Live Debug
      </span>
      <span style={{ flex: 1 }} />
      <label
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 10,
          color: COLORS.textSecondary,
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <input
          type="checkbox"
          checked={showOnlyBlockers}
          onChange={(e) => setShowOnlyBlockers(e.target.checked)}
          style={{ accentColor: COLORS.modeShadow }}
        />
        Show only blockers
      </label>
      <span
        style={{
          fontSize: 9,
          color: COLORS.textTertiary,
          fontFamily: 'ui-monospace, monospace',
        }}
      >
        {lastFetchedAt
          ? `last refresh ${lastFetchedAt.toLocaleTimeString()}`
          : '—'}
      </span>
      <button
        onClick={refresh}
        disabled={loading}
        style={{
          padding: '4px 12px',
          background: loading ? COLORS.bgSurface4 : COLORS.bgSurface5,
          color: loading ? COLORS.textTertiary : COLORS.textPrimary,
          border: `1px solid ${COLORS.borderTertiary}`,
          borderRadius: 4,
          fontSize: 11,
          fontFamily: 'ui-monospace, monospace',
          cursor: loading ? 'wait' : 'pointer',
          fontWeight: 600,
        }}
      >
        {loading ? '⟳ loading…' : '⟳ Refresh'}
      </button>
    </div>
  );

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: COLORS.bgBase,
        overflow: 'hidden',
      }}
    >
      {renderHeader()}

      {error && (
        <div
          style={{
            padding: '10px 14px',
            background: '#3a1a1a',
            color: COLORS.bearLight,
            fontSize: 11,
            fontFamily: 'ui-monospace, monospace',
            borderBottom: `1px solid ${COLORS.bear}`,
          }}
        >
          Failed to load · {error} · Click Refresh to retry. (If backend endpoint
          /api/v9/build/pattern-status is not yet implemented, this will fail
          until CC ships it.)
        </div>
      )}

      {!data && !error && !loading && (
        <div
          style={{
            padding: '20px',
            color: COLORS.textTertiary,
            fontSize: 11,
            fontFamily: 'ui-monospace, monospace',
            textAlign: 'center',
          }}
        >
          No data. Click Refresh.
        </div>
      )}

      {loading && !data && (
        <div
          style={{
            padding: '20px',
            color: COLORS.textTertiary,
            fontSize: 11,
            fontFamily: 'ui-monospace, monospace',
            textAlign: 'center',
          }}
        >
          Loading build status…
        </div>
      )}

      {data && (
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px 14px',
          }}
        >
          <div
            style={{
              display: 'flex',
              gap: 16,
              marginBottom: 12,
              padding: '8px 12px',
              background: COLORS.bgSurface1,
              border: `1px solid ${COLORS.borderFaint}`,
              borderRadius: 6,
              fontSize: 10,
              color: COLORS.textSecondary,
              fontFamily: 'ui-monospace, monospace',
            }}
          >
            <span>
              <span style={{ color: COLORS.textTertiary }}>ts:</span> {data.ts}
            </span>
            <span>
              <span style={{ color: COLORS.textTertiary }}>session:</span> {data.session_date}
            </span>
            <span>
              <span style={{ color: COLORS.textTertiary }}>RTH:</span>{' '}
              {data.rtb_session?.in_session ? (
                <span style={{ color: COLORS.bull }}>open · -{data.rtb_session.minutes_to_close}m</span>
              ) : (
                <span style={{ color: COLORS.textTertiary }}>
                  closed · +{data.rtb_session?.minutes_to_open ?? '—'}m to open
                </span>
              )}
            </span>
            <span style={{ flex: 1 }} />
            <span>
              <span style={{ color: COLORS.textTertiary }}>build:</span> {data.build_version}
            </span>
          </div>

          {data.errors && data.errors.length > 0 && (
            <div
              style={{
                padding: '6px 10px',
                marginBottom: 12,
                background: '#3a280a',
                color: COLORS.caution,
                border: `1px solid ${COLORS.warning}`,
                borderRadius: 4,
                fontSize: 10,
                fontFamily: 'ui-monospace, monospace',
              }}
            >
              warnings: {data.errors.join(' · ')}
            </div>
          )}

          {data.systems.map((sys) => (
            <SystemSection key={sys.id} system={sys} showOnlyBlockers={showOnlyBlockers} />
          ))}
        </div>
      )}
    </div>
  );
}
