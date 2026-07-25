'use client';
/**
 * OpeningTypeChip → full "פתיחה" rubric (Michael 07-24 binding spec + 07-25
 * "לסדר בפרונט את סוג הפתיחה, הזיהוי, סוג התבנית והערכת הירי").
 *
 * WHITE-framed section, same structure as the System-2 rubric, placed ABOVE it
 * in the Switcher. Shows: opening type + direction + confidence (identification),
 * the identification detail (location/stance/reason), the FIRE assessment
 * (opening-trigger window state, fired triggers, latest decision), and the
 * relevant playbook patterns for the effective day-type.
 *
 * Single source: /api/v9/day_type/opening_panel (display-only, Task-A wiring).
 * Falls back to /api/v9/open_type/current if the panel endpoint fails.
 * Polling 15000ms — P30 floor, DO NOT lower.
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

interface PanelData {
  opening?: { type: string | null; location: string | null; direction: string | null; stance: string | null };
  opening_triggers?: {
    mode?: string; window_bars_seen?: number; window_active?: boolean; window_done?: boolean;
    disabled_today?: boolean; fired?: any[]; decisions?: any[]; catalog?: string[];
  };
  provisional?: { day_type?: string | null; reason?: string | null } | null;
  live?: { day_type?: string | null; status?: string | null; direction?: string | null; reason?: string | null };
  effective_day_type?: string | null;
  patterns?: { pattern?: string; verdict?: string; name?: string; cell?: string }[] | any[];
  fired_today?: any[];
  confidence?: number | null;
}

const DIR_COLORS: Record<string, string> = {
  UP: '#16a34a',
  DOWN: '#dc2626',
  NEUTRAL: '#a1a1aa',
};

const POLL_MS = 15000; // P30 floor — do not lower

export function OpeningTypeChip() {
  const [panel, setPanel] = useState<PanelData | null>(null);
  const [fallback, setFallback] = useState<any | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch('/api/v9/day_type/opening_panel');
        if (r.ok) {
          const d = await r.json();
          if (alive) { setPanel(d); return; }
        }
      } catch { /* fall through */ }
      try {
        const r2 = await fetch('/api/v9/open_type/current');
        if (r2.ok) { const d2 = await r2.json(); if (alive) setFallback(d2); }
      } catch { /* fail-silent */ }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const type = panel?.opening?.type ?? fallback?.opening_type ?? null;
  const dir = panel?.opening?.direction ?? panel?.live?.direction ?? fallback?.direction ?? null;
  const conf = (panel as any)?.confidence ?? fallback?.confidence ?? null;
  const loc = panel?.opening?.location ?? null;
  const stance = panel?.opening?.stance ?? null;
  const reason = panel?.provisional?.reason ?? panel?.live?.reason ?? null;
  const trig = panel?.opening_triggers;
  const patterns = Array.isArray(panel?.patterns) ? panel!.patterns! : [];

  const isPending = !type;
  const dirColor = dir ? (DIR_COLORS[String(dir).toUpperCase()] ?? COLORS.textTertiary) : COLORS.textTertiary;
  const typeLabel = type ? String(type).replace(/^OPEN_/, '').replace(/_/g, ' ') : 'PENDING';

  // ── fire assessment line ──
  let fireLabel = '—';
  let fireColor: string = COLORS.textTertiary;
  if (trig?.disabled_today) {
    fireLabel = 'ירי-פתיחה: כבוי היום (אין OR כן)';
  } else if (trig?.fired && trig.fired.length > 0) {
    const f = trig.fired[trig.fired.length - 1];
    const fName = typeof f === 'string' ? f : (f?.type ?? f?.trigger ?? 'FIRED');
    fireLabel = `ירי: ${fName}${trig.fired.length > 1 ? ` (+${trig.fired.length - 1})` : ''}`;
    fireColor = '#eab308';
  } else if (trig?.window_done) {
    fireLabel = 'חלון-פתיחה נסגר · ללא ירי';
  } else if (trig?.window_active) {
    fireLabel = `חלון פעיל · ${trig.window_bars_seen ?? 0} ברים · ממתין לטריגר`;
    fireColor = '#67e8f9';
  } else {
    fireLabel = 'ירי-פתיחה: ממתין לחלון (16:30)';
  }

  // ── relevant patterns (playbook cells for effective day-type) ──
  const patLabels = patterns.slice(0, 3).map((p: any) => {
    const nm = p?.pattern ?? p?.name ?? String(p);
    const v = p?.verdict ?? p?.cell ?? '';
    return v ? `${nm}:${v}` : nm;
  });

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column', gap: 3,
        padding: '4px 6px', borderRadius: 4,
        border: '1px solid #e4e4e7', // WHITE frame per Michael's binding spec
        background: 'transparent',
      }}
    >
      {/* title — white, like a system rubric */}
      <div style={{ fontSize: 7, color: '#e4e4e7', letterSpacing: '0.5px', textTransform: 'uppercase', fontWeight: 700 }}>
        פתיחה — זיהוי + ירי
      </div>

      {/* row 1: type + direction + confidence (identification headline) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 8, fontFamily: 'ui-monospace' }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: isPending ? '#525252' : dirColor, flexShrink: 0 }} />
        <span style={{ fontWeight: 700, color: isPending ? COLORS.textTertiary : dirColor }}>
          {typeLabel}{dir ? ` ${dir}` : ''}
        </span>
        {conf != null && (
          <span style={{ color: COLORS.textTertiary, fontSize: 7 }}>{(Number(conf) * 100).toFixed(0)}%</span>
        )}
        {loc && (
          <span style={{ color: COLORS.textTertiary, fontSize: 7 }} title="מיקום-הפתיחה מול ערך-אתמול">{loc}</span>
        )}
      </div>

      {/* row 2: identification detail (stance / reason) */}
      {(stance || reason) && (
        <div style={{ fontSize: 7, color: COLORS.textDim, lineHeight: 1.3 }}
          title={reason ?? undefined}>
          {stance ? `stance: ${stance}` : ''}{stance && reason ? ' · ' : ''}
          {reason ? String(reason).slice(0, 60) : ''}
        </div>
      )}

      {/* row 3: fire assessment */}
      <div style={{ fontSize: 7.5, fontFamily: 'ui-monospace', color: fireColor }}
        title={trig?.catalog?.length ? `טריגרים אפשריים: ${trig.catalog.join(', ')}` : undefined}>
        {fireLabel}
      </div>

      {/* row 4: relevant patterns for the effective day-type (playbook) */}
      {patLabels.length > 0 && (
        <div style={{ fontSize: 7, color: COLORS.textTertiary, fontFamily: 'ui-monospace' }}
          title="תבניות רלוונטיות מה-playbook לסוג-היום האפקטיבי">
          תבניות: {patLabels.join(' · ')}
        </div>
      )}
    </div>
  );
}
