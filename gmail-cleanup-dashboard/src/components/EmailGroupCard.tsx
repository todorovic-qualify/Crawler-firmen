'use client';

import { useState } from 'react';
import { ActionType, EmailGroup, GMAIL_LABELS } from '@/types/email';
import CategoryBadge from './CategoryBadge';

const AVATAR_COLORS = [
  'bg-indigo-700', 'bg-violet-700', 'bg-sky-700', 'bg-teal-700',
  'bg-emerald-700', 'bg-rose-700', 'bg-amber-700', 'bg-pink-700',
];

function avatarColor(str: string) {
  let h = 0;
  for (const c of str) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

function ActionBtn({ icon, label, onClick, className }: {
  icon: string; label: string; onClick: () => void; className: string;
}) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-200 transition-colors ${className}`}>
      <span>{icon}</span><span>{label}</span>
    </button>
  );
}

export default function EmailGroupCard({ group, onAction }: {
  group: EmailGroup; onAction: (action: ActionType, label?: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showLabelMenu, setShowLabelMenu] = useState(false);
  const initial = (group.senderName || group.senderEmail || '?')[0].toUpperCase();
  const visibleSubjects = expanded ? group.subjects : group.subjects.slice(0, 5);

  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 fade-in hover:border-slate-600 transition-colors">
      <div className="flex items-start gap-4">
        <div className={`flex-shrink-0 w-11 h-11 rounded-xl ${avatarColor(group.senderEmail || group.senderName)} flex items-center justify-center text-lg font-bold text-white`}>
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="font-semibold text-white truncate">{group.senderName}</span>
            <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded-full font-semibold">{group.count} E-Mails</span>
            {group.unreadCount > 0 && <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full font-semibold">{group.unreadCount} ungelesen</span>}
            {group.isNewsletter && <span className="bg-pink-900/60 border border-pink-700/50 text-pink-300 text-xs px-2 py-0.5 rounded-full">Newsletter</span>}
          </div>
          <p className="text-slate-400 text-sm truncate">{group.senderEmail}</p>
        </div>
        <div className="flex-shrink-0"><CategoryBadge category={group.category} size="xs" /></div>
      </div>

      <div className="mt-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Betreffzeilen</p>
        <div className="space-y-1">
          {visibleSubjects.map((s, i) => (
            <div key={i} className="text-sm text-slate-300 bg-slate-900/50 rounded-lg px-3 py-1.5 border-l-2 border-indigo-500/40 truncate">{s}</div>
          ))}
        </div>
        {group.subjects.length > 5 && (
          <button onClick={() => setExpanded((p) => !p)} className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
            {expanded ? '▲ Weniger anzeigen' : `▼ ${group.subjects.length - 5} weitere Betreffzeilen anzeigen`}
          </button>
        )}
      </div>

      {group.suggestedAction !== 'keep' && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
          <span>💡 Vorschlag:</span>
          <span className="text-indigo-400 font-medium">{group.suggestedAction === 'archive' ? 'Archivieren' : group.suggestedAction}</span>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <ActionBtn onClick={() => onAction('archive')} icon="📥" label="Archivieren" className="bg-slate-700 hover:bg-slate-600" />
        <ActionBtn onClick={() => onAction('delete')} icon="🗑️" label="Papierkorb" className="bg-red-900/50 hover:bg-red-800/60 border border-red-700/40" />
        <ActionBtn onClick={() => onAction('markRead')} icon="✅" label="Als gelesen" className="bg-slate-700 hover:bg-slate-600" />
        <ActionBtn onClick={() => onAction('markUnread')} icon="🔵" label="Als ungelesen" className="bg-slate-700 hover:bg-slate-600" />
        <div className="relative">
          <ActionBtn onClick={() => setShowLabelMenu((p) => !p)} icon="🏷️" label="Label" className="bg-indigo-900/50 hover:bg-indigo-800/60 border border-indigo-700/40" />
          {showLabelMenu && (
            <div className="absolute bottom-full mb-1 left-0 z-20 bg-slate-800 border border-slate-600 rounded-xl shadow-xl overflow-hidden min-w-[180px]">
              {GMAIL_LABELS.map((lbl) => (
                <button key={lbl} onClick={() => { setShowLabelMenu(false); onAction('addLabel', lbl); }}
                  className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors">
                  🏷️ {lbl}
                </button>
              ))}
            </div>
          )}
        </div>
        <ActionBtn onClick={() => onAction('keep')} icon="📌" label="Behalten" className="bg-slate-800 hover:bg-slate-700 border border-slate-600/40" />
      </div>
    </div>
  );
}
