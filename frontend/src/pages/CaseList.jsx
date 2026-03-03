import { useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { cx } from '../lib/api';
import CaseTable from '../components/CaseTable';
import Loader from '../components/Loader';
import { Search, Filter } from 'lucide-react';

const STATUS_OPTIONS = ['', 'open', 'in_progress', 'pending_customer', 'escalated', 'resolved', 'closed'];
const PRIORITY_OPTIONS = ['', 'critical', 'high', 'medium', 'low'];

export default function CaseList() {
  const { user } = useAuth();
  const role = user?.role_name;
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', priority: '', q: '' });

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      let data;
      if (role === 'agent') {
        data = await cx.agentCases(user.id);
      } else {
        data = await cx.searchCases({ limit: 100, ...filters });
      }
      setCases(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const filtered = cases.filter((c) => {
    if (filters.status && c.status !== filters.status) return false;
    if (filters.priority && c.priority !== filters.priority) return false;
    if (filters.q) {
      const q = filters.q.toLowerCase();
      return (
        c.subject?.toLowerCase().includes(q) ||
        c.case_number?.toLowerCase().includes(q) ||
        c.investor_name?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {role === 'agent' ? 'My Cases' : 'All Cases'}
        </h1>
        <span className="text-sm text-slate-500">{filtered.length} cases</span>
      </div>

      <div className="card p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search cases..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              className="input pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-slate-400" />
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="input w-auto"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <select
              value={filters.priority}
              onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
              className="input w-auto"
            >
              <option value="">All Priorities</option>
              {PRIORITY_OPTIONS.filter(Boolean).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading ? <Loader /> : <CaseTable cases={filtered} showAgent={role !== 'agent'} />}
    </div>
  );
}
