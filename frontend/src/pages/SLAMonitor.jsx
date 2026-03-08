import { useEffect, useState } from 'react';
import { cx } from '../lib/api';
import StatCard from '../components/StatCard';
import Loader from '../components/Loader';
import { Shield, AlertTriangle, Clock, BarChart3 } from 'lucide-react';

export default function SLAMonitor() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cx.slaStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  const s = stats || {};
  const byType = s.by_type_and_policy || [];
  const byPriority = s.breach_rate_by_priority || [];

  const totalBreaches = byType.reduce((sum, r) => sum + (r.cnt || 0), 0);
  const firstResponseBreaches = byType
    .filter((r) => r.breach_type === 'first_response')
    .reduce((sum, r) => sum + (r.cnt || 0), 0);
  const resolutionBreaches = byType
    .filter((r) => r.breach_type === 'resolution')
    .reduce((sum, r) => sum + (r.cnt || 0), 0);

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Shield size={24} /> SLA Monitor
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Breaches" value={totalBreaches} icon={AlertTriangle} color="red" />
        <StatCard label="First Response" value={firstResponseBreaches} icon={Clock} color="yellow" />
        <StatCard label="Resolution" value={resolutionBreaches} icon={Shield} color="blue" />
        <StatCard
          label="Policies Tracked"
          value={new Set(byType.map((r) => r.policy)).size}
          icon={BarChart3}
          color="purple"
        />
      </div>

      {byPriority.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4">Breach Rate by Priority</h3>
          <div className="space-y-4">
            {byPriority.map((p) => (
              <div key={p.priority}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium capitalize">{p.priority}</span>
                  <span className="text-sm text-slate-500">
                    {p.breached}/{p.total} ({p.pct}%)
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      p.pct >= 70 ? 'bg-red-500' : p.pct >= 40 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(p.pct, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {byType.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4">Breaches by Type & Policy</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Policy</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Breach Type</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Count</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {byType.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium">{r.policy}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${
                        r.breach_type === 'first_response' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {r.breach_type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold">{r.cnt?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
