'use client';
import { useBuildStatus } from '../../../hooks/useBuildStatus';
import { COLORS } from '../../../design/tokens';

const STATUS_ICON: Record<string, string> = {
  fired: '🟢',
  armed: '🟡',
  blocked: '❌',
  vetoed: '⛔',
  not_applicable: '—',
  unknown: '?',
};

const SYSTEM_LABELS: Record<string, { name: string; color: string }> = {
  five_min: { name: 'S2 · Five-Min', color: '#06b6d4' },
  woodies: { name: 'S4 · Woodies CCI', color: '#f59e0b' },
};

export function PatternsTab() {
  const { data, loading, lastFetchedAt, refresh } = useBuildStatus();

  const systems = (data?.systems ?? []).filter(
    (s) => s.id === 'five_min' || s.id === 'woodies'
  );

  // S1 day type from the data
  const s1System = (data?.systems ?? []).find((s) => s.id === 'day_type');
  const s1Interp = s1System?.interpretations ?? [];
  const dayType = s1Interp.find((i) => i.key === 'day_type_gate')?.value ?? '—';
  const openingType = s1Interp.find((i) => i.key === 'opening_type')?.value ?? '—';

  return (
    <div style={{ fontSize: 11, fontFamily: 'ui-monospace, monospace' }}>
      {/* Header + refresh */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontWeight: 700, color: COLORS.textPrimary }}>זיהוי תבניות</span>
        <button
          onClick={refresh}
          disabled={loading}
          style={{
            fontSize: 9, padding: '2px 8px', borderRadius: 3, border: 'none',
            background: COLORS.bgSurface3, color: COLORS.textSecondary, cursor: 'pointer',
          }}
        >
          {loading ? '...' : '↻ רענן'}
        </button>
      </div>

      {/* S1 context */}
      <div style={{
        padding: '4px 6px', marginBottom: 8, borderRadius: 4,
        background: COLORS.bgSurface2, color: COLORS.textSecondary, fontSize: 10,
      }}>
        <span style={{ color: '#a78bfa' }}>S1</span>{' '}
        סוג יום: <span style={{ color: COLORS.textPrimary }}>{dayType}</span>{' · '}
        פתיחה: <span style={{ color: COLORS.textPrimary }}>{openingType}</span>
      </div>

      {/* Per-system pattern cards */}
      {systems.map((sys) => {
        const label = SYSTEM_LABELS[sys.id] ?? { name: sys.name, color: '#888' };
        const armed = sys.patterns.filter((p) => p.status === 'armed').length;
        const blocked = sys.patterns.filter((p) => p.status === 'blocked').length;
        const fired = sys.patterns.filter((p) => p.fired_today).length;

        return (
          <div
            key={sys.id}
            style={{
              marginBottom: 8, borderRadius: 4, overflow: 'hidden',
              border: `1px solid ${COLORS.borderFaint}`,
            }}
          >
            {/* System header */}
            <div style={{
              padding: '4px 6px', background: COLORS.bgSurface3,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ color: label.color, fontWeight: 700, fontSize: 11 }}>{label.name}</span>
              <span style={{ color: COLORS.textTertiary, fontSize: 9 }}>
                {fired > 0 && <span style={{ color: COLORS.bull }}>✓{fired} </span>}
                {armed > 0 && <span style={{ color: '#eab308' }}>{armed}🟡 </span>}
                {blocked > 0 && <span style={{ color: COLORS.bearLight }}>{blocked}❌</span>}
              </span>
            </div>

            {/* Interpretation line */}
            {sys.interpretations && sys.interpretations.length > 0 && (
              <div style={{ padding: '2px 6px', fontSize: 9, color: COLORS.textTertiary }}>
                {sys.interpretations.map((i, idx) => (
                  <span key={idx}>
                    {i.key}=<span style={{ color: COLORS.textSecondary }}>{i.value}</span>
                    {idx < sys.interpretations.length - 1 ? ' · ' : ''}
                  </span>
                ))}
              </div>
            )}

            {/* Pattern rows */}
            <div style={{ padding: '2px 0' }}>
              {sys.patterns.map((p) => {
                const icon = STATUS_ICON[p.status] ?? '?';
                const blocker = (p.blockers && p.blockers.length > 0)
                  ? p.blockers[0].replace('detection.', '').replace('stage_a1.', '').replace('day_type_gate.', '')
                  : null;

                return (
                  <div
                    key={p.id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 4,
                      padding: '1px 6px', fontSize: 10,
                      color: p.status === 'blocked' ? COLORS.textTertiary : COLORS.textSecondary,
                    }}
                  >
                    <span style={{ width: 14, textAlign: 'center' }}>{icon}</span>
                    <span style={{
                      flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {p.name}
                    </span>
                    {blocker && (
                      <span style={{
                        fontSize: 8, color: COLORS.textTertiary, maxWidth: 80,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {blocker}
                      </span>
                    )}
                    {p.fired_today && (
                      <span style={{ fontSize: 8, color: COLORS.bull }}>✓</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Last update */}
      {lastFetchedAt && (
        <div style={{ textAlign: 'center', fontSize: 8, color: COLORS.textTertiary, marginTop: 4 }}>
          {lastFetchedAt.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
      )}
    </div>
  );
}
