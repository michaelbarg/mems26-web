'use client';
// OpeningTypePanel — Michael 2026-07-21: "לסדר את סוג הפתיחה ולהגדיר שיהיה מסודר
// בפאנל סוג הפתיחה והתבניות הרלוונטיות".
// Reads /api/v9/day_type/opening_panel (display-only; one source with the engine):
// opening type + what it foreshadows (classifier's own Dalton mapping) + the
// playbook verdict (FULL/REDUCED/SKIP) per pattern for the effective day-type.
// Poll 15s — opening type resolves once in the first 30 min and rarely changes.
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PatternVerdict {
  pattern: string;
  group: 'CONT' | 'REV' | string | null;
  verdict: 'FULL' | 'REDUCED' | 'SKIP' | string;
  require_with_trend: boolean;
  fired?: boolean; // CC join: pattern actually triggered today (S2 setups / woodies detections)
}

interface OpeningPanelData {
  date: string;
  n_bars: number;
  opening: { type: string | null; location: string | null; direction: string | null };
  provisional: { day_type: string; reason: string } | null;
  live: { day_type: string | null; status: string | null; direction: string | null; reason?: string | null };
  effective_day_type: string | null;
  playbook_on: boolean;
  patterns: PatternVerdict[];
  // Michael 07-22: stance = the tradeable doctrine for THIS opening type
  // (backend opening_type_gate is authoritative; FE falls back to the approved static map).
  stance?: 'DIRECTIONAL' | 'REVERSAL' | 'NO_EDGE' | string | null;
  // single-source cross-check: classify_replay (audit) vs get_live_day_type (live).
  cross_check?: { match: boolean; audit_label?: string | null; live_label?: string | null } | null;
  // Michael 07-22: live state of the opening ENTRY triggers (incl. EXTREME_REJECT)
  opening_triggers?: {
    mode: string;
    window_bars_seen: number;
    window_active: boolean;
    window_done: boolean;
    disabled_today: boolean;
    fired: string[];
    decisions: { ts?: string; pattern?: string; direction?: string; entry?: number;
                 blocked_by?: string | null; outcome?: string | null }[];
    catalog: string[];
  } | null;
  error?: string;
}

// Michael 07-22: תבניות-הפתיחה — display names for the entry triggers
const TRIGGER_HE: Record<string, string> = {
  DRIVE: 'דרייב (OR-צר)',
  TEST_DRIVE: 'בדיקת-פתיחה',
  ORR: 'היפוך-דחייה',
  EXTREME_REJECT: 'בדיקת-קיצון (הכלל של מייקל)',
};

// Approved Dalton stance map (Michael ruling 2026-07-22) — display fallback only;
// when the backend sends `stance` (from opening_type_gate) it wins.
const STANCE_FALLBACK: Record<string, string> = {
  OPEN_DRIVE: 'DIRECTIONAL',
  OPEN_TEST_DRIVE: 'DIRECTIONAL',
  OPEN_REJECTION_REVERSE: 'REVERSAL',
  OPEN_AUCTION_IN: 'NO_EDGE',
  OPEN_AUCTION_OUT: 'NO_EDGE',
};

const STANCE_VIEW: Record<string, { text: string; bg: string; fg: string; title: string }> = {
  DIRECTIONAL: {
    text: '🎯 ודאות-כיוונית', bg: 'rgba(46,160,67,0.15)', fg: '#3fb950',
    title: 'Drive/Test-Drive: מסחר רק עם כיוון-הדרייב; היפוך-בפתיחה מאושר = כניסה מוקדמת (דלטון, פסיקת 07-22)',
  },
  REVERSAL: {
    text: '🔄 עסקת-היפוך', bg: 'rgba(210,153,34,0.18)', fg: '#d29922',
    title: 'Rejection-Reverse: הפתיחה נדחתה — העסקה הסחירה היא ההיפוך (דלטון, פסיקת 07-22)',
  },
  NO_EDGE: {
    text: '⏸ אין-יתרון · המתן', bg: 'rgba(139,148,158,0.12)', fg: '#8b949e',
    title: 'Open-Auction: אין יתרון כיווני בפתיחה — המתן לסיווג-יום/מיקום (דלטון, פסיקת 07-22)',
  },
};

const OPENING_LABELS: Record<string, string> = {
  OPEN_DRIVE: 'Drive',
  OPEN_TEST_DRIVE: 'Test-Drive',
  OPEN_REJECTION_REVERSE: 'Rejection-Reverse',
  OPEN_AUCTION_IN: 'Auction (in range)',
  OPEN_AUCTION_OUT: 'Auction (out of range)',
  UNKNOWN: '—',
};

const OPENING_COLORS: Record<string, string> = {
  OPEN_DRIVE: '#2ea043',
  OPEN_TEST_DRIVE: '#3fb950',
  OPEN_REJECTION_REVERSE: '#d29922',
  OPEN_AUCTION_IN: '#8b949e',
  OPEN_AUCTION_OUT: '#58a6ff',
};

const VERDICT_STYLE: Record<string, { bg: string; fg: string }> = {
  FULL: { bg: 'rgba(46,160,67,0.15)', fg: '#3fb950' },
  REDUCED: { bg: 'rgba(210,153,34,0.15)', fg: '#d29922' },
  SKIP: { bg: 'rgba(248,81,73,0.12)', fg: '#f85149' },
};

function Pill({ text, bg, fg, title }: { text: string; bg: string; fg: string; title?: string }) {
  return (
    <span title={title} style={{
      fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 3,
      background: bg, color: fg, whiteSpace: 'nowrap',
    }}>
      {text}
    </span>
  );
}

export function OpeningTypePanel() {
  const [data, setData] = useState<OpeningPanelData | null>(null);

  useEffect(() => {
    let cancel = false;
    const fetchPanel = () => {
      fetch(`${API}/api/v9/day_type/opening_panel`)
        .then((r) => r.json())
        .then((d) => { if (!cancel) setData(d); })
        .catch(() => { /* keep last data; panel is display-only */ });
    };
    fetchPanel();
    // 15s poll — same tier as StreamHealthPanel/Layer0Strip (P30 floors table).
    const iv = setInterval(fetchPanel, 15_000);
    return () => { cancel = true; clearInterval(iv); };
  }, []);

  const ot = data?.opening?.type ?? null;
  const otColor = (ot && OPENING_COLORS[ot]) || COLORS.textTertiary;
  const preOpen = !data || data.n_bars === 0;

  // Sort: FULL first, then REDUCED, then SKIP — the tradeable patterns lead.
  const order: Record<string, number> = { FULL: 0, REDUCED: 1, SKIP: 2 };
  const patterns = [...(data?.patterns ?? [])].sort(
    (a, b) => (order[a.verdict] ?? 3) - (order[b.verdict] ?? 3) || a.pattern.localeCompare(b.pattern),
  );

  return (
    <div
      id="opening-type-panel"
      style={{
        background: COLORS.bgSurface1,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
        padding: '3px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexWrap: 'wrap',
        minHeight: 22,
      }}
    >
      <span style={{
        fontSize: 8, color: COLORS.textTertiary, fontWeight: 600,
        letterSpacing: '0.04em', textTransform: 'uppercase',
      }}>
        Opening
      </span>

      {preOpen ? (
        <Pill text="pre-open" bg="rgba(139,148,158,0.1)" fg={COLORS.textDisabled} />
      ) : (
        <>
          <Pill
            text={ot ? (OPENING_LABELS[ot] ?? ot.replace(/^OPEN_/, '').replace(/_/g, ' ')) : '—'}
            bg={`${otColor}22`}
            fg={otColor}
            title={data?.opening?.location ? `open location: ${data.opening.location}` : undefined}
          />
          {data?.opening?.direction && data.opening.direction !== 'NEUTRAL' && (
            <Pill
              text={data.opening.direction}
              bg={data.opening.direction === 'UP' ? 'rgba(46,160,67,0.12)' : 'rgba(248,81,73,0.1)'}
              fg={data.opening.direction === 'UP' ? '#3fb950' : '#f85149'}
            />
          )}

          {/* Michael 07-22: the tradeable stance for THIS opening type — reversal / directional / wait.
              Pre-open (no opening type yet): show the separation explicitly so the trader sees
              what WILL populate here at 16:30 (Michael 07-22: "הפרדה לתצוגה לצורך פתיחה"). */}
          {(() => {
            const stance = data?.stance ?? (ot ? STANCE_FALLBACK[ot] : null);
            const sv = stance ? STANCE_VIEW[stance] : null;
            if (sv) return <Pill text={sv.text} bg={sv.bg} fg={sv.fg} title={sv.title} />;
            return (
              <Pill
                text="🕐 ממתין-לפתיחה → סוג-פתיחה · עמדה (🎯/🔄/⏸) · תווית-חיה"
                bg="rgba(88,166,255,0.10)"
                fg="#58a6ff"
                title="ב-16:30 (6 ברים ראשונים) יופיעו כאן בהפרדה: סוג-הפתיחה (Drive/Test/Rejection/Auction) → העמדה הסחירה (כיוונית 🎯 / היפוך 🔄 / המתן ⏸) → התווית-החיה. עד אז — אין המצאת-תווית (חוק-1)."
              />
            );
          })()}

          {/* What the open foreshadows (classifier's own Dalton pp.63-74 mapping) */}
          {data?.provisional?.day_type && (
            <span style={{ fontSize: 9, color: COLORS.textTertiary }} title={data.provisional.reason}>
              → צופה <b style={{ color: '#bc8cff' }}>{data.provisional.day_type.replace(/_/g, ' ')}</b>
            </span>
          )}

          {/* Live label when committed — honest "—" when None (Rule 1: no Normal fallback) */}
          {data?.live?.day_type && data.live.day_type !== 'FORMING' ? (
            <Pill
              text={`חי: ${data.live.day_type.replace(/_/g, ' ')}`}
              bg="rgba(167,139,250,0.12)"
              fg="#a78bfa"
              title={data.live.reason ?? undefined}
            />
          ) : (
            <Pill text="חי: — (FORMING)" bg="rgba(139,148,158,0.08)" fg={COLORS.textDisabled}
              title="אין סוג-יום חי עדיין — התווית תופיע כשהמנוע יקבע (אין fallback ל-Normal)" />
          )}

          {/* Single-source cross-check: audit (classify_replay) vs live (get_live_day_type) */}
          {data?.cross_check && data.cross_check.match === false && (
            <Pill
              text="⚠ audit≠live"
              bg="rgba(248,81,73,0.12)"
              fg="#f85149"
              title={`classify_replay=${data.cross_check.audit_label ?? '—'} · live=${data.cross_check.live_label ?? '—'} — התצוגה נשארת live; ה-audit ל-log בלבד`}
            />
          )}

          <span style={{ color: COLORS.borderStrong, fontSize: 9 }}>│</span>

          {/* Relevant patterns for the effective day-type (playbook cells) */}
          {data?.effective_day_type ? (
            <>
              <span style={{ fontSize: 8, color: COLORS.textTertiary, fontWeight: 600 }}>
                תבניות ({data.effective_day_type.replace(/_/g, ' ')}
                {!data.playbook_on && ' · playbook OFF — תצוגה בלבד'}):
              </span>
              {patterns.map((p) => {
                const st = VERDICT_STYLE[p.verdict] ?? { bg: 'rgba(139,148,158,0.1)', fg: COLORS.textTertiary };
                return (
                  <Pill
                    key={p.pattern}
                    text={`${p.fired ? '● ' : ''}${p.pattern}${p.require_with_trend ? '·wt' : ''}`}
                    bg={st.bg}
                    fg={p.fired ? '#e3b341' : st.fg}
                    title={`${p.verdict}${p.group ? ` · ${p.group}` : ''}${p.require_with_trend ? ' · רק עם המגמה' : ''}${p.fired ? ' · ● ירתה היום' : ''}`}
                  />
                );
              })}
            </>
          ) : (
            <span style={{ fontSize: 9, color: COLORS.textDisabled }}>אין סוג-יום עדיין — תבניות לפי playbook יוצגו משנקבע</span>
          )}

          {/* Michael 07-22: תבניות-הפתיחה — the opening ENTRY triggers, live status */}
          {data?.opening_triggers && (
            <>
              <span style={{ color: COLORS.borderStrong, fontSize: 9 }}>│</span>
              <span style={{ fontSize: 8, color: COLORS.textTertiary, fontWeight: 600 }}>
                תבניות-פתיחה{data.opening_triggers.mode === 'shadow' ? ' (צל)' : ''}
                {data.opening_triggers.window_active
                  ? ` · בר ${data.opening_triggers.window_bars_seen}/6`
                  : data.opening_triggers.window_done ? ' · חלון-נסגר' : ' · ממתין-לפתיחה'}:
              </span>
              {data.opening_triggers.disabled_today ? (
                <Pill text="⚠ דילוג-היום (ריסטארט באמצע-חלון)" bg="rgba(248,81,73,0.10)" fg="#f0883e"
                  title="הבר הראשון שנראה לא היה בר-16:30 — אין OR אמין, דילוג-כן (חוק-1)" />
              ) : (
                data.opening_triggers.catalog.map((tr) => {
                  const dec = (data.opening_triggers?.decisions ?? []).find(
                    (d) => (d.pattern ?? '') === `OPENING_${tr}`);
                  const firedTr = data.opening_triggers?.fired.includes(tr) || !!dec;
                  const label = TRIGGER_HE[tr] ?? tr;
                  if (firedTr) {
                    return (
                      <Pill key={tr}
                        text={`🔫 ${label}${dec?.direction ? ` ${dec.direction}` : ''}${dec?.entry ? ` @${dec.entry}` : ''}`}
                        bg="rgba(46,160,67,0.15)" fg="#3fb950"
                        title={`ירה${data.opening_triggers?.mode === 'shadow' ? ' בצל (אפס-כסף)' : ''}${dec?.blocked_by ? ` · נחסם: ${dec.blocked_by}` : dec?.outcome ? ` · ${dec.outcome}` : ''}`} />
                    );
                  }
                  return (
                    <Pill key={tr} text={label}
                      bg="rgba(139,148,158,0.08)"
                      fg={data.opening_triggers?.window_active ? '#8b949e' : COLORS.textDisabled}
                      title={data.opening_triggers?.window_active ? 'פעיל — ממתין לתנאים' :
                        data.opening_triggers?.window_done ? 'החלון נסגר בלי טריגר' : 'יופעל ב-16:30'} />
                  );
                })
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
