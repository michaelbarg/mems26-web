'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STATUS_ICON: Record<string, string> = {
  fired: '🟢', armed: '🟡', blocked: '❌', vetoed: '⛔',
  not_applicable: '—', unknown: '?',
};

const SYS_META: Record<string, { label: string; color: string; type: string }> = {
  day_type: { label: 'S1 · סיווג יום', color: '#a78bfa', type: 'OBSERVING' },
  five_min: { label: 'S2 · Five-Min', color: '#06b6d4', type: 'FIRING' },
  woodies:  { label: 'S4 · Woodies CCI', color: '#f59e0b', type: 'FIRING' },
};

interface PatternInfo {
  id: string; name: string; status: string; label: string;
  reason: string; fired_today: boolean; blockers: string[];
}
interface SystemInfo {
  id: string; name: string; running: boolean; mode: string;
  patterns: PatternInfo[]; interpretations: Array<{ key: string; value: string }>;
}

export function DetectionPanel() {
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [lastTs, setLastTs] = useState<string>('');

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/v9/build/pattern-status`);
        const d = await r.json();
        setSystems((d.systems ?? []).filter(
          (s: SystemInfo) => s.id in SYS_META
        ));
        setLastTs(new Date().toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' }));
      } catch {}
    };
    poll();
    const id = setInterval(poll, 15000); // 15s — within polling floor
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{
      display: 'flex', gap: 6, padding: '4px 8px',
      background: COLORS.bgSurface1, borderBottom: `1px solid ${COLORS.borderFaint}`,
      overflowX: 'auto', flexShrink: 0, alignItems: 'flex-start',
    }}>
      {systems.map((sys) => {
        const meta = SYS_META[sys.id];
        if (!meta) return null;
        const armed = sys.patterns.filter(p => p.status === 'armed').length;
        const blocked = sys.patterns.filter(p => p.status === 'blocked').length;
        const fired = sys.patterns.filter(p => p.fired_today).length;

        // S1 shows interpretations, not patterns
        const isS1 = sys.id === 'day_type';
        const interps = sys.interpretations ?? [];

        return (
          <div key={sys.id} style={{
            flex: isS1 ? '0 0 160px' : '1 1 0',
            minWidth: isS1 ? 150 : 180,
            borderRadius: 4, overflow: 'hidden',
            border: `1px solid ${COLORS.borderFaint}`,
            background: COLORS.bgSurface2,
          }}>
            {/* Header */}
            <div style={{
              padding: '3px 6px', background: COLORS.bgSurface3,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ color: meta.color, fontWeight: 700, fontSize: 10 }}>{meta.label}</span>
              <span style={{
                fontSize: 8, padding: '1px 4px', borderRadius: 2,
                background: meta.type === 'FIRING' ? '#0e3a1f' : '#1a1a3a',
                color: meta.type === 'FIRING' ? COLORS.bull : '#818cf8',
              }}>{meta.type}</span>
            </div>

            {isS1 ? (
              /* S1: show day_type + opening_type */
              <div style={{ padding: '3px 6px', fontSize: 9 }}>
                {interps.map((i, idx) => (
                  <div key={idx} style={{ color: COLORS.textSecondary }}>
                    <span style={{ color: COLORS.textTertiary }}>{i.key}: </span>
                    <span style={{ color: COLORS.textPrimary }}>{i.value}</span>
                  </div>
                ))}
                {interps.length === 0 && (
                  <div style={{ color: COLORS.textTertiary }}>loading...</div>
                )}
              </div>
            ) : (
              /* S2/S4: pattern list */
              <div style={{ padding: '2px 0', maxHeight: 140, overflowY: 'auto' }}>
                {/* Summary */}
                <div style={{ padding: '1px 6px', fontSize: 8, color: COLORS.textTertiary }}>
                  {fired > 0 && <span style={{ color: COLORS.bull }}>✓{fired} </span>}
                  <span style={{ color: '#eab308' }}>{armed} armed</span>
                  {blocked > 0 && <span> · <span style={{ color: COLORS.bearLight }}>{blocked} blocked</span></span>}
                </div>
                {sys.patterns.map((p) => {
                  const icon = STATUS_ICON[p.status] ?? '?';
                  const blocker = p.blockers?.[0]
                    ?.replace('detection.', '').replace('stage_a1.', '').replace('day_type_gate.', '')
                    ?? null;
                  return (
                    <div key={p.id} style={{
                      display: 'flex', alignItems: 'center', gap: 3,
                      padding: '0px 6px', fontSize: 9,
                      color: p.status === 'blocked' ? COLORS.textTertiary : COLORS.textSecondary,
                      fontFamily: 'ui-monospace, monospace',
                    }}>
                      <span style={{ width: 12, textAlign: 'center', fontSize: 8 }}>{icon}</span>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.name}
                      </span>
                      {blocker && (
                        <span style={{ fontSize: 7, color: COLORS.textTertiary, maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {blocker}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      <div style={{ fontSize: 7, color: COLORS.textTertiary, alignSelf: 'center', whiteSpace: 'nowrap' }}>
        {lastTs}
      </div>
    </div>
  );
}
