'use client';
// T-480 (Michael 25.09 13:40: "שאראה אותו בחי … הרכיב שבאותו הרגע המערכת נמצאת בו, ומה הוא מתכנן"):
// the decision tree's current node + its plan, from GET /api/v9/tree/state (read-only, 15s — diagnostic floor).
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const KINDS = ['WITH_DRIVE', 'REVERSAL', 'EDGE_FADE', 'PULLBACK', 'BREAK', 'VALUE_RETURN'] as const;
const KIND_HEB: Record<string, string> = {
  WITH_DRIVE: 'עם-הדרייב', REVERSAL: 'היפוך', EDGE_FADE: 'דהיית-קצה', PULLBACK: 'פולבק', BREAK: 'פריצה', VALUE_RETURN: 'חזרה-לערך',
};

interface Leaf { leaf: 'TAKE' | 'SHADOW' | 'SKIP'; id: string | null; note?: string | null; path?: string }
interface Recent { il: string; pattern: string; direction: string; entry: number | null; leaf: string; id: string | null; path: string; outcome: string; blocked_by: string | null; legacy?: string | null }
interface BrainQ { q: string; a: string }
interface Brain {
  family: { id: string; title: string; on: string; off: string };
  questions: BrainQ[];
}
interface TreeContext {
  phase: string; opening_type: string; day_type: string; hint: string | null;
  zone: string; price: number | null; structure?: string; il?: string;
}
interface TreeState {
  mode: 'off' | 'shadow' | 'on';
  where_he?: string;
  plan?: { LONG: Record<string, Leaf>; SHORT: Record<string, Leaf> };
  plan_he?: { LONG: string; SHORT: string };
  recent?: Recent[];
  context?: TreeContext;
  brain?: Brain;
  error?: string;
}

const OT_HE: Record<string, string> = {
  OPEN_DRIVE: 'דרייב', OPEN_REJECTION_REVERSE: 'דחייה-היפוך', OPEN_AUCTION_IN: 'אוקציה בטווח',
  OPEN_AUCTION_OUT: 'אוקציה מחוץ', UNKNOWN: 'טרם סווגה',
};
const ZN_HE: Record<string, string> = {
  above_value: 'מעל הערך', near_vah: 'על ה-VAH', mid_value: 'בתוך הערך', near_val: 'על ה-VAL',
  below_value: 'מתחת לערך', unknown: 'אין ערך עדיין',
};
const ST_HE: Record<string, string> = {
  forming: 'IB מתגבש', none: 'בלי הרחבה', up: 'הרחבה למעלה', down: 'הרחבה למטה', two_sided: 'הרחבה לשני הצדדים',
};

function brainFrom(c?: TreeContext, planHe?: { LONG: string; SHORT: string }, server?: Brain): Brain | null {
  if (server?.family && server.questions?.length) return server;
  if (!c) return null;
  const hour = parseInt(String(c.il || '0').slice(0, 2), 10);
  const st = c.structure || '';
  const family = hour >= 20
    ? { id: 'late', title: 'אחרי 20:00', on: 'בלי כניסה חדשה', off: 'כל כניסה' }
    : (c.phase === 'A' || c.phase === 'B' || st === 'forming')
      ? { id: 'opening', title: 'פתיחה', on: 'דהיית קצה · היפוך-דחייה · דרייב עם הכיוון', off: 'ZLR · שלב D' }
      : (st === 'up' || st === 'down')
        ? { id: 'extension', title: 'יציאה מה-IB', on: 'שבירה ועם-הדרייב בכיוון היציאה', off: 'שלב D עם-ההרחבה' }
        : st === 'none'
          ? { id: 'inside', title: 'בתוך ה-IB', on: 'דהיית הרחבה כושלת', off: 'עם-ההרחבה · ZLR עם-ההטיה' }
          : st === 'two_sided'
            ? { id: 'two_sided', title: 'שני צדדים', on: 'דהיית הרחבה כושלת, ספר דק', off: 'שבירה לשני הכיוונים' }
            : { id: 'open', title: 'עוד לא נעול', on: 'מחכים למבנה', off: '' };
  const hint = c.hint === 'LONG' ? 'לונג' : c.hint === 'SHORT' ? 'שורט' : 'בלי הטיה';
  const who = planHe
    ? (c.hint === 'LONG' || c.hint === 'SHORT' ? planHe[c.hint] : `לונג: ${planHe.LONG} · שורט: ${planHe.SHORT}`)
    : (ST_HE[st] || st || '?');
  return {
    family,
    questions: [
      { q: 'מה השוק מנסה', a: `${OT_HE[c.opening_type] || c.opening_type || '?'} · שלב ${c.phase || '?'} · ${hint}` },
      { q: 'כמה טוב הוא מצליח', a: 'נפח ודלתא עדיין לא מחוברים לווקטור' },
      { q: 'איפה ביחס לערך', a: ZN_HE[c.zone] || c.zone || '?' },
      { q: 'מי שולט', a: who },
      { q: 'איפה התזה נשברת', a: 'הסטופ על העוגן של הסטאפ, כשיש מועמד' },
    ],
  };
}

const LEAF_COLOR: Record<string, string> = { TAKE: '#16a34a', SHADOW: '#3b82f6', SKIP: '#7f1d1d' };
const LEAF_MARK: Record<string, string> = { TAKE: '✓', SHADOW: '◐', SKIP: '×' };

function KindChip({ kind, leaf }: { kind: string; leaf?: Leaf }) {
  const l = leaf?.leaf || 'SKIP';
  return (
    <span title={`${kind} → ${l}${leaf?.id ? ':' + leaf.id : ''}\n${leaf?.path || ''}`} style={{
      fontSize: 9, padding: '1px 5px', borderRadius: 3, fontFamily: 'ui-monospace, monospace',
      background: l === 'SKIP' ? 'rgba(255,255,255,0.03)' : LEAF_COLOR[l] + '33',
      color: l === 'SKIP' ? '#6b7280' : LEAF_COLOR[l] === '#7f1d1d' ? '#fca5a5' : '#e5e7eb',
      border: `1px solid ${l === 'SKIP' ? 'transparent' : LEAF_COLOR[l]}`,
    }}>
      {LEAF_MARK[l]} {KIND_HEB[kind] || kind}
    </span>
  );
}

export function TreeV3Strip() {
  const [st, setSt] = useState<TreeState | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/v9/tree/state`).catch(() => null);
        if (r && r.ok) setSt(await r.json());
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, 15000);   // diagnostic floor — do not go below (P30 forensics)
    return () => clearInterval(id);
  }, []);

  const brain = brainFrom(st?.context, st?.plan_he, st?.brain);
  const modeColor = st?.mode === 'on' ? '#16a34a' : st?.mode === 'shadow' ? '#3b82f6' : '#525252';
  const modeLabel = !st ? 'העץ — מתחבר…' : st.mode === 'on' ? 'העץ מחליט' : st.mode === 'shadow' ? 'העץ בצל' : 'העץ כבוי';
  const recent = (st?.recent || []).slice(0, open ? 12 : 3);

  return (
    <div id="tree-v3-strip" style={{
      background: COLORS.bgSurface2, borderBottom: `1px solid ${COLORS.borderFaint}`, flexShrink: 0,
      padding: '3px 12px', display: 'flex', flexDirection: 'column', gap: 3,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <span onClick={() => setOpen(o => !o)} style={{
          cursor: 'pointer', fontSize: 8, fontWeight: 700, padding: '1px 6px', borderRadius: 3, background: modeColor, color: '#fff', whiteSpace: 'nowrap',
        }}>המוח {modeLabel} {open ? '▴' : '▾'}</span>
        <span dir="rtl" style={{ fontSize: 10, color: '#e5e7eb', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1, textAlign: 'right' }}>
          {st?.error ? `שגיאה: ${st.error}` : (st?.where_he || 'טוען…')}
        </span>
        {st?.plan && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
            <span style={{ fontSize: 9, color: '#4ade80', fontWeight: 700 }}>L</span>
            {KINDS.map(k => <KindChip key={'L' + k} kind={k} leaf={st.plan!.LONG[k]} />)}
            <span style={{ width: 6 }} />
            <span style={{ fontSize: 9, color: '#f87171', fontWeight: 700 }}>S</span>
            {KINDS.map(k => <KindChip key={'S' + k} kind={k} leaf={st.plan!.SHORT[k]} />)}
          </div>
        )}
      </div>
      {brain && (
        <div dir="rtl" style={{ display: 'flex', flexDirection: 'column', gap: 1, fontSize: 10, color: '#d1d5db' }}>
          <div><b>משפחה: {brain.family.title}</b> · דולק: {brain.family.on}{brain.family.off ? ` · כבוי: ${brain.family.off}` : ''}</div>
          {brain.questions.map(q => (
            <div key={q.q}><span style={{ color: '#6b7280' }}>{q.q}</span> · {q.a}</div>
          ))}
        </div>
      )}
      {(open || recent.length > 0) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {open && st?.plan_he && (
            <div dir="rtl" style={{ fontSize: 10, color: '#9ca3af' }}>
              <span style={{ color: '#4ade80' }}>לונג:</span> {st.plan_he.LONG} &nbsp;·&nbsp; <span style={{ color: '#f87171' }}>שורט:</span> {st.plan_he.SHORT}
            </div>
          )}
          {recent.map((r, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, fontSize: 9, fontFamily: 'ui-monospace, monospace', color: '#9ca3af', alignItems: 'center' }}>
              <span style={{ color: '#6b7280' }}>{r.il}</span>
              <span style={{ color: r.direction === 'LONG' ? '#4ade80' : '#f87171' }}>{r.direction === 'LONG' ? '▲' : '▼'} {r.pattern}</span>
              <span>@{r.entry ?? '—'}</span>
              <span style={{ color: LEAF_COLOR[r.leaf] === '#7f1d1d' ? '#fca5a5' : LEAF_COLOR[r.leaf], fontWeight: 700 }}>{LEAF_MARK[r.leaf] || '?'} {r.leaf}{r.id ? ':' + r.id : ''}</span>
              {st?.mode === 'shadow' && r.legacy && <span style={{ color: '#6b7280' }}>ישן: {r.legacy}</span>}
              <span style={{ color: '#525252', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: open ? 900 : 420 }}>{r.path}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
