'use client';
// PagesPanel — every page in the system, linked + audit status (Michael 2026-07-08:
// "access to all pages + audit which are good / dated / archive").
// Source: /pages_index.json (agents keep it current; PAGES-AUDIT task classifies).
import { useCallback, useEffect, useState } from 'react';

interface PageRow {
  path: string;
  title: string;
  description: string;
  status: 'active' | 'review' | 'archive-candidate' | 'archived';
  audit_note?: string;
}

const STATUS_STYLE: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: 'פעיל', color: '#3fb950', bg: 'rgba(63,185,80,.12)' },
  review: { label: 'לבדיקה', color: '#d29922', bg: 'rgba(210,153,34,.12)' },
  'archive-candidate': { label: 'מועמד לארכיון', color: '#f85149', bg: 'rgba(248,81,73,.12)' },
  archived: { label: 'בארכיון', color: '#8b949e', bg: 'rgba(139,148,158,.12)' },
};

export function PagesPanel() {
  const [pages, setPages] = useState<PageRow[]>([]);
  const [updated, setUpdated] = useState<string>('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/pages_index.json', { cache: 'no-store' });
      if (!res.ok) return;
      const d = await res.json();
      setPages(Array.isArray(d.pages) ? d.pages : []);
      setUpdated(d.updated || '');
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000); // static file — light poll
    return () => clearInterval(id);
  }, [load]);

  return (
    <section style={{
      border: '1px solid #21262d', borderRadius: 10, background: '#0d1117', padding: 14,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
        <h2 style={{ margin: 0, fontSize: 15, color: '#e6edf3' }}>עמודי המערכת — גישה + סטטוס אודיט</h2>
        <span style={{ fontSize: 11, color: '#8b949e' }}>{updated && `עודכן ${updated.slice(0, 16).replace('T', ' ')}`}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {pages.filter(p => p.status !== 'archived').map(p => {
          const s = STATUS_STYLE[p.status] || STATUS_STYLE.review;
          const external = p.path.startsWith('http');
          return (
            <a key={p.path} href={p.path} target={external ? '_blank' : undefined} rel="noreferrer"
               style={{
                 display: 'flex', gap: 10, alignItems: 'baseline', textDecoration: 'none',
                 padding: '8px 10px', borderRadius: 8, border: '1px solid #21262d', background: '#010409',
               }}>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 999, whiteSpace: 'nowrap',
                color: s.color, background: s.bg, border: `1px solid ${s.color}33`,
              }}>{s.label}</span>
              <span style={{ color: '#58a6ff', fontSize: 13, whiteSpace: 'nowrap' }}>{p.title}</span>
              <span style={{ color: '#8b949e', fontSize: 12, direction: 'ltr' }}>{p.path}</span>
              <span style={{ color: '#6e7681', fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {p.description}{p.audit_note ? ` · ${p.audit_note}` : ''}
              </span>
            </a>
          );
        })}
      </div>
    </section>
  );
}
