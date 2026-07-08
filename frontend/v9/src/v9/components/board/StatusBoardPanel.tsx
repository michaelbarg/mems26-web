'use client';

// Live, prioritized task/issue board. Reads /task_board.json (a static file both
// Cowork and Claude Code edit + keep in lockstep with docs/plans/LIVE_FIX_JOURNAL.md).
// No backend dependency — safe to run on a real-money-live day.

import { useCallback, useEffect, useState } from 'react';
import { groupByLane, priorityCounts } from './boardLogic.mjs';

type TaskLink = { label: string; path: string };
type Task = {
  id: string; title: string; priority: 'P0' | 'P1' | 'P2'; status: string;
  owner: string; where: string; next?: string; evidence?: string; links?: TaskLink[];
};
type BoardMeta = {
  title?: string; subtitle?: string; updated?: string; priority_note?: string;
  indexes?: TaskLink[];
};
type Board = { meta?: BoardMeta; tasks?: Task[] };

const PRIORITY_COLOR: Record<string, string> = {
  P0: 'var(--red, #f85149)', P1: 'var(--orange, #d29922)', P2: 'var(--text-muted, #8b949e)',
};
const OWNER_COLOR: Record<string, string> = {
  CC: '#58a6ff', Cowork: '#bc8cff', Michael: '#3fb950', 'CC+Cowork': '#79c0ff',
};

function Chip({ text, color, bg }: { text: string; color?: string; bg?: string }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '1px 6px', borderRadius: 4,
      color: color || 'var(--text-secondary, #c9d1d9)',
      background: bg || 'rgba(255,255,255,0.06)', whiteSpace: 'nowrap',
    }}>{text}</span>
  );
}

export function StatusBoardPanel() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<string>('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/task_board.json', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setBoard(await res.json());
      setError(null);
      setFetchedAt(new Date().toLocaleTimeString());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000); // static file — light poll
    return () => clearInterval(id);
  }, [load]);

  const meta = board?.meta || {};
  const tasks = board?.tasks || [];
  const lanes = groupByLane(tasks);
  const counts = priorityCounts(tasks);

  return (
    <div style={{
      background: 'var(--bg-panel, #0d1117)', border: '1px solid var(--border, #30363d)',
      borderRadius: 8, padding: 14, color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
            {meta.title || 'Task Board'}
          </div>
          {meta.subtitle && (
            <div style={{ fontSize: 12, color: 'var(--text-muted, #8b949e)' }}>{meta.subtitle}</div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <Chip text={`P0 ${counts.P0}`} color="#fff" bg={PRIORITY_COLOR.P0} />
          <Chip text={`P1 ${counts.P1}`} color="#000" bg={PRIORITY_COLOR.P1} />
          <Chip text={`P2 ${counts.P2}`} />
          <button onClick={load} style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
            background: 'transparent', color: 'var(--text-muted, #8b949e)',
            border: '1px solid var(--border, #30363d)',
          }}>↻</button>
        </div>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginTop: 4 }}>
        {meta.priority_note}{meta.updated ? ` · updated ${meta.updated.slice(0, 16).replace('T', ' ')}` : ''}
        {fetchedAt ? ` · fetched ${fetchedAt}` : ''}
      </div>

      {meta.indexes && meta.indexes.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          <span style={{ fontSize: 11, opacity: 0.6 }}>Where to look:</span>
          {meta.indexes.map((ix) => (
            <span key={ix.path} title={ix.path} style={{
              fontSize: 11, fontFamily: 'ui-monospace, monospace', padding: '1px 6px',
              borderRadius: 4, background: 'rgba(88,166,255,0.10)', color: '#79c0ff',
            }}>{ix.label}</span>
          ))}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--red, #f85149)' }}>
          Could not load /task_board.json ({error}). Is the frontend serving public/?
        </div>
      )}

      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {lanes.map((lane) => (
          <div key={lane.key}>
            <div style={{ fontSize: 12, fontWeight: 700, color: lane.color, marginBottom: 6 }}>
              {lane.emoji} {lane.label} <span style={{ opacity: 0.5 }}>({lane.tasks.length})</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {lane.tasks.map((t: Task) => (
                <div key={t.id} style={{
                  border: '1px solid var(--border, #30363d)', borderLeft: `3px solid ${PRIORITY_COLOR[t.priority]}`,
                  borderRadius: 6, padding: '8px 10px', background: 'rgba(255,255,255,0.02)',
                }}>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Chip text={t.priority} color={t.priority === 'P1' ? '#000' : '#fff'} bg={PRIORITY_COLOR[t.priority]} />
                    <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>{t.id}</span>
                    <Chip text={t.owner} color={OWNER_COLOR[t.owner] || undefined} />
                    <span style={{ fontSize: 11, opacity: 0.5, marginLeft: 'auto' }}>{t.status.replace(/_/g, ' ')}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text, #e6edf3)', marginTop: 4 }}>{t.title}</div>
                  <div style={{ fontSize: 11, fontFamily: 'ui-monospace, monospace', color: 'var(--text-muted, #8b949e)', marginTop: 4 }}>
                    📍 {t.where}
                  </div>
                  {t.next && (
                    <div style={{ fontSize: 12, color: '#79c0ff', marginTop: 4 }}>▶ {t.next}</div>
                  )}
                  {t.evidence && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginTop: 3, fontStyle: 'italic' }}>
                      {t.evidence}
                    </div>
                  )}
                  {t.links && t.links.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 5 }}>
                      {t.links.map((l) => (
                        <span key={l.path} title={l.path} style={{
                          fontSize: 10, fontFamily: 'ui-monospace, monospace', padding: '1px 5px',
                          borderRadius: 3, background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted, #8b949e)',
                        }}>{l.label}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
