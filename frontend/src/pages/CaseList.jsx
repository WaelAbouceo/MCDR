import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../lib/auth';
import { cx, cases as casesApi, users } from '../lib/api';
import CaseTable from '../components/CaseTable';
import Pagination from '../components/Pagination';
import Loader from '../components/Loader';
import { useToast } from '../components/Toast';
import { Search, Filter } from 'lucide-react';

const STATUS_OPTIONS = ['', 'open', 'in_progress', 'pending_customer', 'escalated', 'resolved', 'closed'];
const PRIORITY_OPTIONS = ['', 'critical', 'high', 'medium', 'low'];
const PAGE_SIZE = 25;

export default function CaseList() {
  const { user } = useAuth();
  const toast = useToast();
  const role = user?.role_name;
  const isAgent = role === 'agent' || role === 'senior_agent';
  const canBulk = role === 'team_lead' || role === 'supervisor' || role === 'admin';

  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', priority: '', q: '' });
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkStatus, setBulkStatus] = useState('');
  const [bulkPriority, setBulkPriority] = useState('');
  const [bulkAgentId, setBulkAgentId] = useState('');
  const [userList, setUserList] = useState([]);
  const [bulkApplying, setBulkApplying] = useState(false);

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

  useEffect(() => {
    if (canBulk) users.list().then((r) => setUserList(Array.isArray(r) ? r : [])).catch(() => {});
  }, [canBulk]);

  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll(ids) {
    setSelectedIds((prev) => {
      const allSelected = ids.length > 0 && ids.every((id) => prev.has(id));
      if (allSelected) return new Set();
      return new Set(ids);
    });
  }

  async function applyBulkStatus() {
    if (!bulkStatus || selectedIds.size === 0) return;
    setBulkApplying(true);
    let ok = 0; let err = 0;
    for (const id of selectedIds) {
      try {
        await casesApi.update(id, { status: bulkStatus });
        ok++;
      } catch {
        err++;
      }
    }
    setBulkApplying(false);
    setBulkStatus('');
    setSelectedIds(new Set());
    load();
    toast(`Updated ${ok} case(s)${err ? `; ${err} failed` : ''}`, ok ? 'success' : 'error');
  }

  async function applyBulkPriority() {
    if (!bulkPriority || selectedIds.size === 0) return;
    setBulkApplying(true);
    let ok = 0; let err = 0;
    for (const id of selectedIds) {
      try {
        await casesApi.update(id, { priority: bulkPriority });
        ok++;
      } catch {
        err++;
      }
    }
    setBulkApplying(false);
    setBulkPriority('');
    setSelectedIds(new Set());
    load();
    toast(`Updated ${ok} case(s)${err ? `; ${err} failed` : ''}`, ok ? 'success' : 'error');
  }

  async function applyBulkReassign() {
    const agentId = bulkAgentId ? parseInt(bulkAgentId, 10) : 0;
    if (!agentId || selectedIds.size === 0) return;
    setBulkApplying(true);
    let ok = 0; let err = 0;
    for (const id of selectedIds) {
      try {
        await casesApi.reassign(id, { agent_id: agentId });
        ok++;
      } catch {
        err++;
      }
    }
    setBulkApplying(false);
    setBulkAgentId('');
    setSelectedIds(new Set());
    load();
    toast(`Reassigned ${ok} case(s)${err ? `; ${err} failed` : ''}`, ok ? 'success' : 'error');
  }

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
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
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

      {canBulk && selectedIds.size > 0 && (
        <div className="card p-4 bg-indigo-50 border border-indigo-200 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-indigo-800">
            {selectedIds.size} selected
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={bulkStatus}
              onChange={(e) => setBulkStatus(e.target.value)}
              className="input py-1.5 w-auto text-sm"
            >
              <option value="">Change status</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <button
              onClick={applyBulkStatus}
              disabled={!bulkStatus || bulkApplying}
              className="btn-primary text-sm py-1.5 px-3"
            >
              Apply status
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={bulkPriority}
              onChange={(e) => setBulkPriority(e.target.value)}
              className="input py-1.5 w-auto text-sm"
            >
              <option value="">Change priority</option>
              {PRIORITY_OPTIONS.filter(Boolean).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <button
              onClick={applyBulkPriority}
              disabled={!bulkPriority || bulkApplying}
              className="btn-primary text-sm py-1.5 px-3"
            >
              Apply priority
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={bulkAgentId}
              onChange={(e) => setBulkAgentId(e.target.value)}
              className="input py-1.5 w-auto text-sm min-w-[140px]"
            >
              <option value="">Reassign to</option>
              {userList.filter((u) => u.id !== user?.id).map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.username}</option>
              ))}
            </select>
            <button
              onClick={applyBulkReassign}
              disabled={!bulkAgentId || bulkApplying}
              className="btn-primary text-sm py-1.5 px-3"
            >
              Reassign
            </button>
          </div>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="btn-secondary text-sm py-1.5 px-3"
          >
            Clear
          </button>
        </div>
      )}

      {loading ? (
        <Loader />
      ) : (
        <>
          <CaseTable
            cases={cases}
            showAgent={!isAgent}
            selectable={canBulk}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
          />
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
