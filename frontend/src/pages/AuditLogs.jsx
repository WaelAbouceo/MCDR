import { useEffect, useState, useMemo, useCallback } from 'react';
import { audit, users } from '../lib/api';
import Loader from '../components/Loader';
import {
  ScrollText, Search, ChevronLeft, ChevronRight,
  Filter, Clock, User, Globe, AlertCircle, Eye,
  FileText, Shield, ArrowUpDown, X,
} from 'lucide-react';
import { format } from 'date-fns';

const PAGE_SIZE = 50;

const ACTION_COLORS = {
  GET:        'bg-blue-50 text-blue-700 border-blue-200',
  POST:       'bg-green-50 text-green-700 border-green-200',
  PATCH:      'bg-amber-50 text-amber-700 border-amber-200',
  DELETE:     'bg-red-50 text-red-700 border-red-200',
  PUT:        'bg-amber-50 text-amber-700 border-amber-200',
  page_view:  'bg-purple-50 text-purple-700 border-purple-200',
  read:       'bg-sky-50 text-sky-700 border-sky-200',
  create:     'bg-emerald-50 text-emerald-700 border-emerald-200',
  update:     'bg-orange-50 text-orange-700 border-orange-200',
  add_note:   'bg-teal-50 text-teal-700 border-teal-200',
  search:     'bg-indigo-50 text-indigo-700 border-indigo-200',
  escalate:   'bg-rose-50 text-rose-700 border-rose-200',
};

function actionBadge(action) {
  const cls = ACTION_COLORS[action] || 'bg-slate-50 text-slate-600 border-slate-200';
  return `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`;
}

function statusBadge(code) {
  if (!code) return null;
  if (code < 300) return 'bg-green-100 text-green-700';
  if (code < 400) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
}

function parseDetail(detail) {
  if (!detail) return {};
  const parts = detail.split(' | ');
  const obj = {};
  for (const p of parts) {
    const eq = p.indexOf('=');
    if (eq > 0) {
      obj[p.slice(0, eq)] = p.slice(eq + 1);
    }
  }
  return obj;
}

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [userMap, setUserMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [expandedId, setExpandedId] = useState(null);

  const [filters, setFilters] = useState({
    q: '',
    action: '',
    resource: '',
    user_id: '',
    from_date: '',
    to_date: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = useCallback(() => {
    setLoading(true);
    const params = { limit: PAGE_SIZE, offset };
    if (filters.action) params.action = filters.action;
    if (filters.resource) params.resource = filters.resource;
    if (filters.user_id) params.user_id = filters.user_id;
    if (filters.from_date) params.from_date = filters.from_date;
    if (filters.to_date) params.to_date = filters.to_date;
    audit.logs(params)
      .then(setLogs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [offset, filters]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    users.list()
      .then(list => {
        const map = {};
        for (const u of list) map[u.id] = u;
        setUserMap(map);
      })
      .catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    if (!filters.q) return logs;
    const q = filters.q.toLowerCase();
    return logs.filter((l) =>
      l.action?.toLowerCase().includes(q) ||
      l.resource?.toLowerCase().includes(q) ||
      l.detail?.toLowerCase().includes(q) ||
      (userMap[l.user_id]?.username || '').toLowerCase().includes(q) ||
      l.ip_address?.toLowerCase().includes(q)
    );
  }, [logs, filters.q, userMap]);

  const actions = useMemo(() => [...new Set(logs.map(l => l.action).filter(Boolean))].sort(), [logs]);
  const resources = useMemo(() => [...new Set(logs.map(l => l.resource).filter(Boolean))].sort(), [logs]);
  const activeFilterCount = [filters.action, filters.resource, filters.user_id, filters.from_date, filters.to_date]
    .filter(Boolean).length;

  function clearFilters() {
    setFilters({ q: '', action: '', resource: '', user_id: '', from_date: '', to_date: '' });
    setOffset(0);
  }

  function resolveUser(userId) {
    if (!userId) return { name: 'System', role: '—' };
    const u = userMap[userId];
    return u
      ? { name: u.full_name || u.username, role: u.role?.name || '—' }
      : { name: `#${userId}`, role: '—' };
  }

  return (
    <div className="p-4 sm:p-6 max-w-[1400px] mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield size={24} className="text-indigo-600" /> Audit Trail
        </h1>
        <span className="text-sm text-slate-500">
          {filtered.length} entries {offset > 0 && `(page ${Math.floor(offset / PAGE_SIZE) + 1})`}
        </span>
      </div>

      {/* Search + Filter Toggle */}
      <div className="card p-3 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[220px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by action, resource, user, IP, detail..."
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            className="input pl-9 w-full"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`btn btn-secondary flex items-center gap-1.5 text-sm ${showFilters ? 'ring-2 ring-indigo-300' : ''}`}
        >
          <Filter size={15} />
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-1 bg-indigo-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </button>
        {activeFilterCount > 0 && (
          <button onClick={clearFilters} className="btn btn-secondary text-sm flex items-center gap-1 text-red-600">
            <X size={14} /> Clear
          </button>
        )}
      </div>

      {/* Expandable Filter Panel */}
      {showFilters && (
        <div className="card p-4 grid grid-cols-2 md:grid-cols-5 gap-3 border-l-4 border-indigo-400">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Action</label>
            <select
              value={filters.action}
              onChange={(e) => { setFilters({ ...filters, action: e.target.value }); setOffset(0); }}
              className="input w-full text-sm"
            >
              <option value="">All Actions</option>
              {actions.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Resource</label>
            <select
              value={filters.resource}
              onChange={(e) => { setFilters({ ...filters, resource: e.target.value }); setOffset(0); }}
              className="input w-full text-sm"
            >
              <option value="">All Resources</option>
              {resources.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">User ID</label>
            <input
              type="number"
              placeholder="e.g. 1"
              value={filters.user_id}
              onChange={(e) => { setFilters({ ...filters, user_id: e.target.value }); setOffset(0); }}
              className="input w-full text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">From Date</label>
            <input
              type="datetime-local"
              value={filters.from_date}
              onChange={(e) => { setFilters({ ...filters, from_date: e.target.value }); setOffset(0); }}
              className="input w-full text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">To Date</label>
            <input
              type="datetime-local"
              value={filters.to_date}
              onChange={(e) => { setFilters({ ...filters, to_date: e.target.value }); setOffset(0); }}
              className="input w-full text-sm"
            />
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <Loader />
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center text-slate-400">
          <ScrollText size={48} className="mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">No audit entries found</p>
          <p className="text-sm mt-1">Try adjusting your filters or search query</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 font-semibold text-slate-600 whitespace-nowrap">
                    <Clock size={14} className="inline mr-1 -mt-0.5" /> Timestamp
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600 whitespace-nowrap">
                    <User size={14} className="inline mr-1 -mt-0.5" /> User
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600">Action</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600">Resource</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600 whitespace-nowrap">Res. ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600 whitespace-nowrap">
                    <Globe size={14} className="inline mr-1 -mt-0.5" /> IP
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600">Status</th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-600 w-8"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((l) => {
                  const parsed = parseDetail(l.detail);
                  const httpStatus = parsed.status ? parseInt(parsed.status) : null;
                  const elapsed = parsed.elapsed || null;
                  const usr = resolveUser(l.user_id);
                  const isExpanded = expandedId === l.id;

                  return (
                    <tr key={l.id} className="group">
                      <td colSpan={8} className="p-0">
                        <div
                          className={`flex items-center cursor-pointer px-4 py-2.5 hover:bg-slate-50 transition-colors ${isExpanded ? 'bg-indigo-50/50' : ''}`}
                          onClick={() => setExpandedId(isExpanded ? null : l.id)}
                        >
                          {/* Timestamp */}
                          <div className="w-[140px] shrink-0 text-xs text-slate-500 whitespace-nowrap font-mono">
                            {l.timestamp ? format(new Date(l.timestamp), 'MMM d HH:mm:ss') : '—'}
                          </div>

                          {/* User */}
                          <div className="w-[150px] shrink-0">
                            <div className="text-sm font-medium text-slate-700 truncate">{usr.name}</div>
                            <div className="text-[10px] text-slate-400 uppercase tracking-wider">{usr.role}</div>
                          </div>

                          {/* Action */}
                          <div className="w-[100px] shrink-0">
                            <span className={actionBadge(l.action)}>{l.action}</span>
                          </div>

                          {/* Resource */}
                          <div className="w-[220px] shrink-0 text-xs text-slate-600 font-mono truncate" title={l.resource}>
                            {l.resource || '—'}
                          </div>

                          {/* Resource ID */}
                          <div className="w-[60px] shrink-0 text-xs text-slate-500 text-center">
                            {l.resource_id || '—'}
                          </div>

                          {/* IP */}
                          <div className="w-[110px] shrink-0 text-xs text-slate-400 font-mono">
                            {l.ip_address || '—'}
                          </div>

                          {/* Status */}
                          <div className="w-[70px] shrink-0">
                            {httpStatus ? (
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusBadge(httpStatus)}`}>
                                {httpStatus}
                              </span>
                            ) : elapsed ? (
                              <span className="text-xs text-slate-400">{elapsed}</span>
                            ) : null}
                          </div>

                          {/* Expand icon */}
                          <div className="w-[32px] shrink-0 text-right">
                            <Eye size={14} className={`inline text-slate-300 group-hover:text-indigo-500 transition-colors ${isExpanded ? 'text-indigo-500' : ''}`} />
                          </div>
                        </div>

                        {/* Expanded Detail */}
                        {isExpanded && (
                          <div className="px-4 pb-3 pt-1 bg-slate-50 border-t border-slate-100">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                              <div>
                                <span className="text-slate-400 block mb-0.5">Full Timestamp</span>
                                <span className="text-slate-700 font-mono">
                                  {l.timestamp ? format(new Date(l.timestamp), 'yyyy-MM-dd HH:mm:ss.SSS') : '—'}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">User ID</span>
                                <span className="text-slate-700">{l.user_id ?? 'N/A'}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">Username</span>
                                <span className="text-slate-700">{parsed.user || usr.name}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">Role</span>
                                <span className="text-slate-700">{parsed.role || usr.role}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">IP Address</span>
                                <span className="text-slate-700 font-mono">{l.ip_address || '—'}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">HTTP Status</span>
                                <span className="text-slate-700">{httpStatus || '—'}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">Response Time</span>
                                <span className="text-slate-700">{elapsed || '—'}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block mb-0.5">Resource ID</span>
                                <span className="text-slate-700">{l.resource_id || '—'}</span>
                              </div>
                            </div>
                            {l.detail && (
                              <div className="mt-3 pt-2 border-t border-slate-200">
                                <span className="text-slate-400 text-xs block mb-1">Raw Detail</span>
                                <pre className="text-xs text-slate-600 bg-white rounded p-2 border border-slate-200 whitespace-pre-wrap break-all font-mono">
                                  {l.detail}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Showing {offset + 1}–{offset + filtered.length}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className="btn btn-secondary text-sm flex items-center gap-1 disabled:opacity-40"
          >
            <ChevronLeft size={16} /> Previous
          </button>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={logs.length < PAGE_SIZE}
            className="btn btn-secondary text-sm flex items-center gap-1 disabled:opacity-40"
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
