import { useEffect, useState } from 'react';
import { cx } from '../lib/api';
import Loader from '../components/Loader';
import { Users, BarChart3 } from 'lucide-react';

export default function Team() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cx.qaLeaderboard()
      .then(setLeaderboard)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Users size={24} /> Team Performance
      </h1>

      {leaderboard.length === 0 ? (
        <div className="card p-12 text-center text-slate-400">No team data available</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-3 font-medium text-slate-600">Rank</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Agent</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Avg Score</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Evaluations</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Total Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leaderboard.map((agent, i) => (
                <tr key={agent.user_id || agent.agent_id || i} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold ${
                      i === 0 ? 'bg-yellow-100 text-yellow-700' :
                      i === 1 ? 'bg-slate-200 text-slate-700' :
                      i === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-slate-50 text-slate-500'
                    }`}>
                      {i + 1}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium">{agent.full_name || agent.agent_name || `Agent ${agent.user_id}`}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${
                      agent.avg_score >= 80 ? 'text-green-600' :
                      agent.avg_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {agent.avg_score?.toFixed(1) ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{agent.evals ?? agent.evaluation_count ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{agent.total_score ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
