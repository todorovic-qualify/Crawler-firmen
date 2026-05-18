export default function StatsCard({
  icon, label, value, sub, color = 'indigo',
}: {
  icon: string; label: string; value: number | string; sub?: string;
  color?: 'indigo' | 'pink' | 'emerald' | 'amber' | 'red';
}) {
  const colors = {
    indigo: 'bg-indigo-900/40 border-indigo-700/40 text-indigo-300',
    pink:   'bg-pink-900/40 border-pink-700/40 text-pink-300',
    emerald:'bg-emerald-900/40 border-emerald-700/40 text-emerald-300',
    amber:  'bg-amber-900/40 border-amber-700/40 text-amber-300',
    red:    'bg-red-900/40 border-red-700/40 text-red-300',
  };
  return (
    <div className={`rounded-2xl border p-4 ${colors[color]}`}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-3xl font-bold text-white">{value}</div>
      <div className="text-sm font-medium mt-1 opacity-90">{label}</div>
      {sub && <div className="text-xs opacity-60 mt-0.5">{sub}</div>}
    </div>
  );
}
