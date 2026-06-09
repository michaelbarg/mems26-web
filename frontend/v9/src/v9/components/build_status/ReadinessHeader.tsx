'use client';
import Link from 'next/link';
import { COLORS } from '../../design/tokens';
import type { Readiness, ReadinessCheck } from './types';

/**
 * ReadinessHeader — verdict-first build readiness display.
 *
 * When BLOCKED: isolates the single gating severity:'block' check
 * and surfaces it in plain Hebrew at the top. All other checks
 * demoted to a secondary chip row.
 *
 * P4 from UX audit: "the whole point is למה לא נכנס / כן נכנס"
 */

const VERDICT_STYLES: Record<string, { fg: string; bg: string; border: string }> = {
  READY: { fg: COLORS.bull, bg: '#0e3a1f', border: `${COLORS.bull}40` },
  DEGRADED: { fg: COLORS.warning, bg: '#3a280a', border: `${COLORS.warning}40` },
  BLOCKED: { fg: COLORS.bear, bg: '#3a1a1a', border: `${COLORS.bear}40` },
};

/** Best-effort Hebrew translation for common blocker keys. */
function blockerHebrew(check: ReadinessCheck): string {
  const key = check.key.toLowerCase();
  const detail = check.detail ?? '';

  if (key.includes('snapshot') || detail.includes('snapshot'))
    return `אין snapshot עדכני — ${detail || 'לא נמצא בחלון הכניסה'}`;
  if (key.includes('freshness') || key.includes('stale'))
    return `מידע לא עדכני — ${detail || 'הנתונים ישנים מדי'}`;
  if (key.includes('session') || key.includes('rth'))
    return `מחוץ לשעות מסחר — ${detail || 'RTH לא פעיל'}`;
  if (key.includes('hydrat'))
    return `המערכת לא טעונה — ${detail || 'חסר hydration'}`;
  if (key.includes('gate') || key.includes('global'))
    return `gate חסום — ${detail || check.key}`;
  if (key.includes('bridge') || key.includes('connect'))
    return `אין חיבור לגשר — ${detail || 'bridge לא מחובר'}`;

  // Fallback: show the key + detail as-is
  return detail || check.key;
}

export function ReadinessHeader({ readiness }: { readiness: Readiness | undefined }) {
  if (!readiness) {
    return (
      <div
        style={{
          padding: '6px 12px',
          marginBottom: 12,
          borderRadius: 6,
          background: COLORS.bgSurface1,
          border: `1px solid ${COLORS.borderFaint}`,
          fontSize: 10,
          color: COLORS.textTertiary,
          fontFamily: 'ui-monospace, monospace',
        }}
      >
        readiness: n/a
      </div>
    );
  }

  const vs = VERDICT_STYLES[readiness.verdict] || VERDICT_STYLES.BLOCKED;
  const checks = readiness.checks ?? [];
  const blockers = checks.filter((c) => !c.passed && c.severity === 'block');
  const degraded = checks.filter((c) => !c.passed && c.severity === 'degrade');
  const passing = checks.filter((c) => c.passed);
  const infos = checks.filter((c) => !c.passed && c.severity === 'info');

  // The single gating blocker (or first if multiple)
  const primaryBlocker = blockers.length > 0 ? blockers[0] : null;

  return (
    <div
      style={{
        padding: '10px 14px',
        marginBottom: 12,
        borderRadius: 6,
        background: vs.bg,
        border: `1px solid ${vs.border}`,
        fontFamily: 'ui-monospace, monospace',
      }}
    >
      {/* Verdict pill — always first */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: primaryBlocker || readiness.reason ? 6 : 0 }}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '3px 10px',
            borderRadius: 4,
            background: `${vs.fg}18`,
            border: `1px solid ${vs.fg}50`,
            color: vs.fg,
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: '0.5px',
          }}
        >
          ● {readiness.verdict}
        </span>
        {readiness.reason && (
          <span style={{ color: COLORS.textSecondary, fontSize: 11 }}>
            {readiness.reason}
          </span>
        )}
      </div>

      {/* Primary blocker — called out in Hebrew, prominent */}
      {primaryBlocker && (
        <div
          style={{
            padding: '6px 10px',
            marginBottom: 8,
            borderRadius: 4,
            background: '#4a1a1a',
            border: `1px solid ${COLORS.bear}50`,
            color: COLORS.bearLight,
            fontSize: 12,
            fontWeight: 600,
            direction: 'rtl',
          }}
        >
          {blockerHebrew(primaryBlocker)}
        </div>
      )}

      {/* Additional blockers (rare — usually just one) */}
      {blockers.length > 1 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginBottom: 6 }}>
          {blockers.slice(1).map((c) => (
            <div
              key={c.key}
              style={{
                padding: '3px 8px',
                borderRadius: 3,
                background: '#3a1a1a',
                color: COLORS.bearLight,
                fontSize: 10,
                direction: 'rtl',
              }}
            >
              {blockerHebrew(c)}
            </div>
          ))}
        </div>
      )}

      {/* Degraded warnings */}
      {degraded.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 8px', marginBottom: 6 }}>
          {degraded.map((c) => (
            <span
              key={c.key}
              title={c.detail ?? undefined}
              style={{ fontSize: 9, color: COLORS.warning }}
            >
              ⚠ {c.key}{c.detail ? `: ${c.detail}` : ''}
            </span>
          ))}
        </div>
      )}

      {/* Passing + info checks — demoted chip row */}
      {(passing.length > 0 || infos.length > 0) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 10px', marginBottom: 6 }}>
          {passing.map((c) => (
            <span key={c.key} title={c.detail ?? undefined} style={{ fontSize: 9, color: COLORS.textTertiary }}>
              ✓ {c.key}
            </span>
          ))}
          {infos.map((c) => (
            <span key={c.key} title={c.detail ?? undefined} style={{ fontSize: 9, color: COLORS.textTertiary }}>
              i {c.key}
            </span>
          ))}
        </div>
      )}

      {/* P5: Build → Journal deep-link */}
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <Link
          href="/trades"
          style={{
            fontSize: 10,
            padding: '2px 8px',
            borderRadius: 3,
            background: 'rgba(59,130,246,0.12)',
            color: '#3b82f6',
            border: '1px solid rgba(59,130,246,0.25)',
            fontFamily: 'ui-monospace, monospace',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          ← ראה עסקאות
        </Link>
      </div>
    </div>
  );
}
