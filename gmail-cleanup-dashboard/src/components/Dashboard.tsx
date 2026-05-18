'use client';

import { useState, useCallback, useEffect } from 'react';
import { signOut } from 'next-auth/react';
import { ActionType, Category, CATEGORY_LABELS, DashboardStats, EmailGroup, PendingAction } from '@/types/email';
import StatsCard from './StatsCard';
import EmailGroupCard from './EmailGroupCard';
import ConfirmModal from './ConfirmModal';

type Filter = 'all' | Category;
const LIMITS = [200, 500, 1000];

export default function Dashboard({ userEmail, userName, userImage, hasTokenError }: {
  userEmail: string; userName: string; userImage: string | null; hasTokenError: boolean;
}) {
  const [groups, setGroups] = useState<EmailGroup[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [limit, setLimit] = useState(300);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [executing, setExecuting] = useState(false);
  const [done, setDone] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

  const loadEmails = useCallback(async () => {
    setLoading(true); setError(null); setDone(new Set());
    try {
      const res = await fetch(`/api/gmail/analyze?limit=${limit}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? res.statusText);
      setGroups(data.groups); setStats(data.stats);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [limit]);

  useEffect(() => { loadEmails(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function proposeAction(group: EmailGroup, action: ActionType, label?: string) {
    if (action === 'keep') {
      setDone((prev) => new Set([...prev, group.senderEmail || group.senderName]));
      showToast(`„${group.senderName}“ wird behalten.`);
      return;
    }
    setPending({ action, ids: group.ids, label, senderSummary: group.senderName || group.senderEmail, count: group.count, category: group.category });
  }

  async function confirmAction() {
    if (!pending) return;
    setExecuting(true);
    try {
      const res = await fetch('/api/gmail/actions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pending),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? res.statusText);
      showToast(`✅ ${data.count} E-Mails erfolgreich verarbeitet.`);
      setGroups((prev) => prev.filter((g) => !pending.ids.every((id) => g.ids.includes(id))));
      loadEmails();
    } catch (e: unknown) {
      showToast(`❌ Fehler: ${e instanceof Error ? e.message : String(e)}`);
    } finally { setExecuting(false); setPending(null); }
  }

  const visible = groups.filter((g) => {
    const key = g.senderEmail || g.senderName;
    if (done.has(key)) return false;
    if (filter !== 'all' && g.category !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      return g.senderName.toLowerCase().includes(q) || g.senderEmail.toLowerCase().includes(q) || g.subjects.some((s) => s.toLowerCase().includes(q));
    }
    return true;
  });

  const activeCategories = stats
    ? (Object.entries(stats.categoryBreakdown) as [Category, number][]).filter(([, n]) => n > 0).sort(([, a], [, b]) => b - a)
    : [];

  if (hasTokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Sitzung abgelaufen — bitte neu anmelden.</p>
          <button onClick={() => signOut({ callbackUrl: '/' })} className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-xl">Neu anmelden</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-2xl">📤</span>
            <span className="font-bold text-lg hidden sm:block">Gmail Cleanup</span>
          </div>
          <div className="flex items-center gap-1 bg-slate-800 rounded-xl p-1">
            {LIMITS.map((l) => (
              <button key={l} onClick={() => setLimit(l)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${limit === l ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
                {l.toLocaleString()}
              </button>
            ))}
          </div>
          <button onClick={loadEmails} disabled={loading}
            className="bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-white px-3 py-2 rounded-xl text-sm font-medium transition-colors">
            {loading ? (
              <svg className="animate-spin h-4 w-4 inline" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            ) : '↻'} Laden
          </button>
          <button onClick={() => signOut({ callbackUrl: '/' })}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm" title="Abmelden">
            {userImage && <img src={userImage} alt="" className="w-7 h-7 rounded-full" />}
            <span className="hidden md:block max-w-[140px] truncate">{userEmail}</span>
            <span>⎋</span>
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        {error && <div className="bg-red-900/40 border border-red-700/50 rounded-xl p-4 mb-6 text-red-300 text-sm">⚠️ {error}</div>}

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <StatsCard icon="📧" label="Analysiert" value={stats.totalEmails} color="indigo" />
            <StatsCard icon="🔵" label="Ungelesen" value={stats.totalUnread} color="indigo" />
            <StatsCard icon="📰" label="Newsletter" value={stats.newsletterCount} color="pink" />
            <StatsCard icon="💶" label="Rechnungen" value={stats.financeCount} color="emerald" />
            <StatsCard icon="👥" label="Duplikat-Gruppen" value={stats.duplicateGroups} color="amber" sub="≥3 vom gleichen Absender" />
            <StatsCard icon="🤖" label="Business/KI" value={stats.businessCount} color="indigo" />
          </div>
        )}

        {stats && (
          <div className="flex flex-wrap gap-2 mb-4">
            <button onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors border ${filter === 'all' ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'}`}>
              Alle ({groups.length})
            </button>
            {activeCategories.map(([cat, count]) => (
              <button key={cat} onClick={() => setFilter(cat === filter ? 'all' : cat)}
                className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors border ${filter === cat ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'}`}>
                {CATEGORY_LABELS[cat]} ({count})
              </button>
            ))}
          </div>
        )}

        <div className="mb-4">
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍  Absender oder Betreff suchen…"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors" />
        </div>

        {loading && (
          <div className="space-y-3">
            {[1,2,3,4].map((i) => <div key={i} className="bg-slate-800/60 rounded-2xl p-5 animate-pulse h-36" />)}
            <p className="text-center text-slate-500 text-sm mt-4">Lade und analysiere E-Mails… das kann etwas dauern.</p>
          </div>
        )}

        {!loading && groups.length === 0 && !error && (
          <div className="text-center py-20 text-slate-500">
            <p className="text-5xl mb-4">🎉</p>
            <p className="text-xl font-semibold text-slate-400">Postfach ist aufgeräumt!</p>
            <p className="text-sm mt-2">Keine E-Mails gefunden oder alle wurden bearbeitet.</p>
          </div>
        )}

        {!loading && visible.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500 mb-2">{visible.length} Absender-Gruppen · sortiert nach Anzahl</p>
            {visible.map((g) => (
              <EmailGroupCard key={g.senderEmail || g.senderName} group={g} onAction={(action, label) => proposeAction(g, action, label)} />
            ))}
          </div>
        )}
      </main>

      {pending && <ConfirmModal pending={pending} executing={executing} onConfirm={confirmAction} onCancel={() => setPending(null)} />}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-800 border border-slate-600 rounded-xl px-4 py-3 text-sm text-white shadow-xl fade-in max-w-xs">{toast}</div>
      )}
    </div>
  );
}
