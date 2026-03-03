import { useNavigate } from 'react-router-dom';
import { StatusBadge, PriorityBadge } from './StatusBadge';
import { formatDistanceToNow } from 'date-fns';

export default function CaseTable({ cases, showAgent = false, emptyMsg = 'No cases found' }) {
  const navigate = useNavigate();

  if (!cases || cases.length === 0) {
    return (
      <div className="card p-12 text-center text-slate-400">
        <p>{emptyMsg}</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-3 font-medium text-slate-600">Case #</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Subject</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Priority</th>
              {showAgent && (
                <th className="text-left px-4 py-3 font-medium text-slate-600">Agent</th>
              )}
              <th className="text-left px-4 py-3 font-medium text-slate-600">Investor</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {cases.map((c) => (
              <tr
                key={c.case_id || c.id}
                onClick={() => navigate(`/cases/${c.case_id || c.id}`)}
                className="hover:bg-slate-50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3 font-mono text-xs text-indigo-600">
                  {c.case_number || `#${c.case_id || c.id}`}
                </td>
                <td className="px-4 py-3 max-w-xs truncate">{c.subject}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={c.status} />
                </td>
                <td className="px-4 py-3">
                  <PriorityBadge priority={c.priority} />
                </td>
                {showAgent && <td className="px-4 py-3 text-slate-500">{c.agent_name || c.agent_id || '—'}</td>}
                <td className="px-4 py-3 text-slate-500">
                  {c.investor_name || c.investor_id || c.customer_id || '—'}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">
                  {c.created_at
                    ? formatDistanceToNow(new Date(c.created_at), { addSuffix: true })
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
