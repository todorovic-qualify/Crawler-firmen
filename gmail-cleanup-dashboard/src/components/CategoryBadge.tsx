import { Category, CATEGORY_LABELS } from '@/types/email';

const STYLES: Record<Category, string> = {
  pv_energy:    'bg-yellow-900/60 text-yellow-300 border-yellow-700/50',
  qualify_ai:   'bg-violet-900/60 text-violet-300 border-violet-700/50',
  finance:      'bg-emerald-900/60 text-emerald-300 border-emerald-700/50',
  construction: 'bg-orange-900/60 text-orange-300 border-orange-700/50',
  newsletter:   'bg-pink-900/60 text-pink-300 border-pink-700/50',
  important:    'bg-red-900/60 text-red-300 border-red-700/50',
  other:        'bg-slate-800/60 text-slate-400 border-slate-600/50',
};

const ICONS: Record<Category, string> = {
  pv_energy: '☀️', qualify_ai: '🤖', finance: '💶',
  construction: '🏗️', newsletter: '📧', important: '⭐', other: '📂',
};

export default function CategoryBadge({ category, size = 'sm' }: { category: Category; size?: 'xs' | 'sm' }) {
  const px = size === 'xs' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${px} ${STYLES[category]}`}>
      <span>{ICONS[category]}</span>
      {CATEGORY_LABELS[category]}
    </span>
  );
}
