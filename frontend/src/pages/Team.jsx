import { useEffect, useState } from 'react';
import { cx } from '../lib/api';
import Loader from '../components/Loader';
import { Users, BarChart3, Circle } from 'lucide-react';

const PRESENCE_LABELS = {
  available: { label: 'Available', color: 'text-green-500', bg: 'bg-green-100 text-green-700' },
  on_break: { label: 'On Break', color: 'text-yellow-500', bg: 'bg-yellow-100 text-yellow-700' },
  acw: { label: 'ACW', color: 'text-blue-500', bg: 'bg-blue-100 text-blue-700' },
  in_call: { label: 'In Call', color: 'text-orange-500', bg: 'bg-orange-100 text-orange-700' },
  training: { label: 'Training', color: 'text-purple-500', bg: 'bg-purple-100 text-purple-700' },
  offline: { label: 'Offline', color: 'text-slate-400', bg: 'bg-slate-100 text-slate-500' },
};

export default function Team() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [presenceList, setPresenceList] = useState([]);
  const [presenceSummary, setPresenceSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('presence');

  useEffect(() => {
    Promise.all([
      cx.qaLeaderboard().catch(() => []),
      cx.presenceList().catch(() => []),
      cx.presenceSummary().catch(() => ({})),
    ])
      .then(([lb, pl, ps]) => {
        setLeaderboard(lb);
        setPresenceList(pl);
        setPresenceSummary(ps);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  const totalAgents = Object.values(presenceSummary).reduce((a, b) => a + b, 0);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Users size={24} /> Team
      </h1>

      {/* Presence Summary Cards */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {Object.entries(PRESENCE_LABELS).map(([key, meta]) => (
          <div key={key} className="card p-3 text-center">
            <Circle size={10} className={`inline ${meta.color} fill-current`} />
            <div className="text-xl font-bold mt-1">{presenceSummary[key] || 0}</div>
            <div className="text-[11px] text-slate-500">{meta.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('presence')}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${tab === 'presence' ? 'bg-white shadow text-slate-900 font-medium' : 'text-slate-500 hover:text-slate-700'}`}
        >
          Live Status ({totalAgents})
        </button>
        <button
          onClick={() => setTab('performance')}
          className={`px-4 py-1.5 text-sm rounded-md transition-colors ${tab === 'performance' ? 'bg-white shadow text-slate-900 font-medium' : 'text-slate-500 hover:text-slate-700'}`}
        >
          QA Performance
        </button>
      </div>

      {tab === 'presence' && (
        presenceList.length === 0 ? (
          <div className="card p-12 text-center text-slate-400">No presence data available</div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Agent</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Role</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Since</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {presenceList.map((a) => {
                  const meta = PRESENCE_LABELS[a.status] || PRESENCE_LABELS.offline;
                  return (
                    <tr key={a.agent_id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-medium">{a.full_name}</td>
                      <td className="px-4 py-3 text-slate-500 capitalize">{(a.role || '').replace('_', ' ')}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${meta.bg}`}>
                          <Circle size={6} className="fill-current" />
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">{a.updated_at || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}

      {tab === 'performance' && (
        leaderboard.length === 0 ? (
          <div className="card p-12 text-center text-slate-400">No QA data available</div>
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
        )
      )}
    </div>
  );
}
