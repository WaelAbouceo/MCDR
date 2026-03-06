import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../lib/auth';
import { cx } from '../lib/api';
import CaseTable from '../components/CaseTable';
import Pagination from '../components/Pagination';
import Loader from '../components/Loader';
import { Search, Filter } from 'lucide-react';

const STATUS_OPTIONS = ['', 'open', 'in_progress', 'pending_customer', 'escalated', 'resolved', 'closed'];
const PRIORITY_OPTIONS = ['', 'critical', 'high', 'medium', 'low'];
const PAGE_SIZE = 25;

export default function CaseList() {
  const { user } = useAuth();
  const role = user?.role_name;
  const isAgent = role === 'agent' || role === 'senior_agent';

  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', priority: '', q: '' });
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isAgent) {
        const data = await cx.agentCases(user.id, PAGE_SIZE);
        setCases(data || []);
        setTotal(data?.length || 0);
      } else {
        const params = { limit: PAGE_SIZE, offset };
        if (filters.status) params.status = filters.status;
        if (filters.priority) params.priority = filters.priority;
        if (filters.q) params.q = filters.q;
        const result = await cx.searchCasesPaginated(params);
        setCases(result.items || result || []);
        setTotal(result.total ?? (result.items || result || []).length);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [isAgent, user?.id, offset, filters.status, filters.priority, filters.q]);

  useEffect(() => { load(); }, [load]);

  function handleFilterChange(key, value) {
    setOffset(0);
    setFilters(prev => ({ ...prev, [key]: value }));
  }

  function handleSearch(e) {
    e.preventDefault();
    setOffset(0);
    setFilters(prev => ({ ...prev, q: searchInput }));
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {isAgent ? 'My Cases' : 'All Cases'}
        </h1>
        <span className="text-sm text-slate-500">
          {isAgent ? `${cases.length} cases` : `${total} cases`}
        </span>
      </div>

      <div className="card p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search cases..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onBlur={() => { if (searchInput !== filters.q) handleSearch(new Event('submit')); }}
              className="input pl-9"
            />
          </form>
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-slate-400" />
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="input w-auto"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <select
              value={filters.priority}
              onChange={(e) => handleFilterChange('priority', e.target.value)}
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

      {loading ? (
        <Loader />
      ) : (
        <>
          <CaseTable cases={cases} showAgent={!isAgent} />
          {!isAgent && (
            <Pagination
              offset={offset}
              limit={PAGE_SIZE}
              total={total}
              onChange={setOffset}
            />
          )}
        </>
      )}
    </div>
  );
}
