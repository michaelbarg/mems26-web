'use client';
/**
 * TreeStarField — "שדה-הכוכבים" של עץ-ההחלטות V3 במחשב.
 * מייקל 01.10: "תוסיף את עץ-ההחלטות במבנה התלת-מימדי של הקנבס גם לפרונט-אנד, שאפשר יהיה
 * לראות מהמחשב איך הוא גדל" (המקור: דף-הטלפון tree_v3.html מ-scripts/gen_phone_pages.py —
 * מייקל 24.09 "שדה נוירונים/כוכבים שאראה איך הענפים גדלים", 25.09 "ממש צריך להיות עץ!").
 *
 * אותה שפה כמו בטלפון: השורש במרכז, טבעת לכל שאלה (עומק), הענפים פרוסים בזווית לפי מספר
 * העלים, גודל-כוכב = √n מועמדים, צבע = הפעולה בעלה (ירוק לקחת · אדום לא · כחול צל).
 * וכאן בתלת-מימד: כל טבעת יורדת בעומק (y), מצלמת-מסלול — גרירה = סיבוב, גלגלת = זום,
 * סיבוב-איטי אוטומטי כשלא נוגעים, לחיצה-כפולה = איפוס.
 *
 * "איך הוא גדל" — שלוש שכבות של זמן על אותו שדה:
 *   1. המדידה הלילית (n/win/Σ$ על כל צומת) — tree_v3.json דרך /api/tree-board (לוח 60s).
 *   2. היום — כל החלטה של הגייטוויי נושאת tree_v3.path; כל צומת שמועמד עבר בו היום מקבל
 *      הילה צהובה ומונה (+N) — /api/v9/gateway/decisions (15s, רצפה דיאגנוסטית).
 *   3. עכשיו — הכוכב הצהוב הפועם = הצומת שהמערכת עומדת בו ברגע זה — /api/v9/tree/state (15s).
 * לחיצה על כוכב: הנתיב, המספרים, הפעולה, וההחלטות שעברו בו היום.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Leaf = 'TAKE' | 'SKIP' | 'SHADOW';
interface BoardNode {
  n?: number; win?: number | null; usd?: number; n_live?: number; usd_live?: number;
  take?: number; skip?: number; shadow?: number;
  split?: string; children?: Record<string, BoardNode>;
  leaf?: Leaf; id?: string; note?: string | null;
}
interface Board {
  generated?: string; sessions?: number; routes?: number; scored?: number; tag?: string; file_mtime?: string;
  tree?: BoardNode; leaves?: Array<{ path: string; leaf: string; n: number; ripe?: boolean }>; error?: string;
}
interface Decision {
  ts?: string; t_il?: string; pattern?: string; direction?: string; entry?: number | null;
  outcome?: string; blocked_by?: string | null; live_blocked_by?: string | null; trade_id?: number | null;
  tree_v3?: { leaf?: string; id?: string; path?: string };
}
interface TreeState {
  mode?: string; ts?: string; where_he?: string;
  context?: Record<string, string | number | null | undefined>;
  plan_he?: { LONG: string; SHORT: string };
}
interface Pt {
  i: number; key: string; raw: Array<[string, string]>; d: number; p: number; kids: number[];
  n: number; win: number | null; usd: number; nLive: number; usdLive: number;
  leaf: Leaf | null; split: string | null; note: string | null; id: string | null;
  take: number; skip: number; shadow: number;
  x: number; y: number; z: number; r: number;
}

const HEB_FEAT: Record<string, string> = {
  opening_type: 'סוג-פתיחה', phase: 'שלב', day_type: 'סוג-יום', structure: 'מבנה', pattern: 'תבנית',
  kind: 'סוג-כניסה', direction: 'כיוון', rel_bias: 'מול ההטיה', zone: 'מיקום מול הערך', prior_zone: 'מול ערך-אתמול',
  poc_side: 'צד ה-POC', value_migration: 'נדידת-ערך', edge: 'קצה', test: 'test', volume: 'ווליום', delta: 'דלתא',
  R_atr: 'סטופ/ATR', hour: 'שעה', system: 'מערכת',
};
const LEAF_COL: Record<string, string> = { TAKE: '#3fb950', SKIP: '#f85149', SHADOW: '#79c0ff' };
const LEAF_HEB: Record<string, string> = { TAKE: '✅ לקחת', SKIP: '⛔ לא', SHADOW: '🫧 צל' };
const LIVE = '#facc15';
const RING = (d: number) => (d === 0 ? 0 : 60 + d * 72);
const DROP = 34; // world units the field descends per depth

function countLeaves(nd: BoardNode): number {
  if (nd.leaf) return 1;
  const kids = Object.values(nd.children || {});
  return Math.max(1, kids.reduce((s, c) => s + countLeaves(c), 0));
}

/** The same radial layout as the phone board, lifted into 3D (ring = depth, y = depth). */
function layout(root: BoardNode): Pt[] {
  const pts: Pt[] = [];
  const lay = (nd: BoardNode, d: number, a0: number, a1: number, key: string, raw: Array<[string, string]>, parent: number): number => {
    const R = RING(d);
    const am = (a0 + a1) / 2;
    const n = nd.n || 0;
    const r = nd.leaf ? 2.2 + Math.sqrt(Math.min(n, 900)) * 0.42 : 1.8 + Math.sqrt(Math.min(n, 3000)) * 0.16;
    const i = pts.length;
    pts.push({
      i, key, raw, d, p: parent, kids: [], n, win: nd.win ?? null, usd: nd.usd || 0, nLive: nd.n_live || 0, usdLive: nd.usd_live || 0,
      leaf: nd.leaf || null, split: nd.split || null, note: nd.note || null, id: nd.id || null,
      take: nd.take || 0, skip: nd.skip || 0, shadow: nd.shadow || 0,
      x: R * Math.cos(am), z: R * Math.sin(am), y: d * DROP, r,
    });
    if (nd.children) {
      const entries = Object.entries(nd.children);
      const tot = entries.reduce((s, [, c]) => s + countLeaves(c), 0) || 1;
      let a = a0;
      for (const [k, c] of entries) {
        const w = (a1 - a0) * countLeaves(c) / tot;
        const feat = nd.split || '?';
        const ci = lay(c, d + 1, a, a + w, (key ? key + ' › ' : '') + `${HEB_FEAT[feat] || feat}=${k}`, [...raw, [feat, String(k)]], i);
        pts[i].kids.push(ci);
        a += w;
      }
    }
    return i;
  };
  lay(root, 0, -Math.PI / 2, 1.5 * Math.PI, '', [], -1);
  return pts;
}

/** Walk the field with a situation — the engine's rule: exact / A|B list / "*" default. */
function walk(pts: Pt[], vals: Record<string, string | undefined>): number[] {
  let i = 0;
  const path = [0];
  for (;;) {
    const p = pts[i];
    if (!p || !p.kids.length || !p.split) break;
    const v = vals[p.split];
    if (v === undefined || v === null) break;
    let hit: number | null = null, star: number | null = null;
    for (const k of p.kids) {
      const rk = pts[k].raw[pts[k].raw.length - 1][1];
      if (rk === '*') { star = k; continue; }
      if (rk.split('|').some((x) => x.toUpperCase() === String(v).toUpperCase())) { hit = k; break; }
    }
    const nx = hit !== null ? hit : star;
    if (nx === null) break;
    i = nx;
    path.push(i);
  }
  return path;
}

function parsePath(s: string | undefined): Record<string, string> {
  const o: Record<string, string> = {};
  for (const seg of (s || '').split('/')) {
    const j = seg.indexOf('=');
    if (j > 0) {
      let v = seg.slice(j + 1);
      const m = /^\*\((.*)\)$/.exec(v);
      if (m) v = m[1];
      o[seg.slice(0, j)] = v;
    }
  }
  return o;
}

const fmtUsd = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(Math.round(v)).toLocaleString()}$`;

export function TreeStarField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [boardErr, setBoardErr] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [tree, setTree] = useState<TreeState | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [autoRot, setAutoRot] = useState(true);
  const [follow, setFollow] = useState(true);
  const [showSkip, setShowSkip] = useState(true);
  const [dragging, setDragging] = useState(false);

  // camera (refs — the draw loop reads them without re-rendering React)
  const cam = useRef({ yaw: 0.6, pitch: 0.95, zoom: 1, tx: 0, ty: 0 });
  const idleSince = useRef(0);
  const drag = useRef<{ x: number; y: number; yaw: number; pitch: number; moved: boolean } | null>(null);
  const proj = useRef<Array<{ sx: number; sy: number; sr: number; depth: number }>>([]);

  // ── data ──────────────────────────────────────────────────────────────
  useEffect(() => {
    let alive = true;
    const loadBoard = async () => {
      try {
        const r = await fetch('/api/tree-board', { cache: 'no-store' });
        const d = (await r.json()) as Board;
        if (!alive) return;
        if (!r.ok || d.error) { setBoardErr(d.error || String(r.status)); return; }
        setBoard(d); setBoardErr(null);
      } catch (e) { if (alive) setBoardErr(String(e)); }
    };
    const loadLive = async () => {
      const [ds, ts] = await Promise.allSettled([
        fetch(`${API}/api/v9/gateway/decisions?limit=2000`, { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API}/api/v9/tree/state`, { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)),
      ]);
      if (!alive) return;
      if (ds.status === 'fulfilled' && ds.value) setDecisions(((ds.value as { decisions?: Decision[] }).decisions) || []);
      if (ts.status === 'fulfilled' && ts.value) setTree(ts.value as TreeState);
    };
    loadBoard(); loadLive();
    const a = setInterval(loadBoard, 60000);
    const b = setInterval(loadLive, 15000);
    return () => { alive = false; clearInterval(a); clearInterval(b); };
  }, []);

  const pts = useMemo(() => (board?.tree ? layout(board.tree) : []), [board]);

  // today's walks: node index → decisions that passed through it (ancestors included)
  const today = useMemo(() => {
    const m = new Map<number, Decision[]>();
    const il = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' });
    for (const d of decisions) {
      const p = d.tree_v3?.path;
      if (!p || !pts.length) continue;
      if (d.ts && new Date(d.ts).toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' }) !== il) continue;
      for (const i of walk(pts, parsePath(p))) {
        const arr = m.get(i) || [];
        arr.push(d);
        m.set(i, arr);
      }
    }
    return m;
  }, [decisions, pts]);

  const todayStats = useMemo(() => {
    const s = { n: 0, live: 0, shadow: 0, blocked: 0, byGate: new Map<string, number>() };
    for (const d of decisions) {
      if (!d.tree_v3) continue;
      s.n += 1;
      if (d.outcome === 'live' || d.outcome === 'fired') s.live += 1;
      else if (d.outcome === 'shadow_only' || d.outcome === 'shadow') s.shadow += 1;
      else { s.blocked += 1; const g = d.blocked_by || d.live_blocked_by || '?'; s.byGate.set(g, (s.byGate.get(g) || 0) + 1); }
    }
    return s;
  }, [decisions]);

  const livePath = useMemo(() => {
    const c = tree?.context;
    if (!c || !pts.length) return [] as number[];
    const vals: Record<string, string | undefined> = {};
    for (const k of ['opening_type', 'phase', 'day_type', 'structure', 'zone', 'prior_zone', 'poc_side', 'value_migration']) {
      const v = c[k]; if (v !== undefined && v !== null) vals[k] = String(v);
    }
    return walk(pts, vals);
  }, [tree, pts]);
  const liveNode = livePath.length ? livePath[livePath.length - 1] : null;

  // ── draw loop ─────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const cv = canvasRef.current, wrap = wrapRef.current;
    if (!cv || !wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const W = wrap.clientWidth, H = wrap.clientHeight;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
    const ctx = cv.getContext('2d'); if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // background — the field
    const g = ctx.createRadialGradient(W / 2, H / 2, 10, W / 2, H / 2, Math.max(W, H) * 0.7);
    g.addColorStop(0, '#121826'); g.addColorStop(1, '#0b0e14');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    if (!pts.length) return;

    const c = cam.current;
    const now = Date.now();
    if (autoRot && !drag.current && now - idleSince.current > 2500) c.yaw += 0.0022;
    const cy = Math.cos(c.yaw), sy = Math.sin(c.yaw), cp = Math.cos(c.pitch), sp = Math.sin(c.pitch);
    const F = 900; // focal length
    const base = Math.min(W, H) / 1150 * c.zoom;
    const maxD = pts.reduce((m, p) => Math.max(m, p.d), 0);
    const project = (x: number, y: number, z: number) => {
      const x1 = x * cy - z * sy, z1 = x * sy + z * cy;
      const yc = y - (maxD * DROP) / 2; // centre the cone vertically
      const y1 = yc * cp - z1 * sp, z2 = yc * sp + z1 * cp;
      const s = F / (F + z2 * 0.9 + 420) * base * 1.2;
      return { sx: W / 2 + c.tx + x1 * s * 1.05, sy: H / 2 + c.ty + y1 * s, s, depth: z2 };
    };
    // follow the live star: pan so it sits at the centre
    if (follow && liveNode !== null) {
      const p = pts[liveNode];
      const q = project(p.x, p.y, p.z);
      c.tx += (W / 2 - q.sx) * 0.08; c.ty += (H / 2 - q.sy) * 0.08;
    }
    const pr = pts.map((p) => { const q = project(p.x, p.y, p.z); return { sx: q.sx, sy: q.sy, sr: Math.min(26, Math.max(1.1, p.r * q.s * 2.2)), depth: q.depth, s: q.s }; });
    proj.current = pr;

    // depth rings (faint) — one per question level
    ctx.lineWidth = 0.6;
    for (let d = 1; d <= maxD; d++) {
      ctx.beginPath();
      for (let k = 0; k <= 72; k++) {
        const a = (k / 72) * Math.PI * 2;
        const q = project(RING(d) * Math.cos(a), d * DROP, RING(d) * Math.sin(a));
        if (k === 0) ctx.moveTo(q.sx, q.sy); else ctx.lineTo(q.sx, q.sy);
      }
      ctx.strokeStyle = 'rgba(139,148,158,0.10)'; ctx.stroke();
    }
    // edges, far → near
    const order = pts.map((p) => p.i).sort((a, b) => pr[b].depth - pr[a].depth);
    for (const i of order) {
      const p = pts[i]; if (p.p < 0) continue;
      if (!showSkip && p.leaf === 'SKIP' && !today.has(i)) continue;
      const a = pr[i], b = pr[p.p];
      const col = p.leaf === 'TAKE' ? 'rgba(63,185,80,' : p.leaf === 'SKIP' ? 'rgba(248,81,73,' : p.leaf === 'SHADOW' ? 'rgba(121,192,255,' : 'rgba(139,148,158,';
      const hot = today.has(i);
      ctx.strokeStyle = col + (hot ? '0.75)' : p.n ? '0.28)' : '0.10)');
      ctx.lineWidth = Math.max(0.4, (0.4 + Math.sqrt(Math.min(p.n, 800)) * 0.05) * a.s * 1.6) + (hot ? 0.8 : 0);
      ctx.beginPath(); ctx.moveTo(b.sx, b.sy); ctx.lineTo(a.sx, a.sy); ctx.stroke();
    }
    // nodes, far → near
    const pulse = (Math.sin(now / 260) + 1) / 2;
    ctx.font = '10px ui-monospace, monospace';
    for (const i of order) {
      const p = pts[i]; const q = pr[i];
      if (!showSkip && p.leaf === 'SKIP' && !today.has(i)) continue;
      const col = p.leaf ? LEAF_COL[p.leaf] : (p.n ? '#58a6ff' : '#3a4250');
      const hot = today.get(i);
      const onLive = livePath.includes(i);
      ctx.globalAlpha = p.n || hot ? 0.95 : 0.45;
      if (p.n || hot) { ctx.shadowColor = hot ? LIVE : col; ctx.shadowBlur = Math.min(14, 3 + Math.sqrt(p.n) * 0.25) + (hot ? 6 : 0); }
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(q.sx, q.sy, q.sr, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0; ctx.globalAlpha = 1;
      if (onLive) { ctx.strokeStyle = LIVE; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(q.sx, q.sy, q.sr + 2, 0, Math.PI * 2); ctx.stroke(); }
      if (hot) {
        ctx.strokeStyle = LIVE; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(q.sx, q.sy, q.sr + 3.5, 0, Math.PI * 2); ctx.stroke();
        if (p.leaf || q.sr >= 5) { ctx.fillStyle = LIVE; ctx.fillText(`+${hot.length}`, q.sx + q.sr + 4, q.sy - q.sr - 2); }
      }
      if (i === sel || i === hover) { ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(q.sx, q.sy, q.sr + 5, 0, Math.PI * 2); ctx.stroke(); }
      // labels: the first ring always, bigger stars, the live path, and anything hot
      const label = p.raw.length ? p.raw[p.raw.length - 1][1] : 'שורש';
      if (p.d <= 1 || q.sr >= 7 || onLive || (hot && p.leaf) || i === sel || i === hover) {
        ctx.fillStyle = onLive ? LIVE : (p.d <= 1 ? '#e6edf3' : '#9aa4b2');
        ctx.font = p.d <= 1 ? 'bold 11px ui-monospace, monospace' : '9.5px ui-monospace, monospace';
        ctx.fillText(label === '*' ? '*' : label, q.sx + q.sr + 3, q.sy + 3.5);
      }
    }
    // the live star — a pulsing beacon
    if (liveNode !== null) {
      const q = pr[liveNode];
      ctx.strokeStyle = LIVE; ctx.globalAlpha = 0.9 - pulse * 0.8; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.arc(q.sx, q.sy, q.sr + 6 + pulse * 22, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
    }
  }, [pts, today, livePath, liveNode, sel, hover, autoRot, follow, showSkip]);

  useEffect(() => {
    let raf = 0;
    const loop = () => { draw(); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [draw]);

  // ── interaction ───────────────────────────────────────────────────────
  const hit = (ev: React.PointerEvent | React.MouseEvent) => {
    const cv = canvasRef.current; if (!cv) return null;
    const r = cv.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    let best: number | null = null, bd = 1e9;
    proj.current.forEach((q, i) => {
      if (!showSkip && pts[i]?.leaf === 'SKIP' && !today.has(i)) return;
      const d = Math.hypot(q.sx - x, q.sy - y);
      if (d <= q.sr + 5 && d < bd) { bd = d; best = i; }
    });
    return best;
  };
  const onDown = (ev: React.PointerEvent) => {
    (ev.target as HTMLElement).setPointerCapture(ev.pointerId);
    drag.current = { x: ev.clientX, y: ev.clientY, yaw: cam.current.yaw, pitch: cam.current.pitch, moved: false };
    setDragging(true);
  };
  const onMove = (ev: React.PointerEvent) => {
    const d = drag.current;
    if (d) {
      const dx = ev.clientX - d.x, dy = ev.clientY - d.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) d.moved = true;
      cam.current.yaw = d.yaw + dx * 0.008;
      cam.current.pitch = Math.max(-1.45, Math.min(1.45, d.pitch + dy * 0.008));
      idleSince.current = Date.now();
    } else {
      setHover(hit(ev));
    }
  };
  const onUp = (ev: React.PointerEvent) => {
    const d = drag.current; drag.current = null; idleSince.current = Date.now(); setDragging(false);
    if (d && !d.moved) { const h = hit(ev); setSel(h); if (h !== null) setFollow(false); }
  };
  const onWheel = (ev: React.WheelEvent) => {
    cam.current.zoom = Math.max(0.35, Math.min(7, cam.current.zoom * (ev.deltaY < 0 ? 1.15 : 1 / 1.15)));
    idleSince.current = Date.now();
  };
  const reset = () => { cam.current = { yaw: 0.6, pitch: 0.95, zoom: 1, tx: 0, ty: 0 }; setFollow(false); };

  // ── panel data ────────────────────────────────────────────────────────
  const selected = sel !== null ? pts[sel] : hover !== null ? pts[hover] : null;
  const selToday = selected ? today.get(selected.i) || [] : [];
  const leaves = board?.leaves || [];
  const nTake = leaves.filter((l) => l.leaf === 'TAKE').length, nSkip = leaves.filter((l) => l.leaf === 'SKIP').length;
  const nShadow = leaves.filter((l) => l.leaf === 'SHADOW').length, nRipe = leaves.filter((l) => l.ripe).length;
  const touchedToday = [...today.keys()].filter((i) => pts[i]?.leaf).length;

  const btn = (active: boolean): React.CSSProperties => ({
    fontSize: 10, padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
    border: `1px solid ${active ? LIVE : COLORS.borderTertiary}`, color: active ? LIVE : COLORS.textSecondary,
    background: active ? 'rgba(250,204,21,0.08)' : 'transparent',
  });

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 0, background: COLORS.bgBase }}>
      {/* the field */}
      <div ref={wrapRef} style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block', cursor: dragging ? 'grabbing' : hover !== null ? 'pointer' : 'grab', touchAction: 'none' }}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} onWheel={onWheel} onDoubleClick={reset} />
        <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button style={btn(autoRot)} onClick={() => setAutoRot((v) => !v)} title="סיבוב איטי אוטומטי כשלא נוגעים">⟳ סיבוב</button>
          <button style={btn(follow)} onClick={() => setFollow((v) => !v)} title="לעקוב אחרי הכוכב הצהוב הפועם — איפה המערכת עכשיו">◎ עקוב</button>
          <button style={btn(showSkip)} onClick={() => setShowSkip((v) => !v)} title="להציג גם את ענפי ה-SKIP (אדום). כיבוי = רק לקחת/צל + מה שזז היום">⛔ SKIP</button>
          <button style={btn(false)} onClick={reset} title="איפוס מצלמה (גם לחיצה-כפולה)">⌂</button>
        </div>
        <div dir="rtl" style={{ position: 'absolute', bottom: 8, right: 8, left: 8, background: 'rgba(11,14,20,0.82)', border: '1px solid #2a3140', borderRadius: 8, padding: '5px 10px', fontSize: 11, lineHeight: 1.5, color: COLORS.textPrimary, pointerEvents: 'none' }}>
          {tree ? (
            <>
              <b style={{ color: LIVE }}>● עכשיו</b> {tree.where_he || '—'}
              <span style={{ color: COLORS.textTertiary }}> · {tree.mode === 'on' ? 'העץ מחליט' : tree.mode === 'shadow' ? 'העץ בצל' : 'העץ כבוי'} · {tree.ts || ''}</span>
              {tree.plan_he && <div style={{ color: COLORS.textTertiary, fontSize: 10 }}><span style={{ color: '#4ade80' }}>לונג:</span> {tree.plan_he.LONG} · <span style={{ color: '#f87171' }}>שורט:</span> {tree.plan_he.SHORT}</div>}
            </>
          ) : <span style={{ color: COLORS.textTertiary }}>מצב-העץ: אין נתונים (API)</span>}
        </div>
        {boardErr && <div dir="rtl" style={{ position: 'absolute', top: 44, right: 8, color: '#facc15', fontSize: 11, background: '#2a1f0a', border: '1px solid #eab30855', borderRadius: 6, padding: '4px 8px' }}>⚠ אין לוח-עץ: {boardErr}</div>}
      </div>

      {/* the panel */}
      <div dir="rtl" style={{ width: 320, flexShrink: 0, borderRight: `1px solid ${COLORS.borderTertiary}`, background: COLORS.bgSurface1, overflowY: 'auto', padding: 10, fontSize: 11, lineHeight: 1.5, color: COLORS.textPrimary }}>
        <div style={{ fontSize: 14, fontWeight: 700 }}>🌌 עץ-ההחלטות V3 — שדה-הכוכבים</div>
        <div style={{ color: COLORS.textTertiary, fontSize: 10, marginBottom: 8 }}>
          השורש במרכז · טבעת לכל שאלה · גודל = √מועמדים · צבע = הפעולה בעלה. גרירה = סיבוב · גלגלת = זום · לחיצה = פרטים.
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
          <Kpi l="עלים" v={String(leaves.length)} s={`${nTake} לקחת · ${nSkip} לא · ${nShadow} צל`} />
          <Kpi l="מועמדים במדידה" v={String(board?.routes ?? '—')} s={`${board?.sessions ?? '—'} סשנים · ${board?.tag || ''}`} />
          <Kpi l="היום עברו בעץ" v={String(todayStats.n)} s={`${todayStats.live} לייב · ${todayStats.shadow} צל · ${todayStats.blocked} נחסמו`} col={LIVE} />
          <Kpi l="עלים שזזו היום" v={String(touchedToday)} s={`🌱 ${nRipe} בשלים לפיצול`} col={LIVE} />
        </div>
        <div style={{ color: COLORS.textTertiary, fontSize: 9.5, marginBottom: 8 }}>
          נמדד: {(board?.generated || '—').slice(0, 16).replace('T', ' ')} (scripts/tree_measure.py, לילי) · היום: זרם-ההחלטות של הגייטוויי (15s) · עכשיו: tree/state (15s)
        </div>
        {todayStats.byGate.size > 0 && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 700, fontSize: 10, color: COLORS.textSecondary }}>למה נחסמו היום</div>
            {[...todayStats.byGate.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7).map(([g, n]) => (
              <div key={g} style={{ display: 'flex', justifyContent: 'space-between', color: COLORS.textTertiary }}>
                <span dir="ltr" style={{ fontFamily: 'ui-monospace, monospace' }}>{g}</span><span>{n}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ borderTop: `1px solid ${COLORS.borderFaint}`, paddingTop: 8, marginTop: 4 }}>
          {selected ? (
            <>
              <div style={{ fontWeight: 700, color: selected.leaf ? LEAF_COL[selected.leaf] : '#58a6ff' }}>
                {selected.leaf ? LEAF_HEB[selected.leaf] : `שאלה: ${HEB_FEAT[selected.split || ''] || selected.split || '—'}?`}
                {selected.id ? <span style={{ color: COLORS.textTertiary, fontWeight: 400 }}> · {selected.id}</span> : null}
              </div>
              <div style={{ fontSize: 10, color: COLORS.textSecondary, wordBreak: 'break-word' }}>{selected.key || 'שורש'}</div>
              <div style={{ marginTop: 4 }}>
                מועמדים <b>{selected.n}</b>
                {selected.n ? <> · win {selected.win ?? '—'}% · <span dir="ltr">{fmtUsd(selected.usd)}</span> אילו נלקחו</> : null}
                {selected.nLive ? <div>לייב <b>{selected.nLive}</b> · <span dir="ltr">{fmtUsd(selected.usdLive)}</span></div> : null}
                {!selected.leaf && selected.n ? <div style={{ color: COLORS.textTertiary }}>מתחתיו: {selected.take} לקחת · {selected.skip} לא · {selected.shadow} צל</div> : null}
              </div>
              {selected.note && <div style={{ color: COLORS.textTertiary, fontSize: 10, marginTop: 2 }}>{selected.note}</div>}
              <div style={{ marginTop: 6, fontWeight: 700, color: LIVE }}>היום בצומת הזה: {selToday.length}</div>
              {selToday.slice(0, 12).map((d, k) => (
                <div key={k} dir="ltr" style={{ fontFamily: 'ui-monospace, monospace', fontSize: 9.5, color: COLORS.textSecondary, display: 'flex', gap: 6 }}>
                  <span style={{ color: COLORS.textTertiary }}>{d.t_il || (d.ts || '').slice(11, 19)}</span>
                  <span style={{ color: d.direction === 'LONG' ? '#4ade80' : '#f87171' }}>{d.direction === 'LONG' ? '▲' : '▼'} {d.pattern}</span>
                  <span style={{ color: d.outcome === 'live' ? '#3fb950' : d.outcome === 'shadow_only' ? '#79c0ff' : '#f87171' }}>{d.outcome}{d.blocked_by ? `:${d.blocked_by}` : ''}</span>
                </div>
              ))}
              {selToday.length > 12 && <div style={{ color: COLORS.textTertiary }}>…ועוד {selToday.length - 12}</div>}
            </>
          ) : (
            <div style={{ color: COLORS.textTertiary }}>לחיצה על כוכב מציגה כאן את הנתיב, המספרים, הפעולה — ומה עבר בו היום.</div>
          )}
        </div>

        <div style={{ borderTop: `1px solid ${COLORS.borderFaint}`, paddingTop: 8, marginTop: 10, color: COLORS.textTertiary, fontSize: 10 }}>
          <div><span style={{ color: LEAF_COL.TAKE }}>●</span> לקחת &nbsp; <span style={{ color: LEAF_COL.SKIP }}>●</span> לא &nbsp; <span style={{ color: LEAF_COL.SHADOW }}>●</span> צל &nbsp; <span style={{ color: '#58a6ff' }}>●</span> שאלה &nbsp; <span style={{ color: LIVE }}>◎</span> זז היום / עכשיו</div>
          <div>איך הוא גדל: עלה בשל (n≥30, תוצאה מעורבת) → השאלה הבאה בסדר הדוקטרינרי → ריפליי יום-כולל → ענף עם מספר. היום = הילה צהובה + מונה על כל צומת שמועמד עבר בו.</div>
        </div>
      </div>
    </div>
  );
}

function Kpi({ l, v, s, col }: { l: string; v: string; s: string; col?: string }) {
  return (
    <div style={{ background: COLORS.bgSurface3, border: `1px solid ${COLORS.borderFaint}`, borderRadius: 6, padding: '4px 8px' }}>
      <div style={{ fontSize: 9, color: COLORS.textTertiary }}>{l}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: col || COLORS.textPrimary, fontFamily: 'ui-monospace, monospace' }}>{v}</div>
      <div style={{ fontSize: 9, color: COLORS.textTertiary }}>{s}</div>
    </div>
  );
}
