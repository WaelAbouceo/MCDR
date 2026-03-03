import { useEffect, useState, useMemo } from 'react';
import { users } from '../lib/api';
import { useToast } from '../components/Toast';
import Loader from '../components/Loader';
import {
  Users, Search, UserPlus, Edit3, ShieldCheck, ShieldOff,
  X, Check, ChevronDown, Mail, Clock,
} from 'lucide-react';
import { format } from 'date-fns';

const ROLE_COLORS = {
  admin: 'bg-red-100 text-red-700 border-red-200',
  supervisor: 'bg-purple-100 text-purple-700 border-purple-200',
  agent: 'bg-blue-100 text-blue-700 border-blue-200',
  qa_analyst: 'bg-teal-100 text-teal-700 border-teal-200',
};

const TIER_LABELS = { tier1: 'Tier 1', tier2: 'Tier 2' };

export default function UserManagement() {
  const [userList, setUserList] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editUser, setEditUser] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();

  const fetchData = () => {
    setLoading(true);
    Promise.all([users.list(), users.roles()])
      .then(([u, r]) => { setUserList(u); setRoles(r); })
      .catch((e) => toast.error('Failed to load users: ' + e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => {
    return userList.filter((u) => {
      if (roleFilter && u.role?.name !== roleFilter) return false;
      if (statusFilter === 'active' && !u.is_active) return false;
      if (statusFilter === 'inactive' && u.is_active) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          u.username.toLowerCase().includes(q) ||
          u.full_name.toLowerCase().includes(q) ||
          (u.email || '').toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [userList, search, roleFilter, statusFilter]);

  const stats = useMemo(() => ({
    total: userList.length,
    active: userList.filter(u => u.is_active).length,
    byRole: roles.reduce((acc, r) => {
      acc[r.name] = userList.filter(u => u.role?.name === r.name).length;
      return acc;
    }, {}),
  }), [userList, roles]);

  const handleToggleActive = async (user) => {
    try {
      await users.update(user.id, { is_active: !user.is_active });
      toast.success(`${user.full_name} ${user.is_active ? 'deactivated' : 'activated'}`);
      fetchData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading) return <Loader />;

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Users size={24} className="text-indigo-600" /> User Management
        </h1>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <UserPlus size={16} /> Add User
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="card p-3 text-center">
          <div className="text-2xl font-bold text-slate-800">{stats.total}</div>
          <div className="text-xs text-slate-500">Total Users</div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-xs text-slate-500">Active</div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-2xl font-bold text-red-500">{stats.total - stats.active}</div>
          <div className="text-xs text-slate-500">Inactive</div>
        </div>
        {roles.slice(0, 3).map(r => (
          <div key={r.name} className="card p-3 text-center">
            <div className="text-2xl font-bold text-slate-700">{stats.byRole[r.name] || 0}</div>
            <div className="text-xs text-slate-500 capitalize">{r.name.replace('_', ' ')}s</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card p-3 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, username, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-9 w-full"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="input w-auto text-sm"
        >
          <option value="">All Roles</option>
          {roles.map(r => (
            <option key={r.name} value={r.name}>{r.name.replace('_', ' ')}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input w-auto text-sm"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-3 font-semibold text-slate-600">User</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Username</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Email</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Role</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Tier</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Status</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Created</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${u.is_active ? 'bg-indigo-500' : 'bg-slate-400'}`}>
                        {u.full_name?.charAt(0)?.toUpperCase() || '?'}
                      </div>
                      <span className="font-medium text-slate-800">{u.full_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{u.username}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{u.email || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${ROLE_COLORS[u.role?.name] || 'bg-slate-100 text-slate-600'}`}>
                      {u.role?.name?.replace('_', ' ') || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {TIER_LABELS[u.tier] || u.tier || '—'}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                        <ShieldCheck size={12} /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-600">
                        <ShieldOff size={12} /> Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {u.created_at ? format(new Date(u.created_at), 'MMM d, yyyy') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => setEditUser(u)}
                        className="p-1.5 rounded hover:bg-slate-200 text-slate-500 hover:text-indigo-600 transition-colors"
                        title="Edit"
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={`p-1.5 rounded transition-colors ${
                          u.is_active
                            ? 'hover:bg-red-100 text-slate-500 hover:text-red-600'
                            : 'hover:bg-green-100 text-slate-500 hover:text-green-600'
                        }`}
                        title={u.is_active ? 'Deactivate' : 'Activate'}
                      >
                        {u.is_active ? <ShieldOff size={14} /> : <ShieldCheck size={14} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                    No users match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit User Modal */}
      {editUser && (
        <EditUserModal
          user={editUser}
          roles={roles}
          onClose={() => setEditUser(null)}
          onSaved={() => { setEditUser(null); fetchData(); }}
          toast={toast}
        />
      )}

      {/* Create User Modal */}
      {showCreate && (
        <CreateUserModal
          roles={roles}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); fetchData(); }}
          toast={toast}
        />
      )}
    </div>
  );
}

function EditUserModal({ user, roles, onClose, onSaved, toast }) {
  const [form, setForm] = useState({
    full_name: user.full_name,
    role_id: user.role?.id || '',
    tier: user.tier || 'tier1',
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await users.update(user.id, form);
      toast.success(`${form.full_name} updated`);
      onSaved();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Edit3 size={18} className="text-indigo-600" /> Edit User
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div className="text-xs text-slate-400 font-mono">
            ID: {user.id} · Username: {user.username}
          </div>
          <div>
            <label className="label">Full Name</label>
            <input
              type="text"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="input w-full"
            />
          </div>
          <div>
            <label className="label">Role</label>
            <select
              value={form.role_id}
              onChange={(e) => setForm({ ...form, role_id: parseInt(e.target.value) })}
              className="input w-full"
            >
              {roles.map(r => (
                <option key={r.id} value={r.id}>{r.name.replace('_', ' ')} — {r.description || ''}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Tier</label>
            <select
              value={form.tier}
              onChange={(e) => setForm({ ...form, tier: e.target.value })}
              className="input w-full"
            >
              <option value="tier1">Tier 1</option>
              <option value="tier2">Tier 2</option>
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="btn btn-secondary text-sm">Cancel</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary text-sm flex items-center gap-1"
          >
            <Check size={14} /> {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

function CreateUserModal({ roles, onClose, onCreated, toast }) {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role_id: roles[0]?.id || 1,
    tier: 'tier1',
  });
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    if (!form.username || !form.password || !form.full_name) {
      toast.warning('Please fill in all required fields');
      return;
    }
    setSaving(true);
    try {
      await users.create(form);
      toast.success(`User "${form.username}" created`);
      onCreated();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <UserPlus size={18} className="text-green-600" /> Create User
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Username *</label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="input w-full"
                placeholder="e.g. agent10"
              />
            </div>
            <div>
              <label className="label">Full Name *</label>
              <input
                type="text"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                className="input w-full"
                placeholder="e.g. John Doe"
              />
            </div>
          </div>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="input w-full"
              placeholder="e.g. john@company.com"
            />
          </div>
          <div>
            <label className="label">Password *</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="input w-full"
              placeholder="Min 8 characters"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Role</label>
              <select
                value={form.role_id}
                onChange={(e) => setForm({ ...form, role_id: parseInt(e.target.value) })}
                className="input w-full"
              >
                {roles.map(r => (
                  <option key={r.id} value={r.id}>{r.name.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Tier</label>
              <select
                value={form.tier}
                onChange={(e) => setForm({ ...form, tier: e.target.value })}
                className="input w-full"
              >
                <option value="tier1">Tier 1</option>
                <option value="tier2">Tier 2</option>
              </select>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-5 border-t">
          <button onClick={onClose} className="btn btn-secondary text-sm">Cancel</button>
          <button
            onClick={handleCreate}
            disabled={saving}
            className="btn-primary text-sm flex items-center gap-1"
          >
            <UserPlus size={14} /> {saving ? 'Creating...' : 'Create User'}
          </button>
        </div>
      </div>
    </div>
  );
}
