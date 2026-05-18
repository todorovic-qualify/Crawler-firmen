'use client';

import { signIn } from 'next-auth/react';

const FEATURES = [
  { icon: '🔍', label: 'E-Mails analysieren', desc: 'Automatisch nach Absender & Kategorie gruppiert' },
  { icon: '📊', label: 'Dashboard-Übersicht', desc: 'Newsletter, Rechnungen, Duplikate auf einen Blick' },
  { icon: '🛡️', label: 'Sicher & kontrolliert', desc: 'Keine Aktion ohne deine ausdrückliche Bestätigung' },
  { icon: '🏷️', label: 'Gmail Labels', desc: 'Automatisch Labels erstellen und zuweisen' },
];

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-indigo-600 mb-6 shadow-lg shadow-indigo-900/50">
          <span className="text-4xl">📤</span>
        </div>
        <h1 className="text-4xl font-bold text-white mb-3">Gmail Cleanup Dashboard</h1>
        <p className="text-slate-400 text-lg max-w-md">
          Analysiere dein Postfach, erkenne Muster und räume auf — immer mit deiner Bestätigung.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg mb-8">
        {FEATURES.map((f) => (
          <div key={f.label} className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 flex gap-3">
            <span className="text-2xl flex-shrink-0">{f.icon}</span>
            <div>
              <p className="font-semibold text-white text-sm">{f.label}</p>
              <p className="text-slate-400 text-xs mt-0.5">{f.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
        className="flex items-center gap-3 bg-white hover:bg-slate-100 text-slate-900 font-semibold px-8 py-4 rounded-2xl text-lg transition-all shadow-lg hover:scale-105 active:scale-95"
      >
        <svg viewBox="0 0 24 24" className="w-6 h-6" xmlns="http://www.w3.org/2000/svg">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        Mit Google anmelden
      </button>

      <p className="text-slate-600 text-xs mt-6 max-w-sm text-center">
        Die App benötigt Lese- und Schreibzugriff auf Gmail. Schreibzugriff wird{' '}
        <strong className="text-slate-500">ausschließlich</strong> verwendet, wenn du eine Aktion
        manuell bestätigst. E-Mail-Inhalte werden nicht gespeichert.
      </p>
    </div>
  );
}
