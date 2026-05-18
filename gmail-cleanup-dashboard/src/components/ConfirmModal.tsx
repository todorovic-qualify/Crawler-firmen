'use client';

import { ActionType, ACTION_LABELS, CATEGORY_LABELS, PendingAction } from '@/types/email';

const ACTION_ICONS: Record<ActionType, string> = {
  archive: '📥', delete: '🗑️', markRead: '✅', markUnread: '🔵', addLabel: '🏷️', keep: '📌',
};

export default function ConfirmModal({ pending, executing, onConfirm, onCancel }: {
  pending: PendingAction; executing: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  const dangerous = pending.action === 'delete';
  const actionLabel = pending.action === 'addLabel' && pending.label
    ? `mit Label "${pending.label}" versehen`
    : ACTION_LABELS[pending.action].toLowerCase();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onCancel} />
      <div className={`relative z-10 w-full max-w-md rounded-2xl border p-6 shadow-2xl ${
        dangerous ? 'bg-slate-900 border-red-700/60' : 'bg-slate-900 border-indigo-700/40'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${
            dangerous ? 'bg-red-900' : 'bg-indigo-900'
          }`}>{ACTION_ICONS[pending.action]}</div>
          <div>
            <h3 className="text-lg font-bold">Aktion bestätigen</h3>
            <p className="text-slate-400 text-sm">{CATEGORY_LABELS[pending.category]}</p>
          </div>
        </div>

        <div className={`rounded-xl p-4 mb-4 border text-sm ${
          dangerous ? 'bg-red-950/40 border-red-800/40' : 'bg-indigo-950/40 border-indigo-800/40'
        }`}>
          <p className="text-slate-200">
            Du bist dabei,{' '}
            <span className="font-bold text-white">{pending.count} E-Mail{pending.count !== 1 ? 's' : ''}</span>{' '}
            von{' '}
            <span className="font-semibold text-white">„{pending.senderSummary}“</span>{' '}
            zu{' '}
            <span className={`font-bold ${dangerous ? 'text-red-400' : 'text-indigo-300'}`}>{actionLabel}</span>.
          </p>
        </div>

        {dangerous && (
          <div className="flex items-start gap-2 bg-red-900/30 border border-red-700/40 rounded-xl p-3 mb-4 text-sm text-red-300">
            <span className="mt-0.5 flex-shrink-0">⚠️</span>
            <span>E-Mails im Papierkorb werden nach 30 Tagen automatisch endgültig gelöscht.</span>
          </div>
        )}

        <div className="flex gap-3">
          <button onClick={onCancel} disabled={executing}
            className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-colors">
            Abbrechen
          </button>
          <button onClick={onConfirm} disabled={executing}
            className={`flex-1 font-semibold py-3 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2 ${
              dangerous ? 'bg-red-600 hover:bg-red-500 text-white' : 'bg-indigo-600 hover:bg-indigo-500 text-white'
            }`}>
            {executing ? (
              <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>Wird ausgeführt…</>
            ) : `✓ Ja, ${actionLabel}`}
          </button>
        </div>
      </div>
    </div>
  );
}
