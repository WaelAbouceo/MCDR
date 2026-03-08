import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { cx } from '../lib/api';
import Pagination from '../components/Pagination';
import Loader from '../components/Loader';
import { StatusBadge, PriorityBadge } from '../components/StatusBadge';
import { AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const PAGE_SIZE = 25;

export default function Escalations() {
  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await cx.searchCasesPaginated({
        status: 'escalated',
        limit: PAGE_SIZE,
        offset,
      });
      setCases(result.items || []);
      setTotal(result.total ?? 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Loader />;

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-2">
        <AlertTriangle className="text-red-500" size={24} />
        <h1 className="text-2xl font-bold">Escalated Cases</h1>
        <span className="badge badge-escalated ml-2">{total}</span>
      </div>

      {cases.length === 0 ? (
        <div className="card p-12 text-center text-slate-400">
          No escalated cases. All clear!
        </div>
      ) : (
        <div className="grid gap-4">
          {cases.map((c) => (
            <div
              key={c.case_id}
              onClick={() => navigate(`/cases/${c.case_id}`)}
              className="card p-5 hover:border-red-300 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{c.subject}</p>
                  <p className="text-sm text-slate-500 mt-1">
                    <span className="font-mono text-xs text-indigo-600">{c.case_number}</span>
                    {' · '}
                    {c.investor_name || 'Unknown investor'}
                    {' · Agent: '}
                    {c.agent_name || 'Unassigned'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <PriorityBadge priority={c.priority} />
                  <span className="text-xs text-slate-400">
                    {c.created_at ? formatDistanceToNow(new Date(c.created_at), { addSuffix: true }) : ''}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Pagination offset={offset} limit={PAGE_SIZE} total={total} onChange={setOffset} />
    </div>
  );
}
