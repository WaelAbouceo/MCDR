import { useEffect, useState } from 'react';
import { cx } from '../lib/api';
import Loader from '../components/Loader';
import { BarChart3, Trophy } from 'lucide-react';

export default function Leaderboard() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cx.qaLeaderboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Trophy size={24} /> QA Leaderboard
      </h1>

      {data.length === 0 ? (
        <div className="card p-12 text-center text-slate-400">No QA data yet</div>
      ) : (
        <div className="space-y-3">
          {data.map((agent, i) => {
            const pct = agent.avg_score ? Math.min(agent.avg_score, 100) : 0;
            return (
              <div key={agent.agent_id || i} className="card p-5">
                <div className="flex items-center gap-4">
                  <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full text-lg font-bold ${
                    i === 0 ? 'bg-yellow-100 text-yellow-700' :
                    i === 1 ? 'bg-slate-200 text-slate-700' :
                    i === 2 ? 'bg-orange-100 text-orange-700' :
                    'bg-slate-50 text-slate-400'
                  }`}>
                    {i + 1}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{agent.full_name || agent.agent_name || `Agent ${agent.user_id}`}</span>
                      <span className={`text-lg font-bold ${
                        pct >= 80 ? 'text-green-600' : pct >= 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {agent.avg_score?.toFixed(1)}
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {agent.evals || agent.evaluation_count} evaluations
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
