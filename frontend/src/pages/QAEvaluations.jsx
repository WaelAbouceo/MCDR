import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cx, qa } from '../lib/api';
import Loader from '../components/Loader';
import StatCard from '../components/StatCard';
import { ClipboardCheck, Star, TrendingUp, Users } from 'lucide-react';
import { format } from 'date-fns';

export default function QAEvaluations() {
  const [evals, setEvals] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    qa.listEvaluations({ limit: 50 })
      .then(setEvals)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  const avgScore = evals.length > 0
    ? (evals.reduce((sum, e) => sum + (e.total_score || 0), 0) / evals.length).toFixed(1)
    : '—';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <ClipboardCheck size={24} /> QA Evaluations
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Total Evaluations" value={evals.length} icon={ClipboardCheck} color="teal" />
        <StatCard label="Avg Score" value={avgScore} icon={Star} color="yellow" />
        <StatCard
          label="Unique Agents"
          value={new Set(evals.map(e => e.agent_id)).size}
          icon={Users}
          color="purple"
        />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-3 font-medium text-slate-600">Case</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Agent</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Score</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Feedback</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {evals.map((e, i) => (
              <tr
                key={e.id || i}
                onClick={() => e.case_id && navigate(`/cases/${e.case_id}`)}
                className="hover:bg-slate-50 cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-xs text-indigo-600">
                  {e.case_id || '—'}
                </td>
                <td className="px-4 py-3">{e.agent_id || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`font-bold ${
                    e.total_score >= 80 ? 'text-green-600' :
                    e.total_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {e.total_score ?? '—'}
                  </span>
                </td>
                <td className="px-4 py-3 max-w-xs truncate text-slate-500">
                  {e.feedback || '—'}
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">
                  {e.evaluated_at ? format(new Date(e.evaluated_at), 'MMM d, HH:mm') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
