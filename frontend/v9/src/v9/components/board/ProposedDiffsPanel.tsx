'use client';
/**
 * ProposedDiffsPanel — למידה-v3 (מייקל 07-12): הצעות-הכיול של לולאת-הלמידה
 * הלילית, עם כפתור "החל וקדם" — הקליק של מייקל הוא הפסיקה. שום דיף לא מוחל
 * אוטומטית. ההחלה: ולידציה → מיזוג-כירורגי ל-targets.yaml → טסטים (כישלון =
 * ‏revert) → קומיט+פוש; הפאנל מציג את הפלט ומזכיר שנדרש ריסטארט.
 */
import { useCallback, useEffect, useState } from 'react';

type Diff = { file: string; date: string; content: string };
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || '';

export function ProposedDiffsPanel() {
  const [diffs, setDiffs] = useState<Diff[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const r = await fetch('http://localhost:8000/api/v9/agent/proposed_diffs', { cache: 'no-store' });
      if (r.ok) setDiffs((await r.json()).diffs || []);
    } catch { /* backend down — hide panel */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function apply(file: string) {
    if (!window.confirm(`להחיל את ${file} על targets.yaml?\nהקליק הזה = פסיקה. טסטים ירוצו; כישלון = revert אוטומטי.`)) return;
    setBusy(file);
    try {
      const r = await fetch('http://localhost:8000/api/v9/agent/apply_targets_diff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
        body: JSON.stringify({ file }),
      });
      const data = await r.json().catch(() => ({}));
      setResult((m) => ({ ...m, [file]: (data.output || data.detail || `HTTP ${r.status}`) +
        (data.ok ? '\n✅ הוחל וקומט. ⚠ נדרש ריסטארט-בקאנד (לא בזמן עסקה פתוחה).' : '\n❌ נכשל — לא הוחל.') }));
    } catch (e) {
      setResult((m) => ({ ...m, [file]: `⚠ אין חיבור לבקאנד (${e})` }));
    } finally {
      setBusy(null);
    }
  }

  if (diffs.length === 0) return null;

  return (
    <div dir="rtl" style={{
      background: 'var(--bg-panel, #0d1117)', border: '1px solid var(--orange, #d29922)',
      borderRadius: 8, padding: 14, color: 'var(--text-secondary, #c9d1d9)', marginBottom: 16,
    }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--orange, #d29922)' }}>
        📐 הצעות-כיול מלולאת-הלמידה — ממתינות לפסיקתך ({diffs.length})
      </div>
      {diffs.map((d) => (
        <div key={d.file} style={{ marginTop: 10, border: '1px solid var(--border, #30363d)', borderRadius: 6, padding: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>{d.file}</span>
            <button onClick={() => apply(d.file)} disabled={busy !== null}
                    style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                             background: 'var(--green, #238636)', color: '#fff', border: 'none',
                             opacity: busy ? 0.5 : 1 }}>
              {busy === d.file ? 'מחיל…' : 'החל וקדם (פסיקה)'}
            </button>
          </div>
          <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', margin: '8px 0 0', direction: 'ltr',
                        color: 'var(--text-muted, #8b949e)', maxHeight: 160, overflowY: 'auto' }}>
            {d.content}
          </pre>
          {result[d.file] && (
            <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', margin: '8px 0 0', direction: 'ltr',
                          color: 'var(--text-primary, #e6edf3)', background: 'rgba(255,255,255,0.04)',
                          padding: 8, borderRadius: 4 }}>
              {result[d.file]}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
